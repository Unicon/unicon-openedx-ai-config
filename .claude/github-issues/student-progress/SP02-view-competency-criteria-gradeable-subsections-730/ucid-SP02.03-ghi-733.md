# [BE] GET Competency Criteria for Course

GitHub: https://github.com/openedx/openedx-core/issues/733 (#733, OPEN)
Cached: 2026-09-21

## User Story
As a learner, I need my course progress page to be able to render the competencies and criteria that the subsections in my course are testing so that I can see which competencies my course covers and what each one requires of me to demonstrate mastery of it.

## Description

This ticket builds a GET endpoint that takes in a course run key and returns the Competency Criteria hierarchy for that course. Only enrolled learners and course staff can call it on the LMS, and archived or disabled competency data is left out.

For MVP, the Competency Criteria hierarchy consists of 3 levels of CompetencyCriteriaGroups, with the CompetencyCriteria below them:
- Root Group (one per competency tag, shared by every course)
    - Course Level Group (one per course under that root)
        - Bottom-tier Group
            - Competency Criterion (has subsection association)

Although MVP only supports these 3 levels, the endpoint should return the course's whole subtree under each root at any depth, so it keeps working when deeper hierarchies are supported.

Therefore, we will want to:
1. Fetch all of this course's Course Level CompetencyCriteriaGroups.
2. Fetch all of the Course Level Groups' parents, because these will be the Root Groups of the hierarchy to return.
3. Fetch each Root Group's tag, which will include its lineage.
4. Fetch all of the Course Level Groups' children (the Bottom-tier Groups for this course). Bottom-tier Groups don't store the course, so they can only be found through their parent.
5. Fetch all of the CompetencyCriteria for these Bottom-tier Groups.
6. Create the response payload in accordance with the norms of the other CBE endpoints, which return flat arrays with parent IDs. Whatever the shape, a recipient must be able to reconstruct a nesting like this one from it:
```
{
    taxonomies: [
        {
            root_groups: [
                {
                    tag: {
                        lineage: []
                    },
                    course_level_group: {
                        bottom_tier_groups: [
                            {
                                criteria: [
                                    {}
                                ]
                            }
                        ]
                    }
                }
            ]
        }
    ]
}
```
That way a recipient can see, for each taxonomy, which competency root groups are relevant to this course, and only this course's groups and criteria below each root.

Note that a course may contain subsections associated with more than one Competency Taxonomy, so the response payload will need to handle that.

