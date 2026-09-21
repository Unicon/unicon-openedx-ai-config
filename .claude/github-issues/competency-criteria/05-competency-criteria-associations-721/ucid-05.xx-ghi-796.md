# [BE] Read which courses are blocked for a competency by dominance rules

GitHub: https://github.com/openedx/openedx-core/issues/796 (#796, OPEN)
Cached: 2026-09-21

**Blocked by:** \#666 (this ticket calls `get_courses_with_relative_criteria(tag_ids)`, the public function \#666's own updated draft now builds for its own write-time rejection; see Technical Details).

Repo: `openedx-core`, single-repo. No `openedx-platform` changes — this route registers inside the same `rest_api/v1/urls.py` \#665/\#674/\#675/\#681 already wire into Studio.

## User Story

As a course author managing Competency Criteria for a competency, I want to see which courses already have a taxonomy ancestor or descendant of that competency associated with content, in order to avoid attempting an association that \#666 will reject anyway.

## Acceptance Criteria

```
Scenario: A course is blocked by an ancestor's existing claim
  Given a CompetencyCriterion already associates tag "Critical Thinking" (an ancestor of "Inference") with a subsection in Course X
  When a caller requests the blocked courses for tag "Inference"
  Then Course X appears in the response
  And the conflicting tag reported for Course X is "Critical Thinking"

Scenario: A course is blocked by a descendant's existing claim
  Given a CompetencyCriterion already associates tag "Inference" (a descendant of "Critical Thinking") with a subsection in Course X
  When a caller requests the blocked courses for tag "Critical Thinking"
  Then Course X appears in the response
  And the conflicting tag reported for Course X is "Inference"

Scenario: The block reaches a grandparent or grandchild, not just an immediate parent or child
  Given "Cognitive Skills" is the parent of "Critical Thinking", which is the parent of "Inference"
  And a CompetencyCriterion already associates "Cognitive Skills" with a subsection in Course X
  When a caller requests the blocked courses for tag "Inference"
  Then Course X appears in the response
  And the conflicting tag reported for Course X is "Cognitive Skills"

Scenario: A course claimed only by a sibling tag is not reported
  Given tags "Inference" and "Analysis" share the same parent tag and are neither ancestor nor descendant of each other
  And a CompetencyCriterion already associates "Analysis" with a subsection in Course X
  When a caller requests the blocked courses for tag "Inference"
  Then Course X does not appear in the response

Scenario: A different course, unaffected by a claim elsewhere, is not reported
  Given a CompetencyCriterion already associates tag "Critical Thinking" (an ancestor of "Inference") with a subsection in Course X
  And no relative of "Inference" has any association in Course Y
  When a caller requests the blocked courses for tag "Inference"
  Then Course Y does not appear in the response

Scenario: A caller narrows the response to a requested set of courses
  Given a CompetencyCriterion already associates tag "Critical Thinking" (an ancestor of "Inference") with a subsection in Course X
  And a CompetencyCriterion already associates tag "Cognitive Skills" (a further ancestor of "Inference") with a subsection in Course Y
  And a CompetencyCriterion already associates tag "Critical Thinking" with a subsection in Course Z
  When a caller requests the blocked courses for tag "Inference", narrowed to Course X and Course Y
  Then Course X and Course Y appear in the response
  And Course Z does not appear in the response

Scenario: No related competency has any claim anywhere
  Given tag "Inference" has ancestors and descendants, none of which has any CompetencyCriterion in any course
  When a caller requests the blocked courses for tag "Inference"
  Then the caller receives an empty collection
  And the request is not reported as having failed

Scenario: Read a collection larger than one response carries
  Given more blocked courses exist for a tag than a single response carries at once
  When a caller requests the blocked courses for that tag
  Then the caller receives part of the collection together with a way to request the remainder
  And requesting the remainder yields the blocked courses not already returned, with none repeated and none skipped

Scenario: A narrowed request that itself spans more than one page still paginates correctly
  Given more courses matching a caller's requested course_keys are blocked for a tag than a single response carries at once
  And at least one other blocked course for that tag exists outside the requested course_keys
  When a caller requests the blocked courses for that tag, narrowed to that set of course_keys
  Then the caller receives part of the requested courses together with a way to request the remainder
  And requesting the remainder yields the rest of the requested courses not already returned, with none repeated and none skipped
  And no course outside the requested course_keys appears on any page

Scenario: Reject a request for a competency that doesn't exist
  Given no tag exists with the requested id
  When a caller requests the blocked courses for that id
  Then the response reports the competency as not found

Scenario: Refuse a caller who may not view the competency's taxonomy
  Given a caller who is not permitted to view the taxonomy tag "Inference" belongs to
  When the caller requests the blocked courses for tag "Inference"
  Then the request is refused
  And no blocked course is returned
```

