# [FE] Let the operator choose to replace Course Grade Slot with CBE Progress

GitHub: https://github.com/openedx/openedx-core/issues/839 (#839, OPEN)

## User Story
As a site operator, I want to be able to have the Grade summary replaced with CBE Progress for courses that have competency criteria while courses without competency criteria still show the Grade summary, so that neither students of CBE courses nor students of traditional courses get confused about their overall progress.

## Description

This ticket adds a site-wide operator setting that decides where #734's competency criteria panel goes on the Progress tab: above the stock Grades card (the default content of `ProgressTabCourseGradeSlot`), or in place of it (replacement). The default is "Replacement".

In "Replacement" mode:
- If #733 returns competency criteria for the course, the learner sees the competency criteria panel instead of the Grades card.
- If #733 returns an empty response, the learner sees the Grades card as usual.
- While #733's response is loading, the slot shows nothing, so learners in competency courses don't see the Grades card appear and then disappear.
- If the request to #733 fails for any reason, including a 404 when #733's route isn't deployed, the learner sees the Grades card.
- If the course has criteria but none of them are on subsections this learner can see, the slot stays empty.

The Grade summary and Detailed grades sections below the Grades card don't change in either mode.

The setting lives in #828's Tutor plugin and takes effect when the MFE image is rebuilt.

## Context
Blocked by #733, #734, and #828.

## UX Design

@illiphilli, please add the UX design screenshot(s) and the Figma link for this ticket.

- Figma: TBD
- Screenshots: TBD

## Acceptance Criteria

The scenarios below use these terms:

- The Grades card is the card at the top of the Progress tab headed "Grades", or "Grades and Credit" in a course that offers credit.
- The Grades card's place is the position on the page where that card normally appears.
- A course with competency criteria is one that #733 returns criteria for. A course without competency criteria is one that #733 returns none for.
- In a course with competency criteria, the competency criteria panel also loads the learner's course outline.
- #734 specifies what the panel contains, including in staff view.

```gherkin
Scenario: A course with competency criteria shows the panel in place of the Grades card
  Given the site uses the "Replacement" layout
  And a course has competency criteria
  And at least one of its criteria is on a subsection the panel can show this learner, as #734 specifies
  When the learner opens the course's Progress tab
  Then the learner sees the competency criteria panel in the Grades card's place
  And the Grades card does not appear anywhere on the page

Scenario: A course without competency criteria shows the Grades card as usual
  Given the site uses the "Replacement" layout
  And a course has no competency criteria
  When the learner opens the course's Progress tab
  Then the learner sees the Grades card with everything it shows on a site without the plugin
  And the competency criteria panel does not appear

Scenario: The Grades card does not appear and then disappear while the page loads
  Given the site uses the "Replacement" layout
  And a course has competency criteria
  When the learner opens the course's Progress tab
  Then the Grades card's place stays empty until both #733's answer and the learner's course outline have arrived
  And the Grade summary and Detailed grades sections appear without waiting for either one
  And the Grades card is not shown at any point, before or after they arrive

Scenario Outline: The Grades card is shown when the course's criteria or the learner's course outline can't be loaded
  Given the site uses the "Replacement" layout
  And a course has competency criteria
  And <failure>
  When the learner opens the course's Progress tab
  Then the learner sees the Grades card with everything it shows on a site without the plugin
  And the competency criteria panel does not appear

  Examples:
    | failure                                                                                      |
    | the site's LMS does not provide #733's endpoint                                              |
    | #733's endpoint answers with a server error                                                  |
    | #733's endpoint refuses the request for this learner                                         |
    | the request to #733's endpoint fails because of a network error                              |
    | #733 returns the course's criteria, but the request for the learner's course outline fails   |

Scenario: A course whose criteria this learner can't see leaves the Grades card's place empty
  Given the site uses the "Replacement" layout
  And a course has competency criteria
  And the learner's course outline loads successfully
  And every criterion is on a subsection this learner isn't allowed to know exists, because the subsection is staff-only, restricted to a content group or cohort the learner isn't in, or deleted
  When the learner opens the course's Progress tab
  Then neither the competency criteria panel nor the Grades card is shown
  And the Grade summary and Detailed grades sections are shown as usual

Scenario Outline: Course staff get the same layout as the learner they are viewing
  Given the site uses the "Replacement" layout
  And <course>
  When <viewer> opens the course's Progress tab
  Then the staff member sees <shown> in the Grades card's place

  Examples:
    | viewer                                                          | course                              | shown                         |
    | a member of course staff viewing a specific learner's progress  | a course has competency criteria    | the competency criteria panel |
    | a member of course staff viewing a specific learner's progress  | a course has no competency criteria | that learner's Grades card    |
    | a member of course staff masquerading as a specific learner     | a course has competency criteria    | the competency criteria panel |

Scenario: A failure in the plugin's own code leaves the Grades card and the rest of the page in place
  Given the site uses the "Replacement" layout
  And the plugin code that chooses between the panel and the Grades card throws an error while rendering
  When a learner opens the Progress tab of any course, with or without competency criteria
  Then the learner sees the Grades card
  And the rest of the Progress tab renders as usual
  And the page does not go blank or replace the tab with an error message

Scenario: "Replacement" is the default layout
  Given the operator has enabled the plugin without choosing a layout and has rebuilt the Learning MFE image
  And a course has competency criteria
  When a learner opens the course's Progress tab
  Then the learner sees the competency criteria panel in the Grades card's place
  And the Grades card does not appear

Scenario: The "Above" layout behaves as #734 specifies
  Given the site uses the "Above" layout
  When a learner opens any course's Progress tab
  Then the page behaves as #734 specifies
  And the Grades card is shown in every course, including a course with competency criteria, and including while #733's answer or the learner's course outline is loading and after either request fails

Scenario Outline: The Grade summary and Detailed grades sections are unaffected
  Given the site uses the <layout> layout
  And <course>
  When the learner opens the course's Progress tab
  Then the Grade summary and Detailed grades sections appear and behave as they do on a site without the plugin

  Examples:
    | layout        | course                              |
    | "Replacement" | a course has competency criteria    |
    | "Replacement" | a course has no competency criteria |
    | "Above"       | a course has competency criteria    |
    | "Above"       | a course has no competency criteria |
```

