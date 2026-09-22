# [Placeholder - FE] Build collapsable table display of Competency Criteria on the Course Progress page

GitHub: https://github.com/openedx/openedx-core/issues/734 (#734, OPEN)
Cached: 2026-09-22

_No description yet — placeholder issue._

## Known scope, decided while drafting SP02.06/07/08

Not yet drafted as a real ticket. These are commitments made while scoping the plugin starter tickets that land here when #734 is actually written:

- Replaces the `CompetencyProgressPanel` placeholder (from SP02.08) with the real collapsible competency criteria table, in the main-column Progress tab slot.
- Owns gating: calls #733's endpoint to decide whether the course has competency criteria, and renders nothing when it does not. That check runs on every Progress tab render for every course on the site, including the large majority with no competency data, so #733 should be specified knowing it has this consumer (candidates: the criteria response itself doubles as the answer, or the Progress tab's existing course metadata carries a boolean, cheaper on the hot path but needs an `openedx-platform` change).
- Owns the operator's placement choice: render the panel above the stock Grade Summary card (the only option SP02.08 ships) or in place of it. "In place of" needs `PLUGIN_OPERATIONS.Wrap` on `default_contents` with a wrapper that renders the stock card only in non-competency courses, confirmed feasible against the Frontend Plugin Framework source. Extends SP02.07's Tutor plugin registration, already written as a data-driven mapping for exactly this, rather than rewriting it.
- Whoever adds the gating fetch must catch its own failures and report them explicitly; a React error boundary does not catch errors thrown from async callbacks.
- Sizing flag from the architect's review: the table, the gate, and the operator placement choice together read as more than a 1-2 day ticket. Worth splitting when this is actually scoped.

Depends on #733, SP02.07, and SP02.08.
