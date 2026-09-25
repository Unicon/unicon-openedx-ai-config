# [BE] Record learner’s criterion status for grade

GitHub: https://github.com/openedx/openedx-core/issues/701 (#701, OPEN)
Cached: 2026-09-25

*Companion to \#699, which defines the contract this ticket calls and holds the shared background for the competency evaluation itself.*

## User Story

As a learner, I want my competency mastery updated by the very operation that records my grade, in order to never be shown a grade that has been credited without the mastery it earned.

## Acceptance Criteria

```
Scenario: A graded assignment updates the learner's competency criteria
  Given an assignment is associated with competency criteria
  When a learner's grade for that assignment is recorded
  Then that learner's status for those criteria is updated as part of the same save

Scenario: Grades saved together in one operation each update their criteria
  Given several of a learner's assignments are associated with competency criteria
  When that learner's grades for those assignments are saved in one operation
  Then the learner's status for the criteria of each of those assignments is
    updated as part of that same operation

Scenario: Grading content with no competency criteria behaves exactly as it does today
  Given the graded assignment has no competency criteria associated with it
  When a learner's grade is recorded
  Then the grade is recorded exactly as it is recorded today
    And no competency status is created or changed

Scenario: A competency update that cannot be saved takes the grade with it
  Given an assignment is associated with competency criteria
  When a learner's grade is recorded and the competency status cannot be saved
  Then neither the grade nor the competency status is saved
    And the caller is told the grade was not recorded

Scenario: One graded submission updates every subsection it contributes to
  Given a learner's submission counts towards more than one subsection
    And those subsections are associated with competency criteria
  When that submission is graded
  Then the learner's status for the criteria of every affected subsection
    is updated as part of recording those subsection grades

Scenario: A staff correction to a learner's score updates their competency status
  Given an assignment is associated with a competency criterion requiring at least 75%
    And a learner scored below that threshold
  When staff correct that learner's score for the assignment to 80%
  Then that learner's status for that criterion reports "demonstrated"

Scenario: Withdrawing a staff correction does not take away what it demonstrated
  Given staff corrected a learner's score so that the learner demonstrated a criterion
  When staff withdraw that correction and the learner's original score is restored
  Then that learner's status for that criterion still reports "demonstrated"

Scenario: Content with nothing available to earn produces no status
  Given an assignment associated with a competency criterion has no points
    available to earn
  When a learner's grade for that assignment is recorded
  Then the grade is recorded
    And no competency status is created for that assignment's criterion

Scenario: A grade that is not saved triggers no recomputation above the criterion
  Given a learner's status at a criterion would change
  When the recording of the grade does not complete
  Then no recomputation of that learner's higher levels is carried out

Scenario: Grades already recorded are not revisited
  Given a learner's grades were recorded before any competency criteria
    were associated with that content
  When competency criteria are later associated with that content
  Then those already-recorded grades do not by themselves create any
    competency status for that learner

Scenario: An operator can decline competency tracking entirely
  Given competency mastery tracking is switched off for the deployment
  When a learner's grade is recorded for content associated with competency criteria
  Then the grade is recorded exactly as it is recorded today
    And no competency status is created or changed
```

## Description

Recording a grade in `openedx-platform` today saves the grade alone, and that save is not tied to anything else. This ticket makes the competency status update part of the same save, using the function \#699 provides, at both paths that persist an assignment grade a competency criterion can attach to: the single assignment grade write and the operation that saves many of a learner's assignment grades at once. Computing the levels above the criterion is \#643.

<details>
<summary>Technical Details</summary>

This section is background and a suggested approach, not the ticket's source of truth. The User Story and Acceptance Criteria define what must be true when the work is done.

### In short

**Where the calls go, and why not one level lower.** There are two places the LMS persists an assignment grade a competency criterion can attach to: the single assignment path and the bulk path. Both are hooked on `CreateSubsectionGrade` in `lms/djangoapps/grades/subsection_grade.py`, not on the model methods beneath them. The reason is specific and load-bearing: the columns on the persisted subsection grade row hold only the totals computed from problem scores, and a staff grade override is applied afterwards, in memory, by the caller. Code reading those columns would silently ignore every override, so a learner whose instructor raised their grade to a pass would never be credited with the competency.

