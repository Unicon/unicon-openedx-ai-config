# [BE] GET Competency Criteria for Course

GitHub: https://github.com/openedx/openedx-core/issues/733 (#733, OPEN)
Cached: 2026-09-21

## User Story
As a learner, I need my course progress page to be able to render the competencies and criteria that the subsections in my course are testing so that I can understand my progress towards mastering them.

## Description

This ticket builds a GET endpoint that takes in a course run key and returns the Competency Criteria hierarchy for that course.

For MVP, the Competency Criteria hierarchy consists of 3 levels of CompetencyCriteriaGroups, with the CompetencyCriteria below them:
- Root Group (one per competency tag, shared by every course)
    - Course Level Group (one per course under that root)
        - Bottom-tier Group
            - Competency Criterion (has subsection association)

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

Scenarios under a heading marked openedx-platform are verified in the LMS PR. All other scenarios are verified in the openedx-core PR.

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

**Access and exposure on the LMS and Studio (openedx-platform)**

```gherkin
Scenario: A learner with an active enrollment can read the criteria for their course run
  Given a learner with an active enrollment in course run X, which has competency criteria
  When the learner requests course run X's competency criteria from the LMS
  Then the full result for course run X is returned

# Depends on the (architect, final review) question about whether the LMS access rule is exactly "an active enrollment or course staff".
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

Scenario: The LMS serves the course run's competency criteria and none of the competency authoring routes
  Given an LMS with the learner competency routes from openedx-core mounted
  When a request is sent to the LMS for any competency authoring operation from #665, #674, #675, or #681
  Then the LMS reports that the route does not exist
  And a request to the same LMS for a course run's competency criteria returns that course run's result

# Depends on the (architect, final review) question about whether the course read is served on the LMS only.
Scenario: Studio does not serve a course run's competency criteria
  Given Studio with the competency authoring routes from openedx-core mounted
  When a signed-in user requests a course run's competency criteria from Studio
  Then Studio reports that the route does not exist
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

Scenario: The empty answer costs the same however much competency data other course runs hold
  Given a course run with no competency criteria
  And competency criteria authored in many other course runs on the same site
  When a permitted caller requests that course run's competency criteria
  Then the empty result is produced with the same number of database queries as on a site with no competency data
```

**What the result contains**

```gherkin
Scenario: The result can be reassembled from the taxonomy down to each criterion
  Given a competency with a root group, a course-level group for course run X beneath it, one bottom-tier group beneath that, and two criteria on two different subsections in the bottom-tier group
  When a permitted caller requests course run X's competency criteria
  Then the result contains the competency's taxonomy, the competency, the root group, the course-level group, the bottom-tier group, and both criteria
  And each root group names its competency, and each competency names its taxonomy
  And every other group and every criterion names its parent group, and every parent it names is also in the result

Scenario: The result carries the data the Progress tab displays
  Given course run X has two criteria for one competency
  When a permitted caller requests course run X's competency criteria
  Then the taxonomy carries its name
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
  And "Communication" carries a lineage whose only entry is "Communication"

Scenario: A course-scoped subtree deeper than three levels is returned in full
  Given course run X's course-level group for a competency has two child groups
  And the first child group holds criteria
  And the second child group holds no criteria of its own but has a child group that holds criteria
  When a permitted caller requests course run X's competency criteria
  Then every group in that subtree appears, each naming its parent
  And every criterion appears under the group that holds it, at both depths

Scenario: A criterion without an override carries the rule from its assigned rule profile
  Given a criterion in course run X that has no override and is assigned a rule profile requiring a grade of at least 75 percent
  When a permitted caller requests course run X's competency criteria
  Then that criterion carries the rule type Grade, the comparison "at least", and a threshold of 75 percent

Scenario: A criterion's own override takes the place of a rule profile
  Given a criterion in course run X whose own override requires a grade of at least 82 percent
  And the system default rule profile requires a grade of at least 75 percent
  When a permitted caller requests course run X's competency criteria
  Then that criterion carries the rule type Grade, the comparison "at least", and a threshold of 82 percent

Scenario: A change to a rule profile appears on the next request
  Given two criteria in course run X that are assigned the same rule profile, which requires at least 75 percent
  And course run X's competency criteria have already been requested once
  When the profile is changed to require at least 80 percent and course run X's competency criteria are requested again
  Then both criteria carry a threshold of 80 percent

Scenario: A criterion assigned an archived rule profile keeps that profile's rule
  Given a criterion in course run X that is assigned a rule profile which has since been archived
  When a permitted caller requests course run X's competency criteria
  Then the criterion is returned, carrying the archived profile's rule

Scenario: Repeated requests list everything in the same order
  Given course run X has criteria for several competencies across two taxonomies
  When a permitted caller requests course run X's competency criteria twice with no change in between
  Then both results list every taxonomy, competency, group, and criterion in the same order
```

