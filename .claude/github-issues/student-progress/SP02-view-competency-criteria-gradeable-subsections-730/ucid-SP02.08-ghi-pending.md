# [FE] Render placeholder CBE progress widgets in both learner Progress tab slots

GitHub: not yet filed. Depends on #810 and the Tutor packaging ticket (also not yet filed).
Cached: 2026-09-22

## User Story

As a learner, I want the CBE learner progress experience to appear above (or, in the future, in place of) the `ProgressTabCourseGradeSlot` and above the `ProgressTabRelatedLinksSlot` so that it can serve as my primary reference for understanding my progress in the course.

## Description

This ticket replaces the generic placeholder component from #810 and the Tutor packaging ticket with the two real starter CBE progress widgets, plus the local development loop future frontend tickets will use to build against them. The widgets render on every course's Progress tab for now; the check that limits them to courses with competency criteria will be added in #734.

## Acceptance Criteria

```
Scenario: Both placeholders render in their intended positions
  Given a developer is running a local Learning MFE dev server, pointed at a running Open edX backend, with the plugin's slot configuration loaded
  When they open a course's Progress tab
  Then a clearly labeled placeholder appears in the main column, above the grade summary card
  And a clearly labeled placeholder appears in the right sidebar, above the related links

Scenario: The stock Progress tab content survives
  Given a developer is running a local Learning MFE dev server with the plugin's slot configuration loaded
  When they open a course's Progress tab
  Then the grade summary, the detailed grades table, and the related links list are all still present
  And each of them behaves as it did before the plugin's configuration was loaded

Scenario: The widgets know which learner a staff member is viewing
  Given a developer is running a local Learning MFE dev server with the plugin's slot configuration loaded
  When a member of course staff opens a specific learner's progress view
  Then each placeholder identifies both the course and the learner it is rendering for

Scenario: The widgets know which course a learner is viewing
  Given a developer is running a local Learning MFE dev server with the plugin's slot configuration loaded
  When a learner opens their own Progress tab for a course
  Then each placeholder identifies the course it is rendering for
  And no separate learner is named

Scenario: A failing widget is contained
  Given a developer is running a local Learning MFE dev server with the plugin's slot configuration loaded
  And one of the plugin's widgets throws an error while rendering
  When a learner opens a course's Progress tab
  Then the rest of the Progress tab still renders, including the grade summary and the detailed grades table
  And the plugin's other placeholder still renders
  And the page does not go blank and does not replace the whole tab with an error

Scenario: The Learning MFE is unchanged when the plugin's configuration is not loaded
  Given a local Learning MFE dev server running without the plugin's slot configuration
  When a learner opens a course's Progress tab
  Then the page renders exactly as it does in a checkout that has never had the plugin set up

@code-review-only
Scenario: A developer new to the repository reaches a rendering widget from the documentation alone
  Given a developer with a frontend-app-learning checkout and no prior knowledge of this plugin
  When they follow the repository's local development instructions from start to finish, using the example configuration file the repository ships
  Then their local Learning MFE dev server starts
  And both placeholders appear on a course's Progress tab

Scenario: The placeholders reflow on a small screen
  Given a developer is running a local Learning MFE dev server with the plugin's slot configuration loaded
  When they open a course's Progress tab at a phone-sized viewport
  Then the placeholders reflow with the rest of the page
  And no horizontal scrolling or overlapping content is introduced
```

<details>
<summary>Technical Details</summary>

This section is background and a suggested approach, not the ticket's source of truth. The User Story and Acceptance Criteria define what must be true when the work is done; everything below exists to save the implementer some thinking.

### In short

**What this ticket delivers, and what it deliberately leaves out.** The deliverable is two React widgets in the package #810 creates, a hook that tells them which course they are in, an error fallback, tests, the example configuration file that supports local development, and an edit to the Tutor plugin's registration so it installs these widgets instead of the generic placeholder it shipped with. The widgets render on every course's Progress tab, with no check for whether the course has competency criteria. That is deliberate rather than an omission: the backend endpoint that answers the question is #733, which does not exist yet, and #734 owns adding the check once it does. Building a placeholder check now would mean inventing a temporary switch and then removing it. Verifying this ticket needs no Docker image build: the fast local development loop below is sufficient, and the Tutor plugin's own registration only needs a small, mechanical edit once these widgets exist.

**Where a widget learns which course it is rendering for.** Neither of the two target slots passes any props to what it renders, so a widget has to find the course itself. Read it from the route with `react-router-dom`'s `useParams()`, which yields `courseId`, and `targetUserId` as well when course staff are viewing one learner's progress. The URL is the Learning MFE's public contract. The alternative, copying the host application's own Redux selector, would tie an external package to the internal shape of the host's application state, which can change in any release without notice. The placeholders display the values the hook returns, so this ticket proves the seam works rather than only proving that a component can be inserted. Every later widget in this package reads the course the same way.

