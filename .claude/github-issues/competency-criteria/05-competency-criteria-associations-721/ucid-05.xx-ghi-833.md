# [FE] Delete a Competency Rule Box

GitHub: https://github.com/openedx/openedx-core/issues/833 (#833, OPEN)
Cached: 2026-10-14

## User Story
As a course author, I want to delete a whole Rule Box from a competency's rules in one action, in order to fix a mistake or remove rules I no longer want without removing each association one at a time.

## Description

This ticket implements the ⋮ menu on the rule boxes in the Competency Criteria Associations panel. When a user clicks on this the ⋮ menu, then all of the Competency Criteria Associations within the box should be deleted, and the box should no longer display on the screen.

If the deleted box was the one in focus, focus should move to the box directly above it in the same Rule Group, or to the box directly below it if there's nothing above. If that was the last box in the Rule Group, the Rule Group goes away too, and focus follows the same rule as deleting a Rule Group in #709.

In the event that deletion fails, the frontend should notify the user that some of the box's content couldn't be removed, and still display precisely what is stored on the backend.

## Context
- #709 deletes a whole Rule Group or Course Group
- #710 deletes a single Competency Criterion association
- #786 will add the confirmation dialog in front of this delete. This ticket deletes on click without the confirmation dialog in place.

## UX Design

