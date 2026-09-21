# [UXD] Build the UI for Competency Criteria Associations

GitHub: https://github.com/openedx/openedx-core/issues/648 (#648, CLOSED)
Cached: 2026-09-21

# \[UXD\] Manage & Apply Competencies: design review and sign-off

**Task \#648 — the parent of the Manage & Apply Competencies work.** This is a design **review and sign-off** ticket: the finished designs already exist, and this ticket is the vehicle to present them for team review and record agreement. The deliverable is reviewed, signed-off design artifacts, not code.

Children (implementation): \#671 (create / remove Competency Criteria Groups), \#672 (select / deselect gradeable-subsection associations). Foundation: \#670 (the page, its competency tree, and the course-search / browse panel). Repo (eventual build): `frontend-app-authoring`.

## Use Case

As a course author who will use the Manage & Apply Competencies page to build competency criteria, I want the finished designs for the whole page reviewed and signed off by the team, so that the shipped authoring experience matches validated intent and \#670/\#671/\#672 don't build against designs that get re-litigated mid-implementation.

## Description

Finished UX designs exist for the entire Manage & Apply Competencies page: the page shell and two-panel layout, the competency tree, Competency Criteria Groups (create, nest, remove), and gradeable-subsection associations (select, deselect, already-associated, and blocked/rejected states). No code exists for this page: \#670, \#671, and \#672 are all unbuilt.

Figma link to existing designs: [https://www.figma.com/design/VhAdaucNQS49x0Afp9xPZw/Competency-Application?node-id=3-45424\&t=zImspZK8unjhmx3e-4](https://www.figma.com/design/VhAdaucNQS49x0Afp9xPZw/Competency-Application?node-id=3-45424&t=zImspZK8unjhmx3e-4) 

## Delivery Checklist

*The deliverable is a reviewed and signed-off set of design artifacts, not code. There is no Gherkin and no QA path; acceptance is this checklist completed and sign-off recorded.*

- [ ] Finished designs for the full Manage & Apply Competencies page linked on this ticket.  
- [ ] Page shell / two-panel layout reviewed.  
- [ ] Competency tree and its selection behavior reviewed.  
- [ ] Competency Criteria Group screens reviewed: create, nest (up to 3 levels), remove, and the AND/OR ("within all" / "within any") control.  
- [ ] Gradeable-subsection association screens reviewed: select, deselect, already-associated indication, and the blocked/rejected state (dominance validation).  
- [ ] Any requested changes or re-litigated decisions documented on this ticket, with rationale.  
- [ ] Final sign-off recorded, confirming the designs are ready for \#670/\#671/\#672 to build against.  
- [ ] Sign-off and any resulting design updates communicated to \#670, \#671, and \#672.
