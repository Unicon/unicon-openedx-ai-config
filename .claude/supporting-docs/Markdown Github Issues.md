# 1.1

## Use Case

Competency-Based Education (CBE) programs require learners to *demonstrate* mastery of specific competencies, not just complete coursework. Open edX currently has no way to define or evaluate the rules that determine whether a learner has demonstrated a competency — for example, "a learner must score 75% or higher on Assignment 1 OR Assignment 2 to demonstrate the Writing Poetry competency."

This issue implements the foundational database layer that makes the following possible:

- Course Authors and Platform Administrators can define competency achievement criteria in Studio, specifying which course content (assignments, exams, etc.) a learner must complete, at what threshold, and with what AND/OR logic  
- The platform can track each learner's progress toward demonstrating each competency as they receive grades and completions  
- A history of criteria changes is preserved for audit and traceability

Without this data model, no competency progress dashboards, automated competency evaluations, or CBE-specific authoring tools can be built.

---

## Description

Implement the Django database models defined in ADR-0002 (Competency Criteria Model) and ADR-0003 (Competency Criteria Versioning). This is a data-layer-only issue: no API endpoints, no UI, and no business logic beyond schema constraints and delete protection.

**Authoring/Definition Models**

- `CompetencyTaxonomy` — extends `Taxonomy` via Django multi-table inheritance to mark taxonomies as CBE-enabled  
- `CompetencyCriteriaGroup` — AND/OR expression tree internal nodes  
- `CompetencyRuleProfile` — reusable evaluation rule defaults scoped by taxonomy, course, or organization  
- `CompetencyCriteria` — leaf nodes in the criteria tree, linking tag/object associations to optional rule overrides

**Lookup Data**

- `CompetencyMasteryStatuses` — shared status values: Demonstrated, AttemptedNotDemonstrated, PartiallyAttempted

**Learner Progress Models (append-only)**

- `StudentCompetencyCriteriaStatus`  
- `StudentCompetencyCriteriaGroupStatus`  
- `StudentCompetencyStatus`

Per ADR-0003, `django-simple-history` is applied to the three authoring definition models only. Learner status tables are append-only by design and do not use history tracking.

---

## Acceptance Criteria

**Note:** This issue delivers a data model, not a user-facing feature. There is no manual QA path. Acceptance is determined by a PR reviewer verifying the following against ADR-0002 and ADR-0003.

**Schema Correctness (ADR-0002)**

- [ ] `CompetencyTaxonomy` uses Django MTI (not a `taxonomy_type` column); `taxonomy_ptr_id` is both the PK and FK to `oel_tagging_taxonomy.id`  
- [ ] `CompetencyCriteriaGroup` has all required columns: `id`, `parent_id` (nullable self-FK), `oel_tagging_tag_id`, `course_id` (nullable), `name`, `ordering`, `logic_operator` (AND/OR/null)  
- [ ] `CompetencyRuleProfile` has all required columns; `rule_payload` is a validated JSON field with shape enforced per `rule_type`  
- [ ] `CompetencyCriteria` has all required columns including nullable `rule_type_override` and `rule_payload_override` with the same validation contract  
- [ ] `CompetencyMasteryStatuses` is seeded with all three values: Demonstrated, AttemptedNotDemonstrated, PartiallyAttempted  
- [ ] `StudentCompetencyStatus` enforces a constraint limiting status to Demonstrated and PartiallyAttempted only (not AttemptedNotDemonstrated)  
- [ ] All 10 indexes from Decision 5 of ADR-0002 are present  
- [ ] Delete protection is implemented: hard deletion of definition rows is blocked once any related `StudentCompetency*Status` rows exist

**Versioning (ADR-0003)**

- [ ] `django-simple-history` (`HistoricalRecords()`) is applied to `CompetencyCriteriaGroup`, `CompetencyCriteria`, and `CompetencyRuleProfile`  
- [ ] `django-simple-history` is **not** applied to `oel_tagging_tag`, `oel_tagging_taxonomy`, or `CompetencyTaxonomy`  
- [ ] Learner status tables use append-only rows (only a `created` timestamp, no `updated`); no history package applied

**General**

- [ ] Migrations are present and apply cleanly from scratch  
- [ ] No columns exist on any model that are not defined in the ADRs  
- [ ] All FK relationships match the ADR definitions exactly

---

## Technical Notes

### Files to Create

*(Adjust path to match where the new app lands, e.g., `openedx_learning/apps/competencies/`)*

- `apps.py`, `__init__.py`  
- `models.py` — all new models  
- `migrations/0001_initial.py` — schema migration  
- `migrations/0002_seed_mastery_statuses.py` — data migration to seed `CompetencyMasteryStatuses`  
- `admin.py` — basic admin registrations

### Files to Modify

