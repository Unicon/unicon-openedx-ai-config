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
- Blocked by #743

## Notes for drafting
Context gathered from the pre-handoff checks of #754 and SP10.05 (2026-10-06). The decisions below are recorded in #754's cache file; check it for the current wording before drafting.

### The backend contract this ticket renders (#754)
- Every response has a top-level `reason`. `next_action` is present for `retry_available` and `not_started`, and null for `no_criteria_in_course`, `all_demonstrated`, `nothing_openable`, and `nothing_actionable`. A response with no recommendation is still a 200.
- `next_action` carries `course_id`, a ready-to-use learning MFE `url`, `subsection` (`id`, `display_name`), and `criteria[]`. Each criterion has `criterion_id`, `tag_id` (integers, matching #733 and #738), `competency_name`, `status` (null when the learner has no status row), and `rule` (`rule_type`, `rule_payload`).
- `criteria[]` lists only the recommended subsection's criteria that aren't Demonstrated and aren't suppressed by a demonstrated ancestor group or competency. `criterion_id` and `tag_id` are there so the panel can link the recommendation to the criterion and competency cards it already renders.
- When `next_action` is null (except `no_criteria_in_course`), #754 also returns a top-level `resume_url` for the target learner, and #755 shows a resume-link fallback. No other extra payload fields come from Figma.
- The endpoint follows #738's caller rules: a learner sees their own result, and course staff viewing a specific learner, or masquerading as one, see that learner's result.
- Group and competency statuses roll up asynchronously, so right after a learner demonstrates one subsection in an OR group, an untouched sibling may briefly still be recommended. #754 accepts this.

### Product behavior worth knowing when writing the UI states
- `nothing_actionable` covers three situations the panel can't tell apart: a submission is awaiting grading, the learner can't retry, or the system can't tell whether a retry is possible (for example LTI). The panel shows the resume-link fallback for it, so no per-reason copy is needed.
- ORA doesn't accept a new submission once graded. A graded ORA becomes retryable only after staff reset the learner's state, so `retry_available` will mostly point at problems.

### Related tickets
- #754: the backend endpoint. SP10.05 (no GitHub issue yet): the "can submit now" check #754 uses.
- #738 and #733: the criteria and status reads the same right-hand panel already renders from.
- The Student Progress panel ships as a frontend-app-learning plugin (see the epic's sibling frontend tickets for the established pattern).

### Decisions from the pre-handoff check
- No recommendation: when `next_action` is null, show a resume-link fallback using #754's `resume_url`, for `all_demonstrated`, `nothing_openable`, and `nothing_actionable`. For `no_criteria_in_course` the whole CBE panel is hidden (as in #734), so nothing shows. The fallback's copy comes from UX.
- Resume link source: #754 returns it, computed for the target learner the same way the course home "Resume course" button does (`completion.utilities.get_key_to_last_completed_block` plus `jump_to`, or the course's first block when there's no completion data). #755 does not call the Outline tab API: that would be a second, heavier request, and it computes the link for the requester, so staff viewing a learner would get their own position. If #754's implementer finds this is more than a small addition, the fallback is dropped and the notice is simply hidden when `next_action` is null.
- Threshold: show one threshold that satisfies every criterion in `criteria[]` (for example the highest "or better" value; if all criteria share one rule, that rule). If the rules can't be combined, or any rule type, op, or scale isn't recognized, drop the "and score ..." clause and log the unrecognized rule once, as #734's rule lines do. Wording for each op reuses #734's rule-line wording: `gte` "or better", `lte` "or lower", `eq` "exactly", with the percent formatted by `intl.formatNumber`.
- Hidden scores: #754 skips a retry candidate whose score is hidden from the target learner (the course's show-correctness setting), so a "Retake" never reveals a result #739 and #740 mask as "Available". "Take" reveals nothing. #755 needs no masking logic.
- Host: #755 builds the self-contained `RecommendedNextAction` component and places it inside #743's Course Progress card, so #755 is blocked by #743. The component catches its own render errors so a crash can't blank Focus Areas.
- Loading and errors: show nothing while loading; if #754 fails, show nothing and log the failure, matching #734 and #739.
- Staff viewing a learner: pass the route's `targetUserId` (`/course/:courseId/progress/:targetUserId/`) to #754 the same way #738 takes its optional learner id, and include it in the query key. The link opens courseware as the staff member, which is acceptable. Masquerade needs no frontend work.
- No separate "course has criteria" gate is needed before calling #754: #743 doesn't render the right-hand panel at all for a course with no criteria, so the component never mounts and never calls #754.
- Out of scope for MVP: a click-tracking event on the link, and scrolling to or highlighting the related competency cards via `criterion_id`/`tag_id`.
- Closing clause: "toward demonstrating <competency>" replaces the design's "in order to achieve mastery" (the architect's preference, matching the page's "Demonstrated" vocabulary). With several competencies in `criteria[]`, join their names with `intl.formatList` (locale-aware "A, B, and C"); the combined-threshold rule above already handles different rules. Examples: "Retake <link> and score 80% or better toward demonstrating Writing Poetry and Analysis." and, when rules can't combine, "Retake <link> toward demonstrating Writing Poetry and Analysis."
- Translation: each sentence variant (reason by op, plus the forms without a threshold, plus the fallback) is one whole translatable message with the link, threshold, and competency names as values, never fragments joined in code.

### For the UX Design placeholder (@illiphilli)
- Drop "You have N attempt(s) remaining"; #754 doesn't return attempts.
- Where the notice sits in the new Course Progress card, now that the Sections list is gone.
- The fallback's copy when there is no recommendation.
- Confirm the "Take" / "Retake" verbs ("Take" is the architect's own wording, not from the design).
- Update the sentence's closing clause from "in order to achieve mastery" to "toward demonstrating <competency>", matching the page's "Demonstrated" vocabulary. Account for a subsection with several competencies: their names are listed ("Writing Poetry and Analysis", "A, B, and C"), and when their thresholds can't be combined into one, the "and score ..." part is omitted. Examples: "Retake <link> and score 80% or better toward demonstrating Writing Poetry and Analysis." and "Retake <link> toward demonstrating Writing Poetry and Analysis."

### Open for drafting
- (implementer) Message structure: separate message ids per reason and op, or ICU `select` over whole sentences.
- (implementer) Freshness: after a learner follows the link, submits, and returns in the same session, the notice must not replay a stale cached recommendation (refetch on mount or a short stale time).
