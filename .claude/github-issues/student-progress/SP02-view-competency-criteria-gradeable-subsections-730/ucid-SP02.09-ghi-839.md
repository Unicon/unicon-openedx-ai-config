# [FE] Let the operator choose to replace Course Grade Slot with CBE Progress

GitHub: https://github.com/openedx/openedx-core/issues/839 (#839, OPEN)
Cached: 2026-10-18

## User Story
As a site operator, I want to be able to have the Grades card replaced with CBE Progress for courses that have competency criteria while courses without competency criteria still show the Grades card, so that neither students of CBE courses nor students of traditional courses get confused about their overall progress.

## Description

This ticket adds a site-wide operator setting that decides where #734's competency criteria panel goes on the Progress tab: above the stock Grades card (the default content of `ProgressTabCourseGradeSlot`), or in place of it (replacement). The default is "Replacement".

In "Replacement" mode:
- If #733 returns competency criteria for the course, the learner sees the competency criteria panel instead of the Grades card.
- If #733 returns an empty response, the learner sees the Grades card as usual.
- While #733's response is loading, the slot shows nothing, so learners in competency courses don't see the Grades card appear and then disappear.
- If the request to #733 fails for any reason, including a 404 when #733's route isn't deployed, the learner sees the Grades card.
- If the course has criteria but the panel can't be shown, for example because the learner's course outline fails to load, the slot stays empty.

The Grade summary and Detailed grades sections below the Grades card don't change in either mode.

The setting lives in #828's Tutor plugin and takes effect when the MFE image is rebuilt.

## Context
Blocked by #733, #734, and #828.

## UX Design

This ticket needs no new design. In the "Replacement" layout, #734's competency criteria panel takes the Grades card's place, as #734's happy path [Figma already shows](https://www.figma.com/design/VqDdtf3NOsUihle6SNS6Kw/-Course-Level----Student-Progress?node-id=983-3817&t=eJLFBvoAFbCnde7b-4): 

<img width="3790" height="5248" alt="Image" src="https://github.com/user-attachments/assets/71b69a7c-0f63-4cbf-a414-314b6fdb3ac9" />

## Acceptance Criteria

The scenarios below use these terms:

- The Grades card is the card at the top of the Progress tab headed "Grades", or "Grades and Credit" in a course that offers credit.
- The Grades card's place is the position on the page where that card normally appears.
- The Grade summary and Detailed grades sections are the two sections below the Grades card. They live in a different slot, `ProgressTabGradeBreakdownSlot`, and stay on the page in both layouts. The title's "Course Grade Slot" is `ProgressTabCourseGradeSlot`, which holds the Grades card, and "CBE Progress" is #734's competency criteria panel.
- A course with competency criteria is one that #733 returns criteria for. A course without competency criteria is one that #733 returns none for.
- In a course with competency criteria, the competency criteria panel also loads the learner's course outline.
- #734 specifies what the panel contains, including in staff view.

