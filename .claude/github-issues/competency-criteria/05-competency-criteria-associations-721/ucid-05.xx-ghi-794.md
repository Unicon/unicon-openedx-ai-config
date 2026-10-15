# [FE] Update/Edit Competency Criteria & Groups

GitHub: https://github.com/openedx/openedx-core/issues/794 (#794, OPEN)
Cached: 2026-09-21

## User Story

As a course author, I want to change how an existing bottom-tier group combines its rule boxes, or the score an existing rule box requires, in order to correct a mastery rule without deleting and rebuilding the whole branch.

## Acceptance Criteria

```
Scenario: Change how a saved bottom-tier group combines its rule boxes
  Given a bottom-tier group whose rule boxes already have saved content, set to require any one of them
  When I change it to require all of them
  Then the change is saved
  And it still reads as requiring all of them after I reload

Scenario: Change the score a rule box requires
  Given a rule box that already has content associated with it
  When I change the score it requires
  Then every piece of content in that rule box is judged by the new score
  And the new score is still shown after I reload

Scenario: A persisted rule box's score cannot duplicate one already in the same group
  Given a bottom-tier group containing two rule boxes with different scores, both already holding content
  When I change one rule box's score to match the other's
  Then the change is refused and the reason is shown
  And both rule boxes keep the scores they had

Scenario: Setting a rule box back to the default value returns it to the default
  Given a rule box I previously changed to a score of my own
  When I set it back to the same value the system default supplies
  Then the displayed score is unchanged, since the page never distinguishes a default from a matching override (see #672)
  And inspecting the underlying data directly confirms the override has been cleared and the criterion now follows the system default

Scenario: A change is rejected by the backend
  Given I change how a bottom-tier group combines its rule boxes, or the score a rule box requires
  When the save is rejected
  Then the control returns to the value it held before my change
  And an error is shown, following this feature's existing generic error-handling pattern

Scenario: I lack permission to change an existing bottom-tier group's or rule box's settings
  Given a bottom-tier group or rule box I am not permitted to edit
  When I view it
  Then no control to change how it combines its children or what score it requires is offered
  And I can still read the combining choice and the score it currently has
```

## Description

\#672 renders the bottom-tier group cards and rule boxes and builds the two controls this ticket makes editable: the combining-logic control on a bottom-tier group and the score field on a rule box. Both render as read-only text there, because each takes an optional change handler and \#672 passes none. This ticket passes one on a persisted row, wired to the backend.

<details>
<summary>Technical Details</summary>

This section is background and a suggested approach, not the ticket's source of truth. The User Story and Acceptance Criteria define what must be true when the work is done; what follows exists to save the implementer some thinking, not to bind them.

### In short

**This ticket adds no new rendering.** \#672's `LogicOperatorSelect` and `ScoreThresholdField` already render an editable control when given a change handler and read-only text when not, and \#672 passes none. This ticket passes one on a persisted bottom-tier group and a persisted rule box, wired to a mutation, when the requesting user is permitted to make the change. Nothing about the components themselves changes, and there is no second "is it editable" flag to keep in step with the handler.

**Two different endpoints back the two controls.** The any/all control on a persisted bottom-tier group calls \#760, which changes how a Competency Criteria Group combines the criteria and groups beneath it, addressed by the bottom-tier group's own id. The score field on a persisted rule box calls \#759, which changes the rule that a set of Competency Criteria are evaluated by in one request, addressed by every criterion id currently inside that rule box. A rule box is a display grouping of criteria that share one rule, so changing "the box's score" really means re-issuing \#759's batch update against every criterion in it, so that they continue to share one rule, and therefore remain one rule box, afterward.

**A rule box's identity is still its rule, which constrains what a score change can validly produce.** If the new score matches another rule box already in the same group, the criteria being updated would, after the call succeeds, share a rule with that other box and merge into it on the next refetch, leaving the author looking at one box where there had been two, with no explanation. This ticket refuses that value in the field before the call is made. \#672 owns both halves of the check: the helper that computes a rule's identity key and the helper that lists a group's existing rule boxes. Write the check directly against those two rather than extracting a shared validator; \#671 writes the same one-line check for a not-yet-saved rule box, and neither ticket needs the other to exist.

**Setting an override back to the applicable default is not a special case this ticket needs to detect.** Per ADR 0002's own write-event rules, the backend itself reassigns a criterion from a matching override back to a profile reference whenever the value matches, so this ticket only needs to send whatever value the author entered. The "following the default again" outcome is the backend's doing, and \#672's effective-rule display already renders that state correctly whether the value arrived as a profile reference or as a matching override.

**Rejection rolls the control back to what it displayed before the change**, mirroring \#672's own rejection handling for the create call: the control is optimistic-free, meaning it does not adopt the attempted value until the mutation succeeds, so "rolling back" is simply not having changed the displayed value in the first place, and only the error needs surfacing.

### Implementation specifics