**Archived and disabled records**

```gherkin
Scenario: An archived criterion is left out while its siblings stay
  Given a bottom-tier group in course run X that holds two criteria, one of them archived
  When a permitted caller requests course run X's competency criteria
  Then only the criterion that is not archived is returned

Scenario: A criterion whose tag association is archived is left out
  Given a bottom-tier group in course run X that holds two criteria
  And the tag association behind one of them is archived, while that criterion itself is not
  When a permitted caller requests course run X's competency criteria
  Then only the other criterion is returned

Scenario: An archived bottom-tier group is left out while its sibling stays
  Given course run X's course-level group for a competency has two bottom-tier groups, each holding criteria
  And the first bottom-tier group is archived, while its criteria are not marked archived
  When a permitted caller requests course run X's competency criteria
  Then the first bottom-tier group and its criteria are absent
  And no criterion in the result names the archived group as its parent
  And the second bottom-tier group and its criteria are still returned

Scenario Outline: An archived root or course-level group takes its competency out of course run X's result
  Given course run X has criteria for two competencies
  And the first competency's <group> is archived, while nothing beneath it is marked archived
  When a permitted caller requests course run X's competency criteria
  Then the first competency, its groups, and its criteria are absent
  And the second competency and its criteria are still returned

  Examples:
    | group                               |
    | root group                          |
    | course-level group for course run X |

Scenario Outline: A competency whose tag, any ancestor tag, or taxonomy is retired is left out with everything beneath it
  Given competency taxonomy A, in which "Root Cause Analysis" is a child of "Problem Definition", which is a child of the top-level tag "Problem Solving"
  And competency taxonomy B, which holds the competency "Communication"
  And course run X has criteria for "Root Cause Analysis" and for "Communication"
  And <retirement>
  When a permitted caller requests course run X's competency criteria
  Then "Root Cause Analysis", its root group, and every group and criterion beneath that root group are absent
  And "Communication" and its criteria are still returned under taxonomy B

  Examples:
    | retirement                                                                             |
    | the "Root Cause Analysis" tag is archived                                              |
    | the parent tag "Problem Definition" is archived, and "Root Cause Analysis" is not      |
    | the grandparent tag "Problem Solving" is archived, and neither of the tags below it is |
    | taxonomy A is archived, and none of its tags is                                        |
    | taxonomy A is disabled                                                                 |

Scenario Outline: A course run whose criteria are all excluded returns an empty result
  Given course run X has competency criteria, and <exclusion>
  When a permitted caller requests course run X's competency criteria
  Then the result contains no taxonomies, competencies, groups, or criteria, the same as for a course run that never had criteria

  Examples:
    | exclusion                                            |
    | every one of its criteria is archived                |
    | the only taxonomy its criteria belong to is disabled |

Scenario: Nothing appears without a criterion beneath it
  Given course run X has criteria for competencies in taxonomies A and B
  And every criterion in one of taxonomy A's bottom-tier groups for course run X is archived, while that group itself is not
  And every criterion under taxonomy B is archived, while none of its groups is
  When a permitted caller requests course run X's competency criteria
  Then the bottom-tier group whose criteria are all archived is absent
  And taxonomy B, its competencies, and its groups are absent
  And every taxonomy, competency, and group that remains has at least one criterion beneath it
```

**Organization assignment (openedx-platform)**

