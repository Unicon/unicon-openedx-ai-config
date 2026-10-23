# [FE] Add Taxonomy Type dropdown to taxonomy import flow

GitHub: https://github.com/openedx/openedx-core/issues/615 (#615, CLOSED)
Cached: 2026-10-22

## Use Case

As a Platform Administrator, I need to select a Taxonomy Type when importing a taxonomy so that the platform correctly stores the imported taxonomy as a Competency Taxonomy or a standard tag taxonomy.

---

## Description

Today, the taxonomy import workflow in Studio follows these steps:

1. Log in to Studio as an Admin or Staff user.  
2. Click on the **Taxonomies** tab.  
3. Click the **Import** button.  
4. Upload a JSON or CSV file in the required template format.  
5. Click **Continue**.  
6. The modal advances to a **"Populate Taxonomy Information"** step with two fields: Taxonomy Name and Taxonomy Description.  
7. Click **Import** to complete the process.

This issue adds a **Taxonomy Type** dropdown to step 6, beneath the existing Description field. The dropdown offers two user-selectable options: "Tags" (default) and "Competency". A third type ("System") is reserved for platform use and must not appear as a selectable option. The selected value is sent to the taxonomy import API endpoint as part of the import request when the user clicks **Import** in step 7\.

This ticket covers the dropdown UI, form state, and API payload only. Displaying the taxonomy type in the taxonomy list or detail views is out of scope and will be addressed in a future ticket (\#616). Until that display ticket ships, QA must verify backend storage of the taxonomy type via Postman.

**Dependency:** The import endpoint's support for `taxonomy_type` is implemented in \#614. That ticket must be merged before this frontend change can be verified end-to-end. The Postman-based GET verification in Acceptance Criteria (Scenarios 2 and 3\) additionally depends on \#618, which adds `taxonomy_type` to the GET response.

---

## Acceptance Criteria

Displaying the taxonomy type in the list or detail views is out of scope. Backend storage must be verified via Postman until the display ticket ships.

```
Scenario 1: Dropdown appears in the correct modal step with correct options
  Given the user has uploaded a taxonomy file and advanced to the "Populate Taxonomy Information" step
  Then a "Taxonomy Type" dropdown is visible below the Description field
  And "Tags" is selected by default
  And "Tags" and "Competency" are the only options in the dropdown
  And "System" is not present as an option
  And the dropdown label and option strings are rendered through the existing i18n message system (useIntl / intl.formatMessage), not hardcoded
  And the dropdown has a properly associated <label> and aria-* attributes consistent with the other fields in the wizard

Scenario 2: Importing with Competency type selected
  Given the user is on the "Populate Taxonomy Information" step
  And the user selects "Competency" from the Taxonomy Type dropdown
  When the user clicks "Import"
  Then the import completes successfully
  And the new taxonomy appears in the taxonomy list
  And [Postman, requires #618 merged] GET the new taxonomy returns taxonomy_type = "competency"

Scenario 3: Importing with Tags type (default or explicit selection)
  Given the user is on the "Populate Taxonomy Information" step
  And the Taxonomy Type dropdown is left at its default or set explicitly to "Tags"
  When the user clicks "Import"
  Then the import completes successfully
  And the new taxonomy appears in the taxonomy list
  And [Postman, requires #618 merged] GET the new taxonomy returns taxonomy_type = "tags"
```
---
## UX Designs

[Figma Link](https://www.figma.com/design/VhAdaucNQS49x0Afp9xPZw/Competency-Application?node-id=1061-13019&t=y4640jJ9EpAXIi0O-4)

<img width="4742" height="2442" alt="Image" src="https://github.com/user-attachments/assets/eb59bb8b-587c-4948-b83b-c09a0a67e62e" />

---

## Technical Notes

### Files to Create

None expected.

### Modified Files

| File | Nature of modification |
| :---- | :---- |
| `src/taxonomy/import-tags/ImportTagsWizard.jsx` | Add Taxonomy Type dropdown to `PopulateStep`; extend `taxonomyPopulateData` state |
| `src/taxonomy/data/apiHooks.ts` | Add `taxonomy_type` to the `FormData` POST payload in `useImportNewTaxonomy` |
| `src/taxonomy/data/types.ts` | Add `taxonomyType` to the relevant request payload type if one exists |
| `src/taxonomy/import-tags/messages.js` (confirm exact path) | Add i18n message definitions for the "Taxonomy Type" label and "Tags"/"Competency" option strings |
| `src/taxonomy/data/apiHooks.test.ts` (confirm exact path) | Add a unit test asserting `taxonomy_type` is included in the `FormData` payload for both dropdown selections |

### Implementation Notes

- **Dropdown placement:** The `PopulateStep` component (lines 183–220 of `ImportTagsWizard.jsx`) renders the Name and Description fields. Add the Taxonomy Type dropdown directly below the Description textarea, using the same UI component library patterns already present in the file. Options: "Tags" (default) and "Competency" only — do not include "System".  
- **State:** The `taxonomyPopulateData` state (lines 305–308) currently holds `{ taxonomyName, taxonomyDesc }`. Extend it with `taxonomyType: 'tags'` as the default. The existing change handler pattern (lines 189–199) works with an additional field without restructuring.  
- **API payload:** The `useImportNewTaxonomy` hook (lines 113–137 of `apiHooks.ts`) builds `FormData` and POSTs to `createTaxonomyFromImport()` (defined at `api.ts:95`). Always append `taxonomy_type` to the FormData — send `"competency"` or `"tags"` depending on the dropdown selection. The backend accepts both values explicitly; do not omit the field.  
- **i18n:** The dropdown label ("Taxonomy Type") and option strings ("Tags", "Competency") must go through the existing i18n infrastructure (`useIntl()` / `intl.formatMessage()`), matching the pattern already used for the Name and Description fields in `ImportTagsWizard.jsx`. Do not hardcode these strings; this is a required step, not optional.  
- **Accessibility:** The dropdown needs a properly associated `<label>` and `aria-*` attributes consistent with the existing form fields in the wizard. The paragon Select/Form component likely handles this by default — verify it does, don't assume.  
- **Testing:** Add a unit test for `useImportNewTaxonomy` asserting `taxonomy_type` is present in the submitted `FormData` for both the `"tags"` and `"competency"` selections.  
- **No new components needed.** The dropdown should reuse existing Select/Form patterns already present in the file.

### Example Resolution Prompt

In `frontend-app-authoring`, update the taxonomy import modal to add a Taxonomy Type dropdown. In `src/taxonomy/import-tags/ImportTagsWizard.jsx`, add a dropdown to the `PopulateStep` component (currently lines 183–220) below the Description textarea. Options: "Tags" (default) and "Competency" — do not include "System". Extend the `taxonomyPopulateData` state (currently lines 305–308) with `taxonomyType: 'tags'`. Route the dropdown's label and option strings through the existing `useIntl()` / `intl.formatMessage()` i18n infrastructure — do not hardcode them — and add the corresponding message definitions. Ensure the dropdown has a properly associated `<label>` and `aria-*` attributes consistent with the wizard's other fields. In `src/taxonomy/data/apiHooks.ts`, update `useImportNewTaxonomy` (lines 113–137) to always append `taxonomy_type` to the `FormData` sent to `createTaxonomyFromImport()`: send `"competency"` or `"tags"` based on the dropdown selection, and add a unit test asserting this field is present in the payload for both selections. Match the existing component and state-management patterns already in the file.  
