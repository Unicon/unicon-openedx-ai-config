# [BE] Recompute learner competency statuses on operator command

GitHub: https://github.com/openedx/openedx-core/issues/774 (#774, OPEN)
Cached: 2026-09-21

## User Story

As an operator, I want a Django Management Command that can force a recomputation of learners' competency statuses over a selection I choose, in order to correct statuses left behind by a background job that never finished, without waiting for those learners to be graded again.

## Acceptance Criteria

This is a Django management command run by an operator, with no Open edX instance UI or Django Admin to click through. The scenarios below can be verified by automated unit tests plus an operator running the command (including with `--dry-run`), not by manual QA testing against an Open edX instance.

```
Scenario: A status left behind by a failed background job is corrected
  Given a learner's competency status is lower than their criterion statuses imply
  When the recomputation is run over a selection that includes that learner
  Then that learner's competency status reports the value their criterion
    statuses imply

Scenario: A status that is higher than the learner's results justify is left alone
  Given a learner's competency status is higher than their criterion statuses imply
  When the recomputation is run over a selection that includes that learner
  Then that learner's status is unchanged
    And the operator is told that nothing changed for that learner

Scenario: Running the recomputation twice changes nothing the second time
  Given the recomputation has already been run over a selection
  When it is run again over the same selection
  Then no learner's status changes
    And the operator is told that nothing changed

Scenario: The operator is told what was examined and what was changed
  When the recomputation completes over a selection
  Then the operator is told how many learners were examined, how many statuses were
    raised, how many were unchanged, and which learners could not be processed

Scenario: A selection that matches nothing completes cleanly
  Given the selection matches no learners
  When the recomputation is run
  Then it completes successfully
    And the operator is told that nothing was examined

Scenario: Running with no selection at all is refused
  When the recomputation is run without specifying what to run it over
  Then it stops with an explanation
    And no learner's status is changed

Scenario: A selection that cannot be interpreted changes nothing
  When the recomputation is run with a selection that cannot be interpreted
  Then it stops with an explanation
    And no learner's status is changed

Scenario: A trial run reports what it would do without changing anything
  Given several learners' statuses are lower than their criterion statuses imply
  When the recomputation is run as a trial
  Then the operator is told the same counts a real run would report
    And no learner's status is changed

Scenario: One learner's failure does not abandon the rest
  Given the selection includes several learners
    And the recomputation for one of them cannot complete
  When the run finishes
  Then the remaining learners' statuses are still brought up to date
    And the learner that could not be processed is reported

Scenario: Grading during a recomputation is not blocked or set back
  Given the recomputation is running over a selection that includes a learner
  When a grade is recorded for that learner during the run
  Then the grade is recorded without waiting
    And that learner's statuses afterwards report values no lower than either the
      recomputation or the grade alone would have produced
```

## Description

A learner's competency statuses above the criterion level are written by a background job that Celery retries on failure, and retries only cover the failures the job itself sees. A worker can die partway up a competency tree, a queued job can be lost before it ever runs, and a defect can be fixed after it has already left statuses behind. Today the only way to correct any of that is to grade the learner's work again.

This ticket gives an operator a command that re-runs the same recomputation over a chosen selection. It applies the same rule as the background job, which is that a status may be raised but never lowered, so it repairs any status that is lower than the learner's stored criterion results justify. It cannot repair a status that is too high: a run against an over-credited learner completes, reports success, and changes nothing. Operators need to know that before they reach for the tool rather than after.

Competency criteria edits are deliberately not applied to learners retroactively. Running this command is the one thing that applies a corrected criteria tree to results a learner already has, and it does so in the upward direction only.

<details>
<summary>Technical Details</summary>

This section is background and a suggested approach, not the ticket's source of truth. The User Story and Acceptance Criteria define what must be true when the work is done.

### In short

**What it does.** It re-runs exactly the recomputation the background job runs, over a selection the operator gives it, with the same rule that a status may be raised but never lowered. So it repairs any status lower than the learner's stored criterion results justify, which is what a half-finished or lost recomputation leaves behind.

**Why there is no locking here.** Raising a status is already safe against a grade change happening at the same moment, because each write takes effect only when the stored value is lower than the computed one and the database decides that in a single statement. Nothing here needs a row lock or a transaction. The root-group lock that the concurrency decision record defines belongs solely to the staff-correction path, and an implementer who assumes it applies here would make recovery contend with live grading for no gain.

**What it cannot recover, and why that is worth stating in the ticket.** Any status that is too high. That includes a rollup defect that computed too high, content tagged to a criterion that should not have counted, and a criteria tree restructured so that a stored "demonstrated" is no longer justified. The concurrency decision record names content tagging errors and rollup bugs as reasons this mechanism exists, and as scoped this command addresses only the half of each that errs low. There is one acceptance criterion whose entire purpose is to document that limit so it is discovered in review rather than during an incident.

