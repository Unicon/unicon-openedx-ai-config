# [FE] Explain archived competency rules in the Courses & Content panel

GitHub: none yet (to be created as a sub-issue of #723)
Cached: 2026-09-25

## User Story
As a course author, I need to know which courses' rules for a competency were archived, in order to understand why I can't add new Competency Criteria associations for that course.

## Description
This ticket updates the Courses & Content panel so that when a course's course-level group for the selected competency is archived, expanding that course shows a sentence explaining the situation instead of displaying the course's sections and gradeable subsections. This should work like the "This course has no gradeable subsections." text that already appears in an expanded course row. The list of archived courses comes from the `archived_course_keys` field that 10.22 adds to #681's response.

## Context
- 10.22 adds `archived_course_keys` to #681's response, listing the course runs whose course-level group for this competency is archived.

## Notes for drafting

- The gap: when learners already have progress in a course and the author deletes that course's section or its last Rule Group (#709), or removes its last association (#710), #674/#675 archive the course-level group instead of deleting it. After that, #717 rejects every new association for that course under this competency with a 400, and never creates a fresh course-level group in its place. There is no way to unarchive a course-level group. The competency's root group is not affected: #717 reactivates an archived root when new content arrives.
- Decision (2026-09-25): hide those courses up front instead of letting the author hit the rejection. In the Browse Courses panel (#670), a course whose course-level group is archived shows no sections or subsections, the same way a course with no gradeable subsections is shown today, plus a sentence saying that course's competency criteria have been archived. The Competency Criteria Associations panel (#672) doesn't render those courses at all.
- The frontend learns which courses are archived from 10.22, which adds an `archived_course_keys` field (course run keys) to #681's response. #681's existing lists exclude archived rows, so they can't provide this on their own.
- Blocked by 10.22 (the archived-course list), #670 (the Browse Courses panel and its no-gradeable-subsections state), and #672 (the associations panel). Related: #709 and #710 (the deletes that lead to this state), #674 and #675 (the archive), #717 (the rejection).

Decisions from the pre-handoff check
- What counts as an archived course? One whose course-level group for the selected competency is archived, as listed in 10.22's `archived_course_keys`. Archived criteria or Rule Groups under an active course-level group lock nothing and don't trigger the message. The lock is per competency and per course run.
- Where does the sentence appear? Only in an expanded course row in the Courses & Content panel, in place of the section and subsection outline, the same place "This course has no gradeable subsections." renders today (frontend-app-authoring `course-search/messages.ts`, in #670's code). The course stays expandable. The outline isn't fetched for an archived course.
- What does the sentence say? Starting copy: "This course's rules for this competency were archived, so no new competency criteria associations can be added. Other runs of this course are unaffected. Learners' recorded progress is kept."
- Is there a Figma frame? No. Add the UX Design placeholder tagging @illiphilli for the archived state and its copy.
- What shows while #681 is loading or has failed? The normal outline, matching #797's behavior while its data is unknown. #717's rejection is the backstop.
- Which wins when a course is both archived and has #797's disabled (dominance-ineligible) content? The archived sentence, since it replaces the whole outline. It shows for every author, including those without write access to the course.
- Do archived courses count in "Showing N of M Courses"? Yes, they count as listed courses and add no associations. This is automatic.
- Is an archived course still findable by search? Yes. It shows the sentence when expanded. This is automatic.
- Does the Competency Criteria Associations panel (#672) need changes? No. #681 already leaves out archived groups, so an archived course never gets a section there. #672 is still a dependency because 10.23 reads `archived_course_keys` through its provider, the same way the panel reads `canEditCourse`.
- Does anything switch live after a delete? Yes. After a delete archives a course, the #681 refetch that #709, #710, and #833 already make returns the course in `archived_course_keys`, so its expanded outline switches to the sentence with no reload. This deserves an AC scenario.
