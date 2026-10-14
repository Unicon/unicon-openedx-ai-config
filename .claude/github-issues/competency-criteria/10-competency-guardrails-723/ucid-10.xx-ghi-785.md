# [FE] Confirm every edit to a competency criterion or criteria group

GitHub: https://github.com/openedx/openedx-core/issues/785 (#785, OPEN)
Cached: 2026-09-21

## User Story

As a course author, I want to confirm before I change a competency rule, in order to understand that my change affects future evaluations only and does not alter what learners have already earned.

## Acceptance Criteria

```
Scenario: Saving a criterion's score threshold asks for confirmation first
  Given an author has changed a criterion's score threshold in the score popover
  When they choose Save in the popover
  Then a confirmation explaining that only future evaluations are affected is shown
    And the change is not yet saved

Scenario: Confirming saves the change
  Given the confirmation is shown for an edited criterion
  When the author confirms
  Then the change is saved
    And the confirmation closes

Scenario: Cancelling a score threshold change abandons the save and keeps the author's edits
  Given the confirmation is shown after the author chose Save in the score popover
  When the author cancels
  Then the change is not saved
    And the author's unsaved edits are still in the score popover

Scenario: Choosing a new any/all value for a criteria group asks for confirmation right away
  Given a criteria group set to combine its rules with "any"
  When the author chooses "all" in its any/all dropdown
  Then the same kind of confirmation is shown immediately
    And the change is not yet saved

Scenario: Cancelling an any/all change switches the dropdown back
  Given the confirmation is shown after the author changed a criteria group's dropdown from "any" to "all"
  When the author cancels
  Then the change is not saved
    And the dropdown shows "any" again

Scenario: The confirmation appears whether or not any learner has been evaluated
  Given a criterion that no learner has been evaluated against
  When an author changes its score threshold and chooses Save in the score popover
  Then the confirmation is still shown

Scenario: A save that fails does not claim to have succeeded
  Given the author has confirmed an edit
  When saving fails
  Then the failure is shown to the author
    And the author's edits are still on screen

Scenario: The confirmation is usable by keyboard and screen reader
  When the confirmation is shown
  Then focus moves into it
    And its message and buttons are announced
    And it can be dismissed from the keyboard
```

## Description

Editing a competency criterion or criteria group on the Competency Management page saves immediately with no confirmation. An author has no indication that their change applies only going forward, and that learners already evaluated against the old rule keep the status they earned.

This ticket adds the confirmation step. The wording and behavior come from the design spike \#775.

