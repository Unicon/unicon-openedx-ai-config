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
- #786 will add the confirmation dialog in front of this delete. This ticket deletes on click without the confirmation dialog in place.

## UX Design

@illiphilli, please add the UX design screenshot(s) and the Figma link for this ticket.

- Figma: TBD
- Screenshots: TBD

## Acceptance Criteria

```gherkin
Scenario: Deleting a saved Rule Group removes it and its content, with no confirmation
  Given a Course Group holds three saved Rule Groups
  When I click the trash can icon on the second Rule Group
  Then no confirmation is shown
  And the Rule Group stays on the page until the server confirms the deletion, and then it disappears along with every rule box and subsection in it
  And the other two Rule Groups and their contents are unchanged
  And the subsections that were in the deleted Rule Group are no longer marked as already associated in the content panel
  And the deleted Rule Group is still gone after I reload the page

Scenario: Deleting a Course Group removes that course's whole section, with no confirmation
  Given Course Groups for two courses are shown, and one of them holds more than one saved Rule Group
  When I click the trash can icon on that Course Group
  Then no confirmation is shown
  And once the server confirms the deletion, that Course Group disappears along with every Rule Group, rule box, and subsection in it
  And the other Course Group and its contents are unchanged
  And the deleted Course Group is still gone after I reload the page

Scenario: A Rule Group the server archives rather than removes disappears like any other
  Given a Course Group holds two saved Rule Groups, and a learner already has recorded progress on a subsection in one of them
  When I delete that Rule Group
  Then it disappears from the page, the same as a Rule Group no learner has progress in
  And nothing on the page tells me whether it was removed or archived
  And the Course Group's other Rule Group is unchanged

Scenario: Deleting an unsaved empty Rule Group removes it without contacting the server
  Given I added an empty Rule Group to a Course Group with "+ Rule Group" and have put no content in it
  And the saved Rule Group directly above it holds more than one rule box
  When I click the trash can icon on the empty Rule Group
  Then it disappears immediately, with no confirmation shown and nothing sent to the server
  And the saved Rule Group directly above it is in focus, together with the first rule box in it
  And no empty Rule Group or empty rule box is left on the page, and the controls to add a Rule Group or a rule box are available again

Scenario: Deleting the Rule Group in focus moves focus to the Rule Group directly above it
  Given a Course Group holds four saved Rule Groups, and the second one holds more than one rule box
  And the third Rule Group is in focus
  When I delete the third Rule Group
  Then the second Rule Group is in focus, together with the first rule box in it
  And a gradable subsection I select afterward from that course is added to that first rule box

Scenario: Deleting the top Rule Group in focus moves focus to the one directly below it, in the same Course Group
  Given two Course Groups are shown, one above the other
  And the lower Course Group holds three saved Rule Groups, its second Rule Group holds more than one rule box, and its first Rule Group is in focus
  When I delete that first Rule Group
  Then the Rule Group that was second in the lower Course Group is in focus, together with the first rule box in it
  And no Rule Group in the upper Course Group is in focus

Scenario Outline: When the Course Group holding focus disappears, focus moves to the nearest Rule Group above it, which is the last Rule Group of the Course Group above
  Given two expanded Course Groups are shown, one above the other
  And the upper Course Group holds more than one saved Rule Group, and its last Rule Group holds more than one rule box
  And in the lower Course Group, <what is in focus>
  When I <delete what>
  Then the lower Course Group is no longer shown
  And the last Rule Group of the upper Course Group is in focus, together with the first rule box in it, and it is visible without further scrolling

  Examples:
    | what is in focus                                                                             | delete what                      |
    | one of several saved Rule Groups is in focus                                                 | delete the lower Course Group    |
    | its only saved Rule Group is in focus                                                        | delete that Rule Group           |
    | an unsaved empty Rule Group is in focus                                                      | delete the lower Course Group    |
    | an unsaved empty Rule Group is in focus, and there is exactly one saved Rule Group beside it | delete that one saved Rule Group |

Scenario: Focus that moves into a collapsed Course Group expands it
  Given two Course Groups are shown, one above the other, and the upper one is collapsed
  And a Rule Group in the lower Course Group is in focus
  When I delete the lower Course Group
  Then the upper Course Group is expanded
  And its last Rule Group is in focus, together with the first rule box in it, and it is visible without further scrolling

Scenario: When the top Course Group holding focus disappears, focus moves to the first Rule Group of the Course Group below it
  Given two Course Groups are shown, one above the other
  And the lower Course Group holds more than one saved Rule Group, and its first Rule Group holds more than one rule box
  And a Rule Group in the upper Course Group is in focus
  When I delete the upper Course Group
  Then the first Rule Group of the lower Course Group is in focus, together with the first rule box in it

Scenario Outline: Deleting the last group on the page leaves the panel's empty state
  Given the associations panel shows one Course Group, and it holds one saved Rule Group, and no learner has recorded progress in any of its subsections
  When I delete <target>
  Then the panel shows the same empty-state message as a competency with no associations, with no Course Group, Rule Group, or rule box shown
  And nothing is left in focus, so a gradable subsection I select afterward is added under a new Course Group for its course, with no error

  Examples:
    | target              |
    | the Course Group    |
    | its only Rule Group |

Scenario: Deleting the last group I can see moves focus to a Course Group another author added meanwhile
  Given the associations panel shows one Course Group, and it holds one saved Rule Group, which is in focus
  And another author has added an association in a different course since my page loaded
  When I delete that Course Group
  Then the panel is refreshed from the server and shows the other author's Course Group
  And the first Rule Group of that Course Group is in focus, together with the first rule box in it
  And no unsaved Rule Group is shown, and the controls to add a Rule Group or a rule box are available

Scenario Outline: Deleting a group that does not hold focus leaves focus where it is
  Given two Course Groups are shown, each holding more than one saved Rule Group
  And in the upper Course Group, a Rule Group with more than one rule box is in focus, together with a rule box in it other than its first
  When I click the trash can icon on <target>
  Then the same Rule Group and the same rule box are still in focus

  Examples:
    | target                                           |
    | a different Rule Group in the upper Course Group |
    | the lower Course Group                           |

Scenario Outline: A failed deletion shows an error and refreshes the panel to match the server
  Given a saved Rule Group is in focus
  And the server is unable to delete <target>
  When I click the trash can icon on <target>
  Then <target> is not removed from the page before the server responds
  And an error message is shown
  And the panel is refreshed from the server, and <target> is still shown, with the contents the server holds for it
  And focus stays on that Rule Group and its rule box

  Examples:
    | target                         |
    | that Rule Group                |
    | that Rule Group's Course Group |

Scenario Outline: Deleting a group another author already deleted counts as a successful deletion
  Given a saved Rule Group is in focus
  And another author has already deleted <target>
  When I click the trash can icon on <target>
  Then <target> disappears, and no error message is shown
  And focus moves as it would after a successful deletion

  Examples:
    | target                         |
    | that Rule Group                |
    | that Rule Group's Course Group |

Scenario: The trash can icon is offered only on courses I can edit
  Given Course Groups for two courses are shown, and I have studio write access to only one of those courses
  When I view the associations panel
  Then the Course Group for the course I can edit, and each Rule Group in it, shows a trash can icon
  And the Course Group for the course I cannot edit, and each Rule Group in it, shows no trash can icon, not even a disabled one

Scenario: Clicking again while a deletion is in progress does not delete twice
  Given I have clicked the trash can icon on a saved Rule Group or Course Group, and the server has not responded yet
  When I click that trash can icon again, or any other trash can icon on the panel
  Then every trash can icon on the panel is disabled until the server responds, and no second deletion is sent
  And once the server confirms the first deletion, the group disappears with no error shown

Scenario: Subsections cannot be selected while a deletion is in progress
  Given I have clicked the trash can icon on a saved Rule Group or Course Group, and the server has not responded yet
  When I look at the content panel
  Then every subsection's select control is disabled until the deletion finishes

Scenario Outline: Keyboard focus follows the new selection target after a delete
  Given I reach the trash can icon on <target> using only the keyboard
  When I press Enter on it and the deletion succeeds
  Then keyboard focus moves to <keyboard focus afterward>

  Examples:
    | target                                                      | keyboard focus afterward            |
    | a Rule Group, with another Rule Group left on the panel     | the Rule Group that is now in focus |
    | a Course Group, with another Course Group left on the panel | the Rule Group that is now in focus |
    | the only Rule Group on the panel                            | the panel's empty-state message     |
```

