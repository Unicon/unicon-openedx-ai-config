# [BE] Compute whether a learner can submit to a subsection

GitHub: https://github.com/openedx/openedx-core/issues/855 (#855, OPEN)
Cached: 2026-10-22

## User Story
As a learner, I want Open edX to know whether I can still submit to a subsection in order to get a recommended next action in my CBE course that I can actually act on, without having to figure this out myself or have someone tell me.

## Description
This ticket adds a function to openedx-platform that is called by #754's endpoint. Given a learner and a list of subsections, it returns four answers for each subsection, each yes, no, or unknown:
- Whether the subsection's scored content accepts work from the learner now: a new submission, or an ORA peer, self, or training step the learner still needs to do.
- Whether the learner has submitted or attempted anything in the subsection.
- Whether the learner has done all of their own work in the subsection, so it is just waiting on someone else to grade it.
- Whether all of the subsection's scored content has been graded.

When the learner can't see a subsection, or it has no scored content, it returns nothing for that subsection. The function takes the whole list at once, batched rather than one subsection at a time, so that it builds the learner's view of the course once and reads the learner's state for every listed subsection in a fixed number of database queries. Its cost doesn't grow with the number of subsections #754 asks about. #754 uses these answers to tell the difference between subsections the learner can continue, retry, those that the learner hasn't started, and those that the learner can't do anything with right now.

How each kind of scored content is checked:
- ORA: accepts work if the learner has no active submission (never submitted, or staff reset their state) and the submission window is open, if the learner still needs to do their own peer, self, or training step and that step is open, or if the ORA lets learners reset their own response and the learner still can. ORA doesn't accept a new submission once graded, so a graded ORA can only be retried after a staff reset.
- Problems: accepts a submission while attempts remain and the problem isn't past its due date plus any grace period, or past course end when it has no due date.
- Timed or proctored exams: an exam the learner hasn't started, or is still taking within its time limit, is judged by its problems. A submitted exam or one whose time has run out doesn't accept any new submissions/work from the learner, except for a practice exam the learner can still reset themselves.
- Graded content locked for the learner's enrollment track (for example audit): no.
- Any other scored content (for example LTI): unknown.

## Context
- Corresponding architecture spike: #757
- Blocks #754

## Acceptance Criteria

The check is an internal function, and QA sees it only through #754's recommendation, which also depends on due dates and criteria. A reviewer therefore confirms each item below at code review time against the check's unit tests. Each item states a rule, and its table lists the cases the unit tests must cover.

These items use the following terms:

- The check is the function this ticket adds. Its caller, #754's code, gives it a learner and a list of subsections, and it answers for each subsection. Each item below describes one subsection's answers. The four answers for a subsection are each yes, no, or unknown:
  - `accepts_learner_work`: whether the subsection accepts work from the learner now, meaning a new submission or an ORA peer, self, or training step the learner still owes
  - `attempted`: whether the learner has attempted anything in the subsection
  - `all_learner_work_done`: whether the learner has done all of their own work on every counting component, meaning they submitted it and finished any ORA step they owe
  - `all_scored`: whether every counting component has a score for the learner
- When the learner can't see a subsection, or it has no counting components, the check returns nothing to evaluate for that subsection instead of the four answers.
- A counting component is a component in the subsection that is scored, is worth more than zero points, and is visible to the learner. Components in ungraded subsections count too. HTML and video components are never counting components.
- The learner's due date is the subsection's due date as it applies to that learner. It can differ from the course-wide date, for example because of an individual extension or a self-paced schedule.
- A subsection is past due for the learner once the learner's due date, and any grace period the course has after it, have both passed. A subsection with no due date is not past due.
- An ORA's submission window is the one the ORA shows the learner. An ORA set to take its dates from the subsection uses the subsection's start and the learner's due date. An ORA set to use its own dates uses the dates its author entered. An ORA set to use the course's dates uses the course's start and end. Each of the ORA's peer, self, and training steps has its own window, set the same way.
- Unless a case says otherwise, the subsection is graded, is not a timed or proctored exam, and is not past due for the learner. Its only counting component is the one the case names. The learner is enrolled in a track that can access graded content, and the course has no grace period. An ORA is graded by staff only and doesn't let learners reset their own response.