The setting and its documentation are confirmed at code review and on a Tutor environment.

- [ ] An operator chooses between the "Above" and "Replacement" layouts with a single setting in #828's Tutor plugin, set with Tutor's normal configuration commands, without editing any file in the plugin.
- [ ] On a Tutor environment, changing the setting to "Above" and rebuilding the Learning MFE image switches the Progress tab to the "Above" layout, and changing it back and rebuilding again restores the "Replacement" layout.
- [ ] `example.env.config.jsx` registers the "Replacement" layout, and a local Learning MFE checkout that uses it as its `env.config.jsx` shows that layout.
- [ ] With the setting at its default, the slot configuration the Tutor plugin writes for the Learning MFE matches `example.env.config.jsx`.
- [ ] The README documents the setting: its name, its two values and what a learner sees with each, its default, and that a change takes effect only after the MFE image is rebuilt.
- [ ] The README tells an operator who configures the Learning MFE without Tutor which entry in `example.env.config.jsx` to change to get the "Above" layout.
- [ ] The README states what learners in courses with competency criteria stop seeing in the "Replacement" layout: the Grades card, including the learner's current grade against the passing grade, the letter-grade ranges, credit eligibility, and the upgrade prompt shown to audit learners. It also states that the Grade summary and Detailed grades sections still appear, and that courses without competency criteria are unchanged.
- [ ] The plugin's changelog entry for this change states that a site upgrading from an earlier version of the plugin will stop showing the Grades card in its courses with competency criteria unless the operator sets the "Above" layout, and it names the setting value that does that.

<details>
<summary>Technical Details</summary>

This is a suggested approach, not the source of truth. The User Story, Description, and Acceptance Criteria define what must be true when the work is done. The approach uses the Frontend Plugin Framework's `PLUGIN_OPERATIONS.Wrap`. frontend-base drops `Wrap` (see Additional context), so frontend-app-learning#1905 is likely to change how this ticket is wired.

**Summary**

