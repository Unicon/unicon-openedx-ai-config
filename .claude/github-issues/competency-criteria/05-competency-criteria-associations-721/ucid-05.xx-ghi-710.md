# [FE] Manage & Apply Competencies: delete a Competency Criteria Association

GitHub: https://github.com/openedx/openedx-core/issues/710 (#710, OPEN)
Cached: 2026-10-22

## Use Case

As a course author who associated the wrong gradeable subsection with a Competency Rule Group, or no longer wants a subsection counted toward a competency, I want to remove a single association from a Competency Rule Group box's Selected Content list, so that I can correct the rule's content without deleting or recreating the whole box.

## Acceptance Criteria

Frontend ticket. Testable once \#672's Selected Content list and \#670's Browse Courses panel chip exist, \#674 exists, and #709's group-removal rendering logic exists.

```
Scenario: Remove an association via its Competency Rule Group box item
  Given a gradeable subsection is associated with a Competency Rule Group box, among other associations in the same box
  When I click the remove ("X") affordance on that association's item in the box's Selected Content list
  Then that association is removed
  And the item no longer appears in the box's Selected Content list
  And the subsection's chip in the Browse Courses panel no longer shows it as already-associated, and it is selectable again
  And the box's other associations remain unchanged

Scenario: Remove an association via its Browse Courses panel chip
  Given a gradeable subsection is associated with a Competency Rule Group box, among other associations in the same box
  When I click the remove ("X") affordance on that subsection's already-associated chip in the Browse Courses panel
  Then that association is removed
  And the subsection's chip in the Browse Courses panel no longer shows it as already-associated, and it is selectable again
  And the item no longer appears in the box's Selected Content list
  And the box's other associations remain unchanged

Scenario: Removing the last association empties a box with siblings present
  Given a Competency Rule Group box has exactly one association, and other boxes exist for the competency
  When I remove that association, from either its Selected Content item or its Browse Courses panel chip
  Then the now-empty box is removed from the page
  And the competency's other boxes remain unaffected

Scenario: Removing the last association from the only remaining box
  Given a Competency Rule Group box has exactly one association, and it is the only box for the competency
  When I remove that association, from either its Selected Content item or its Browse Courses panel chip
  Then the box is removed
  And a placeholder box is shown as the new implicit active target

Scenario: Backend rejects the removal
  Given a remove request to the backend fails
  When I click the remove affordance on an association, from either entry point
  Then the association remains visible in the box's Selected Content list, and its Browse Courses panel chip still shows it as associated
  And an error is shown, following this feature's existing generic-error-handling pattern

Scenario: A course author without write access cannot remove an association
  Given I lack studio write access to the course the association's subsection belongs to
  Then neither the Selected Content item's remove affordance nor the Browse Courses panel chip's remove affordance is rendered
```

### Screenshot below illustrates some of the workflow, but the [Figma](https://www.figma.com/design/VhAdaucNQS49x0Afp9xPZw/Competency-Application?node-id=1892-48456&t=V5MSxdfsFJXzffTx-1) tells the story.

<img width="1240" height="899" alt="Image" src="https://github.com/user-attachments/assets/0d7e70c6-95ff-4a38-a93c-66241673f280" />

<img width="3546" height="2574" alt="Image" src="https://github.com/user-attachments/assets/b2c45b76-64b7-431f-a0c5-a237f095798c" />

## Description

This ticket adds a remove/deselect action to a single Selected Content item, letting a course author remove one subsection's association from a Competency Rule Group box without affecting that box's other associations.

**Current behavior**

An associated subsection is currently visible in two places at once: as an item in its Competency Rule Group box's Selected Content list (`SelectedContentItem`, built "display only, no deselect action" by \#672), and as an already-associated chip on the subsection itself in \#670's Browse Courses panel. Neither currently offers a way to remove the association; the only "undo" available is deleting the entire Competency Rule Group box (5.10c), which removes every other association in it too.

**Requested change**

- Both of that association's existing chips gain a remove/deselect "X": the one on its item in the Competency Rule Group box's Selected Content list, and the one on the subsection's own chip in \#670's Browse Courses panel.  
- Clicking either X removes the same one association via \#674; the Competency Rule Group box, its logic operator, and its other associations are unaffected. Both surfaces are rendered from the same GET-backed association data, so removing from either X updates both at once: the item disappears from the box's Selected Content list, and the subsection's chip in the Browse Courses panel visibly reverts to unassociated, selectable again.  
- If removing an association empties its Competency Rule Group box, \#674 deletes that now-empty box in the same call (see Technical Details). The box simply disappears from the page if sibling boxes remain, or the panel falls back to the placeholder box if it was the last one, per 5.10c's existing rendering logic, reused here rather than re-implemented.

<details>
<summary>Out of scope</summary>

