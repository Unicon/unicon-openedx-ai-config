# Competency Criteria: epic index

GitHub (`openedx/openedx-core`) is the source of truth. This README and the ticket
files under each epic folder are a local cache for reference, so Claude and whoever is
drafting tickets can read them without re-fetching from GitHub every time. If a file here
looks stale, trust the linked GitHub issue over the local copy.

Each epic below is its own GitHub issue in `openedx/openedx-core`, using GitHub's native
sub-issues feature to link its tickets. The epic number is the "Column D" number from the
master spreadsheet, [Competency Criteria & Learner Progress Package Summary](https://docs.google.com/spreadsheets/d/1eArBhSKZK2k4qU4LOSdFVlKHcDz2ON6YsnrfifjF5FA/edit)
(epic tab), which stays the source of truth for epic and use-case numbers; this README
is not a copy of it and can drift, so check the sheet itself when a number matters. Folder
names are `<epic-number>-<short-slug>-<github-epic-issue-number>`.

| Epic # | GitHub epic | Title | Folder |
| --- | --- | --- | --- |
| 1 | [#718](https://github.com/openedx/openedx-core/issues/718) | Competency Taxonomy Type | `01-competency-taxonomy-type-718/` |
| 2 | [#719](https://github.com/openedx/openedx-core/issues/719) | Separate Taxonomy Editing and Competency Management Pages | `02-separate-taxonomy-editing-and-competency-management-pages-719/` |
| 4 | [#720](https://github.com/openedx/openedx-core/issues/720) | Initial Competency Management Page | `04-initial-competency-management-page-720/` |
| 5 | [#721](https://github.com/openedx/openedx-core/issues/721) | Competency Criteria Associations | `05-competency-criteria-associations-721/` |
| 6 | [#722](https://github.com/openedx/openedx-core/issues/722) | Competency Rule Profile (org/course/taxonomy scoped) | `06-competency-rule-profile-722/` |
| 10 | [#723](https://github.com/openedx/openedx-core/issues/723) | Competency Guardrails | `10-competency-guardrails-723/` |
| 11 | [#724](https://github.com/openedx/openedx-core/issues/724) | Course Copy Carries Competency Criteria | `11-course-copy-carries-competency-criteria-724/` |
| 13 | [#725](https://github.com/openedx/openedx-core/issues/725) | Competency Mastery Status Evaluation | `13-competency-mastery-status-evaluation-725/` |

**Epic 6 (#722) is marked Out of Scope** in both its GitHub title (`[OOS-EPIC-CC]`) and the
spreadsheet; its sub-issues are cached here anyway for reference, but treat them as
parked, not active backlog.

**Epic numbers 3, 7, 8, 9, and 12 don't exist in this workstream.** Per the spreadsheet
owner, they were deemed out of scope before the SOW was signed, so there is intentionally
no epic 3, 7, 8, 9, or 12 folder here.

Each ticket file inside an epic folder is named `ucid-<epic-number>.xx-ghi-<issue-number>.md`.
The `.xx` is a placeholder: the per-ticket "Use Case" number from the spreadsheet could not
be reliably bulk-extracted (the sheet's export flattens multi-paragraph cells in a way that
breaks row boundaries for some tickets), so only the GitHub issue number is guaranteed
accurate here. Rename a file to its real `ucid-<epic>.<use-case>` once you've confirmed the
number against the spreadsheet.
