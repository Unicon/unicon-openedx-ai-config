# [BE] Branch tag association deletes between archiving and hard delete

GitHub: https://github.com/openedx/openedx-core/issues/779 (#779, OPEN)
Cached: 2026-09-21

## User Story

As a course author, I want to keep the mastery already recorded against it when I remove a competency tag from content, so I don't destroy learners' earned competency history when tidying up a course.

## Acceptance Criteria

This ticket modifies an existing endpoint (see Description), so testability differs by category below.

### Ordinary path — testable now via Postman or the existing Studio tagging UI

No lock involved; this is exactly today's tag add/remove behavior.

```
Scenario: Removing an association nothing depends on deletes it outright
  Given a content object tagged with a tag that no learner has been evaluated against
  When that tag is removed from the object
  Then the association no longer exists
    And it behaves exactly as removing a tag does today

Scenario: Applying a tag that was never associated creates a new association
  Given a content object that has never been tagged with a given tag
  When that tag is applied to the object
  Then a new association is created
    And it is not archived
```

### Locked path — testable via Postman or the UI, but needs a manufactured fixture

Nothing sets `deletion_locked=True` in production yet; \#782 is what does. Exercising any of these today means creating that state directly first (Django admin, shell, or a test fixture).

```
Scenario: Removing an association that learner mastery depends on retires it instead
  Given a content object tagged with a tag that a learner has been evaluated against
  When that tag is removed from the object
  Then the association still exists but is archived
    And the learner's mastery status still resolves through it

Scenario: Re-applying a retired tag brings the original association back
  Given a content object whose association with a tag is archived
  When that same tag is applied to that object again
  Then the association is no longer archived
    And it is the same association as before, not a new one

Scenario: Re-applying a retired tag keeps its mastery history attached
  Given an archived association that a learner was evaluated against
  When that same tag is applied to that object again
  Then the learner's existing mastery status is still attached to that association

Scenario: Replacing an object's tags retires only the depended-upon ones
  Given a content object with two tags, one depended upon by learner mastery and one not
  When the object's tags are replaced with a list containing neither
  Then the depended-upon association is archived
    And the other association no longer exists
```

### Internal distinction — unit-test only, never observable via the API or UI

Whether a removed association was archived or hard-deleted is, by design, never visible in the response or the UI. Confirming which one actually happened requires inspecting the database directly, in a test.

```
Scenario: The caller cannot tell which of the two happened
  Given two content objects, one whose association is depended upon and one whose is not
  When the same tag is removed from each
  Then both requests report success in the same way
```

## Description

Removing a tag from a content object today deletes the association row outright. Once competency mastery is recorded against that association, deleting it would leave the learner's status pointing at nothing. `ObjectTag` gains an `archived` field in \#776 and a `deletion_locked` field that \#782 sets, and this ticket makes the removal path use them.

**Exactly one existing endpoint is touched, and no new one is added.** `ObjectTagView`'s `PUT` action (there is no POST, PATCH, or DELETE for `ObjectTag`) is a full replace of an object's tag set: a caller sends the complete list of tags an object should now have, and the view's `tag_object()` function reconciles what to add, keep, and remove. Adding, removing, and re-applying a tag all go through this same one action. This ticket only changes what happens inside `tag_object()`'s removal step; it adds no route and no new function.

<details>
<summary>Technical Details</summary>

This section is background and a suggested approach, not the ticket's source of truth. The User Story and Acceptance Criteria define what must be true when the work is done.

### In short

**Where the branch goes, and why there is no DELETE endpoint to use.** Tag associations are not removed one at a time. A caller sends the complete list of tags an object should now have, and `tag_object()` reconciles: it keeps what is still listed, adds what is new, and removes what is missing. The removal step inside that reconciliation is the only place an association is ever deleted, so it is the only place the branch can go.

**What the branch decides.** For each association that reconciliation would remove, if it is locked against deletion it is archived instead, and if it is not, it is deleted exactly as today. The rule is deliberately narrow: without a lock, nothing about today's behavior changes.

