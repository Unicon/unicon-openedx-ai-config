# [FE] Let the operator choose to replace the Course completion and Grades cards with CBE Progress

GitHub: https://github.com/openedx/openedx-core/issues/839 (#839, OPEN)
Cached: 2026-10-18

## User Story
As a site operator, I want to be able to have the Course completion and Grades cards replaced with CBE Progress for courses that have competency criteria while courses without competency criteria still show both cards, so that neither students of CBE courses nor students of traditional courses get confused about their overall progress.

## Description

This ticket implements the site-wide operator setting that #828 adds to tutor-mfe, which decides where #734's competency criteria panel goes on the Progress tab: above the stock Course completion and Grades cards (the default contents of `ProgressTabCourseCompletionSlot` and `ProgressTabCourseGradeSlot`), or in place of both (replacement). The default is "Replacement".

In "Replacement" mode:
- If #733 returns competency criteria for the course, the learner sees the competency criteria panel instead of the Course completion and Grades cards.
- If #733 returns an empty response, the learner sees the Course completion and Grades cards as usual.
- While #733's response is loading, the cards' place shows nothing, so learners in competency courses don't see the cards appear and then disappear.
- If the request to #733 fails for any reason, including a 404 when #733's route isn't deployed, the learner sees the Course completion and Grades cards.
- If the course has criteria but the panel can't be shown, for example because the learner's course outline fails to load, the cards' place stays empty.

The Grade summary and Detailed grades sections below the Grades card don't change in either mode.

The setting lives in tutor-mfe, added by #828, and takes effect when the MFE image is rebuilt.

## Context
Blocked by #733, #734, and #828.

## UX Design

This ticket needs no new design. In the "Replacement" layout, #734's competency criteria panel takes the place of the Course completion and Grades cards, as #734's happy path [Figma already shows](https://www.figma.com/design/VqDdtf3NOsUihle6SNS6Kw/-Course-Level----Student-Progress?node-id=983-3817&t=eJLFBvoAFbCnde7b-4): 

<img width="1155" height="1600" alt="Image" src="https://github.com/user-attachments/assets/2760e14c-4af0-4301-aea1-7893a165ef4a" />

## Acceptance Criteria

The scenarios below use these terms:

- The Course completion card is the card at the top of the Progress tab headed "Course completion". It appears only in courses that show the progress graph, which is a per-course setting.
- The Grades card is the card headed "Grades", or "Grades and Credit" in a course that offers credit.
- The progress cards are the Course completion card and the Grades card together. Their place is the top of the main column, where those cards normally appear.
- The Grade summary and Detailed grades sections are the two sections below the Grades card. They live in a different slot, `ProgressTabGradeBreakdownSlot`, and stay on the page in both layouts. The title's "Course completion and Grades cards" are the stock contents of `ProgressTabCourseCompletionSlot` and `ProgressTabCourseGradeSlot`, and "CBE Progress" is #734's competency criteria panel.
- A certificate status message that the Progress tab shows between the two cards stays where it is in both layouts.
- A course with competency criteria is one that #733 returns criteria for. A course without competency criteria is one that #733 returns none for.
- In a course with competency criteria, the competency criteria panel also loads the learner's course outline.
- #734 specifies what the panel contains, including in staff view.

