# [FE] Display Competency Statuses for Learner in Course

GitHub: https://github.com/openedx/openedx-core/issues/740 (#740, OPEN)
Cached: 2026-09-21

## User Story
As a learner, I need to know my mastery status for each competency in my course in order to understand what I need to work on improving and how I can speak about my skills.

## Description
This ticket implements the oval status indicator display for each competency in the CBE progress cards on the Course Progress page.

This implementation will call the endpoint built in #738 to get the competency statuses.

For each competency tag serving as a card title, if the learner's status is:
- Nonexistent, then display the "Available" oval in blue/white with the corresponding icon.
- PartiallyAttempted, then display the "Partially Attempted" oval in blue with the corresponding icon.
- Demonstrated, then display the "Demonstrated" oval in green with the checkmark icon.

For each competency tag serving as a card subtitle, if the learner's status is:
- Nonexistent, then display "Available" after the pipe next to the tag name.
- PartiallyAttempted, then display "Partially Attempted" after the pipe next to the tag name.
- Demonstrated, then display "Demonstrated" after the pipe next to the tag name.

## Context
- #738 is the backend counterpart to this ticket.
- Blocked by #734 and #739.

## Notes for drafting

Figma link: https://www.figma.com/design/VqDdtf3NOsUihle6SNS6Kw/-Course-Level----Student-Progress?node-id=983-3817&t=txS1ECYsvaWv8KoX-4

Carried over from the #738 and #739 pre-handoff checks (2026-10-05):

- #738 returns `student_competency_statuses` entries keyed by `tag_id`, each with the stored `status` string. They cover the course's competency tags and their ancestor tags. #643 (OPEN) writes the ancestor rows by rolling status up through `Tag.parent` to the top of the taxonomy, so a parent tag with no criteria of its own, such as a #734 card heading, can still have a status.
- The competency status is the learner's overall, cross-course `StudentCompetencyStatus`, not a per-course-run status (#738 decision). A competency demonstrated in another course shows Demonstrated here before the learner attempts anything in this course. This was accepted knowingly.
- A competency can only be stored as `Demonstrated` or `PartiallyAttempted`. A database constraint rejects `AttemptedNotDemonstrated` at that level (ADR 0002). A competency with no status row is shown as "Available".
- #768 icons: Available is an empty circle, Partially Attempted a half-filled circle, Demonstrated a circle with a check. Statuses never rely on color alone. Figma: "Reduced Scope frames" in https://www.figma.com/design/VqDdtf3NOsUihle6SNS6Kw/-Course-Level----Student-Progress?node-id=983-3816.
- #733's tag lineage entries carry each ancestor's `id` and `value`, so the frontend can match an ancestor's status to its place in the lineage. A tag under an archived ancestor is treated as archived and is left out of both #733 and #738.
- #739 builds the shared status hook (keyed by course and target learner) and an oval component supporting all four states. #740 reuses both, which assumes #739 lands first.
- #739's loading and failure rules: the panel waits for every request it started; if #738 fails, the cards render with no ovals and the error is logged; a failure never falls back to "Available".
- Staff parity (#738 decision): staff viewing a specific learner, or masquerading as one, see that learner's statuses. The query key includes the target learner. Masquerade changes reload the page, so it needs no query-key entry.
- Roll-up is asynchronous (ADR 0004), so a subsection can briefly show Demonstrated while its competency still shows an older status. This lag is accepted.
- Criteria behind #734's placeholder rows (subsections the viewer can't see) still count in the competency's roll-up, so a competency status can reflect work the learner sees no row for.
- #743's Focus Areas sidebar (epic #742) also shows `StudentCompetencyStatus` per #768, so decisions here likely carry over to it.
- CCX courses are out of scope for MVP.

UX design screenshot shared by the architect on 2026-10-05 (the Progress tab with the sunburst, the Focus Areas sidebar, and the competency cards):

- Each card's title is a top-level competency tag ("Critical Thinking", "Communication", "Problem Solving"). Its status is a pill at the right end of the card header, with icon and label.
- Each sub-competency inside a card ("Analysis", "Written Communication") has a target icon, its name, a pipe, and the status label in small text, inside a single outlined pill tinted by status.
- Subsection rows sit under each sub-competency's rule line ("COMPLETE ALL OF THE FOLLOWING AT 80% OR BETTER"). A Demonstrated row shows a check and its percentage, for example "95%". Other rows show "Not Demonstrated" or "Available".
- The design never shows "Not Demonstrated" on a card title or a sub-competency, which matches the database constraint below.

### Decisions from the pre-handoff check

- If a subsection shows "Available" because the course hides its score (the #739 masking rule), the parent tag shows "Available" too.
- The mask reaches every ancestor: the tag that owns the masked criterion and every ancestor up to the top-level tag, wherever that tag appears on the page.
- Any criterion in this course whose score is hidden from the viewer masks the tags above it, whether or not the learner has submitted it. A criterion counts as hidden when it is a named row and #739 masks its oval (`show_grades` false, or missing from the Progress API's `section_scores`).
- Criteria behind #734's placeholder rows never trigger masking.
- The masking lives in one shared place: a pure function in the plugin's data layer, exposed through #739's shared hook. #739 builds the subsection rule, #740 adds the propagation to tags, and #743 and #745 read the same masked statuses so the page never contradicts itself.
- Staff viewing a learner, or masquerading as one, see the learner's masking, because the Progress API computes `show_grades` with the learner's staff access (`openedx-platform/lms/djangoapps/course_home_api/progress/views.py:217,303`).
- A masked tag shows "Available", the same as a masked subsection oval in #739, and looks exactly like a tag with no status row. A distinct "results not released yet" state is a possible UXD follow-up with @illiphilli, not part of #740.
- Defaults not asked, recorded from the experts' recommendations:
  - Placement, using #734's terms: every card heading, at any depth and with or without its own criteria, gets the status pill at the right end of the card header ("card title" in the Description). Every tag row with a target icon gets name, pipe, status ("card subtitle"). Breadcrumb ancestors show no status. A heading with no criteria of its own takes its status from `lineage[-2].id` of its child rows.
  - `AttemptedNotDemonstrated` gets no special handling and no AC, since the database forbids it for a competency.
  - A heading with no status row shows "Available" even when its rows have statuses (before #643 ships, or during the roll-up delay). The frontend never recomputes a status.
  - If #738 or the Progress API fails, headings get no pill and rows get no pipe or status, the error is logged, and nothing falls back to "Available". This extends #739's failure rule, because the mask can't be computed without the Progress API.
  - Known limitations to note in Technical Details, not fix: a heading's status rolls up child tags the card doesn't show, so "Partially Attempted" can sit above all-Demonstrated rows; masking covers only this course's criteria, so a competency can read Available here and Demonstrated on another course's page.
  - The AC state accessibility outcomes: a screen reader hears each tag with its status and not the pipe; the status is always in text; the small status text meets WCAG AA contrast against its tint; pills wrap on a phone.
  - The card model should carry each heading's and row's tag `id`, so statuses join by `tag_id`. If #734 isn't implemented yet, amend #734's Technical Details; otherwise #740 extends `buildCompetencyCards`. Not checked yet: whether #734 has a PR.
