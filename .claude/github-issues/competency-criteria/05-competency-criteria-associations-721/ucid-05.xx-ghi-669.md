# [BE] Add start-date range filter and outline delivery for accessible courses (Competency Criteria Associations)

GitHub: https://github.com/openedx/openedx-core/issues/669 (#669, CLOSED)
Cached: 2026-09-21

**Repo:** `openedx-core` (CBE sprint-0 backlog). The implementation lands in `openedx-platform` — see Files to create and modify, below. Tracked in this repo's backlog per team convention: all CBE-program tickets are filed here regardless of which repo the code touches.

**Related:** \#665 (gradeable-subsection-to-competency association), \#670 (frontend, Manage & Apply Competencies screen), ticket 5.7 (fetch competency criteria).

## Use Case

As a Platform Administrator configuring Competency Criteria associations, I want to fetch the courses I have access to within a specified time range, along with each course's outline (sections and gradeable subsections), so that the Manage & Apply Competencies screen can display those courses and let me drill into their gradeable subsections to attach criteria.

## Description

**Current state**

`HomePageCoursesViewV2` (`GET /api/contentstore/v2/home/courses`, `cms/djangoapps/contentstore/rest_api/v2/views/home.py`) already lists the courses the current user can access — scoped via `get_courses_accessible_to_user()` (`cms/djangoapps/contentstore/views/course.py`) — with pagination and filters for `org`, `search`, `active_only`/`archived_only`, and `order`. It has no course-run start-date field and no date-range filter today. Course outlines (sections, subsections, the `graded` flag) are already served by `CourseIndexView` (`GET /api/contentstore/v1/course_index/{course_id}`), the same endpoint Studio's own outline UI uses.

**Requested change**

Extend `HomePageCoursesViewV2` rather than building a new endpoint:

