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

## Notes for drafting

### Decisions from the pre-handoff check

- Whose statuses: full parity with today's Progress tab. The learner sees their own statuses, course staff (and CCX coaches) see a specific learner's statuses on the "view this learner's progress" page, and staff masquerading as a specific learner see that learner's statuses.
- Where the effective-learner decision lives: the openedx-core view takes an optional learner id and asks a resolver named in the `OPENEDX_LEARNING` settings who the learner is. The default resolver allows only the requester. The LMS points the setting at a function extracted from `ProgressTabView._get_student_user`, which both views then share. Give the resolver a generic name so #742, #745, and #753 can reuse it.
- Ticketing: one ticket with two PRs, one in openedx-core and one in openedx-platform, the same shape as #733.
- Parent competencies: return statuses for ancestor tags (which #643 writes), keyed by tag id. This needs #733's tag lineage to carry ancestor tag ids, which is a change to #733 itself, not part of #738.
- Archived and disabled items: return statuses for exactly the set of items #733 returns. Statuses for archived criteria, groups, tags, or taxonomies, and for disabled taxonomies, are left out.
- A tag whose ancestor tag is archived is treated as archived too, so #733 leaves it out and #738 returns no status for it or for the archived ancestor.
- Competency-level status: return only the learner's overall, cross-course `StudentCompetencyStatus`. Course-run group statuses are out of scope and can be added later without breaking callers.
- CCX courses are out of scope for MVP.
- An item with no status row is left out of the response, and the frontend shows it as "Available". A malformed course key returns 400, and an unknown well-formed key returns an empty response, as in #733. A requester who isn't allowed to see another learner gets 404, matching `ProgressTabView`.
- Stored statuses are returned as they are, with no recomputation at read time. The brief lag from asynchronous roll-up (ADR 0004) is accepted.
- The per-subsection percentage score is out of scope for #738. When the plugin needs it, the plugin calls the existing Progress tab API (`/api/course_home/v1/progress/{course_key}`) itself, which returns `block_key` and `percent_graded` for each subsection.
- Group course scope follows #665's implementation in PR #847: only the course-level group's `course_id` points to the course run, and bottom-tier groups have a null `course_id` and are found through their parent. ADR 0002's amended Decision 2 says every group in a course subtree carries `course_id`, which conflicts with this.
- Each status is returned as the lookup row's status string, never its id.
- The response carries no learner identifier, so it can't undercut the Progress tab's option to hide a learner's username.
- Staff masquerading as a role or content group, rather than a specific learner, get their own statuses, the same as the Progress tab shows their own grades.
- If a masqueraded learner has since unenrolled, the masquerade is cleared and the endpoint returns the staff member's own statuses, the same as `ProgressTabView`.