#734's competency criteria panel stays registered exactly as it is. "Replacement" adds one more entry to `ProgressTabCourseGradeSlot`: a `Wrap` on the stock Grades card, whose wrapper shows the card only when the course has no competency criteria the panel can use. The panel and the wrapper decide from one shared hook, so they never render together. The Tutor plugin adds the `Wrap` entry only when its new placement setting is "Replacement".

**Approach**

1. Add `useCompetencyPanelState()` in `src/data/`, built on `useProgressRouteParams()` and on #734's `useCourseCompetencyCriteria`, `hasCompetencyCriteria`, and `useCourseOutline` hooks, which read the learning_sequences course outline through #734's plugin-owned query client. Sharing that client and its query keys means no extra requests. The hook returns one of three states:
   - `loading`.
   - `unavailable`: #733 failed, #733 is empty, or the outline failed.
   - `ready`: #733 has criteria and the outline loaded.

   Read #733's result before the outline's. The outline query stays disabled until #733 returns criteria, and a disabled query that has never run reports no data and a pending status. Checking both queries together would therefore leave every course without criteria stuck in `loading`. When cached data is present, let it win over a later refetch error, so a failed background refetch doesn't swap the panel for the card.
2. Make `CompetencyProgressPanel` render only when the hook returns `ready`, and keep its pruning. The panel and the wrapper then branch on one predicate, so they can never both render.
3. Add `CompetencyGradesCardWrapper`. The framework renders a wrapper as `createElement(wrapper, { component, pluginProps })`, where `component` is the stock `CourseGrade` element. The wrapper returns `component` when the hook returns `unavailable`, and `null` otherwise.

   Put the wrapper's logic inside `ErrorBoundary` from `@edx/frontend-platform/react`, with `fallbackComponent={component}`. That boundary also logs through `logError`. The wrapper needs its own boundary because the framework renders `default_contents` and its wrappers outside any `PluginContainer`, so neither a framework error boundary nor `errorFallbackComponent` covers them. Export the wrapper from `src/index.jsx`. The framework checks `typeof wrapper === 'function'`, so the wrapper must be a plain function component, not a `memo` or `forwardRef` object.
4. In `example.env.config.jsx`, keep #829's `competency_progress_panel` Insert, which sits at priority 20, above the stock content at 50. Add `{ op: PLUGIN_OPERATIONS.Wrap, widgetId: 'default_contents', wrapper: CompetencyGradesCardWrapper }`, with a comment saying to delete that entry to get "Above". The panel is inserted once in both modes, so it can't appear twice.
5. In the Tutor plugin:
   - Register the placement setting in `hooks.Filters.CONFIG_DEFAULTS`, with "Replacement" as its default.
   - Add `CompetencyGradesCardWrapper` to the existing `mfe-env-config-buildtime-imports` line.
   - Keep the Insert in #828's mapping, and emit the `Wrap` separately. tutor-mfe copies `PLUGIN_SLOTS` strings into `env.config.jsx` without rendering them through Jinja, and a `PLUGIN_SLOTS` item can't read config, so the `Wrap` can't be an ordinary entry in the mapping. Emit it through the `mfe-env-config-runtime-definitions-learning` patch instead, which Tutor does render. Inside a Jinja `{% if %}` on the setting, call `addPlugins(config, 'org.openedx.frontend.learning.progress_tab_course_grade.v1', [<the Wrap entry>])`. In tutor-mfe's template, `addPlugins`, `config`, and `PLUGIN_OPERATIONS` are all in scope inside that patch, but they are template internals rather than documented API.
   - Keep the `Wrap` entry's JSX as one Python constant, identical to the entry in `example.env.config.jsx`.
6. In courses without criteria, the Grades card now waits for #733 in "Replacement" mode, so a failed #733 request must fail fast. #734's plugin-owned query client does not retry 4xx responses, so a missing #733 route shows the Grades card after one request. Keep that rule if the client changes.

Out of scope: choosing the placement per course, and the move to frontend-base's slot API in frontend-app-learning#1905.

**Files to create and modify**

