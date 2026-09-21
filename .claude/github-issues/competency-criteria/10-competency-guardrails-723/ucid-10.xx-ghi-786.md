# [FE] Confirm every deletion of a tag association from the Competency Management page

GitHub: https://github.com/openedx/openedx-core/issues/786 (#786, OPEN)
Cached: 2026-09-21

## User Story

As a course author, I want to confirm before I remove a competency's association with content, so I understand this action cannot be undone from this screen and that learners keep the mastery they have already earned.

## Acceptance Criteria

```
Scenario: Deleting an association asks for confirmation first
  Given an author is viewing a competency's content associations
  When they delete one
  Then a confirmation is shown
    And the association is not yet removed

Scenario: Confirming removes the association from the page
  Given the confirmation is shown for an association
  When the author confirms
  Then the association is removed from the page

Scenario: Cancelling leaves the association in place
  Given the confirmation is shown for an association
  When the author cancels
  Then the association is still listed
    And nothing is sent to the server

Scenario: The confirmation reads the same whatever happens underneath
  Given two associations, one that learner mastery depends on and one that does not
  When the author deletes each
  Then the same confirmation wording is shown for both

Scenario: A deletion that fails does not appear to have succeeded
  Given the author has confirmed a deletion
  When the request fails
  Then the failure is shown to the author
    And the association is still listed

Scenario: The confirmation is usable by keyboard and screen reader
  When the confirmation is shown
  Then focus moves into it
    And its message and buttons are announced
    And it can be dismissed from the keyboard

Scenario: Both entry points that directly remove one association show the confirmation
  Given a course author viewing a competency's rule box
  When they click the "X" on an already-associated subsection's chip in the Browse Courses panel, or the "X" on that same association's item in the box's Selected Content list
  Then the confirmation is shown either way

Scenario: Deleting a whole criteria group shows the confirmation too
  Given a course author viewing a competency's criteria group
  When they click the control to delete the whole group
  Then the confirmation is shown
    And the group and everything beneath it is not yet removed
```

## Description

Removing a competency's association with a piece of content on the Competency Management page happens immediately, with no confirmation. Underneath, that removal will either delete the association or retire it, depending on whether any learner has been evaluated through it, and the author is deliberately not told which.

This ticket adds the confirmation step. The wording and behavior come from the design spike \#775, and the backend behavior it triggers is \#779.

**Three ways to delete an association on this page are in scope:** the "X" on a chip in the Browse Courses panel, the "X" on a chip in a rule box's Selected Content list, and the control to delete a whole criteria group (\#709). There is no control to delete a whole rule box (a display-only grouping of criteria that share one score threshold, not a persisted record). An author reduces a live rule box to nothing by removing its criteria one at a time.

<details>
<summary>Technical Details</summary>

This section is background and a suggested approach, not the ticket's source of truth. The User Story and Acceptance Criteria define what must be true when the work is done.

### In short

**Why one wording covers both outcomes.** The server decides whether to remove the association or retire it, based on whether learner mastery depends on it, and does not report which it did. So the dialog cannot describe the mechanism. It can say the action cannot be undone from this screen and that existing learner mastery is unaffected, both of which are true either way.

**What the frontend sends is unchanged.** Removal already happens by submitting the object's new set of tags; the archive-or-delete branch is entirely server-side in \#779. This ticket adds a confirmation in front of the existing request and changes nothing about the request itself.

**Take the wording from the design spike.** The starting text is a draft that \#775 refines, together with the responsive and accessible behavior.

**There are two entry points to a direct association removal, confirmed against the actual Competency Management UI:** the "X" on an already-associated subsection's chip in the Browse Courses panel, and the "X" on that same association's item in the rule box's own Selected Content list. Both must show the confirmation.

**The third entry point is deleting a whole criteria group, \#709's action.** This ticket gates it with the same dialog, since removing a group also removes or retires every association beneath it.

### Implementation specifics

- **Gate the existing delete action** on the Competency Management page's association list, from both entry points identified above (the Browse Courses panel chip and the box's Selected Content list item). Do not change the request, the endpoint, or the payload.  
- **Also gate \#709's whole-group delete action, the same way.** Same dialog, same wording, same "not yet removed until confirmed" behavior.  
- **Use the dialog \#775 specifies**, including final wording, button labels, focus behavior, and small-screen layout. If \#775 has not landed, block on it rather than inventing copy.  
- **Reuse the project's existing modal component**, the same one \#785 uses, so the two confirmations behave consistently and focus trapping and announcement come for free.  
- **Do not report which outcome occurred**, and do not add a request to find out whether learner mastery depends on the association. The author is deliberately not told.  
- **Surface a failure and leave the association listed.** Do not optimistically remove it from the list before the request succeeds, or a failed delete will look like a successful one until the page is reloaded.  
- **Tests:** the delete action shows the dialog and sends nothing, from all three entry points; confirming removes the association or the group; cancelling sends nothing and leaves it listed; the same wording is used regardless of the server's outcome or which entry point triggered it; a failed request reports the failure and leaves the association listed; focus moves into the dialog and it is keyboard dismissible.  
- **Out of scope:** the edit confirmation (\#785), the design itself (\#775), the server-side archive-versus-delete branch (\#779), and the Course Outline and Libraries pages, which are \#784, and any whole-rule-box delete control, which does not exist.  
- Context \#775 is the design spike that produces this dialog's wording and behavior.  
- \#779 is the server-side branch this confirmation sits in front of.  
- \#709 specifies the whole-group delete action this ticket also gates.

The approved implementation approach on \#655, for why the author is not told whether the association was removed or retired.

</details>
