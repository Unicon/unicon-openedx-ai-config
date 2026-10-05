# [FE] Display Subsection Competency Statuses for Learner in Course

GitHub: https://github.com/openedx/openedx-core/issues/739 (#739, OPEN)
Cached: 2026-09-21

## User Story
As a learner, I need to know my competency mastery status for each subsection assignment in my course in order to understand what I need to work on improving.

## Description
This ticket implements the oval status indicator display for each subsection assignment in the competency cards on the Course Progress page.

This implementation will call the endpoint built in #738 to get the competency statuses and the Progress API `/api/course_home/v1/progress/{course_key}` to get the subsection percentage scores.

For each subsection, if the learner's competency status on it is:
- Nonexistent, then display the "Available" oval in blue/white with the corresponding icon.
- AttemptedNotDemonstrated, then display the "Not Demonstrated" oval in red with the corresponding icon.
- PartiallyAttempted, then display the "Partially Attempted" oval in blue with the corresponding icon.
- Demonstrated, then display their percentage score on this assignment in the oval in green with the checkmark icon.

## Context
- #738 is the backend counterpart to this ticket.
- Blocked by #734.

## Notes for drafting

Figma link: https://www.figma.com/design/VqDdtf3NOsUihle6SNS6Kw/-Course-Level----Student-Progress?node-id=983-3817&t=txS1ECYsvaWv8KoX-4

Carried over from #738's pre-handoff check and the lookups behind it (2026-10-05):

