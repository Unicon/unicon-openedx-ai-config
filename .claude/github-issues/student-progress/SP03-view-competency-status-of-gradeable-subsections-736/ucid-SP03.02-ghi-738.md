# [BE] GET Competency Statuses for Learner in Course

GitHub: https://github.com/openedx/openedx-core/issues/738 (#738, OPEN)
Cached: 2026-09-21

## User Story
As a learner, I need to know what mastery level I demonstrated on each subsection as well as my overall mastery level for each competency assessed in the course in order to understand what I need to work on improving and how I can speak about my skills.

## Description
This ticket is for building a GET endpoint that fetches the Competency Status for all competency criteria and parent competencies in a given course for a given learner.

This endpoint should do the following logic. Steps 1, 3, and 4 skip anything #733 excludes (archived criteria, groups, tags, and taxonomies, and disabled taxonomies), so the response covers exactly the items #733 returns.
1. Get the course-level CompetencyCriteriaGroups for this course: the groups whose course_id points to the CourseRun for this course run key. There is one per competency assessed in the course.
2. Get the StudentCompetencyStatus records where user_id is the learner's id and oel_tagging_tag_id is the tag of one of those course-level groups or one of that tag's ancestor tags. Include all of these records in the response payload.
3. Get all the CompetencyCriteriaGroups whose parent_id is one of the course-level groups fetched in step 1.
4. Get all CompetencyCriterion records that belong to the groups fetched in steps 1 and 3.
5. Get all StudentCompetencyCriteriaStatus records where user_id is the learner's id and competency_criteria_id is one of the CompetencyCriterion ids fetched in step 4. Include all of these records in the response payload.
6. Join each status record to CompetencyMasteryStatus so the response payload carries the status value (for example, "Demonstrated") rather than its id.

The response payload will then resemble something to the effect of the following:
```json
{
    "student_competency_statuses": [{"tag_id": 40, "status": "PartiallyAttempted"},
                                    {"tag_id": 41, "status": "PartiallyAttempted"}],
    "student_competency_criteria_statuses": [{"criterion_id": 90, "status": "Demonstrated"},
                                             {"criterion_id": 91, "status": "AttemptedNotDemonstrated"}]
}
```

## Context
- The statuses are written by #699 (a criterion's status when a grade is recorded) and #643 (the roll-up from criterion to competency, continuing up through each parent tag to the top of the taxonomy). Neither blocks building this endpoint, but both are needed to see real statuses end to end.
- #739 and #740 are the frontend counterparts to this ticket.

## Acceptance Criteria

In these scenarios, L is a learner, and a caller permitted to read L's statuses is one of the following:
- Under openedx-core's default learner resolution, L.
- On the LMS, L with an active enrollment in the course run, a member of the course run's staff who names L, or a member of its staff who is masquerading as L.

**Access under openedx-core's default learner resolution**

```gherkin
Scenario: A caller who is not signed in is rejected
  Given L has recorded statuses in course run X
  When a caller who is not signed in requests competency statuses for course run X
  Then the request is rejected as unauthenticated
  And the response contains none of L's statuses

Scenario Outline: A signed-in user gets their own statuses under the default
  Given openedx-core's default learner resolution, with nothing replacing it
  And L is signed in and has recorded statuses in course run X
  When L requests competency statuses for course run X <naming>
  Then L's statuses for course run X are returned

  Examples:
    | naming                   |
    | without naming a learner |
    | naming L's own user id   |

Scenario: Naming another learner under the default is refused the same way as naming no one who exists
  Given openedx-core's default learner resolution, with nothing replacing it
  And signed-in user M, and learner L who has recorded statuses in course run X
  When M requests L's competency statuses for course run X
  Then the request is refused as not found
  And the response is the same one M gets for a learner id that matches no user
  And the response contains none of L's statuses
```

**Access on the LMS (openedx-platform)**