The frontend will use this payload to show which competencies the course covers, which subsections test each one, and what threshold each criterion requires. So the payload needs each root group's competency tag name and taxonomy, each competency tag's lineage (the tag's ancestor chain from the top of its taxonomy down to the tag itself, which the frontend uses to group a tag under its parent and show a breadcrumb above it), each criterion's subsection usage key (which the frontend uses to get the subsection names), and each criterion's effective rule (the payload from competency_rule_profile_id or the rule_type_override, and rule_payload_override).

## Acceptance Criteria

In these scenarios, a permitted caller is one of the following:
- Under openedx-core's default permission, any signed-in user.
- On the LMS, a learner with an active enrollment in the course run, or a member of its staff.

Scenarios under a heading marked openedx-platform are verified in the LMS PR. All other scenarios are verified in the openedx-core PR. Cases that can't be set up through the product's APIs, such as states the archive cascades prevent, are covered by the unit tests listed in Technical Details rather than here.

**Access under openedx-core's default permission**

```gherkin
Scenario: A caller who is not signed in is rejected
  Given a course run that has competency criteria
  When a caller who is not signed in requests that course run's competency criteria
  Then the request is rejected as unauthenticated
  And the response contains none of that course run's competency data

Scenario: Any signed-in user can read a course run's competency criteria under the default permission
  Given openedx-core's permission for reading a course run's competency criteria, with nothing rebinding it
  And a signed-in user who is neither enrolled in nor on the staff of a course run that has competency criteria
  When that user requests the course run's competency criteria
  Then the full result for that course run is returned
```

**Access and exposure on the LMS (openedx-platform)**

```gherkin
Scenario: A learner with an active enrollment can read the criteria for their course run
  Given a learner with an active enrollment in course run X, which has competency criteria
  When the learner requests course run X's competency criteria from the LMS
  Then the full result for course run X is returned

Scenario: A learner enrolled in a course run that has not started yet can read its criteria
  Given a learner with an active enrollment in course run X, which has competency criteria and has not started yet
  When the learner requests course run X's competency criteria from the LMS
  Then the full result for course run X is returned

Scenario: A member of the course staff who is not enrolled can read the criteria
  Given a member of course run X's staff who is not enrolled in course run X
  When the staff member requests course run X's competency criteria from the LMS
  Then the full result for course run X is returned

Scenario Outline: A signed-in user with neither an active enrollment nor a staff role is refused
  Given a signed-in user who is not on course run X's staff and who <enrollment>
  When the user requests course run X's competency criteria from the LMS
  Then the request is refused as not permitted
  And the response contains none of course run X's competency data

  Examples:
    | enrollment                                              |
    | has never enrolled in course run X                      |
    | enrolled in course run X and later unenrolled           |
    | has an active enrollment only in a different course run |

Scenario: The LMS does not serve the competency authoring routes
  Given an LMS with the learner competency routes from openedx-core mounted
  When a request is sent to the LMS for any competency authoring operation from #665, #674, #675, or #681
  Then the LMS reports that the route does not exist
```

**Course resolution**

```gherkin
Scenario: A malformed course run key is rejected
  Given a signed-in caller
  When the caller requests competency criteria for a value that is not a well-formed course run key
  Then the request is rejected with a message saying the course run key is malformed
  And no competency data is returned

Scenario Outline: A well-formed key with no competency criteria returns an empty result
  Given <course run>
  When a permitted caller requests that course run's competency criteria
  Then the request succeeds
  And the result contains no taxonomies, competencies, groups, or criteria

  Examples:
    | course run                                                             |
    | a course run in the catalog that has never had competency criteria     |
    | a well-formed course run key that matches no course run in the catalog |
```

**What the result contains**

```gherkin
Scenario: The result can be reassembled from the taxonomy down to each criterion and carries what the Progress tab displays
  Given a competency with a root group, a course-level group for course run X beneath it, one bottom-tier group beneath that, and two criteria on two different subsections in the bottom-tier group
  When a permitted caller requests course run X's competency criteria
  Then the result contains the competency's taxonomy, the competency, the root group, the course-level group, the bottom-tier group, and both criteria
  And each root group names its competency, and each competency names its taxonomy
  And every other group and every criterion names its parent group, and every parent it names is also in the result
  And the taxonomy carries its name
  And the competency carries its name and its external identifier
  And every group, including the root group, carries its name, its combining logic as stored, and its position among its siblings
  And each criterion carries the usage key of the subsection it is measured on

Scenario: Only course run X's part of a competency shared with other course runs is returned
  Given a competency whose root group has one course-level group for course run X and another for course run Y, each with its own bottom-tier group and criteria
  And a second competency whose only criteria are in course run Y
  When a permitted caller requests course run X's competency criteria
  Then the result contains the shared root group and course run X's course-level group, bottom-tier group, and criteria
  And no group or criterion from course run Y's branch appears
  And the second competency does not appear

Scenario: Competencies from two taxonomies each appear under their own taxonomy
  Given course run X has criteria for a competency in competency taxonomy A and for a competency in competency taxonomy B
  And the same subsections also carry tags from a taxonomy that is not a competency taxonomy
  When a permitted caller requests course run X's competency criteria
  Then taxonomies A and B both appear, each with its own name
  And each competency appears under its own taxonomy only
  And no tag from the taxonomy that is not a competency taxonomy appears

Scenario: Each competency carries its lineage from the top of its taxonomy
  Given a competency taxonomy in which "Root Cause Analysis" is a child of "Problem Definition", which is a child of the top-level tag "Problem Solving"
  And "Communication" is a top-level tag in the same taxonomy
  And course run X has criteria for "Root Cause Analysis" and for "Communication"
  When a permitted caller requests course run X's competency criteria
  Then "Root Cause Analysis" carries the lineage "Problem Solving", "Problem Definition", "Root Cause Analysis", in that order
  And each entry in that lineage carries the identifier of the tag it names
  And "Communication" carries a lineage whose only entry is "Communication", carrying the "Communication" tag's identifier

Scenario: A criterion without an override carries the system default rule profile's rule
  Given a criterion in course run X that has no override and is assigned the system default rule profile, which requires a grade of at least 75 percent
  When a permitted caller requests course run X's competency criteria
  Then that criterion carries the rule type Grade, the comparison gte, and a threshold of 75 percent

Scenario: A criterion's own override takes the place of the rule profile
  Given a criterion in course run X whose own override requires a grade of at least 82 percent
  And the system default rule profile requires a grade of at least 75 percent
  When a permitted caller requests course run X's competency criteria
  Then that criterion carries the rule type Grade, the comparison gte, and a threshold of 82 percent

Scenario: Repeated requests list everything in the same order
  Given course run X has criteria for several competencies across two taxonomies
  When a permitted caller requests course run X's competency criteria twice with no change in between
  Then both results list every taxonomy, competency, group, and criterion in the same order
```

**Archived and disabled records**

In these scenarios, a learner already has a recorded competency status through every criterion involved. Without one, deleting a criterion, group, tag, or taxonomy removes it outright instead of archiving it.

```gherkin
Scenario: An archived criterion is left out while its siblings stay
  Given a bottom-tier group in course run X that holds two criteria
  When one of the criteria is archived through #674
  And a permitted caller requests course run X's competency criteria
  Then only the criterion that is not archived is returned

Scenario Outline: Archiving a group takes its whole subtree out of the result while the rest stays
  Given course run X has criteria for two competencies, and the first competency's course-level group for course run X has two bottom-tier groups, each holding criteria
  When the first competency's <group> is archived through #675
  And a permitted caller requests course run X's competency criteria
  Then the archived group, every group beneath it, and every criterion beneath it are absent
  And no remaining group or criterion names an absent group as its parent
  And every group and criterion that is not beneath the archived group is still returned
  And a competency with nothing left beneath it is absent

  Examples:
    | group                               |
    | first bottom-tier group             |
    | course-level group for course run X |

Scenario Outline: A competency whose tag or taxonomy is archived is left out with everything beneath it
  Given course run X has criteria for competency "Root Cause Analysis" in competency taxonomy A and for competency "Communication" in competency taxonomy B
  And <archiving>
  When a permitted caller requests course run X's competency criteria
  Then "Root Cause Analysis", its root group, and every group and criterion beneath that root group are absent
  And "Communication" and its criteria are still returned under taxonomy B

  Examples:
    | archiving                                                    |
    | the "Root Cause Analysis" tag is archived                    |
    | taxonomy A is archived, and none of its tags is              |
    | taxonomy A is disabled                                       |

Scenario Outline: A course run whose criteria are all excluded returns an empty result
  Given course run X has competency criteria, and <exclusion>
  When a permitted caller requests course run X's competency criteria
  Then the result contains no taxonomies, competencies, groups, or criteria, the same as for a course run that never had criteria

  Examples:
    | exclusion                                                 |
    | every one of its criteria has been archived through #674  |
    | the only taxonomy its criteria belong to is disabled      |
```

**Subsections a learner cannot see (openedx-platform)**

```gherkin
Scenario: Criteria on subsections a learner cannot see are still returned
  Given course run X has criteria on five subsections: one released, one not yet released, one hidden from learners, one restricted to a content group the learner is not in, and one since deleted from the course
  And a learner with an active enrollment in course run X
  When the learner requests course run X's competency criteria from the LMS
  Then all five criteria are returned, each carrying its subsection's usage key

Scenario: Every permitted caller gets the same result for a course run
  Given two learners with active enrollments in course run X who are in different content groups
  And a member of course run X's staff
  When each of the three requests course run X's competency criteria from the LMS
  Then all three receive the same result
```

<details>
<summary>Technical Details</summary>

This is a suggested approach, not the source of truth. The User Story, Description, and Acceptance Criteria define what must be true when the work is done.

**Summary**

openedx-core adds a learner-facing view that finds the course run's course-level groups in one indexed query and returns the empty result immediately when there are none. This keeps cheap the emptiness check that #734 and #839 make on every Progress tab render. When there are course-level groups, the view walks down each course-level group's subtree, loads the surviving criteria with their effective rules, and prunes every branch that leads to no criterion. Who may read the criteria depends on openedx-platform data, so the read permission is a named django-rules entry with a permissive default. openedx-platform rebinds that permission and mounts only this learner URL module on the LMS.

**Approach**

In openedx-core, all within `openedx_learning`, which may import `openedx_catalog` and `openedx_tagging`:

1. `applets/cbe/rules.py` registers the permission `openedx_learning.view_course_competency_criteria`, checked on a `CourseKey` and defaulting to `rules.is_authenticated`. openedx-platform rebinds it, so the name is a contract with openedx-platform. `openedx_learning/rules.py` imports this module for `AutodiscoverRulesConfig`.
2. `get_course_competency_criteria(course_key)` in `applets/cbe/api.py` stays out of `__all__` until a second caller needs it. It takes no user, so the result is the same for every permitted caller of a course run, which #839 relies on. It runs these steps:
   1. One query for the course-level groups: `CompetencyCriteriaGroup` rows with `course__course_key=course_key`, not archived, whose parent (the root) is not archived, whose root tag passes #778's tag exclusion (a tag counts as archived when it or its taxonomy is archived), none of whose ancestor tags is archived (a tag under an archived ancestor is treated as archived too, matched through the ancestors' stored `lineage` prefixes), and whose taxonomy is enabled, with `select_related("parent__tag__taxonomy")`. If this query finds nothing, return the empty result; it is the only query on the empty path. A key with no catalog `CourseRun` row falls out of the same join, so don't call `get_course_run()`, which raises.
   2. Walk down one query per level with `parent_id__in=<previous level>` and not archived, until a level comes back empty. Leaf groups have `course_id` null (#665), so only their parent finds them. An archived group hides everything below it, even though #675's cascade should already have archived everything below it too.
   3. One query for criteria: `group_id__in=<every group found>`, not archived, whose object tag passes #778's association exclusion, with `select_related("object_tag", "rule_profile")`. The effective rule is the profile's `rule_type` and `rule_payload` when `rule_profile_id` is set, and otherwise the two override fields. ADR 0002 guarantees exactly one of the two is set. Keep this resolution on `CompetencyCriterion`, or reuse one if #716 adds it, so evaluation code can share it.
   4. Prune bottom-up in Python. A group survives if it has a surviving criterion or a surviving child group. A root, its tag, and its taxonomy survive if anything below them does.
3. `CourseCompetencyCriteriaView` in `applets/cbe/rest_api/v1/views.py` parses the key (`InvalidKeyError` returns 400), checks the permission (403 if denied), and returns flat arrays. It uses JWT and session authentication, as `openedx_tagging`'s `view_auth_classes` does, because the Learning MFE calls it with a JWT cookie.

   ```json
   {
     "taxonomies": [{"id": 3, "name": "Core Skills"}],
     "tags": [{"id": 41, "taxonomy_id": 3, "value": "Analysis", "external_id": "CT-1",
               "lineage": [{"id": 40, "value": "Critical Thinking"}, {"id": 41, "value": "Analysis"}]}],
     "groups": [{"id": 7, "parent_id": null, "tag_id": 41, "name": "Analysis", "logic_operator": "OR", "ordering": 0},
                {"id": 12, "parent_id": 7, "tag_id": 41, "name": "Course X", "logic_operator": "AND", "ordering": 0}],
     "criteria": [{"id": 90, "group_id": 15, "object_id": "block-v1:...", "rule_type": "Grade",
                   "rule_payload": {"op": "gte", "value": 0.75, "scale": "percent"}}]
   }
   ```

   A root is a group whose `parent_id` is null. Each `lineage` entry carries the tag's `id` and `value`, ordered from the top of the taxonomy down to the tag itself, so #738 can key parent-competency statuses by tag id. The ids aren't in `Tag.get_lineage()`, which returns only value strings. Every ancestor's stored `Tag.lineage` is a prefix of the tag's own `lineage`, so one more query, filtering on `taxonomy_id` and `lineage__in=<every prefix>` (an indexed column), loads the ancestors for every tag in the result. The empty path never reaches this query. `rule_payload` is returned as stored, so a Grade `value` is a fraction from 0.0 to 1.0. Because of pruning, the four arrays are always empty together.
4. `openedx_learning/learner_urls.py` routes `v1/courses/<course_key>/competency-criteria/` to the view. It is separate from #665's `openedx_learning.urls`, so the LMS can serve it without also serving #665's authoring write routes, which stay Studio-only.

In openedx-platform, where `openedx_learning` is already in the LMS's `INSTALLED_APPS`:

5. `lms/urls.py` adds `path("api/cbe/", include("openedx_learning.learner_urls"))`.
6. In `lms/djangoapps/courseware/rules.py`, which loads only in the LMS and already rebinds permissions with `rules.set_perm`, import openedx-core's rules module first, then rebind the permission to `CourseEnrollment.is_enrolled(user, course_key)` or `has_access(user, "staff", course_key)`. That is the check ProgressTabView makes after it loads the course. The Progress tab applies its full `load` check (course visibility and start date) before the MFE calls this endpoint, so this permission doesn't repeat it.

Tests must cover these cases in openedx-core:
- The empty path costs one query, and the same one query however many criteria other course runs hold.
- An unknown course key.
- A malformed key.
- Two taxonomies.
- A root shared by two courses returns only this course's subtree.
- A subtree deeper than three levels, which #665's API doesn't create in MVP but the database allows: every group in it appears, and criteria appear at every depth.
- Each exclusion prunes all the way up. The exclusions are an archived criterion, bottom-tier group, intermediate group, course-level group, root, tag, or taxonomy, and a disabled taxonomy.
- An archived group whose criteria and child groups are not marked archived, a state #675's cascade prevents, is still pruned with everything beneath it.
- An archived tag association under a criterion that is not archived, a state reachable only through a direct tagging API call, leaves that criterion out.
- An active bottom-tier group whose criteria are all archived, a state #674's upward cascade prevents, is absent.
- A competency tag that is not archived but has an archived ancestor tag, a state #780's subtree archiving prevents, is absent with everything beneath its root group.
- A change to the system default profile's threshold appears on the next request, which shows the rule is read fresh rather than cached.
- A criterion with overrides.
- A top-level tag's one-entry lineage.
- A three-level tag's lineage, where each entry carries its own tag's id in order from the top of the taxonomy.

In openedx-platform, the tests must cover:
- An enrolled learner, an unenrolled user, and an inactive enrollment.
- Course staff with no enrollment.

**Files to create and modify**

| File | Change |
| --- | --- |
| src/openedx_learning/applets/cbe/rules.py | new: the permission, with its default |
| src/openedx_learning/rules.py | new: imports the applet rules |
| src/openedx_learning/applets/cbe/api.py | modified: get_course_competency_criteria() |
| src/openedx_learning/applets/cbe/models/criteria.py | modified: effective rule on CompetencyCriterion |
| src/openedx_learning/applets/cbe/rest_api/v1/views.py | modified: CourseCompetencyCriteriaView |
| src/openedx_learning/applets/cbe/rest_api/v1/serializers.py | modified: response serializers |
| src/openedx_learning/learner_urls.py | new: learner-only URL module |
| openedx-platform: lms/urls.py | modified: mount learner_urls |
| openedx-platform: lms/djangoapps/courseware/rules.py | modified: rebind the permission |

**Additional context**

- This view, its rebindable permission, and the LMS-only learner URL module are the learner-facing API pattern for CBE. #738, #742, #745, and #753 follow it.
- #734 and #839 consume this response. #734 shows a placeholder row in place of any criterion whose subsection isn't in the viewer's learning_sequences course outline.
- Out of scope:
  - Deciding how criteria on subsections a learner can't see are displayed, which belongs to #734.
  - Response caching.
  - Returning archived criteria and groups with an archived indicator, so a learner can see the competency history they earned against them. Learner statuses survive archiving (#816); showing them is a post-MVP question for the status endpoints starting at #738.
  - Excluding criteria whose competency taxonomy isn't assigned to the course's organization. Competency taxonomies are instance-wide for MVP, and the Competency Management page (#664, #773) doesn't check organization assignment, so this endpoint doesn't either. If org assignment is respected later, it should be added across CBE at once.
- Blocked by the CBE models and `archived` fields (#613, #716, #776), by #778's tag and object-tag exclusion, and by #665 (the system-default profile on create, the `/api/cbe/` prefix, and the `rest_api` package).
- `docs/openedx_learning/decisions/0002-competency-criteria-model.rst`: the profile-or-overrides invariant and fractional thresholds.
- `src/openedx_tagging/rules.py` and openedx-platform's `content_tagging/rules.py`: the precedent for openedx-core defaults that the platform rebinds.
- `docs/openedx_catalog/decisions/0001-catalog-models-usage.rst`: every existing course has a `CourseRun` row, and REST APIs identify courses by course key, never by `CourseRun` ID.

</details>

## Open Questions

- (implementer) Whether the course key goes in the path or in a `?course_key=` query parameter. It must accept every valid course key, including `+` and `:`.
- (implementer) The deterministic order of each array. The recommendation is groups by `ordering` and then `id`, and everything else by `id`.