**Why `react-router-dom` has to stay a peer dependency.** #810 declares it as one, and it has to stay that way for this hook to work at all. React libraries hand data down through a context, which is a JavaScript object with its own identity. If the package listed `react-router-dom` as a regular dependency, npm would install a second copy of the router nested underneath it, that second copy would carry its own separate and empty context, and `useParams()` would return an empty object with no error of any kind.

**Where the widgets sit relative to the stock content, and why that is a number rather than a rewrite.** The framework sorts a slot's widgets by ascending priority, and treats the slot's own stock content as a widget at priority 50. Registering at priority 20 therefore puts a widget above the stock content, and leaving `keepDefault` at its default keeps that stock content rendering. Moving a widget below the stock content later is a one-number change in the configuration, not a change to the component.

**How a failing widget stays contained.** The plugin framework already renders each widget inside an error boundary, so a crash in this package cannot reach the rest of the Progress tab. What the slot configuration chooses is what appears in the widget's place, and this package supplies a fallback that renders nothing and reports the failure to the operator's logging service. Rendering nothing is not merely tidy: a slot renders its widgets into a React fragment with no wrapper element of its own, so a widget that returns nothing leaves no empty container and no stray spacing behind. A visible error card, by contrast, would be unactionable for a learner and would damage a page they need.

**How the package is developed and verified without Tutor.** A local `frontend-app-learning` checkout can point at this repository directly through a webpack alias, and can be given the slot configuration this ticket writes to `example.env.config.jsx`, the first version of that file in this repository. The Tutor plugin already exists by this point, registering a generic placeholder in its place, but nothing in this ticket's own verification touches it. That means the whole of this ticket is verifiable in a normal dev server against a devstack, in a fast edit-and-reload loop. Check that loop into the repository as a documented, copy-and-paste procedure and as an example configuration file, because it is how seven dependent frontend tickets will do their work, and getting it wrong is the difference between a fast loop and a Docker rebuild per change.

### Implementation specifics

- **Barrel.** `src/index.jsx` re-exports `CompetencyProgressPanel`, `CompetencyProgressSummary`, and `SilentErrorFallback` as named exports and does no work at import time. The entry point is imported into a JavaScript configuration file that every MFE on the site reads, so it must import only packages every MFE already has, which is React, Paragon, and `@edx/frontend-platform`.
- **Route parameters.** `useProgressRouteParams()` in `src/data/useProgressRouteParams.js` wraps `useParams()` and returns `{ courseId, targetUserId }`, with `targetUserId` undefined on the learner's own route. No decoding is needed: the Learning MFE's `DecodePageRoute` redirects to a fully decoded URL before the Progress tab renders. Keeping this in one file means a future change in how the host exposes the course is a single-file change for the whole package.
- **Placeholder content.** Each widget is a Paragon `Card` containing one sentence of throwaway English and the values from `useProgressRouteParams`. Paragon is what makes the placeholder match the surrounding cards and inherit the host MFE's theme with no styling wiring at all. Both placeholders are replaced by real interfaces in #734 and #743.
- **Error fallback.** `SilentErrorFallback` renders `null` and calls `logError` from `@edx/frontend-platform/logging`, so operators still see the failure in whatever logging service they configured and learners see nothing.
- **Slot configuration.** Create `example.env.config.jsx`, the first version of this file in the repository, registering one widget per slot into `org.openedx.frontend.learning.progress_tab_course_grade.v1` and `org.openedx.frontend.learning.progress_tab_related_links.v1`, using the canonical slot ids rather than their `idAliases`. Each is a `PLUGIN_OPERATIONS.Insert` whose widget object carries a stable `id` (`competency_progress_panel` and `competency_progress_summary`), `type: DIRECT_PLUGIN`, `priority: 20`, `RenderWidget`, and `errorFallbackComponent`, which the framework reads from the widget object rather than from anything enclosing it. Leave `keepDefault` at its default of true, so the stock Grades card and the stock related links both survive.
- **Update the Tutor plugin's registration.** Edit `tutor-contrib-<repository-name>/<module-name>/plugin.py`, created by the Tutor packaging ticket, so its two `PLUGIN_OPERATIONS.Insert` entries reference these two widgets instead of the generic placeholder, and add `errorFallbackComponent: SilentErrorFallback` to each, a field the placeholder registration did not use since #810 ships no error fallback. Keep the same widget ids and priority the Tutor ticket chose where they still make sense, so the edit is confined to which component renders, not a rewrite of the registration's structure. From this point on, keep this file's JSX identical to `example.env.config.jsx`: that file is what developers use in their local loop, so a divergence between the two means local development stops matching what operators get.
- **Local development loop, to be documented in the README.** Add a `module.config.js` at the root of a `frontend-app-learning` checkout containing `localModules: [{ moduleName: <this package's name>, dir: <absolute path to this repository>, dist: 'src' }]`, which is a webpack alias rather than `npm link`, and copy `example.env.config.jsx` to `env.config.jsx` in that same checkout root. There is no `module.config.js.example` in `frontend-app-learning` to copy from, so the file is created rather than copied.
- **Tests.** Jest, through `@openedx/frontend-build`, on the workflow #810 creates. The cases worth having are: `useProgressRouteParams` returns `targetUserId` on the staff route pattern and leaves it undefined on the learner route; each widget renders its placeholder with the course ID from the route; and `SilentErrorFallback` renders no DOM.
- **Gating is out of scope and belongs to #734.** The widgets render on every course. #734 adds the check against #733's endpoint, and it also owns the operator's choice of rendering the panel in place of the stock grade summary card rather than above it.
- **Two things for #734 and #733 to weigh, out of scope here.** Once #734 adds the check, it runs on every Progress tab render, for every course on the site, including the large majority that have no competency data, and the Progress tab is a heavily visited page. #733 should be specified knowing it has this consumer. Either its criteria response doubles as the answer, so one cheap call returns an empty payload for a non-competency course, or the Progress tab's existing course metadata carries a boolean, which is cheaper on the hot path but needs a change in `openedx-platform`. Separately, a React error boundary catches only errors thrown during render, not errors thrown inside asynchronous callbacks, so whoever adds that fetch must have it catch its own failures rather than rely on the boundary.
- **Internationalization is optional and is not a condition for closing this ticket.** The placeholder strings are discarded in #734 and #743, so extraction tooling added now would be tooling for strings that will not survive. Whether the package wires up `@edx/frontend-platform/i18n` and string extraction is a decision that belongs with the first strings that reach learners.

