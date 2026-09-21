# [BE] Add deletion-lock functions to openedx_tagging

GitHub: https://github.com/openedx/openedx-core/issues/777 (#777, OPEN)
Cached: 2026-09-21

## User Story

As a plugin or feature developer building on tagging, I want to mark a tag association as depended upon by my feature, in order to have the tagging app retire it rather than destroy it when someone deletes it, without the tagging app needing to know anything about my feature.

## Acceptance Criteria

Not testable via Postman or the frontend, now or after any later ticket lands: this ticket adds no REST endpoint and none is planned. Acceptance is determined by a PR reviewer confirming the following against the API functions and their unit tests:

- [ ] `lock_object_tag_for_deletion()` sets `deletion_locked=True` on the given association(s); reading an association back afterward reports it as locked.  
- [ ] Locking an already-locked association is idempotent: it remains locked and the call succeeds without error.  
- [ ] A single call can lock several associations at once; every one of them reports as locked afterward.  
- [ ] Locking an id that does not resolve to an existing association raises (the model's `DoesNotExist`) and writes nothing, rather than silently succeeding or partially applying.  
- [ ] Locking an association changes only `deletion_locked`: `archived` and the object, taxonomy, and tag it joins are all unchanged.  
- [ ] `get_tags_locked_for_deletion()` reports a tag as in use when at least one association beneath it is locked, and not in use when none are.  
- [ ] `is_taxonomy_locked_for_deletion()` reports a taxonomy as in use when at least one association anywhere beneath it is locked.  
- [ ] An archived association that is still locked continues to count toward its tag's and taxonomy's in-use answer (both functions use \#778's opt-out to see archived rows, not the default filter that hides them).  
- [ ] A query-count test over a large set of tags shows `get_tags_locked_for_deletion()`'s query count does not grow with the size of the set.

## Description

`openedx_tagging` has no way for another app to tell it that a record is depended upon. The field to record that arrives on `ObjectTag` in \#776, but nothing sets it, and nothing answers the question for the tag and taxonomy above it.

This ticket adds both halves: `lock_object_tag_for_deletion()`, the function a caller invokes to lock an association, and two more functions, `get_tags_locked_for_deletion()` and `is_taxonomy_locked_for_deletion()`, that answer whether a tag or a taxonomy has any locked association beneath it. \#782 is the first caller of the former; \#779 and \#780 are the callers of the latter two. No endpoints are created or modified by this ticket.

<details>
<summary>Technical Details</summary>

This section is background and a suggested approach, not the ticket's source of truth. The User Story and Acceptance Criteria define what must be true when the work is done.

### In short

**What the API is for.** A caller that stores data referencing a tag association calls the lock function to record that fact. From then on, deleting that association retires it instead of removing it, which is what keeps the caller's references resolvable. The tagging app never learns why the association is locked, only that it is.

**Only associations are locked; tags and taxonomies are asked about.** The dependency always attaches to an association, because that is what a competency criterion points at. A tag matters because associations exist beneath it, and a taxonomy because associations exist somewhere in it. So there is one setter, for associations, and two reader functions, `get_tags_locked_for_deletion()` and `is_taxonomy_locked_for_deletion()`,  
 that walk down from a tag or a taxonomy to answer the same question for them.

**Archived associations still count.** An association that was locked and then removed is archived rather than deleted, and it keeps its lock. It must still make the tag above it count as in use, or deleting that tag would destroy the association the learner's mastery hangs off. This ticket's own reader functions (described below, under Implementation specifics) therefore have to see archived rows, even though \#778's normal read paths will hide archived rows by default once it lands. Both functions must use the opt-out \#778 documents rather than the default filter that hides archived rows elsewhere.

**The derivation must answer for a whole set of tags at once, not one at a time.** Deleting a tag with subtags expands to that tag plus every descendant beneath it, potentially many rows, and \#780's delete branch needs to know which of all of them are in use before deciding what to archive versus what to delete. If `get_tags_locked_for_deletion()` could only answer "is this one tag in use?", \#780 would have to call it once per tag in that subtree, one query per row, on an operation that can span a large tree. Instead, it accepts a whole collection of tag ids in a single call and returns which of them are in use, so \#780 makes one query no matter how many tags it is asking about.

**No unlock function, deliberately.** Nothing in the approved approach removes a lock. A learner mastery status is never deleted, so the dependency that justified the lock never goes away. Adding an unlock now would be an unused function on a public API that later has to be supported. **Decided:** unlocking is out of scope for this MVP. If a lock ever needs clearing, that happens directly against the database, by SQL or the Django admin, not through a supported API call; this ticket does not build a path for it.

### Implementation specifics

- **One setter in `src/openedx_tagging/api.py`:** `lock_object_tag_for_deletion()`, added to the module's public surface. Do not add `lock_tag_for_deletion` or `lock_taxonomy_for_deletion`; those records have no field to set.  
- **Accept identifiers, not model instances**, consistent with the rest of `src/openedx_tagging/api.py`, whose module docstring states that callers use the API rather than the models. Accept either a single id or an iterable so a caller writing several status rows locks in one query rather than one per row.  
- **Implement the setter as a single bulk `.update(deletion_locked=True)`** over the given ids rather than a fetch-then-save loop. Raise the model's `DoesNotExist` when an id does not resolve, and do so before any write, so a partly-applied lock is not possible.  
- **Add two more functions to `src/openedx_tagging/api.py`, also public:** `get_tags_locked_for_deletion(tag_ids)`, answering which of a given set of tags have a locked association, and `is_taxonomy_locked_for_deletion(taxonomy_id)`, answering whether a taxonomy has any locked association anywhere beneath it.  
-   
- **Implement** `get_tags_locked_for_deletion()`  
-  **as one query returning the in-use subset**, along the lines of filtering `ObjectTag` on the given tag ids and `deletion_locked=True` and returning the distinct tag ids found. Do not loop. Return the subset rather than a boolean per tag, so the caller in \#780 can split its removal set in one step.  
- **Implement** `is_taxonomy_locked_for_deletion()`  
-  **as a single existence check** over associations whose tag belongs to that taxonomy. It never needs to enumerate.  
- **Both reader functions must include archived associations.** Use the documented opt-out that \#778 provides rather than adding a second one, and add a test that fails if the opt-out is dropped, because losing it here silently destroys learner history rather than raising.  
- **Do not add an unlock function** and do not expose either field through the REST API. Neither is in the approved approach; adding them creates public surface with no caller.  
- **No permission checks**, matching the contract stated in `src/openedx_tagging/api.py`: the caller authorizes.  
- **Respect the layering.** These functions live in `openedx_tagging` and must not import anything competency-related. Confirm with `lint-imports`.  
- **Tests** in the existing `openedx_tagging` API tests: the setter locks an association; locking twice is idempotent; a list of ids locks all of them in one call; an unknown id raises and writes nothing; locking leaves `archived` and every other field untouched; a tag with a locked association reads as in use and one without does not; a taxonomy reads as in use when any association anywhere beneath it is locked; an archived locked association still makes its tag read as in use; a query-count assertion over a large tag set showing `get_tags_locked_for_deletion()`  
-  does not scale with the set size.  
- **Out of scope:** setting the lock from the competency side (\#782), the delete branches that read it (\#779, \#780), and any UI or REST exposure.

## Files to modify

| File | Nature of modification |
| :---- | :---- |
| src/openedx\_tagging/api.py | add `lock_object_tag_for_deletion()`, `get_tags_locked_for_deletion()`, and `is_taxonomy_locked_for_deletion()` to the public surface  |
| tests/openedx\_tagging/ | idempotency, bulk, unknown-id, no-side-effect, derivation, archived-counts, and query-count tests |

## Context

- The approved implementation approach on \#655, for the push-based lock design.  
- `src/openedx_tagging/api.py`, whose module docstring sets the contract these functions follow: callers use the API rather than the models, and the caller enforces authorization.  
- `.importlinter` for the layering that keeps `openedx_tagging` free of competency concerns.  
- Depends on \#776 for the `deletion_locked` field and \#778 for the opt-out that lets the readers see archived associations. Consumed by \#782, and read by \#779 and \#780.  

</details>
