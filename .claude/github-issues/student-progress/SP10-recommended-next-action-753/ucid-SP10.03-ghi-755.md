# [FE] Build Display of Recommended Next Action

GitHub: https://github.com/openedx/openedx-core/issues/755 (#755, OPEN)
Cached: 2026-09-21

## User Story
As a learner, I want to know what my recommended next action is in my CBE course in order to maintain momentum in learning and skill demonstration without having to figure this out myself or have someone tell me.

## Description
This ticket implements the Recommended Next Action notice inside the right hand CBE progress panel that goes in the ProgressTabRelatedLinksSlot.

This implementation will call the endpoint built in #754. If the `reason` listed in that endpoint's response is:
- `retry_available`, then the first word in the sentence should be "Retake"
- `not_started`, then the first word in the sentence should be "Take"
- Anything else, then do not show the Recommended Next Action notice.

Next in the sentence should be the name of the subsection, which links out to it in the platform.

Then the sentence should say "and score XX% <y> in order to achieve mastery."

Therefore, the sentence displayed in the "RECOMMENDED NEXT ACTION" notice will say: "Take/Retake <Subsection Name/Link> and score <threshold> in order to achieve mastery."

## Context
- Corresponding architecture spike: #757
- Frontend counterpart to #754

## Notes for drafting
Context gathered from the pre-handoff checks of #754 and SP10.05 (2026-10-06). The decisions below are recorded in #754's cache file; check it for the current wording before drafting.

### The backend contract this ticket renders (#754)
- Every response has a top-level `reason`. `next_action` is present for `retry_available` and `not_started`, and null for `no_criteria_in_course`, `all_demonstrated`, `nothing_openable`, and `nothing_actionable`. A response with no recommendation is still a 200.
- `next_action` carries `course_id`, a ready-to-use learning MFE `url`, `subsection` (`id`, `display_name`), and `criteria[]`. Each criterion has `criterion_id`, `tag_id` (integers, matching #733 and #738), `competency_name`, `status` (null when the learner has no status row), and `rule` (`rule_type`, `rule_payload`).
- `criteria[]` lists only the recommended subsection's criteria that aren't Demonstrated and aren't suppressed by a demonstrated ancestor group or competency. `criterion_id` and `tag_id` are there so the panel can link the recommendation to the criterion and competency cards it already renders.
- When `next_action` is null, the agreed fallback is the course's existing resume link. No extra payload fields come from Figma.
- The endpoint follows #738's caller rules: a learner sees their own result, and course staff viewing a specific learner, or masquerading as one, see that learner's result.
- Group and competency statuses roll up asynchronously, so right after a learner demonstrates one subsection in an OR group, an untouched sibling may briefly still be recommended. #754 accepts this.

### Product behavior worth knowing when writing the UI states
- `nothing_actionable` covers three situations the panel can't tell apart: a submission is awaiting grading, the learner can't retry, or the system can't tell whether a retry is possible (for example LTI). Copy for it has to fit all three.
- ORA doesn't accept a new submission once graded. A graded ORA becomes retryable only after staff reset the learner's state, so `retry_available` will mostly point at problems.

### Related tickets
- #754: the backend endpoint. SP10.05 (no GitHub issue yet): the "can submit now" check #754 uses.
- #738 and #733: the criteria and status reads the same right-hand panel already renders from.
- The Student Progress panel ships as a frontend-app-learning plugin (see the epic's sibling frontend tickets for the established pattern).