**ORA, problems, and exams**

- [ ] An ORA accepts work when the learner has no response on record and its submission window is open, when the learner owes their own peer, self, or training step and that step is open, or when the ORA lets learners reset their own response and the learner still can.

  | ORA state | Accepts work? |
  | --- | --- |
  | The learner has never submitted a response, and the submission window is open. | Yes |
  | The learner saved a draft response without submitting it, and the submission window is open. | Yes |
  | The learner's submitted response is awaiting grading. | No |
  | The learner's submitted response is awaiting grading. The ORA lets learners reset their own response, has no peer step, and its submission window is open. | Yes |
  | The learner's submitted response is awaiting grading. The ORA lets learners reset their own response, but it has a peer step. | No |
  | The learner submitted a response and still owes their own peer assessment step, which is open. | Yes |
  | The learner submitted a response and still owes their own self assessment step, which is open. | Yes |
  | The learner submitted a response and still owes their own peer assessment step, whose due date has passed. | No |
  | The learner's submitted response has been graded. | No |
  | Staff removed the learner's submitted response from grading without resetting the learner's state. | No |
  | The learner's response was graded, staff then reset the learner's state, and the submission window is open. | Yes |
  | Staff reset the learner's state, and the submission window has closed. | No |
  | The learner has never submitted a response, and the submission window has not opened yet. | No |
  | The learner has never submitted a response, the ORA takes its dates from the subsection, and the learner's due date has passed. | No |
  | The learner has never submitted a response, the ORA takes its dates from the subsection, the learner's due date passed an hour ago, and the course has a one-day grace period. | No |
  | The learner has never submitted a response, the ORA takes its dates from the subsection, the subsection's course-wide due date has passed, and the learner has an individual extension that has not passed. | Yes |
  | The learner has never submitted a response, the ORA uses its own dates, and its submission deadline has passed. | No |
  | The learner has never submitted a response, the ORA uses its own dates, its submission deadline has not passed, and the subsection is past due for the learner. | Yes |
  | The learner has never submitted a response, the ORA uses the course's dates, the subsection has no due date, and the course has ended. | No |

- [ ] A problem accepts work while the learner has attempts left and the problem has not closed for that learner.

  | Problem state | Accepts work? |
  | --- | --- |
  | The learner has used 1 of 3 attempts. | Yes |
  | The problem allows unlimited attempts, and the learner has used 5. | Yes |
  | The learner has used all 3 of 3 attempts. | No |
  | The learner had used all 3 attempts, and staff then reset the learner's attempts. | Yes |
  | The learner has attempts left, and the learner's due date has passed. | No |
  | The learner has attempts left, the subsection's course-wide due date has passed, and the learner has an individual extension that has not passed. | Yes |
  | The learner has attempts left, the learner's due date passed an hour ago, and the course has a one-day grace period. | Yes |
  | The learner has attempts left, and both the learner's due date and the course's grace period after it have passed. | No |
  | The learner has attempts left, the subsection has no due date, the course has no grace period, and the course end date has passed. | No |
  | The learner has attempts left, the subsection has no due date, the course ended an hour ago, and the course has a one-day grace period. | Yes |
  | The learner has attempts left, the subsection has no due date, and the course has not ended. | Yes |

- [ ] A timed or proctored exam in a course whose exams run on edx-proctoring is judged by its problems until the learner's exam attempt has ended, and accepts no work after that. In every case, the exam's problems have attempts left.

  | The learner's exam attempt | Accepts work? |
  | --- | --- |
  | There is none, because the learner never started the exam or staff removed their attempt. | Yes |
  | It was created, but the learner has not started the exam yet. | Yes |
  | It is marked declined, because the learner chose to take an optional proctored exam without proctoring, which shows the exam as ordinary content. | Yes |
  | It is in progress. | Yes |
  | It is waiting for the learner to confirm submission, and the learner can still go back to the exam. | Yes |
  | It is in progress, its time limit has run out, and nothing has recorded the time-out yet. The learner has nothing left to do, because each problem was graded when the learner submitted it. | No |
  | It was submitted, including an attempt whose time ran out, which edx-proctoring records as submitted. | No |
  | It is awaiting a second review. | No |
  | It was verified. | No |
  | It was rejected. | No |
  | It ended in an error. | No |
  | It ended in an error, and staff then marked it ready to resume. | Yes |