1. **Add an optional start-date-range filter** to the existing accessible-courses listing. The filter matches courses whose course-run start date (`CourseOverview.start`) falls within the given range. Courses with no start date always appear, regardless of the range. End-date filtering is not included (a later enhancement, separate SOW).  
2. **No change needed for outlines.** The frontend (\#670) fetches each course's outline lazily, per course, via the existing `CourseIndexView` on drill-in/expand — this ticket does not add outline data to the course-list response.

**Explicitly out of scope**

- Fetching competency criteria — handled separately by ticket 5.7, cross-referenced against these outlines on the frontend (\#670).  
- End-date filtering — deferred past MVP.  
- Any competency-to-course association — only gradeable-subsection-to-competency association exists (\#665).  
- Attaching/associating competency criteria to a subsection — that's \#665's and 5.7's job, not this read-only listing endpoint.  
- The frontend UI (\#670) and the create-criterion flow (\#665 / the UC5.11 create-and-select UI).  
- A per-course "has criteria configured" indicator on the course list — the list stays course-only; no signal is shown before drill-in.

## Acceptance Criteria

These scenarios are verifiable via Postman.

```
Scenario: Fetch accessible courses within a start-date range
  Given the requesting user has access to a set of courses via HomePageCoursesViewV2
  And some of those courses have a course-run start date within a specified range and some outside it
  When GET /api/contentstore/v2/home/courses is called with the start-date range params
  Then the response's "results" array includes the accessible courses whose start date falls within the range
  And it excludes accessible courses whose start date falls outside the range
  And it excludes courses the user cannot access

Scenario: Each returned course's outline is available on drill-in
  Given the endpoint returns an accessible course
  When the frontend calls CourseIndexView (GET /api/contentstore/v1/course_index/{course_id}) for that course
  Then the outline response includes the course's sections and its gradeable subsections (graded: true)

Scenario: No accessible courses in range
  Given the user has no accessible courses whose start date falls within the specified range (and none lacking a start date)
  When the endpoint is called
  Then the response returns "results": [] with a 200 status code

Scenario: Unauthenticated caller
  Given a request without valid authentication
  When the endpoint is called
  Then the response returns a 401 status code
```

## Open Questions

- **\[non-blocking, owner: architect/implementer\]** Exact name for the new query params and response field (placeholders used in this ticket: `start_date_after` / `start_date_before` query params; the response field is currently unnamed). Confirm before implementation; does not change scope or design.

## Technical Details

**Data Structures**

No new models, serializers, or migrations. Two new optional query params on the existing `GET /api/contentstore/v2/home/courses` contract: `start_date_after`, `start_date_before` (ISO date strings, independently optional and combinable).

**Logic**

- `CourseOverview.get_all_courses()` (`openedx/core/djangoapps/content/course_overviews/models.py:681-717`) already implements a null-inclusive OR pattern for its existing `active_only` param: `Q(end__isnull=True) | Q(end__gte=now)`. Add `start_date_after`/`start_date_before` as sibling parameters on this same method, applying `Q(start__isnull=True) | Q(start__gte=after, start__lte=before)` when either is set. `CourseOverview.start` is `models.DateTimeField(null=True)`, so the `isnull` branch satisfies "courses with no start date still appear." This is the correct integration point: `get_all_courses`'s current filtering is plain-kwarg (`filter_={'id__in': ...}` passed straight to `.filter(**filter_)`), which can't express a null-inclusive OR — that capability has to live inside this method's own logic, not bolted on afterward by a caller.  
- `get_courses_accessible_to_user(request)` (`cms/djangoapps/contentstore/views/course.py:998`) forwards the new params through to `get_all_courses` alongside its existing `filter_={'id__in': ...}` call.  
- The params must be added to `allowed_query_params` (`cms/djangoapps/contentstore/views/course.py:476`), the whitelist that gates which query params actually take effect. Note: this view already documents an `org` query param that is missing from this whitelist and is silently ignored today — a pre-existing, unrelated bug, flagged here so the new params don't suffer the same silent no-op; not this ticket's job to fix `org`.  
- `HomePageCoursesViewV2.get()` (`cms/djangoapps/contentstore/rest_api/v2/views/home.py`) needs no parsing change — it already forwards `request` unchanged down the chain. Add the two new params to its `apidocs.string_parameter(...)` declarations for schema/doc visibility.  
- No `openedx-core` change. Outlines use the existing `CourseIndexView`, fetched lazily per course by the frontend on expand.

**Example Resolution Prompt**

In `openedx-platform`, add optional `start_date_after`/`start_date_before` params to `CourseOverview.get_all_courses()` (`openedx/core/djangoapps/content/course_overviews/models.py`), mirroring the existing `active_only` param's pattern: when either is set, apply `Q(start__isnull=True) | Q(start__gte=after, start__lte=before)` to the queryset before other filtering. In `cms/djangoapps/contentstore/views/course.py`, thread these two params from `get_courses_accessible_to_user(request)` into the `get_all_courses` call, and add them to `allowed_query_params` (\~line 476\) so they aren't silently dropped (verify this doesn't also require fixing the existing `org` whitelist gap — that's a separate, pre-existing issue, out of scope here). Add matching `apidocs.string_parameter` docs to `HomePageCoursesViewV2.get()` in `cms/djangoapps/contentstore/rest_api/v2/views/home.py`; no logic change needed there. Add/extend tests covering: in-range match, null-start inclusion, out-of-range exclusion, both-params-absent (unchanged behavior), and that the params actually reach `get_all_courses` through the whitelist.

## Context

- `HomePageCoursesViewV2`: `cms/djangoapps/contentstore/rest_api/v2/views/home.py`  
- `get_course_context_v2`: `cms/djangoapps/contentstore/utils.py`  
- `get_courses_accessible_to_user`: `cms/djangoapps/contentstore/views/course.py`  
- `CourseOverview` model (the `start` field): `openedx/core/djangoapps/content/course_overviews/models.py`  
- `CourseIndexView` (outline, unchanged, already exists): `cms/djangoapps/contentstore/rest_api/v1/views/course_index.py`  
- \#665, \#670, ticket 5.7 — see Related, above.  
- Prior investigation ruled out `edx-search`'s `course_discovery_search()`: its only call site in the platform is the LMS free-text `CourseListView` (`lms/djangoapps/course_api/`), the wrong audience and mechanism for this admin workflow, and it carries a runtime dependency on platform-only settings classes (`SEARCH_FILTER_GENERATOR`/`SEARCH_RESULT_PROCESSOR`) that this design avoids entirely by not using it.  
- This ticket proposes extending an existing `openedx-platform` endpoint rather than migrating its logic into `openedx-core`. There is a known community direction of migrating code from `openedx-platform` into `openedx-core` over time; if `get_courses_accessible_to_user`/`CourseOverview`\-based listing is ever a migration candidate, community review may prefer migrating first rather than extending in place. Proceeding with the platform-side extension as scoped; this is a risk to be surfaced during community review, not a reason to hold the ticket.

## Files to create and modify

**New files**

None.

**Modified files**

| File | Nature of modification |
| :---- | :---- |
| `openedx/core/djangoapps/content/course_overviews/models.py` | `CourseOverview.get_all_courses`: add `start_date_after`/`start_date_before` params, null-inclusive `Q` date-range filter (mirrors existing `active_only` pattern) |
| `cms/djangoapps/contentstore/views/course.py` | `get_courses_accessible_to_user`: thread new params through to `get_all_courses`; add params to `allowed_query_params` |
| `cms/djangoapps/contentstore/rest_api/v2/views/home.py` | `HomePageCoursesViewV2`: add doc-only query-param declarations |
| Existing test file(s) for the three functions above | Add range/null-inclusion/exclusion/whitelist coverage (exact test file paths to be confirmed by the implementer) |