</details>

<details>
<summary>Files to create and modify</summary>

Paths are relative to the root of the repository created in #810.

**New files**

| File | Purpose |
| --- | --- |
| `src/CompetencyProgressPanel.jsx` | The placeholder widget for the main-column Progress tab slot. |
| `src/CompetencyProgressSummary.jsx` | The placeholder widget for the right sidebar slot. |
| `src/SilentErrorFallback.jsx` | The error fallback that logs the failure and renders nothing. |
| `src/data/useProgressRouteParams.js` | Reads `courseId` and `targetUserId` from the Progress route. |
| `src/CompetencyProgressPanel.test.jsx` | Rendering tests for the main-column widget. |
| `src/CompetencyProgressSummary.test.jsx` | Rendering tests for the sidebar widget. |
| `src/data/useProgressRouteParams.test.js` | Learner-route and staff-route parameter tests. |
| `example.env.config.jsx` | The slot configuration, used for local development and by operators who configure the MFE by hand. |

**Modified files**

| File | Nature of modification |
| --- | --- |
| `src/index.jsx` | Re-export both widgets and the error fallback. |
| `README.rst` | Add what the plugin does and the local development loop. |
| `tutor-contrib-<repository-name>/<module-name>/plugin.py` | Swap the placeholder registration for the two real widgets and add the error fallback. |

</details>

<details>
<summary>Context</summary>

- #810 creates the repository, the package manifest, the build, continuous integration, and the placeholder component this ticket replaces.
- The Tutor packaging ticket creates `tutor-contrib-<repository-name>/` and its registration of the placeholder component into both Progress tab slots; this ticket edits that same registration.
- `openedx/sample-plugin`: its `frontend-plugin-sample/src/plugin.jsx` is a worked example of a Paragon-styled widget written for a plugin slot.
- `openedx/frontend-app-learning`: the two target slots are `src/plugin-slots/ProgressTabCourseGradeSlot/` and `src/plugin-slots/ProgressTabRelatedLinksSlot/`, each with its own `README.md` showing a registration example; `src/course-home/progress-tab/ProgressTab.jsx` shows the surrounding layout; `src/constants.ts` defines the Progress routes; `example.env.config.jsx` at that repository's root is the local development template.
- #733 defines the backend endpoint that #734 will use to decide whether a course has competency criteria.
- #734 builds the first real widget in the main-column slot and adds the competency-course check.
- #739, #740, #743, #747, #751, and #755 are the remaining frontend tickets that build on this package.
- This ticket belongs to epic #730.

</details>
