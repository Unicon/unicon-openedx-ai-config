# [BE] Course search: accept ISO 8601 datetimes in the start date filter

GitHub: https://github.com/openedx/openedx-core/issues/842 (#842, CLOSED)
Cached: 2026-10-14

## User Story

As a Platform Administrator browsing courses on the Competency Management page, I want the start date filter to use the exact boundaries of the days I select in my own time zone, in order to find the courses that Studio shows as starting on those days.

## Acceptance Criteria

```
Scenario: The filter uses the exact start boundary sent by the caller
  Given a course starts at 2027-06-30T22:00:00Z
  When the course list is requested with a start boundary of 2027-07-01T00:00:00+04:00
  Then the course is included in the results

Scenario: The filter uses the exact end boundary sent by the caller
  Given a course starts at 2027-07-01T02:00:00Z
  When the course list is requested with an end boundary of 2027-06-30T23:59:00-04:00
  Then the course is included in the results

Scenario: A course outside the boundaries is excluded
  Given a course starts at 2027-06-30T19:59:00Z
  When the course list is requested with a start boundary of 2027-07-01T00:00:00+04:00
  Then the course is not included in the results

Scenario: Boundaries in UTC and with an offset give the same result
  Given a set of courses with different start dates
  When the course list is requested once with boundaries in UTC ("Z") and once with the same moments written with a time zone offset
  Then both requests return the same courses

Scenario: Only a start boundary or only an end boundary is given
  Given a set of courses with different start dates
  When the course list is requested with only one of the two boundaries
  Then the results are limited on that side only

Scenario: An invalid boundary value is rejected
  Given the course list endpoint
  When a boundary value is not a valid ISO 8601 datetime
  Then the request fails with a validation error that names the invalid parameter

Scenario: A plain calendar date is rejected
  Given the course list endpoint
  When a boundary value is a date without a time, for example 2027-07-01
  Then the request fails with a validation error that names the invalid parameter

Scenario: A datetime without a time zone is rejected
  Given the course list endpoint
  When a boundary value is a datetime without a time zone, for example 2027-07-01T00:00:00
  Then the request fails with a validation error that names the invalid parameter
```

## Description

The course search on the Competency Management page (#670) filters courses by start date through the course list endpoint added in #669. The endpoint accepts only a calendar date and compares it against a UTC day, while Studio shows course start dates in the user's time zone. As a result, a user outside UTC does not find a course by the start date that Studio shows for it (see #<bug>). With this change, the front end sends the exact start and end of the selected days in the user's time zone as ISO 8601 datetimes, and the back end filters by those moments.

<details>
<summary>Technical Details</summary>

This section is background and a suggested approach. The User Story and Acceptance Criteria define what must be true when the work is done.

**In short**

**Parsing the boundaries.** The `start_date_on_or_after` and `start_date_on_or_before` query parameters of `GET /api/contentstore/v2/home/courses` accept an ISO 8601 datetime with a time zone, either `Z` or an offset such as `+04:00`. The parameters no longer accept a plain `YYYY-MM-DD` date. The back end converts each value to UTC before filtering. A value that isn't an ISO 8601 datetime with a time zone, including a plain date and a datetime without a time zone, fails the request with a `400` validation error.

**Filtering.** A course matches when its start is at or after the `start_date_on_or_after` moment and at or before the `start_date_on_or_before` moment. The back end uses the moments exactly as received and no longer extends the end boundary to the end of a UTC day.

**Implementation specifics**

- **Parameter parsing:** `get_date_param` in `cms/djangoapps/contentstore/api/views/utils.py` validates with `serializers.DateField`, which rejects datetimes. The course list view in `cms/djangoapps/contentstore/views/course.py` needs a datetime-aware equivalent that returns a UTC-aware `datetime` and raises a DRF `ValidationError` (`400`) for a plain date, a datetime without a time zone, or an unparseable value.
- **Filter logic:** `CourseOverview.get_all_courses` in `openedx/core/djangoapps/content/course_overviews/models.py` currently sets `start__lt = start_date_on_or_before + timedelta(days=1)`. It becomes `start__gte = start_date_on_or_after` and `start__lte = start_date_on_or_before`.
- **API docs:** update the parameter descriptions and examples in `cms/djangoapps/contentstore/rest_api/v2/views/home.py`, which currently document the `YYYY-MM-DD` format.
- **Tests:** cover each Acceptance Criteria scenario, including a boundary exactly equal to a course start (included on both sides), a value with `Z`, a value with a positive and a negative offset, and the rejected values: an unparseable value, a plain `YYYY-MM-DD` date, and a datetime without a time zone.
- **Out of scope:** the front-end change that sends the boundaries as ISO 8601 datetimes is tracked in #<bug>.

</details>

<details>
<summary>Files to create and modify</summary>

**Modified files**

| File | Nature of modification |
| --- | --- |
| `cms/djangoapps/contentstore/api/views/utils.py` | Parse the boundary parameters as ISO 8601 datetimes |
| `cms/djangoapps/contentstore/views/course.py` | Use the datetime parsing for `start_date_on_or_after` and `start_date_on_or_before` |
| `openedx/core/djangoapps/content/course_overviews/models.py` | Filter by the exact boundary moments in `get_all_courses` |
| `cms/djangoapps/contentstore/rest_api/v2/views/home.py` | Update the parameter documentation and examples |

</details>

<details>
<summary>Context</summary>

- #669: the course list endpoint and its start date filter.
- #670: the Competency Management course search that uses the filter.
- #<bug>: the time zone bug in the start date filter, including steps to reproduce from time zones east and west of UTC.

</details>