<details>
<summary>Technical Details</summary>

This is a suggested approach, not the source of truth. The User Story, Description, and Acceptance Criteria define what must be true when the work is done.

**Summary**

One provider action deletes a saved Course Group or Rule Group through #675 and refetches #681 whether the request succeeds or fails, so the page only ever shows what the server holds. A placeholder Rule Group is removed on the client alone. After the refetch lands, one pure helper resolves focus against the refreshed data and a snapshot of the page order taken when the request was sent, and #710 and #833 reuse that helper.

**Approach**

1. `deleteCompetencyCriteriaGroup(tagId, groupId)` in `data/api.ts` sends `DELETE /api/cbe/v1/competencies/<tag_id>/criteria-groups/<group_id>/` (#675). `useDeleteCompetencyCriteriaGroup(tagId)` in `data/apiHooks.ts` invalidates `competencyQueryKeys.competencyCriteriaGroups(tagId)` in `onSettled`, following `useDeleteTaxonomy` in `src/taxonomy/data/apiHooks.ts`, and additionally returns the `invalidateQueries` promise from `onSettled`. Returning the promise means the mutation settles, and `isPending` clears, only after the refetch has landed, on success and failure alike. Treat a success response as "gone" whether #675 hard-deleted or archived the group: #681 excludes archived rows, and the page never reads `archived` or the cascade counts.
2. Add a trash `IconButton` with Paragon's `Delete` icon to each `CriteriaGroupBox` card, saved and placeholder alike, and to each `CourseGroupSection` header.
   - Render it only when `canEditCourse(courseId)` is true.
   - The handler calls `e.stopPropagation()`. Without that, the click also reaches the card's own focus handler and puts that group in focus, and the delete then moves focus away from the group the author was working in.
   - While `isDeletingGroup` is true, every trash control on the panel, including the placeholder's, is disabled. That serializes deletes, so two focus resolutions never race. Also guard `deleteGroup` with a ref, since a double click can land before the disabled state renders.
   - The content panel's select control from #670 is also disabled while `isDeletingGroup` is true, so a subsection can't be added to a group that is being deleted.
3. In `CompetencyAssociationsContext.tsx`, add two actions:
   - `deleteGroup(groupId)` serves both levels, because #675 accepts a Course Group id and a Rule Group id alike. Just before sending, it snapshots the page order: the visible Course Group ids in render order, each with its Rule Group ids in #672's sibling order. After the mutation settles it calls `resolveFocusAfterRemoval(snapshot, groupId)`. On a failure it also calls `showToast`, except on a 404: #675 returns 404 for a group that is already gone, and the page treats that as a successful deletion.
   - `removePlaceholderGroup()` sends no request. It focuses the last saved Rule Group in the placeholder's Course Group (#672's `lastBottomTierGroupForCourse`) and that group's first rule box, which removes the placeholder per #671.