- Deleting the whole Competency Rule Group box directly: 5.10c.  
- Confirmation dialogs, in-use/learner-status warnings: Use Case 10\. This ticket removes an association directly on click.  
- Creating an association and the blocked/dominance-conflict indication: \#672.  
- The rule/threshold configuration fields: \#671.  
- The exact backend request/response contract for \#674: not resolved here, that's \#674's own ticket.

</details>

<details>
<summary>Technical Details</summary>

### Data Structures

- `deleteCompetencyCriterion(criterionId)` (`data/api.ts`): DELETE call to \#674's endpoint. Contract assumed to mirror \#665's URL shape (e.g. `DELETE .../competencies/<tag_id>/criteria/<criterion_id>/`). \#674 deletes the emptied Competency Rule Group box server-side, in the same call, when the removed association was that box's last one; the exact response shape is \#674's own ticket to define.  
- `useDeleteCompetencyCriterion` (`data/apiHooks.ts`): a React Query mutation hook mirroring \#672's `useCreateCompetencyCriterion` conventions; invalidates the GET (\#681) query on success.

### Logic

- Both entry points call the same `useDeleteCompetencyCriterion` hook: `SelectedContentItem`'s new remove affordance (in the Competency Rule Group box), and the matching remove affordance added to the subsection's already-associated chip in \#670's Browse Courses panel.  
- On success: the invalidated GET query drops the removed association from both surfaces at once, since both render from the same GET-backed data — the item disappears from the box's Selected Content list, and the subsection's Browse Courses panel chip reverts to unassociated and selectable.  
- Because \#674 cascades an emptied box away server-side, this ticket does not call 5.10c's delete endpoint. It does reuse 5.10c's `activeGroupId`\-recomputation logic (not its API call) once the GET refetch reflects the box's removal, so the active target stays consistent with 5.10c's rules (falls back to a remaining sibling box, or the placeholder if none remain).  
- On delete failure, leave the association visible on both surfaces and follow \#672's generic error-handling pattern.  
- No confirmation dialog: Use Case 10's job.  
- Neither remove affordance is rendered at all — not merely disabled — for a course author without studio write access to the course.

### Example Resolution Prompt

> Implement the frontend consumer of \#674 in `frontend-app-authoring`, extending \#671/\#672's `src/taxonomy/competency-management/criteria-groups/` directory (check whether 5.10c already added `data/api.ts`/`data/apiHooks.ts` entries before adding new ones). Add `deleteCompetencyCriterion` and `useDeleteCompetencyCriterion` per Technical Details → Data Structures. Add a remove affordance to `SelectedContentItem.tsx` (from \#672) and a matching one to \#670's already-associated subsection chip in the Browse Courses panel, both wired to this hook per Technical Details → Logic. Since \#674 cascades an emptied box away server-side, do not call 5.10c's delete endpoint; reuse only its `activeGroupId`\-recomputation logic once the GET refetch reflects the box's removal. Hide (not disable) both remove affordances without studio write access. No confirmation dialog (Use Case 10's job). Follow \#672's generic error-handling pattern on failure.

## Context

- Sibling create ticket for the same entity: \#672 — builds `SelectedContentList`/`SelectedContentItem` as display-only, and the "chip with an X" reference this ticket's affordance follows.  
- Companion ticket whose rendering logic this one reuses: 5.10c (no GitHub issue yet) — owns the `activeGroupId`\-recomputation and placeholder-fallback logic this ticket relies on once a box disappears.

## Files to create and modify

**Modified files** (conditional: check whether \#671/\#672/5.10c already created these before adding new content)

| File | Nature of modification |
| :---- | :---- |
| `src/taxonomy/competency-management/criteria-groups/SelectedContentItem.tsx` (from \#672) | Add a remove ("X") affordance wired to `useDeleteCompetencyCriterion`; hidden without studio write access. |
| \#670's Browse Courses panel's subsection-row component (path TBD, not yet built) | Add a remove ("X") affordance to an already-associated subsection's chip, wired to the same `useDeleteCompetencyCriterion` hook; hidden without studio write access. |
| `src/taxonomy/competency-management/data/api.ts` | Add `deleteCompetencyCriterion`. |
| `src/taxonomy/competency-management/data/apiHooks.ts` | Add `useDeleteCompetencyCriterion`. |

Frontend implementation in `frontend-app-authoring`. Parent design: \#648. Foundation this builds on: \#670, \#671. Sibling on the same page: \#672 (creates the associations this ticket deletes), 5.10c (deletes a whole Competency Rule Group box — this ticket reuses its `activeGroupId`\-recomputation and placeholder-fallback rendering logic when emptying a box's last association; no GitHub issue yet).

**Blocked by:** \#674 (backend delete-association endpoint, which also cascades an emptied box away server-side); \#672 (builds `SelectedContentList`/`SelectedContentItem` as "display only, no deselect action" — this ticket adds that action); 5.10c (the `activeGroupId`\-recomputation rendering logic this ticket reuses when a box empties; no GitHub issue yet); \#681 (GET groups \+ criteria endpoint).

</details>
