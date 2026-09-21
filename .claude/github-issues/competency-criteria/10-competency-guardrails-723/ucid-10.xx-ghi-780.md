# [BE] Branch tag and taxonomy deletes between archiving and hard delete

GitHub: https://github.com/openedx/openedx-core/issues/780 (#780, OPEN)
Cached: 2026-09-21

## User Story

As a platform administrator, I want to keep the mastery learners have already earned when a competency or entire competency framework is deleted, so I can reorganize a framework without destroying learner records.

## Acceptance Criteria

### Ordinary path — testable now via Postman or the existing Studio UI

```
Scenario: Deleting a tag nothing depends on removes it outright
  Given a tag that no learner has been evaluated against
  When it is deleted from its taxonomy
  Then the tag no longer exists
    And deletion behaves exactly as it does today

Scenario: Deleting a taxonomy nothing depends on removes it outright
  Given a taxonomy no learner has been evaluated against
  When it is deleted
  Then the taxonomy no longer exists

Scenario: Deleting a tag that does not belong to the taxonomy is still refused
  Given a tag identifier that does not belong to the target taxonomy
  When a delete is requested for it
  Then the request is refused as it is today
    And nothing is archived or deleted
```

### Locked path — testable via Postman or the UI, but needs a manufactured fixture

Nothing sets `deletion_locked=True` (the field \#776 adds) in production yet; \#782 is what does. Exercising any of these today means creating that state directly first (Django admin, shell, or a test fixture).

```
Scenario: Deleting a tag that learner mastery depends on retires it instead
  Given a tag that a learner has been evaluated against
  When it is deleted from its taxonomy
  Then the tag still exists but is archived
    And the learner's mastery status still resolves through it

Scenario: A single bulk request handles a mixture correctly
  Given a taxonomy with three tags, one of which a learner has been evaluated against
  When all three are deleted in one request
  Then the depended-upon tag is archived
    And the other two no longer exist
    And the request reports success once

Scenario: A parent with a depended-upon subtag is archived too, not deleted
  Given a parent tag with no association of its own, a subtag beneath it whose association is locked, and an unrelated sibling subtag with no locked association
  When the parent is deleted with its subtags
  Then the parent and the depended-upon subtag are both archived
    And the unrelated sibling subtag is deleted normally

Scenario: Deleting a taxonomy that learner mastery depends on retires it instead
  Given a taxonomy containing a tag that a learner has been evaluated against
  When the taxonomy is deleted
  Then the taxonomy still exists but is archived
    And the learner's mastery status still resolves through it
```

### Internal distinction — unit-test only, never observable via the API or UI

```
Scenario: The caller cannot tell which of the two happened
  Given one depended-upon tag and one that is not
  When each is deleted
  Then both requests report success in the same way

Scenario: Archiving a taxonomy does not set archived on its own tags
  Given a taxonomy that becomes archived, with unarchived tags beneath it
  When those tags are read directly from the database
  Then their own `archived` field is still False
    And #778's read-path filter, not this field, is what hides them

Scenario: Ordinary subtree deletion still removes every descendant
  Given a tag with two levels of subtags, none of them locked
  When the tag is deleted with its subtags
  Then the tag and every descendant at every level no longer exist
```

## Description

Deleting a tag or a taxonomy today removes the row outright. Once competency mastery is recorded against it, that would leave learner statuses pointing at nothing. `Tag` and `Taxonomy` gain an `archived` field in \#776 and a `deletion_locked` field that \#782 sets, and this ticket makes both delete paths use them.

Two paths need the branch: 

- Tag deletion goes through `Taxonomy.delete_tags()`, which takes a list of tag values and deletes them together, so the branch has to be made per tag inside one bulk request rather than for the request as a whole.  
- Taxonomy deletion goes through a new `perform_destroy()` override on `TaxonomyView`, the method DRF already calls internally on every `DELETE` request and provides specifically to be overridden, so the branch can run without touching the route or its permission checks.

<details>
<summary>Technical Details</summary>

This section is background and a suggested approach, not the ticket's source of truth. The User Story and Acceptance Criteria define what must be true when the work is done.

### In short

**"Locked" means `deletion_locked=True` on an `ObjectTag`, never a database row lock.** Every use of "lock"/"locked" below refers to that boolean field \#776 adds and \#782 sets (read through the functions \#777 provides), not to a `SELECT ... FOR UPDATE` or any other database-level locking mechanism.

**The rule, and how narrow it is.** For each record a delete would remove, if it is locked against deletion, it is archived instead, and if it is not, it is deleted exactly as today. A deployment with no competency mastery recorded sees no change in behavior at all.

**Why the tag branch has to be per tag rather than per request.** `delete_tags()` accepts a list of tag values and deletes them in one operation. A single request can therefore contain a mixture of tags that must be archived and tags that can be removed, and it has to do both and still report one success.

**A locked subtag forces every ancestor above it, up to what was requested, to be archived too.** Deleting a parent nothing depends on, while one of its subtags is locked, cannot hard-delete the parent: doing so would take the archived subtag down with it, since `Tag.parent` cascades on delete. So the rule is not "evaluate each tag on its own lock" but "a tag is archived if it is itself locked, or if any descendant within the requested subtree is." An unrelated sibling subtag with no locked descendant of its own is unaffected and is still deleted normally.

**This needs the full subtree enumerated up front, which nothing today does.** `delete_tags()` currently deletes only the tags named in the request and lets `Tag.parent`'s `CASCADE` remove descendants as a side effect; `with_subtags` is purely a validation gate, not an expansion step. Computing the rule above needs the whole subtree as one flat set first. `Tag` already maintains what this needs: `descendant_count`, just above `delete_tags()` in the same file, finds every descendant of a tag with `taxonomy.tag_set.filter(depth__gt=tag.depth, lineage__startswith=tag.lineage)`, using the `depth`/`lineage` fields every `Tag` already maintains on save. `delete_tags()` should use that same pattern, unioned across every requested tag.

**How a tag or a taxonomy is judged to be depended upon.** Neither carries a lock of its own. Only a tag association does. \#777's `get_tags_locked_for_deletion()` answers this per tag directly, not per subtree; walking from each directly-locked tag up through its ancestors' `lineage` (see above) is this ticket's own addition on top of that answer, not something \#777 needs to change to provide. A taxonomy is depended upon when any association anywhere within it is locked, which \#777's `is_taxonomy_locked_for_deletion()` already answers directly.

**Existing validation stays in front of the branch.** `delete_tags()` already refuses a free-text taxonomy, a read-only taxonomy, a tag value that does not belong to the taxonomy, and a parent with children when subtags were not requested. All of those must still fail the same way, against the originally requested tags, before the subtree is even enumerated.

### Implementation specifics

- **Rewrite the start of `delete_tags()` to enumerate the full removal set before validating or branching anything.** For each requested tag, when `with_subtags` is set, include every descendant via `taxonomy.tag_set.filter(depth__gt=tag.depth, lineage__startswith=tag.lineage)`, the same pattern `descendant_count` already uses. Union this across all requested tags into one flat id set.  
- **Tag branch goes in `Taxonomy.delete_tags()`**, operating on that fully enumerated set, not just the tags named in the request.  
- **Find the directly-locked tags via `get_tags_locked_for_deletion()` (\#777)**, then compute the archive set: each directly-locked tag, plus every ancestor of it whose own `lineage` is a prefix of that tag's `lineage` and which is also in the removal set. Everything else in the removal set is safe to delete.  
- **Split into two bulk operations:** one `.update(archived=True)` over the computed archive set, one `.filter(id__in=...).delete()` over the rest. Do not branch per row inside a loop.  
- **Taxonomy branch goes in a new `perform_destroy()` override on the `TaxonomyView` class** in `src/openedx_tagging/rest_api/v1/views.py`. Archive the taxonomy when it is locked and delete it otherwise. Keep the response identical in both cases.  
- **The derived answers must count archived associations.** An association that was already removed is archived and keeps its lock, and the tag above it is still depended upon. \#777's readers include archived rows for exactly this reason; do not filter them out here, and do not reimplement the query locally, where that guarantee could quietly be lost.  
- **Preserve every existing error.** The free-text, read-only, foreign-tag, and children-without-subtags failures in `delete_tags()` must raise before any write, unchanged.  
- **`delete_tags_from_taxonomy()` in `src/openedx_tagging/api.py` needs no change** if the branch sits in the model method it delegates to. Confirm that and say so rather than editing both.  
- **Archiving a taxonomy has a search-index consequence** that this ticket does not handle: the index keeps serving the archived taxonomy's tags until an event tells it otherwise. That event fan-out is \#781, and the two should be sequenced together so a released version never archives a taxonomy without notifying the index.  
- **Archiving a taxonomy does not set `archived` on its tags by itself.** Only \#778's read-path filter hides an archived taxonomy's tags, matching the same resolution already applied to \#778; the field is not cascaded automatically just because a taxonomy or a parent tag becomes archived through some other, unrelated action. This is distinct from the ancestor archiving above, which is this ticket's own delete request explicitly computing and setting `archived=True` on specific ancestors as part of deciding what that one request does, not an automatic side effect of another tag's state changing.  
- **Tests** in the existing `openedx_tagging` model and REST test modules, one per acceptance scenario, plus: a mixed bulk request that archives some rows and deletes others in one call; a mixed subtree at two or more levels of depth, including an ancestor with no lock of its own that must still be archived because of a locked descendant, alongside an unrelated sibling that is still deleted; a query-count assertion showing the branch does not add a query per row; and confirmation that each existing validation error still fires and writes nothing.  
- **Out of scope:** setting the lock (\#782), tag association deletes (\#779), the archive event fan-out (\#781), and hiding archived records from reads (\#778).  
- 

## Files to modify

| File | Nature of modification |
| :---- | :---- |
| src/openedx\_tagging/models/base.py | rewrite `delete_tags()` to enumerate the subtree via `depth`/`lineage`, compute the ancestor-aware archive set, then branch between archive and delete  |
| src/openedx\_tagging/rest\_api/v1/views.py | add a `perform_destroy()` override to the `TaxonomyView` class and branch it between archive and delete  |
| tests/openedx\_tagging/ | one test per scenario, a mixed bulk and mixed subtree test, a query-count assertion, and existing-validation regression tests |

## Context

- The approved implementation approach on \#655: archive only when a learner status row exists, and the caller is not told which happened.  
- `src/openedx_tagging/models/base.py`, `Taxonomy.delete_tags()`, for the existing validation and subtag expansion this branch sits behind.  
- `src/openedx_tagging/rest_api/v1/views.py`, the `TaxonomyView` and `TaxonomyTagsView` classes, for the delete surfaces.  
- Depends on \#776 for both fields and \#777 for the lock query. The lock is set by \#782, which must lock the taxonomy as well as the tag for the taxonomy branch to be correct. Sequence alongside \#781.

</details>