4. `resolveFocusAfterRemoval` applies a pure `focusTargetAfterRemoval(snapshot, fresh, focus)` in `utils.ts`. `fresh` is the refetched #681 payload, read with `queryClient.getQueryData`, not the tree the click handler closed over. Read `focus` and `placeholder` as they are when the request settles, so a group the author clicked during the request keeps focus if it still exists. The helper checks these rules in order:
   - If the Rule Group in focus still exists in `fresh`, focus is unchanged. For a placeholder Rule Group, check its Course Group instead. This rule covers deleting a group that did not hold focus, and a delete the server refused.
   - Otherwise, if that Rule Group's Course Group still exists, focus the nearest surviving Rule Group above it in the snapshot, or failing that, the nearest one below.
   - Otherwise, focus the last Rule Group of the nearest surviving Course Group above it in the snapshot, or failing that, the first Rule Group of the nearest one below.
   - Otherwise, if `fresh` still shows a Course Group, which happens when another author added one during the delete, focus the first Rule Group of the first visible Course Group in `fresh`, in #672's order.
   - Otherwise, unset both parts of focus. This is the only place that writes the unset pair, and it runs only when no Course Group is left. #671 stores no separate placeholder flag: it treats "the Rule Group in focus is unset while at least one Course Group is shown" as "an unsaved Rule Group exists". Unsetting focus while a Course Group is still shown would make the page behave as if an unsaved Rule Group were there.

   The chosen Rule Group gets its first rule box from `fresh`, not #672's last-rule-box default. Candidates come from the snapshot, so they are already known to be visible, except in the rule for a Course Group another author added, which takes its candidate from #672's visible Course Groups in `fresh`. Collapse state plays no part in the choice. Because the target is resolved against refreshed data, #675's upward cascade, a 404 for a group already deleted elsewhere, and a concurrent edit all take this same path. In the cascade case, a Rule Group's removal takes its Course Group, and any placeholder in it, with it.
