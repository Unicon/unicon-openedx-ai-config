# [BE] Compute whether a learner can re-attempt a subsection

GitHub: pending (no issue yet)
Cached: 2026-10-06

## User Story
As a learner, I need Open edX to know whether or not I can re-attempt a subsection so that it can provide me with my recommended next action in my CBE course in order for me to maintain momentum in learning and skill demonstration without having to figure this out myself or have someone tell me.

## Description
This ticket implements the re-attempt check function from the design proposed in #757 in openedx-platform which is called on by #754's endpoint. Given a learner and a subsection, it returns the subsection's re-attempt state: retryable, not retryable, or unknown. It also reports whether the learner has a submission awaiting grading, so #754 can tell "awaiting grading" apart from "not started".

How each content type is checked:
- ORA: ORA's own resubmission check.
- Problems: attempts used against the maximum, and whether the problem is past due.
- Timed or proctored exams: not retryable once submitted.
- Anything else (for example LTI): unknown.

## Context
- Corresponding architecture spike: #757
- Blocks #754

## Notes for drafting
Split out of #754 during #754's pre-handoff check (2026-10-06), because keeping it in #754 put that ticket at about 4 to 6 developer-days. #754 keeps the openedx-core read plus the openedx-platform endpoint and ranking (about 2.5 to 3 days); this ticket owns the re-attempt state check (estimated about 2 days, the biggest research risk). #754 consumes its result.

