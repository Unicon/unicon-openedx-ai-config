# [BE] Confirm no UNSTABLE markers remain in the CBE APIs

GitHub: not filed yet (#TBD)
Cached: 2026-10-31

## User Story
As a developer of openedx-core, openedx-platform, or a community plugin, I want every CBE API in openedx-core and openedx-platform to carry no UNSTABLE marker once the Student Progress work is complete, in order to rely on them as stable contracts that change only through the DEPR process.

## Description
openedx-core's README states the convention: an API marked UNSTABLE may change at any time, and every other API is stable, with breaking changes announced through the community DEPR process. #Epic11-TBD removes every UNSTABLE marker from the CBE code when the competency criteria work completes. The Student Progress work merges after that and may add entry points, such as learner status reads, that carry markers of their own. Once the last student progress backend feature merges, this ticket searches both repos again and removes whatever that search finds, so that the release ships with no UNSTABLE marker on any CBE code.

The expected outcome is that the search finds nothing, because #Epic11-TBD already removed everything and new entry points were added without markers. The ticket exists to confirm that, not to assume it. If the search finds nothing, the ticket closes with a comment recording the search and its empty result.

## Context
- This ticket runs after the last student progress backend feature merges. Removing a marker commits the function to DEPR for any later breaking change, so it is the last change before release.
- #Epic11-TBD removes the markers the competency criteria work leaves, and is where the starting inventory lives.

## Acceptance Criteria

There is no manual QA path. Acceptance is determined by a PR reviewer, or by the closing comment when there is no PR, verifying the following against the code:

- [ ] Searching openedx-core and openedx-platform for `UNSTABLE` finds no marker on any CBE code: nothing under `src/openedx_learning/applets/cbe/` in openedx-core, its REST API included, and nothing in the CBE code openedx-platform holds.
- [ ] If the search found markers, every docstring that held one still reads as a complete contract description without it, and the PR touches docstrings and comments only, with the existing tests passing unchanged.
- [ ] If the search found nothing, the closing comment names the commits searched in each repo and states that no marker was found.

<details>
<summary>Technical Details</summary>

This is a suggested approach, not the source of truth. The User Story, Description, and Acceptance Criteria define what must be true when the work is done.

**Approach**

1. Run a repo-wide search for `UNSTABLE` in openedx-core over `src/`, `docs/`, and `README.rst`, and in openedx-platform over the CBE code it holds.
2. For each marker found on CBE code, delete the UNSTABLE paragraph from the docstring and leave the rest of the docstring as it is. One PR per repo that needs one.
3. If nothing is found, close the ticket with a comment naming the searched commits.

Starting point, from a search on 2026-10-31: the only CBE markers are the 17 in openedx-core that #Epic11-TBD removes, all in `src/openedx_learning/applets/cbe/`. openedx-platform holds none on CBE code. Entry points the Student Progress epics add after that date are what this ticket is for.

**Additional context**

- The README's one sentence on the convention stays as it is. No file under `docs/` mentions the markers, and openedx-core keeps no changelog file, so no documentation changes with this ticket.

</details>
