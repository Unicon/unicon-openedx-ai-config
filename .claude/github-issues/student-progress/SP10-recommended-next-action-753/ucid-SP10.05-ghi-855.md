# [BE] Compute whether a learner can submit to a subsection

GitHub: pending (no issue yet)
Cached: 2026-10-06

## User Story
As a learner, I want Open edX to know whether I can still submit to a subsection in order to get a recommended next action in my CBE course that I can actually act on, without having to figure this out myself or have someone tell me.

## Description
This ticket adds a function to openedx-platform that is called by #754's endpoint. Given a learner and a subsection, it returns two things:
- Whether the subsection's graded content accepts a submission from the learner now: yes, no, or unknown.
- Whether the learner has submitted or attempted anything in the subsection.

#754 uses these to tell retries, not-started subsections, and dead ends apart.

How each kind of graded content is checked:
- ORA: accepts a submission only if the learner has no active submission (never submitted, or staff reset their state) and the submission window is open. ORA doesn't accept a new submission once graded, so a graded ORA can only be retried after a staff reset.
- Problems: accepts a submission while attempts remain and the problem isn't past its due date plus any grace period, or past course end when it has no due date.
- Timed or proctored exams: any existing attempt means no.
- Graded content locked for the learner's enrollment track (for example audit): no.
- Any other scored content (for example LTI): unknown.

## Context
- Corresponding architecture spike: #757
- Blocks #754

## Acceptance Criteria

These scenarios use the following terms:

- The check is the function this ticket adds. Its caller, #754's code, gives it a learner and a subsection. It reports four things: whether the subsection accepts a submission from that learner now, whether the learner has attempted anything in the subsection, whether the learner has submitted every counting component, and whether every counting component has a score for the learner. The first answer is one of three: the subsection accepts a submission, it does not accept one, or it is unknown.
- A counting component is a component in the subsection that is scored, is worth more than zero points, and is visible to the learner. Components in ungraded subsections count too. HTML and video components are never counting components.
- The learner's due date is the subsection's due date as it applies to that learner. It can differ from the course-wide date, for example because of an individual extension or a self-paced schedule.
- A subsection is past due for the learner once the learner's due date, and any grace period the course has after it, have both passed. A subsection with no due date is not past due.
- An ORA's submission window is the one the ORA shows the learner. An ORA set to take its dates from the subsection uses the subsection's start and the learner's due date. An ORA set to use its own dates uses the dates its author entered. An ORA set to use the course's dates uses the course's start and end.
- Unless a scenario says otherwise, the subsection is graded, is not a timed or proctored exam, and is not past due for the learner. Its only counting component is the one the scenario names. The learner is enrolled in a track that can access graded content, and the course has no grace period.