## Description

This is the read-only counterpart to the dominance rule \#666 enforces at write time: given a competency, which courses already have a taxonomy ancestor or descendant of it associated with content, and are therefore ineligible for a new association under \#666's rule. It exists so the frontend (a separate, sibling ticket, not yet numbered, which consumes this endpoint to gray out ineligible content in the authoring UI) can tell an author before they attempt an invalid selection, rather than after \#666 rejects it.

This ticket never changes what is or isn't allowed. \#666 remains the sole authority on the rule; a stale or racing read here only means an author is rejected on submit the same as today, not a data-integrity problem.

<details>
<summary>Technical Details</summary>

This section is background and a suggested approach, not the source of truth. The User Story and Acceptance Criteria define what must be true when the work is done; the notes below exist to save the implementer some thinking.

### In short

**What the endpoint reads, and at what granularity.** `GET /cbe/rest_api/v1/competencies/<int:tag_id>/blocked-courses/` takes one competency tag and returns every course where a taxonomy ancestor or descendant of that tag already has a `CompetencyCriterion`. The granularity is course-level, matching the rule itself (\#666 blocks per course, not per subsection) and matching what the frontend sibling ticket needs to gray out a course, not a specific subsection within it.

**Optional narrowing to a caller-supplied set of courses.** An optional `course_keys` query parameter, a comma-separated list of course keys (e.g. `?course_keys=course-v1:Org+Course+Run1,course-v1:Org+Course+Run2`), narrows the response to only the requested courses; omitting it returns every blocked course, unchanged from the behavior already specified above. A single comma-separated parameter is used rather than a repeated one (`?course_keys=A&course_keys=B`) because this codebase's existing query-param convention validates params through a small `QueryParamsSerializer` checked against `request.query_params.dict()` (see `TaxonomyListQueryParamsSerializer` on `TaxonomyView`), and `QueryDict.dict()` collapses a repeated key down to its last value, so a repeated-parameter design would silently lose all but one value under that same pattern.

**What this filter optimizes, and what it doesn't.** This is a response-shaping, payload-size optimization, not a database-query optimization: `get_courses_with_relative_criteria` still resolves every `CompetencyCriterion` under the competency's taxonomy relatives regardless of the filter, because a criterion's course can only be known after parsing its `ObjectTag.object_id`. What the filter does save is the size of the response body, and it skips the per-course `CourseRun` lookup during serialization for any course that doesn't pass the filter, not for every matched course.

**Reusing \#666's lookup rather than re-deriving it.** \#666 adds `get_ancestor_tags(tag)` and `get_descendant_tags(tag)` to `openedx_tagging.api` as public, reusable functions; this ticket calls those directly. \#666's own updated draft also factors out the second half of its logic — for a set of relative tag ids, find every course that already has a `CompetencyCriterion` under one of them — into a public function on `openedx_learning.applets.cbe.api`: `get_courses_with_relative_criteria(tag_ids: Iterable[int]) -> dict[CourseKey, int]`, mapping each affected course key to the first relative tag id found to have a criterion there. \#666's own `_validate_containment()` is a thin wrapper over this same function (it just checks whether one specific course key is a key in the result); this ticket calls it directly to get the full mapping instead of testing membership for one course. This ticket does not build that walk itself; it depends on \#666 landing with `get_courses_with_relative_criteria` in place.

**Why course resolution goes through the tagged object's usage key.** `CompetencyCriteriaGroup.course_id` is nullable per ADR 0002 Decision 2 (it scopes evaluation windowing, not rule assignment, so a course-bound criterion can still have a null value there). The reliable path, the same one \#665 and \#666 both use, is to parse each candidate `CompetencyCriterion`'s `ObjectTag.object_id` as a `UsageKey` and read its course key off that, defensively skipping a row whose `object_id` doesn't parse.

**Grouping happens in Python, over a small result set.** Once the relative tags' criteria are loaded, deciding which courses come up more than once (because two different relative tags each have a claim in the same course) is done in a Python pass, not a single SQL aggregate. This is deliberate: the endpoint is called once when an author opens the association panel, not per keystroke, and the result set is small enough (one competency's ancestor/descendant set, times that competency's actual criteria) that the simplicity of a Python grouping outweighs a more complex query.

**No caching, no precomputation, no denormalized table.** A stale read is harmless, because \#666 remains the actual authority at write time. Adding caching or a denormalized table would be solving a performance problem this endpoint doesn't have at its expected call frequency and data size.

**Permission matches \#681, not \#665's write-side check.** This endpoint reads across a competency's ancestor/descendant tree, potentially spanning many courses, the same shape as \#681's own read across a competency's tree — not the single-course-write shape `oel_tagging.can_tag_object` was designed for. \#681 gates its own read with a `CompetencyReadPermission` DRF permission class whose `has_object_permission` checks `rules.has_perm("oel_tagging.view_tag", request.user, tag)`, which delegates to `can_view_taxonomy` and is permissive by design (anyone can view an enabled taxonomy). This ticket reuses that exact permission class against the resolved `tag`, rather than introducing a second one.

**Response contract.** Paginated from the first commit, in the standard `results`/`next`/`previous`/`count` envelope, with a pagination class pinned per view rather than inherited from the consuming project (matching \#773's and \#665's pattern, since this is a published library and an unpaginated list would be a breaking change to wrap in an envelope later). Each row carries the blocked course's key as a string (e.g. `"course-v1:Org+Course+Run"`), never the `CourseRun` integer primary key, which `src/openedx_catalog/models/course_run.py` states explicitly is internal-only, plus the id and value of the conflicting competency tag, so the frontend can render a message like "Already associated with Critical Thinking in this course" without a second lookup.

### Implementation specifics

- **New API function.** `get_blocked_courses(tag: Tag, course_keys: Iterable[CourseKey] | None = None) -> list[BlockedCourse]` in `src/openedx_learning/applets/cbe/api.py`, where `BlockedCourse` is a small dataclass carrying `course_key: CourseKey`, `conflicting_tag_id: int`, and `conflicting_tag_value: str`. Compute `relative_ids` as the union of `get_ancestor_tags(tag)` and `get_descendant_tags(tag)` ids (from `openedx_tagging.api`, added by \#666); return an empty list immediately if that union is empty, without calling `get_courses_with_relative_criteria` at all.  
- **Calls \#666's shared function directly.** `get_blocked_courses()` calls `get_courses_with_relative_criteria(relative_ids)` (from \#666's updated draft, in this same `api.py` module) and gets back a `dict[CourseKey, int]` mapping every affected course to whichever relative tag conflicts there. This ticket does not re-derive any part of that walk, including its tie-break: `get_courses_with_relative_criteria` already resolves a course claimed by more than one relative tag deterministically (lowest tag id wins), so the read and \#666's write always agree on which tag would be named if the author tried the association. When `course_keys` is supplied, it is applied to this mapping's keys before the per-course `CourseRun` lookup below, dropping any course not in the requested set; the mapping itself, and the criterion scan that built it, are unaffected by the filter.  
- **Course resolution per criterion** happens inside `get_courses_with_relative_criteria` itself (parsing `ObjectTag.object_id` via `UsageKey.from_string`, resolving the `CourseRun` via `openedx_catalog.api.get_course_run()`) — nothing left for this ticket to implement on that front. Map the returned `CourseKey`s (after the optional `course_keys` filter above) to `BlockedCourse` rows via `CourseRun.course_key` (never `CourseRun.id`), looking up each `CourseRun` and its conflicting tag's value for the response.  
- **Serializer.** `BlockedCourseSerializer(serializers.Serializer)` in `src/openedx_learning/applets/cbe/rest_api/v1/serializers.py`, with `course_key` (string), `conflicting_tag_id` (int), and `conflicting_tag_value` (string), all read-only.  
- **View.** `CompetencyBlockedCoursesView(mixins.ListModelMixin, GenericViewSet)` in `src/openedx_learning/applets/cbe/rest_api/v1/views.py`. Resolve `tag = get_object_or_404(Tag, pk=tag_id)` in `get_queryset` (or an equivalent lookup), call `self.check_object_permissions(request, tag)` against `CompetencyReadPermission` (reused from \#681, not redefined here). Parse the optional `course_keys` query parameter through a small `CompetencyBlockedCoursesQueryParamsSerializer(serializers.Serializer)` (a `CharField(required=False)` holding the raw comma-separated string, validated against `request.query_params.dict()` the same way `TaxonomyListQueryParamsSerializer` is), split it on commas and parse each piece via `CourseKey.from_string` in the view, then return `get_blocked_courses(tag, course_keys=parsed_keys_or_none)`. Because the result is a plain Python list rather than a queryset, use a pagination class that works over any sequence (DRF's page-number and limit/offset paginators both do).  
- **URL registration.** Register `competencies/<int:tag_id>/blocked-courses/` on the existing router in `src/openedx_learning/applets/cbe/rest_api/v1/urls.py`, alongside `criteria/` (\#665) and `criteria-groups/` (\#681).  
- **Pagination class.** `CompetencyBlockedCoursesPagination` in `src/openedx_learning/applets/cbe/rest_api/paginators.py`, following the same pinned-page-size pattern as `CompetencyRuleProfilePagination` (\#773) rather than inheriting the consuming project's default.  
- **Permission.** Reuse `CompetencyReadPermission` from \#681 (`src/openedx_learning/applets/cbe/rest_api/v1/permissions.py`) unmodified; do not add a second read permission class.  
- **Public-API impact.** Additive only: one new function on `openedx_learning.applets.cbe.api`, no changes to any existing public function's signature. Mark `get_blocked_courses` UNSTABLE per the README's convention, matching \#773's own precedent for a new function in an incomplete family.  
- **Layering.** No new cross-app import beyond what \#665/\#666 already establish (`openedx_tagging`, `openedx_catalog` from `openedx_learning`); `lint-imports` should pass with no `.importlinter` changes.  
- **No PII surface, no migration.** This ticket adds no model and no schema change.  
- **Tests.** `tests/openedx_learning/applets/cbe/test_api.py`: ancestor-only conflict, descendant-only conflict, multi-level (grandparent/grandchild) conflict, sibling not reported, a second course unaffected, no relatives with any claim (empty), same course claimed by two relatives resolves to one row via the tie-break, a caller-supplied `course_keys` filter narrows the result to only the requested courses, excluding other blocked courses that exist outside that set. `tests/openedx_learning/applets/cbe/test_views.py`: the paginated envelope, an unknown `tag_id` returning 404, the permission-refusal case, and a `course_keys`\-filtered request whose matching courses themselves exceed one page — pagination must apply to the filtered result set, not the other way around, so this proves the view filters before paginating rather than paginating the unfiltered set and filtering each page.  
- **Out of scope, named so nobody builds it here:** any change to \#666's actual enforcement; subsection-level detail in the response; any frontend/UI work (the sibling ticket, not yet numbered); caching, async precomputation, or a denormalized table.

Files to create and modify **Modified files**

| File | Nature of modification |
| :---- | :---- |
| src/openedx\_learning/applets/cbe/api.py | add `get_blocked_courses(tag, course_keys=None)`, calling \#666's `get_courses_with_relative_criteria(tag_ids)` |
| src/openedx\_learning/applets/cbe/rest\_api/v1/serializers.py | add `BlockedCourseSerializer` and `CompetencyBlockedCoursesQueryParamsSerializer` (validates the optional `course_keys` query parameter) |
| src/openedx\_learning/applets/cbe/rest\_api/v1/views.py | add `CompetencyBlockedCoursesView` |
| src/openedx\_learning/applets/cbe/rest\_api/v1/urls.py | register `competencies/<int:tag_id>/blocked-courses/` on the existing router |
| src/openedx\_learning/applets/cbe/rest\_api/paginators.py | add `CompetencyBlockedCoursesPagination` |
| tests/openedx\_learning/applets/cbe/test\_api.py | add tests for `get_blocked_courses` |
| tests/openedx\_learning/applets/cbe/test\_views.py | add envelope, 404, and permission-refusal tests |

- Context **\#666:** "Enforce competency-hierarchy dominance for Competency Criteria" — the write-side rule this ticket reads proactively. Adds `get_ancestor_tags(tag)`/`get_descendant_tags(tag)` to `openedx_tagging.api` and `get_courses_with_relative_criteria(tag_ids)` to `openedx_learning.applets.cbe.api`, all of which this ticket calls directly rather than re-deriving. \#666's own `_validate_containment()` is a thin wrapper over the same shared function, so the read (a gray-out hint) and the write (the actual enforcement) can never disagree.  
- **\#665:** establishes the `UsageKey.from_string` / `openedx_catalog.api.get_course_run()` parse-and-resolve pattern this ticket reuses for course resolution.  
- **\#681:** "Build GET endpoint to fetch Competency Criteria Groups and Criteria for a competency" — source of the `CompetencyReadPermission` class this ticket reuses unmodified (`rules.has_perm("oel_tagging.view_tag", ...)`, delegating to `can_view_taxonomy`).  
- **\#773:** source of the pinned-pagination-class pattern (`CompetencyRuleProfilePagination`) and the rationale for pagination from the first commit in a published library.  
- **ADR 0002** (`docs/openedx_learning/decisions/0002-competency-criteria-model.rst`): Decision 2 for why `CompetencyCriteriaGroup.course_id` is nullable and scopes evaluation windowing rather than rule assignment; Decision 4's worked example for one tag legitimately having criteria in multiple groups.  
- `src/openedx_tagging/models/base.py`: `Tag.lineage`, `Tag.depth`, and `Tag.descendant_count`, the existing lineage-prefix mechanism `get_ancestor_tags`/`get_descendant_tags` (\#666) mirror.  
- `src/openedx_catalog/models/course_run.py`: `CourseRun.course_key` as the client-facing course identifier, and the model's own docstring stating its integer primary key should not be exposed in APIs.  
- The frontend sibling ticket, not yet numbered, which consumes this endpoint to gray out ineligible content in the authoring UI.

</details>
