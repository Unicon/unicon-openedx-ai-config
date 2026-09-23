# [Placeholder - FE] Let the operator render the CBE progress panel in place of the Progress tab's Grades card

GitHub: not yet filed. Depends on #734 and #828.

_No description yet — placeholder issue._

## Known scope, decided during #734's pre-handoff check

- #734 renders the competency criteria panel above the stock "Grades" card, the default content of `ProgressTabCourseGradeSlot`. The Figma shows the panel with no Grades card, which is the "in place of" layout this ticket adds.
- The operator chooses between "above" and "in place of". "In place of" uses `PLUGIN_OPERATIONS.Wrap` on the slot's `default_contents`, with a wrapper that renders the stock Grades card only in courses with no competency criteria. That wrapper needs #734's check against #733's endpoint, which is why this ticket follows #734.
- Extends #828's data-driven Tutor slot mapping rather than rewriting it.
- frontend-app-learning#1905 moves plugin slots to frontend-base's `Slot` API, so the `PLUGIN_OPERATIONS.Wrap` mechanism may change before this ticket is built.