```gherkin
Scenario Outline: An ORA accepts a submission only when the learner has no response on record and the ORA's submission window is open
  Given the subsection's counting component is an ORA
  And <ORA state>
  When the check runs for the learner and the subsection
  Then the check reports that the subsection <result>

  Examples:
    | ORA state | result |
    | the learner has never submitted a response and the submission window is open | accepts a submission |
    | the learner saved a draft response without submitting it and the submission window is open | accepts a submission |
    | the learner submitted a response that is awaiting grading, and the ORA lets learners reset their own response before it is graded | does not accept a submission |
    | the learner submitted a response, and the ORA is waiting for the learner to complete their own peer or self assessment step | does not accept a submission |
    | the learner's submitted response has been graded | does not accept a submission |
    | staff removed the learner's submitted response from grading without resetting the learner's state | does not accept a submission |
    | the learner's response was graded, staff then reset the learner's state, and the submission window is open | accepts a submission |
    | staff reset the learner's state and the submission window has closed | does not accept a submission |
    | the learner has never submitted a response and the submission window has not opened yet | does not accept a submission |
    | the learner has never submitted a response, the ORA takes its dates from the subsection, and the learner's due date has passed | does not accept a submission |
    | the learner has never submitted a response, the ORA takes its dates from the subsection, the learner's due date passed an hour ago, and the course has a one-day grace period | does not accept a submission |
    | the learner has never submitted a response, the ORA takes its dates from the subsection, the subsection's course-wide due date has passed, and the learner has an individual extension that has not passed | accepts a submission |
    | the learner has never submitted a response, the ORA uses its own dates, and its submission deadline has passed | does not accept a submission |
    | the learner has never submitted a response, the ORA uses the course's dates, the subsection has no due date, and the course has ended | does not accept a submission |

Scenario Outline: A problem accepts a submission while the learner has attempts left and the problem has not closed for that learner
  Given the subsection's counting component is a problem
  And <problem state>
  When the check runs for the learner and the subsection
  Then the check reports that the subsection <result>

  Examples:
    | problem state | result |
    | the learner has used 1 of 3 attempts | accepts a submission |
    | the problem allows unlimited attempts and the learner has used 5 | accepts a submission |
    | the learner has used all 3 of 3 attempts | does not accept a submission |
    | the learner had used all 3 attempts, and staff then reset the learner's attempts | accepts a submission |
    | the learner has attempts left and the learner's due date has passed | does not accept a submission |
    | the learner has attempts left, the subsection's course-wide due date has passed, and the learner has an individual extension that has not passed | accepts a submission |
    | the learner has attempts left, the learner's due date passed an hour ago, and the course has a one-day grace period | accepts a submission |
    | the learner has attempts left, and both the learner's due date and the course's grace period after it have passed | does not accept a submission |
    | the learner has attempts left, the subsection has no due date, the course has no grace period, and the course end date has passed | does not accept a submission |
    | the learner has attempts left, the subsection has no due date, the course ended an hour ago, and the course has a one-day grace period | accepts a submission |
    | the learner has attempts left, the subsection has no due date, and the course has not ended | accepts a submission |

Scenario Outline: Any exam attempt record, whatever its status, means the subsection does not accept a submission
  Given the subsection is a timed or proctored exam in a course whose exams run on edx-proctoring
  And the problems in the exam have attempts left
  And the learner has an exam attempt record that <attempt status>
  When the check runs for the learner and the subsection
  Then the check reports that the subsection does not accept a submission

  Examples:
    | attempt status |
    | was created, but the learner has not started the exam yet |
    | is marked declined, because the learner chose to take the optional proctored exam without proctoring |
    | is in progress |
    | was submitted |
    | timed out |
    | ended in an error |

Scenario: An exam the learner has no attempt record for is judged by its problems
  Given the subsection is a timed or proctored exam in a course whose exams run on edx-proctoring
  And the learner has no attempt record for the exam, because they never started it or staff removed their attempt
  And the problems in the exam have attempts left
  When the check runs for the learner and the subsection
  Then the check reports that the subsection accepts a submission

Scenario Outline: An exam in a course that uses the edx-exams service reports unknown until the learner has attempted a counting component, and does not accept a submission afterward
  Given the subsection is a timed or proctored exam in a course whose exams run on the edx-exams service
  And the problems in the exam have attempts left
  And <learner activity>
  When the check runs for the learner and the subsection
  Then the check reports that <result>

  Examples:
    | learner activity | result |
    | the learner has not submitted an answer to any problem in the exam | it is unknown whether the subsection accepts a submission |
    | the learner submitted an answer to one problem in the exam | the subsection does not accept a submission |

Scenario Outline: Graded content locked for the learner's enrollment track does not accept a submission, whatever its type
  Given the course locks graded content for audit learners
  And the learner is enrolled in the audit track
  And the subsection's counting component is <component>
  When the check runs for the learner and the subsection
  Then the check reports that the subsection does not accept a submission

  Examples:
    | component |
    | a problem with attempts left |
    | an ORA the learner has never submitted to, with its submission window open |
    | an LTI component |

Scenario Outline: The same content accepts a submission when the learner's enrollment is not locked out of it
  Given the subsection's counting component is a problem with attempts left
  And <enrollment>
  When the check runs for the learner and the subsection
  Then the check reports that the subsection accepts a submission

  Examples:
    | enrollment |
    | the course locks graded content for audit learners, and the learner is enrolled in the verified track |
    | the learner is enrolled in the audit track, and graded content is not locked for their enrollment in this course |
    | the course locks graded content for audit learners, the learner is enrolled in the audit track, and the subsection is not graded |

Scenario Outline: Scored content the check can't evaluate reports unknown while the subsection is not past due
  Given the subsection's counting component is an LTI component the learner's enrollment can access
  And <dates>
  When the check runs for the learner and the subsection
  Then the check reports that it is unknown whether the subsection accepts a submission

  Examples:
    | dates |
    | the subsection has no due date and the course has not ended |
    | the learner's due date has not passed |
    | the learner's due date passed an hour ago, and the course has a one-day grace period |

Scenario Outline: A subsection past due for the learner does not accept a submission, whatever its content
  Given the subsection is past due for the learner
  And <content>
  When the check runs for the learner and the subsection
  Then the check reports that the subsection does not accept a submission

  Examples:
    | content |
    | the subsection's counting component is an LTI component |
    | the subsection is a timed or proctored exam in a course whose exams run on the edx-exams service |
    | checking the subsection's only counting component fails with an unexpected error |
    | the subsection's counting component is an ORA that uses its own dates, and its submission deadline has not passed |

Scenario Outline: Any counting component that accepts a submission makes the subsection accept one
  Given the subsection has a problem with attempts left
  And it has <other component>
  When the check runs for the learner and the subsection
  Then the check reports that the subsection accepts a submission

  Examples:
    | other component |
    | an ORA whose submitted response is awaiting grading |
    | an LTI component |
    | an ORA whose check fails with an unexpected error |

Scenario Outline: When no counting component accepts a submission and the subsection is not past due, unknown wins over "does not accept"
  Given the subsection has a problem whose attempts are all used
  And it has <unknown component>
  When the check runs for the learner and the subsection
  Then the check reports that it is unknown whether the subsection accepts a submission

  Examples:
    | unknown component |
    | an LTI component |
    | an ORA whose check fails with an unexpected error |

Scenario Outline: Components that are hidden from the learner or worth zero points don't make the subsection accept a submission
  Given the subsection has a problem whose attempts are all used
  And it has <other problem>, with attempts left
  When the check runs for the learner and the subsection
  Then the check reports that the subsection does not accept a submission

  Examples:
    | other problem |
    | a problem hidden from the learner by their cohort |
    | a problem in randomized library content that was not picked for the learner |
    | a problem worth zero points |

Scenario Outline: A subsection the learner can't see at all does not accept a submission and has not been attempted
  Given <visibility>
  When the check runs for the learner and the subsection
  Then the check reports that the subsection does not accept a submission
  And it reports the learner as not having attempted the subsection

  Examples:
    | visibility |
    | the subsection is unreleased for the learner |
    | the subsection is staff-only |
    | the learner is not enrolled in the course |

Scenario Outline: A subsection with nothing for the learner to submit does not accept a submission
  Given the subsection's only components are <components>
  When the check runs for the learner and the subsection
  Then the check reports that the subsection does not accept a submission
  And it reports the learner as not having attempted the subsection

  Examples:
    | components |
    | an HTML component and a video component, both of which the learner has viewed |
    | problems that are all hidden from the learner by their cohort |
    | problems that are all worth zero points, none of which the learner has opened |

Scenario: A failed component check is logged, counts as attempted, and doesn't stop the check from answering
  Given the subsection has an ORA and a problem
  And checking the ORA fails with an unexpected error
  And the learner has not submitted an answer to the problem
  When the check runs for the learner and the subsection
  Then the check returns its answers instead of raising the error
  And the failure is logged, identifying the course and the ORA
  And the check reports the learner as having attempted the subsection

Scenario Outline: The learner counts as having attempted the subsection once they have submitted to or been scored on any counting component, graded or not, or started an exam attempt
  Given <learner activity>
  When the check runs for the learner and the subsection
  Then the check reports the learner as <attempted>

  Examples:
    | learner activity | attempted |
    | the learner submitted an ORA response that is still awaiting grading, and has done nothing else | having attempted the subsection |
    | the learner submitted an answer to one problem | having attempted the subsection |
    | the learner received a score from an LTI component | having attempted the subsection |
    | the learner started an attempt at the subsection's timed exam and has answered nothing | having attempted the subsection |
    | the learner opened the subsection's problems without submitting an answer | not having attempted the subsection |
    | the learner saved an ORA draft without submitting it | not having attempted the subsection |
    | the learner launched an LTI component that has not sent a score | not having attempted the subsection |
    | the learner has never opened the subsection | not having attempted the subsection |

Scenario Outline: The check reports whether the learner has submitted every graded part, and whether every one has been graded
  Given the subsection has a problem and an ORA, both counting components
  And <learner activity>
  When the check runs for the learner and the subsection
  Then the check reports the learner as <submitted>
  And it reports the learner as <graded>

  Examples:
    | learner activity | submitted | graded |
    | the learner answered the problem and has not touched the ORA | not having submitted every part | not having had every part graded |
    | the learner answered the problem, and the ORA response is awaiting grading | having submitted every part | not having had every part graded |
    | the learner answered the problem, and the ORA response has been graded | having submitted every part | having had every part graded |
    | the learner answered the problem, and the ORA is waiting for the learner to complete their own peer or self assessment step | having submitted every part | not having had every part graded |
    | the learner answered the problem, and checking the ORA fails with an unexpected error | having submitted every part | not having had every part graded |
    | the learner answered the problem, the ORA response had been graded, staff then reset the learner's state, and the learner has not resubmitted | not having submitted every part | not having had every part graded |

Scenario Outline: The check answers for the learner it is given, not for the user making the request
  Given the current request belongs to a staff member viewing the learner's progress, directly or while masquerading as the learner
  And <learner state>
  When the check runs for the learner and the subsection
  Then the check reports that the subsection <result>

  Examples:
    | learner state | result |
    | the learner is in the audit track of a course that locks graded content for audit learners, and the problem has attempts left | does not accept a submission |
    | the subsection's course-wide due date has passed, the learner has an individual extension that has not passed, and the staff member has none | accepts a submission |
    | the learner has used all of the problem's attempts, and the staff member has used none | does not accept a submission |
    | the learner submitted a response to the ORA, and the staff member has not | does not accept a submission |
    | the ORA's submission window has closed for the learner, although the staff member, as course staff, could still submit to it | does not accept a submission |

Scenario Outline: The check changes nothing and emits no events
  Given <subsection and learner history>
  When the check runs for the learner and the subsection, from the learner's own request or from a staff member's
  Then no record is created, changed, or deleted, for the learner or for anyone else
  And nothing in the subsection is marked as started or complete
  And no tracking or analytics event is emitted

  Examples:
    | subsection and learner history |
    | the subsection has an ORA, a problem, and an LTI component, and the learner has never opened it |
    | the subsection has an ORA and a problem, and the learner has submitted to both |
    | the subsection is a timed exam the learner has never started |
```

