# [BE] Add filtering to GET Competency Criteria & Groups

GitHub: https://github.com/openedx/openedx-core/issues/682 (#682, OPEN)
Cached: 2026-09-21

## User Story

As a Platform Administrator, I want to see only the criteria for the course runs I am currently browsing, and to be told how many of the competency's criteria that leaves out of view, in order to keep editing a competency that has been reused across many course runs without loading or scrolling through every run it has ever been attached to.

## Acceptance Criteria

```
Scenario: No course-run scope supplied
  Given a competency has criteria attached under several course runs
  When a caller requests that competency's criteria structure with no course-run scope
  Then every one of the competency's criteria groups and criteria is returned
  And the response reports that the number of criteria in view equals the competency's instance-wide total

Scenario: Scoped to specific course runs
  Given a competency has criteria attached under ten course runs
  When a caller requests that competency's criteria structure scoped to three of those course runs
  Then the competency's instance-wide criteria structure is returned
  And the complete criteria structure for each of those three course runs is returned, with no part of any of them omitted
  And nothing belonging to the other seven course runs is returned
  And the number of criteria the response reports as in view matches the number of criteria actually returned

Scenario: Course runs are returned in the order they were requested
  Given a competency has criteria attached under course runs C, A, and B
  When a caller requests that competency's criteria structure scoped to C, A, and B in that order
  Then the competency's instance-wide criteria structure comes first
  And the criteria structures for C, A, and B follow in that same order
  And a caller that reorders its request gets the criteria structures back in the new order, without having to reorder them itself

Scenario: Scoped to an empty set of course runs
  Given a competency has criteria attached under several course runs
  When a caller requests that competency's criteria structure scoped to an empty set of course runs
  Then only the competency's instance-wide criteria structure is returned
  And the request succeeds rather than being treated as an error
  And the response still reports the competency's true instance-wide criteria total

Scenario: Gaps in the requested list of course runs are ignored
  Given a competency has criteria attached under course runs A and B
  When a caller requests that competency's criteria structure scoped to a list that contains A and B but also has a stray separator, whether trailing or between the two
  Then the result is identical to requesting A and B with no stray separator
  And the request is not refused

Scenario: A list containing nothing but gaps
  Given a competency has criteria attached under several course runs
  When a caller requests that competency's criteria structure scoped to a list made up only of stray separators
  Then the result is identical to requesting an empty set of course runs
  And the request is not refused

Scenario: More course runs requested than the endpoint accepts
  Given a caller has a list of course runs longer than the endpoint's limit
  When the caller requests a competency's criteria structure scoped to that list
  Then the request is refused with an explanation naming the limit
  And no partial or truncated criteria structure is returned

Scenario: A malformed course-run identifier
  Given a caller's list of course runs includes one entry that is neither a valid course-run identifier nor a stray separator
  When the caller requests a competency's criteria structure scoped to that list
  Then the whole request is refused with an explanation
  And no criteria structure is returned

Scenario: A valid course-run identifier that matches no course run
  Given a caller's list of course runs includes a well-formed identifier for a course run that no longer exists
  When the caller requests a competency's criteria structure scoped to that list
  Then the request succeeds
  And the criteria structures for the course runs that do exist are returned as normal, still in the order the caller listed them
  And the identifier that matched nothing produces no error and no empty placeholder

Scenario: The same course run requested more than once
  Given a caller's list of course runs names the same course run twice
  When the caller requests that competency's criteria structure scoped to that list
  Then that course run's criteria structure is returned exactly once, in the position where it was first named
  And its criteria are counted once toward the number reported as in view

Scenario: A competency with no criteria anywhere
  Given a competency has no criteria attached to it under any course run
  When a caller requests that competency's criteria structure, with or without a course-run scope
  Then no criteria are returned
  And the response reports both the number in view and the instance-wide total as zero

Scenario: Criteria exist, but none in the requested scope
  Given a competency has criteria attached under course runs A and B
  When a caller requests that competency's criteria structure scoped to course run C only
  Then no criteria are returned
  And the response reports zero criteria in view
  And the response reports a non-zero instance-wide total, so the caller can tell the competency is not empty

Scenario: Removed criteria are excluded from what is shown and from both counts
  Given a competency has criteria under a course run, some of which have been removed
  When a caller requests that competency's criteria structure scoped to that course run
  Then only the criteria that have not been removed are returned
  And neither the number reported as in view nor the instance-wide total includes any removed criterion
  And the number reported as in view matches the number of criteria actually returned

Scenario: Counts cover the selected competency only
  Given a competency has sub-competencies, and those sub-competencies have criteria of their own
  When a caller requests the parent competency's criteria structure
  Then only the parent competency's own criteria are returned
  And neither the number in view nor the instance-wide total includes any sub-competency's criteria

Scenario: Scoping does not change who may read a competency's criteria
  Given a caller does not have permission to view the competency
  When the caller requests that competency's criteria structure scoped to course runs they can otherwise see
  Then the request is refused for lack of permission
  And no criteria, and neither count, are disclosed
```