**How the grade and the leaf status come to share a transaction.** None of those methods is transactional today, so each gains a narrow `transaction.atomic()` block around the grade row write and the new call, and nothing else. The competency call must not be wrapped in `try`/`except`: the point of the shared transaction is that the grade does not commit without its leaf status, so swallowing the error would quietly give up the guarantee. A criterion whose stored rule is malformed is already handled inside \#699 by skipping it and logging, so the only errors that reach here are genuine storage failures. The safety valve for a deployment that does not want the coupling at all is the setting below, not a caught exception.

**One piece of grades surgery this forces.** The new transaction on the single assignment path would otherwise enclose the grade-calculated event that `PersistentSubsectionGrade.update_or_create_grade()` emits. That must not happen: if the leaf write raises, the transaction rolls back but the event has already announced a grade that does not exist. `CreateSubsectionGrade.update_or_create_model()` is the sole caller of that method, so the emission can simply move up to the end of the caller, after the atomic block, with no change in behavior for anyone else and no fallout in existing tests.

**How the follow-up work is queued so it cannot run too early.** Everything above the leaf is recomputed by a new Celery task in `lms/djangoapps/grades/tasks.py`, which is a thin wrapper around one `openedx-core` function. It is enqueued with `transaction.on_commit` from inside the atomic block, so it is queued only once the grade has actually committed and can never read a grade that is still in flight. The enqueue is skipped when the `openedx-core` call reports that no leaf status changed, which is the common case, so re-persisting unchanged grades queues nothing. The bulk path enqueues one task for the whole batch carrying every changed assignment, not one per assignment. Because the recompute only ever raises a status and never lowers one, Celery redelivering or reordering the task is harmless and it can be retried freely.

**The bulk path does not apply staff grade overrides, and that is deliberately left alone.** It never has, and changing it would change what grades that path reports, which is outside this ticket. So the statuses written there come from exactly the numbers the batch persists, which keeps the criterion status and the grade row it commits with in agreement. Little is lost by that: the bulk path only handles grades that have never been stored before, so an override rarely exists yet; where one does, setting it triggers a recalculation through the single path, which is override-correct; and because a status can only ever be raised, the bulk path's value can never displace a higher one the single path already got right.

**Turning it off.** The new query on the assignment grade write path runs on one of the busiest writes in the LMS. A deployment not using competency-based education should not pay for it, and a deployment that hits a problem needs a way to stop competency code from blocking grade writes without a code deploy. Both call sites are gated on a single Django setting, defaulting to off.

### Implementation specifics

