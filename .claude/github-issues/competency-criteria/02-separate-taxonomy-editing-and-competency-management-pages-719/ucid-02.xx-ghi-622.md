# [UXD] Create UX designs for taxonomy actions menu with Apply Competencies and Edit Taxonomy options

GitHub: https://github.com/openedx/openedx-core/issues/622 (#622, CLOSED)
Cached: 2026-09-21

## UX Design: Taxonomy actions menu — "Manage Competencies" entry point and workflow fork

### Use Case

As an Open edX Admin or Staff user, I want a dedicated entry point in the taxonomy actions menu to manage competency criteria for a competency taxonomy, so that I can navigate to the Competency Management page without confusing it with the taxonomy editing flow.

### Description

**Current behavior**

1. Log in to Studio as an Admin or Staff user.  
2. Navigate to the Taxonomies page.  
3. Each imported taxonomy card shows a three-dot (⋮) vertical actions button.  
4. Clicking the three-dot button opens a dropdown with four options: Re-import, Export, Delete, Manage Organizations.  
5. Clicking the card body (anywhere outside the three-dot button) navigates to the taxonomy editing page, where tags can be browsed and edited.

There is no entry point from a taxonomy card into competency management flows.

**Requested change**

Add a dedicated entry point to the Competency Management page for competency-type taxonomies. All taxonomies — including competency taxonomies — must retain a clear path to the taxonomy editing page; the new option may not displace edit access for any taxonomy type.

The exact mapping of triggers to destinations (card click vs. three-dot menu option) is a design decision — see Open Questions. Two models are under consideration:

| Path | Option A | Option B |
| :---- | :---- | :---- |
| Primary (card click) | Taxonomy editing page for all taxonomy types. | Competency Management page for Taxonomies of Competency type. Tag Taxonomies still go to Taxonomy editing page. |
| Secondary (three-dot menu) | "Manage Competencies" option added for Taxonomies of Competency type. | "Edit Taxonomy" option added for Taxonomies of Competency type. |

The designs must make the fork between editing a taxonomy and managing competencies explicit and intuitive. Detailed design of the Competency Management page itself is out of scope as this has been handled previously and will be updated in future tickets/issues.

### Acceptance Criteria

This is a design spike. The deliverable is design artifacts and documented decisions, not working code. There is no Gherkin and no QA path.

- [ ] Navigation model decided (Option A or Option B — see Open Questions) and rationale documented.  
- [ ] Menu option label decided ("Manage Competencies", "Apply Competencies", or another term) and rationale documented.  
- [ ] Updated three-dot menu mockup showing the chosen navigation model in context with Re-import, Export, Delete, and Manage Organizations.  
- [ ] Flow diagram or annotated wireframe showing the two navigation paths branching from a taxonomy card (edit taxonomy vs. manage competencies).  
- [ ] High-level wireframe of the Competency Management page entry state.  
- [ ] Design artifacts published to Figma — designer to add link when complete.  
- [ ] All Open Questions resolved and documented before this ticket is closed.

### Open Questions

1. **Navigation model for competency taxonomies (designer, blocking):** Two options:  
     
   - Option A: Card click → taxonomy editing page; three-dot menu gains "Manage Competencies."  
   - Option B: Card click → Competency Management page; three-dot menu gains "Edit Taxonomy" (swapping which action is primary for competency taxonomies).

   

   Which model fits how operators will primarily use competency taxonomies day-to-day?

   

2. **Menu option label (designer):** "Manage Competencies", "Apply Competencies", or another term? Document rationale alongside the decision.

### Context for the Designer

The Taxonomies page in Studio (`frontend-app-authoring`) renders a card for each imported taxonomy. Each card has a three-dot actions menu (currently: Re-import, Export, Delete, Manage Organizations) and a clickable card body that navigates to the taxonomy editing page. As of ticket 5 (Frontend taxonomy type badge), competency taxonomies are visually distinguished from tag taxonomies by a badge, which is the context in which this new menu option will appear.

The two navigation paths this ticket introduces are materially different in intent: editing a taxonomy changes its tag structure, while managing competencies creates competency criteria groups and rules against content. The designs must prevent operators from landing in the wrong flow.

**Related tickets:**

- Ticket 5 — Frontend taxonomy type badge (provides the visual distinction between competency and tag taxonomy cards that contextualizes this menu option)  
- Future implementation ticket: "Add Manage Competencies option to taxonomy actions menu"  
- Future implementation ticket: "Competency Management page — initial implementation"
