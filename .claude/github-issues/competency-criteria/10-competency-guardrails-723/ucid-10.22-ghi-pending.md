# [Placeholder] Change GET Competency Criteria Endpoint to Include Archived Records

GitHub: none yet (to be created as a sub-issue of #723)
Cached: 2026-09-25

## User Story
As a course author, I need to know when a course's competency rules have been archived in order to understand why I can't create more rules for this course.

## Description
This ticket will change the GET Competency Criteria Endpoint so that it now returns archived CompetencyCriteriaGroups in its response payload.

## Context

## Notes for drafting

- Why this ticket exists: when learners already have progress in a course and the author deletes that course's section, or its last Rule Group (#709), or its last association (#710), #674/#675 archive the course-level group instead of deleting it. After that, #717 rejects every new association for that course under this competency, and there is no way to unarchive a course-level group. The frontend needs to know which courses are in that state so it can hide them and explain why (10.23), instead of letting the author select content that will always be rejected.
- #681's GET returns only non-archived groups and criteria. That is an explicit AC ("Archived groups and criteria are excluded by default"), and it lists an audit option for archived rows as out of scope. #681 is already in code review, so this is a separate ticket rather than a change to #681.
- Proposed shape (2026-09-25): add a short list of the course ids whose course-level group for this competency is archived, instead of including archived rows themselves. The frontend never needs the archived rows, only which courses to hide, and leaving them out means the associations panel can't accidentally render one. Whether this is a new field on #681's response or its own small endpoint is the architect's call.
- A course can't have both an archived and an active course-level group for the same competency, because #665's unique constraint allows one course-level group per course per competency, archived or not. So "has an archived course-level group" means "can never get new criteria for this competency".
- The root group is different: #717 now reactivates an archived root when new content arrives, so an archived root is not reported and doesn't block anything.
- Blocked by #681 (the endpoint it extends, or sits next to) and the archived-field ticket (#716). Consumed by 10.23 (the frontend half).

Decisions from the pre-handoff check
- What shape does the archived information take? A new `archived_course_keys` field on #681's response, listing the course run keys whose course-level group for this competency is archived. #681's existing rows stay unchanged, so its "Archived groups and criteria are excluded by default" AC and #682's counts still hold, and the single #681 refetch that #709, #710, and #833 already make after a delete picks up a newly locked course with no extra work.
- What counts as a locked course? Exactly one whose course-level group for this competency is archived, which is #717's rejection condition. Archived Rule Groups or criteria under an active course-level group lock nothing and are not reported. An archived root is not reported either, since #717 reactivates it. The list covers only the selected competency's own groups, not its sub-competencies'.
- How is the list computed? As a flat filter on this competency's archived course-level groups, not by walking down from the root, so an archived root doesn't hide the archived courses beneath it.
- Does the list follow #682's `course_keys` filter? Yes, the same scope as the rows: unfiltered when the parameter is omitted, limited to the requested course runs when present. Whichever of #682 and 10.22 lands second implements it.
- Is it acceptable for the author to learn a course's rules were archived? Yes, as a narrow exception to #786's rule of not telling the author whether a removal deleted or archived, limited to the course-level lock because it is permanent and the author would hit it anyway. #655's 2026-08-25 product decision deferred showing delete impact to a future nice-to-have, rather than forbidding it.
- Is the list filtered by the caller's access to each course? No, same as #681, which already shows every course-level group's course key to anyone who can view the taxonomy.
- Does it include when a course was archived? No. It only reports whether a course's course-level group is archived, not the date it was archived.
- Which identifier? The course run key string, the same `course_key` #681 serializes. Never the internal course run id.
- How does QA set up an archived course-level group? That's QA's call; the ticket adds no test fixture or script. QA can grade a learner, delete the course's rules so they archive, then confirm the course appears in the list with Postman. The ACs state the starting data without prescribing how it's produced.
- #681 is in code review, but its PR wasn't found in openedx-core's open PRs on 2026-09-25. Confirm the actual response shape against whatever merges.