- [ ] A practice exam whose attempt has ended accepts work when the learner can reset the attempt themselves and the reset leaves them something to submit. A learner can reset any ended practice attempt except a verified one. Resetting starts a new attempt. When the old attempt was submitted, the reset also wipes the learner's problem answers and attempt counts, so the learner starts the problems fresh. When the old attempt ended any other way, the reset keeps the problems' answers and attempt counts as they were, so the problems decide. In every case, the learner has not reset the attempt. The check answers from what a reset would allow and never performs one.

  | The learner's newest practice exam attempt | If the learner reset it | Accepts work? |
  | --- | --- | --- |
  | It was submitted, and the learner has used every attempt on the problems. | The reset would wipe the problems, so every attempt would be available again. | Yes |
  | It ended in an error, and the problems have attempts left. | The reset would keep the problems as they are, and attempts would remain. | Yes |
  | It ended in an error, and the learner has used every attempt on the problems. | The reset would keep the problems as they are, so no attempts would remain. | No |
  | It was verified, and the problems have attempts left. | The learner can't reset a verified attempt, so the attempts left on the problems can't be used. | No |

- [ ] A timed or proctored exam in a course whose exams run on the edx-exams service reports unknown until the learner has attempted a counting component, and does not accept work afterward. The edx-exams service keeps the learner's exam attempt in a separate system the check can't read, so the check can't tell an exam in progress from a submitted one. Once the learner has answered anything, the check assumes the exam was submitted, because an exam stays in progress only for its time limit. In every case, the exam's problems have attempts left under their own attempt limits.

  | Learner activity | Accepts work? |
  | --- | --- |
  | The learner has not submitted an answer to any problem in the exam. | Unknown |
  | The learner submitted an answer to one problem in the exam. | No |

**Enrollment track, unknown content, and dates**

- [ ] Graded content locked for the learner's enrollment track does not accept work, whatever its type. In every case, the course locks graded content for audit learners and the learner is enrolled in the audit track.

  | The subsection's counting component | Accepts work? |
  | --- | --- |
  | A problem with attempts left | No |
  | An ORA the learner has never submitted to, with its submission window open | No |
  | An LTI component | No |

- [ ] The same content accepts work when the learner's enrollment is not locked out of it. In every case, the subsection's counting component is a problem with attempts left.

  | Enrollment | Accepts work? |
  | --- | --- |
  | The course locks graded content for audit learners, and the learner is enrolled in the verified track. | Yes |
  | The learner is enrolled in the audit track, and graded content is not locked for their enrollment in this course. | Yes |
  | The course locks graded content for audit learners, the learner is enrolled in the audit track, and the subsection is not graded. | Yes |

- [ ] Scored content the check can't evaluate reports unknown, whatever the dates. In every case, the subsection's counting component is an LTI component the learner's enrollment can access.

  | Dates | Accepts work? |
  | --- | --- |
  | The subsection has no due date, and the course has not ended. | Unknown |
  | The learner's due date has not passed. | Unknown |
  | The learner's due date passed an hour ago, and the course has a one-day grace period. | Unknown |
  | Both the learner's due date and the course's grace period after it have passed. | Unknown |

- [ ] The check applies no due date to the subsection as a whole. Each component's own dates decide its answer. In every case, the subsection is past due for the learner.

  | Content | Accepts work? |
  | --- | --- |
  | The subsection's counting component is an LTI component. | Unknown |
  | The subsection is a timed or proctored exam in a course whose exams run on the edx-exams service, and the learner has answered nothing. | Unknown |
  | Checking the subsection's only counting component fails with an unexpected error. | Unknown |
  | The subsection's counting component is an ORA that uses its own dates, the learner has never submitted a response, and its submission deadline has not passed. | Yes |
  | The subsection's counting component is a problem with attempts left. | No |