```gherkin
Scenario: A learner with an active enrollment gets their own statuses from the LMS
  Given L has an active enrollment in course run X and recorded statuses there
  When L requests competency statuses for course run X from the LMS without naming a learner
  Then L's statuses for course run X are returned

Scenario Outline: Course staff get the statuses of the learner they name
  Given a member of course run X's staff who is not enrolled in course run X
  And L, who <enrollment>, has recorded statuses in course run X
  When the staff member requests competency statuses for course run X from the LMS, naming L
  Then L's statuses for course run X are returned

  Examples:
    | enrollment                                        |
    | has an active enrollment in course run X          |
    | enrolled in course run X and has since unenrolled |

Scenario: Staff masquerading as a specific learner get that learner's statuses
  Given L has an active enrollment in course run X and recorded statuses there
  And a member of course run X's staff, who is not enrolled in course run X, is masquerading as L
  When the staff member requests competency statuses for course run X from the LMS without naming a learner
  Then L's statuses for course run X are returned

Scenario Outline: Staff whose masquerade does not resolve to a current learner get their own statuses
  Given S, a member of course run X's staff, has recorded statuses of their own in course run X
  And L has different recorded statuses in course run X
  And S <masquerade>
  When S requests competency statuses for course run X from the LMS without naming a learner
  Then S's own statuses are returned
  And none of L's statuses are returned

  Examples:
    | masquerade                                                               |
    | is masquerading as the Learner role, without choosing a specific learner |
    | is masquerading as a learner in a content group                          |
    | began masquerading as L, and L has since unenrolled from course run X    |

Scenario Outline: A request for another learner the requester may not see is refused as not found
  Given <requester>
  And L has an active enrollment in course run X and recorded statuses there
  When the requester asks for competency statuses for course run X from the LMS, naming L
  Then the request is refused as not found
  And the response is the same one the requester gets for a learner id that matches no user
  And the response contains none of L's statuses

  Examples:
    | requester                                                              |
    | learner M, with an active enrollment in course run X and no staff role |
    | a member of course run Y's staff who has no role in course run X       |

Scenario Outline: A signed-in user with neither an active enrollment nor a staff role is refused
  Given a signed-in user U who is not on course run X's staff and who <enrollment>
  When U requests competency statuses for course run X from the LMS without naming a learner
  Then the request is refused as not permitted
  And the response contains none of U's statuses

  Examples:
    | enrollment                                                                                                               |
    | has never enrolled in course run X, and has recorded statuses for course run X's competencies through other course runs |
    | enrolled in course run X, has recorded statuses there, and has since unenrolled                                          |
```

**Learner ids that match no user**

```gherkin
Scenario Outline: A learner id that matches no user is refused as not found
  Given <requester>
  When the requester asks for competency statuses for course run X, naming learner id <learner id>
  Then the request is refused as not found
  And the response is identical to the one given for a learner the requester may not see

  Examples:
    | requester                                                         | learner id                          |
    | a signed-in user under openedx-core's default learner resolution | "abc", which is not an integer      |
    | a member of course run X's staff, requesting from the LMS        | "abc", which is not an integer      |
    | a member of course run X's staff, requesting from the LMS        | an integer that matches no user     |
```

**Course resolution**

```gherkin
Scenario: A malformed course run key is rejected
  Given a signed-in caller
  When the caller requests competency statuses for a value that is not a well-formed course run key
  Then the request is rejected with a message saying the course run key is malformed
  And no statuses are returned

Scenario Outline: A request with nothing to report returns an empty result
  Given L has recorded statuses, earned in other course runs, for competencies that the requested course run does not assess
  And <course run>
  When a permitted caller requests L's competency statuses for that course run
  Then the request succeeds
  And the result contains no criterion statuses and no competency statuses

  Examples:
    | course run                                                                                                                      |
    | a course run in the catalog that has never had competency criteria                                                              |
    | a well-formed course run key that matches no course run in the catalog                                                          |
    | a course run with competency criteria, where L has no recorded status for any of its criteria, competencies, or their ancestors |
```

**What the result contains**