Figma Links:
[E1 · Edit a rule's score (Cancel / Save)](https://www.figma.com/design/VhAdaucNQS49x0Afp9xPZw/Competency-Application?node-id=3056-39361)
[E2 · Confirm rule change](https://www.figma.com/design/VhAdaucNQS49x0Afp9xPZw/Competency-Application?node-id=3056-39817)
[E4 · Change a group's any/all](https://www.figma.com/design/VhAdaucNQS49x0Afp9xPZw/Competency-Application?node-id=3056-40729)
[E5 · Confirm logic change](https://www.figma.com/design/VhAdaucNQS49x0Afp9xPZw/Competency-Application?node-id=3056-41185)
[E2b · Save failed](https://www.figma.com/design/VhAdaucNQS49x0Afp9xPZw/Competency-Application?node-id=3062-41986)

Screenshots:

<img width="1600" height="1161" alt="Image" src="https://github.com/user-attachments/assets/da445053-19c6-44de-9f26-414c73c80532" />

<img width="1600" height="1161" alt="Image" src="https://github.com/user-attachments/assets/3cb7e231-f2ce-45cf-a215-2de574673934" />

<img width="1600" height="1161" alt="Image" src="https://github.com/user-attachments/assets/a110be53-ba95-4155-8adf-a13696c39152" />

<img width="1600" height="1161" alt="Image" src="https://github.com/user-attachments/assets/c66aaeae-f520-4952-a809-ae9be3d9ff55" />

<img width="1600" height="1161" alt="Image" src="https://github.com/user-attachments/assets/8b717fa8-18f7-4325-b7f1-ce831fc15637" />

<details>
<summary>Technical Details</summary>

This section is background and a suggested approach, not the ticket's source of truth. The User Story and Acceptance Criteria define what must be true when the work is done.

### In short

**Why the warning is unconditional.** It appears on every criterion and group edit, not only when learner statuses already exist. Product chose that deliberately: a dialog that appears only sometimes trains authors to expect saves to be silent and then surprises them, and the frontend would need to know whether any learner had been evaluated in order to decide, which is information it does not have on this screen.

**What the wording has to be true about.** An edit changes future evaluations only. It never rewrites a status a learner already earned, and it never removes anything. That is the whole content of the message, and it is why this dialog is worded differently from the delete confirmation in \#786.

**The two edit surfaces, confirmed against the actual Competency Management UI (not assumed):** a criterion's rule threshold (operator and percentage, in the "Competency Completion Rule" panel under a course/content association) and a criteria group's combining logic (the "any"/"all" dropdown). These are two different controls, not one shared save path, so each one opens the confirmation in its own way, as described below.

**Take the wording from the design spike rather than this ticket.** The starting text is a draft that \#775 refines, along with the responsive and accessible behavior. Do not treat the sample copy in the spike as final without checking what \#775 concluded.

**How each edit surface opens the confirmation, per \#775.** Both surfaces apply a change as soon as it is made today, so there is no save step to intercept. \#775 adds one where it is needed. The score popover gets Cancel and Save buttons, and Save opens the confirmation; the author's edits stay in the popover until they confirm or cancel. The any/all dropdown has no separate save step, so choosing a new value opens the confirmation right away. Cancelling that confirmation switches the dropdown back to its previous value, because a dropdown has no unsaved edit to keep on screen.

### Implementation specifics

- **Gate the score popover's Save and the any/all dropdown's change.** Add Cancel and Save buttons to the score popover, let the author edit the threshold freely, and open the confirmation from Save. For the dropdown, hold the newly chosen value as pending and open the confirmation; send the update only when the author confirms.  
- **Use the dialog \#775 specifies**, including its final wording, button labels, focus behavior, and small-screen layout. If \#775 has not landed, block on it rather than inventing copy: the wording is the substance of this ticket.  
- **Reuse the project's existing modal component** rather than building one, so focus trapping and screen-reader announcement come for free and match the rest of the authoring frontend.  
- **What cancelling does depends on the surface.** In the score popover, cancelling the confirmation preserves the popover's form state: do not reset the form, refetch, or navigate away. For the any/all dropdown, cancelling restores the value it had before the author's choice.  
- **Show the confirmation for both record types**, a criterion and a criteria group, from whatever edit surfaces exist for each.  
- **Do not condition it on learner status.** No extra request to find out whether anyone has been evaluated; the dialog is unconditional.  
- **Surface a save failure to the author** and leave their edits on screen. Do not close the dialog on failure in a way that loses the change.  
- **Tests:** Save in the score popover shows the dialog and does not save; choosing a new any/all value shows the dialog and does not save; confirming saves; cancelling after the popover's Save does not save and keeps the edits in the popover; cancelling after an any/all change does not save and restores the previous value; both record types show it; a criterion with no learner status still shows it; a failed save reports the failure and keeps the edits; focus moves into the dialog and it is keyboard dismissible.  
- **Out of scope:** the delete confirmation for an association (\#786), the design itself (\#775), the backend update endpoints, which \#759 and \#760 provide, and any change to what an edit does server-side.  
- Context \#775 is the design spike that produces this dialog's wording, responsive behavior, and accessible behavior.  
- The approved implementation approach on \#655, for the decision that edit warnings are unconditional and that tag and taxonomy edits get none.  
- \#759 and \#760 provide the update endpoints this gates.  
- `.claude/frontend-app-authoring-architecture-overview.md` for the authoring frontend's conventions and existing modal patterns.

</details>