- App registry / `INSTALLED_APPS` — add the new app  
- `requirements/*.txt` — add `django-simple-history` if not already present

### Implementation Notes

- **MTI:** `CompetencyTaxonomy(Taxonomy)` uses Django's built-in multi-table inheritance. `taxonomy_ptr_id` is implicit — do not declare it manually.  
- **Self-referential FK:** `CompetencyCriteriaGroup.parent_id` is `ForeignKey('self', null=True, blank=True)` for root nodes.  
- **JSON payload validation:** `rule_payload` and `rule_payload_override` use `JSONField`. Payload shape validation by `rule_type` belongs in `clean()` or a custom validator — not DB constraints alone.  
- **Seeded data:** `CompetencyMasteryStatuses` rows must be created in a dedicated data migration, not in fixtures or application code.  
- **Append-only status tables:** `Student*Status` tables have only `created`, no `updated`. Current status \= latest row for a given `(user_id, target_entity_id)` pair ordered by `created DESC, id DESC`.  
- **Delete protection:** Implement via overriding `delete()` on definition models (or Django signals) to raise `ProtectedError` when related `StudentCompetency*Status` rows exist. Consider whether this should also apply to `oel_tagging_objecttag` rows per Decision 7\.  
- **`django-simple-history` registration:** Add `history = HistoricalRecords()` to `CompetencyCriteriaGroup`, `CompetencyCriteria`, and `CompetencyRuleProfile` only. The corresponding `Historical*` tables are auto-generated in migrations.

### Example Resolution Prompt

Implement the Django data models for CBE Competency Achievement Criteria as specified in ADR-0002 and ADR-0003 in the `openedx-core` repository. Create a new Django app at `openedx-core/openedx_learning/apps/competencies`. Models to implement: `CompetencyTaxonomy` (MTI extending `Taxonomy`), `CompetencyCriteriaGroup` (self-referential tree with AND/OR `logic_operator`), `CompetencyRuleProfile` (JSON-payload rule defaults scoped by taxonomy/course/org), `CompetencyCriteria` (leaf criterion with optional rule overrides and the same JSON validation contract), `CompetencyMasteryStatuses` (seeded lookup table), and the three `StudentCompetency*Status` append-only tables. Apply `django-simple-history` to the three authoring definition models only. Include all 10 indexes from Decision 5 of ADR-0002. Add a data migration to seed `CompetencyMasteryStatuses`. Implement delete protection that blocks hard deletion of definition rows once any learner status rows exist.

# 1.2

## Use Case

As a Platform Administrator, I need the taxonomy Create and Import endpoints to accept a Taxonomy Type field so that I can indicate when a taxonomy should be treated as a Competency Taxonomy rather than a standard tag taxonomy.

---

## Description

This issue updates the REST Create endpoint and REST Import action in **openedx-core** to accept an optional `taxonomy_type` field. The field accepts two values: `"competency"` (triggers creation of a `CompetencyTaxonomy` record alongside the base `Taxonomy` in a single transaction) and `"tags"` (creates a plain `Taxonomy`; also the default when the field is omitted). Unsupported values, including `"system"`, must be rejected with a 400 — system taxonomies are created programmatically and must not be user-creatable via these endpoints.

Taxonomy type is a derived property of the model structure — a competency taxonomy has a `CompetencyTaxonomy` MTI child row, a system taxonomy has `system_defined = True`, and a tag taxonomy is neither. No new type column is added to the schema.

**Architecture constraint:** `openedx_tagging` is a standalone library with no dependencies on other openedx-core packages. It must not import or instantiate `CompetencyTaxonomy`. The creation of a `CompetencyTaxonomy` row belongs in the CBE applet (`openedx_learning/applets/cbe/`), which depends on `openedx_tagging` — not the other way around. This ticket updates the `openedx_tagging` serializer and view layer to accept and surface `taxonomy_type`, but the dispatching of competency-specific creation logic is handled at a higher layer. The specific mechanism (view override, mixin, or extension point in the CBE applet) is an implementation decision for the developer.

**Endpoints in scope:**

- `POST /api/tagging/v1/taxonomies/` — the direct Create endpoint in openedx-core  
- `POST /api/content_tagging/v1/taxonomies/import/` — the Studio import endpoint in openedx-platform, whose `create_import()` action inherits from `TaxonomyView` in openedx-core. Most of the work is in the parent class; the openedx-platform layer needs verification that `taxonomy_type` flows through the `super()` call correctly.

**Out of scope:**

