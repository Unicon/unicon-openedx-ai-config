# [BE] GET Recommended Next Action for CBE Learner in Course

GitHub: https://github.com/openedx/openedx-core/issues/754 (#754, OPEN)
Cached: 2026-09-21

## User Story
As a learner, I want to know what my recommended next action is in my CBE course in order to maintain momentum in learning and skill demonstration without having to figure this out myself or have someone tell me.

## Description
This ticket implements the design proposed in #757. It is a learner-facing endpoint that takes in the course and the learner and returns the recommended next action for that learner.

This is the algorithm that will be used to calculate the Recommended Next Action:
1. Given a course and a learner.
2. Find every subsection in the course that carries a competency criterion.
3. Remove from that set:
   - Any subsection the learner can't currently open or act on right now: unreleased, prerequisite-gated, past its due date, graded content locked for the learner's enrollment track, or otherwise unavailable.
   - Any criterion whose ancestor group (at any level), or whose competency, already reports "Demonstrated" for this learner, even when that specific criterion has no status row of its own. This is what keeps an already-satisfied OR group (for example, the duplicate-subsection workaround, once one duplicate is demonstrated) from still recommending its untouched siblings. A competency demonstrated in another course counts.
4. Split what's left into two groups:
   - **Retry candidates:** the learner's status on this subsection's criterion isn't "Demonstrated," the subsection's re-attempt state is retryable, and no resubmission is already awaiting grading. A subsection whose re-attempt state is unknown or not retryable is not a retry candidate, but it doesn't fall into "not-started" either, since it does have a status row; it simply isn't recommended.
   - **Not-started candidates:** the learner has no status row on this subsection's criterion, and no submission or attempt has been recorded against it yet. This keeps a subsection whose submission is still awaiting grading from being mistaken for one the learner hasn't touched at all.
5. If any retry candidates exist, recommend the one that comes chronologically first in the course outline (section order, then subsection order). Otherwise, if any not-started candidates exist, recommend the one that comes chronologically first in the course outline. Otherwise, there's no recommendation.
6. Return, for the selected subsection: its display name, a ready-to-use navigation URL, and, for each of its criteria that is not "Demonstrated" and not removed in step 3, the criterion id, competency tag id, competency name, status (null when the learner has no status row), and rule.

The response payload will be something to the effect of this:
```json
{
  "next_action": {
    "course_id": "course-v1:Org+Course+Run",
    "url": "https://<learning-mfe>/course/<course_id>/<subsection_id>",
    "subsection": {
      "id": "block-v1:Org+Course+Run+type@sequential+block@abc123",
      "display_name": "Poetry Assignment 1"
    },
    "criteria": [
      {
        "criterion_id": 91,
        "tag_id": 41,
        "competency_name": "Writing Poetry",
        "status": "AttemptedNotDemonstrated",
        "rule": {
          "rule_type": "Grade",
          "rule_payload": { "op": "gte", "value": 0.75, "scale": "percent" }
        }
      }
    ]
  },
  "reason": "retry_available"
}
```

## Context
- Corresponding architecture spike: #757
- Frontend counterpart: #755
- Blocked by: UCID10.05 #TBD

## Notes for drafting