| File | Change |
| --- | --- |
| `src/data/useCompetencyPanelState.js` | new: the shared three-state hook |
| `src/CompetencyGradesCardWrapper.jsx` | new: the wrapper and its error boundary |
| `src/CompetencyProgressPanel.jsx` | modified: render only on `ready` |
| `src/index.jsx` | modified: export the wrapper |
| `example.env.config.jsx` | modified: add the `Wrap` entry |
| `tutor-contrib-<repository-name>/<module-name>/plugin.py` | modified: setting default, `Wrap` constant, conditional patch, import |
| `README.rst` | modified: operator documentation for the setting |
| `CHANGELOG.rst` | modified: the new default on upgrade |

**Additional context**

- In the Frontend Plugin Framework, `PluginSlot` and `data/utils.js` (`organizePlugins`, `wrapComponent`) under `src/plugins/` show how `default_contents` and wrappers are rendered. This approach was checked against version 1.8.0. frontend-app-learning allows `^1.7.0`.
- In tutor-mfe, `tutormfe/templates/mfe/build/mfe/env.config.jsx` shows `addPlugins`, where `PLUGIN_SLOTS` strings land, and where the `-learning` runtime patch is rendered. tutor-mfe's frontend-base compat template (`tutormfe/templates/mfe/partials/env.config.compat.jsx`) does not render the `-learning` patch, so the `Wrap` entry would drop if the Learning MFE were routed through it.
- frontend-base ADR 0011, "No slot wrapping operation", replaces `Wrap` with a custom slot layout that filters `useWidgets()` with `byId()` and `withoutId()`. Because the panel stays its own widget, it maps directly onto that model.
- @arbrandes commented on #828 that the plugin may be built into tutor-mfe after frontend-app-learning#1905. That would change where the placement setting lives.

</details>

## Open Questions

- (architect, final review) The title and User Story say "Grade summary", "Course Grade Slot", and "CBE Progress". The element this ticket replaces is the Grades card, the default content of `ProgressTabCourseGradeSlot`. The slot itself stays and holds the panel. "Grade summary" is a different section, which stays in both modes, and "CBE Progress" is #734's competency criteria panel. As written, the User Story says CBE courses lose the Grade summary, and the Description says they don't. Do you want to reword the title and User Story?
- (architect, final review) The Description's loading and failure bullets mention only the request to #733. The draft pass decided that a failed course outline request also shows the Grades card, so the wrapper waits on both requests, and the AC cover both. Do you want to add the course outline request to those two Description bullets?
- (architect, final review) In "Replacement" mode, in a course with criteria, what should the learner see if the panel itself throws while rendering? In the recommended design, the panel's `SilentErrorFallback` leaves the slot empty, because the wrapper can't see a render error inside the panel. Options: A) an empty slot, with the error logged, which matches the empty-panel rule (recommended); B) the Grades card, by having the wrapper render the panel inside its own error boundary and dropping the Insert in that mode.
- (architect, final review) #828's Technical Details say later tickets only edit the entries in its slot mapping. Tutor can't read a setting from a mapping entry, so the recommended design emits the `Wrap` entry through the Jinja-rendered `mfe-env-config-runtime-definitions-learning` patch next to the mapping. Do you accept that, and soften #828's sentence to say later tickets may add registrations next to the mapping?
- (implementer) The setting's name and value spellings, and what an unknown value does. The recommendation is that any value other than "Above" behaves as the default, "Replacement".

## Notes for drafting

### Known scope, decided during #734's pre-handoff check

- #734 renders the competency criteria panel above the stock "Grades" card, the default content of `ProgressTabCourseGradeSlot`. The Figma shows the panel with no Grades card, which is the "Replacement" layout this ticket adds.
- The operator chooses between "Above" and "Replacement". "Replacement" uses `PLUGIN_OPERATIONS.Wrap` on the slot's `default_contents`, with a wrapper that renders the stock Grades card only in courses with no competency criteria. That wrapper needs #734's check against #733's endpoint, which is why this ticket follows #734.
- Extends #828's data-driven Tutor slot mapping rather than rewriting it.
- frontend-app-learning#1905 moves plugin slots to frontend-base's `Slot` API, so the `PLUGIN_OPERATIONS.Wrap` mechanism may change before this ticket is built.

### Decisions from the pre-handoff check

