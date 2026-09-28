# [FE] Delete a Competency Rule Box

GitHub: https://github.com/openedx/openedx-core/issues/833 (#833, OPEN)
Cached: 2026-09-25

## User Story
As a course author, I want to delete a whole Rule Box from a competency's rules in one action, in order to fix a mistake or remove rules I no longer want without removing each association one at a time.

## Description

This ticket implements the trash can icon on the rule boxes in the Competency Criteria Associations panel. When a user clicks on this trash can icon, then all of the Competency Criteria Associations within the box should be deleted, and the box should no longer display on the screen.

If the deleted box was the one in focus, focus should move to the box directly above it in the same Rule Group, or to the box directly below it if there's nothing above. If that was the last box in the Rule Group, the Rule Group goes away too, and focus follows the same rule as deleting a Rule Group in #709.

In the event that deletion fails, the frontend should notify the user that some of the box's content couldn't be removed, and still display precisely what is stored on the backend.

## Context
- #709 deletes a whole Rule Group or Course Group
- #710 deletes a single Competency Criterion association
- #786 adds the confirmation dialog in front of this delete. This ticket deletes on click.

## Notes for drafting

Decisions from the pre-handoff check
- What is a rule box? It has no database row. It is the set of criteria in one Rule Group (bottom-tier group) that share the same score, derived on the frontend by #672's `ruleBoxesForGroup`. "Rule Group" in this ticket means the bottom-tier group, as in #709.
- How is a rule box deleted? Loop #674 once per criterion, one request at a time, never in parallel. Parallel requests can each still see the other's criterion, so neither removes the emptied group, which leaves an empty group stored. Sequential requests are safe because the group can only disappear on the final request, and every intermediate state is a valid, smaller box. No new backend ticket for MVP. Rule boxes are expected to hold no more than a handful of subsections; revisit a bulk-delete endpoint (shaped like #759) only if partial failures show up in practice. Switching later changes one frontend function.
- Which criteria does the delete remove? Only the ones the author saw at the moment of the click. Anything another author added to that score in the meantime survives and appears after the refresh.
- What happens on a partial failure? Stop at the first failure, refresh the panel, and show a specific message saying some of the box's content could not be removed. Clicking the trash again retries the rest. The message never reveals whether anything was archived or deleted.
- Can archive and delete differ within one box? Yes. #674 decides per criterion, and the author is not told either way (#786). #681 hides archived rows, so both look the same.
- What happens when the deleted box was its Rule Group's last box? #674's cascade removes the Rule Group, possibly the course section, and possibly everything down to #672's empty state. The archived course-level group gap accepted for #709 applies here too.
- Where does focus go when the deleted rule box held focus and its Rule Group survives? To the rule box directly above it in the same Rule Group, or the one directly below it if there is none above (in #672's display order). This differs from #672's default of focusing a group's last rule box, which still applies when the author clicks a group. When the Rule Group itself is gone, use the shared group-level rule from #709. Focus is unchanged when the deleted box did not hold it. Whichever of #709, #710, and #833 is implemented first builds the shared helper, including this rule-box case; the others reuse it.
- Do placeholders get a trash control? A placeholder rule box does, and deleting it is client-side only with no confirmation. A placeholder rule box inside a placeholder Rule Group has its trash hidden. (Decided 2026-09-25.)
- Does a rule box that is the only box in its Rule Group keep its trash? Yes. Deleting it has the same result as deleting the Rule Group.
- Who owns the confirmation dialog? #786, amended to add the rule box trash as a fourth entry point. As approved on 2026-09-21, #786 says no rule box delete control exists, and no other ticket covers it. #833 deletes on click.
- Without studio write access to a course, is the trash hidden or disabled? Hidden, via #672's `canEditCourse`.