**Combining components**

- [ ] Any counting component that accepts work makes the subsection accept work. In every case, the subsection also has a problem with attempts left.

  | The subsection's other component | Accepts work? |
  | --- | --- |
  | An ORA whose submitted response is awaiting grading | Yes |
  | An LTI component | Yes |
  | An ORA whose check fails with an unexpected error | Yes |

- [ ] When no counting component accepts work, unknown wins over no. In every case, the subsection also has a problem whose attempts are all used.

  | The subsection's other component | Accepts work? |
  | --- | --- |
  | An LTI component | Unknown |
  | An ORA whose check fails with an unexpected error | Unknown |

- [ ] Components that are hidden from the learner or worth zero points don't make the subsection accept work. In every case, the subsection also has a problem whose attempts are all used, and the other problem has attempts left.

  | The subsection's other problem | Accepts work? |
  | --- | --- |
  | A problem hidden from the learner by their cohort | No |
  | A problem in randomized library content that was not picked for the learner | No |
  | A problem worth zero points | No |

- [ ] The check returns nothing to evaluate when the learner can't see the subsection or it has nothing for the learner to submit.

  | The subsection | Result |
  | --- | --- |
  | It is unreleased for the learner. | Nothing to evaluate |
  | It is staff-only. | Nothing to evaluate |
  | Its only components are an HTML component and a video component, both of which the learner has viewed. | Nothing to evaluate |
  | Its only problems are all hidden from the learner by their cohort. | Nothing to evaluate |
  | Its only problems are all worth zero points, and the learner has opened none of them. | Nothing to evaluate |

- [ ] A failed component check is logged with the course and the component, and the check returns its answers instead of raising the error. The failed component makes an answer unknown only when the other components don't settle that answer.

  | The subsection | `accepts_learner_work` | `attempted` | `all_learner_work_done` | `all_scored` |
  | --- | --- | --- | --- | --- |
  | It has an ORA and a problem. Checking the ORA fails, and the learner has not answered the problem. | Yes | Unknown | No | No |
  | Its only counting component is an ORA, and checking the ORA fails. | Unknown | Unknown | Unknown | Unknown |

**What the learner has done**

- [ ] The learner counts as having attempted the subsection once they have submitted to or been scored on any counting component, graded or not, or started an exam attempt. An exam attempt the learner has created or declined but not started doesn't count.

  | Learner activity | Attempted? |
  | --- | --- |
  | The learner submitted an ORA response that is still awaiting grading, and has done nothing else. | Yes |
  | The learner submitted an answer to one problem. | Yes |
  | The learner received a score from an LTI component. | Yes |
  | The learner started an attempt at the subsection's timed exam and has answered nothing. | Yes |
  | The learner's attempt at the subsection's proctored exam was created, but the learner has not started the exam or answered anything. | No |
  | The learner declined proctoring on the subsection's optional proctored exam and has answered nothing. | No |
  | The learner submitted the subsection's practice exam. | Yes |
  | The learner opened the subsection's problems without submitting an answer. | No |
  | The learner saved an ORA draft without submitting it. | No |
  | The learner launched an LTI component that has not sent a score. The platform keeps no record of a launch, so the check can't tell this from an LTI component the learner never opened. | No |
  | The learner has never opened the subsection. | No |

- [ ] The check reports whether the learner has done all of their own work on every counting component, and whether every one has been scored. In every case, the subsection has a problem and an ORA, both counting components.

  | Learner activity | `all_learner_work_done` | `all_scored` |
  | --- | --- | --- |
  | The learner answered the problem and has not touched the ORA. | No | No |
  | The learner answered the problem, and the ORA response is awaiting grading. | Yes | No |
  | The learner answered the problem, and the ORA response has been graded. | Yes | Yes |
  | The learner answered the problem, submitted the ORA response, and still owes their own peer or self assessment step. | No | No |
  | The learner answered the problem, and checking the ORA fails with an unexpected error. | Unknown | Unknown |
  | The learner answered the problem, the ORA response had been graded, staff then reset the learner's state, and the learner has not resubmitted. | No | No |