```gherkin
Scenario: Each recorded status is reported by name and keyed by its criterion's or tag's id
  Given course run X has three criteria for competency "Root Cause Analysis"
  And L's recorded status is "Demonstrated" for the first criterion and "AttemptedNotDemonstrated" for the second, and L has no recorded status for the third
  And L's recorded status for "Root Cause Analysis" is "PartiallyAttempted"
  When a permitted caller requests L's competency statuses for course run X
  Then the first criterion is reported as "Demonstrated" and the second as "AttemptedNotDemonstrated"
  And "Root Cause Analysis" is reported as "PartiallyAttempted"
  And the third criterion does not appear
  And each criterion status carries that criterion's id
  And the "Root Cause Analysis" status carries the "Root Cause Analysis" tag's id
  And the result contains nothing that identifies L, neither L's username nor L's user id

Scenario: The learner's statuses for a competency's ancestors are reported and matched to its lineage
  Given a competency taxonomy in which "Root Cause Analysis" is a child of "Problem Definition", which is a child of the top-level tag "Problem Solving"
  And "Fishbone Diagrams" is another child of "Problem Definition"
  And course run X has criteria for "Root Cause Analysis" and for no other tag in that taxonomy
  And L has recorded statuses for "Root Cause Analysis", "Problem Definition", "Problem Solving", and "Fishbone Diagrams"
  When a permitted caller requests L's competency statuses for course run X
  Then L's statuses for "Root Cause Analysis", "Problem Definition", and "Problem Solving" are returned
  And each ancestor's status carries that ancestor tag's id
  And L's status for "Fishbone Diagrams", which course run X does not assess, does not appear

Scenario: A competency carries the learner's overall recorded status, while criterion statuses come only from course run X
  Given competency "Analysis" has criteria in course run X and in course run Y
  And L demonstrated "Analysis" through course run Y's criteria, so "Analysis" is recorded as "Demonstrated"
  And L's recorded status for course run X's "Analysis" criterion is "AttemptedNotDemonstrated"
  When a permitted caller requests L's competency statuses for course run X
  Then "Analysis" is reported as "Demonstrated"
  And course run X's "Analysis" criterion is reported as "AttemptedNotDemonstrated"
  And no status for any course run Y criterion is returned
```

**Archived and disabled records**

In these scenarios, L already has a recorded status through every criterion involved. Without one, deleting a criterion, group, tag, or taxonomy removes it outright instead of archiving it.

```gherkin
Scenario Outline: Statuses follow #733's result when part of the course run's competency data is retired
  Given course run X has criteria for "Root Cause Analysis", a child of "Problem Definition" under the top-level tag "Problem Solving" in competency taxonomy A, and for "Communication" in competency taxonomy B
  And "Root Cause Analysis"'s course-level group for course run X has two bottom-tier groups, each holding two criteria
  And L has a recorded status for every one of those criteria, for both competencies, and for every ancestor of each
  When <retirement>
  And a permitted caller requests L's competency statuses for course run X
  Then L's statuses are returned for exactly the criteria and tags that #733's result for course run X contains, including the tags in each competency's lineage
  And none of L's statuses for the retired item, for anything beneath it, or for any ancestor that no remaining competency in course run X has in its lineage, is returned
  And L's statuses for "Communication" and its criteria are still returned

  Examples:
    | retirement                                                                                     |
    | one criterion in the first bottom-tier group is archived through #674                          |
    | the first bottom-tier group is archived through #675                                           |
    | "Root Cause Analysis"'s course-level group for course run X is archived through #675           |
    | the "Root Cause Analysis" tag is archived                                                      |
    | the "Problem Definition" tag is archived through #780, which archives every tag beneath it too |
    | taxonomy A is archived, and none of its tags is                                                |
    | taxonomy A is disabled                                                                         |
```

**Subsections a learner cannot see (openedx-platform)**

The Progress tab's own API, `/api/course_home/v1/progress/{course_key}`, sends the real score for a subsection set to never show individual assessment results, and the page hides it. This endpoint matches that: a learner who inspects the network response can read statuses the page does not show them.

