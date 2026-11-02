# [BE] Remove the UNSTABLE markers from the CBE APIs

GitHub: not filed yet (#TBD)
Cached: 2026-10-31

## User Story
As a developer of openedx-platform or a community plugin, I want the CBE APIs in openedx-core and openedx-platform to carry no UNSTABLE marker once the competency criteria work is complete, in order to rely on them as stable contracts that change only through the DEPR process.

## Description
openedx-core's README states the convention: an API marked UNSTABLE may change at any time, and every other API is stable, with breaking changes announced through the community DEPR process. While the competency criteria work was in progress, the CBE applet's public functions, REST serializers, and REST views were marked UNSTABLE. Once the last feature PR of this epic merges, this code is complete for the release, and this ticket removes their markers so the functions read as the stable contracts they now are.

The definition of done is that no UNSTABLE marker of any CBE code remains anywhere in openedx-core or openedx-platform, found by searching the code at implementation time. The counts and locations in Technical Details are what a search found on the day this ticket was written. They are a starting point, not an inventory: a marker that was missed that day, or added after it, is in scope all the same.

## Context
- This ticket runs after the last feature PR of this epic merges. Removing a marker commits the function to DEPR for any later breaking change, so it is the last change before release.
- #SP10-TBD confirms that there are still no UNSTABLE markers once the Student Progress work completes.

## Acceptance Criteria

There is no manual QA path. Acceptance is determined by a PR reviewer verifying the following against the code:

- [ ] Searching openedx-core and openedx-platform for `UNSTABLE` finds no marker on any CBE code: nothing under `src/openedx_learning/applets/cbe/` in openedx-core, its REST API included, and nothing in the CBE code openedx-platform holds. Markers not listed in Technical Details count the same as the ones that are.
- [ ] Every docstring that held a marker still reads as a complete contract description without it: no dangling "so its shape may change" clause and no empty paragraph.
- [ ] No behavior changes: each PR touches docstrings and comments only, and the existing tests pass unchanged.

<details>
<summary>Technical Details</summary>

This is a suggested approach, not the source of truth. The User Story, Description, and Acceptance Criteria define what must be true when the work is done.

**Approach**

1. Run a repo-wide search for `UNSTABLE` in openedx-core over `src/`, `docs/`, and `README.rst`, and in openedx-platform over the CBE code it holds. The search result at implementation time is the inventory.
2. Delete the UNSTABLE paragraph from each docstring the search finds on CBE code. Leave the rest of each docstring as it is.
3. Re-read each edited docstring once, so the sentence before the removed paragraph still ends the thought.
4. One PR per repo. The openedx-platform PR exists only if the search there finds a marker.

Starting point, from a search of upstream main in openedx-core and upstream master in openedx-platform on 2026-10-31:

| Repo | Markers | Files |
| --- | --- | --- |
| openedx-core | 17 | `src/openedx_learning/applets/cbe/api.py` (12), `src/openedx_learning/applets/cbe/rest_api/v1/serializers.py` (3), `src/openedx_learning/applets/cbe/rest_api/v1/views.py` (2) |
| openedx-platform | 0 | The two `UNSTABLE` hits in the platform are in code unrelated to CBE and stay. |

**Additional context**

- The README's one sentence on the convention stays as it is. No file under `docs/` mentions the markers, and openedx-core keeps no changelog file, so no documentation changes with this ticket.
- #SP10-TBD repeats the search once the Student Progress work completes, since that work merges after this ticket and may add entry points with markers of their own.

</details>