- What "Replacement" replaces: exactly the default content of `ProgressTabCourseGradeSlot` (https://github.com/openedx/frontend-app-learning/tree/release/ulmo/src/plugin-slots/ProgressTabCourseGradeSlot), which is the `CourseGrade` card headed "Grades" (or "Grades and Credit"). "Grade summary" and "Detailed grades" live in a different slot, `ProgressTabGradeBreakdownSlot`, and stay on the page. The `CourseGrade` card also carries the current and passing grade bar, the letter-grade ranges, credit eligibility, and the audit learner's "Unlock to view grades" upgrade banner, so all of those go away with it in "Replacement" mode. Confirmed in frontend-app-learning `CourseGrade.jsx`. Defaulted without a question: this loss is accepted and documented for operators as the trade-off of "Replacement".
- Condition that replaces the card: the course qualifies when #733's response is non-empty, and doesn't qualify when #733 returns empty arrays. #733 is empty when the course has no course-level CompetencyCriteriaGroup with unarchived criteria: none were authored, or every criterion or group is archived, or every criterion's tag, tag ancestor or taxonomy is archived, or the taxonomy is disabled, or the course has no catalog CourseRun row. This is one course-level answer, the same for every learner, and the same check #734 uses to decide whether to render. The wrapper needs only #733's response to decide.
- Empty panel: a qualifying course can still give this learner an empty panel. #733's response is non-empty, but after #734 joins the criteria to the learner's course outline, nothing is left. That happens only when every criterion sits on a subsection the learner can't know exists (staff-only, content-group restricted, or deleted). Unreleased subsections don't cause it, because the Outline API includes them. In that case the slot stays empty, and the stock Grades card is not shown.
- Loading and failure: in "Replacement" mode, the slot stays empty until #733 answers, then shows either the panel or the stock Grades card. Any #733 failure, including a 404 when #733's route isn't deployed, shows the stock Grades card. Failing open matters because #734 itself renders nothing on failure.
- Timing and mechanism: write the ticket now, with the Description and AC in outcome terms only. Technical Details names the Frontend Plugin Framework's `PLUGIN_OPERATIONS.Wrap` as today's mechanism, flagged as likely to change. frontend-base's accepted ADR 0011 ("No slot wrapping operation") drops `Wrap`. Its replacement is a custom layout that filters `useWidgets()` (`byId()`, `withoutId()`), so frontend-app-learning#1905 will change the mechanism. #1905 is blocked on #1946 and has no timeline. Adolfo's comment on #828 also says the plugin may be built into `tutor-mfe` after #1905 rather than shipping its own Tutor plugin.
- Defaulted without a question: the choice is one site-wide Tutor setting. Its default is "Replacement" (decided by the architect), matching the Figma. Because #734 ships with "Above", a site upgrading to the release with this ticket loses the Grades card in its CBE courses without changing any setting, so the operator docs and release notes call this out. Per-course choice is out of scope. In staff view, staff see what the learner sees. The plugin's `example.env.config.jsx` shows the "Replacement" registration for operators who don't use Tutor. The AC use Gherkin scenarios for what learners see, plus a checklist for the setting and the docs.
- Naming: "Grade summary" in the title and User Story names the wrong component. The replaced element is the "Grades" card. "CBE Progress" names nothing that exists. #734 calls it the competency criteria panel. The title and User Story are the architect's to reword.
- Implementer-owned: the setting's name and value spellings, what an unknown value does, and react-query caching. The wrapper and #734's panel share one #733 request through the same react-query key.
- Out of scope: choosing the layout per course, changing the Grade summary or Detailed grades sections, and the frontend-base migration (frontend-app-learning#1905), which will change how the replacement is wired.

### Decisions from the draft pass (BA)

- A failed course outline request in a course with criteria shows the Grades card in "Replacement" mode, so the wrapper waits on both #733 and the outline.
- If the wrapper itself throws while rendering, the learner sees the Grades card. The Frontend Plugin Framework puts no error boundary around `default_contents` or a `Wrap` wrapper (checked in 1.8.0), so the wrapper carries its own.
- Operators who don't use Tutor: the README says which entry in `example.env.config.jsx` to change to get "Above".
- Posted #829 still says #734 owns the "Replacement" choice. A comment on #829 would correct it.
