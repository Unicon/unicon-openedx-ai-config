# [FE] Confirm every deletion of a tag association from the Competency Management page

GitHub: https://github.com/openedx/openedx-core/issues/786 (#786, OPEN)
Cached: 2026-09-25

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

Scenario: Deleting a whole Rule Group or Course Group shows the confirmation too
  Given a course author viewing a competency's rules
  When they click the trash control on a saved Rule Group or on a Course Group
  Then the confirmation is shown
    And the group and everything beneath it is not yet removed

Scenario: Deleting a whole rule box shows the confirmation too
  Given a course author viewing a competency's rule box that has saved content
  When they click the rule box's trash control
  Then the confirmation is shown
    And none of the box's associations are removed yet

Scenario: Deleting an unsaved placeholder does not ask for confirmation
  Given a course author has added a Rule Group or rule box with no content in it yet
  When they click its trash control
  Then it is removed from the page immediately
    And no confirmation is shown
```
[Figma Link](https://www.figma.com/design/VhAdaucNQS49x0Afp9xPZw/Competency-Application?node-id=2069-48957&t=6uwoGM2Z0scaqjZv-1)

<img width="1231" height="892" alt="Image" src="https://github.com/user-attachments/assets/578e8398-cb6d-4ff6-b8f5-aa90360fa5c6" />

## Description

Removing a competency's association with a piece of content on the Competency Management page happens immediately, with no confirmation. Underneath, that removal will either delete the association or retire it, depending on whether any learner has been evaluated through it, and the author is deliberately not told which.

This ticket adds the confirmation step. The wording and behavior come from the design spike \#775. The backend behavior it triggers is \#674 (delete one criterion) and \#675 (delete a whole group).

**Four ways to delete an association on this page are in scope:** the "X" on a chip in the Browse Courses panel, the "X" on a chip in a rule box's Selected Content list, the trash control that deletes a whole Rule Group or Course Group (\#709), and the trash control that deletes a whole rule box (\#833). A rule box is a display-only grouping of criteria that share one score threshold, not a persisted record, so \#833 deletes it by removing each of its criteria. Deleting an unsaved placeholder Rule Group or rule box removes nothing on the server and shows no confirmation.

<details>
<summary>Technical Details</summary>

This section is background and a suggested approach, not the ticket's source of truth. The User Story and Acceptance Criteria define what must be true when the work is done.

### In short

**Why one wording covers both outcomes.** The server decides whether to remove the association or archive it, based on whether learner mastery depends on it, and does not report which it did. So the dialog cannot describe the mechanism. It can say the action cannot be undone from this screen and that existing learner mastery is unaffected, both of which are true either way.

**What the frontend sends is unchanged.** Removal on this page goes through the \#674 and \#675 delete endpoints, and the archive-or-delete branch is entirely server-side in those endpoints. This ticket adds a confirmation in front of the existing request and changes nothing about the request itself.

**Take the wording from the design spike.** The starting text is a draft that \#775 refines, together with the responsive and accessible behavior.

**There are two entry points to a direct association removal, confirmed against the actual Competency Management UI:** the "X" on an already-associated subsection's chip in the Browse Courses panel, and the "X" on that same association's item in the rule box's own Selected Content list. Both must show the confirmation.

**The third and fourth entry points are deleting a whole Rule Group or course section (\#709) and deleting a whole rule box (\#833).** This ticket gates both with the same dialog, since each removes or archives every association beneath it. For a rule box, one confirmation covers all of the box's criteria, not one per criterion.

### Implementation specifics

- **Gate the existing delete action** on the Competency Management page's association list, from both entry points identified above (the Browse Courses panel chip and the box's Selected Content list item). Do not change the request, the endpoint, or the payload.  
- **Also gate \#709's whole-group delete action and \#833's whole-rule-box delete action, the same way.** Same dialog, same wording, same "not yet removed until confirmed" behavior. Do not gate deleting an unsaved placeholder.  
- **Use the dialog \#775 specifies**, including final wording, button labels, focus behavior, and small-screen layout. If \#775 has not landed, block on it rather than inventing copy.  
- **Reuse the project's existing modal component**, the same one \#785 uses, so the two confirmations behave consistently and focus trapping and announcement come for free.  
- **Do not report which outcome occurred**, and do not add a request to find out whether learner mastery depends on the association. The author is deliberately not told.  
- **Surface a failure and leave the association listed.** Do not optimistically remove it from the list before the request succeeds, or a failed delete will look like a successful one until the page is reloaded.  
- **Tests:** the delete action shows the dialog and sends nothing, from all four entry points; deleting an unsaved placeholder shows no dialog; confirming removes the association or the group; cancelling sends nothing and leaves it listed; the same wording is used regardless of the server's outcome or which entry point triggered it; a failed request reports the failure and leaves the association listed; focus moves into the dialog and it is keyboard dismissible.  
- **Out of scope:** the edit confirmation (\#785), the design itself (\#775), the server-side archive-versus-delete branch (\#674, \#675), and the Course Outline and Libraries pages, which are \#784.  
- Context \#775 is the design spike that produces this dialog's wording and behavior.  
- \#674 and \#675 are the server-side branch this confirmation sits in front of.  
- \#709 specifies the whole-group delete action, and \#833 the whole-rule-box delete action, that this ticket also gates.

The approved implementation approach on \#655, for why the author is not told whether the association was removed or archived.

</details>