- **Two call sites, one module.** `CreateSubsectionGrade.update_or_create_model()` and `CreateSubsectionGrade.bulk_create_models()` in `lms/djangoapps/grades/subsection_grade.py`. Do not hook `PersistentSubsectionGrade.update_or_create_grade()` or `PersistentSubsectionGrade.bulk_create_grades()`.  
- **Hook coverage is complete for the single assignment path.** `update_or_create_model()` has four callers: `SubsectionGradeFactory.update()` and `.create()`, `lms/djangoapps/grades/api.py`, and `lms/djangoapps/grades/rest_api/v1/gradebook_views.py`. All four are paths that should record competency status, including the gradebook write, which is how staff-entered grades reach the database.  
- **The assignment fraction must be override-adjusted, and there is no accessor for it.** `PersistentSubsectionGrade` exposes no `percent_graded` property, so compute the fraction as `graded_total.earned / graded_total.possible` from the `CreateSubsectionGrade` instance's `graded_total`, and on the single path only after the `if hasattr(model, 'override')` block has recomputed it via `_aggregated_score_from_model()`. Do not read `earned_graded` and `possible_graded` off the persisted row: those columns are written from problem-score totals before any override is applied, and `_aggregated_score_from_model()` substitutes `override.earned_graded_override` and `override.possible_graded_override` only in memory. An implementer who goes by the column names will get this wrong, and the staff-correction scenario is the test that catches it.  
- **On the bulk path, use the totals it persists, un-overridden.** Do not call `PersistentSubsectionGradeOverride.get_override` there, and do not wire up the `PersistentSubsectionGradeOverride.prefetch(user_id, course_key)` call that `bulk_create_grades()` already makes and never uses. That call is a leftover, not a hook.  
- **Skip any assignment whose graded possible is zero.** There are no graded points to demonstrate anything against, so omit the object rather than passing `0.0` and recording a failed status. Same rule as omitting an unattempted object, which on the assignment paths is a `first_attempted is None` check.  
- **Move the grade-calculated event emission**, do not defer it, from `PersistentSubsectionGrade.update_or_create_grade()` to the end of `CreateSubsectionGrade.update_or_create_model()`, after the atomic block. `update_or_create_model()` is that method's only caller, so this is behavior preserving and needs no `transaction.on_commit()` wrapper. Check `update_or_create_model()` for early returns so the emission runs on exactly the paths that reached it before, and no others. The bulk path emits no such event, so nothing has to move there.  
- **The `openedx-core` contract** is `record_graded_object_statuses(user_id=..., scores=[GradedObjectScore(object_id=..., fraction=...)])` returning a count, per \#699, and `roll_up_competency_statuses(user_id=..., object_ids=[...])`, per \#643. Import both from `openedx_learning.api`, never from the applet modules beneath it. The bulk path makes a single call carrying a list of scores; the learner is the one `student` that method receives, so no grouping by user is needed.  
- **`object_id` is the string form of the usage key** for an assignment, matching how the tagging app stores an object tag's target.  
- **The new Celery task** goes in `lms/djangoapps/grades/tasks.py` next to `recalculate_subsection_grade_v3`, following its shape: `@shared_task(bind=True, base=LoggedPersistOnFailureTask, time_limit=SUBSECTION_GRADE_TIMEOUT_SECONDS, max_retries=2, default_retry_delay=RETRY_DELAY_SECONDS)` then `@set_code_owner_attribute`. `autoretry_for` is used nowhere in that module, so `bind=True` is required and the retry is raised by hand in the task body as `if not isinstance(exc, KNOWN_RETRY_ERRORS): raise` then `raise self.retry(kwargs=kwargs, exc=exc)`. Declare the task to take keyword arguments and enqueue it with `apply_async(kwargs={"user_id": ..., "object_ids": [...]})` so the manual retry can pass `kwargs` through unchanged. Reuse `SUBSECTION_GRADE_TIMEOUT_SECONDS` rather than adding a constant; a rollup walk is far cheaper than a subsection regrade.  
- **The task must not wrap its call in a transaction**, for the reason given in \#643.  
- **`bulk_create_grades()` is insert-only.** It calls `bulk_create` with no `update_conflicts`, so a re-run against already-persisted rows raises on the unique constraint rather than updating. Two consequences: such a failure is not attributable to competency code, and the new transaction now rolls the whole batch back where a partial batch could previously commit. That second one is a behavior change on a path unrelated to competencies and belongs in the PR description.  
- **Feature gate:** a new top-level Django setting `ENABLE_COMPETENCY_MASTERY_TRACKING`, defaulting to `False`, guarding both call sites. This follows `ENABLE_COURSE_ASSESSMENT_GRADE_CHANGE_SIGNAL`, which already gates the neighboring signal in `lms/djangoapps/grades/subsection_grade_factory.py`. Declare it in `lms/envs/common.py` with the same `.. toggle_name:` annotation block the surrounding settings carry, including `toggle_implementation: DjangoSetting`, `toggle_default`, `toggle_description`, `toggle_use_cases`, and `toggle_creation_date`; the annotation is what the toggle documentation build reads, so a bare assignment is incomplete.  
- **Dependency and version pin:** this ticket needs an `openedx-core` release containing \#699 and \#643, and a bump of the `openedx-core` pin in `requirements/edx/base.txt`.  
- **Test gotcha:** `transaction.on_commit` callbacks never fire under `django.test.TestCase`, which wraps each test in a transaction that is rolled back. Use `captureOnCommitCallbacks` or `TransactionTestCase` in the enqueue tests, or they will pass while asserting nothing.  
- **Tests:** a learner whose grade is below the criterion threshold but whose override raises it above is credited, which is the test that fails if the fraction is read from the persisted columns; the leaf write is inside the same transaction as the grade, verified by making the `openedx-core` call raise and asserting no `PersistentSubsectionGrade` row exists; the rollup task is enqueued exactly once after commit when a leaf changed and not at all when none did; the bulk path enqueues one task carrying every changed object id rather than one per object; an assignment with zero graded possible is not passed to `openedx-core`; with the setting off, no call and no enqueue occur and grade behavior is unchanged; the grade-calculated event still fires, and fires after the transaction commits. Assignment-path tests go in `lms/djangoapps/grades/tests/test_subsection_grade.py`; task tests go in `lms/djangoapps/grades/tests/test_tasks.py`.  
- **Out of scope:** course final grades, since course-level competency criteria are out of scope per \#699; all evaluation and rollup logic, which lives in `openedx-core` per \#699 and \#643; applying staff grade overrides on the bulk path; and the operator recompute command in \#774, which ships as a management command inside the library and needs no platform change.

