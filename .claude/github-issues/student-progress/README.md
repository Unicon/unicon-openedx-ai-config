# Student Progress: epic index

GitHub (`openedx/openedx-core`) is the source of truth. This README and the ticket
files under each epic folder are a local cache for reference, so Claude and whoever is
drafting tickets can read them without re-fetching from GitHub every time. If a file here
looks stale, trust the linked GitHub issue over the local copy.

Each epic below is its own GitHub issue in `openedx/openedx-core`, using GitHub's native
sub-issues feature to link its tickets. The epic number is the "Column D" number from the
master spreadsheet, [Competency Criteria & Learner Progress Package Summary](https://docs.google.com/spreadsheets/d/1eArBhSKZK2k4qU4LOSdFVlKHcDz2ON6YsnrfifjF5FA/edit)
(sprint-planning tab), which stays the source of truth for epic and use-case numbers; this
README is not a copy of it and can drift, so check the sheet itself when a number
matters. The epic number carries an `SP` prefix in both the spreadsheet and the GitHub
epic field for this workstream. Folder names are `SP<epic-number>-<short-slug>-<github-epic-issue-number>`.

Most sub-issues in this workstream are still placeholders (title only, BA-created, no
description yet). This cache holds whatever is currently on GitHub, placeholder or not.

| Epic # | GitHub epic | Title | Folder |
| --- | --- | --- | --- |
| SP2 | [#730](https://github.com/openedx/openedx-core/issues/730) | View Competency Criteria Gradeable Subsections | `SP02-view-competency-criteria-gradeable-subsections-730/` |
| SP3 | [#736](https://github.com/openedx/openedx-core/issues/736) | View Competency Status of Gradeable Subsections | `SP03-view-competency-status-of-gradeable-subsections-736/` |
| SP4 | [#742](https://github.com/openedx/openedx-core/issues/742) | Competency Status Summary Sidebar | `SP04-competency-status-summary-sidebar-742/` |
| SP7 | [#745](https://github.com/openedx/openedx-core/issues/745) | Competency Status Sunburst | `SP07-competency-status-sunburst-745/` |
| SP8 | [#749](https://github.com/openedx/openedx-core/issues/749) | Competency Status Sunburst Tooltip | `SP08-competency-status-sunburst-tooltip-749/` |
| SP10 | [#753](https://github.com/openedx/openedx-core/issues/753) | Recommended Next Action | `SP10-recommended-next-action-753/` |

**Epic numbers SP1, SP5, SP6, and SP9 don't exist in this workstream** (consistent with the
gaps in Competency Criteria's numbering: work deemed out of scope before the SOW was
signed). There is intentionally no SP1, SP5, SP6, or SP9 folder here.

Each ticket file inside an epic folder is named `ucid-SP<epic-number>.xx-ghi-<issue-number>.md`.
The `.xx` is a placeholder: the per-ticket "Use Case" number from the spreadsheet could not
be reliably bulk-extracted (the sheet's export flattens multi-paragraph cells in a way that
breaks row boundaries for some tickets), so only the GitHub issue number is guaranteed
accurate here. Rename a file to its real `ucid-SP<epic>.<use-case>` once you've confirmed the
number against the spreadsheet.
