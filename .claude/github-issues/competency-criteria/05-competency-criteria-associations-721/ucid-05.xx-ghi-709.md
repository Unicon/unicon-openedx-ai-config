# [FE] Manage & Apply Competencies: delete a Competency Rule Group

GitHub: https://github.com/openedx/openedx-core/issues/709 (#709, OPEN)
Cached: 2026-09-25

## Use Case

As a course author who created a Competency Rule Group in error, or whose rule structure has changed, I want to delete a Competency Rule Group, whether it is an unbacked placeholder box or a real, persisted group with associations, so that the competency's rule structure reflects only the groups I actually intend to keep, without leaving stray boxes or reloading the page.

## Acceptance Criteria

Frontend ticket. Testable once \#671's groups render, \#672's active-group scheme exists, and \#675 exists.

```
Scenario: Delete an unbacked placeholder box
  Given a Competency Rule Group box exists but no subsection has been selected into it yet
  When I click that box's delete object
  Then the box is removed from the page immediately
  And no backend request is made

Scenario: Delete a persisted group
  Given a Competency Rule Group has been persisted to the backend, with or without associated subsections
  When I click that group's delete object
  Then the group and any associations it contains are deleted
  And the group no longer appears on the page

Scenario: Deleting the active group when other groups remain
  Given the active group has one or more other real, persisted sibling groups
  When I delete the active group
  Then one of the remaining sibling groups becomes the new active group automatically
  And subsequent subsection selections target that remaining group

Scenario: Deleting the last remaining group falls back to the placeholder
  Given the group I delete is the only remaining group for the competency
  When I delete it
  Then no real groups remain for the competency
  And a placeholder box is shown as the new implicit active target

Scenario: Backend rejects the delete request
  Given a delete request to the backend fails
  When I click delete on a persisted group
  Then the group remains visible on the page
  And an error is shown, following this feature's existing generic-error-handling pattern (#672's Technical Details → Logic)

Scenario: A course author without write access cannot delete a group
  Given I lack studio write access to the course the competency's groups belong to
  Then the delete object is not rendered
```
[Figma Link](https://www.figma.com/design/VhAdaucNQS49x0Afp9xPZw/Competency-Application?node-id=1919-58613&t=V5MSxdfsFJXzffTx-1)

<img width="3548" height="2574" alt="Image" src="https://github.com/user-attachments/assets/f2ffa80b-3ec4-4cce-b693-0cc8303a854b" />

## Description

This ticket adds a delete action to a Competency Rule Group box, covering both an unbacked placeholder box (a client-side-only removal) and a real, persisted group (which also removes whatever associations it contains).

**Current behavior**

\#671 renders a competency's Competency Rule Group box(es), with no way to delete one yet.

**Requested change**

This ticket builds and renders the delete/trash object on each group box, following the design, and wires it to the following behavior. Clicking it:

- If the box is the not-yet-backed placeholder (no `group_id` yet), it is removed from local render state only. No backend call is made, since nothing has been persisted.  
- If the box is a real, persisted group, it is deleted via \#675, which cascades its associations away in the same call.  
- If the deleted group was the active group (\#672's `activeGroupId`), the active target automatically becomes one of the remaining real groups (the first remaining in the list) if any remain, or the placeholder box if none do.  
- If the deleted group is the only remaining group for the competency, the page falls back to a placeholder box, exactly as \#671/\#672 already render for "no real groups yet." This ticket does not build new placeholder-rendering logic; it only triggers the existing conditional by shrinking the group list to zero.


<details>
<summary>Explicitly out of scope</summary>

- Removal-confirmation dialogs and in-use/learner-status warnings: Use Case 10\. This ticket performs a direct delete on click, per the same precedent the pre-split design used for this action.  
- Creating a group, nesting, and the AND/OR operator control: \#671.  
- Deleting a single association without deleting its group: 5.10d.  
- The exact backend request/response contract: \#675's own ticket.
</details>

<details>
<summary>Technical Details</summary>

### Data Structures

- `deleteCompetencyCriteriaGroup(groupId)` (`data/api.ts`): DELETE call to \#675's endpoint. Contract assumed to mirror \#665's URL shape (e.g. `DELETE .../competencies/<tag_id>/groups/<group_id>/`); the exact shape is \#675's own ticket to define, not this one's.  
- `useDeleteCompetencyCriteriaGroup` (`data/apiHooks.ts`): a React Query mutation hook mirroring \#672's `useCreateCompetencyCriterion` conventions (matching `useCreateTag`'s pattern); invalidates the GET (\#681) query on success so the group list refetches without the deleted group.

### Logic

- This ticket renders the delete/trash object itself (a Paragon icon button, following the design) on each `CriteriaGroupBox`; \#671 does not include it. The object is not rendered at all — not merely disabled — for a course author without studio write access to the course.  
- The delete object click handler branches on whether the box is the unbacked placeholder or a real group:  
  - Placeholder: remove it from local render state only.  
  - Real group: call `useDeleteCompetencyCriteriaGroup`; on success, the invalidated GET query drops the deleted group from the rendered list.  
- After a real-group deletion, if `userSelectedGroupId` pointed at the just-deleted group, clear it and set it to the first remaining real group's id if any remain, or leave it unset (falling through to \#672's derived-default formula, which resolves to the placeholder) if none do.  
- If deletion empties the group list entirely, the existing "zero real groups → show placeholder" conditional from \#671/\#672 renders the placeholder automatically; this ticket adds no new placeholder-rendering logic. 5.10d's emptied-group cascade reuses this exact path rather than reimplementing it.  
- On delete failure, leave the group visible and follow \#672's generic error-handling pattern.  
- No confirmation dialog: Use Case 10's job.

### Example Resolution Prompt

> Implement the frontend consumer of \#675 in `frontend-app-authoring`, extending \#671/\#672's `src/taxonomy/competency-management/criteria-groups/` directory (check whether \#671/\#672 already created `data/api.ts`/`data/apiHooks.ts` before adding new files). Add `deleteCompetencyCriteriaGroup` and `useDeleteCompetencyCriteriaGroup` per Technical Details → Data Structures. Build and render `CriteriaGroupBox.tsx`'s delete/trash object (a Paragon icon button following the design; not rendered at all for a user without studio write access), and wire it to branch on placeholder vs. real group per Technical Details → Logic, setting `userSelectedGroupId` to a remaining sibling if one exists, or clearing it to fall through to the placeholder if none do. Reuse the existing "zero real groups → placeholder" conditional from \#671/\#672 rather than adding new placeholder-rendering logic — 5.10d depends on this same path. No confirmation dialog (Use Case 10's job). Follow \#672's generic error-handling pattern on failure.

## Context

- Sibling create ticket for the same entity: \#671 — renders the group boxes this ticket adds a delete object to.  
- Companion ticket reusing this ticket's group-removal logic: 5.10d (no GitHub issue yet), which triggers this same deletion path when removing the last association in a group.  
- `activeGroupId` scheme and derived-default formula this ticket recomputes against: \#672 Technical Details → Data Structures.  
- No genuine "last item removed → parent reverts to a placeholder" precedent exists yet in `src/taxonomy/` (nothing comparable is built there today). The closest analogs in `frontend-app-authoring` are in `src/library-authoring/`: `LibraryContent.tsx`, `LibraryCollectionComponents.tsx`, and `CollectionDetails.tsx` each swap a list or stats view for a placeholder component once a derived count reaches zero — the same shape this ticket's "group list shrinks to zero → placeholder shows" behavior follows, via \#671/\#672's own existing empty-state conditional rather than a new component.

## Files to create and modify

**Modified files** (conditional: check whether \#671/\#672 already created these before adding new content)

| File | Nature of modification |
| :---- | :---- |
| `src/taxonomy/competency-management/criteria-groups/CriteriaGroupBox.tsx` (from \#671) | Add and render the delete/trash object (Paragon icon button, per the design; hidden without studio write access), with a click handler branching on placeholder vs. real group. |
| `src/taxonomy/competency-management/criteria-groups/CriteriaGroupTree.tsx` (from \#671) | Pass a delete callback down; recompute `activeGroupId` against the post-deletion group list. |
| `src/taxonomy/competency-management/data/api.ts` | Add `deleteCompetencyCriteriaGroup`. |
| `src/taxonomy/competency-management/data/apiHooks.ts` | Add `useDeleteCompetencyCriteriaGroup`. |

Frontend implementation in `frontend-app-authoring`. Parent design: \#648. Foundation this builds on: \#670 (page shell), \#671 (creates and renders the groups this ticket deletes). Siblings on the same page: \#672 (creates associations), 5.10d (deletes a single association — reuses this ticket's group-removal logic when the last association in a group is removed; no GitHub issue yet).

**Blocked by:** \#675 (backend delete-group endpoint, cascades associations); \#672 (the `activeGroupId` scheme this ticket recomputes after a deletion); \#681 (GET groups \+ criteria endpoint, needed to render the groups this ticket deletes).

</details>

