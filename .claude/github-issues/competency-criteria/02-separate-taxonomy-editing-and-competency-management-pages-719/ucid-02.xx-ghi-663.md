# [FE] Add "Apply Competencies" entry point to the taxonomy card menu and footer, with a placeholder Competency Management page

GitHub: https://github.com/openedx/openedx-core/issues/663 (#663, CLOSED)
Cached: 2026-10-22

**Blocked by:** \#616, "\[FE\] Add taxonomy type badge to Taxonomies page" (open, unmerged). \#616 owns the `TaxonomyData` field this ticket's conditional-visibility logic keys off — that field does not exist in `frontend-app-authoring` today. \#616 is itself blocked on backend issues \#618 and \#630 (unmerged). This ticket is ready for development but cannot be implemented, demoed, or tested until \#616 lands.

Repo: `frontend-app-authoring` (Studio MFE). No backend or `openedx-core` change.

## Use Case

As a Studio Admin or Staff user managing a Competency-type taxonomy, I want an "Apply Competencies" action available directly from the Taxonomies page — as an item in the taxonomy card's actions menu, and as a standalone card-footer button — so that I can navigate straight to that taxonomy's Competency Management page in one click, without confusing this action with the taxonomy tag-editing flow that the unchanged card click already opens.

## Description

**Current state**

1. Log in to Studio as an Admin or Staff user and navigate to the Taxonomies page.  
2. Each imported taxonomy card shows a three-dot (⋮) actions button.  
3. Clicking the three-dot button opens a dropdown with four items, in this order: Re-import, Export, Delete, Manage Organizations.  
4. Clicking the card body anywhere outside the three-dot button navigates to the Taxonomy Editing page (tag browsing/editing) — identical behavior for every taxonomy type.  
5. Taxonomies carry a type (Tag or Competency). The field and its visual badge are being delivered by a separate ticket, \#616, which is currently open and itself blocked on unmerged backend issues \#618 and \#630.  
6. There is no entry point from a taxonomy card into competency management. Neither the menu nor the card click leads to competency criteria authoring today. No Competency Management page exists anywhere in the MFE.

**Requested change**

