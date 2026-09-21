# [BE] Exclude archived competency criteria and criteria groups from evaluation when a grade is recorded

GitHub: https://github.com/openedx/openedx-core/issues/816 (#816, OPEN)
Cached: 2026-09-21

## User Story

As a course author, I want a competency criterion I have archived to be skipped when new grades are recorded, in order to stop a mastery rule I archived from continuing to record new learner mastery.

## Acceptance Criteria

```
Scenario: An archived criterion records no new mastery
  Given a graded assignment whose only competency criterion has been archived
    And a learner with no recorded status for that criterion
  When a grade for that assignment is recorded for that learner
  Then the grade is recorded
    And no status is recorded for that learner against that criterion
    And the caller is told that nothing changed

Scenario: A status recorded before archiving is left alone
  Given a learner whose status for a criterion was recorded while that criterion was still active
  When a later grade for the same content is recorded for that learner
  Then that learner's status for that criterion is unchanged, including when it was recorded

Scenario: An active criterion sharing a tagged assignment with an archived one is still evaluated
  Given one assignment is tagged with a competency once
    And two criteria in different groups both use that single tagged association
    And one of those two criteria has been archived
  When a grade for that assignment is recorded for a learner
  Then the active criterion reports the status its own threshold implies
    And no status is recorded for that learner against the archived criterion

Scenario: A criterion that is archived because its group was archived is skipped the same way
  Given a criterion that was archived because the group above it was archived, rather than on its own
  When a grade for the content it applies to is recorded for a learner
  Then no status is recorded for that learner against that criterion
```

## Description

Once a learner has earned mastery through a competency criterion, deleting that criterion archives it rather than removing it. Archiving hides the criterion from authoring, and this ticket makes grade recording skip it too, so an archived rule cannot go on awarding new mastery.

<details>
<summary>Technical Details</summary>

This section is background and a suggested approach, not the ticket's source of truth. The User Story and Acceptance Criteria define what must be true when the work is done.

### In short

**Where the change goes.** When a grade is recorded, \#699 resolves which competency criteria apply to the graded content with a single query: it joins criteria to their tag-object associations on the graded object's id, and keeps only those whose tag belongs to a competency taxonomy. This ticket adds one condition to that one query. Nothing else in the grade path changes, and no status row is read, rewritten, or removed.

**The one archived flag the query reads, and why it alone is enough.** The added condition drops a criterion whose own `archived` flag is set. That covers a criterion retired directly, and, because \#675's archive cascade sets `archived=True` on every criterion in an archived subtree as part of archiving its group, it also covers a criterion retired as part of retiring the group above it. This ticket does not additionally join to the parent `CompetencyCriteriaGroup` to check its flag too: \#675's cascade archives a whole subtree, group and every criterion beneath it, inside one `transaction.atomic()` block, so there is no committed state where a group is archived but a criterion beneath it isn't. A crash partway through that cascade rolls the whole transaction back rather than leaving a mismatched pair behind. Reading the criterion's own flag is therefore sufficient, and a second join against the group buys no additional correctness, only cost.

**What deliberately does not change.** Mastery a learner already earned through a criterion is never revisited. Archiving stops a criterion being applied to grades recorded from that point on; the existing status row, including its last-changed time, is left exactly as it is. There is no backfill and no cleanup pass over existing statuses.

**Why an assignment shared by an active rule and an archived one still works correctly.** The exclusion is evaluated per criterion row, not per tag association. Two criteria in different groups can point at the same tag-object association, and archiving one of them leaves the other's row untouched, so the active one is still resolved and still reports what its own threshold implies. This is also why the companion ticket that archives tag associations (\#817) cannot cover this case on its own: that ticket, by design, leaves an association active whenever any non-archived criterion still uses it.

### Implementation specifics

- **The condition goes on the criteria-resolution query** inside `record_graded_object_statuses` in `src/openedx_learning/applets/cbe/api.py`: add `archived=False` on `CompetencyCriterion`. No join to the parent `CompetencyCriteriaGroup`, and no ancestor walk.  
- **No signature change.** `record_graded_object_statuses(*, user_id, scores)` keeps its signature, its requirement that the caller is inside the grade's transaction, and its return value, which is the count of leaf status rows created or raised. Content whose criteria are all archived returns zero, which is how the caller is told nothing changed, and how the downstream rollup task knows not to enqueue any further work.  
- **No migration and no new model field.** The `archived` field is added by \#716.  
- **Tests** in `tests/openedx_learning/applets/cbe/test_leaf_status_api.py`: an archived criterion with no prior status for the learner writes no row, returns zero, and still records the grade; a status recorded while the criterion was still active is unchanged, including its timestamp, by a later grade for the same content; one tag association shared by two criteria in different groups, one archived, writes exactly one row, for the active criterion at its own threshold; a criterion archived by its group's cascade (both group and criterion end up `archived=True`) is skipped the same as one archived directly, confirming the query needs only the criterion's own flag; an active criterion under a non-archived group is still evaluated.  
- **Confirm the landed shape before starting.** \#699 is not merged as of this writing. Its Technical Details name the resolution query and the `record_graded_object_statuses` signature, but the actual field names and query form must be read from the merged code.  
- **Out of scope:** excluding archived criteria and groups from the rollup above the leaf, which is \#815 and must land before this ticket; archiving the tag association when the last active rule using it is archived, which is \#817; any change to a status already recorded.  
- **No decision-record change is needed for this ticket on its own.** \#815 amends ADR 0002's changelog to state that archived rows are excluded from evaluation and combination generally, which covers this ticket too.

Files to create and modify **Modified files**

| File | Nature of modification |
| :---- | :---- |
| src/openedx\_learning/applets/cbe/api.py | Add the criterion-archived condition to the criteria-resolution query in `record_graded_object_statuses`. |
| tests/openedx\_learning/applets/cbe/test\_leaf\_status\_api.py | Add the archived-exclusion cases, including the shared-association case and the group-cascade case. |

- Context \#699 is the grade-evaluation query this ticket extends, not amended. It resolves criteria by joining to tag associations on the graded object's id, filters to tags in a competency taxonomy, and excludes a criterion whose tag association is archived. It does not check `CompetencyCriterion.archived` directly.  
- \#716 adds the `archived` boolean to `CompetencyCriterion` (and to `CompetencyCriteriaGroup`, which this ticket doesn't read). This ticket only reads the criterion's own field.  
- \#675's cascade archives an entire subtree, a group and every criterion beneath it, inside one transaction, and sets `archived=True` on every criterion in that subtree as part of the same write. That's what makes a criterion archived via its group behave the same as one archived directly, and why this ticket doesn't need to check the group's flag too.  
- \#815 (excluding archived criteria and groups from the rollup) must ship before this ticket. If this ticket shipped first, a learner who failed a criterion before it was retired would be permanently stuck at "attempted but not demonstrated" on that group: this ticket stops the criterion being re-evaluated, so nothing could ever unstick them, while the group above still required it.  
- `docs/openedx_learning/decisions/0002-competency-criteria-model.rst`: Decision 4 for the criterion's fields and its tag-association reference, Decision 7 for the archive-instead-of-delete rule, and the worked example showing one tag association shared across several criteria.  
- `docs/openedx_learning/decisions/0004-competency-mastery-concurrency.rst`: Decision 1 for why this function runs inside the grade's transaction, and Decision 4 for why an automatic write may raise a status but never lower it.

</details>