Files to create and modify **Modified files**

| File | Nature of modification |
| :---- | :---- |
| lms/djangoapps/grades/subsection\_grade.py | wrap `CreateSubsectionGrade.update_or_create_model()` and `bulk_create_models()` in `transaction.atomic()`, call `openedx-core` with the override-adjusted fraction, enqueue the rollup on commit, emit the grade-calculated event after the block |
| lms/djangoapps/grades/models.py | remove the grade-calculated event emission from `PersistentSubsectionGrade.update_or_create_grade()` |
| lms/djangoapps/grades/tasks.py | add the rollup Celery task, following `recalculate_subsection_grade_v3`'s `bind=True` manual-retry shape |
| lms/envs/common.py | add `ENABLE_COMPETENCY_MASTERY_TRACKING`, default `False`, with the surrounding toggle annotation block |
| requirements/edx/base.txt | bump the `openedx-core` pin to the release containing the new API |
| lms/djangoapps/grades/tests/test\_subsection\_grade.py | single and bulk assignment path transaction, override, enqueue, zero-possible, and setting-off tests |
| lms/djangoapps/grades/tests/test\_tasks.py | rollup task delegation and manual-retry tests |

- Context \#699 defines `record_graded_object_statuses` and `GradedObjectScore` and holds the shared background for this work, including why the leaf write shares the grade's transaction.  
- \#643 defines `roll_up_competency_statuses` and why it must run outside a transaction.  
- \#642 defines the tables written by both.  
- Celery prior art: `recalculate_subsection_grade_v3` and `_update_subsection_grades` in `lms/djangoapps/grades/tasks.py`, including `LoggedPersistOnFailureTask`, `@set_code_owner_attribute`, and `KNOWN_RETRY_ERRORS`.  
- Feature-gate prior art: `ENABLE_COURSE_ASSESSMENT_GRADE_CHANGE_SIGNAL` as used in `lms/djangoapps/grades/subsection_grade_factory.py` and annotated in `lms/envs/common.py`.  
- Staff overrides reach the single assignment path through `override_subsection_grade()` in `lms/djangoapps/grades/api.py`, which sends `SUBSECTION_OVERRIDE_CHANGED` and enqueues a subsection recalculation.  
- `lms/djangoapps/grades/models.py`, `PersistentSubsectionGrade.bulk_create_grades()`, for the insert-only batch behavior and the unused override prefetch.

</details>