- [ ] Once the learner's edx-proctoring exam attempt has ended, the learner counts as having done all of their own work on the exam, even if they left problems unanswered. In every case, the exam is a practice exam with two problems.

  | The learner's exam attempt | `all_learner_work_done` | `all_scored` |
  | --- | --- | --- |
  | The learner submitted it with one problem unanswered. | Yes | No |
  | The learner submitted it with both problems answered. | Yes | Yes |
  | It is in progress, and the learner has answered one problem. | No | No |

**Checking many subsections at once**

- [ ] The check builds the learner's view of the course once per call and makes the same number of database queries however many subsections it is given. In every case, every subsection given has a problem and an ORA, both counting components, and the learner has submitted to both.

  | Subsections given to the check | Builds of the learner's course view | Database queries |
  | --- | --- | --- |
  | One | One | Some number N |
  | Fifty | One | The same N |

**Whose answers, and no side effects**

- [ ] The check answers for the learner it is given, not for the user making the request. In every case, the current request belongs to a staff member viewing the learner's progress, directly or while masquerading as the learner.

  | Learner state | Accepts work? |
  | --- | --- |
  | The learner is in the audit track of a course that locks graded content for audit learners, and the problem has attempts left. | No |
  | The subsection's course-wide due date has passed, the learner has an individual extension that has not passed, and the staff member has none. | Yes |
  | The learner has used all of the problem's attempts, and the staff member has used none. | No |
  | The learner submitted a response to the ORA that is awaiting grading, and the staff member has not submitted one. | No |
  | The ORA's submission window has closed for the learner, although the staff member, as course staff, could still submit to it. | No |

- [ ] The check changes nothing and emits no events, whether it runs from the learner's own request or from a staff member's. No record is created, changed, or deleted, for the learner or for anyone else, nothing in the subsection is marked as started or complete, and no tracking or analytics event is emitted. The one exception is the selection of randomized library content that the platform saves the first time it builds a learner's view of the course, which the Progress page also saves.

  | Subsection and learner history |
  | --- |
  | The subsection has an ORA, a problem, and an LTI component, and the learner has never opened it. |
  | The subsection has an ORA and a problem, and the learner has submitted to both. |
  | The subsection is a timed exam the learner has never started. |
  | The learner's ORA response has received every peer assessment it needs, but ORA has not yet updated the response's grading status. |

<details>
<summary>Technical Details</summary>

This is a suggested approach, not the source of truth. The User Story, Description, and Acceptance Criteria define what must be true when the work is done.

**Summary**

The check builds the learner's own view of the course once per call with `get_course_blocks`, which already applies that learner's visibility rules, personalized due dates, and audit content gating, and reads every listed subsection from that one view. It reads each counting component's state with read-only model queries, one query per model for all listed subsections at once: `StudentModule` for problems, the submissions package's `Submission` and `Score` plus ORA's `AssessmentWorkflow` for ORA, and the edx-proctoring attempt model for exams. Each component reports what it lets the learner do now under its own dates, and the four subsection answers combine those reports, so a failed component check makes an answer unknown only when the other components don't settle it. No block is bound as the learner, so the check itself writes nothing and emits no event.

**Approach**

1. Add a dataclass and a function to `lms/djangoapps/course_home_api/progress/api.py`:

   ```python
   @dataclass(frozen=True)
   class SubsectionSubmissionState:
       accepts_learner_work: bool | None
       attempted: bool | None
       all_learner_work_done: bool | None
       all_scored: bool | None

   def get_subsection_submission_states(
       user: User,
       subsection_keys: Iterable[UsageKey],
       collected_block_structure: BlockStructureBlockData | None = None,
   ) -> dict[UsageKey, SubsectionSubmissionState | None]:
   ```

   The result has one entry for every key in `subsection_keys`, which all belong to the same course run. A value of `None` means there is nothing to evaluate for that subsection. `None` in a field means unknown, so callers compare with `is True` and `is False`, never by truthiness. The fields mean:
   - `accepts_learner_work`: at least one counting component lets the learner do graded work now, either by submitting or by finishing an ORA peer, self, or training step they owe.
   - `attempted`: the learner has submitted to or been scored on at least one counting component, or has an exam attempt.
   - `all_learner_work_done`: on every counting component, the learner has done everything they can until others grade it, meaning they submitted it and owe no ORA step.
   - `all_scored`: every counting component has a score for the learner.

   `user` is the target learner, which #754 resolves with `get_student_user()`. The function never reads the request or the requesting user, either directly or through `crum`, a library that lets any code fetch the current request without being passed it. The one exception is outside the function's own code: `get_course_blocks` runs the content-gating partition, which reads `crum`'s current request only to word its denial message. Gating itself is evaluated for `user`.