### Decisions from the pre-handoff check
- Scope: one ticket, two PRs, like #733 and #738: the openedx-core read plus the openedx-platform endpoint and ranking. The re-attempt state check (ORA, capa, unknown fallback) is split into a separate openedx-platform ticket, cached as ucid-SP10.05-ghi-pending.md until it has a GitHub issue; #754 depends on it.
- Core read input: `course_key`, reusing #733's course walk (so #733's archived and disabled exclusions apply).
- Endpoint URL: match openedx-platform's convention for LMS djangoapp APIs: the app mounts under `api/<app_name>/` in `lms/urls.py` with a version segment, and course-scoped paths put the resource before the course key (`course_home_api` uses `progress/{settings.COURSE_KEY_PATTERN}`). For example `api/<app_name>/v1/next-action/<course_key>`; the app name follows from the new djangoapp's name.
- Placement: the platform endpoint and ranking live in a new LMS djangoapp, created by #754, for CBE learner features.
- Dead ends are excluded: a subsection is recommendable only if its graded component accepts a submission from this learner now. Past-due not-started subsections and audit content-gated subsections are excluded; a retry whose resubmission is already awaiting grading is excluded.
- Reason codes (collapsed set): `reason` is always top-level, never inside `next_action`. Values: `retry_available`, `not_started`, `no_criteria_in_course`, `all_demonstrated`, `nothing_openable`, `nothing_actionable`. `nothing_actionable` covers retry state unknown, awaiting grading, and retries exhausted (attempts used up or submission window closed).
- Empty result: a response with no recommendation is a successful 200 response with `next_action` set to null and a top-level `reason`.
- Re-attempt state, supplied by the re-attempt check ticket, is one of three values: retryable, not retryable, or unknown (content types the check can't evaluate, such as LTI).
- Related tickets for Technical Details' additional context (the architect kept them out of Context): #733 (criteria read, `api/cbe/` mount, archived and disabled exclusions), #738 (status read, shared learner resolver, caller permissions), #642 (learner status tables, not merged), and #699, #643, #701 for real data end to end.
- Re-attempt check outcomes (from SP10.05's pre-handoff check, 2026-10-06): an ORA is retryable only after a staff reset, since ORA doesn't accept a new submission once graded. If one component in a subsection is awaiting grading and another accepts a submission, the subsection is still recommendable, so step 4's "no resubmission is already awaiting grading" applies per component. The re-attempt check lives in the existing `lms/djangoapps/course_home_api/progress/` app because it isn't CBE-specific, so #754 creates the new LMS djangoapp for CBE learner features itself, for its endpoint and ranking.
- Precedence: when both `nothing_openable` and `nothing_actionable` apply, `nothing_actionable` wins.
- Callers: full parity with #738. The learner sees their own result; course staff can view a specific learner; staff masquerading as a specific learner see that learner, masquerading as a role see their own; others get 404; no learner identifier in the response. Openability, re-attempt state, and pending submissions are computed for the target learner, not the staff requester. Reuse #738's shared learner resolver.
- Ordering: "chronologically first in the course outline" means outline position (section order, then subsection order), not due date.
- `criteria[]`: only the recommended subsection's criteria that are not Demonstrated and not suppressed by a demonstrated ancestor group or competency. `status` is null when there is no status row. Each item includes `criterion_id` and `tag_id`, as #733 and #738 do.
- Suppression: a competency demonstrated in another course suppresses this course's criteria for it, and "enclosing group" means any ancestor group. `all_demonstrated` means "nothing left to demonstrate in this course".
- Course final-grade criteria can't happen in the MVP (criteria only target subsections); the ticket doesn't need to mention them.
- Roll-up lag: accepted and stated in the ticket. Group and competency statuses roll up asynchronously (ADR 0004), so an untouched OR sibling may briefly still be recommended right after another sibling is Demonstrated. Same tradeoff #738 accepts.
- Payload: no extra fields from Figma. When `next_action` is null (except `no_criteria_in_course`), the response also carries a top-level `resume_url` for the target learner, computed the way the course home "Resume course" button does (`completion.utilities.get_key_to_last_completed_block` plus `jump_to`, or the course's first block when there's no completion data), so #755 can show a resume-link fallback without a second request. Decided in #755's pre-handoff check (2026-10-06), on the condition that it's a small addition; if it isn't, drop it and #755 hides the notice instead.
- Hidden scores (from #755's pre-handoff check): skip a retry candidate whose score is hidden from the target learner by the course's show-correctness setting, and move on to the next candidate, so a "Retake" recommendation never reveals a result #739 and #740 mask as "Available".

### Research notes for drafting (openedx-platform, from the pre-handoff check)
- Target-learner openability: `get_user_course_outline` (learning_sequences/api/outlines.py) runs per target user and covers release dates, prerequisites, hide-after-due, and personalized due dates (edx-when). Pass the learner, not the staff viewer, since `can_see_all_content` bypasses processors for staff. Audit content type gating appears not to be covered (inferred).
- ORA retry: `allow_resubmission` (openassessment/xblock/utils/allow_resubmission.py) has no lightweight entry point; checking another learner means loading the block as that learner (inferred). Belongs to the new re-attempt ticket.
- capa retry (confirmed from code): `ProblemBlock.closed()` is true when attempts are used up or the problem is past its close date, which is the due date (or course end when there's no due date) plus any grace period. The due date is always enforced, contrary to #757 section 1.
- Awaiting grading vs not started: `PersistentSubsectionGrade.first_attempted` is not set for an ungraded ORA submission; use the submissions API or the ORA workflow instead.
- Exams: a submitted timed or proctored exam can't start a new attempt even if capa shows attempts left (medium confidence); treat it as not retryable.
- URL: no legacy courseware branch at HEAD; `make_learning_mfe_courseware_url` (openedx/features/course_experience/url_helpers.py) builds the learning MFE link.
- Data dependencies: criteria models are on upstream main (#800); learner status tables (#642) are not merged. #613 is still open.

### Left for drafting
- (implementer) Combining re-attempt state across component types in one subsection; ordering and caching of the re-attempt checks.
