# [FE] Right Side Course Competency Progress

GitHub: https://github.com/openedx/openedx-core/issues/743 (#743, OPEN)
Cached: 2026-09-21

## User Story
As a learner, I want to be able to see a high level summary of my overall status on the top level competencies assessed in my course in order to understand the big picture of my progress.

## Description
This ticket will replace the placeholder student competency status right hand side with the real one, which will consist of a card titled "Course Progress" with a subtitle of "Focus Areas". Underneath that will be a box stating the tag name of each competency for which a card displayed in the central competency in #734 along with the same status displayed as part of #740. In a course with no competency criteria, nothing from this ticket renders in the right column.

## Context
- #734 already contains the calculation for what the top level competencies are, because they are the competencies for which cards are created in this ticket.
- #740 already contains the calculation for which competency status to display
- Displaying the Recommended Next Action is out of scope for this ticket because it will be handled in #755.
Blocked by #734, #739, and #740.

## Notes for drafting

- #734 leaves #829's sidebar registration and placeholder component in place, so learners see #829's placeholder until this ticket ships (decided 2026-10-21; #734's Technical Details step 8 and Files table still say the registration is removed and need editing). This ticket replaces the body of #829's `CompetencyProgressSummary` component. Keep that component name: it is a named export of the published package, and renaming it would break any operator configuration that imports it. The registration lives in one place, `getPluginSlots` in `src/pluginSlots.js`, which both `example.env.config.jsx` and tutor-mfe call. Tutor sites pick up the change only after tutor-mfe's pinned package version is bumped, which #828 leaves open.
- Decided in #740's pre-handoff check: the Focus Areas sidebar must read competency statuses through the shared hook from #739, which applies the masking rule (a competency is masked while any of its criteria in this course has a hidden score, propagated to every ancestor tag). Reading #738's raw statuses would reveal what the competency cards hide.
- #755 renders its own `RecommendedNextAction` component into this ticket's Course Progress card (#755's Files table lists that card as modified). This ticket does no Recommended Next Action work. What it owes #755: the whole right-hand panel renders nothing in a course with no competency criteria, so #755's expensive #754 call never fires there; a named card component file that #755 can modify; a place below the Focus Areas rows where the notice goes; and a definite heading level (see the decisions below).

### Decisions from the pre-handoff check (2026-10-21)

- Card set and order: one Focus Area row per card that #734 renders, showing that card's heading label and the card's heading status pill from #740, in the same order as the cards. This ticket never re-derives the card set. #734 is to be revised so that a card's heading is always the topmost-level ancestor tag (for example "Problem Solving", not "Problem Definition" with a breadcrumb), so that card order within a taxonomy is the taxonomy's own tag order, and the per-taxonomy heading above the central cards stays. Two #740 scenarios that assume a heading below the top level go stale with that revision.
- Panel states: the panel follows #734's central panel exactly. It appears only when the cards appear (criteria non-empty and the outline loaded). Rows show their labels at once; pills appear when statuses land, with no temporary "Available". If the status request fails, rows show labels with no pills, as #740's headings do. An outline failure hides the whole panel, including #755's notice.
- Headings: "Course Progress" is an `h2`, matching the stock Course completion and Grades card titles. "Focus Areas" is an `h3`, and #755's "Recommended Next Action" heading is an `h3` sibling of it. The rows are a list. When the course's cards span more than one taxonomy, the rows are grouped under an `h4` subheading per taxonomy name; with one taxonomy there is no subheading. The mock shows only the single-taxonomy case, so @illiphilli needs to design the grouped case.
- Placement: the card renders above everything else in the right column, and the stock right-column content (certificate status panel, related links) keeps rendering below it. #829 owns the registration and is to be edited (decided 2026-10-21) so that `competency_progress_summary` registers into `org.openedx.frontend.learning.progress_tab_certificate_status_side_panel.v1`, the first slot in the right column on frontend-app-learning master, instead of the related links slot, at priority 20 with `keepDefault` left true. This ticket therefore changes no slot configuration and only replaces the placeholder component's body. The slot id comes from a lookup of frontend-app-learning master on 2026-10-21; confirm it against `src/course-home/progress-tab/ProgressTab.jsx` when drafting.
- Small screens: both columns are full width below the `md` breakpoint, so the right column stacks below the whole main column and this card lands at the bottom of the page. Accepted for this ticket; note it for @illiphilli.
- Rows are plain text, not links, matching #734's rule that no tag name is a link. There is no cap on the number of rows; long names wrap.
- "Course Progress" and "Focus Areas" are fixed, translatable strings in `src/messages.js`. Tag names show as stored. Status labels reuse #740's rendering (`StatusOval` without a score), and the AC says "the heading's status as #740 shows it" rather than listing statuses.
- No new operator setting to hide the card; an operator's own `pluginSlots` configuration already can.
- Data: the sidebar re-runs #734's `useCompetencyCards` and #739's `useCompetencyStatuses` and relies on the plugin's single module-level `QueryClient` to dedupe requests across the two slots (#739 names #743 as a consumer of that cache). No shared selector; one caller. Require a test that mounts both widgets together and asserts each endpoint is requested once.
- Staff viewing a specific learner flows through `useProgressRouteParams` into `useCompetencyStatuses`, so #740's staff masking rule applies with no new work. The AC carries one staff scenario mirroring #740's.
- Nothing owed to #744 by this ticket, but #744 should document: a top-level row's status comes from #643's roll-up and reads "Available" until #643 ships; one hidden-score exam masks its whole top-level row; statuses span all of the learner's courses, so "Course Progress" can read "Partially Attempted" after everything in this course is done; and a site that writes its own `pluginSlots` instead of calling `getPluginSlots` must register the widget by hand.
- Unresolved, raised by the BA and not verified by Claude: the mock's grey "Available" pill versus #740's blue/white specification, and "Not Demonstrated" in the mock's legend versus #740's three heading statuses. Exact pill parity with the central card headings is the rule; whichever side is wrong gets fixed, and the AC does not restate colors.