<details>
<summary>Technical Details</summary>

This is a suggested approach, not the source of truth. The User Story, Description, and Acceptance Criteria define what must be true when the work is done.

**Summary**

The check builds the learner's own view of the subsection with `get_course_blocks`, which already applies that learner's visibility rules, personalized due dates, and audit content gating. It then reads each counting component's state with read-only queries: `StudentModule` for problems, the submissions package's `Submission` model for ORA, and the edx-proctoring attempt model for exams. A subsection past the learner's due date plus grace period does not accept a submission; otherwise any component that accepts one wins, then any unknown. No block is bound as the learner, so the check itself writes nothing and emits no event. The one write is a randomized library selection that `get_course_blocks` can save (step 6).

**Approach**

1. Add a dataclass and a function to `lms/djangoapps/course_home_api/progress/api.py`:

   ```python
   @dataclass(frozen=True)
   class SubsectionSubmissionState:
       accepts: Literal["yes", "no", "unknown"]
       attempted: bool
       all_submitted: bool
       all_scored: bool

   def get_subsection_submission_state(user: User, subsection_key: UsageKey) -> SubsectionSubmissionState:
   ```

   `user` is the target learner, which #754 resolves with `_get_student_user`. The function never reads the request, `crum`, or the requesting user. The one exception is outside the function's own code: `get_course_blocks` runs the content-gating partition, which reads `crum`'s current request only to word its denial message. Gating itself is evaluated for `user`.

