# [FE] Delete Competency Course & Rule Groups

GitHub: https://github.com/openedx/openedx-core/issues/709 (#709, OPEN)
Cached: 2026-09-25

## User Story
As a course author, I want to delete a whole Rule Group or a whole Course Group from a competency's rules in one action, in order to fix a mistake or delete/archive rules I no longer want without removing each association one at a time.

## Description

This ticket implements the functionality for the trash can icon for both Course Groups and Rule Groups. When the user clicks on the trash can icon, the frontend should call the backend endpoint that deletes CompetencyCriteriaGroups with the id of the group that should be deleted. Upon a successful deletion, the frontend should update to accurately display only the remaining groups. Upon an unsuccessful deletion, the frontend should report to the user that an error occurred.

After a delete, focus moves to the Rule Group directly above the deleted one, or to the one directly below it if there's nothing above. If a deletion fails, the frontend shows an error and refreshes the panel so it matches the backend. The trash can icon is hidden on courses the user can't edit.

## Context
- #675 is the backend delete endpoint.
- #786 adds the confirmation dialog in front of this delete. This ticket deletes on click.

## Notes for drafting

Decisions from the pre-handoff check
- What does "Course Groups" mean? The course section (the course-level group, one per course). Deleting it removes every Rule Group and rule for that course under this competency. "Rule Group" means a bottom-tier group.
- Do unsaved placeholders get a trash control? Yes. Deleting a placeholder Rule Group is a client-side removal with no backend call. (Decided 2026-09-25.)
- What happens when the last group on the page is deleted? No placeholder appears; the page shows #672's empty-state message, consistent with the 2026-09-21 comment on #710.
- Where does focus go after a delete removes the focused group, the placeholder, or the placeholder's course section? To the Rule Group directly above the deleted one on the page, or the one directly below it if there is none above, and that Rule Group's first rule box. This differs from #672's default of focusing a group's last rule box, which still applies when the author clicks a group. When a whole course section is gone, the same above-then-below rule applies across course sections: the last Rule Group of the section above, else the first Rule Group of the section below. Unset only when nothing remains. Focus is unchanged when the deleted group did not hold it.
- Who owns that post-delete focus rule? Whichever of #709, #710, and #833 is implemented first builds the shared helper and provider function; the others reuse it. #710 may land before #709.
- How is the archived course-level group gap handled? Accepted for MVP, with no unarchiving of course-level groups. Once #675 archives a course-level group, #717 rejects any new content for that course under this competency. 10.22 (backend) reports which courses have an archived course-level group, and 10.23 (frontend) hides those courses' sections in the Browse Courses panel with a sentence saying their competency criteria were archived. #717 reactivates an archived root, so the whole competency is never locked. Neither is part of #709.
- Who owns the confirmation dialog? #786. #709 deletes on click.
- Does deleting an unsaved placeholder show a confirmation? No.
- Without studio write access to a course, is the trash hidden or disabled? Hidden, via #672's `canEditCourse`.
- What happens on a failed delete, including a 404 for a group already deleted elsewhere? Show the error and refetch the panel so it matches the server. The group is never removed from the page before the server confirms.