```gherkin
Scenario: Statuses are returned for criteria on subsections whose content or results the learner cannot see
  Given L has an active enrollment in course run X and recorded statuses for criteria on three subsections
  And after L was graded, one subsection was hidden from learners, one was restricted to a content group L is not in, and one was set to never show individual assessment results
  When L requests competency statuses for course run X from the LMS
  Then L's statuses for all three criteria are returned
```

<details>
<summary>Technical Details</summary>

This is a suggested approach, not the source of truth. The User Story, Description, and Acceptance Criteria define what must be true when the work is done.

**Summary**

openedx-core adds a learner-facing view that asks a deployer-supplied resolver whose statuses the request may read. It then reads that learner's stored statuses for exactly the criteria and tags in #733's result, by calling #733's selection instead of querying the hierarchy again. The default resolver allows only the requester. openedx-platform extracts `ProgressTabView._get_student_user` into a shared function and points the setting at a small wrapper around it that adds the Progress tab's enrollment refusal, so staff and masquerade resolve exactly as they do on the Progress tab.

**Approach**

In openedx-core, within `openedx_learning`:

1. `get_learner_competency_statuses(user_id, course_key)` goes in `applets/cbe/api.py`, out of `__all__` like #733's function. It calls `get_course_competency_criteria(course_key)` and collects its criterion ids and every tag id in every lineage (a lineage includes the tag itself). Reusing #733's selection is what limits the result to exactly #733's items, including criteria at any depth below the course-level group, which Description steps 3 and 4 cover only one level deep. When #733's result is empty, return without querying the status tables, so the empty path stays at #733's one query. Otherwise read the learner's criterion-status rows and `StudentCompetencyStatus` rows filtered to those ids, one query each, with the `CompetencyMasteryStatus` string in the same query. Use the model and field names #642 lands; draft PR #802 already differs from ADR 0002's.
2. `applets/cbe/rest_api/learners.py` defines the resolver contract: a callable `(request, course_key, learner_id) -> User`, where `learner_id` is an `int` or `None`. It raises `django.http.Http404` when the named learner doesn't exist or the requester may not see them, with the same bare 404 for both. It raises `rest_framework.exceptions.PermissionDenied` when the requester may not read learner data for the course run at all. Use DRF's `PermissionDenied`, not Django's, because an exception handler modeled on `openedx_tagging`'s renders Django's as a 500. The module loads the dotted path in the top-level `OPENEDX_LEARNING_LEARNER_RESOLVER` setting at call time. The default resolver returns `request.user` when `learner_id` is `None` or the requester's own id, and raises `Http404` otherwise. The setting name, the signature, and the exceptions are a contract with openedx-platform; document them in the default's docstring. The resolver is not a key in the existing `OPENEDX_LEARNING` dict, because operators supply that dict for `openedx_content` media storage and openedx-platform's YAML loader replaces it whole, which would silently drop the LMS's resolver.
3. `LearnerCompetencyStatusesView` goes in `applets/cbe/rest_api/v1/views.py`, routed in #733's `learner_urls.py` at `v1/courses/<course_key>/competency-statuses/` with #733's authentication. It returns 400 for a malformed course key. It reads an optional `learner_id` query parameter; a non-integer gets the same 404 as an unknown id, as on the Progress tab. It calls the resolver before step 1, so a refused requester is refused even for a course run with no criteria. It returns the Description's two arrays, ordered by id.

In openedx-platform:

4. Move `ProgressTabView._get_student_user` to a module function, `get_student_user()`, in `lms/djangoapps/course_home_api/utils.py`, dropping `self` and changing nothing else. `ProgressTabView` calls it and keeps its own enrollment check and 401.
5. Beside it, add `resolve_course_learner(request, course_key, learner_id)`, which `lms/envs/common.py` names in `OPENEDX_LEARNING_LEARNER_RESOLVER`. It follows the same order as `ProgressTabView.get`:
   1. Compute `has_access(request.user, "staff", course_key)` first. `setup_masquerade` marks the requester as masquerading, and after that `has_access` denies staff.
   2. Call `get_student_user()`, so its 404s come before the enrollment refusal.
   3. Raise `PermissionDenied` when the requester lacks staff access and the resolved learner has no active enrollment, the same check `ProgressTabView` makes with `CourseEnrollment.get_enrollment(...).is_active`. This is 403 rather than `ProgressTabView`'s 401, because the AC separate a refused request from an unauthenticated one, and #733 refuses with 403.

