# [BE] Lock tagging records against deletion when a learner competency status is written

GitHub: https://github.com/openedx/openedx-core/issues/782 (#782, OPEN)
Cached: 2026-09-21

## User Story

As a learner, I want the competency framework my earned mastery is recorded against to survive someone tidying up tags or taxonomies, so I keep the competencies I have demonstrated.

## Acceptance Criteria

```
Scenario: Recording a learner's mastery locks the tag association it was evaluated through
  Given a learner has no recorded mastery for a competency
  When a mastery status is recorded for that learner against that competency
  Then the tag association the criterion was evaluated through is locked against deletion

Scenario: The locked association protects the tag and taxonomy above it too
  Given the tag association from the previous scenario is now locked
  When someone asks whether the tag, or its taxonomy, is safe to delete
  Then both report that they are depended upon, without either one carrying a lock of its own

Scenario: Deleting a protected tag archives it instead of removing it
  Given a learner has recorded mastery against a competency
  When an administrator deletes that competency
  Then the competency is archived rather than removed
  And the learner's recorded mastery still resolves through it

Scenario: Recording mastery for a second learner does not fail on an already-locked record
  Given a tag association already locked against deletion
  When a mastery status is recorded for another learner against the same competency
  Then the status is recorded
  And the association remains locked

Scenario: Content with no competency criteria locks nothing
  Given a learner is graded on content with no competency criteria associated with it
  When the grade is recorded
  Then no tagging record is locked against deletion

Scenario: A failed status write locks nothing
  Given a mastery status write that does not complete
  When the operation ends
  Then no tagging record is left locked against deletion
```

## Description

`openedx_tagging` gains a way to mark a tag association as depended upon in \#777, but nothing calls it, so no record is ever protected and every delete still removes rows outright. This ticket marks the tag association a criterion was evaluated through, so it can't be deleted, preserving the student competency status data recorded against it. Locking the association is also what protects the tag and taxonomy above it: \#780's delete branch decides whether a tag or a taxonomy is safe to remove by asking whether any association beneath it is locked, so this one write is what the whole chain depends on.

The direction matters. `openedx_tagging` is a standalone library that must not know competency-based education exists, so the feature that creates the dependency is responsible for declaring it. Competency mastery is the only thing that creates a dependency on tagging data today.

<details>
<summary>Technical Details</summary>

This section is background and a suggested approach, not the ticket's source of truth. The User Story and Acceptance Criteria define what must be true when the work is done.

### In short

**When the lock is set.** At the moment a learner competency status row is written. That row is the dependency: it is what would be orphaned if the tag association behind it were deleted. Setting the lock at write time rather than at delete time is what lets the tagging app answer the question without querying anything competency-related.

**Only the association is locked; the tag and taxonomy are protected without a lock of their own.** `deletion_locked` exists only on `ObjectTag` — \#777 deliberately has no equivalent field or setter for `Tag` or `Taxonomy`, since neither has anything to set. A tag or a taxonomy is judged safe to delete by asking, through \#777's reader functions, whether any association beneath it is locked. So locking the one association a criterion points at is enough: it is what the tag and taxonomy above it are actually asked about.

**Locking rides along with the status write.** The lock must not be able to exist without the status row that justifies it, and more importantly, the status row must not exist without the lock, since that would leave a window in which the record it depends on could be deleted. So the lock is set in the same transaction as the status write.

**Locking is cheap and idempotent, so it does not need to be conditional.** The lock function is bulk update and setting an already-set flag is a no-op, so there is no need to check first whether an association is already locked. Do not add a read to avoid a write here; the read costs as much as the write it saves.

### Implementation specifics

- **Call** `lock_object_tag_for_deletion()`, \#777's only setter,  
-  from the competency applet, in the same transaction as the learner status write. The status write is the function \#699 adds; hook the lock there so every caller of it gets the behavior rather than each call site remembering.  
- **Lock the tag association each criterion was evaluated through.** Do not call anything for the tag or the taxonomy directly — there is nothing to call; \#777 provides no setter for either, by design (see Technical Details).  
- **Batch across the whole call. \#699 evaluates every criterion attached to a graded object in one call, so collect the distinct association ids across all of them and make one bulk call, not one call per criterion.**  
-   
- **Do not lock when nothing is written.** \#699 returns without writing when the graded content has no criteria, which is the overwhelmingly common case; that path must issue no lock query at all.  
- **Set the lock inside the existing transaction rather than opening one.** \#699 runs inside the caller's grade transaction by design, so opening another here would break the guarantee that the grade, the status, and the lock commit together.  
- **Import only from the tagging app's public API**, `openedx_tagging.api`, never from its models or internals. Confirm with `lint-imports`.  
- **Do not add an unlock anywhere.** Learner mastery statuses are not deleted, so a locked record stays locked.  
- **Tests** in the competency applet tests: a status write locks the association; a second learner's status write against an already-locked association succeeds and leaves it locked; a graded object with no criteria issues no lock query; a query-count assertion showing the lock is one bulk call regardless of how many criteria were evaluated; a rolled-back status write leaves nothing locked; an end-to-end test that deleting a locked tag archives it rather than removing it, and that its taxonomy is likewise protected without either one carrying its own lock.  
- **Out of scope:** the lock API itself (\#777), the delete branches that read the lock (\#779, \#780), and any change to how or when a learner status is written.

## Files to modify 

| File | Nature of modification |
| :---- | :---- |
| src/openedx\_learning/applets/cbe/api.py | lock the tag association in the same transaction as the learner status write |
| tests/openedx\_learning/applets/cbe/ | lock-on-write, idempotency, no-criteria, query-count, rollback, and end-to-end delete tests |

## Context

- The approved implementation approach on \#655, for the push-based lock design and why the depending feature sets it.  
- \#777 provides `lock_object_tag_for_deletion()` in `src/openedx_tagging/api.py`, the only setter this ticket calls. It also provides `get_tags_locked_for_deletion()` and `is_taxonomy_locked_for_deletion()`, the reader functions \#780's delete branch uses to derive whether a tag or taxonomy is protected — this ticket doesn't call those directly, but they're why locking the association alone is sufficient.  
- \#699 provides the learner status write this hooks into, and \#642 provides the status tables.  
- \#780 depends on the association being locked here to correctly decide the taxonomy case.  
- `.importlinter` for the layering that keeps `openedx_tagging` free of competency concerns.

</details>