2. Build the learner's view once per call, with `get_course_blocks` on the course's root block and its default transformers, as `CourseData.structure` in `lms/djangoapps/grades/course_data.py` does. `get_course_blocks` deep-copies the course's whole block structure and runs every transformer over all of it before it prunes, even when it is given a subsection as its starting block, so one call per subsection would copy and transform the course once per subsection. #754 passes the course's collected block structure it already loaded, the same seam `CourseData` uses, so this call doesn't reload it from the cache. That view already leaves out blocks the learner can't see (unreleased, staff-only, hidden by cohort, not picked from randomized library content), and each block's `due` is the learner's own date from edx-when. Blocks locked by audit content gating stay in the view with `authorization_denial_reason` set, evaluated for `user`; the content gating partition is the only partition that sets that field. A counting component is a block in this view with `has_score` true, `weight` not 0, and a `max_score` (collected by `GradesTransformer`) that is not 0. Components in ungraded subsections count too, so don't filter on `graded` the way `get_ora_as_assignments` does. Map a subsection to `None` when it is absent from the learner's block structure or has no counting components, because there is nothing to evaluate there. The block structure doesn't collect the grace period (the subsection's inherited `graceperiod`), problems' `max_attempts`, or ORA's `allow_learner_resubmissions` and `resubmissions_grace_period`. Read them from the modulestore without binding to a user, for example with `modulestore().get_item(subsection_key, depth=None)`.