**Why re-applying un-archives in place rather than creating a new row.** An archived association still occupies its slot in the unique constraint on the object, taxonomy, and tag together. Creating a second row for the same three values would either violate that constraint or force it to be widened to include the archived flag, and widening it would let duplicate live associations exist. Un-archiving the existing row also keeps any competency criterion's foreign key pointing at a stable row rather than orphaning it against a superseded one.

- This is a distinct question from, and unaffected by, \#655's later "error rather than auto-unarchive" resolution about recreating a `Tag` with the same value as an archived one: that discussion concerns whether creating a *new* `Tag` row should silently resurrect an old one when the two might represent different competencies with a coincidentally shared name, an ambiguity that does not exist here, where the same `Tag` id is being reapplied to the same object id, not recreated.

**A consequence worth stating plainly.** Because the original row comes back, its mastery history comes back with it. An author who removes a competency tag and later re-adds it does not get a clean slate; the learners previously evaluated against that association are still evaluated against it. That is the intended behavior, and it is the reason the confirmation dialog in \#775 says the action cannot be undone from this screen rather than promising deletion.

### Implementation specifics

- **The branch goes in `tag_object()`** in `src/openedx_tagging/api.py`, in the step that removes associations no longer present in the submitted tag list. Do not add a new public function and do not add a DELETE endpoint.  
- **Read the lock through the query function \#777 adds**, not by reading `deletion_locked` directly, so the two delete branches in this ticket and \#780 ask the same question the same way.  
- **Resolve the removal set in bulk, then split it in two.** One `.update(archived=True)` over the locked ids and one delete over the rest, rather than a per-association branch inside a loop. `tag_object()` already handles a whole object's tags at once, and a per-row query here would be an N+1 on every content-tagging save.  
- **The un-archive step needs to see archived rows**, which \#778 filters out of the normal read paths. Use the documented opt-out that \#778 provides rather than adding a second one.  
- **Un-archive in place with `.update(archived=False)` on the existing row.** Do not delete and recreate, and do not touch the unique constraint on `(object_id, taxonomy, tag)`.  
- **Leave the lock alone when un-archiving.** A re-applied association is still depended upon by the same learner statuses, so clearing `deletion_locked` would make the next removal destroy them.  
- **The response shape does not change.** A caller must not be able to tell archiving from deletion, per the approved approach, so do not add a field reporting which happened.  
- **Check the interaction with `resync_object_tags` and `copy_tags`** in the same module. Both create or move associations and neither should resurrect an archived row unintentionally or copy the archived flag to a new object. State what each does in the PR description even if neither needs changing.  
- **Tests** in the existing `openedx_tagging` API tests, one per scenario, plus: a query-count assertion showing the branch adds a constant number of queries rather than one per association; a test that the unique constraint is unchanged; a test that a competency criterion's foreign key still points at the same row after a remove-then-re-apply cycle.  
- **Out of scope:** setting the lock (\#782), tag and taxonomy deletes (\#780), the archive event fan-out (\#781), and the confirmation dialog (\#786).

## Files to modify

| File | Nature of modification |
| :---- | :---- |
| src/openedx\_tagging/api.py | branch the removal step of `tag_object()` between archive and delete; un-archive an existing row when a tag is re-applied |
| tests/openedx\_tagging/ | one test per scenario, a query-count assertion, and a foreign-key stability test |

### Context 

- The approved implementation approach on \#655: archive only when a learner status row exists, un-archive in place on re-apply, and why the caller is not told which happened.  
- `src/openedx_tagging/api.py`, `tag_object()`, for the existing reconciliation this branch sits inside, and `resync_object_tags` and `copy_tags` for the neighbouring paths.  
- `src/openedx_tagging/models/base.py` for the unique constraint on `ObjectTag`.  
- Depends on \#776 for both fields, \#777 for the lock query, and \#778 for the documented opt-out that lets this path see archived rows. The lock itself is set by \#782.

</details>
