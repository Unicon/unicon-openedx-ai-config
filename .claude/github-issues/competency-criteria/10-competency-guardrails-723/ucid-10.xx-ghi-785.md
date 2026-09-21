# [FE] Confirm every edit to a competency criterion or criteria group

GitHub: https://github.com/openedx/openedx-core/issues/785 (#785, OPEN)
Cached: 2026-09-21

## User Story

As a course author, I want to confirm before I change a competency rule, in order to understand that my change affects future evaluations only and does not alter what learners have already earned.

## Acceptance Criteria

```
Scenario: Editing a criterion asks for confirmation before saving
  Given an author has changed a competency criterion
  When they submit the change
  Then a confirmation explaining that only future evaluations are affected is shown
    And the change is not yet saved

Scenario: Confirming saves the change
  Given the confirmation is shown for an edited criterion
  When the author confirms
  Then the change is saved
    And the confirmation closes

Scenario: Cancelling abandons the save and keeps the author's edits
  Given the confirmation is shown for an edited criterion
  When the author cancels
  Then the change is not saved
    And the author's unsaved edits are still on screen

Scenario: Editing a criteria group asks for confirmation too
  Given an author has changed a competency criteria group
  When they submit the change
  Then the same kind of confirmation is shown before saving

Scenario: The confirmation appears whether or not any learner has been evaluated
  Given a criterion that no learner has been evaluated against
  When an author edits and submits it
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

<details>
<summary>Technical Details</summary>

This section is background and a suggested approach, not the ticket's source of truth. The User Story and Acceptance Criteria define what must be true when the work is done.

### In short

**Why the warning is unconditional.** It appears on every criterion and group edit, not only when learner statuses already exist. Product chose that deliberately: a dialog that appears only sometimes trains authors to expect saves to be silent and then surprises them, and the frontend would need to know whether any learner had been evaluated in order to decide, which is information it does not have on this screen.

**What the wording has to be true about.** An edit changes future evaluations only. It never rewrites a status a learner already earned, and it never removes anything. That is the whole content of the message, and it is why this dialog is worded differently from the delete confirmation in \#786.

**The two edit surfaces, confirmed against the actual Competency Management UI (not assumed):** a criterion's rule threshold (operator and percentage, in the "Competency Completion Rule" panel under a course/content association) and a criteria group's combining logic (the "any"/"all" dropdown). These are two different controls, not one shared save path — see the open complication below for what that means for this ticket.

**Take the wording from the design spike rather than this ticket.** The starting text is a draft that \#775 refines, along with the responsive and accessible behavior. Do not treat the sample copy in the spike as final without checking what \#775 concluded.

**Open complication, not yet resolved: there is no distinct save action to gate.** Both edit surfaces above currently auto-apply on change; there is no visible "Save" step to intercept, which is what "gate the submit, not the field" below assumes exists. Confirming before a change takes effect may mean intercepting every field's change handler directly rather than a single submit action, which is a materially different (and likely harder) interaction than what \#775's starting design (a dialog with Cancel/Save Changes buttons) assumes. This probably needs to go back to \#775 before this ticket's own implementation approach can be trusted, rather than being resolved here.

### Implementation specifics

- **Gate the submit, not the field.** Let the author edit freely; intercept the save. *(See the open complication above: it's not yet clear this ticket has a "submit" to gate.)*  
- **Use the dialog \#775 specifies**, including its final wording, button labels, focus behavior, and small-screen layout. If \#775 has not landed, block on it rather than inventing copy: the wording is the substance of this ticket.  
- **Reuse the project's existing modal component** rather than building one, so focus trapping and screen-reader announcement come for free and match the rest of the authoring frontend.  
- **Cancelling preserves form state.** Do not reset the form, refetch, or navigate away.  
- **Show the confirmation for both record types**, a criterion and a criteria group, from whatever edit surfaces exist for each.  
- **Do not condition it on learner status.** No extra request to find out whether anyone has been evaluated; the dialog is unconditional.  
- **Surface a save failure to the author** and leave their edits on screen. Do not close the dialog on failure in a way that loses the change.  
- **Tests:** submitting shows the dialog and does not save; confirming saves; cancelling does not save and preserves edits; both record types show it; a criterion with no learner status still shows it; a failed save reports the failure and keeps the edits; focus moves into the dialog and it is keyboard dismissible.  
- **Out of scope:** the delete confirmation for an association (\#786), the design itself (\#775), the backend update endpoints, which \#759 and \#760 provide, and any change to what an edit does server-side.  
- Context \#775 is the design spike that produces this dialog's wording, responsive behavior, and accessible behavior.  
- The approved implementation approach on \#655, for the decision that edit warnings are unconditional and that tag and taxonomy edits get none.  
- \#759 and \#760 provide the update endpoints this gates.  
- `.claude/frontend-app-authoring-architecture-overview.md` for the authoring frontend's conventions and existing modal patterns.

</details>
