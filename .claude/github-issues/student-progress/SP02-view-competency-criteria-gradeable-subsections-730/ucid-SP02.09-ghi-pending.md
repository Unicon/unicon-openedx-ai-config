# [FE] Let the operator choose to replace Course Grade Slot with CBE Progress

GitHub: not yet filed. Depends on #734 and #828.

## User Story
As a site operator, I want to be able to have the Grade summary replaced with CBE Progress for courses that have competency criteria while courses without competency criteria still show the Grade summary, so that neither students of CBE courses nor students of traditional courses get confused about their overall progress.

## Description

This ticket adds a site-wide operator setting that decides where #734's competency criteria panel goes on the Progress tab: above the stock Grades card (the default content of `ProgressTabCourseGradeSlot`), or in place of it. The default is "in place of".

In "in place of" mode:
- If #733 returns competency criteria for the course, the learner sees the competency criteria panel instead of the Grades card.
- If #733 returns an empty response, the learner sees the Grades card as usual.
- While #733's response is loading, the slot shows nothing, so learners in competency courses don't see the Grades card appear and then disappear.
- If the request to #733 fails for any reason, including a 404 when #733's route isn't deployed, the learner sees the Grades card.
- If the course has criteria but none of them are on subsections this learner can see, the slot stays empty.

The Grade summary and Detailed grades sections below the Grades card don't change in either mode.

The setting lives in #828's Tutor plugin and takes effect when the MFE image is rebuilt.

## Context
Blocked by #733, #734, and #828.

## Notes for drafting

### Known scope, decided during #734's pre-handoff check

- #734 renders the competency criteria panel above the stock "Grades" card, the default content of `ProgressTabCourseGradeSlot`. The Figma shows the panel with no Grades card, which is the "in place of" layout this ticket adds.
- The operator chooses between "above" and "in place of". "In place of" uses `PLUGIN_OPERATIONS.Wrap` on the slot's `default_contents`, with a wrapper that renders the stock Grades card only in courses with no competency criteria. That wrapper needs #734's check against #733's endpoint, which is why this ticket follows #734.
- Extends #828's data-driven Tutor slot mapping rather than rewriting it.
- frontend-app-learning#1905 moves plugin slots to frontend-base's `Slot` API, so the `PLUGIN_OPERATIONS.Wrap` mechanism may change before this ticket is built.

### Decisions from the pre-handoff check

- What "in place of" replaces: exactly the default content of `ProgressTabCourseGradeSlot` (https://github.com/openedx/frontend-app-learning/tree/release/ulmo/src/plugin-slots/ProgressTabCourseGradeSlot), which is the `CourseGrade` card headed "Grades" (or "Grades and Credit"). "Grade summary" and "Detailed grades" live in a different slot, `ProgressTabGradeBreakdownSlot`, and stay on the page. The `CourseGrade` card also carries the current and passing grade bar, the letter-grade ranges, credit eligibility, and the audit learner's "Unlock to view grades" upgrade banner, so all of those go away with it in "in place of" mode. Confirmed in frontend-app-learning `CourseGrade.jsx`. Defaulted without a question: this loss is accepted and documented for operators as the trade-off of "in place of".
- Condition that replaces the card: the course qualifies when #733's response is non-empty, and doesn't qualify when #733 returns empty arrays. #733 is empty when the course has no course-level CompetencyCriteriaGroup with unarchived criteria: none were authored, or every criterion or group is archived, or every criterion's tag, tag ancestor or taxonomy is archived, or the taxonomy is disabled, or the course has no catalog CourseRun row. This is one course-level answer, the same for every learner, and the same check #734 uses to decide whether to render. The wrapper needs only #733's response to decide.
- Empty panel: a qualifying course can still give this learner an empty panel. #733's response is non-empty, but after #734 joins the criteria to the learner's course outline, nothing is left. That happens only when every criterion sits on a subsection the learner can't know exists (staff-only, content-group restricted, or deleted). Unreleased subsections don't cause it, because the Outline API includes them. In that case the slot stays empty, and the stock Grades card is not shown.
- Loading and failure: in "in place of" mode, the slot stays empty until #733 answers, then shows either the panel or the stock Grades card. Any #733 failure, including a 404 when #733's route isn't deployed, shows the stock Grades card. Failing open matters because #734 itself renders nothing on failure.
- Timing and mechanism: write the ticket now, with the Description and AC in outcome terms only. Technical Details names the Frontend Plugin Framework's `PLUGIN_OPERATIONS.Wrap` as today's mechanism, flagged as likely to change. frontend-base's accepted ADR 0011 ("No slot wrapping operation") drops `Wrap`. Its replacement is a custom layout that filters `useWidgets()` (`byId()`, `withoutId()`), so frontend-app-learning#1905 will change the mechanism. #1905 is blocked on #1946 and has no timeline. Adolfo's comment on #828 also says the plugin may be built into `tutor-mfe` after #1905 rather than shipping its own Tutor plugin.
- Defaulted without a question: the choice is one site-wide Tutor setting. Its default is "in place of" (decided by the architect), matching the Figma. Because #734 ships with "above", a site upgrading to the release with this ticket loses the Grades card in its CBE courses without changing any setting, so the operator docs and release notes call this out. Per-course choice is out of scope. In staff view, staff see what the learner sees. The plugin's `example.env.config.jsx` shows the "in place of" registration for operators who don't use Tutor. The AC use Gherkin scenarios for what learners see, plus a checklist for the setting and the docs.
- Naming: "Grade summary" in the title and User Story names the wrong component. The replaced element is the "Grades" card. "CBE Progress" names nothing that exists. #734 calls it the competency criteria panel. The title and User Story are the architect's to reword.
- Implementer-owned: the setting's name and value spellings, what an unknown value does, and react-query caching. The wrapper and #734's panel share one #733 request through the same react-query key.
- Out of scope: choosing the layout per course, changing the Grade summary or Detailed grades sections, and the frontend-base migration (frontend-app-learning#1905), which will change how the replacement is wired.
