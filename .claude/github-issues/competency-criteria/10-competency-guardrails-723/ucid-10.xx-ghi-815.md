# [BE] Exclude archived criteria and groups when rolling up a learner's competency status

GitHub: https://github.com/openedx/openedx-core/issues/815 (#815, OPEN)
Cached: 2026-10-22

## User Story

As a learner, I want a mastery requirement that has been archived to stop counting toward the competency it sat under, in order to not be held short of a competency by a requirement nobody is being measured on any more.

## Acceptance Criteria

```
Scenario: A archived requirement no longer has to be met
  Given a criteria group requires two assignments together
    And the requirement for the first assignment has been archived
  When a learner demonstrates the requirement for the second assignment
  Then that learner's status for that group reports "demonstrated"

Scenario: A requirement a learner failed before it was archived no longer holds them back
  Given a criteria group requires two assignments together
    And a learner's status for the first requirement reports
      "attempted but not demonstrated"
    And that first requirement has since been archived
  When that learner demonstrates the requirement for the second assignment
  Then that learner's status for that group reports "demonstrated"

Scenario: A archived branch no longer has to be completed
  Given a criteria group requires two nested groups together
    And one of those two nested groups has been archived
  When a learner demonstrates every requirement of the other nested group
  Then that learner's status for the outer group reports "demonstrated"

Scenario: A competency whose requirements have all been archived reports no status
  Given every requirement beneath a competency has been archived
    And a learner who has never been evaluated against any of them
  When that learner's statuses are recomputed
  Then no status is reported for that learner at that competency

Scenario: Mastery already earned through a requirement that was later archived is kept
  Given a learner's status for a competency reports "demonstrated"
    And the requirement that earned it has since been archived
  When that learner's statuses are recomputed
  Then that learner's status for that competency still reports "demonstrated"

Scenario: A parent competency with its own requirements is still demonstrated when a sub-competency is archived
  Given a parent competency has its own requirements and two sub-competencies
    And every requirement beneath one of those sub-competencies has been archived
  When a learner meets the parent's own requirements
  Then that learner's status for the parent competency reports "demonstrated"

Scenario: A parent competency with no requirements of its own stays short when a sub-competency is archived
  Given a parent competency has two sub-competencies and no requirements of its own
    And every requirement beneath one of those sub-competencies has been archived
  When a learner demonstrates the other sub-competency
  Then that learner's status for the parent competency reports "partially attempted"

Scenario: A sub-competency whose requirements were archived is still reported for investigation
  Given a parent competency has a sub-competency whose requirements have all been archived
  When a learner's statuses are recomputed
  Then that sub-competency is reported for investigation

Scenario: A sub-competency that never had requirements is still reported for investigation
  Given a parent competency has a sub-competency with no requirements attached anywhere beneath it
  When a learner's statuses are recomputed
  Then that sub-competency is reported for investigation

Scenario: A group's already-recorded unmet status is not erased when its last live requirement is archived
  Given a criteria group requires two assignments together
    And a learner's status for that group reports "attempted but not demonstrated," earned through the first requirement
    And that learner has never attempted the second requirement
  When the first requirement is archived
    And that learner's statuses are recomputed
  Then that learner's status for that group still reports "attempted but not demonstrated"

Scenario: A previously demonstrated requirement is not enough to change a status on its own
  Given a criteria group requires two assignments together
    And a learner has demonstrated the first requirement
    And that learner's status for the second requirement reports "attempted but not demonstrated"
    And that learner's status for the group therefore reports "attempted but not demonstrated"
  When the second requirement is archived
  Then that learner's status for the group still reports "attempted but not demonstrated"
    And it is not raised to "demonstrated" until a new grade is recorded for that requirement or an operator runs the recomputation, at which point it reports "demonstrated"
```

Scenario 2 is the one to protect above the others: it's what fails, permanently, if \#816 ships before this ticket. No permission or error scenario applies: the rollup has no caller identity, and excluding a child introduces no new failure mode.

## Description

This ticket stops an archived competency requirement from counting toward a learner's status going forward, without touching anything a learner already earned or attempted. If every requirement under a sub-competency ends up archived, that sub-competency can never be earned again, which can permanently cap its parent's status unless the parent has requirements of its own.

<details>
<summary>Technical Details</summary>

This section is background and a suggested approach, not the ticket's source of truth. The User Story and Acceptance Criteria define what must be true when the work is done.

### In short