3. Before evaluating any component, load the learner's state for all counting components of all listed subsections, one query per model: the `StudentModule` rows filtered on `student`, `course_id`, and `module_state_key__in` the counting components' keys, the way `SubsectionGradeFactory._csm_scores` reads them for a whole course; the ORA rows described in rule 5 below; and the exam attempts described in rule 3 below. The rules then read from those results instead of querying per component. For each counting component, decide whether it accepts work from the learner now: yes, no, or unknown. Use the first rule below that applies. The answer says only what the learner could do, not whether they should. A learner can reset a submitted practice exam or an ORA response awaiting grading themselves, so both answer yes, and #754 decides from the other three fields whether recommending them makes sense.
   1. `authorization_denial_reason` is set: no.
   2. The subsection is an exam (`MilestonesAndSpecialExamsTransformer.is_special_exam`) and `exams_ida_enabled(course_key)` is on: no when any counting component in the subsection counts as attempted under step 4, otherwise unknown. The edx-exams service keeps no local attempt records, so the check can't tell an exam in progress from a submitted one. An exam is in progress only for its time limit, so once the learner has answered anything, the exam has almost always been submitted.
   3. The subsection is an exam, and the learner has an edx-proctoring attempt for it. Read the learner's attempts from `ProctoredExamStudentAttempt` directly (step 6) in one query for the whole call, filtered on `user` and `proctored_exam__course_id`, and group them by `proctored_exam__content_id` in Python, newest `created` first, because a practice exam can have several rows. Staff "remove attempt" hard-deletes the row, so a removed attempt no longer counts.
      - The attempt hasn't ended when its status is one of edx-proctoring's incomplete statuses (`eligible`, `created`, `download_software_clicked`, `ready_to_start`, `started`, `ready_to_submit`), when it is `declined`, which shows the learner the exam as ordinary content, or when staff have set its `ready_to_resume` flag. Such an exam falls through to the rules below and is judged by its problems. The exception is a `started` or `ready_to_submit` attempt whose time limit has run out, which has ended: no. edx-proctoring records a time-out only when its API next reads the attempt, so the stored status can still say `started`. Compute the time left with `edx_proctoring.utils.get_time_remaining_for_attempt`, which reads only the attempt's `started_at` and `allowed_time_limit_mins` and writes nothing.
      - Any other status means the attempt has ended: no. The exception is a practice exam (`ProctoredExam.is_practice_exam`) whose status isn't `verified`, because the learner can reset it themselves. A `submitted` practice attempt is yes, because that reset also deletes the exam's problem state. Any other ended practice attempt falls through to its problems, because that reset leaves the problem state in place.
   4. Problem: follow `ProblemBlock.closed()`, plus treat the course end (plus the grace period) as the close date when the subsection has no due date. The answer is no when `max_attempts` is set and the learner's `attempts` (from their `StudentModule.state` JSON) has reached it, or when the close date has passed. The close date is the learner's due date for the subsection, or `CourseOverview.end` when there is no due date, plus the grace period. Otherwise the answer is yes.
   5. ORA: find the learner's active submissions for every listed ORA with one query, `Submission.objects.filter(student_item__student_id__in=<ids>, student_item__course_id=str(course_key), student_item__item_id__in=<the ORA usage keys, as strings>)`, and match each row to its ORA by `student_item__item_id`. Here `<ids>` are the learner's `anonymous_user_id` values from a plain `AnonymousUserId.objects.filter(user=user, course_id=course_key)` query (model in `common/djangoapps/student/models`). No row for an ORA means no submission there. `Submission.objects` already excludes submissions that a staff reset or a learner reset soft-deleted, and a submission that staff removed from grading stays active. Then:
      - With no active submission, the answer is yes while the submission window is open, otherwise no.
      - When the submission's `AssessmentWorkflow` (read directly from `openassessment.workflow.models`, in one query with `submission_uuid__in` the active submissions' uuids) has status `peer`, `self`, or `training`, the learner still owes that step. The answer is yes while that step is open, otherwise no. ORA updates the stored status when the learner finishes one of their own steps, so it is current for those steps. A missing workflow row means the learner owes no step.
      - Otherwise the answer is yes only when the learner can still reset their response themselves: `allow_learner_resubmissions` is on, the ORA has no peer step, the workflow status isn't `done` or `cancelled`, the submission window is open, and, when `resubmissions_grace_period` is set, that period counted from the submission's `created_at` hasn't passed. ORA also refuses a reset while staff hold its grading lock; the check ignores that short-lived lock. Every other case is no.

      ORA's windows depend on `date_config_type`. In `subsection` mode, the submission and every step are open from the subsection's start until the learner's due date, with no grace period, because ORA's `is_closed` never applies one. Step 2 already enforces the start, because `StartDateTransformer` leaves an unreleased subsection out of the learner's view. In `course_end` mode the submission and every step run from the course's start to its end. In `manual` mode each uses its own dates, from `submission_start` and `submission_due` or from its `valid_assessments` entry, and a blank date is filled the way ORA's `resolve_dates` fills it: from the neighboring steps, and finally from the ORA's own `start` and the learner's `due`. `resolve_dates` (`openassessment/xblock/utils/resolve_dates.py`) is a pure function, so the check can call it directly. The workflow names steps `peer`, `self`, and `training`, while `valid_assessments` names them `peer-assessment`, `self-assessment`, and `student-training`.
   6. Any other scored type, LTI for example: unknown.

   If evaluating a component raises an exception, the check logs it with the course key and the component's usage key, treats that component as unknown for all four fields, and continues.