- **Mutation hooks.** `useUpdateCompetencyCriteriaGroupOperator(groupId)` and `useUpdateCompetencyCriteriaRule(criterionIds, rulePayload)` in `src/taxonomy/competency-management/data/apiHooks.ts`, modeled on `useCreateCompetencyCriterion` in the same file, which \#672 adds. Both invalidate the \#681 groups query on success, following the same pattern.  
- **API functions.** `updateCompetencyCriteriaGroupOperator(groupId, logicOperator)` and `updateCompetencyCriteriaRule(criterionIds, rulePayload)` in `data/api.ts`, against \#760's and \#759's endpoints respectively.  
- **Enable editing on a persisted row.** In `criteria-groups/CriteriaGroupBox.tsx` and `criteria-groups/RuleBox.tsx`, pass an `onChange` to the `LogicOperatorSelect` and the `ScoreThresholdField` on a persisted row, wired to the mutations above, gated by \#672's `canEditCourse(courseId)`, resolved for whichever course the group or criterion being edited belongs to (a bottom-tier group's own course, via its course-level parent; a criterion's, via the subsection its `ObjectTag` points at). Passing no handler when the predicate is false is what satisfies the permission scenario: the value still renders, as read-only text, with no control offered.  
- **Do not touch the placeholder call sites.** \#671 passes its own `onChange` to the same two components on a not-yet-saved card, writing to local provider state rather than to an endpoint. Leave those call sites alone; the permission predicate does not apply to them.  
- **Duplicate-score check.** Supply `getInlineValidationMessage` to the persisted rule box's `ScoreThresholdField`, returning a message when `ruleBoxesForGroup(groupId)` already contains a box whose key equals `ruleKeyOf` of the candidate rule and is not the box being edited. Both helpers are \#672's. Add the message to `messages.ts` if it is not already there; \#671 writes the same check for a placeholder and may have added it first.  
- **Do not convert the score value.** `ScoreThresholdField` already converts between the displayed percentage and the stored fraction, so the value handed to `updateCompetencyCriteriaRule` is already the fraction \#759 expects.  
- **Error surfacing.** Use `showToast` from `useToastContext` (`src/generic/toast-context`), the same pattern \#672 uses for a failed create call, so the two error paths look identical to the author.  
- **Permission gating.** Route both controls through \#672's `canEditCourse(courseId)`; do not introduce a second gating mechanism. Resolving which course a bottom-tier group or a criterion belongs to, to pass into it, is this ticket's own job, since \#671 only ever resolves it from a group already known to be in a rendered course section.  
- **Out of scope, owned elsewhere.** Rendering the bottom-tier group card, the rule box, the connector, the course-level header, the two field components themselves, the rule-box derivation helpers, the create-association call, and course-expansion focus all belong to \#672. Adding a new bottom-tier group or rule box, and all not-yet-saved-card behavior including editing its fields, belong to \#671. Deleting a group is \#709; deleting an association is \#710.  
- **Test cases to cover.**  
  - Changing a persisted bottom-tier group's operator from any to all, and back, both persist across a refetch.  
  - Changing a persisted rule box's score updates every criterion in that box.  
  - Changing a persisted rule box's score to match a sibling box's score is refused with an inline message, and neither box's score changes.  
  - Editing a persisted rule box's score to the value it already has is not treated as a duplicate of itself.  
  - Setting a persisted rule box's score back to the applicable default value succeeds and the box displays as following the default on the next read.  
  - A rejected operator change or score change leaves the control showing its pre-change value and surfaces an error via the shared toast pattern.  
  - When the permission predicate is false, both controls render as read-only text showing their current values, with no interactive control.

Files to create and modify **New files**

| File | Purpose |
| :---- | :---- |
| `src/taxonomy/competency-management/criteria-groups/CriteriaGroupBox.edit.test.tsx` | Editing a persisted bottom-tier group's operator, rejection rollback, and the permission-gated read-only rendering. |
| `src/taxonomy/competency-management/criteria-groups/RuleBox.edit.test.tsx` | Editing a persisted rule box's score, the duplicate-score refusal, rejection rollback, and the permission-gated read-only rendering. |

**Modified files**

| File | Nature of modification |
| :---- | :---- |
| `src/taxonomy/competency-management/data/api.ts` | Add `updateCompetencyCriteriaGroupOperator` and `updateCompetencyCriteriaRule`. |
| `src/taxonomy/competency-management/data/apiHooks.ts` | Add `useUpdateCompetencyCriteriaGroupOperator` and `useUpdateCompetencyCriteriaRule`, both invalidating the groups query on success. |
| `src/taxonomy/competency-management/criteria-groups/CriteriaGroupBox.tsx` | Pass an `onChange` to `LogicOperatorSelect` on a persisted bottom-tier group, wired to the group-operator mutation and gated by the permission predicate. |
| `src/taxonomy/competency-management/criteria-groups/RuleBox.tsx` | Pass an `onChange` and a `getInlineValidationMessage` to `ScoreThresholdField` on a persisted rule box, wired to the rule mutation and gated by the permission predicate. |
| `src/taxonomy/competency-management/messages.ts` | Add the duplicate-score message if it is not already present. |

- Context **\#672:** renders the bottom-tier group cards and rule boxes, builds `LogicOperatorSelect` and `ScoreThresholdField` with the optional `onChange` and `getInlineValidationMessage` props this ticket supplies, and owns `ruleKeyOf` and `ruleBoxesForGroup`, which this ticket's duplicate check reads. It also owns the error-toast pattern this ticket's rejection handling follows.  
- **\#671:** a sibling that adds the not-yet-saved bottom-tier group and rule box and makes their fields editable. It is independent of this ticket: both extend \#672 and neither depends on the other, so they can be built in either order or at the same time.  
- **\#759:** the batch rule-update endpoint this ticket's score-change control calls.  
- **\#760:** the group-combining-operator update endpoint this ticket's any/all control calls.  
- ADR `docs/openedx_learning/decisions/0002-competency-criteria-model.rst` in `openedx-core`: the write-event rule that reassigns a matching override back to a profile reference, relevant to the "back to default" scenario above.  
- Frontend prior art: `src/taxonomy/tree-table/EditableCell.tsx` for the `getInlineValidationMessage` prop, `src/taxonomy/tag-list/hooks.ts` for a caller building one of those validators, and `src/generic/toast-context` for the error toast.

</details>