5. Set a one-shot keyboard focus request whenever the deleted group is gone. That is always true for the placeholder, and true for a saved group when it is absent from `fresh`.
   - The `CriteriaGroupBox` now in focus takes the request by calling `focus({ preventScroll: true })`. `preventScroll` keeps this call from fighting #672's `scrollIntoView` on the rule box.
   - If that card's Course Group is collapsed, `CourseGroupSection` expands it first. Its `isCollapsed` is #672's local component state, so the section sets it itself when the request names one of its cards.
   - When nothing is left, `CourseGroupList` focuses the empty-state message, which needs `tabIndex={-1}`.

   Keep the request in the provider, not in a card. #672's panel shows its loading spinner while the refetch's name lookup loads, which unmounts every card and resets every Course Group to expanded, so the request must outlive that unmount and be taken once the cards render again. Clear the request once it is taken, and on the next focus write, so a section the author expands later can't steal focus. When a failed delete leaves the group on the page, DOM focus stays on its trash button.

Out of scope:

- The confirmation dialog (#786), which goes between the trash handler and `deleteGroup`.
- Deleting a rule box or a placeholder rule box (#833).
- Deleting an association (#710).
- Explaining archived courses in the Courses & Content panel (#841).

#710 and #833 call `resolveFocusAfterRemoval` with their own cases. If either of them lands first, extend its helper rather than adding a second one.

**Files to create and modify**

| File | Change |
| --- | --- |
| `src/taxonomy/competency-management/data/api.ts` (provisional) | modified: add `deleteCompetencyCriteriaGroup` |
| `src/taxonomy/competency-management/data/apiHooks.ts` (provisional) | modified: add `useDeleteCompetencyCriteriaGroup` |
| `src/taxonomy/competency-management/CompetencyAssociationsContext.tsx` (provisional) | modified: add `deleteGroup`, `removePlaceholderGroup`, `resolveFocusAfterRemoval`, `isDeletingGroup`, and the keyboard focus request |
| `src/taxonomy/competency-management/utils.ts` (provisional) | modified: add `focusTargetAfterRemoval` and the page-order snapshot |
| `src/taxonomy/competency-management/criteria-groups/CriteriaGroupBox.tsx` (provisional) | modified: add the Rule Group trash control and make the card a keyboard focus target |
| `src/taxonomy/competency-management/criteria-groups/CourseGroupSection.tsx` (provisional) | modified: add the Course Group trash control, and expand the section when the keyboard focus request names one of its cards |
| `src/taxonomy/competency-management/criteria-groups/CourseGroupList.tsx` (provisional) | modified: make the empty-state message focusable |
| `src/taxonomy/competency-management/messages.ts` | modified: add the trash control labels and the delete error |
| the content panel component from #670 (provisional) | modified: disable the subsection select control while `isDeletingGroup` is true |

**Additional context**

- A Course Group is #672's course-level group, rendered by `CourseGroupSection`. A Rule Group is #672's bottom-tier group, rendered by `CriteriaGroupBox`.
- This ticket extends work from three other tickets. #672 builds the provider, the focus pair, `canEditCourse`, the ordering and rule-box helpers, and the empty state. #671 builds the placeholder Rule Group. #681 is the GET that the refetch reads. Paths marked provisional are created by #672 and #671 and are not on `frontend-app-authoring` master yet.
- `src/taxonomy/taxonomy-card/TaxonomyCard.tsx` is prior art for stopping propagation on a control inside a clickable card.

</details>