4. Read three more facts for every counting component, whichever rule decided its answer in step 3. Each fact is yes or no, or unknown for a component whose check raised an exception.
   - Attempted: a problem with `attempts > 0`, an ORA with an active submission, or any other type with `StudentModule.grade` set. On an exam subsection, an edx-proctoring attempt the learner has started also makes the subsection attempted: any status other than `eligible`, `created`, `download_software_clicked`, `ready_to_start`, or `declined`.
   - Learner work done: a problem with `attempts > 0`, an ORA with an active submission whose workflow status isn't `peer`, `self`, or `training`, or any other type with `StudentModule.grade` set. An edx-proctoring attempt that has ended under step 3.3, including a `submitted` practice attempt the learner could reset, makes every counting component in the exam done, because submitting the exam is the learner's last step even when they left problems unanswered. An attempt that hasn't ended makes no component done.
   - Scored: a problem once it is submitted, because it is scored on submission; an ORA whose active submission has a `submissions.models.Score` row, read directly like `Submission` in one query with `submission__in` the active submissions; or any other type with `StudentModule.grade` set.

5. Combine the component answers into the four fields:
   - `accepts_learner_work` and `attempted` each ask whether any component qualifies. Each is true when any component is yes, unknown when no component is yes but at least one is unknown, and false when every component is no.
   - `all_learner_work_done` and `all_scored` each ask whether every component qualifies. Each is false when any component is no, unknown when no component is no but at least one is unknown, and true when every component is yes.

6. Keep the check read-only. `StudentModule`, `Submission`, `Score`, `AssessmentWorkflow`, and `ProctoredExamStudentAttempt` are read directly through their models rather than through their packages' APIs, because those APIs write on read. Never bind a block as the learner (no `get_block_for_descriptor` and no `FieldDataCache`). Don't call any of these, because each one writes:
   - `submissions.api.get_submissions`, which creates a `StudentItem`
   - `anonymous_id_for_user`, which creates an `AnonymousUserId`
   - `openassessment.workflow.api.get_workflow_for_submission`, which updates the workflow from its assessments as it reads it
   - the `edx_proctoring.api` read functions: `get_current_exam_attempt` and `get_exam_attempt_by_id` mark an expired attempt as timed out when they read it

   `get_course_blocks` makes one write of its own: the first time it runs for a learner who has no selection for a randomized library block, `ContentLibraryTransformer` saves a selection and emits `edx.librarycontentblock.content.assigned`. The progress tab's grade read and `calculate_progress_for_learner_in_course` already make that same selection for the same learner, so the check accepts that write.

7. Tests: warm the block structure before asserting the read-only rule. Then fail the test on any INSERT, UPDATE, or DELETE captured with `CaptureQueriesContext`, and on any call to `eventtracking.tracker.emit`. Beyond the AC, cover these cases:
   - a learner with no `AnonymousUserId` row in the course
   - an individual extension set with `edx_when.api.set_date_for_block(..., user=learner)` while `crum`'s current user is a staff member who has no extension
   - an exam subsection whose problems are locked for an audit learner, in a course with `exams_ida` on, where the lock wins and the check reports no
   - a practice exam with an `onboarding_reset` row and a newer `created` row, where the newer row decides
   - an ORA in `manual` mode whose peer step has a blank due date
   - one subsection and fifty subsections checked in one call make the same number of database queries, asserted with `assertNumQueries`, and `get_course_blocks` runs once per call

**Files to create and modify**

| File | Change |
| --- | --- |
| lms/djangoapps/course_home_api/progress/api.py | modified: add SubsectionSubmissionState and get_subsection_submission_states() |
| lms/djangoapps/course_home_api/progress/tests/test_api.py | modified: add a ModuleStoreTestCase class for get_subsection_submission_states() |

**Additional context**

- This ticket's rules for problems and ORA, in step 3, supersede #757 section 1 where the two differ.
- Prior art for reading ORA dates and steps from the block structure: `get_ora_as_assignments` in `lms/djangoapps/courseware/courses.py`. Prior art for the exam branch: `MilestonesAndSpecialExamsTransformer` in `lms/djangoapps/course_api/blocks/transformers/milestones.py`.
- The platform already imports these packages directly: `submissions.models.Submission` in `lms/djangoapps/grades/management/commands/recalculate_subsection_grades.py`, `edx_proctoring.models` in `lms/djangoapps/instructor/views/api_v2.py`, and ORA's `openassessment.data` in `lms/djangoapps/instructor/ora.py`. `openassessment.workflow.models` is a new direct import.

</details>