- #738's response, per its decisions: `student_competency_statuses` entries keyed by `tag_id` and `student_competency_criteria_statuses` entries keyed by `criterion_id`, each with the stored `status` string. The ids match #733's `tags[].id` and `criteria[].id`. An item with no status row is absent from the response, and the frontend shows it as "Available". The response carries no learner identifier.
- Status vocabulary (#768, accepted by UXD on 2026-10-01): no row = Available, `PartiallyAttempted` = Partially Attempted (competencies only), `AttemptedNotDemonstrated` = Not Demonstrated (subsections only), `Demonstrated` = Demonstrated. `PartiallyAttempted` is legal for a criterion in the schema but nothing produces it today. #768's last comment, on whether the sunburst legend needs icons and not just color, is unanswered; it is UX only.
- Status is stored per criterion, which is a subsection and competency pair. A subsection tagged with two competencies has two criteria, so it can show two statuses.
- Confirmed in frontend-app-learning: the Progress tab plugin slots `ProgressTabGradeBreakdownSlot` and `ProgressTabCourseGradeSlot` (`src/plugin-slots/`) pass no `pluginProps`, so the plugin can't read the page's progress data and must call the Progress API itself.
- Confirmed in openedx-platform: the Progress API (`lms/djangoapps/course_home_api/progress/serializers.py`) returns `section_scores`, a list of chapters, each with `subsections` carrying `block_key` (the subsection usage key), `num_points_earned`, `num_points_possible`, and `percent_graded`. It is a list, not a map keyed by usage key, so the client indexes it. The staff route is `/api/course_home/v1/progress/{course_key}/{student_id}`.
- Inferred, not verified: #733's criterion `object_id` matches the Progress API's `block_key` string for the same subsection. Confirm before relying on it as the join.
- Staff parity (#738 decision): course staff viewing a specific learner (`/progress/{course_key}/{student_id}`) see that learner's statuses, and so do staff masquerading as a specific learner. The frontend passes the route's target user id to #738 when there is one. Masquerade needs no frontend work, because the server resolves it from the session.
- #734 left `targetUserId` out of its query keys because neither of its responses depended on the viewed learner. #738's response does, so its query key must include the target learner.
- #734 shows a placeholder row for a criterion whose subsection isn't in the viewer's course outline. Decide how a status for such a criterion is shown.
- Statuses are rolled up asynchronously (ADR 0004), so a subsection can briefly show Demonstrated while its competency still shows an older status. This lag is accepted.
- CCX courses are out of scope for MVP.

Facts confirmed during #739's pre-handoff check:

- Subsection grades can go down after a reset, a default rescore, a grade override, or a resubmission when `only_if_higher` is false (`lms/djangoapps/grades/models.py:455-481`, `grades/api.py:85-96,137-139`). #699 (ticket text) judges a criterion on the platform's override-adjusted fraction and never lowers a stored status. So a Demonstrated criterion can sit beside a current score below its rule.
- The Progress API's `percent_graded` comes from the same override-adjusted `graded_total` the grade-change signal carries (`grades/subsection_grade.py:171-172,197-225`). It is a 0 to 1 fraction rounded to 4 decimals.
- The Progress API returns `percent_graded` regardless of course settings. The host hides a subsection's score in its Detailed grades table unless that subsection's `show_grades` is true (`frontend-app-learning/src/course-home/progress-tab/grades/detailed-grades/DetailedGradesTable.jsx:20-27`). `show_grades` follows the show-correctness setting, the due date, and the viewer's staff access (`grades/subsection_grade.py:60-71`). Subsections set to `never_but_include_grade` are left out of `section_scores` entirely (`course_home_api/progress/views.py:190-200`).
- The host loads its own Progress API data before the plugin slots render (`frontend-app-learning/src/tab-page/TabPage.tsx:83-94`), so the plugin's call is a second request to an expensive view. No cheaper learner-accessible per-subsection score API exists.
- A tag's `object_id` is written as `str(content_key)` (`openedx-platform/openedx/core/djangoapps/content_tagging/api.py:225`) and the Progress API's `block_key` is `str(subsection.location)`. Equality is inferred, not verified on a devstack. With the masking decision below, this join now decides whether any status is shown, not only the percentage.
- Changing masquerade reloads the page (`frontend-app-learning/src/instructor-toolbar/masquerade-widget/MasqueradeWidgetOption.tsx:53`), so query keys don't need masquerade state.
- #768 icons: Available is an empty circle, Partially Attempted a half-filled circle, Not Demonstrated a circle with a minus, Demonstrated a circle with a check. "Statuses never rely on color alone." Figma: "Reduced Scope frames" in https://www.figma.com/design/VqDdtf3NOsUihle6SNS6Kw/-Course-Level----Student-Progress?node-id=983-3816. #768 doesn't cover score display, colors, placement, or hidden scores.
- No plugin repo is checked out locally.

### Decisions from the pre-handoff check

- When a criterion is Demonstrated but the learner's current score no longer meets its rule, the Demonstrated oval still shows the current percentage. This is a known limitation: the oval can show a percentage below its own rule line. The frontend never compares the score to the rule and never recomputes the status.
- When the host would hide a subsection's score from this viewer (`show_grades` false), the oval shows "Available", whatever the stored status. Staff see real statuses wherever `show_grades` is true for them.
- Loading and failure: the panel waits for every request it started. If #733 or the outline fails, #734's behavior holds and the panel is hidden. If #738 fails, or the Progress API fails, #734's cards render with no ovals and the error is logged. A failure never falls back to "Available".
- Placeholder rows for hidden subsections get no oval.
- A subsection that #734 shows as a named row but that is missing from the Progress API's `section_scores` shows "Available", whatever its stored status. The plugin can't tell why a subsection is missing: the Progress API drops subsections set to "Never show individual assessment results, but show overall assessment results after due date" (`never_but_include_grade`, `openedx-platform/lms/djangoapps/course_home_api/progress/views.py:190-200`), and it builds `section_scores` from the learner's own course structure (`lms/djangoapps/grades/course_grade.py:249-257`), which can leave out other subsections too. Neither the Progress API nor the learning_sequences outline exposes a subsection's show-correctness setting once it is dropped. "Available" never reveals a hidden result. Its cost is that a `never_but_include_grade` subsection never shows its status, even after its due date, which matches the Progress page itself.
- Only the Demonstrated oval shows a percentage. Not Demonstrated shows no score.
- One ticket, accepting about 2.5 developer-days.
- #739 builds the shared status hook (keyed by course and target learner) and an oval component supporting all four states. #740 reuses both.
- Defaults not asked, recorded from the experts' recommendations: a `PartiallyAttempted` criterion renders the Partially Attempted oval; an unknown status value shows no oval and is logged once; "Available" is used for unreleased and locked subsections too, per #768's vocabulary; the screen reader announces the status word, not only the number; #739 is blocked by #734 merged and #738's contract, develops against mocks, and verifies end to end once #738 is deployed; the plugin makes its own Progress API call, with passing the data through `pluginProps` upstream as a possible later contribution.