```gherkin
Scenario Outline: A course with competency criteria shows the panel in place of the progress cards, which is the default layout
  Given <layout>
  And a course has competency criteria
  When the learner opens the course's Progress tab
  Then the learner sees the competency criteria panel in the progress cards' place
  And neither the Course completion card nor the Grades card appears anywhere on the page

  Examples:
    | layout                                                                                                          |
    | the site uses the "Replacement" layout                                                                          |
    | the operator has left tutor-mfe's placement setting at its default and has rebuilt the Learning MFE image       |

Scenario: A course without competency criteria shows the progress cards as usual
  Given the site uses the "Replacement" layout
  And a course has no competency criteria
  When the learner opens the course's Progress tab
  Then the learner sees the Course completion and Grades cards with everything they show on a site without the plugin
  And the competency criteria panel does not appear

Scenario: The progress cards do not appear and then disappear while the page loads
  Given the site uses the "Replacement" layout
  And a course has competency criteria
  When the learner opens the course's Progress tab
  Then the progress cards' place stays empty until both #733's answer and the learner's course outline have arrived
  And the Grade summary and Detailed grades sections appear without waiting for either one
  And neither the Course completion card nor the Grades card is shown at any point while they load

Scenario Outline: The progress cards are shown when the course's criteria can't be loaded
  Given the site uses the "Replacement" layout
  And competency criteria have been authored for a course
  And <failure>
  When the learner opens the course's Progress tab
  Then the learner sees the Course completion and Grades cards with everything they show on a site without the plugin
  And the competency criteria panel does not appear

  Examples:
    | failure                                                                                      |
    | the site's LMS does not provide #733's endpoint                                              |
    | #733's endpoint answers with a server error                                                  |
    | #733's endpoint refuses the request for this learner                                         |
    | the request to #733's endpoint fails because of a network error                              |

Scenario: A course with competency criteria never shows the progress cards when the panel can't be shown
  Given the site uses the "Replacement" layout
  And #733 returns criteria for the course
  And the request for the learner's course outline fails
  When the learner opens the course's Progress tab
  Then neither the competency criteria panel nor either progress card is shown
  And the error is reported to the site's logging service
  And the Grade summary and Detailed grades sections are shown as usual

Scenario Outline: A course that hides its progress graph has no Course completion card in either case
  Given the site uses the "Replacement" layout
  And a course turns off its progress graph, so the Course completion card never appears in it
  And <course>
  When the learner opens the course's Progress tab
  Then the learner sees <shown> at the top of the main column
  And no error message appears

  Examples:
    | course                              | shown                                                                       |
    | a course has competency criteria    | the competency criteria panel, and no Grades card                           |
    | a course has no competency criteria | the Grades card, with everything it shows on a site without the plugin      |

Scenario Outline: Course staff get the same layout as the learner they are viewing
  Given the site uses the "Replacement" layout
  And <course>
  When <viewer> opens the course's Progress tab
  Then the staff member sees <shown> in the progress cards' place

  Examples:
    | viewer                                                          | course                              | shown                                         |
    | a member of course staff viewing a specific learner's progress  | a course has competency criteria    | the competency criteria panel                 |
    | a member of course staff viewing a specific learner's progress  | a course has no competency criteria | that learner's Course completion and Grades cards |
    | a member of course staff masquerading as a specific learner     | a course has competency criteria    | the competency criteria panel                 |

Scenario: The "Above" layout keeps the progress cards in every course
  Given the site uses the "Above" layout
  When a learner opens any course's Progress tab
  Then the Course completion and Grades cards are shown, including while the panel is loading and after it fails to load
  And in a course with competency criteria, the competency criteria panel appears above the Course completion card

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

The layouts and their documentation are confirmed at code review and on a Tutor environment.

- [ ] This ticket adds no setting of its own. On a Tutor environment whose Learning MFE image installs a package version that includes this ticket, changing tutor-mfe's placement setting from #828 to "Above" and rebuilding the Learning MFE image switches the Progress tab to the "Above" layout, and changing it back and rebuilding again restores the "Replacement" layout. Until tutor-mfe's pinned package version is bumped, the tester needs a tutor-mfe build that installs that package version.
- [ ] The README documents the package's two placement values, what a learner sees with each, the default, and that on a Tutor site tutor-mfe's placement setting from #828 chooses between them, taking effect only after the MFE image is rebuilt.
- [ ] The README tells an operator who configures the Learning MFE without Tutor which placement value to pass in `example.env.config.jsx` to get the "Above" layout.
- [ ] The README states what learners in courses with competency criteria stop seeing in the "Replacement" layout: the Course completion card, which shows how much of the course content the learner has completed, and the Grades card, including the learner's current grade against the passing grade, the letter-grade ranges, credit eligibility, and the upgrade prompt shown to audit learners. It explains that these are hidden because they don't accurately describe a learner's progress in a course with competency criteria. It also states that the Grade summary and Detailed grades sections still appear, and that courses without competency criteria are unchanged.

<details>
<summary>Technical Details</summary>

This is a suggested approach, not the source of truth. The User Story, Description, and Acceptance Criteria define what must be true when the work is done. The approach uses the Frontend Plugin Framework's `PLUGIN_OPERATIONS.Wrap`. frontend-base drops `Wrap` (see Additional context), so frontend-app-learning#1905 is likely to change how this ticket is wired.

**Summary**

#734's competency criteria panel stays one widget, inserted at the top of `ProgressTabCourseCompletionSlot` in both layouts. "Replacement" adds a `Wrap` on the stock content of two slots, `ProgressTabCourseCompletionSlot` and `ProgressTabCourseGradeSlot`, and the wrapper shows the stock card only when #733 returns no criteria for the course or its request fails. The panel and the wrappers decide from one shared hook, so the panel and the stock cards never render together. The `Wrap` entries come from the package's slot configuration function (#829), which tutor-mfe already calls with its placement setting (#828), so tutor-mfe needs nothing from this ticket beyond a bump of its pinned package version.

**Approach**

1. Add `useCompetencyPanelState()` in `src/data/`, built on `useProgressRouteParams()` and on #734's `useCourseCompetencyCriteria` and `hasCompetencyCriteria` hooks, which share #734's plugin-owned query client and query keys, so the hook adds no requests. It decides from #733's response alone, because whether a course has competency criteria is a course-level answer. It returns one of three states:
   - `loading`: #733 hasn't answered yet.
   - `unavailable`: #733 failed or returned no criteria.
   - `ready`: #733 returned criteria.

   When cached data is present, let it win over a later refetch error, so a failed background refetch doesn't swap the panel for the stock cards.
2. Make `CompetencyProgressPanel` render only when the hook returns `ready`, and otherwise keep #734's behavior: it still waits for the course outline and renders nothing if the outline fails. In a course with criteria, the wrappers hide both stock cards regardless of what the panel then renders, so an outline failure or a panel render error leaves the top of the main column empty, with the error logged by #734's query client or by the panel's error boundary.
3. Add `CompetencyReplacementWrapper`. The framework renders a wrapper as `createElement(wrapper, { component, pluginProps })`, where `component` is the slot's stock content: the `CourseCompletion` element in the completion slot and the `CourseGrade` element in the grade slot. The wrapper returns `component` when the hook returns `unavailable`, and `null` otherwise.

   Put the wrapper's logic inside `ErrorBoundary` from `@edx/frontend-platform/react`, with `fallbackComponent={component}`. That boundary also logs through `logError`. The wrapper needs its own boundary because the framework renders `default_contents` and its wrappers outside any `PluginContainer`, so neither a framework error boundary nor `errorFallbackComponent` covers them. The framework checks `typeof wrapper === 'function'`, so the wrapper must be a plain function component, not a `memo` or `forwardRef` object.

   In a course that disables the progress graph, the completion slot's stock content is `{enableProgressGraph && <CourseCompletion />}`, which evaluates to `false`, so the wrapper receives `component === false`. Return `null` before rendering the boundary in that case, because `ErrorBoundary` renders `fallbackComponent || <ErrorPage />`, and a `false` fallback would turn a wrapper error into a full-page error message inside the Progress tab. The panel is unaffected, because it is a separate widget in that slot and renders whether or not the stock card does.
4. In #829's slot configuration function, keep the `competency_progress_panel` Insert in `org.openedx.frontend.learning.progress_tab_course_completion.v1` at priority 20, above the stock content at 50, in both layouts. When the placement value is "Replacement", also add `{ op: PLUGIN_OPERATIONS.Wrap, widgetId: 'default_contents', wrapper: CompetencyReplacementWrapper }` to that slot and to `org.openedx.frontend.learning.progress_tab_course_grade.v1`. Use the value spellings of tutor-mfe's setting from #828. The panel is inserted once in both layouts, so it can't appear twice. In `example.env.config.jsx`, pass the placement explicitly, with a comment naming the other value. tutor-mfe and the example call the same function, so they register the same entries without a separate parity check, and the wrapper needs no export from `src/index.jsx`.
5. Leave `ProgressTabCertificateStatusMainBodySlot` alone. It sits between the two stock cards, so in "Replacement" in a course with criteria, a certificate status message shown there appears between the panel and the Grade summary.
6. In courses without criteria, both stock cards now wait for #733 in "Replacement" mode, so a failed #733 request must fail fast. #734's plugin-owned query client does not retry 4xx responses, so a missing #733 route shows the cards after one request. Keep that rule if the client changes. A 5xx is still retried, and react-query's default of three retries hides the cards for several seconds on every course's Progress tab while the LMS is failing, so retry a 5xx at most once.

**Tests**

These cases need an injected fault or a direct call to the slot configuration function, so they are covered by tests and code review rather than by the Acceptance Criteria:

- In the "Replacement" layout, when the wrapper throws while rendering, the stock card it wraps is shown, the rest of the Progress tab renders as usual, and the error is logged. Cover both slots, in a course with competency criteria and in one without.
- In the "Replacement" layout, in a course that disables the progress graph, the completion slot's wrapper renders nothing and never shows an error page.
- In the "Replacement" layout, in a course with competency criteria, when the competency criteria panel throws while rendering, neither the panel nor either stock card is shown, the error is logged, and the Grade summary and Detailed grades sections are still shown.
- The slot configuration function returns the panel's Insert in the completion slot for every placement value, adds both `Wrap` entries for "Replacement" and when no value is passed, and adds no `Wrap` entry for "Above".

Out of scope: choosing the placement per course, the tutor-mfe setting itself (#828), and the move to frontend-base's slot API in frontend-app-learning#1905.

**Files to create and modify**

| File | Change |
| --- | --- |
| `src/data/useCompetencyPanelState.js` | new: the shared three-state hook |
| `src/CompetencyReplacementWrapper.jsx` | new: the wrapper and its error boundary |
| `src/CompetencyProgressPanel.jsx` | modified: render only on `ready` |
| `src/pluginSlots.js` | modified: the two `Wrap` entries for "Replacement" |
| `example.env.config.jsx` | modified: explicit placement value |
| `README.rst` | modified: operator documentation for the two layouts |

**Additional context**

- In the Frontend Plugin Framework, `PluginSlot` and `data/utils.js` (`organizePlugins`, `wrapComponent`) under `src/plugins/` show how `default_contents` and wrappers are rendered. This approach was checked against version 1.8.0. frontend-app-learning allows `^1.7.0`.
- In frontend-app-learning, `src/course-home/progress-tab/ProgressTab.jsx` shows the main column's order, and `src/plugin-slots/ProgressTabCourseCompletionSlot/` shows how the completion slot passes `enableProgressGraph`. That slot exists only on master (openedx/frontend-app-learning#1943). This ticket supports only master and the Willow release.
- frontend-base ADR 0011, "No slot wrapping operation", replaces `Wrap` with a custom slot layout that filters `useWidgets()` with `byId()` and `withoutId()`. Because the panel stays its own widget, it maps directly onto that model.

</details>

## Open Questions

- (implementer) What an unknown placement value does. The recommendation is that any value other than "Above" behaves as the default, "Replacement".