### Decisions already made on #754 that bind this ticket
- Placement: lives in the same new LMS djangoapp for CBE learner features as #754's endpoint and ranking.
- Re-attempt state has three values: retryable, not retryable, unknown (from #757 section 1). Content types the check can't evaluate (LTI, for example) report unknown.
- Dead ends are excluded from recommendation: a subsection is recommendable only if its graded component accepts a submission from this learner now. That covers past-due subsections, audit content-gated subsections, and a retry whose resubmission is already awaiting grading.
- #754's `reason` codes: retry state unknown, awaiting grading, and retries exhausted (attempts used up or submission window closed) all map to `nothing_actionable`. Because #754 doesn't distinguish those three outcomes in its response, this ticket only needs to give #754 enough to sort each subsection into retry candidate, not started, or excluded.
- Everything is computed for the target learner, not the staff requester (full #738 caller parity, including masquerade).
- Not started vs awaiting grading: #754's not-started group requires no status row and no submission or attempt recorded, so a submission awaiting grading must be detectable.

### Decisions from the pre-handoff check
- Meaning of the check: for one learner and one subsection, it answers two things. First, whether the subsection's graded content accepts a submission from this learner now (retryable, not retryable, or unknown). Second, whether the learner has submitted or attempted anything there at all, graded or not. It applies to any subsection, not only retries; #754 uses it for both its retry and not-started groups.
- ORA: an ORA accepts a submission now only if the learner has no active submission (never submitted, or staff reset their state) and the ORA's submission window is open. A graded ORA is not retryable unless staff reset it. Detect this with a read-only query on the submissions package's models (`Submission.objects` filtered by the learner's anonymized id, course, and ORA item id, `.exists()`), not `submissions.api.get_submissions`, which writes a `StudentItem` row on read. `Submission.objects` already excludes submissions soft-deleted by a staff reset. This depends on the package's models rather than its `api` module, accepted until someone asks otherwise. Don't load the ORA block or call `allow_resubmission`.
- ORA vs CBE retakes (to raise with product, out of scope here): ORA itself doesn't allow a new submission after grading. In practice a learner can retake ORA content only after a staff "reset learner state" or through the duplicate-subsection OR-group workaround.
- Problems: retryable while attempts remain and the problem isn't closed (due date plus any grace period, or course end when there's no due date), using the learner's own dates.
- Exams: any edx-proctoring attempt on the subsection (started, timed out, submitted, error) means not submittable, overriding what the problems inside report. Courses whose exams run on the edx-exams service report unknown for exams.
- Other scored content the check can't evaluate (LTI, for example) reports unknown. A not-started subsection of that kind is still recommendable by #754 unless it's past due; "attempted" there means a score has been received.
- Audit content gating lives here: a graded component locked for the learner's enrollment track does not accept a submission. The platform's `ContentTypeGatingService` reads the user from the current request, so evaluate its predicate for the target learner instead.
- Mixed state: if one component is awaiting grading and another accepts a submission, the subsection is recommendable (any accepting component wins). #754's step 4 wording "no resubmission is already awaiting grading" has to be read per component accordingly.
- Components that count: scored components the learner can see. HTML and video are ignored, as are components hidden by a cohort or not picked from randomized library content.
- Errors: if a component's check fails, it reports unknown for that component and logs the failure.
- The new LMS djangoapp: this ticket creates it, since it lands before #754. The app name is the implementer's to propose; it also sets #754's URL prefix (`api/<app_name>/v1/...`).
- Read-only: the check must not write anything as the learner. No attempt recorded, no completion marked, no `StudentModule` row created, and no analytics or tracking event emitted, because the learner didn't open anything. It runs on every progress panel load and whenever staff view a learner.

### Platform research
- capa (confirmed from code): `ProblemBlock.closed()` (xmodule/capa_block.py) is true if `used_all_attempts()` or `is_past_due()`. `close_date` is the due date, or the course end when there is no due date, plus the grace period when one is set. So the due date is always enforced. This contradicts #757 section 1's "no due-date logic" for capa.
- ORA (confirmed from code, ora2 7.0.0 locally; platform pins 7.1.0, assumed unchanged): `allow_resubmission` (openassessment/xblock/utils/allow_resubmission.py) returns false once the workflow is `done` or `cancelled` (`has_been_graded`) or while a staff grading lock is held. Its grace period is measured from the submission's creation. It backs the learner's "reset my submission" button, which works only before grading. This contradicts #757's "unlimited resubmission up to a due date".
- ORA staff reset (confirmed from code): "delete learner state" goes through `reset_student_attempts(..., delete_module=True)` (lms/djangoapps/instructor/enrollment.py) to ORA's `clear_student_state`, which calls `submissions.api.reset_score(..., clear_state=True)`. That soft-deletes the submissions, and `Submission.objects` excludes deleted rows, so `get_submissions` no longer returns them.
- `get_submissions` creates a `StudentItem` row (a bookkeeping record: anonymized learner id, course, item) the first time it reads a learner's item (confirmed from submissions/api.py `_get_or_create_student_item`). That write violates the read-only decision. The submissions package has no public read-only function that returns a learner's graded and ungraded submissions for one item (confirmed).
- Awaiting grading (confirmed from code): `PersistentSubsectionGrade.first_attempted` is not set for an ungraded ORA submission. capa attempts are in `StudentModule` state.
- Exams: edx-proctoring's `create_exam_attempt` refuses a new attempt once one exists (medium confidence on re-entry behavior). The per-course waffle flag `exams_ida` (openedx/core/djangoapps/course_apps/toggles.py) routes exams to the edx-exams service, which leaves no local edx-proctoring attempt rows (inferred).
- Audit gating (confirmed from code): `ContentTypeGatingService._content_type_gate_for_block` (openedx/features/content_type_gating/services.py) treats a component as gated when it is graded, scored, weight not 0, and `has_access(user, 'load', ...)` fails with `incorrect_user_group`. It takes the user from the request via `crum`. ORA appears to be gated for audit learners (inferred: its weight defaults to None).
- Learner's own dates (confirmed from code): `get_course_blocks(user, ...)` with the default transformers applies edx-when's `DateOverrideTransformer(user)`, so `due` reflects personalized and relative dates.
- Neither #643 nor #701 creates a platform djangoapp (confirmed from their tickets). #643 is openedx-core only; #701 adds to the existing `lms/djangoapps/grades/`.

### Open for drafting
- (implementer) Precedence between unknown and not retryable when combining components. #754 can't observe the difference, since both map to `nothing_actionable`.
- (implementer) Caching inside the check. Walking the outline in order and stopping at the first hit is #754's loop, not this ticket's.
- (implementer) How capa gets the learner's effective due date: `get_course_blocks`, edx-when directly, or binding the block as the learner. It must mirror `closed()`.
