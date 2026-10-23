# [FE] Add taxonomy type badge to Taxonomies page

GitHub: https://github.com/openedx/openedx-core/issues/616 (#616, CLOSED)
Cached: 2026-10-22

## Use Case

As a Platform Administrator, I need to see a taxonomy type badge on each taxonomy card on the Taxonomies page so that I can quickly distinguish Competency Taxonomies from standard tag taxonomies at a glance without leaving the page.

---

## Description

This issue updates every taxonomy card to always display exactly one type badge:

- **"Competency"** — new badge for Competency Taxonomies, visually distinct color from System-level
- **"Tags"** — new badge for standard tag taxonomies

The badge is determined by the`taxonomyType` field being added to the API response (added by #618). The priority order is:

1. If `taxonomyType` is `"competency"` → show "Competency" badge
3. Otherwise → show "Tags" badge

This ticket is the display counterpart to the import dropdown added in #615 and removes the need for Postman verification of taxonomy type after import.

**Dependency:** Requires #618 (GET endpoint returning `taxonomy_type`) and #630 (verifies `TaxonomyOrgSerializer` in edx-platform passes `taxonomy_type` through in the `/api/content_tagging/v1/taxonomies/` response) to be merged first.

---

## Acceptance Criteria

**Scenario 1: Competency taxonomy shows Competency badge**

```
Given a Competency Taxonomy exists on the platform
When I navigate to the Taxonomies page
Then the taxonomy card displays a "Competency" icon
```

**Scenario 2: Standard tag taxonomy shows Tags badge**

```
Given a standard tag taxonomy exists on the platform
When I navigate to the Taxonomies page
Then the taxonomy card displays a "Tags" icon
```

**Scenario 3: Every taxonomy card shows exactly one type badge**

```
Given multiple taxonomies of different types exist on the platform
When I navigate to the Taxonomies page
Then each taxonomy card displays exactly one type icon
And no taxonomy card displays more than one type icon
```

---
## UX Designs

[Figma Link](https://www.figma.com/design/VhAdaucNQS49x0Afp9xPZw/Competency-Application?node-id=1114-16717&t=xASI6SV3J1gNYlzA-4)

<img width="947" height="371" alt="Image" src="https://github.com/user-attachments/assets/28b44b08-c402-4a75-9cbe-84cc6d2497d1" />

---

## Technical Notes

Note that this section was drafted before the system taxonomy type was removed. Ignore anything below related to the system type taxonomy.

### Files to Create

| File | Purpose |
| :---- | :---- |
| `src/taxonomy/taxonomy-card/TaxonomyTypeBadge.jsx` | New badge component that accepts `systemDefined` and `taxonomyType` props and renders the correct label and color |

### Modified Files

| File | Nature of modification |
| :---- | :---- |
| `src/taxonomy/data/types.ts` | Add `taxonomyType: 'competency' | 'tags'` to `TaxonomyData` interface |
| `src/taxonomy/taxonomy-card/index.jsx` | Replace conditional `SystemDefinedBadge` rendering (lines 122–128) with `TaxonomyTypeBadge`, passing both `systemDefined` and `taxonomyType` |

### Implementation Notes

- **`taxonomyType` is not yet in the frontend data layer.** Add `taxonomyType: 'competency' | 'tags'` to the `TaxonomyData` interface in `types.ts` (lines 2–18). The `camelCaseObject()` call in the API hook automatically converts `taxonomy_type` from the response to `taxonomyType` — no hook changes needed.
- **Badge priority logic belongs in `TaxonomyTypeBadge`.** The component receives both `systemDefined: boolean` and `taxonomyType: 'competency' | 'tags'` and applies the priority order: System-level first, then Competency, then Tags. Keeping the logic inside the component makes it testable in isolation.
- **Visual reference for the new component:** Use the same badge/pill UI component already used by `src/taxonomy/system-defined-badge/index.jsx` as the pattern. "System-level" retains its existing styling; "Competency" uses a distinct color variant; "Tags" uses a neutral color variant.
- **Card update:** `TaxonomyCard` (`taxonomy-card/index.jsx`, lines 122–128) currently conditionally renders `<SystemDefinedBadge />` when `showSystemBadge` is true. Replace this with `<TaxonomyTypeBadge systemDefined={systemDefined} taxonomyType={taxonomyType} />` — always rendered, no conditional, since every taxonomy now shows a badge.
- **`systemDefined` is not removed.** It remains on the interface and in existing code. This ticket does not clean it up; that is a separate concern.
- **`taxonomy_type` passthrough in edx-platform:** The frontend calls `/api/content_tagging/v1/taxonomies/`. Verify that `TaxonomyOrgSerializer` (`edx-platform/openedx/core/djangoapps/content_tagging/rest_api/v1/serializers.py`, lines 70–99) includes `taxonomy_type` in its response — this is covered by #630, but confirm it is merged and working before testing this ticket.

### Example Resolution Prompt

In `frontend-app-authoring`, add taxonomy type badges to the Taxonomies page. In `src/taxonomy/data/types.ts`, add `taxonomyType: 'competency' | 'tags'` to the `TaxonomyData` interface. Create `src/taxonomy/taxonomy-card/TaxonomyTypeBadge.jsx` that accepts `systemDefined: boolean` and `taxonomyType: 'competency' | 'tags'` props and renders exactly one badge: "System-level" if `systemDefined` is true, "Competency" if `taxonomyType === 'competency'`, or "Tags" otherwise. Use the same badge/pill UI component as `src/taxonomy/system-defined-badge/index.jsx` as the visual pattern, with a distinct color variant for "Competency" and a neutral variant for "Tags". In `src/taxonomy/taxonomy-card/index.jsx`, replace the conditional `<SystemDefinedBadge />` at lines 122–128 with `<TaxonomyTypeBadge systemDefined={systemDefined} taxonomyType={taxonomyType} />` — always rendered, no conditional. Do not remove `systemDefined` from the interface or any existing code.