```gherkin
Scenario Outline: A course with competency criteria shows the panel in place of the Grades card, which is the default layout
  Given <layout>
  And a course has competency criteria
  When the learner opens the course's Progress tab
  Then the learner sees the competency criteria panel in the Grades card's place
  And the Grades card does not appear anywhere on the page

  Examples:
    | layout                                                                                               |
    | the site uses the "Replacement" layout                                                               |
    | the operator has enabled the plugin without choosing a layout and has rebuilt the Learning MFE image |

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
  And the Grades card is not shown at any point while they load

Scenario Outline: The Grades card is shown when the course's criteria can't be loaded
  Given the site uses the "Replacement" layout
  And competency criteria have been authored for a course
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

Scenario: A course with competency criteria never shows the Grades card when the panel can't be shown
  Given the site uses the "Replacement" layout
  And #733 returns criteria for the course
  And the request for the learner's course outline fails
  When the learner opens the course's Progress tab
  Then neither the competency criteria panel nor the Grades card is shown
  And the error is reported to the site's logging service
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

Scenario: The "Above" layout keeps the Grades card in every course
  Given the site uses the "Above" layout
  When a learner opens any course's Progress tab
  Then the Grades card is shown, including while the panel is loading and after it fails to load
  And in a course with competency criteria, the competency criteria panel appears above the Grades card

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
- [ ] The README documents the setting: its name, its two values and what a learner sees with each, its default, and that a change takes effect only after the MFE image is rebuilt.
- [ ] The README tells an operator who configures the Learning MFE without Tutor which entry in `example.env.config.jsx` to change to get the "Above" layout.
- [ ] The README states what learners in courses with competency criteria stop seeing in the "Replacement" layout: the Grades card, including the learner's current grade against the passing grade, the letter-grade ranges, credit eligibility, and the upgrade prompt shown to audit learners, and explains that these are hidden because they don't accurately describe a learner's progress in a course with competency criteria. It also states that the Grade summary and Detailed grades sections still appear, and that courses without competency criteria are unchanged.

<details>
<summary>Technical Details</summary>

This is a suggested approach, not the source of truth. The User Story, Description, and Acceptance Criteria define what must be true when the work is done. The approach uses the Frontend Plugin Framework's `PLUGIN_OPERATIONS.Wrap`. frontend-base drops `Wrap` (see Additional context), so frontend-app-learning#1905 is likely to change how this ticket is wired.

**Summary**

#734's competency criteria panel stays registered exactly as it is. "Replacement" adds one more entry to `ProgressTabCourseGradeSlot`: a `Wrap` on the stock Grades card, whose wrapper shows the card only when #733 returns no criteria for the course or its request fails. The panel and the wrapper decide from one shared hook, so they never render together. The Tutor plugin adds the `Wrap` entry only when its new placement setting is "Replacement".

**Approach**

1. Add `useCompetencyPanelState()` in `src/data/`, built on `useProgressRouteParams()` and on #734's `useCourseCompetencyCriteria` and `hasCompetencyCriteria` hooks, which share #734's plugin-owned query client and query keys, so the hook adds no requests. It decides from #733's response alone, because whether a course has competency criteria is a course-level answer. It returns one of three states:
   - `loading`: #733 hasn't answered yet.
   - `unavailable`: #733 failed or returned no criteria.
   - `ready`: #733 returned criteria.

   When cached data is present, let it win over a later refetch error, so a failed background refetch doesn't swap the panel for the card.
2. Make `CompetencyProgressPanel` render only when the hook returns `ready`, and otherwise keep #734's behavior: it still waits for the course outline and renders nothing if the outline fails. In a course with criteria, the wrapper hides the Grades card regardless of what the panel then renders, so an outline failure or a panel render error leaves the slot empty, with the error logged by #734's query client or #829's `SilentErrorFallback`.
3. Add `CompetencyGradesCardWrapper`. The framework renders a wrapper as `createElement(wrapper, { component, pluginProps })`, where `component` is the stock `CourseGrade` element. The wrapper returns `component` when the hook returns `unavailable`, and `null` otherwise.

   Put the wrapper's logic inside `ErrorBoundary` from `@edx/frontend-platform/react`, with `fallbackComponent={component}`. That boundary also logs through `logError`. The wrapper needs its own boundary because the framework renders `default_contents` and its wrappers outside any `PluginContainer`, so neither a framework error boundary nor `errorFallbackComponent` covers them. Export the wrapper from `src/index.jsx`. The framework checks `typeof wrapper === 'function'`, so the wrapper must be a plain function component, not a `memo` or `forwardRef` object.
4. In `example.env.config.jsx`, keep #829's `competency_progress_panel` Insert, which sits at priority 20, above the stock content at 50. Add `{ op: PLUGIN_OPERATIONS.Wrap, widgetId: 'default_contents', wrapper: CompetencyGradesCardWrapper }`, with a comment saying to delete that entry to get "Above". The panel is inserted once in both modes, so it can't appear twice.
5. In the Tutor plugin:
   - Register the placement setting in `hooks.Filters.CONFIG_DEFAULTS`, with "Replacement" as its default.
   - Add `CompetencyGradesCardWrapper` to the existing `mfe-env-config-buildtime-imports` line.
   - Keep the Insert in #828's mapping, and emit the `Wrap` separately. tutor-mfe copies `PLUGIN_SLOTS` strings into `env.config.jsx` without rendering them through Jinja, and a `PLUGIN_SLOTS` item can't read config, so the `Wrap` can't be an ordinary entry in the mapping. Emit it through the `mfe-env-config-runtime-definitions-learning` patch instead, which Tutor does render. Inside a Jinja `{% if %}` on the setting, call `addPlugins(config, 'org.openedx.frontend.learning.progress_tab_course_grade.v1', [<the Wrap entry>])`. In tutor-mfe's template, `addPlugins`, `config`, and `PLUGIN_OPERATIONS` are all in scope inside that patch, but they are template internals rather than documented API.
   - Keep the `Wrap` entry's JSX as one Python constant, identical to the entry in `example.env.config.jsx`.
6. In courses without criteria, the Grades card now waits for #733 in "Replacement" mode, so a failed #733 request must fail fast. #734's plugin-owned query client does not retry 4xx responses, so a missing #733 route shows the Grades card after one request. Keep that rule if the client changes.

**Tests**

These cases need an injected fault or a comparison of config files, so they are covered by tests and code review rather than by the Acceptance Criteria:

- In the "Replacement" layout, when the wrapper throws while rendering, the Grades card is shown, the rest of the Progress tab renders as usual, and the error is logged. Cover a course with competency criteria and one without.
- In the "Replacement" layout, in a course with competency criteria, when the competency criteria panel throws while rendering, neither the panel nor the Grades card is shown, the error is logged, and the Grade summary and Detailed grades sections are still shown.
- `example.env.config.jsx` registers the "Replacement" layout, and with the setting at its default, the slot configuration the Tutor plugin writes for the Learning MFE matches `example.env.config.jsx`.

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

**Additional context**

- In the Frontend Plugin Framework, `PluginSlot` and `data/utils.js` (`organizePlugins`, `wrapComponent`) under `src/plugins/` show how `default_contents` and wrappers are rendered. This approach was checked against version 1.8.0. frontend-app-learning allows `^1.7.0`.
- In tutor-mfe, `tutormfe/templates/mfe/build/mfe/env.config.jsx` shows `addPlugins`, where `PLUGIN_SLOTS` strings land, and where the `-learning` runtime patch is rendered. tutor-mfe's frontend-base compat template (`tutormfe/templates/mfe/partials/env.config.compat.jsx`) does not render the `-learning` patch, so the `Wrap` entry would drop if the Learning MFE were routed through it.
- frontend-base ADR 0011, "No slot wrapping operation", replaces `Wrap` with a custom slot layout that filters `useWidgets()` with `byId()` and `withoutId()`. Because the panel stays its own widget, it maps directly onto that model.
- @arbrandes commented on #828 that the plugin may be built into tutor-mfe after frontend-app-learning#1905. That would change where the placement setting lives.

</details>

## Open Questions

- (implementer) The setting's name and value spellings, and what an unknown value does. The recommendation is that any value other than "Above" behaves as the default, "Replacement".