**What it cannot recover at all, by design.** It recomputes the criteria-group and competency levels from the criterion statuses already stored. It cannot recompute those criterion statuses, because this library has no access to grades, and it does not need to: a failure to record one rolled the grade back with it, so no recorded grade is missing its criterion status.

**Why a management command rather than a Django admin action.** A recompute across a range of learners is an operations task. An admin action is bounded by what an operator can select on a changelist page and by the request timeout, and the LMS picks up management commands shipped in this library automatically, so this needs no change in `openedx-platform` at all.

### Implementation specifics

- **Command** at `src/openedx_learning/management/commands/recompute_competency_statuses.py`, following the style of `src/openedx_content/management/commands/lp_dump.py`. This is the first management command in this package, so `management/` and `management/commands/` and their `__init__.py` files are new.  
- **Arguments:** `--user-id` (repeatable), `--tag-id` (repeatable), `--modified-since` (ISO 8601, filtering on the criterion status `modified` column), `--batch-size` (default 500), and `--dry-run`. At least one of the three selectors is required, so an operator cannot recompute the whole instance by accident.  
- **It calls `roll_up_competency_statuses(user_id=..., object_ids=[...])` from \#643 and adds no recomputation logic of its own.** Turn the selection into that call's arguments with an internal helper in the applet, resolving each selected learner's affected object ids by joining `StudentCompetencyCriteriaStatus` through `CompetencyCriteria` to `ObjectTag.object_id`. Keep that helper out of every `__all__`: the command lives inside `openedx-core` and may import applet internals directly, so this ticket adds nothing to the public API.  
- **Do not add `select_for_update()` and do not add `transaction.atomic()`.** The monotone write is already concurrency-safe, and a transaction around the walk would reintroduce the problem the concurrency decision record's Decision 3 exists to avoid.  
- **Batch and commit per learner**, so an interrupted run leaves no learner half-processed and one learner's failure does not abort the rest. Log and continue on a per-learner failure and include the failures in the summary.  
- **Report learners examined, statuses raised, statuses unchanged, and per-learner failures.** "Unchanged" must include the too-high case, so an operator can see that the tool ran and declined to act rather than inferring that nothing was wrong.  
- **Implement `--dry-run` by computing and comparing without issuing the update**, not by rolling a transaction back, because the underlying write is a conditional update.  
- **Tests** in `tests/openedx_learning/applets/cbe/test_recompute_command.py`: a group status left too low by an interrupted cascade is raised, and its ancestors with it; a status that is already correct is untouched and its `modified` timestamp does not move; a status that is too high is left untouched and reported as unchanged, which is the test that documents the tool's limit; `--dry-run` reports the same counts and writes nothing; running with no selector exits with an error; a competency-level status never receives `AttemptedNotDemonstrated`; a learner whose recomputation raises does not abort the remaining learners.  
- **Amend the concurrency decision record's Decision 5** in this ticket's PR: the recovery mechanism re-runs the monotone rollup, so it repairs statuses that are too low and cannot repair one that is too high; correcting an over-credited learner requires the staff correction path in Decision 6; and it covers criteria-group and competency statuses only, never criterion statuses.  
- **Out of scope:** the staff-correction path and its root-group lock; any recomputation of criterion statuses from grades; and any lowering of a status. Correcting an over-credited learner (the staff-correction path in Decision 6\) has no ticket and is not planned as one: it requires a root-group lock the way this command deliberately does not, and that lock is not worth designing for a case this ticket's own Description already frames as an extreme edge case. Until or unless that changes, correcting an over-credited learner is a manual database operation, not a supported tool.

Files to create and modify **New files**

| File | Purpose |
| :---- | :---- |
| src/openedx\_learning/management/**init**.py | package marker |
| src/openedx\_learning/management/commands/**init**.py | package marker |
| src/openedx\_learning/management/commands/recompute\_competency\_statuses.py | selectors, batching, per-learner iteration, reporting |
| tests/openedx\_learning/applets/cbe/test\_recompute\_command.py | raise, no-lower, dry-run, selector-required, and per-learner failure tests |

**Modified files**

| File | Nature of modification |
| :---- | :---- |
| src/openedx\_learning/applets/cbe/rollup.py | add the internal helper resolving a learner selection to affected object ids |
| docs/openedx\_learning/decisions/0004-competency-mastery-concurrency.rst | amend Decision 5: raise-only, what it can and cannot repair, groups and competencies only |

- Context `docs/openedx_learning/decisions/0004-competency-mastery-concurrency.rst`, Decision 5 for the requirement, Decision 4 for why raising is safe without a lock, Decision 6 for the correction path this tool deliberately is not, and Rejected Alternative 8 for the crash-mid-cascade case it exists to catch.  
- `docs/openedx_learning/decisions/0003-competency-criteria-versioning.rst`, Decision 4, for why authoring changes are not retroactive and therefore why running this command has that effect in the upward direction.  
- Management command prior art: `src/openedx_content/management/commands/lp_dump.py` and `lp_load.py`.  
- Depends on \#700 for the status tables and \#643 for the recomputation it calls. Documented by \#729.

</details>
