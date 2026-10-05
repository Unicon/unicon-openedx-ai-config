# [Placeholder - FE] Build a right sidebar (or central) display of top level competencies ("Focus Areas") with their Competency status displayed.

GitHub: https://github.com/openedx/openedx-core/issues/743 (#743, OPEN)
Cached: 2026-09-21

_No description yet — placeholder issue._

## Notes for drafting

- #734 removes the `competency_progress_summary` sidebar registration (from #829) from the plugin's `example.env.config.jsx` and from the Tutor plugin's slot mapping, so learners don't see #829's sidebar placeholder text. This ticket must re-add that registration, in both files, when it builds the real sidebar.