2. Build the learner's view with `get_course_blocks(user, subsection_key)` and its default transformers. That view already leaves out blocks the learner can't see (unreleased, staff-only, hidden by cohort, not picked from randomized library content), and each block's `due` is the learner's own date from edx-when. Blocks locked by audit content gating stay in the view with `authorization_denial_reason` set, evaluated for `user`; the content gating partition is the only partition that sets that field. A counting component is a block in this view with `has_score` true, `weight` not 0, and a `max_score` (collected by `GradesTransformer`) that is not 0. When the subsection itself is absent from the learner's block structure, or there are no counting components, return `SubsectionSubmissionState(accepts="no", attempted=False, all_submitted=False, all_scored=False)`. The block structure doesn't collect the grace period (the subsection's inherited `graceperiod`) or problems' `max_attempts`. Read both from the modulestore without binding to a user, for example with `modulestore().get_item(subsection_key, depth=None)`.

3. Give each counting component the result of the first rule that applies:
   1. `authorization_denial_reason` is set: "no".
   2. The subsection is an exam (`MilestonesAndSpecialExamsTransformer.is_special_exam`) and `exams_ida_enabled(course_key)` is on: "no" when any counting component in the subsection counts as attempted under step 4, otherwise "unknown". The edx-exams service keeps no local attempt records, so the answer rests on the components' own state. This matches the edx-proctoring rule in the next item, where any existing attempt means "no".
   3. The subsection is an exam and the learner has any edx-proctoring attempt record for it, whatever its status: "no". Query `ProctoredExamStudentAttempt.objects.filter(user=user, proctored_exam__course_id=..., proctored_exam__content_id=...).exists()` directly (step 6 explains why). Staff "remove attempt" hard-deletes the row, so a removed attempt no longer blocks.
   4. Problem: mirror `ProblemBlock.closed()`. The result is "no" when `max_attempts` is set and the learner's `attempts` (from their `StudentModule.state` JSON) has reached it, or when the subsection has no due date and `CourseOverview.end` plus the grace period has passed. Otherwise it is "yes". The due-date branch of `closed()` is the past-due rule in step 5.
   5. ORA: "no" when the learner has an active submission; otherwise "yes" only inside the submission window. To check for a submission, query `Submission.objects.filter(student_item__student_id__in=<ids>, student_item__course_id=str(course_key), student_item__item_id=str(usage_key)).exists()`, where `<ids>` are the `anonymous_user_id` values of the learner's existing `AnonymousUserId` rows for the course (model in `common/djangoapps/student/models`), read with a plain query such as `AnonymousUserId.objects.filter(user=user, course_id=course_key).values_list("anonymous_user_id", flat=True)`. No rows means no submissions. `Submission.objects` already excludes submissions that a staff reset soft-deleted, and a submission that staff removed from grading still exists, so it still blocks a new one. The window depends on `date_config_type`, which `OpenAssessmentDateTransformer` collects along with the ORA's own dates: `subsection` is open until the learner's due date, with no grace period, because ORA's `is_closed` never applies one. The window check compares only against the learner's due date. The start is enforced by step 2, because `get_course_blocks` leaves an unreleased subsection out of the learner's view (`StartDateTransformer`); `course_end` runs from the course's start to its end; `manual` runs from `submission_start` to `submission_due`, parsed the way `get_ora_as_assignments` parses them.
   6. Any other scored type, LTI for example: "unknown".

   If evaluating a component raises an exception, that component reports "unknown" and counts as attempted. The check logs the exception with the course key and the component's usage key, then continues.

4. Read `attempted` for every counting component, whichever rule decided its result. A problem counts when `attempts > 0`, an ORA counts when it has a submission, and any other type counts when the learner's `StudentModule.grade` is set. On an exam subsection, any edx-proctoring attempt record also counts.

   The dataclass's other two fields come from the same per-component reads:
   - `all_submitted` is true when every counting component counts as attempted under the per-component rule above (a problem with `attempts > 0`, an ORA with an active submission, any other type with `StudentModule.grade` set). A component whose check raised an error counts as submitted, the same way it counts as attempted. An exam attempt record makes the subsection attempted but does not make any component submitted.
   - `all_scored` is true when every counting component has a score for the learner. A problem counts as scored once it is submitted, because it is scored on submission. An ORA counts as scored when its active submission has a `submissions.models.Score` row, read directly through the model the same way the check already reads `Submission`. Any other type counts as scored when `StudentModule.grade` is set. A component whose check raised an error counts as not scored.
   - Both fields are false in the early return of step 2, which covers a subsection missing from the learner's view and a subsection with no counting components.
   - `all_scored` implies `all_submitted`, which implies `attempted`.

5. Combine the component results. If the subsection's learner `due` plus the grace period has passed, `accepts` is "no". Otherwise `accepts` is "yes" if any component reported "yes", else "unknown" if any reported "unknown", else "no".

6. Keep the check read-only. `StudentModule`, `Submission`, and `ProctoredExamStudentAttempt` are read directly through their models rather than through their packages' APIs, because those APIs write on read. Never bind a block as the learner (no `get_block_for_descriptor` and no `FieldDataCache`). Don't call any of these, because each one writes:
   - `submissions.api.get_submissions`, which creates a `StudentItem`
   - `anonymous_id_for_user`, which creates an `AnonymousUserId`
   - the `edx_proctoring.api` read functions: `get_current_exam_attempt` and `get_exam_attempt_by_id` mark an expired attempt as timed out when they read it

   `get_course_blocks` makes one write of its own: the first time it runs for a learner who has no selection for a randomized library block, `ContentLibraryTransformer` saves a selection and emits `edx.librarycontentblock.content.assigned`. The progress tab's grade read and `calculate_progress_for_learner_in_course` already make that same selection for the same learner, so the check accepts that write.

7. Tests: warm the block structure before asserting the read-only rule. Then fail the test on any INSERT, UPDATE, or DELETE captured with `CaptureQueriesContext`, and on any call to `eventtracking.tracker.emit`. Beyond the AC, cover these cases:
   - a learner with no `AnonymousUserId` row in the course
   - an individual extension set with `edx_when.api.set_date_for_block(..., user=learner)` while `crum`'s current user is a staff member who has no extension
   - an exam subsection whose problems are locked for an audit learner, in a course with `exams_ida` on, where the lock wins and the check reports "no"

**Files to create and modify**

| File | Change |
| --- | --- |
| lms/djangoapps/course_home_api/progress/api.py | modified: add SubsectionSubmissionState and get_subsection_submission_state() |
| lms/djangoapps/course_home_api/progress/tests/test_api.py | modified: add a ModuleStoreTestCase class for get_subsection_submission_state() |

**Additional context**

- This ticket's rules for problems and ORA, in step 3, supersede #757 section 1. They differ from it on two points: a problem always enforces its due date (or the course end when it has no due date) plus the grace period, and an ORA accepts a new submission only when the learner has no active submission.
- Prior art for reading ORA dates from the block structure: `get_ora_as_assignments` in `lms/djangoapps/courseware/courses.py`. Prior art for the exam branch: `MilestonesAndSpecialExamsTransformer` in `lms/djangoapps/course_api/blocks/transformers/milestones.py`.
- Both packages' models are already imported directly elsewhere in the platform: `submissions.models.Submission` in `lms/djangoapps/grades/management/commands/recalculate_subsection_grades.py`, and `edx_proctoring.models` in `lms/djangoapps/instructor/views/api_v2.py`.

</details>

## Open Questions

- (architect, final review) May the check use `get_course_blocks`, even though the first time it runs for a learner with no selection for a randomized library block, it saves a selection to `StudentModule` and emits `edx.librarycontentblock.content.assigned`? This conflicts with the read-only decision and with the AC scenario "The check changes nothing and emits no events". The progress tab's grade read and `calculate_progress_for_learner_in_course` already run the same transformer for the same learner, so in practice the selection usually exists before the check runs. Options: A) accept the write as existing platform behavior, and add one sentence to the read-only scenario excluding the randomized library selection; B) call `get_course_blocks` without the two library transformers and filter library children from the learner's stored selection, read-only, treating every child as visible when no selection exists (about half a day more, and a second copy of the platform's selection filter to keep in sync). Recommended: A.
- (architect, final review) Should the check report "does not accept" for any subsection past the learner's due date plus grace period, before it looks at the content? Something has to enforce the due date for content the check can't evaluate, such as LTI, or #754 recommends a not-started LTI subsection after its due date. Checking past due first also means an ORA set to use its own dates, or the course's dates, reports "does not accept" once the subsection is past due, even while the ORA's own deadline is still open. Options: A) apply the past-due rule first, to every component, as the AC and Technical Details state; B) apply it only to components reported as unknown, so an ORA still open on its own dates reports "accepts" (this changes one AC row); C) #754 enforces the subsection due date from the learner's outline, and the check reports only the content's state. Recommended: A, because it gives learners a single due-date rule and #754's Description already removes past-due subsections.
- (architect, final review) Do scored components in an ungraded subsection count? A competency criterion can target an ungraded subsection; if its components don't count, #754 never recommends it. Audit content gating only locks graded components, so an audit learner can submit to these. Options: A) they count, and the enrollment-track lock doesn't apply to them, as the AC and Technical Details state; B) only components in graded subsections count. Recommended: A.
- (architect, final review) A learner can reset a submitted practice exam themselves, which deletes the old attempt and starts a new one. Under the "any attempt record means does not accept" rule, a practice exam with a submitted attempt reports "does not accept" even though the learner could act on it. Options: A) accept this, since practice exams rarely carry competency criteria; B) treat a practice exam's attempt like no attempt, so its problems decide. Recommended: A.
- (implementer) Should the check accept an optional `collected_block_structure` and pass it through to `get_course_blocks`? #754 may call the check for many subsections in one request, and without it each call reloads the course's collected block structure from the cache. `lms/djangoapps/grades/course_data.py` already uses this seam. Recommended: add the optional keyword argument.
