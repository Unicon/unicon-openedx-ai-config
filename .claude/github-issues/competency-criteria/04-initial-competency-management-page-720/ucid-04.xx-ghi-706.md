# [FE] Import Competency Framework button on the Competency Management page

GitHub: https://github.com/openedx/openedx-core/issues/706 (#706, OPEN)
Cached: 2026-09-21

## Use Case

As a curriculum author managing a competency taxonomy on the Competency Management page, I want to import a competency framework from that page with the taxonomy type already set to Competency, so that I don't have to leave for the general Taxonomies list "Import" action.

## Acceptance Criteria

Frontend/QA-testable.

    Scenario: Button is visible on the Competency Management page
      Given I am on the Competency Management page for a taxonomy
      And I have permission to create taxonomies
      Then I see an "Import Competency Framework" action in the page's action toolbar

    Scenario: Button is hidden without create-taxonomy permission
      Given I am on the Competency Management page for a taxonomy
      And I do not have permission to create taxonomies
      Then I do not see the "Import Competency Framework" action

    Scenario: Clicking the button opens the import wizard with type pre-set to Competency
      Given I am on the Competency Management page for a taxonomy
      When I select "Import Competency Framework"
      Then the import wizard opens on the upload step
      And no export/plan/confirm steps are shown
      When I proceed to the populate step
      Then the taxonomy-type dropdown field is pre-set to "Competency"
      And the dropdown can be selected to change the taxonomy-type to either "Competency" or "Taxonomy"

    Scenario: Successful import creates a new taxonomy and navigates to it
      Given I have opened the import wizard from "Import Competency Framework"
      And I have uploaded a valid framework file
      And I have entered both a taxonomy name and a description
      When I confirm the import
      Then a new taxonomy of type Competency is created
      And I am navigated to that new taxonomy's Competency Management page

    Scenario: Cancelling the wizard makes no changes
      Given I have opened the import wizard from "Import Competency Framework"
      When I close the wizard without completing it
      Then no taxonomy is created
      And I remain on the original taxonomy's Competency Management page

Failure cases.

    Scenario: Import button stays disabled until name and description are both entered
      Given I have opened the import wizard from "Import Competency Framework"
      And I have uploaded a valid framework file
      When I fill in only the taxonomy name
      Then the Import action remains disabled
      And it becomes enabled only once the description is also filled in

    Scenario: Unsupported file type is silently rejected
      Given I have opened the import wizard from "Import Competency Framework"
      When I select a file that is not .csv or .json
      Then the upload step's continue action remains disabled
      And no import request is sent
      And no explanatory message is shown, matching the Taxonomies list behavior

    Scenario: Import cannot be double-submitted
      Given I have uploaded a valid file and entered a name and description
      When I confirm the import
      Then the Import button shows its pending state
      And the dialog cannot be interacted with until the request settles
      And exactly one POST to the import endpoint is made

    Scenario: Backend rejects the import
      Given I have opened the import wizard from "Import Competency Framework"
      And the import endpoint will return an error
      When I confirm the import
      Then the wizard closes
      And a dismissible page-level alert titled "Import error" appears
      And no new taxonomy is created
      And I remain on the original taxonomy's Competency Management page
      And I am not navigated anywhere

    Scenario: Retrying after a failed import starts over
      Given an import from "Import Competency Framework" has just failed
      When I select "Import Competency Framework" again
      Then the wizard opens on the upload step with no file selected
      And the name and description fields are empty
      And the taxonomy-type field is again pre-set to "Competency"
      And the dropdown can be selected to change the taxonomy-type to either "Competency" or "Taxonomy"

    Scenario: Import fails because the file itself is invalid
      Given I have uploaded a .csv or .json file the backend cannot parse
      When I confirm the import
      Then the same failure handling applies as for any other backend error
      And no partially populated taxonomy is left behind

### Top right of the header

<img width="3548" height="2574" alt="Image" src="https://github.com/user-attachments/assets/7cbdc67b-953f-4f2b-aa29-509d979d1d42" />

## Description

**Current state**

Taxonomy import today has two entry points, both opening the same `ImportTagsWizard`, branched by a `reimport` boolean the caller supplies (the wizard has no in-modal choice between the two):

