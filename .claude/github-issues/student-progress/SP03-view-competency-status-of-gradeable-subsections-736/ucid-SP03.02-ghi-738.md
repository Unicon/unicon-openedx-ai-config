# [BE] GET Competency Statuses for Learner in Course

GitHub: https://github.com/openedx/openedx-core/issues/738 (#738, OPEN)
Cached: 2026-09-21

## User Story
As a learner, I need to know what mastery level I demonstrated on each subsection as well as my overall mastery level for each competency assessed in the course in order to understand what I need to work on improving and how I can speak about my skills.

## Description
This ticket is for building a GET endpoint that fetches the Competency Status for all competency criteria and parent competencies in a given course for a given learner.

This endpoint should do the following logic:
1. Get all CompetencyCriteriaGroups where the course_id is the course run key for this course.
2. Get the StudentCompetencyStatus records where the user_id in the record is the user_id of the requesting student and oel_tagging_tag_id is one of the oel_tagging_tag_id values associated with this course's CompetencyCriteriaGroup. Include all of these records in the response payload.
3. Get all the CompetencyCriteriaGroups where parent_id is the course level CompetencyCriteriaGroup fetched in step 1.
4. Get all CompetencyCriteria for all of the fetched CompetencyCriteriaGroups for this course.
5. Get all StudentCompetencyCriteriaStatus records where the user_id in the record is the user_id of the requesting student and competency_criteria_id is one of the ids of the CompetencyCriteria fetched. Include all of these records in the response payload.
6. Get all CompetencyMasteryStatus records to include the status value in the response payload.

The response payload will then resemble something to the effect of the following:
```json
{
    "student_competency_statuses": [{"oel_tagging_tag_id": 1, "status": "Demonstrated"}],
    "student_competency_criteria_statuses": [{"competency_criteria_id": 2, "status": "AttemptedNotDemonstrated"}]
}
```

## Context

## Notes for drafting

### Decisions from the pre-handoff check

- Whose statuses: full parity with today's Progress tab. The learner sees their own statuses, course staff (and CCX coaches) see a specific learner's statuses on the "view this learner's progress" page, and staff masquerading as a specific learner see that learner's statuses.
- Where the effective-learner decision lives: the openedx-core view takes an optional learner id and asks a resolver named in the `OPENEDX_LEARNING` settings who the learner is. The default resolver allows only the requester. The LMS points the setting at a function extracted from `ProgressTabView._get_student_user`, which both views then share. Give the resolver a generic name so #742, #745, and #753 can reuse it.
- Ticketing: one ticket with two PRs, one in openedx-core and one in openedx-platform, the same shape as #733.
- Parent competencies: return statuses for ancestor tags (which #643 writes), keyed by tag id. This needs #733's tag lineage to carry ancestor tag ids, which is a change to #733 itself, not part of #738.
- Archived and disabled items: return statuses for exactly the set of items #733 returns. Statuses for archived criteria, groups, tags, or taxonomies, and for disabled taxonomies, are left out.
- Competency-level status: return only the learner's overall, cross-course `StudentCompetencyStatus`. Course-run group statuses are out of scope and can be added later without breaking callers.
- CCX courses are out of scope for MVP.
- An item with no status row is left out of the response, and the frontend shows it as "Available". A malformed course key returns 400, and an unknown well-formed key returns an empty response, as in #733. A requester who isn't allowed to see another learner gets 404, matching `ProgressTabView`.
- Stored statuses are returned as they are, with no recomputation at read time. The brief lag from asynchronous roll-up (ADR 0004) is accepted.
- The per-subsection percentage score is out of scope for #738. The existing Progress tab API already returns it.
- Each status is returned as the lookup row's status string, never its id.
- The response carries no learner identifier, so it can't undercut the Progress tab's option to hide a learner's username.
- Staff masquerading as a role or content group, rather than a specific learner, get their own statuses, the same as the Progress tab shows their own grades.
- If a masqueraded learner has since unenrolled, the masquerade is cleared and the endpoint returns the staff member's own statuses, the same as `ProgressTabView`.