**What actually changes, and what follows for free.** This ticket excludes archived rows from the two queries \#643 uses to fetch a criteria group's children, `CompetencyCriteriaGroup` and `CompetencyCriterion`, filtered at the point they're fetched. Once an archived child is invisible to its group, \#643's existing logic already produces nearly every scenario above with no new logic: an all-archived group has nothing left to combine, and \#643 already treats that as no status rather than "demonstrated"; a status a learner already earned is never revisited, because \#643's writes already only raise a stored value, never lower or clear one; and a parent still reaches "demonstrated" through its own requirements when a sub-competency's route is permanently closed, because that's already how the either-suffices parent rule works today.

**Filter at the fetch, not after.** \#643 evaluates children in stored order and can stop as soon as one is attempted-and-not-demonstrated. Filtering after that scan has already started would let an archived child sitting first in the order settle the group before exclusion ever runs, which is exactly what scenario 2 would fail on.

**Archiving itself never calls the rollup.** This ticket changes what the rollup computes, not when it runs. Nothing in \#674 or \#675's archive path should call `roll_up_competency_statuses`; a status only changes the next time an actual trigger does, a new grade or the operator command (scenario 11).

**Not automatic: a group that is itself archived must not get its own status written**, even though nothing else stops the walk from reaching it. Until the companion ticket (\#816) ships, a leaf status can still be recorded beneath an archived branch, so this ticket skips the write at an archived group directly and continues the walk to its parent.

**The parent-competency rule itself doesn't change.** \#643 already computes a parent as demonstrated through its own requirements or through all of its sub-competencies. A fully archived sub-competency simply never produces a status, so it already fails that second route without any change to the rule.

**Not automatic: the investigation-logging query is widened.** \#643 logs a sub-competency with no root criteria group anywhere beneath it as an authoring gap. Archiving that group rather than deleting it, so the row still exists and today's check would miss it. This ticket adds `archived=False` to the same existence check, so an archived branch is flagged the same as one that was never authored, per \#643's own convention of not caring why a status can never be produced, only that it can't. Trade-off: the warning now fires on every rollup for an affected learner, not once.

### Implementation specifics

- **Both filters go on the two queries in `src/openedx_learning/applets/cbe/rollup.py`** that \#643 adds to fetch a group's children: add `archived=False` to the query fetching child `CompetencyCriteriaGroup` rows, and to the query fetching child `CompetencyCriterion` rows. Do not filter downstream of these two queries, and do not filter inside the AND/OR combination function itself.  
- **Order the AND branch's conditions so "was anything attempted at all" is tested before "are all attempted children demonstrated."** The group must resolve to no row whenever no remaining child has a status, including when no children remain after exclusion. Confirm the OR branch the same way.  
- **"No row" means no statement is issued**, never a delete of an existing `StudentCompetencyCriteriaGroupStatus` or `StudentCompetencyStatus` row and never a write of a lower value into one. \#643's conditional `UPDATE`, which fires only when the stored status is strictly below the computed one, already provides this; the change here is making sure the not-evaluated case issues nothing rather than falling through to a write.  
- **Skip the status write at a group that is itself archived, in the per-level loop of phase one**, and still collect its parent and continue the walk upward, including skipping the `StudentCompetencyStatus` write that a root group would otherwise trigger.  
- **Widen \#643's phase-two detection query** from "no root `CompetencyCriteriaGroup` row anywhere beneath this sub-competency" to "no *non-archived* root `CompetencyCriteriaGroup` row anywhere beneath this sub-competency": add `archived=False` to the existence check that currently only tests row presence via `Tag.lineage` prefix matching. Do not additionally check `CompetencyCriterion.archived` on the leaves; that would close the narrow blind spot named in Technical Details but at the cost of a leaf-level query on a path \#643 deliberately batched to one query per parent, and is left as a known limitation instead.  
- **No signature change and no migration.** `roll_up_competency_statuses(*, user_id, object_ids)` keeps its signature and its docstring contract that the caller must not be inside a transaction. Both `archived` fields are added by \#716; this ticket only reads them.  
- **Confirm the landed shape before starting.** \#643 is not merged as of this writing. Its own Files section names `rollup.py` and `statuses.py` and its Technical Details name the queries described above, but the actual function and module names must be read from the merged code rather than assumed from this ticket.  
- **Tests** in `tests/openedx_learning/applets/cbe/test_rollup_api.py`: an AND group of two children with the first archived and the second demonstrated reports "demonstrated"; the same shape where the learner's status on the archived child is already "attempted but not demonstrated" and that child is first in stored ordering, the test that fails if exclusion is applied after the short-circuit rather than before it; an outer AND group of two nested groups with one nested group archived and the other demonstrated reports "demonstrated"; an OR group whose only demonstrated child is archived does not report "demonstrated"; a root group whose every child is archived, for a learner never evaluated, writes neither a group status nor a competency status; an AND group whose every child is archived does not report "demonstrated" (the empty-collection case); a competency status already reporting "demonstrated" is left unchanged, including its timestamp, after the criterion that earned it is archived and the rollup runs again; a group status already reporting "attempted but not demonstrated" is left unchanged, not erased, when the requirement that produced it is archived and no other child of that group has ever been attempted; a group whose surviving child was already demonstrated before its sibling was archived recomputes to "demonstrated" only when the rollup is actually invoked, not as a side effect of the archive call itself, so a test asserting the group's stored status immediately after archiving, before any rollup call, must still show the old value; a group that is itself archived receives no status row while its non-archived parent is still recomputed.  
- **Tests** in `tests/openedx_learning/applets/cbe/test_tag_rollup.py`: a parent with its own requirements and two sub-competencies, one of them fully archived, reports "demonstrated" when the learner meets the parent's own requirements; a parent with no requirements of its own and two sub-competencies, one fully archived and the other demonstrated, reports "partially attempted"; a fully-archived sub-competency produces the same investigation warning as one that was never given requirements, asserted against captured logs.  
- **Out of scope:** stopping archived criteria from being evaluated when a grade is recorded, which is \#816 and must land after this ticket; archiving the tag association itself, which is \#817; any change to \#643's parent-competency combination rule.  
- **Decision record:** amend the changelog of `docs/openedx_learning/decisions/0002-competency-criteria-model.rst`, matching the prose-only style already used in that file's changelog entries (no class or method names, no code blocks), to record that archived criteria and criteria groups are excluded from status combination, that statuses already recorded against them are never lowered or removed, and that a fully-archived branch produces the same investigation warning as one that was never given requirements. ADR 0002 Decision 7 currently says archived rows are hidden from authoring and new associations but is silent on evaluation, which is the gap this closes.

## Files to modify

| File | Nature of modification |
| :---- | :---- |
| src/openedx\_learning/applets/cbe/rollup.py | Filter archived children out of both child-enumeration queries, order the empty-collection guard ahead of the all-demonstrated test, skip status writes at an archived group, and widen the phase-two detection query to also catch a fully-archived root group. |
| tests/openedx\_learning/applets/cbe/test\_rollup\_api.py | Add the phase-one exclusion, stored-ordering, empty-collection, archived-group, already-earned-status, and already-recorded-unmet-status cases. |
| tests/openedx\_learning/applets/cbe/test\_tag\_rollup.py | Add the two parent-route cases and the investigation-logging case covering both an archived branch and a never-authored one. |
| docs/openedx\_learning/decisions/0002-competency-criteria-model.rst | Changelog amendment recording that archived definition rows are excluded from status combination, that recorded statuses are never lowered or removed, and that a fully-archived branch produces the same investigation warning as a never-authored one. |

- Context \#643 is the rollup this ticket extends, not amended. It computes a criteria group from its children with AND or OR in stored order with short-circuit evaluation, computes a competency from its root group, computes a parent competency as the OR of its own requirements and all of its direct sub-competencies, and logs a sub-competency with no root criteria group anywhere beneath it for investigation.  
- \#716 adds the `archived` boolean to both `CompetencyCriteriaGroup` and `CompetencyCriterion`. This ticket only reads those fields and adds no migration of its own.  
- \#674 and \#675 are the archive endpoints that set `archived`, including \#675's cascade that archives every criterion in an archived subtree and \#674's upward cascade that archives a group once its last non-archived child is archived.  
- This ticket must ship before \#816 ("Exclude archived competency criteria and criteria groups from evaluation when a grade is recorded"). If that ticket shipped first, a learner who failed a criterion before it was archived would be permanently stuck at "attempted but not demonstrated" on that group: the criterion could never be re-evaluated to unstick them, and the group above would still require it.  
- `docs/openedx_learning/decisions/0002-competency-criteria-model.rst`: Decision 2 for `logic_operator`, `ordering`, and the worked short-circuit example; Decision 6 for the three learner status tables and the two values allowed at the competency level; Decision 7 for the archive-instead-of-delete rule.  
- `docs/openedx_learning/decisions/0004-competency-mastery-concurrency.rst`: why every status write is raise-only, and why the rollup runs outside a transaction.  
- `src/openedx_tagging/models/base.py`: `Tag.parent`, `Tag.depth`, `Tag.lineage`, and `TAXONOMY_MAX_DEPTH`, which bound and terminate the parent-competency walk.

</details>