[Figma Link](https://www.figma.com/design/VhAdaucNQS49x0Afp9xPZw/Competency-Application?node-id=3181-53604&t=j7kO8gbQYx04umfA-1)

<img width="3548" height="2574" alt="Image" src="https://github.com/user-attachments/assets/b1cd8eae-a711-4036-aa2f-1d1d162bf2bc" />

## Acceptance Criteria

```gherkin
Scenario: Deleting a saved rule box removes the box and everything in it
  Given a saved Rule Group holds two or more rule boxes
  And one of those rule boxes holds two or more subsections, whether or not learners have already been evaluated against any of them
  And none of those subsections is associated with this competency through any other rule box
  When I click that rule box's ⋮ menu
  Then, with no confirmation step, that rule box and all of its subsections are no longer shown
  And the Rule Group's other rule boxes are unchanged
  And those subsections are no longer marked as already associated in the content panel
  And nothing on the page says whether any of them was archived or deleted
  And after I reload the page, the rule box and its subsections are still not shown

Scenario: Content added at the same score after my panel loaded survives the delete
  Given my panel shows a rule box holding subsections A and B
  And since my panel loaded, subsection C was added to the same Rule Group at that rule box's score from another browser session
  When I click that rule box's ⋮ menu
  Then the panel shows that rule box holding only subsection C, with A and B no longer shown
  And if that rule box was in focus before, it is still in focus

Scenario Outline: Deleting a Rule Group's last rule box removes whatever it leaves empty
  Given a Rule Group holds exactly one rule box, which shows a ⋮ menu
  And <the rest of the panel>
  When I click that rule box's ⋮ menu
  Then <what the panel shows>

  Examples:
    | the rest of the panel | what the panel shows |
    | the same course section holds another Rule Group | that Rule Group is gone, and the course section still shows its other Rule Group |
    | its course section holds no other Rule Group, and another course section is shown | that whole course section is gone, and the other course section is unchanged |
    | no other Rule Group or course section is shown | no course section is shown, and the panel shows its empty-state message inviting a content selection, with no placeholder card |

Scenario Outline: Deleting the rule box in focus moves focus within its Rule Group
  Given a Rule Group holds three saved rule boxes, and the <position> rule box is in focus
  When I click the ⋮ menu on the rule box in focus
  Then the rule box that was <new focus> is in focus, and its Rule Group is still in focus
  And a subsection I select next is added to that rule box

  Examples:
    | position | new focus |
    | second   | first, directly above it |
    | first    | second, directly below it |

Scenario: Deleting the rule box in focus when its Rule Group goes away
  Given the rule box in focus is the only rule box in its Rule Group
  And another Rule Group is shown directly above that Rule Group
  When I click that rule box's ⋮ menu
  Then focus moves where it would after deleting that whole Rule Group in #709: here, the Rule Group directly above, together with its first rule box

Scenario: Deleting a Rule Group's last saved rule box also removes a placeholder rule box in that Rule Group
  Given a Rule Group holds one saved rule box and a placeholder rule box, and the placeholder rule box is in focus
  And another Rule Group is shown in the same course section
  When I click the saved rule box's ⋮ menu
  Then the Rule Group, including its placeholder rule box, is no longer shown
  And focus moves where it would after deleting that whole Rule Group in #709
  And the controls for adding a Rule Group or a rule box are available again

Scenario: Deleting a course section's last rule box also removes a placeholder Rule Group in that section
  Given a course section holds one saved Rule Group with one saved rule box, and a placeholder Rule Group I have added, which is in focus
  And another course section is shown
  When I click the saved rule box's ⋮ menu
  Then that course section, including the placeholder Rule Group, is no longer shown
  And focus moves where it would after deleting that course section in #709
  And the controls for adding a Rule Group or a rule box are available again

Scenario: Focus stays put when the deleted rule box was not in focus
  Given a saved rule box is in focus
  When I click the ⋮ menu on a different saved rule box, in the same Rule Group or in another one
  Then the same rule box and Rule Group are still in focus
  And a subsection I select next is added to the rule box in focus

Scenario: Deleting a placeholder rule box
  Given I have added a placeholder rule box to a saved Rule Group
  When I click the placeholder rule box's ⋮ menu
  Then the placeholder rule box is no longer shown, and nothing is sent to the server
  And the Rule Group's saved rule boxes are unchanged
  And the Rule Group's last saved rule box, directly above where the placeholder was, is in focus
  And the controls for adding a Rule Group or a rule box are available again

Scenario: A placeholder Rule Group's rule box has no ⋮ menu
  Given I have added a placeholder Rule Group
  When I view the placeholder rule box inside it
  Then that rule box shows no ⋮ menu

Scenario: A delete that fails partway stops and shows what is left
  Given a saved rule box holds three subsections
  And the system removes the first subsection it is asked to remove, then fails on the next
  When I click that rule box's ⋮ menu
  Then exactly one of the three subsections is removed, and the other two are still shown in that rule box
  And I am shown a message that some of the rule box's content could not be removed
  And the message does not say whether anything was archived or deleted
  And the panel shows the same content it shows after I reload the page
  And if that rule box was in focus before, it is still in focus

Scenario: A delete that fails before removing anything says nothing was removed
  Given a saved rule box holds three subsections
  And the system fails on the first subsection it is asked to remove
  When I click that rule box's ⋮ menu
  Then all three subsections are still shown in that rule box
  And I am shown a message that the rule box could not be removed, which differs from the message for a delete that failed partway
  And the panel shows the same content it shows after I reload the page

Scenario: Subsections another author already removed do not stop the delete
  Given a saved rule box holds three subsections
  And another author has removed one of them since my panel loaded
  When I click that rule box's ⋮ menu
  Then the rule box and all three subsections are no longer shown
  And no failure message is shown

Scenario: Clicking the ⋮ menu again after a failure removes the rest
  Given a failed delete left two subsections in a saved rule box
  When I click that rule box's ⋮ menu again, and nothing fails
  Then the remaining subsections and the rule box are no longer shown
  And no failure message is shown for this attempt

Scenario: A delete in progress cannot be started a second time
  Given I have clicked a saved rule box's ⋮ menu and its deletion has not finished
  When I click that ⋮ menu again, or any other ⋮ menu on the panel
  Then every ⋮ menu on the panel is disabled until the deletion finishes, and no second deletion starts
  And no failure message is shown when the first deletion finishes

Scenario: Subsections cannot be selected while a delete is in progress
  Given I have clicked a saved rule box's ⋮ menu and its deletion has not finished
  When I look at the content panel
  Then every subsection's select control is disabled until the deletion finishes

Scenario: The ⋮ menu is hidden on a course I cannot edit
  Given the panel shows a course section for a course I can see but do not have studio write access to
  And it shows a course section for a course I can edit
  When I view the associations panel
  Then no rule box in the first course section shows a ⋮ menu, not even a disabled one
  And every saved rule box in the second course section shows one

Scenario: The ⋮ menu works from the keyboard and says which rule box it deletes
  Given a Rule Group shows two saved rule boxes
  When I reach each rule box's ⋮ menu using only the keyboard
  Then a screen reader announces each one as a button, with names that tell the two rule boxes apart
  And pressing Enter or Space on one deletes that rule box, the same as clicking it
  And after the deletion finishes, whether or not it succeeded, keyboard focus moves to the rule box or Rule Group that is now in focus, or to the panel's empty-state message when nothing is left
```

<details>
<summary>Technical Details</summary>

This is a suggested approach, not the source of truth. The User Story, Description, and Acceptance Criteria define what must be true when the work is done.

**Summary**

A rule box has no database row, so deleting one calls #674 once for each criterion the author saw in the box, strictly one request at a time. The whole run is one React Query mutation that refreshes the panel once when it ends, on success or failure, and then writes focus once against the refreshed data. Deleting a placeholder rule box only moves focus and sends nothing to the server.

**Approach**

1. Add `deleteCompetencyCriterion(groupId, criterionId)` to `data/api.ts`, calling #674's `DELETE /api/cbe/v1/criteria-groups/<group_id>/criteria/<criterion_id>/`. #710 needs the same function, so whichever ticket lands first adds it. Do not loop over #710's `useDeleteCompetencyCriterion`, which refreshes the panel after every request.
2. Add `useDeleteRuleBox(tagId)` to `data/apiHooks.ts`: a `useMutation` with a `mutationKey`, taking `{ groupId, ruleKey, criterionIds }`.
   - `mutationFn` awaits one request at a time in a `for` loop. Parallel requests are unsafe: #674 removes a Rule Group only when a request finds it empty, and two concurrent requests each still see the other's criterion, so neither removes the group and an empty group stays stored.
   - Count a 404 as a success: #674 returns 404 for a criterion that is already gone, for example because another author removed it. On the first other rejected request, stop and throw an error that records how many requests succeeded before it.
   - `onSettled` returns the `invalidateQueries` promise for the #681 groups query, so the mutation stays pending until the refetch lands. Otherwise the stale box briefly shows an enabled ⋮ menu whose next click re-sends ids that are already gone.
3. Add `deleteRuleBox(groupId, ruleKey)` to `CompetencyAssociationsContext.tsx`. When it is called, snapshot the box's criterion ids from `ruleBoxesForGroup(groupId)`, the rule keys of the boxes directly above and below it, and the Rule Group order across course sections that #709's rule reads. Only the snapshotted ids are sent, which is why content added at that score after the panel loaded survives. Return early if any delete on the panel is pending. #786 puts its confirmation in front of this call.
4. Expose `isAnyDeletePending` from the provider, true while any rule box delete or #709's group delete is pending. Read the rule box side through `useMutationState` on that `mutationKey` (prior art: `src/course-outline/data/outlineStatusHooks.ts`). The pending state lives in the provider because collapsing a course section unmounts its rule boxes. The content panel's select control from #670 is disabled while it is true, so a subsection can't be added to a box that is being deleted. If #709 already disables it on `isDeletingGroup`, switch that condition to `isAnyDeletePending`.
5. When the mutation fails, choose the message from the success count: one or more successes means the partial-failure message, and zero means the nothing-removed message. Show it with `showToast`.
6. Then write focus once, as a functional update on the focus that is current at that moment, since the author may have clicked elsewhere during the delete. Read the refreshed data from `queryClient.getQueryData` through the `utils.ts` helpers, because the provider's `ruleBoxesForGroup` still reflects the pre-refresh render. With `G` as the deleted box's Rule Group and `S` as its course section:
   - If `G` is gone and focus was in `G` (on the deleted box, or on #671's placeholder rule box), or focus is #671's placeholder Rule Group under `S` and `S` is gone, apply #709's group-level rule from the snapshot.
   - Otherwise, if focus is on the deleted box's rule key and that key is gone from `G`, move to the snapshotted box above, else the one below, else `lastRealRuleKeyIn(G)`.
   - Otherwise leave focus alone. This covers a partial failure, and a box that survives holding newly added content.

   Whichever of #709, #710, and #833 lands first builds the shared helper with only its own cases. #833's cases include the full group-level rule, because the cascade can remove a Rule Group, its course section, or everything.
7. After every delete, move keyboard focus to the element for the resulting focus target, or to the empty-state message. The ⋮ menu button was disabled or removed, so the browser has already dropped keyboard focus to the page body. #672's `RuleBox` and `CriteriaGroupBox` already hold refs for scroll-into-view; add `tabIndex={-1}` where an element is not natively focusable.
8. In `RuleBox.tsx`, render a ⋮ IconButton (Inline size, more_vert) that opens a menu with Remove rule when `canEditCourse(courseId)` is true, disabled while `isAnyDeletePending` is true, so two post-delete focus writes never race, the same rule #709 applies to its group deletes, with an accessible name built from the box's score label, which is unique within a Rule Group. Stop propagation of its click and key events: `RuleBox` and `CriteriaGroupBox` focus themselves on click, so a bubbled click would put the box being deleted in focus first.
9. A placeholder rule box's ⋮ menu writes `{ groupId, ruleKey: lastRealRuleKeyIn(groupId) }` directly and sends nothing. Write it directly, not through `focusGroup`, because #672 makes re-focusing the group already in focus a no-op. The placeholder rule box inside a placeholder Rule Group (`focus.groupId === null`) renders no ⋮ menu.

Out of scope:

- The confirmation dialog (#786).
- Deleting a Rule Group or course section (#709).
- Removing a single association (#710).

**Files to create and modify**

Every path is under `src/taxonomy/competency-management/` and is provisional. `messages.ts` exists on `master`; #672 and #671 create the other files.

| File | Change |
| --- | --- |
| `data/api.ts` | modified: `deleteCompetencyCriterion`, unless #710 added it |
| `data/apiHooks.ts` | modified: `useDeleteRuleBox` |
| `CompetencyAssociationsContext.tsx` | modified: `deleteRuleBox`, `isAnyDeletePending`, and the post-delete focus write |
| `utils.ts` | modified: the shared post-delete focus helper, or #833's cases added to it if #709 or #710 built it |
| `criteria-groups/RuleBox.tsx` | modified: the ⋮ menu |
| `messages.ts` | modified: the ⋮ menus's accessible name and the two failure messages |
| the content panel component from #670 | modified: disable the subsection select control while `isAnyDeletePending` is true |

**Additional context**

- #672 defines `ruleBoxesForGroup`, `lastRealRuleKeyIn`, the focus pair, and `canEditCourse`. #671 defines a placeholder as an unset part of that focus pair.
- #674 defines the endpoint's cascade and its 404 for a criterion that is already gone. #681 is the GET the refresh reads, and it omits archived rows, which is why archived and deleted content look the same.

</details>
