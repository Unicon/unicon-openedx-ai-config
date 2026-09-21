# [FE] Display Competency ID on the Competency Management page

GitHub: https://github.com/openedx/openedx-core/issues/680 (#680, CLOSED)
Cached: 2026-09-21

**Repo:** `frontend-app-authoring` (Studio MFE).

Build a new read-only page in Studio that shows one competency taxonomy's competencies as
an expand/collapse tree, with each competency's Competency ID next to it.

## Use Case

As a Platform Administrator, I want to open the Competency Management page for a competency
taxonomy and see its competencies in an expand/collapse (accordion) tree, each with its
Competency ID, so that I can browse and reference the taxonomy's competencies by their
stable IDs as the starting point for applying competency criteria.

## Acceptance Criteria

Frontend/QA-testable.

    Scenario: The page renders the taxonomy's competencies as a tree
      Given a competency taxonomy with nested competencies
      When a Platform Administrator opens its Competency Management page
      Then the page shows the taxonomy's competencies as a nested tree (root, groups, sub-competencies)

    Scenario: The tree opens with the taxonomy's top-level competencies visible
      Given a competency taxonomy with nested competencies
      When a Platform Administrator opens its Competency Management page
      Then the taxonomy root row is expanded, showing its top-level competencies
      And nodes below the top level are collapsed

    Scenario: Accordion expand/collapse
      Given the competency tree is displayed
      When the user collapses or expands a node (or uses Expand All / Collapse All)
      Then the node's children hide or show accordingly, with tree indentation intact

    Scenario: Competency ID is shown at every level and matches the source data
      Given competencies with external_id values
      When the tree is displayed
      Then each competency row shows its own Competency ID (external_id), on group and leaf nodes alike
      And each displayed ID equals that tag's external_id

    Scenario: Competency without an ID
      Given a competency whose external_id is empty or absent
      When the page loads
      Then that row shows no ID
      And no other competency's ID is shown

    Scenario: Read-only
      Given a user viewing the page
      Then the Competency Name and ID are read-only and there is no editing on the page

    Scenario: Small-screen / responsive
      Given the page at a narrow viewport
      Then the tree and each competency's ID remain readable and correctly associated, and the layout does not break

## Description

**Current state**

There is no Competency Management page and no `/taxonomy/:taxonomyId/competencies` route in
the MFE.

**Requested change**

Create the page and its route, and render on it:

1. The taxonomy's competencies as a nested expand/collapse tree (taxonomy root → groups →
   sub-competencies), including Expand All / Collapse All, reusing the existing tag
   tree-table rendering.
2. Each competency's Competency ID next to its row, at every level of the tree, read-only.

**Explicitly out of scope**

- Editing the Competency ID. 
- Any backend, API, or data-layer change.
- Sorting, filtering, or reordering competencies by ID.

[Figma Link](https://www.figma.com/design/VhAdaucNQS49x0Afp9xPZw/Competency-Application?node-id=1-3816&t=Ifrnzv9zzPSoMwse-1)

<img width="1349" height="977" alt="Image" src="https://github.com/user-attachments/assets/044f66cd-6403-4fb9-8f8e-5710d147bfc3" />


<details>
<summary>Technical Details</summary>

**Data Structures**

Nothing new. A tree row is already a `TagTreeNode`, which extends `TagData` and therefore
already carries `externalId` (the Competency ID) at every level of the tree.

**Logic**

The page reads the taxonomy id from its route, fetches that taxonomy's tags with the
existing `useTagListData` hook, and renders them with the existing tag tree-table, which
already provides the nesting and the accordion behavior. Adding the Competency ID is then a
display concern only: render each row's `externalId` in its own column, styled per the
Figma design.

Four decisions to respect:

- **Read-only.** Strip the tag-CRUD affordances the existing tree-table offers. This page
  never edits.
- **Empty Competency ID renders as nothing.** Many tags legitimately have no `external_id`.
  Handle that at the cell boundary so the string `undefined` can never reach the DOM.
- **Default expand state.** The root row starts expanded, so the taxonomy's top-level
  competencies are visible on load; nodes below the top level start collapsed. Set this
  explicitly rather than inheriting the tree-table's default, which is fully collapsed. On the
  Taxonomy Detail page that default is reasonable because top-level tags are already visible,
  but here the collapsed node is the taxonomy root itself, so a first-time visitor would see one
  row, the taxonomy's own name, and no competencies at all until they click.
- **Route ownership.** #663 also registers `/taxonomy/:taxonomyId/competencies` with a
  placeholder page, but it is sequenced later, so plan on creating the route here. If #663
  has landed first, reuse its route and replace the placeholder page instead.

## Files to create and modify

**New files**

| File | Purpose |
| --- | --- |
| `src/taxonomy/competency-management/CompetencyManagementPage.tsx` | The page: fetch the taxonomy's tags and render the competency tree |
| `src/taxonomy/competency-management/CompetencyTree.tsx` | *(optional)* the tree itself, if cleaner than inlining it in the page |
| `src/taxonomy/competency-management/messages.ts` | i18n strings |
| `src/taxonomy/competency-management/index.ts` | Public interface for the feature folder |
| co-located RTL tests | Cover the behavior listed in Technical Details |

**Modified files**

| File | Nature of modification |
| --- | --- |
| `src/index.jsx` | Register `/taxonomy/:taxonomyId/competencies` → `CompetencyManagementPage`, as a sibling of `/taxonomy/:taxonomyId` under the `TaxonomyLayout` route |

</details>