- **Taxonomies list page** (`TaxonomyListPage.tsx`): the "Import" button opens `ImportTagsWizard` with no `taxonomy` and no `reimport` prop, runs the `upload` → `populate` steps, and on submit calls `useImportNewTaxonomy()` → `POST /api/content_tagging/v1/taxonomies/import/`. It always **creates a brand-new taxonomy**. The `populate` step collects only `taxonomyName` and `taxonomyDesc`.
- **Taxonomy detail Actions menu** (`TaxonomyMenu.jsx`): the "Import" item opens `ImportTagsWizard` with `taxonomy` and `reimport`, runs `export` → `upload` → `plan` → `confirm` via `useImportPlan`/`useImportTags` → `PUT /api/content_tagging/v1/taxonomies/{id}/tags/import/`, and **replaces tags in the existing taxonomy** (with a warning that non-matching tags are removed).

**Current failure behavior of the create-new import** (the baseline this ticket must match, all in `src/taxonomy/import-tags/ImportTagsWizard.jsx`):

- A file whose extension is not `.csv` or `.json` never reaches the wizard's `handleFileLoad`; the `Dropzone` (line 123-126) rejects it and the continue action stays disabled (line 490). The wizard renders no explanatory message for a rejected file.
- The populate step's Import button is disabled until **both** name and description are filled (line 506), not name alone.
- While the request is in flight, `disableDialog()` puts a transparent overlay over the whole dialog (line 434-437) and the `LoadingButton` goes to its pending state, so the import cannot be double-submitted.
- On failure, `importNewTaxonomy`'s `finally` block calls `onClose()` unconditionally (line 333-336), so the wizard closes and unmounts on error exactly as it does on success. `TaxonomyListPage.tsx:39-44` mounts it only while the modal flag is set, so `file`, `taxonomyName`, `taxonomyDesc`, and `currentStep` are all destroyed. The error surfaces as a dismissible page-level Paragon `Alert` titled "Import error", rendered by `TaxonomyLayout.tsx:27-32` above the page, not inside the dialog. There is no fix-and-retry in place: the user reopens the wizard and re-enters everything.
- The message in that alert is the raw Axios string (`"Request failed with status code 400"`), not the backend's message, because `useImportNewTaxonomy` (`src/taxonomy/data/apiHooks.ts:113-137`) does not wrap its errors in `getApiErrorMessage` the way the reimport path's `useImportTags`/`useImportPlan` do (`apiHooks.ts:149-154`, `:181-186`). `AlertError` dumps `error.response.data` as a `<pre>` JSON block below the title when the response has a body. The existing test at `ImportTagsWizard.test.jsx:357-365` pins this generic-message behavior in place.

There is **no taxonomy "type" concept in the code today**: `TaxonomyData` (`src/taxonomy/data/types.ts:2-18`) has no type field, the populate step renders only name and description controls (`ImportTagsWizard.jsx:183-228`), and `useImportNewTaxonomy`'s payload (`taxonomy_name`, `taxonomy_description`, `file`) carries no type. #615 adds that control, and #614 makes the backend accept its value.

**Requested change**

