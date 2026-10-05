# [BE] Add Archived Course Keys to GET Competency Criteria & Groups Endpoint

GitHub: https://github.com/openedx/openedx-core/issues/840 (#840, OPEN)
Cached: 2026-09-25

## User Story
As a course author, I need the Competency Management page to know which courses can no longer take new rules for a competency, in order to be told up front instead of having my new associations rejected.

## Description
This ticket adds an `archived_course_keys` field to the response of the GET Competency Criteria & Groups endpoint that lists the course run keys whose course-level group for the selected competency is archived. Unarchiving course-level groups is out of scope for MVP, so the frontend needs to know which courses to pre-emptively prevent course authors from trying to recreate.

## Context
- #681 is the endpoint this ticket extends.
- #674 and #675 archive a course-level group when a delete would otherwise destroy learner progress.
- #717 prevents creating new Competency Criteria in an archived course-level group.
- #841 is the frontend ticket that uses this list to hide archived courses in the Browse Courses panel.

## Acceptance Criteria

These scenarios can be checked by calling the endpoint directly, for example with Postman. Unless a scenario says otherwise, the caller has permission to view the competency's taxonomy. "Reported as archived" means the course run's key appears in the response's new list of archived course runs.

```gherkin
Scenario: A course run with an archived course-level group is reported by its course run key
  Given a competency's course-level group for course run X is archived
  And the competency has active course-level groups for course run Y and for another run of X's course (for example "course-v1:OrgX+CS101+2027")
  When a caller fetches the competency's criteria structure
  Then course run X is reported as archived, identified by its course run key (for example "course-v1:OrgX+CS101+2026"), never by an internal id
  And neither course run Y nor the other run of X's course is reported as archived

Scenario: Archived Rule Groups and criteria under an active course-level group are not reported
  Given a competency's course-level group for course run Y is active
  And one of Y's Rule Groups is archived, and another of Y's Rule Groups is active but holds an archived criterion alongside an active one
  When a caller fetches the competency's criteria structure
  Then course run Y is not reported as archived

Scenario: An archived root group is not reported and does not hide the archived courses under it
  Given a competency's course-level groups for course runs X and Y are both archived, and so is the competency's root group above them
  When a caller fetches the competency's criteria structure
  Then exactly course runs X and Y are reported as archived
  And the list contains no entry without a course run key

Scenario: Only the selected competency's own course-level groups are reported
  Given competency P has a sub-competency S
  And P's course-level group for course run X is archived, and S's course-level group for course run Y is archived
  When a caller fetches P's criteria structure
  Then course run X is reported as archived
  And course run Y is not reported as archived

Scenario: The list is empty when no course-level group is archived
  Given a competency has no archived course-level group, whether because it has no criteria structure yet or because every course-level group it has is active
  When a caller fetches the competency's criteria structure
  Then the response includes the list of archived course runs, and that list is empty

Scenario Outline: The list follows the same course-run scope as the criteria structure
  This scenario needs #682's optional course-run filter on this endpoint. Whichever of #682 and this ticket merges second makes it pass.

  Given a competency's course-level groups for course runs X and Y are archived, and its course-level group for course run Z is active
  When a caller fetches the competency's criteria structure <scope>
  Then the course runs reported as archived are <reported>

  Examples:
    | scope                                 | reported |
    | with no course-run scope              | X and Y  |
    | scoped to course runs X and Z         | X only   |
    | scoped to an empty set of course runs | none     |

Scenario: The criteria structure leaves out archived rows
  Given a competency's course-level group for course run X is archived, along with every Rule Group and criterion under it
  And its course-level group for course run Y is active, with active Rule Groups and criteria
  When a caller fetches the competency's criteria structure
  Then course run X is reported as archived
  And the structure includes course run Y's groups and criteria and none of course run X's

Scenario: A delete that archives a course-level group is reported on the next fetch
  Given a competency's course-level group for course run X is active and holds a single Rule Group
  And a learner has recorded progress on a criterion in that Rule Group
  When an author deletes that Rule Group
  And a caller then fetches the competency's criteria structure
  Then course run X is reported as archived
  And course run X's groups and criteria no longer appear in the structure

Scenario: Archived course runs are reported regardless of the caller's access to those courses
  Given a competency's course-level group for course run X is archived
  And the caller can view the competency's taxonomy but has no Studio access to course run X
  When the caller fetches the competency's criteria structure
  Then course run X is reported as archived

Scenario: A caller who cannot view the competency learns nothing about archived courses
  Given a competency's course-level group for course run X is archived
  And the caller cannot view the competency's taxonomy
  When the caller fetches the competency's criteria structure
  Then the request is refused for lack of permission
  And no course run is disclosed as archived
```

<details>
<summary>Technical Details</summary>

This is a suggested approach, not the source of truth. The User Story, Description, and Acceptance Criteria define what must be true when the work is done.

**Approach**

File paths and names are those on #681's PR branch (alezconsultant/openedx-core#3).

1. Add `archived_course_keys: list[CourseKey]` to the `CompetencyCriteriaTree` dataclass and fill it in `get_competency_criteria_tree()` in `src/openedx_learning/applets/cbe/api.py`, so Python and REST callers get the same list from one place.
2. Compute it with one flat query over the competency's groups, so an archived root can't hide the course-level groups under it: `CompetencyCriteriaGroup.objects.filter(tag_id=tag_id, archived=True, course__isnull=False, parent__isnull=False, parent__parent__isnull=True).values_list("course__course_key", flat=True)`. Return each key once, sorted by its string.
3. The `parent__parent__isnull=True` clause (the group's parent is a root) is what makes a group course-level, and it selects the same group #717 checks before rejecting a new association. Don't select on `course__isnull=False` alone. ADR 0002 has every group in a course subtree carry the course, while #665 sets it only on the course-level group, so under ADR 0002's shape that filter also reports a course when one of its Rule Groups is archived. Build the archived Rule Group in the tests both with and without the course set, so the test fails under a course-only filter whichever shape lands.
4. Derive this query and the `groups` query from one queryset filtered to the competency, so that #682's `course_keys` predicate scopes both. When `course_keys` is omitted the list covers every course run, when it is a list the list covers only those runs, and when it is empty the list is empty. If this ticket merges first, #682 applies the scope to the list.
5. In `CompetencyCriteriaTreeView.get()` in `src/openedx_learning/applets/cbe/rest_api/v1/views.py`, add the list to the response next to `groups` and `criteria` as course run key strings. The key is always present, for example `"archived_course_keys": ["course-v1:OrgX+CS101+2026"]`, and is `[]` when nothing is archived.

The field is additive to #681's unshipped contract and leaves its `groups` and `criteria` rows unchanged. Explaining archived courses in the Courses & Content panel is out of scope; #841 covers it.

**Additional context**

- #716 adds the `archived` column to both the group and criterion models.
- `docs/openedx_learning/decisions/0002-competency-criteria-model.rst`: Decision 2 for `course_id`, and Decision 7 for archiving instead of deleting once learner status exists.

</details>