- Card click behavior is **unchanged** for all taxonomy types: it continues to route to the Taxonomy Editing page. No "Edit Taxonomy" menu item is added — this was considered during design (\#622) and explicitly rejected in favor of leaving the card click alone.  
- Exactly one new item, **"Apply Competencies,"** is appended to the three-dot menu (final order: Re-import, Export, Delete, Manage Organizations, Apply Competencies), rendered only when the taxonomy's type is Competency. Tag-type taxonomies keep exactly the original four items. The label was deliberately chosen over "Manage Competencies" during \#622's design discussion, to distinguish this action from the tag-editing the existing Taxonomy Editor already does.  
- For Competency-type taxonomies only, the card footer additionally gains a standalone "Apply Competencies" button. Both surfaces navigate to the same destination for the same taxonomy — no additional taxonomy-selection step.  
- A new route, `/taxonomy/:taxonomyId/competencies`, and a content-empty placeholder page (breadcrumb \+ title only) are added as the shared destination, so both entry points land somewhere real and testable.  
- Gating uses the existing `canTagObject` permission — no new permission tier.

**Explicitly out of scope**

- The Competency Management page's actual content: the taxonomy-switcher dropdown and hierarchical TreeView shown in \#622's rough wireframe. \#622 itself names a separate future ticket, "Competency Management page — initial implementation," to own this.  
- Any entry point on the Taxonomy Editing (detail) page's own header. This was floated during \#622's discussion but does not appear in the final signed-off design mocks — only the Taxonomies list-page card is affected.  
- The taxonomy-type field and its visual badge (\#616) and the backend field plumbing it depends on (\#618, \#630). This ticket consumes that data; it does not build it.  
- Defensive handling for a Tag-type taxonomy's id typed directly into `/taxonomy/:taxonomyId/competencies`. No operator-facing path produces this URL for a Tag taxonomy; revisit if it becomes a real issue once the destination page has real content.

## Acceptance Criteria

```
Scenario: Competency-type taxonomy card shows the new menu item
  Given I am logged in to Studio as an Admin or Staff user
  And a taxonomy of type Competency exists on the Taxonomies page
  When I open the taxonomy card's three-dot actions menu
  Then I see five items in order: Re-import, Export, Delete, Manage Organizations, Apply Competencies

Scenario: Tag-type taxonomy card menu is unaffected
  Given a taxonomy of type Tag exists on the Taxonomies page
  When I open that taxonomy card's three-dot actions menu
  Then I see exactly the original four items
  And "Apply Competencies" does not appear

Scenario: Card click still opens the Taxonomy Editing page, regardless of type
  Given a taxonomy card of either type exists on the Taxonomies page
  When I click the card body outside the three-dot button
  Then I am taken to the Taxonomy Editing page for that taxonomy, unchanged from before this ticket

Scenario: Competency-type card shows a footer "Apply Competencies" button
  Given a taxonomy of type Competency exists
  Then its card footer displays an "Apply Competencies" button
  And a Tag-type taxonomy's card footer displays no such button

Scenario: Menu item navigates to the Competency Management page
  Given a taxonomy of type Competency exists
  When I select "Apply Competencies" from its three-dot menu
  Then I am navigated to /taxonomy/:taxonomyId/competencies for that specific taxonomy, with no extra taxonomy-selection step
  And the page renders a breadcrumb and title; page content beyond that is out of scope for this ticket

Scenario: Footer button reaches the same destination as the menu item
  Given a taxonomy of type Competency exists
  When I click the card-footer "Apply Competencies" button
  Then I land on the same route and taxonomy scope that the menu item would produce

Scenario: User without the required permission
  Given I am logged in as a user without `canTagObject` permission on a Competency-type taxonomy
  When I view that taxonomy's card
  Then "Apply Competencies" does not appear in the menu or as a footer button

Scenario: Small-screen rendering
  Given I view the Taxonomies page on a small screen
  When a Competency-type card renders
  Then the footer button and five-item menu remain usable, consistent with the existing Paragon Card.Footer pattern used elsewhere in this repo (e.g. GalleryCard)
```

## UX Designs

[Figma link](https://www.figma.com/design/VhAdaucNQS49x0Afp9xPZw/Competency-Application?node-id=1076-12821&t=y4640jJ9EpAXIi0O-4)

<img width="1880" height="718" alt="Image" src="https://github.com/user-attachments/assets/e18e5ea0-ac02-4684-9104-7612eba81918" />

## Open Questions

- **\[BLOCKING, owner: implementer \+ \#616's author\]** What exact field/shape will \#616 add to `TaxonomyData` for taxonomy type (e.g. `taxonomyType: 'tag' | 'competency'`, a `taxonomyClass` enum, or a boolean)? This is the literal predicate every conditional in this ticket keys off. Per team decision, coordinate directly with \#616's author now rather than waiting for \#616 to merge, since this ticket is \#616's first real consumer — getting the shape wrong here means revising every file in the Files to Modify table below. Resolve and document the field name as a comment on this ticket before implementation starts; update the Files to Modify table with the real name at that point.

## Context

- **Design source:** openedx-core issue \#622, "\[UXD\] Create UX designs for taxonomy actions menu with Apply Competencies and Edit Taxonomy options" — in Final Axim Review. Read it for the label rationale ("Apply Competencies" over "Manage Competencies") and the click-pattern decision (card click unchanged for all types).  
- **Hard dependency:** \#616, "Frontend taxonomy type badge" — open, blocked on backend \#618 and \#630 (unmerged). Confirmed directly against `frontend-app-authoring` HEAD: `TaxonomyData` (`src/taxonomy/data/types.ts:2-18`) has no type field today.  
- **Related, closed:** \#615, "\[FE\] Add Taxonomy Type dropdown to taxonomy import flow" — likely origin of the settable taxonomy-type field \#616 surfaces on the frontend.  
- **Frontend conventions:**new strings need `defineMessages` i18n entries following the `course-authoring.taxonomy-menu.<action>.label` convention already used in `src/taxonomy/taxonomy-menu/messages.ts`.  
- **Code, confirmed against `frontend-app-authoring` HEAD:**  
  - `src/taxonomy/taxonomy-menu/TaxonomyMenu.jsx` — the existing 4-item menu. Items are a `{title, action, show}` map (`pickBy`\-filtered), rendered as `Dropdown.Item`s. `useNavigate` is already imported (line 14\) but unused; every existing `action` currently opens a modal via `useToggle`. "Apply Competencies" is the first item whose `action` navigates.  
  - `src/taxonomy/taxonomy-menu/messages.ts` — i18n id convention: `course-authoring.taxonomy-menu.<action>.label`.  
  - `src/taxonomy/taxonomy-card/index.jsx` — the card: `Card.Header` carries `TaxonomyMenu` as `actions`; `Card.Body` holds the description. No `Card.Footer` today.  
  - `src/taxonomy/taxonomy-detail/TaxonomyDetailPage.jsx` — the pattern to mirror for the new placeholder page: `useParams` → `useTaxonomyDetails(taxonomyId)` → `Loading`/`ConnectionErrorAlert` guards → `Breadcrumb` \+ `Container`.  
  - `src/taxonomy/TaxonomyLayout.tsx` — chrome host (`Header`, `StudioFooterSlot`, `Toast`, `TaxonomyContext`) via `<Outlet/>`; any sibling route added under it inherits this chrome for free.  
  - `src/files-and-videos/generic/table-components/GalleryCard.jsx:80-85` — existing in-repo precedent for Paragon `Card.Footer`, confirming it's already a supported, used pattern, just not yet in `taxonomy-card`.  
  - `src/index.jsx:104-116` — current taxonomy routes, gated by `getConfig().ENABLE_TAGGING_TAXONOMY_PAGES === 'true'`.

## Technical Notes

### Files to Create

| File | Purpose |
| :---- | :---- |
| `src/taxonomy/competency-management/index.ts` | Public interface exporting `CompetencyManagementPage`, per this feature's module-boundary convention |
| `src/taxonomy/competency-management/CompetencyManagementPage.tsx` | Placeholder page: breadcrumb (Taxonomies → taxonomy name → Manage & Apply Competencies), fetches the taxonomy via `useTaxonomyDetails`, empty-state body only — no TreeView/switcher |
| `src/taxonomy/competency-management/messages.ts` | i18n strings for the placeholder page |
| `src/taxonomy/competency-management/CompetencyManagementPage.test.tsx` | RTL tests mirroring `TaxonomyDetailPage.test.jsx` (loading/error/happy path) |

### Files to Modify

| File | Nature of modification |
| :---- | :---- |
| `src/taxonomy/taxonomy-menu/TaxonomyMenu.jsx` | Add a 5th `menuItems` entry, `applyCompetencies`, after `manageOrgs`; `action` calls the already-imported `navigate(\`/taxonomy/${taxonomy.id}/competencies\`)`;` show`keyed off the taxonomy-type field #616 adds (real field name pending — see Open Questions). Extend the`taxonomy`PropTypes/JSDoc`Pick\<TaxonomyData, …\>\` to include it. |
| `src/taxonomy/taxonomy-menu/messages.ts` | Add `applyCompetenciesMenu` (`id: course-authoring.taxonomy-menu.apply-competencies.label`, `defaultMessage: 'Apply Competencies'`) |
| `src/taxonomy/taxonomy-menu/TaxonomyMenu.test.tsx` | Add Competency-type and Tag-type fixtures; assert conditional render and that clicking navigates |
| `src/taxonomy/taxonomy-card/index.jsx` | Destructure the new type field from `original`; add `<Card.Footer>` (after `Card.Body`) rendered only for Competency-type, containing a `Button as={NavLink}` to the same route as the menu item |
| `src/taxonomy/taxonomy-card/messages.ts` | Add `applyCompetenciesButton` message |
| `src/taxonomy/taxonomy-card/TaxonomyCard.test.jsx` | Add Competency/Tag fixtures; assert footer button visibility and link target |
| `src/index.jsx` | Inside the existing `ENABLE_TAGGING_TAXONOMY_PAGES` block, add `<Route path="/taxonomy/:taxonomyId/competencies" element={<CompetencyManagementPage />} />` as a sibling of the existing `/taxonomy/:taxonomyId` route |
| `src/taxonomy/index.ts` | Re-export `CompetencyManagementPage` alongside `TaxonomyDetailPage`/`TaxonomyListPage`/`TaxonomyLayout` |

Not modified here: `src/taxonomy/data/types.ts` — the type field is \#616's contract to add; this ticket only consumes it.

### Implementation Notes

New sibling route under the existing `TaxonomyLayout`, inheriting its chrome via the existing `<Outlet/>`, with a deliberately empty-content page. This was chosen over two alternatives: reusing/stubbing the existing `TaxonomyDetailPage` route (rejected — \#622's whole point was to make editing-a-taxonomy and managing-competencies explicitly separate flows, so folding them back into one route would undo that), and a modal mirroring `ManageOrgsModal` (rejected — the accepted design is a full page with breadcrumbs and, eventually, a taxonomy switcher and tree; that's page-shaped UI, and the future ticket is already named "Competency Management **page**").

Add one shared predicate (e.g. `isCompetencyTaxonomy(taxonomy)`) rather than repeating the type comparison in both `TaxonomyMenu` and `TaxonomyCard`. \#616 should add this predicate as part of shipping the type field, since it needs the same check internally for its badge; this ticket imports it rather than inventing a second one.

This is MFE-only: no backend or `openedx-core` change, no `.importlinter` concern, no cross-feature import — everything stays inside the `taxonomy` feature and is consumed through its own `index.ts`. No ADR is warranted; this is UI wiring, not a new contract or data model.

**Hard dependency, stated plainly:** none of this is implementable, demoable, or testable until \#616 lands the type field on `TaxonomyData` and its backend prerequisites (\#618, \#630) ship first.

### Example Resolution Prompt

Implement the "Apply Competencies" entry points on Studio's Taxonomies page in `frontend-app-authoring`. Prerequisite: the taxonomy-type field and shared predicate that issue \#616 adds to `TaxonomyData` (`src/taxonomy/data/types.ts`) must exist first — confirm its real name and import \#616's predicate rather than inventing a second one; this prompt uses `isCompetencyTaxonomy(taxonomy)` as a placeholder name.

1. In `src/taxonomy/taxonomy-menu/TaxonomyMenu.jsx`, add a 5th entry to the `menuItems` object after `manageOrgs`, keyed `applyCompetencies`: `{ title: intl.formatMessage(messages.applyCompetenciesMenu), action: () => navigate(\`/taxonomy/${taxonomy.id}/competencies\`), show: isCompetencyTaxonomy(taxonomy) }`.` navigate`is already available via`useNavigate()`in this file. Extend the`taxonomy`PropTypes shape and the`Pick\<TaxonomyData, …\>\` JSDoc.  
2. In `src/taxonomy/taxonomy-menu/messages.ts`, add `applyCompetenciesMenu` (`id: course-authoring.taxonomy-menu.apply-competencies.label`, `defaultMessage: 'Apply Competencies'`).  
3. In `src/taxonomy/taxonomy-card/index.jsx`, destructure the type field from `original`, and add a `<Card.Footer>` (see `src/files-and-videos/generic/table-components/GalleryCard.jsx` for the existing in-repo `Card.Footer` pattern) right after `<Card.Body>`, rendered only when `isCompetencyTaxonomy(original)`, containing `<Button as={NavLink} to={\`/taxonomy/${id}/competencies\`} variant="primary"\>{intl.formatMessage(messages.applyCompetenciesButton)}\`.  
4. In `src/taxonomy/taxonomy-card/messages.ts`, add `applyCompetenciesButton`.  
5. Create `src/taxonomy/competency-management/` (`index.ts`, `CompetencyManagementPage.tsx`, `messages.ts`, test file). Mirror `src/taxonomy/taxonomy-detail/TaxonomyDetailPage.jsx`'s data shape (`useParams`, `useTaxonomyDetails(taxonomyId)`, `Loading`/`ConnectionErrorAlert` guards, `Breadcrumb`). Render only a breadcrumb, a title, and a placeholder body — no TreeView, no taxonomy switcher; those belong to the separate "Competency Management page — initial implementation" ticket.  
6. In `src/index.jsx`, inside the existing `getConfig().ENABLE_TAGGING_TAXONOMY_PAGES === 'true'` block, add `<Route path="/taxonomy/:taxonomyId/competencies" element={<CompetencyManagementPage />} />` as a sibling of `/taxonomy/:taxonomyId`; re-export the page from `src/taxonomy/index.ts`.  
7. Extend `TaxonomyMenu.test.tsx` and `TaxonomyCard.test.jsx` with Competency-type and Tag-type fixtures asserting conditional rendering both ways; add `CompetencyManagementPage.test.tsx` mirroring `TaxonomyDetailPage.test.jsx`.

Do not touch `src/taxonomy/data/types.ts`, any backend code, or `openedx-core` — this ticket only consumes the type field and predicate \#616 introduces.  