```gherkin
Scenario: Criteria from a competency taxonomy no longer assigned to the course run's organization are left out
  Given course run X belongs to organization O
  And course run X has criteria for a competency in competency taxonomy A and for a competency in competency taxonomy B, both assigned to organization O when the criteria were authored
  And taxonomy A is later unassigned from organization O and is not assigned to all organizations
  When a permitted caller requests course run X's competency criteria from the LMS
  Then taxonomy A, its competencies, its groups, and its criteria are absent
  And taxonomy B and its criteria are still returned

Scenario Outline: A competency taxonomy assigned to the course run's organization, or to all organizations, is kept
  Given course run X belongs to organization O
  And course run X has criteria for a competency in competency taxonomy A
  And taxonomy A is assigned to <assignment>
  When a permitted caller requests course run X's competency criteria from the LMS
  Then taxonomy A and its criteria are returned

  Examples:
    | assignment        |
    | organization O    |
    | all organizations |

Scenario: A course run whose only competency taxonomy is no longer assigned to its organization returns an empty result
  Given course run X belongs to organization O, and all of its criteria belong to competency taxonomy A
  And taxonomy A is no longer assigned to organization O or to all organizations
  When a permitted caller requests course run X's competency criteria from the LMS
  Then the result contains no taxonomies, competencies, groups, or criteria, the same as for a course run that never had criteria

Scenario: On the LMS, the empty answer costs the same however much competency data other course runs hold
  Given a learner with an active enrollment in course run X, which has no competency criteria
  And competency criteria authored in many other course runs, under taxonomies assigned to several organizations
  When the learner requests course run X's competency criteria from the LMS
  Then the empty result is produced with the same number of database queries as on a site with no competency data
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

openedx-core adds a learner-facing view that finds the course run's course-level groups in one indexed query and returns the empty result immediately when there are none. This keeps cheap the emptiness check that #734 and #839 make on every Progress tab render. When there are course-level groups, the view walks down each course-level group's subtree, loads the surviving criteria with their effective rules, and prunes every branch that leads to no criterion. Two rules need openedx-platform data: who may read the criteria, and whether a taxonomy is still assigned to the course's organization. Both are named django-rules entries with permissive defaults. openedx-platform rebinds both and mounts only this learner URL module on the LMS.

**Approach**

In openedx-core, all within `openedx_learning`, which may import `openedx_catalog` and `openedx_tagging`:

1. `applets/cbe/rules.py` registers two names that openedx-platform rebinds, so both names are a contract with openedx-platform:
   - The permission `openedx_learning.view_course_competency_criteria`, checked on a `CourseKey`, defaulting to `rules.is_authenticated`.
   - The rule `openedx_learning.competency_taxonomy_applies_to_course`, tested with `rules.test_rule(name, course_key, taxonomy)`, defaulting to `rules.always_true`. The rule takes no user, so the response stays the same for every caller of a course run, which #839 relies on.

   `openedx_learning/rules.py` imports this module for `AutodiscoverRulesConfig`. `applets/cbe/api.py` imports it too, because `test_rule` returns false for an unregistered rule, which would silently empty every response.
2. `get_course_competency_criteria(course_key)` in `applets/cbe/api.py` stays out of `__all__` until a second caller needs it. It runs these steps:
   1. One query for the course-level groups: `CompetencyCriteriaGroup` rows with `course__course_key=course_key`, not archived, whose parent (the root) is not archived, whose root tag passes #778's tag exclusion (a tag counts as archived when it, any ancestor, or its taxonomy is archived), and whose taxonomy is enabled, with `select_related("parent__tag__taxonomy")`. If this query finds nothing, return the empty result; it is the only query on the empty path. A key with no catalog `CourseRun` row falls out of the same join, so don't call `get_course_run()`, which raises.
   2. Drop the course-level groups whose taxonomy fails the taxonomy rule, testing each distinct taxonomy once.
   3. Walk down one query per level with `parent_id__in=<previous level>` and not archived, until a level comes back empty. Leaf groups have `course_id` null (#665), so only their parent finds them. An archived group hides everything below it.
   4. One query for criteria: `group_id__in=<every group found>`, not archived, whose object tag passes #778's association exclusion, with `select_related("object_tag", "rule_profile")`. The effective rule is the profile's `rule_type` and `rule_payload` when `rule_profile_id` is set, even when that profile is archived, and otherwise the two override fields. ADR 0002 guarantees exactly one of the two is set. Keep this resolution on `CompetencyCriterion`, or reuse one if #716 adds it, so evaluation code can share it.
   5. Prune bottom-up in Python. A group survives if it has a surviving criterion or a surviving child group. A root, its tag, and its taxonomy survive if anything below them does.
3. `CourseCompetencyCriteriaView` in `applets/cbe/rest_api/v1/views.py` parses the key (`InvalidKeyError` returns 400), checks the permission (403 if denied), and returns flat arrays. It uses JWT and session authentication, as `openedx_tagging`'s `view_auth_classes` does, because the Learning MFE calls it with a JWT cookie.

   ```json
   {
     "taxonomies": [{"id": 3, "name": "Core Skills"}],
     "tags": [{"id": 41, "taxonomy_id": 3, "value": "Analysis", "external_id": "CT-1",
               "lineage": ["Critical Thinking", "Analysis"]}],
     "groups": [{"id": 7, "parent_id": null, "tag_id": 41, "name": "Analysis", "logic_operator": "OR", "ordering": 0},
                {"id": 12, "parent_id": 7, "tag_id": 41, "name": "Course X", "logic_operator": "AND", "ordering": 0}],
     "criteria": [{"id": 90, "group_id": 15, "object_id": "block-v1:...", "rule_type": "Grade",
                   "rule_payload": {"op": "gte", "value": 0.75, "scale": "percent"}}]
   }
   ```

   A root is a group whose `parent_id` is null. `lineage` comes from `Tag.get_lineage()`, which runs no query. `rule_payload` is returned as stored, so a Grade `value` is a fraction from 0.0 to 1.0. Because of pruning, the four arrays are always empty together.
4. `openedx_learning/learner_urls.py` routes `v1/courses/<course_key>/competency-criteria/` to the view. It is separate from #665's `openedx_learning.urls`, so the LMS can serve it without also serving #665's authoring write routes.

In openedx-platform, where `openedx_learning` is already in the LMS's `INSTALLED_APPS`:

5. `lms/urls.py` adds `path("api/cbe/", include("openedx_learning.learner_urls"))`.
6. Rebind both names, importing openedx-core's rules module first:
   - In `lms/djangoapps/courseware/rules.py`, which loads only in the LMS and already rebinds permissions with `rules.set_perm`, rebind the permission to `CourseEnrollment.is_enrolled(user, course_key)` or `has_access(user, "staff", course_key)`. That is the check ProgressTabView makes after it loads the course.
   - In `openedx/core/djangoapps/content_tagging/rules.py`, rebind the taxonomy rule with `rules.set_rule`: true when `TaxonomyOrg.get_relationships(taxonomy, TaxonomyOrg.RelType.OWNER, org_short_name=course_key.org)` finds a row, which covers both the course's organization and all organizations (`org=None`). A taxonomy with no `TaxonomyOrg` rows is excluded. The short-name match is case-sensitive.

Tests must cover these cases in openedx-core:
- The empty path costs one query.
- An unknown course key.
- A malformed key.
- Two taxonomies.
- A root shared by two courses returns only this course's subtree.
- A subtree deeper than three levels.
- Each exclusion prunes all the way up. The exclusions are an archived criterion, group, intermediate group, root, object tag, tag, ancestor tag, or taxonomy; a disabled taxonomy; and a taxonomy rule that returns false.
- A criterion on an archived profile.
- A criterion with overrides.
- A top-level tag's one-entry lineage.

In openedx-platform, the tests must cover:
- An enrolled learner, an unenrolled user, and an inactive enrollment.
- Course staff with no enrollment.
- A taxonomy assigned to the course's organization, to all organizations, only to another organization, and to none.

**Files to create and modify**

| File | Change |
| --- | --- |
| src/openedx_learning/applets/cbe/rules.py | new: the permission and the taxonomy rule, with defaults |
| src/openedx_learning/rules.py | new: imports the applet rules |
| src/openedx_learning/applets/cbe/api.py | modified: get_course_competency_criteria() |
| src/openedx_learning/applets/cbe/models.py | modified: effective rule on CompetencyCriterion |
| src/openedx_learning/applets/cbe/rest_api/v1/views.py | modified: CourseCompetencyCriteriaView |
| src/openedx_learning/applets/cbe/rest_api/v1/serializers.py | modified: response serializers |
| src/openedx_learning/learner_urls.py | new: learner-only URL module |
| openedx-platform: lms/urls.py | modified: mount learner_urls |
| openedx-platform: lms/djangoapps/courseware/rules.py | modified: rebind the permission |
| openedx-platform: openedx/core/djangoapps/content_tagging/rules.py | modified: rebind the taxonomy rule |

**Additional context**

- This view, its two rebindable rules, and the LMS-only learner URL module are the learner-facing API pattern for CBE. #738, #742, #745, and #753 follow it.
- #734 and #839 consume this response.
- Out of scope:
  - Filtering criteria by what the learner can see, which belongs to #734.
  - Response caching.
- Blocked by the CBE models and `archived` fields (#613, #716, #776), by #778's tag and object-tag exclusion including the archived-ancestor rule, and by #665 (the system-default profile on create, the `/api/cbe/` prefix, and the `rest_api` package).
- `docs/openedx_learning/decisions/0002-competency-criteria-model.rst`: the profile-or-overrides invariant and fractional thresholds.
- `src/openedx_tagging/rules.py` and openedx-platform's `content_tagging/rules.py`: the precedent for openedx-core defaults that the platform rebinds.
- `docs/openedx_catalog/decisions/0001-catalog-models-usage.rst`: every existing course has a `CourseRun` row, and REST APIs identify courses by course key, never by `CourseRun` ID.

</details>

## Open Questions

- (architect, final review) Who adds the archived-ancestor rule to the tagging read path? #778 excludes a tag when the tag or its taxonomy is archived, but not when an ancestor is, and #733 should reuse a tagging rule rather than write its own. Options: A) amend #778 before it merges (recommended); B) a small follow-up tagging ticket that #733 depends on; C) #733 adds the rule to `openedx_tagging` itself.
- (architect, final review) Is LMS access exactly "active enrollment or course staff", or should it also include the Progress tab's full `load` check (course visibility and start date)? The `load` check loads the course from the modulestore on every Progress tab render for every course, and the Progress tab already applies it before the MFE calls this endpoint, so the two options differ only for direct API calls. Options: A) enrollment or staff (recommended); B) the full `load` check.
- (architect, final review) Is the learner read mounted on the LMS only, through its own `openedx_learning.learner_urls` module outside #665's `openedx_learning.urls`? Options: A) a separate module, LMS only (recommended); B) inside `openedx_learning.urls`, which would mount #665's authoring writes on the LMS too.
- (architect, final review) Where does the filter for "taxonomy is still assigned to the course's organization" live? `TaxonomyOrg` exists only in openedx-platform, and openedx-core must not import it. Options: A) a named django-rules rule with no user argument, tested inside the API, defaulting to allow, and rebound by the platform (recommended); B) a batch callable supplied through settings; C) a platform-owned wrapper view or subclass; D) an openedx-filters step.
- (architect, final review) Four concerns about the human-written sections. Steps 1 to 5 of the Description fetch exactly three levels of groups, while the pre-handoff decision returns the course's subtree at any depth. The Description doesn't mention the openedx-platform half of the work (the LMS mount and the permission rebind) or who may call the endpoint. The Context still holds its placeholder text; candidate bullets are the blockers #613, #665, #716, #776, and #778, and the consumers #734 and #839. The User Story ends "understand my progress towards mastering them", but this ticket returns requirements only, and progress arrives with the status work that starts at #738.
- (implementer) Whether the course key goes in the path or in a `?course_key=` query parameter. It must accept every valid course key, including `+` and `:`.
- (implementer) The deterministic order of each array. The recommendation is groups by `ordering` and then `id`, and everything else by `id`.

## Notes for drafting

### Decisions from the pre-handoff check

- LMS exposure: #733 adds a learner-only URL module under `/api/cbe/v1/` in openedx-core, and also makes the openedx-platform `lms/urls.py` change that mounts only that module, in the same ticket (two PRs). #665's authoring write routes stay off the LMS.
- Permission: openedx-core registers a named django-rules permission that allows any authenticated user by default. openedx-platform rebinds it to the Progress tab's own access check: an active enrollment, or course staff.
- Threshold: each criterion in the response carries its resolved effective rule (rule type and payload), taken from its overrides or else its assigned profile. The frontend never resolves a profile ID itself.
- Display data inline: the IDs, plus each criterion's `object_id` (subsection usage key), each group's `logic_operator`, `name` and `ordering`, each competency tag's `value`, `external_id` and `lineage`, and each taxonomy's ID and `name`. Subsection display names come from the LMS Course Home Outline API, joined by usage key. That API keeps unreleased subsections with their `display_name`, confirmed in openedx-platform's learning_sequences `ScheduleOutlineProcessor`.
- Empty and unknown courses: a well-formed course key with no criteria, or with no catalog CourseRun row, returns 200 with empty arrays. A malformed key returns 400. #734 uses the empty 200 response as its check for whether to render, so the empty case must stay cheap.
- Tree depth: return each relevant root plus its complete course-scoped subtree at any depth, with criteria for every group in that subtree. Don't hard-code three levels, and don't wait on #731.
- Leaf `course_id`: treat #665's implementation as the database truth, meaning leaf groups have `course_id` null. Find the course-level groups by course, then walk down to their children. Neither #665 nor ADR 0002 is updated by this work.
- Tag lineage: each competency tag in the response also carries its `lineage`, read from the Tag row #733 already loads, so it adds no query. `lineage` is the list of tag values from the root down to and including the tag itself, matching `ObjectTagMinimalSerializer.lineage`. #734 uses it for parent grouping, the breadcrumb, and detecting a top-level tag (a tag whose lineage has one entry). `depth` is left out because it is always the lineage length minus 1, matching `ObjectTagMinimalSerializer`, which returns `lineage` without `depth`. No separate LMS tags endpoint is built: the LMS mounts no tagging routes today, and content tagging's MVP deliberately keeps tags Studio-only.
- Archived ancestors: a competency tag is excluded, with its root group and everything below it, when any tag in its lineage is archived, not only its direct parent. Archiving does not cascade, so a grandparent can be archived while the parent is not. This rule belongs in the tagging layer, as part of #778's read-path filter (a tag counts as archived when it, any ancestor, or its taxonomy is archived), and #733 reuses it, following the #817 precedent. Not yet confirmed whether #778 already covers ancestors.
- Archived and disabled records are excluded: archived groups and criteria; criteria whose ObjectTag, tag or taxonomy is archived; and disabled taxonomies. This matches #681's default, #778, and `openedx_tagging/rules.py`.
- Deleted, unpublished and hidden subsections: #733 returns the stored criteria as they are, the same for every learner, and does not filter by what the learner can see. The Student Progress page will eventually tell the learner that a subsection they can't see yet still counts toward their progress, so the frontend needs those criteria. #734 decides how to display a criterion whose `object_id` doesn't match a subsection in the Outline API's list.
- No new ADR. Record the learner-facing API pattern in #733's Technical Details, and have #738, #742, #745 and #753 reference #733.
- Defaults recorded without a question: no response caching in this ticket. The root group's own fields are returned, and what the root's `logic_operator` means for display, when other courses also feed the root, is left to #731 and #732. Course final-grade criteria are not in MVP (#665 lists them as out of scope).
- Implementer-owned: the URL form (course key in the path or as a query parameter), and the deterministic order of array elements.

### Decisions from the draft pass (BA)

- Prune fully: every returned taxonomy, competency, and group leads to at least one criterion, and a course whose criteria are all excluded returns empty.
- A criterion assigned an archived rule profile is returned with that profile's rule.
- Criteria for a competency taxonomy no longer assigned to the course's organization are excluded (openedx-platform side).
- #665 now assigns the system default profile when no rule fields are given, so a criterion always has a profile or overrides.
- #778 (open) doesn't cover archived ancestor tags. #613, #716, #776 are open and unmerged.