Add an "Import Competency Framework" action to the Competency Management page's header toolbar (following whatever action-toolbar pattern #680 establishes; mirror the `SubHeader` + `ActionRow` convention `TaxonomyDetailPage.jsx` uses if #680 hasn't defined its own). Clicking it opens the create-new `ImportTagsWizard` flow — no `taxonomy`, no `reimport` prop, the same code path the Taxonomies list "Import" button uses — with the taxonomy-type control (added by #615) **pre-selected to "Competency" and locked** for this entry point. On success it creates a brand-new Competency-type taxonomy via `useImportNewTaxonomy` and navigates the user to that new taxonomy's Competency Management page.

Failure handling is parity, not improvement: because this entry point reuses `ImportTagsWizard` and `useImportNewTaxonomy` unchanged, every failure case behaves exactly as it does from the Taxonomies list, including the rough edges documented above (wizard closes on error, page-level alert, generic error text, no in-place retry). The one difference is where the user lands: the Competency Management page they started on, not the Taxonomies list. Do not "fix" the shared failure behavior here.

<details>
<summary>Explicitly out of scope</summary>

- Building #680's page, route, or competency tree; and #663's entry point into that page.
- #614's and #615's own work: defining the type field's shape/enum, adding it to `TaxonomyData`, rendering the type control, and making the backend accept and persist it. This ticket only presets and locks that control once it exists.
- Any change to `ImportTagsWizard`'s existing `reimport=true` (replace-tags) path, its file parsing, or the import backend/pipeline.
- Letting the user pick a taxonomy type other than Competency from this entry point.
- Improving the shared import failure UX: surfacing the backend's real error message on the create-new path, keeping the wizard open on error, or adding a rejected-file message. All of that is shared with the Taxonomies list "Import" button and belongs in its own ticket.
</details>

<details>
<summary>Technical Notes</summary>


### Files to Modify

| File | Change |
| --- | --- |
| `src/taxonomy/competency-management/CompetencyManagementPage.tsx` *(placeholder name — confirm against #680)* | Add an "Import Competency Framework" item to the page's action toolbar; render `ImportTagsWizard` with no `taxonomy`/`reimport` prop plus the locked-type prop below. |
| `src/taxonomy/competency-management/messages.ts` *(placeholder — confirm against #680)* | `defineMessages` entry for the button/menu-item label. |
| `src/taxonomy/import-tags/ImportTagsWizard.jsx` | Add an optional prop (e.g. `initialTaxonomyType` + `lockTaxonomyType`, or equivalent per #615's actual field name) so the populate step's type control, once #615 adds it, can be pre-filled to `"competency"` and disabled when set by this caller. Existing callers that omit the prop are unaffected. Do not touch `importNewTaxonomy`'s `try`/`catch`/`finally` (line 312-337): its failure behavior is the parity baseline. |
| `src/taxonomy/import-tags/messages.ts` | Copy for the locked-type state if needed (e.g. "Type is set to Competency for this import"). |
| `src/taxonomy/data/apiHooks.ts` | Only if #615 does not already wire `type` through `useImportNewTaxonomy`'s `FormData`/payload, add it there. Leave the hook's error handling alone: wrapping it in `getApiErrorMessage` would change the Taxonomies list flow too and break the test at `ImportTagsWizard.test.jsx:357-365`. |


### Example Resolution Prompt

> Add an "Import Competency Framework" action to the Competency Management page in `frontend-app-authoring` (built by #680 — confirm its actual page component path first; if #680 hasn't defined its own header-actions area, model it on `src/taxonomy/taxonomy-detail/TaxonomyDetailPage.jsx`'s `SubHeader`/`ActionRow` pattern). The action opens `src/taxonomy/import-tags/ImportTagsWizard.jsx` on its **create-new** path: render it with no `taxonomy` and no `reimport` prop, identical to `src/taxonomy/TaxonomyListPage.tsx`, so it resolves to `useImportNewTaxonomy()` (`src/taxonomy/data/apiHooks.ts`) → `POST /api/content_tagging/v1/taxonomies/import/`, not `useImportTags`/`useImportPlan`. Add an optional prop to `ImportTagsWizard` (match the field name #615 introduces) that pre-fills and disables the type control in the populate step with value `"competency"`; existing callers that don't pass it are unaffected. On success only, after `mutateAsync` resolves, navigate to the new taxonomy's Competency Management page (`/taxonomy/:taxonomyId/competencies`, using the new id from the mutation response); never navigate from `onClose`, which also fires on failure. Leave all failure handling exactly as it is: `importNewTaxonomy`'s existing `catch` calls `setAlertError` and its `finally` closes the wizard, and that page-level "Import error" alert is the required behavior here, identical to the Taxonomies list. Do not add a local error handler, do not keep the modal open on error, and do not wrap `useImportNewTaxonomy` in `getApiErrorMessage`. Gate visibility with the same permission check `TaxonomyListPage.tsx` uses for its "Import" button. Use `defineMessages` for new copy and match the existing `import-tags` component's `data-testid` convention. Add tests following `ImportTagsWizard.test.jsx`'s `it.each(['success', 'error'])` pattern, with the error case asserting the alert fired and `navigate` did not. Do not touch the `reimport=true` path, file parsing, or the import backend.

**Issue #706. Subtask of #680** (the Competency Management page at `/taxonomy/:taxonomyId/competencies`). Frontend, `frontend-app-authoring` (`src/taxonomy/`).

**Blocked by:** **#614** (BE) and **#615** (FE), the pair that introduces a taxonomy type on the create/import path. #614 is what actually makes "import as Competency" stick: presetting the type in the frontend does nothing unless the backend accepts and persists it on `POST /api/content_tagging/v1/taxonomies/import/`. #615 adds the Taxonomy Type control to the import wizard's populate step, which is the control this ticket presets and locks. Both are load-bearing. Also **#680** (the page this button sits on). **Related:** #663 (the entry point that reaches #680's page).

</details>