Beyond the Acceptance Criteria, tests must cover these internal behaviors in openedx-core:
- With no course-level groups, the call costs exactly one query and never reads the status tables. With statuses present, the query count doesn't grow with the number of rows.
- A criterion recorded as `PartiallyAttempted` is returned as stored.
- A group subtree deeper than three levels returns statuses for criteria at every depth.
- For each state #733's cascades prevent, the statuses returned are exactly the learner's rows whose ids are in #733's result. Those states are an archived group whose children aren't archived, an archived object tag under a criterion that isn't, an active group whose criteria are all archived, and a tag that isn't archived under an archived ancestor.
- A configured resolver is honored: one that returns another user yields that user's statuses, and one that raises `PermissionDenied` yields 403.

Tests must cover these cases in openedx-platform:
- Staff who aren't enrolled and are masquerading as a specific learner get that learner's statuses. This test fails if the staff check moves after `get_student_user()`.
- `ProgressTabView`'s existing tests pass unchanged.

**Files to create and modify**

| File | Change |
| --- | --- |
| src/openedx_learning/applets/cbe/api.py | modified: get_learner_competency_statuses() |
| src/openedx_learning/applets/cbe/rest_api/learners.py | new: resolver loading and the requester-only default |
| src/openedx_learning/applets/cbe/rest_api/v1/views.py | modified (created by #733): LearnerCompetencyStatusesView |
| src/openedx_learning/applets/cbe/rest_api/v1/serializers.py | modified (created by #733): response serializer |
| src/openedx_learning/learner_urls.py | modified: route the view |
| openedx-platform: lms/djangoapps/course_home_api/utils.py | modified: get_student_user() and resolve_course_learner() |
| openedx-platform: lms/djangoapps/course_home_api/progress/views.py | modified: call get_student_user() |
| openedx-platform: lms/envs/common.py | modified: set OPENEDX_LEARNING_LEARNER_RESOLVER |

**Additional context**

- Blocked by #733 (the selection, `learner_urls.py`, and the LMS mount of `/api/cbe/`) and by #642 (the status tables; draft PR #802 doesn't yet include the criterion-status table).
- #742, #745, and #753 reuse this resolver and its setting.
- Group course scope follows #665's PR #847, where only the course-level group carries `course_id`. This conflicts with ADR 0002's amended Decision 2, which says every group in a course subtree carries it. Reusing #733's selection keeps this ticket correct either way.
- Known limitations:
  - The competency status is the learner's overall, cross-course status. Course staff can therefore read status a learner earned in other organizations' courses, for the competencies this course run assesses, including for a user who never enrolled in it.
  - Statuses for criteria on subsections whose results the course hides are returned as stored, and #739 and #740 mask them, so they are readable in the network response. The competency-level status already reflects those results, so masking only the criterion rows on the server wouldn't hide them.
  - The extracted `get_student_user()` keeps `ProgressTabView`'s CCX coach check, so a CCX coach can read statuses for a learner in their CCX, as on the Progress tab.
  - Statuses are returned without recomputation, so they can trail a grade by the asynchronous roll-up in `docs/openedx_learning/decisions/0004-competency-mastery-concurrency.rst`.
- Out of scope:
  - CCX courses.
  - Course-run group statuses (`StudentCompetencyCriteriaGroupStatus`). A later ticket can add them as a new array without breaking callers.
  - The per-subsection percentage score, which the plugin reads from `/api/course_home/v1/progress/{course_key}` (`block_key`, `percent_graded`).

</details>