## Description

The criteria structure is bounded by limiting what a caller asks for, not by splitting the answer into pages: a caller names the course runs it wants and receives the complete criteria for each of those, never part of one. Which course runs are in view is decided by the caller before it calls this endpoint (see \#669 and \#670); this endpoint does not search or filter courses itself, it only accepts the course runs it is given.

<details>
<summary>Technical Details</summary>
This section is background and a suggested approach, not the ticket's source of truth. The User Story and Acceptance Criteria define what must be true when the work is done; what follows exists to save the implementer some thinking, not to bind them.

### In short

**What changes.** This is an additive extension to the competency criteria endpoint that \#681 introduces, `GET /cbe/rest_api/v1/competencies/<competency_tag_id>/criteria-groups/`, and to the function behind it, `get_competency_criteria_tree`. The endpoint gains one optional query parameter, `course_keys`, holding a comma-separated list of course run key strings, and the response gains two integer counts. Whether it's omitted, sent empty, or populated determines which of the three Acceptance Criteria states applies; omitting it is \#681's existing unfiltered behavior, kept for admin, export, and debugging use.

**Deciding what is in scope.** The course run keys arrive already resolved by the caller: deciding which course runs are in view, including title search, date filtering, and paging, is the job of \#669 and \#670. This endpoint turns those keys into internal `CourseRun` ids through a new bulk resolver in `openedx_catalog`, then selects groups with a single predicate: the group belongs to this competency, and either it has no course scope at all or its course scope is one of the resolved ids. Every group inside a course-scoped subtree carries the course id, not just the top one, so "no course scope" picks out exactly the instance-wide subtree, and the three states need almost no branching: with no ids the predicate degrades to "no course scope," and with the parameter absent the course clause is dropped entirely.

**Normalizing what the caller sent.** The raw parameter is parsed into course keys before any of the Acceptance Criteria scenarios above apply, handling stray separators, duplicates, and the length cap in one pass; see Implementation specifics for the exact order and the status codes involved.

**Ordering the response.** \#681's response is two flat arrays, `groups` and `criteria`, that a client reassembles into a tree using the parent references each row carries. Course scoping ranks each row by its course run's position in the caller's request, matching the order guaranteed in Acceptance Criteria; sorting happens in Python after the rows are fetched, since the cap already bounds how many rows there can be.

**The two counts.** `criteria_count` and `total_criteria_count` are what the Acceptance Criteria call the number of criteria in view and the instance-wide total. The numerator costs nothing extra, because it is a count of the criteria rows the response already loaded. The denominator is one additional `COUNT(*)`. The important property is that the denominator is the numerator's query with the course-scope predicate removed and nothing else changed, in particular the same exclusion of archived groups and archived criteria; if the two queries filter differently, the unfiltered case stops satisfying its own acceptance criterion that the two numbers agree. Both counts cover the selected competency's own criteria only, filtering on that one tag id exactly.

**The layering contract.** `openedx_catalog` is currently absent from `.importlinter`'s package list even though it is a real Django app, so no rule governs who may import it. This ticket is the first code to import it from another app, via the bulk resolver, so it is the natural moment to give it a declared position. It belongs beside `openedx_tagging` as a peer: `openedx_catalog` imports only `openedx_django_lib`, and `openedx_tagging` stays generic about what it tags.

### Implementation specifics

- **Signature.** `get_competency_criteria_tree(tag_id: int, course_keys: list[CourseKey] | None = None) -> CompetencyCriteriaTree` in `src/openedx_learning/applets/cbe/api.py`. `None` means unfiltered, `[]` means instance-wide subtree only; the docstring must state that distinction explicitly, since it is the whole contract.  
- **Return type.** Add `criteria_count: int` and `total_criteria_count: int` to the `CompetencyCriteriaTree` dataclass and populate both inside `get_competency_criteria_tree`, so the two counts always share exactly the same filters.  
- **Query-parameter parsing.** Add a `CompetencyCriteriaQueryParamsSerializer` alongside \#681's serializers, following the existing `*QueryParamsSerializer` pattern in `src/openedx_tagging/rest_api/v1/serializers.py`, fed from `request.query_params.dict()` as in that app's views. The field is `serializers.CharField(required=False, allow_blank=True)` with no `default`, so the three states stay distinguishable by testing whether the key is present in `validated_data`.  
- **Normalization order, exactly.** Split on `,`; strip each element; drop empty elements; reject with 400 if more than 100 elements remain; parse each remaining element with `CourseKey.from_string`, converting `InvalidKeyError` into a 400 for the whole request; de-duplicate with `dict.fromkeys` to preserve first-occurrence order. Duplicates count toward the 100 limit because the limit is applied before de-duplication.  
- **Cap.** 100 entries, rejected with HTTP 400 whose detail names the number. Comma-separated list parameters already exist in this codebase without a cap (`get_object_tag_counts` in `src/openedx_tagging/api.py`); this endpoint caps deliberately, because a bounded input is what lets the response guarantee complete subtrees.  
- **Group predicate.** `oel_tagging_tag_id = <tag> AND (course_id IS NULL OR course_id IN <resolved ids>)`, with the parenthesized clause omitted entirely when `course_keys` is `None`. Filter on the exact tag id, so sub-competency criteria stay out of the result and both counts.  
- **Bulk resolver.** Add `get_course_run_ids(course_keys: Iterable[CourseKey]) -> dict[CourseKey, CourseRun.ID]` to `src/openedx_catalog/api_impl.py` and list it in that module's `__all__`. It runs one `CourseRun.objects.filter(course_key__in=...).values_list("course_key", "id")`; keys with no matching row are simply absent from the returned mapping, so a stale key resolves silently. Matching is case-sensitive, consistent with `get_course_run`. An empty input returns an empty dict directly.  
- **Ordering.** Build `{course_run_id: index}` from the de-duplicated request list and sort `groups` and `criteria` in Python by that rank as the primary key, with unscoped rows ranked ahead of every scoped one. Leave \#681's existing within-subtree ordering as the secondary key, and tie-break by `id` so the order is total. A criterion inherits its parent group's rank, so a client walking either array sees the same course sequence.  
- **Counts and the archived filter.** Both counts are of `CompetencyCriterion` rows reached through `CompetencyCriteriaGroup.oel_tagging_tag_id`. Both exclude rows where the criterion is archived or its group is archived. `total_criteria_count` is one extra `COUNT(*)`, built as the numerator's query with the course-scope predicate removed and every other filter identical; `criteria_count` costs no query, it is the length of the criteria list already loaded. The `archived` column comes from \#716.  
- **Permission and error precedence.** Reuse `CompetencyReadPermission` in `src/openedx_learning/applets/cbe/rest_api/v1/permissions.py` unchanged. Fetch the competency tag and run the permission check before parsing `course_keys`, so a caller who lacks permission gets 403 and a nonexistent competency gets 404, ahead of any 400 about their query string.  
- **Indexes.** ADR 0002 Decision 5's `CompetencyCriteriaGroup(oel_tagging_tag_id, course_id)` and `CompetencyCriteria(competency_criteria_group_id)` already cover both the scoped read and the instance-wide count.  
- **Layering.** Add `openedx_catalog` to `root_packages` in `.importlinter`, and to the `src_layering` contract on the same line as `openedx_tagging` using the existing peer syntax (`openedx_tagging | openedx_catalog`, matching how `components | containers` is already written). Verify with `lint-imports`.  
- **Tests.** In `tests/openedx_learning/applets/cbe/test_api.py`, cover the three parameter states, request-order preservation including a reordered request, duplicate collapsing to first position, a well-formed key matching no `CourseRun`, criteria present but none in scope (zero numerator, non-zero denominator), a competency with no criteria at all (both zero), archived criteria and archived groups excluded from the returned rows and from both counts, and a parent competency whose sub-competencies have criteria of their own. In `tests/openedx_learning/applets/cbe/test_rest_api.py`, cover trailing and doubled commas, a value of only commas, a malformed key, 101 entries rejected with the limit named, and a 403 that discloses neither count. In `tests/openedx_catalog/test_api.py`, cover the resolver's empty input, unknown key, and duplicate key cases.  
- **Companion tickets.** Wiring the authoring frontend to this parameter is \#683. Resolving which course runs are in view, including title search, date filtering, and paging, is \#669 and \#670.

Files to create and modify **Modified files**

| File | Nature of modification |
| :---- | :---- |
| `src/openedx_learning/applets/cbe/api.py` | Add optional `course_keys` to `get_competency_criteria_tree`; add both count fields to `CompetencyCriteriaTree`. |
| `src/openedx_learning/applets/cbe/rest_api/v1/serializers.py` | Add the query-params serializer and the two count fields to the response (file created by \#681). |
| `src/openedx_learning/applets/cbe/rest_api/v1/views.py` | Parse and validate `course_keys` after the permission check, then pass it through (file created by \#681). |
| `src/openedx_catalog/api_impl.py` | Add the bulk course-key-to-id resolver and list it in `__all__`. |
| `.importlinter` | Add `openedx_catalog` to `root_packages` and as a peer of `openedx_tagging` in `src_layering`. |
| `tests/openedx_learning/applets/cbe/test_api.py` | Scope, ordering, de-duplication, archived-exclusion, and count cases. |
| `tests/openedx_learning/applets/cbe/test_rest_api.py` | Query-parameter validation, cap, and error-precedence cases (file created by \#681). |
| `tests/openedx_catalog/test_api.py` | Resolver cases: empty input, unknown key, duplicate key. |

- Context \#681 defines the endpoint and the `get_competency_criteria_tree` function this ticket extends; this work is additive to both and adds no new endpoint.  
- \#613 (the `CompetencyCriteriaGroup` and `CompetencyCriterion` models) and \#716 (their `archived` column) must both land before this work can start.  
- \#676 holds the backend design reasoning behind scoping by caller-supplied course keys rather than by a server-side course query. A follow-up amendment to ADR 0002's retrieval-scope and pagination wording is tracked on \#676 and is not part of this ticket's work; the ADR's current text predates this design.  
- `docs/openedx_learning/decisions/0002-competency-criteria-model.rst` for the criteria data model, and Decision 5 for the existing indexes this access pattern relies on.  
- Prior art for the query-parameter serializer pattern: `src/openedx_tagging/rest_api/v1/serializers.py` and `src/openedx_tagging/rest_api/v1/views.py`. Prior art for a comma-separated list parameter: `get_object_tag_counts` in `src/openedx_tagging/api.py`.  
- `src/openedx_catalog/api.py`'s module docstring states that the catalog app provides no "list courses" methods because course visibility is not modeled there. That is why the caller resolves which course runs are in view and passes their keys in.  
- `src/openedx_catalog/models/course_run.py`'s class docstring is the rule against ever exposing `CourseRun`'s integer primary key in an API, which is why the parameter and the response both speak in course keys.
</details>
