# [BE] GET Competency Criteria for Course

GitHub: https://github.com/openedx/openedx-core/issues/733 (#733, OPEN)
Cached: 2026-09-21

## User Story
As a learner, I need my course progress page to be able to render the competencies and criteria that the subsections in my course are testing so that I can understand my progress towards mastering them.

## Description

This ticket builds a GET endpoint that takes in a course run key as input and then fetches the corresponding Competency Criteria hierarchy.

For MVP, the Competency Criteria hierarchy consists of 3 levels:
- Root (Competency Tag Level)
    - Course Level
        - Bottom-tier Level
            - Competency Criterion (has subsection association)

Therefore, we will want to:
1. Fetch all the Course Level CompetencyCriteriaGroups.
2. Fetch all of the Course Level Groups' parents because these will be the Root Groups of the hiearchy to return.
3. Fetch all of the Course Level Group's child Course Level Groups (the Bottom-tier Level Groups for this course).
4. Fetch all of the CompetencyCriteria for these Bottom Tier Groups.
5. Create the response payload in accordance with the norms of the other endpoints. If the response is not in a shape like:
{
    CompetencyTaxonomyCompetencyCriteria: [
        {
            RootCompetencyCriteriaGroup: {}
            CourseLevelCompetencyCriteriaGroups: [
                {
                    BottomTierCompetencyCriteriaGroups: [
                        {
                            CompetencyCriteria: [
                                {}
                            ]
                        }
                    ]
                }
            ]
        }
    ]
}
Then a shape like that one needs to be able to be reconstructed from all of the flat arrays returned so that a recipient of this payload can understand for each taxonomy, what competency tag root groups are relevant to this course and then also share just this course's course level group and its children down to the CompetencyCriteria level.

Note that a course may content subsections associated with more than one Competency Taxonomy, so the response payload will need to be able to handle that.

The frontend will be expected to use the tag_id of each Root Level Group to find out what Taxonomies are included in this course and the objecttag_ids to find out what subsection names go with which competency tag names for display. The frontend will also need the competency_rule_profile_id, rule_type_override, and rule_payload_override fields to know what rule thresholds to display as well.

## Context

## Notes for drafting

### Decisions from the pre-handoff check

- LMS exposure: #733 adds a learner-only URL module under `/api/cbe/v1/` in openedx-core, and also makes the openedx-platform `lms/urls.py` change that mounts only that module, in the same ticket (two PRs). #665's authoring write routes stay off the LMS.
- Permission: openedx-core registers a named django-rules permission that allows any authenticated user by default. openedx-platform rebinds it to the Progress tab's own access check: an active enrollment, or course staff.
- Threshold: each criterion in the response carries its resolved effective rule (rule type and payload), taken from its overrides or else its assigned profile. The frontend never resolves a profile ID itself.
- Display data inline: the IDs, plus each criterion's `object_id` (subsection usage key), each group's `logic_operator`, `name` and `ordering`, each competency tag's `value` and `external_id`, and each taxonomy's ID and `name`. Subsection display names come from the Progress tab's own data, joined by usage key. That data carries `block_key` and `display_name`, confirmed in openedx-platform `course_home_api/progress/serializers.py`.
- Empty and unknown courses: a well-formed course key with no criteria, or with no catalog CourseRun row, returns 200 with empty arrays. A malformed key returns 400. #734 uses the empty 200 response as its check for whether to render, so the empty case must stay cheap.
- Tree depth: return each relevant root plus its complete course-scoped subtree at any depth, with criteria for every group in that subtree. Don't hard-code three levels, and don't wait on #731.
- Leaf `course_id`: treat #665's implementation as the database truth, meaning leaf groups have `course_id` null. Find the course-level groups by course, then walk down to their children. Neither #665 nor ADR 0002 is updated by this work.
- Tag lineage: out of scope for #733, and #733's endpoint is not changed later for it. A separate follow-up ticket adds an LMS endpoint that returns a taxonomy's tags, the same thing the Studio endpoint does today. That ticket still needs to be filed, and its GitHub number cited here.
- Archived and disabled records are excluded: archived groups and criteria; criteria whose ObjectTag, tag or taxonomy is archived; and disabled taxonomies. This matches #681's default, #778, and `openedx_tagging/rules.py`.
- Deleted, unpublished and hidden subsections: #733 returns the stored criteria as they are, the same for every learner. #734 drops any criterion whose `object_id` doesn't match a subsection in the Progress tab's list, which already leaves out subsections this learner can't see.
- No new ADR. Record the learner-facing API pattern in #733's Technical Details, and have #738, #742, #745 and #753 reference #733.
- Defaults recorded without a question: no response caching in this ticket. The root group's own fields are returned, and what the root's `logic_operator` means for display, when other courses also feed the root, is left to #731 and #732. Course final-grade criteria are not in MVP (#665 lists them as out of scope).
- Implementer-owned: the URL form (course key in the path or as a query parameter), and the deterministic order of array elements.