- Returning `taxonomy_type` in GET/LIST responses (see \#618).

---

## Acceptance Criteria

These scenarios are verifiable via Postman against a local or dev environment.

**Scenario 1: Creating a Competency Taxonomy**

```
Given a POST request to /api/content_tagging/v1/taxonomies/
And the request body includes taxonomy_type set to "competency"
When the endpoint processes the request
Then the response returns 201
And a CompetencyTaxonomy record is created linked to the new Taxonomy
```

**Scenario 2: Creating a taxonomy with taxonomy\_type set to "tags"**

```
Given a POST request to /api/content_tagging/v1/taxonomies/
And the request body includes taxonomy_type set to "tags"
When the endpoint processes the request
Then the response returns 201
And no CompetencyTaxonomy record is created
```

**Scenario 3: Creating a taxonomy without a taxonomy\_type (default)**

```
Given a POST request to /api/content_tagging/v1/taxonomies/
And the request body does not include a taxonomy_type field
When the endpoint processes the request
Then the response returns 201
And the behavior is identical to Scenario 2
```

**Scenario 4: Rejected taxonomy\_type values**

```
Given a POST request to /api/content_tagging/v1/taxonomies/
And the request body includes taxonomy_type set to "system" or any unsupported value
When the endpoint processes the request
Then the response returns 400
And the validation error identifies taxonomy_type as the invalid field
```

**Scenario 5: Importing a Competency Taxonomy**

```
Given a multipart POST request to /api/content_tagging/v1/taxonomies/import/
And the request includes a valid taxonomy file and taxonomy_type set to "competency"
When the endpoint processes the request
Then the import completes successfully
And a CompetencyTaxonomy record is created linked to the new Taxonomy
```

**Scenario 6: Importing without a taxonomy\_type (default)**

```
Given a multipart POST request to /api/content_tagging/v1/taxonomies/import/
And the request does not include a taxonomy_type field
When the endpoint processes the request
Then the import completes successfully
And no CompetencyTaxonomy record is created
```

**Scenario 7: Rejected taxonomy\_type on import**

```
Given a multipart POST request to /api/content_tagging/v1/taxonomies/import/
And the request includes taxonomy_type set to "system" or any unsupported value
When the endpoint processes the request
Then the response returns 400
And the validation error identifies taxonomy_type as the invalid field
```

---

## Technical Notes

### Files to Create

The CBE applet will need a `create_competency_taxonomy()` function. If `openedx_learning/applets/cbe/api.py` does not already exist (from the data model ticket), it should be created here.

### Modified Files

**openedx-core**

| File | Nature of modification |
| :---- | :---- |
| `src/openedx_tagging/rest_api/v1/serializers.py` | Add `taxonomy_type` as a write-only `ChoiceField` |
| `src/openedx_tagging/rest_api/v1/views.py` | Update `perform_create()` and `create_import()` to surface `taxonomy_type` for use by higher layers |
| `openedx_learning/applets/cbe/api.py` | Add `create_competency_taxonomy()` — wraps `create_taxonomy()` and creates the `CompetencyTaxonomy` row in a single `transaction.atomic()` |

**openedx-platform**

| File | Nature of modification |
| :---- | :---- |
| `openedx/core/djangoapps/content_tagging/rest_api/v1/views.py` | Verify `TaxonomyOrgView.create_import()` (lines 109–133) passes `taxonomy_type` through the `super()` call; patch if it does not |

### Implementation Notes

- **Layering constraint.** `openedx_tagging/api.py::create_taxonomy()` creates only a plain `Taxonomy`. It must not import or call anything from `openedx_learning`. The `CompetencyTaxonomy` creation belongs exclusively in the CBE applet.  
    
- **`create_competency_taxonomy()` in the CBE applet.** This function calls `create_taxonomy()` then creates a linked `CompetencyTaxonomy` row, wrapped in `transaction.atomic()`. It is the only place that knows about both layers.  
    
- **Routing in the REST layer.** The `openedx_tagging` view accepts `taxonomy_type` from validated data and makes it available, but the dispatch to `create_competency_taxonomy()` happens at a layer that can see both `openedx_tagging` and the CBE applet. The specific mechanism (a CBE-provided view mixin that overrides `perform_create()`, or an extension point) is an implementation decision — choose the approach that best fits the existing extension patterns in this codebase.  
    
- **Validation in the serializer.** Add `taxonomy_type` as a `ChoiceField` with `required=False`, `write_only=True`, and `choices=["tags", "competency"]`. Omitting the field is equivalent to `"tags"`. `"system"` is intentionally absent, producing a standard DRF 400 if attempted.  
    
- **Coordination with \#618 (GET responses).** This ticket owns the write side of `taxonomy_type`: a `write_only=True` `ChoiceField` for input. Issue \#618 owns the read side: a separate `SerializerMethodField` that computes `taxonomy_type` from the model structure. These are two distinct fields on the same serializer and do not conflict, but the valid-values constant (e.g. `TAXONOMY_TYPE_COMPETENCY = "competency"`) should be defined once in a shared location and referenced by both tickets to avoid divergence.  
    
- **`create_import()` action.** Locate this action in `TaxonomyView` in `views.py` and apply the same `taxonomy_type` handling as `perform_create()`. The openedx-platform `TaxonomyOrgView.create_import()` calls `super().create_import()`, so if the parent handles `taxonomy_type`, the platform layer likely requires no code changes — only verification that the field is not stripped before the `super()` call.

### Example Resolution Prompt

Across openedx-core and openedx-platform, add `taxonomy_type` support to taxonomy creation and import. In `openedx-core/src/openedx_tagging/rest_api/v1/serializers.py`, add `taxonomy_type` as a write-only `ChoiceField` with `required=False` and `choices=["tags", "competency"]`; define the valid-value constants once in a shared location so issue \#618 can reference them for the read side. In `src/openedx_tagging/rest_api/v1/views.py`, update both `perform_create()` (around line 262\) and the `create_import()` action to surface `taxonomy_type` from validated data for use by higher layers — do not call `CompetencyTaxonomy` directly from this layer. In `openedx_learning/applets/cbe/api.py`, add `create_competency_taxonomy()`: call `create_taxonomy()` from `openedx_tagging`, then create the linked `CompetencyTaxonomy` row, wrapped in `transaction.atomic()`. Wire the dispatch to `create_competency_taxonomy()` at a layer that can see both `openedx_tagging` and the CBE applet — a CBE-provided view mixin overriding `perform_create()` is one viable approach. In `openedx-platform/openedx/core/djangoapps/content_tagging/rest_api/v1/views.py`, verify that `TaxonomyOrgView.create_import()` (lines 109–133) does not strip `taxonomy_type` before calling `super().create_import()`; patch if needed. Reject `"system"` and all other unsupported values with a 400 on both endpoints.

# 1.3

## Use Case

As a Platform Administrator, I need the taxonomy Get endpoint to return the Taxonomy Type so that platform interfaces can identify which taxonomies are Competency Taxonomies and which are standard tag taxonomies.

---

## Description

This issue updates the taxonomy retrieval API to include a `taxonomy_type` field in the response for both the single-taxonomy (`GET /api/tagging/v1/taxonomies/{id}/`) and list (`GET /api/tagging/v1/taxonomies/`) endpoints. The field returns `"competency"` for Competency Taxonomies and `null` for all other taxonomies. The returned `"competency"` value must match what the Create endpoint accepts.

This ticket covers the read path only. It does not add write behavior, change authorization rules, or alter any other field in the response. System-level taxonomy behavior (`system_defined`) is unchanged and out of scope.

**Also in scope:** Verify that `TaxonomyOrgSerializer` in edx-platform (`openedx/core/djangoapps/content_tagging/rest_api/v1/serializers.py`) does not exclude `taxonomy_type` from its response — the frontend Taxonomies page calls the edx-platform endpoint, not the openedx-tagging endpoint directly. Patch if needed.

**Dependency:** Requires the `CompetencyTaxonomy` model (\[link to data model ticket\]) and the updated Create endpoint (\[link to Create ticket\]) to be merged first.

---

## Acceptance Criteria

These scenarios are verifiable via Postman against a local or dev environment.

**Scenario 1: Retrieving a Competency Taxonomy**

```
Given a taxonomy exists that was created as a Competency Taxonomy
When I send GET /api/content_tagging/v1/taxonomies/{id}/
Then the response includes a taxonomy_type field
And the taxonomy_type value is "competency"
```

**Scenario 2: Retrieving a non-Competency Taxonomy**

```
Given a taxonomy exists that is not a Competency Taxonomy
When I send GET /api/content_tagging/v1/taxonomies/{id}/
Then the response includes a taxonomy_type field
And the taxonomy_type value is null
```

**Scenario 3: Retrieving the taxonomy list**

```
Given both Competency Taxonomies and non-Competency Taxonomies exist on the platform
When I send GET /api/content_tagging/v1/taxonomies/
Then each taxonomy in the response includes a taxonomy_type field
And Competency Taxonomies return "competency"
And all other taxonomies return null
```

---

## Technical Notes

### Files to Create

None expected.

### Modified Files

**openedx-core**

| File | Nature of modification |
| :---- | :---- |
| `src/openedx_tagging/rest_api/v1/serializers.py` | Add `taxonomy_type` as a read-only `SerializerMethodField` returning `"competency"` or `null` |
| `src/openedx_tagging/rest_api/v1/views.py` | Add `select_related('competencytaxonomy')` to `get_queryset()` to prevent N+1 on list |

**edx-platform**

| File | Nature of modification |
| :---- | :---- |
| `openedx/core/djangoapps/content_tagging/rest_api/v1/serializers.py` | Verify `TaxonomyOrgSerializer` (lines 70–99) does not exclude `taxonomy_type` from its `Meta.fields`; add it if missing |

### Implementation Notes

- **`SerializerMethodField` logic:**

```
def get_taxonomy_type(self, obj):
    if hasattr(obj, 'competencytaxonomy'):
        return "competency"
    return None
```

  No `system_defined` check — this field is deliberately oblivious to system taxonomies. System taxonomies return `null` here, the same as standard tag taxonomies. The `system_defined` field on the response already handles system taxonomy identification and is unchanged by this ticket.


- **N+1 risk on list:** Add `.select_related('competencytaxonomy')` to `get_queryset()` on `TaxonomyView`. Django joins the table once; `hasattr` on a pre-fetched miss returns `False` without an extra query.  
    
- **Consistency with Create endpoint:** The `"competency"` value returned here must exactly match the accepted input on the Create endpoint. Define it once as a named constant and reuse it in both the serializer method and the write-side `ChoiceField` validator.  
    
- **Read-only field:** Mark `taxonomy_type` as `read_only=True` to prevent any risk of it being written via PATCH.  
    
- **edx-platform passthrough:** `TaxonomyOrgSerializer` extends `TaxonomySerializer`. If its `Meta.fields` is an explicit list, `taxonomy_type` must be added to it. If it uses `fields = '__all__'` or inherits without override, no change is needed — just verify.

### Example Resolution Prompt

In `openedx-core/src/openedx_tagging/rest_api/v1/serializers.py`, add `taxonomy_type` as a read-only `SerializerMethodField` on `TaxonomySerializer`. The method returns `"competency"` if `hasattr(obj, 'competencytaxonomy')`, and `None` otherwise. Do not check `system_defined` — this field is intentionally oblivious to system taxonomy status. In `views.py`, add `.select_related('competencytaxonomy')` to `TaxonomyView.get_queryset()`. Define `"competency"` as a named constant shared with the Create endpoint's `ChoiceField`. In `edx-platform/openedx/core/djangoapps/content_tagging/rest_api/v1/serializers.py`, check whether `TaxonomyOrgSerializer` (lines 70–99) has an explicit `Meta.fields` list; if so, add `taxonomy_type` to it.

# 1.4

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

This ticket covers the dropdown UI, form state, and API payload only. Displaying the taxonomy type in the taxonomy list or detail views is out of scope and will be addressed in a future ticket. Until that display ticket ships, QA must verify backend storage of the taxonomy type via Postman.

**Dependency:** The import endpoint's support for `taxonomy_type` is implemented in \[link to backend Create/Import ticket\]. That ticket must be merged before this frontend change can be verified end-to-end.

---

## Acceptance Criteria

Displaying the taxonomy type in the list or detail views is out of scope. Backend storage must be verified via Postman until the display ticket ships.

**Scenario 1: Dropdown appears in the correct modal step with correct options**

```
Given the user has uploaded a taxonomy file and advanced to the "Populate Taxonomy Information" step
Then a "Taxonomy Type" dropdown is visible below the Description field
And "Tags" is selected by default
And "Tags" and "Competency" are the only options in the dropdown
And "System" is not present as an option
```

**Scenario 2: Importing with Competency type selected**

```
Given the user is on the "Populate Taxonomy Information" step
And the user selects "Competency" from the Taxonomy Type dropdown
When the user clicks "Import"
Then the import completes successfully
And the new taxonomy appears in the taxonomy list
And [Postman] GET the new taxonomy returns taxonomy_type = "competency"
```

**Scenario 3: Importing with Tags type (default or explicit selection)**

```
Given the user is on the "Populate Taxonomy Information" step
And the Taxonomy Type dropdown is left at its default or set explicitly to "Tags"
When the user clicks "Import"
Then the import completes successfully
And the new taxonomy appears in the taxonomy list
And [Postman] GET the new taxonomy returns taxonomy_type = null
```

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

### Implementation Notes

- **Dropdown placement:** The `PopulateStep` component (lines 183–220 of `ImportTagsWizard.jsx`) renders the Name and Description fields. Add the Taxonomy Type dropdown directly below the Description textarea, using the same UI component library patterns already present in the file. Options: "Tags" (default) and "Competency" only — do not include "System".  
- **State:** The `taxonomyPopulateData` state (lines 305–308) currently holds `{ taxonomyName, taxonomyDesc }`. Extend it with `taxonomyType: 'tags'` as the default. The existing change handler pattern (lines 189–199) works with an additional field without restructuring.  
- **API payload:** The `useImportNewTaxonomy` hook (lines 113–137 of `apiHooks.ts`) builds `FormData` and POSTs to `createTaxonomyFromImport()` (defined at `api.ts:95`). Always append `taxonomy_type` to the FormData — send `"competency"` or `"tags"` depending on the dropdown selection. The backend accepts both values explicitly; do not omit the field.  
- **No new components needed.** The dropdown should reuse existing Select/Form patterns already present in the file.

### Example Resolution Prompt

In `frontend-app-authoring`, update the taxonomy import modal to add a Taxonomy Type dropdown. In `src/taxonomy/import-tags/ImportTagsWizard.jsx`, add a dropdown to the `PopulateStep` component (currently lines 183–220) below the Description textarea. Options: "Tags" (default) and "Competency" — do not include "System". Extend the `taxonomyPopulateData` state (currently lines 305–308) with `taxonomyType: 'tags'`. In `src/taxonomy/data/apiHooks.ts`, update `useImportNewTaxonomy` (lines 113–137) to always append `taxonomy_type` to the `FormData` sent to `createTaxonomyFromImport()`: send `"competency"` or `"tags"` based on the dropdown selection. Match the existing component and state-management patterns already in the file.

# 1.5

## Use Case

As a Platform Administrator, I need to see a taxonomy type badge on each taxonomy card on the Taxonomies page so that I can quickly distinguish Competency Taxonomies, standard tag taxonomies, and system-level taxonomies at a glance without leaving the page.

---

## Description

Today, the Taxonomies page in Studio displays a "System-level" badge only on system-defined taxonomies. All other taxonomies show no type indicator.

This issue updates every taxonomy card to always display exactly one type badge:

- **"Competency"** — new badge for Competency Taxonomies, visually distinct color from System-level  
- **"Tags"** — new badge for standard tag taxonomies  
- **"System-level"** — existing badge, retained as-is for system-defined taxonomies

The badge is determined by two fields already present (or being added) to the API response: `systemDefined` (existing boolean) and `taxonomyType` (added by \[link to ticket 3\]). The priority order is:

1. If `systemDefined` is true → show "System-level" badge (unchanged behavior)  
2. Else if `taxonomyType` is `"competency"` → show "Competency" badge  
3. Otherwise → show "Tags" badge

This ticket is the display counterpart to the import dropdown added in \[link to ticket 4\] and removes the need for Postman verification of taxonomy type after import.

**Dependency:** Requires \[link to ticket 3\] (GET endpoint returning `taxonomy_type`) to be merged first, and that `TaxonomyOrgSerializer` in edx-platform passes `taxonomy_type` through in the `/api/content_tagging/v1/taxonomies/` response.

---

## Acceptance Criteria

**Scenario 1: Competency taxonomy shows Competency badge**

```
Given a Competency Taxonomy exists on the platform
When I navigate to the Taxonomies page
Then the taxonomy card displays a "Competency" badge
And the badge is visually distinct in color from the System-level badge
```

**Scenario 2: Standard tag taxonomy shows Tags badge**

```
Given a standard tag taxonomy exists on the platform
When I navigate to the Taxonomies page
Then the taxonomy card displays a "Tags" badge
```

**Scenario 3: System taxonomy shows System-level badge**

```
Given a system-level taxonomy exists on the platform
When I navigate to the Taxonomies page
Then the taxonomy card displays a "System-level" badge
```

**Scenario 4: Every taxonomy card shows exactly one type badge**

```
Given multiple taxonomies of different types exist on the platform
When I navigate to the Taxonomies page
Then each taxonomy card displays exactly one type badge
And no taxonomy card displays more than one type badge
```

---

## Technical Notes

### Files to Create

| File | Purpose |
| :---- | :---- |
| `src/taxonomy/taxonomy-card/TaxonomyTypeBadge.jsx` | New badge component that accepts `systemDefined` and `taxonomyType` props and renders the correct label and color |

### Modified Files

| File | Nature of modification |
| :---- | :---- |
| `src/taxonomy/data/types.ts` | Add `taxonomyType: 'competency' | null` to `TaxonomyData` interface |
| `src/taxonomy/taxonomy-card/index.jsx` | Replace conditional `SystemDefinedBadge` rendering (lines 122–128) with `TaxonomyTypeBadge`, passing both `systemDefined` and `taxonomyType` |

### Implementation Notes

- **`taxonomyType` is not yet in the frontend data layer.** Add `taxonomyType: 'competency' | null` to the `TaxonomyData` interface in `types.ts` (lines 2–18). The `camelCaseObject()` call in the API hook automatically converts `taxonomy_type` from the response to `taxonomyType` — no hook changes needed.  
- **Badge priority logic belongs in `TaxonomyTypeBadge`.** The component receives both `systemDefined: boolean` and `taxonomyType: 'competency' | null` and applies the priority order: System-level first, then Competency, then Tags. Keeping the logic inside the component makes it testable in isolation.  
- **Visual reference for the new component:** Use the same badge/pill UI component already used by `src/taxonomy/system-defined-badge/index.jsx` as the pattern. "System-level" retains its existing styling; "Competency" uses a distinct color variant; "Tags" uses a neutral color variant.  
- **Card update:** `TaxonomyCard` (`taxonomy-card/index.jsx`, lines 122–128) currently conditionally renders `<SystemDefinedBadge />` when `showSystemBadge` is true. Replace this with `<TaxonomyTypeBadge systemDefined={systemDefined} taxonomyType={taxonomyType} />` — always rendered, no conditional, since every taxonomy now shows a badge.  
- **`systemDefined` is not removed.** It remains on the interface and in existing code. This ticket does not clean it up; that is a separate concern.  
- **`taxonomy_type` passthrough in edx-platform:** The frontend calls `/api/content_tagging/v1/taxonomies/`. Verify that `TaxonomyOrgSerializer` (`edx-platform/openedx/core/djangoapps/content_tagging/rest_api/v1/serializers.py`, lines 70–99) includes `taxonomy_type` in its response — this is covered as part of \[link to ticket 3\], but confirm it is merged and working before testing this ticket.

### Example Resolution Prompt

In `frontend-app-authoring`, add taxonomy type badges to the Taxonomies page. In `src/taxonomy/data/types.ts`, add `taxonomyType: 'competency' | null` to the `TaxonomyData` interface. Create `src/taxonomy/taxonomy-card/TaxonomyTypeBadge.jsx` that accepts `systemDefined: boolean` and `taxonomyType: 'competency' | null` props and renders exactly one badge: "System-level" if `systemDefined` is true, "Competency" if `taxonomyType === 'competency'`, or "Tags" otherwise. Use the same badge/pill UI component as `src/taxonomy/system-defined-badge/index.jsx` as the visual pattern, with a distinct color variant for "Competency" and a neutral variant for "Tags". In `src/taxonomy/taxonomy-card/index.jsx`, replace the conditional `<SystemDefinedBadge />` at lines 122–128 with `<TaxonomyTypeBadge systemDefined={systemDefined} taxonomyType={taxonomyType} />` — always rendered, no conditional. Do not remove `systemDefined` from the interface or any existing code.

# 1.6

## Use Case

As a Platform Administrator, I need a clear and intuitive way to navigate to and manage Competency Taxonomies and tag taxonomies from the Studio home page so that I can quickly access the taxonomies I care about without confusion about what each option does.

---

## Description

The UX Designer has proposed a dropdown on the Taxonomies tab of the Studio home page with two options: "Competency" and "Tags". In the current design, clicking either option launches the taxonomy import wizard with the corresponding Taxonomy Type pre-selected.

Two concerns have been raised with this design:

1. **Labeling:** Nothing in the current design indicates that clicking an option starts an import/creation flow. A user clicking "Competency" will likely expect to see their competency taxonomies — not be taken into an import wizard. This is a significant discoverability risk.  
     
2. **Use case frequency:** Platform Administrators will far more often want to view and manage existing taxonomies than to create new ones from the home page. The import wizard is already accessible via the Import button on the Taxonomies page itself.

Three directions are on the table for the designer to evaluate:

**Option A — Navigation only:** Dropdown options navigate to the Taxonomies page pre-filtered by type ("Competency Taxonomies", "Tag Taxonomies"). Import stays on the Taxonomies page as it currently is. Note: this requires filter/tab functionality on the Taxonomies page, which would expand the scope of ticket 7\.

**Option B — Navigation \+ creation:** Four options — "View Competency Taxonomies", "View Tag Taxonomies", "Add Competency Taxonomy", "Add Tag Taxonomy". Covers both the management and creation use cases, at the cost of a more complex dropdown.

**Option C — Label fix only:** Retain the current import-only behavior but update the labels to make the action unambiguous — for example, "Add Competency Taxonomy" and "Add Tag Taxonomy", or prefix each with "+". Lowest-effort change; does not address the frequency-of-use concern.

The designer should evaluate these options (and any alternatives) and produce a revised design. The chosen direction feeds directly into ticket 7\.

---

## Acceptance Criteria

This is a design spike. The deliverable is design artifacts and documented decisions, not working code. There is no Gherkin and no QA path.

- [ ] The three options above (and any designer alternatives) have been reviewed with the team and a direction has been chosen with documented rationale  
- [ ] The revised design clearly communicates to the user what action each dropdown option performs before they click it  
- [ ] Figma or design file is updated to reflect the agreed-upon approach  
- [ ] If Option A or B is chosen, the design specifies how filtering behaves on the Taxonomies page and notes are added to ticket 7 to expand its scope accordingly  
- [ ] Notes for ticket 7 are written capturing the agreed workflow, interaction details, and any new filtering or navigation requirements the implementation will need

---

## Context for the Designer

**Current import workflow** (from ticket 4 — what the existing design routes users into):

1. Click Import on the Taxonomies page  
2. Upload a JSON or CSV file  
3. Click Continue  
4. Fill in Taxonomy Name, Taxonomy Description, and Taxonomy Type (dropdown: Tags default, Competency option)  
5. Click Import

**Taxonomy types available to users:** "Competency" and "Tags" only. System-level taxonomies exist but cannot be user-created and should not appear as dropdown options.

**Filtering capability:** The Taxonomies page does not currently have filter or tab functionality. If Option A or B is chosen, this will need to be built as part of ticket 7 — budget accordingly.

**Related tickets:**

- Ticket 4: Import flow with Taxonomy Type dropdown (the flow the current design leads into)  
- Ticket 5: Taxonomy type badge on taxonomy cards (the visual that makes filtering meaningful)  
- Ticket 7: Implementation of whichever design this ticket produces  
- \[Link to current Figma design\]

# 2.1

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

# 4.1

## Architecture Spike: Determine Competency ID field strategy for taxonomy competency data

### Use Case

As a Platform Administrator, I want a stable, human-readable Competency ID visible for each competency in the Competency Management UI and on the assignment workflow, so that I can reference and communicate specific competencies using a meaningful identifier that my institution recognizes.

### Description

**Current behavior**

The existing tag/taxonomy data model exposes several identifier fields per tag: an internal PK (`id`, never user-visible), a stable external reference (`uuid`), and a client-meaningful key (`_key` / `key`). None of these is designed for use as a human-readable Competency ID in a management UI or assignment workflow. No such field currently exists.

**Requested change**

Determine the ID field strategy for competency taxonomies: which field or fields represent the Competency ID, how the ID is assigned, and how it behaves across import, re-import, API retrieval, and UI display. This spike produces a documented recommendation for the data model implementation ticket — not code.

Key constraints the recommendation must respect:

- This is an internal identifier. If CASE IDs or CTDL IDs are added in the future, they are separate fields with their own semantics — this ID is not a CASE ID.  
- Changes to the data model are additive; existing identifier fields are not replaced.  
- The recommendation must be approved by the engineering team and the Open edX community.

### Acceptance Criteria

This is an architecture spike. The deliverable is a documented technical recommendation, not working code. There is no Gherkin and no QA path.

- [ ] Recommendation document published (see Open Questions for format).  
- [ ] Recommendation specifies whether a new field is added or an existing field is repurposed, and justifies the choice.  
- [ ] ID assignment strategy decided and documented (see Open Questions).  
- [ ] Uniqueness scope decided: within a taxonomy, globally, or advisory only.  
- [ ] Import and re-import behavior specified: whether the ID is preserved, overwritten from the import file, or conflict-flagged.  
- [ ] API serialization specified: which field is exposed and under what name.  
- [ ] Backward compatibility and migration implications documented.  
- [ ] Recommendation reviewed and approved by the engineering team and Open edX community.  
- [ ] All Open Questions resolved before this ticket is closed.

### Open Questions

1. **ID assignment strategy (architect, blocking):** Two options:  
     
   - Option A (auto-generate with override): derive a default from the competency name — initials of each word plus a hierarchical position suffix (e.g., `PK-1`, `PK-1.2`, `PK-1.2.3` for root / second level / third level). User can override. The exact format of the suffix is part of what this spike defines.  
   - Option B (user-entered only): field is blank until the operator supplies a value. No auto-generation.

   

   Option B is simpler to implement and avoids the edge case where a name change silently invalidates a previously meaningful auto-generated ID. Which fits the operator use case better?

   

2. **Uniqueness scope (architect):** Must the Competency ID be unique within a taxonomy, unique globally across all competency taxonomies, or is it advisory (displayed but not enforced)?  
     
3. **Re-import behavior (architect):** On re-import, is the stored Competency ID preserved, overwritten if the import file includes an ID column, or always preserved (import file ID column ignored)? What import file column, if any, maps to this field?  
     
4. **Recommendation format (architect):** ADR under `docs/decisions/`, a GitHub discussion for community comment, or both? The community approval requirement suggests at minimum a public discussion before the ADR is finalized.

### Context for the Architect

**Existing data model identifiers** (see `src/openedx_tagging/core/tagging/models/`):

- `id` — internal PK, never user-visible  
- `uuid` — stable external reference  
- `_key` / `key` — client-meaningful, the DB field used in tagging operations

**UX context:** The existing UX designs for the Competency Management page and the assignment workflow show a visible Competency ID per competency. This ID appears on the control used to apply a competency to an assignment. The exact field this maps to is what this spike must determine.

**Architect's current position (starting point, not a decision):**

The Competency ID should be an internal identifier. CASE IDs and CTDL IDs, if added, are separate fields — conflating them (as has been suggested in the past) mixes internal and external identifier semantics and will cause problems when institutions want both.

The natural auto-generation scheme is: initials of each word in the competency name plus a hierarchical depth/position suffix. However, Option B (user-entered only) is likely simpler and avoids name-change invalidation. This is the core design question the spike should resolve with team and community input.  
