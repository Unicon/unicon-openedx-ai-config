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

# 6.1

## Use Case

As an operator responsible for a given organization, course, or competency taxonomy, I need to create a reusable Competency Rule Profile (a default mastery rule such as ">= 75%") scoped to that organization, course, and/or competency taxonomy, or as an instance-wide default, so that the Competency Criteria authored under that scope inherit a consistent default rule instead of each author re-entering the same threshold by hand.

*Role note: the CBE backlog names "Platform Administrator." The full permission model for scope-bearing profiles is unresolved and tracked in Open Questions. One rule is fixed: creating the instance-wide default (all scope fields null) is restricted to global staff (`is_staff`).*

---

## Description

Build a REST Create endpoint (`POST`) in the CBE applet (`src/openedx_learning/applets/cbe/`, per ADR-0001) that creates a `CompetencyRuleProfile` as defined in ADR-0002 (`docs/openedx_learning/decisions/0002-competency-criteria-model.rst`). The request accepts the scope fields (`organization`, `course`, `competency_taxonomy` — each independently optional), a `rule_type`, and a `rule_payload`.

A profile may set any subset of the three scope fields, including none. A profile with all three scope fields null is the **instance-wide default** and may be created only by global staff (`is_staff`); a non-staff request to create an all-null profile is rejected with a 403. **At most one all-null instance-wide default may exist**: a second all-null create is rejected with a 409 (an application-level check in the create path, not a database unique constraint and not an ADR-0002 change), so that "the" instance-wide default is unambiguous. Duplicate *scoped* profiles at the same `(competency_taxonomy, course, organization)` are allowed (ADR-0002 defines only an index there, no unique constraint).

For the MVP only `rule_type == "Grade"` is accepted; `"View"` and `"MasteryLevel"` are rejected with a 400 even though the model enumerates them (out of MVP per `cbe-project-context.md`). The `Grade` `rule_payload` is validated against the ADR's typed contract (operator from `>, >=, <, <=, =`; a threshold value; a scale); a malformed payload returns a 400 identifying the offending field. Because DRF's `ModelSerializer` does not call `Model.clean()`, the create path must call `full_clean()` (or the shared validator) before saving so an invalid payload surfaces as a 400, not a 500.

This ticket is the foundation of a consistent CRUD set with 6.2 (Update/Delete) and 6.3 (Get/List): it lands the `rest_api/` package, the shared serializer, the permission class, the `rules.py` predicates, and the router registration that 6.2 and 6.3 extend. The new REST surface and the new `api.py` functions are marked **UNSTABLE**, so the identifier and permission model can still change before stabilization without DEPR. The external handle is the integer `id` for MVP (matching final ADR-0002 and the `openedx_tagging` REST precedent).

**Depends on** the data-model ticket (Markdown Github Issues.md 1.1 / ADR-0002), which creates the CBE applet and the `CompetencyRuleProfile` model.

**Out of scope:**
- Any `rule_type` other than `Grade`.
- A uniqueness/duplicate-conflict rule for *scoped* profiles (ADR-0002 has an index only; adding a unique constraint is an ADR-0002 change, not this ticket).
- The full org/course/taxonomy permission model beyond the fixed all-null-is-staff rule (see Open Questions).
- Update, Delete, Get, and any UI (6.2, 6.3, 6.4/6.5).
- Mounting these endpoints into a served edx-platform URL (separate sibling ticket, see Context) — until that lands, the acceptance criteria are exercised through openedx-core's own test client.

---

## Acceptance Criteria

These scenarios are verifiable via Postman against a local or dev environment (once the platform URL-mount sibling ticket has landed; before that, via openedx-core's API test client).

**Scenario 1: Creating a Grade-rule profile at a valid scope**
```
Given a POST request to the competency rule profile endpoint
And the body sets rule_type to "Grade" and a valid Grade rule_payload
And the body sets at least one of organization, course, competency_taxonomy
When the endpoint processes the request
Then the response returns 201
And the response body includes the new profile's id
And the response echoes the submitted rule_type, rule_payload, and scope fields
```

**Scenario 2: Creating the instance-wide default as global staff**
```
Given an authenticated request from a global staff user (is_staff)
And a POST body with rule_type "Grade", a valid Grade rule_payload, and all scope fields omitted or null
And no all-null instance-wide default profile exists yet
When the endpoint processes the request
Then the response returns 201
And organization, course, and competency_taxonomy are all null in the response body
```

**Scenario 3: Rejecting the instance-wide default from a non-staff user**
```
Given an authenticated request from a user who is not global staff
And a POST body with all scope fields omitted or null
When the endpoint processes the request
Then the response returns 403
And the profile is not created
```

**Scenario 4: Rejecting a second instance-wide default (pending confirmation, see Open Questions)**
```
Given an all-null instance-wide default profile already exists
And a global staff user sends a POST body with all scope fields omitted or null
When the endpoint processes the request
Then the response returns 409
And no second all-null profile is created
```

**Scenario 5: Rejecting a non-MVP rule_type**
```
Given a POST request to the competency rule profile endpoint
And the body sets rule_type to "View" or "MasteryLevel"
When the endpoint processes the request
Then the response returns 400
And the validation error identifies rule_type as the invalid field
```

**Scenario 6: Rejecting a malformed Grade payload**
```
Given a POST request to the competency rule profile endpoint
And rule_type is "Grade" but rule_payload is missing a required key or uses an unsupported operator
When the endpoint processes the request
Then the response returns 400
And the validation error identifies rule_payload as the invalid field
```

**Scenario 7: Referencing a non-existent scope entity**
```
Given a POST request to the competency rule profile endpoint
And competency_taxonomy refers to a taxonomy that does not exist
When the endpoint processes the request
Then the response returns 400
And the validation error identifies the scope field as invalid
```

**Scenario 8: Unauthorized create of a scoped profile (TBD, see Open Questions)**
```
Given a user who does not have permission to configure rule profiles for the requested scope
When the endpoint processes the request
Then the profile is not created
And an authorization error is returned
```

---

## Technical Notes

Assumed app label from the data-model ticket's `apps.py` is `oel_cbe`; permission strings are built as `f"{app_label}.{action}_competencyruleprofile"`. Adjust to whatever 1.1 actually sets. Auth is reused from `openedx_tagging.rest_api.utils` (the `@view_auth_classes` decorator: JWT + `SessionAuthenticationAllowInactiveUser`); CBE → `openedx_tagging` is an allowed import direction.

### Files to Create

| File | Purpose |
| :---- | :---- |
| `src/openedx_learning/applets/cbe/rest_api/__init__.py` | package marker |
| `src/openedx_learning/applets/cbe/rest_api/urls.py` | `path("v1/", include(v1_urls))` |
| `src/openedx_learning/applets/cbe/rest_api/v1/__init__.py` | empty (mirrors tagging) |
| `src/openedx_learning/applets/cbe/rest_api/v1/serializers.py` | `CompetencyRuleProfileSerializer` (shared across 6.1/6.2/6.3) |
| `src/openedx_learning/applets/cbe/rest_api/v1/views.py` | `CompetencyRuleProfileViewSet` (create only in this ticket) |
| `src/openedx_learning/applets/cbe/rest_api/v1/permissions.py` | `CompetencyRuleProfileObjectPermissions` |
| `src/openedx_learning/applets/cbe/rest_api/v1/urls.py` | `DefaultRouter` registration |
| `src/openedx_learning/applets/cbe/rules.py` | `is_staff` default predicates + `rules.add_perm` |
| `src/openedx_learning/applets/cbe/rest_api/v1/tests/test_views_create.py` | APIClient tests |

### Modified Files

| File | Nature of modification |
| :---- | :---- |
| `src/openedx_learning/applets/cbe/api.py` | Add `create_competency_rule_profile()`; create the module if the data-model ticket has not |
| `src/openedx_learning/applets/cbe/apps.py` | `ready()`: `from . import rules` so the predicates register at startup |

### Implementation Notes

- **REST structure (single viewset, mixins added per ticket).** Use a `GenericViewSet` composed with only the mixins each ticket owns — 6.1 adds `CreateModelMixin`, 6.3 adds `Retrieve`/`ListModelMixin`, 6.2 adds `Update`/`DestroyModelMixin`. The final class equals a `ModelViewSet` but no untested operation ships early. This mirrors `ObjectTagView` in `src/openedx_tagging/rest_api/v1/views.py`.
- **Serializer.** `CompetencyRuleProfileSerializer(serializers.ModelSerializer)` with fields `["id", <organization>, <course>, <competency_taxonomy>, "rule_type", "rule_payload"]` (use the exact scope field names 1.1 defines; `id` read-only). Constrain input with `rule_type = serializers.ChoiceField(choices=[("Grade", "Grade")])` so `View`/`MasteryLevel` yield 400 automatically. All scope fields optional. Do **not** add a uniqueness validator for scoped profiles.
- **All-null uniqueness.** Enforce "at most one all-null default" in the create path (`api.create_competency_rule_profile`): if all scope fields are null and an all-null row already exists, raise a domain error the view maps to 409. This is deliberately application-level, so no DB constraint and no ADR-0002 amendment.
- **Permissions.** `CompetencyRuleProfileObjectPermissions(DjangoObjectPermissions)` copies the `perms_map` from `src/openedx_tagging/rest_api/v1/permissions.py` (GET/HEAD→`view`, POST→`add`, PUT/PATCH→`change`, DELETE→`delete`). In `rules.py`, register the safe MVP default `rules.add_perm("oel_cbe.add_competencyruleprofile", rules.is_staff)` and the same for `view`/`change`/`delete` (matching `is_taxonomy_admin = rules.is_staff` in tagging). Document inline that edx-platform overrides these via `rules.set_perm` (see Context — sibling ticket). This keeps the permission *seam* identical under all three permission options in Open Questions; only the registered predicate differs, and that override lives platform-side.
- **Domain delegation.** `perform_create` calls `cbe.api.create_competency_rule_profile(**serializer.validated_data)`, which builds the instance, calls `full_clean()`, and saves under `transaction.atomic()`. The library's product is its in-process `api.py`, not the REST layer (same pattern as `TaxonomyView.perform_create` → `create_taxonomy`).
- **Router.** `router.register("competency-rule-profiles", views.CompetencyRuleProfileViewSet, basename="competency-rule-profile")`. This URL registration is shared with 6.2/6.3.

### Example Resolution Prompt

Create the CBE REST package at `src/openedx_learning/applets/cbe/rest_api/` mirroring `src/openedx_tagging/rest_api/`. In `rest_api/v1/serializers.py`, add `CompetencyRuleProfileSerializer(serializers.ModelSerializer)` over `openedx_learning.applets.cbe.models.CompetencyRuleProfile` with `id` read-only, all scope fields optional, and `rule_type = serializers.ChoiceField(choices=[("Grade", "Grade")])` so `View`/`MasteryLevel` return 400; do not add uniqueness validation for scoped profiles. In `rest_api/v1/permissions.py`, add `CompetencyRuleProfileObjectPermissions(DjangoObjectPermissions)` copying the `perms_map` from `src/openedx_tagging/rest_api/v1/permissions.py`. In `src/openedx_learning/applets/cbe/rules.py`, register `rules.add_perm("oel_cbe.add_competencyruleprofile", rules.is_staff)` plus `view`/`change`/`delete`, and add `from . import rules` to `apps.py` `ready()`. In `rest_api/v1/views.py`, add `@view_auth_classes` (imported from `openedx_tagging.rest_api.utils`) on `CompetencyRuleProfileViewSet(mixins.CreateModelMixin, GenericViewSet)` with `serializer_class`, `permission_classes = [CompetencyRuleProfileObjectPermissions]`, `get_queryset` returning `CompetencyRuleProfile.objects.all()`, and a `perform_create` that delegates to `cbe.api.create_competency_rule_profile(**serializer.validated_data)`. In `api.py`, implement that function to build the instance, call `full_clean()`, enforce "at most one all-null profile" (raise a domain error → 409 if a second all-null is attempted), save under `transaction.atomic()`, and return it. In `rest_api/v1/urls.py`, register the viewset on a `DefaultRouter` at `"competency-rule-profiles"` (basename `"competency-rule-profile"`); in `rest_api/urls.py`, `path("v1/", include(v1_urls))`. Mark the serializer, viewset, and `api.py` functions UNSTABLE. Do not mount anything into edx-platform (separate ticket). Add APIClient tests for 201 (scoped and all-null-as-staff), 409 (second all-null), 400 (non-Grade type, bad payload, non-existent scope), 403 (all-null as non-staff), 401 (anonymous).

---

## Context

Prior art to mirror file-for-file:
- `src/openedx_tagging/rest_api/utils.py` — `view_auth_classes`, `UserPermissionsHelper`.
- `src/openedx_tagging/rest_api/v1/permissions.py` — `TaxonomyObjectPermissions.perms_map` (copy verbatim).
- `src/openedx_tagging/rest_api/v1/urls.py` — `DefaultRouter` registration.
- `src/openedx_tagging/rules.py` — `is_taxonomy_admin = rules.is_staff` and the `add_perm` block; the `set_perm` override point is demonstrated in `tests/openedx_tagging/test_rules.py`.
- `src/openedx_tagging/apps.py` — `ready()` import pattern and the `label` convention (tagging uses `oel_tagging`).
- `src/openedx_tagging/rest_api/v1/views.py` `TaxonomyView.perform_create` → `create_taxonomy` — the REST-adapter-over-domain-function pattern.

Authoritative model: `docs/openedx_learning/decisions/0002-competency-criteria-model.rst`. Blocking dependency: data-model ticket (Markdown Github Issues.md 1.1). Layering: `.importlinter` (CBE → `openedx_tagging` allowed; never import `openedx-platform`).

**Related sibling tickets (edx-platform, tracked separately per the "platform work is its own ticket" rule):**
- **[PLAT-1 — MVP, verification-blocking] Mount CBE Competency Rule Profile REST URLs in edx-platform.** openedx-core defines these URLs but does not mount them into a served app; edx-platform does (as it exposes `/api/content_tagging/v1/taxonomies/` over openedx-core's `/api/tagging/v1/taxonomies/`). Without this, Postman/MFE cannot reach the endpoints, so the Postman-verifiable acceptance criteria on 6.1/6.2/6.3 pass only through openedx-core's test client. This is the most important sibling ticket; it blocks *acceptance*, not the code, of all three.
- **[PLAT-2 — non-MVP, only if permission Option B or C is chosen] Register scoped permission predicates for CompetencyRuleProfile in edx-platform** via `rules.set_perm("oel_cbe.{add,change,delete,view}_competencyruleprofile", <scoped predicate>)` at app-ready, keeping the all-null instance-wide default `is_staff`-only.

---

## Open Questions

- `[BLOCKING] What permission model governs a scope-bearing (org/course/taxonomy) Competency Rule Profile? To be resolved before dev; resolve once for the whole 6.1/6.2/6.3 set. (why it matters: sets the permission class and the wording/status of the "unauthorized" scenarios, and whether management is delegable below global staff.) Options: A) Global-staff-only for MVP (is_staff), same as the instance-wide default [recommended: A] B) A pluggable permission hook the consuming platform overrides via rules.set_perm, mirroring oel_tagging's *_objectid deny-by-default predicates, so org/course scoping is enforced platform-side (sibling ticket PLAT-2) C) Hybrid: taxonomy-scoped profiles use the existing oel_tagging.* predicates; org- and course-scoped profiles are global-staff-only for MVP.`
- `[non-blocking] Confirm the "at most one instance-wide default" interpretation. (why it matters: reconciles two prior decisions — "all-null = the instance-wide default" (singular) vs "no uniqueness constraint" — and drives Scenario 4. Current best-judgment: allow at most one all-null profile via an application-level 409.) Options: A) At most one all-null default; second all-null create returns 409; scoped duplicates still allowed [recommended: A] B) Allow multiple all-null profiles (then downstream resolution must disambiguate them) C) Defer, treating the instance-wide default as a logical concept resolved outside the table.`
- `[non-blocking] External handle: id vs uuid. (why it matters: ADR-0002 is final and gives only id; adding uuid is a deliberate ADR amendment plus a migration, and switching after stabilization is DEPR-governed.) Options: A) Use id for MVP, matching the final ADR and the tagging precedent, with the API marked UNSTABLE so uuid can be added before stabilization if judged necessary [recommended: A] B) Amend ADR-0002 now to add uuid and use it as the lookup field.`

# 6.2

## Use Case

As an operator responsible for a given organization, course, or competency taxonomy, I need to update or delete an existing Competency Rule Profile, so that when mastery policy changes I can revise the shared default in one place, or retire a profile that is no longer in use, without leaving Competency Criteria pointing at a rule that no longer applies.

*Role note: same permission caveat as 6.1 (see Open Questions). Management of the instance-wide default (all-null profile) is assumed global-staff-only, mirroring its create rule.*

---

## Description

Build the REST Update (`PATCH`/`PUT`) and Delete (`DELETE`) endpoints for `CompetencyRuleProfile`, extending the viewset and reusing the serializer, URL collection, and permission class established in 6.1. Update may change the `rule_payload` and, within MVP, must keep `rule_type == "Grade"`; the same payload validation as 6.1 applies (the create serializer is reused, so `View`/`MasteryLevel` are rejected with 400 and a malformed payload with 400 via `full_clean()`).

Delete is **protected**: if the profile is still referenced by any `CompetencyCriteria` (via the `competency_rule_profile` FK, ADR-0002), the delete is blocked with a 409, the profile is not deleted, and the referencing criteria are unchanged. This mirrors the ADR-0002 delete-protection pattern that the data-model ticket already applies for learner-status rows (definition rows cannot be hard-deleted while dependents exist). An unreferenced profile deletes normally (204).

**"Referenced" means an explicit FK reference** (`competency_rule_profile_id = <this profile>`). A profile consumed only via the *fallback* scope path (criteria with a null FK that resolve to it by org/course/taxonomy) is **not** protected and can be deleted; broadening protection to fallback usage is out of MVP scope.

Update and Delete are kept in one ticket deliberately: with the shared viewset, Update is `UpdateModelMixin` reusing the create serializer and Delete is `DestroyModelMixin` plus one `ProtectedError` → 409 translation, together comfortably ~1 developer-day. Splitting Delete out would isolate under half a day of work behind full ticket/review overhead.

**Depends on** the data-model ticket (1.1 / ADR-0002) and on 6.1 (shared serializer, URL collection, permission class, viewset shell).

> **Coordination addendum (delete-protection hook — do not edit ticket 1.1's description; fold this in with the 1.1 author):** The Protect-409 behavior requires the data-model layer to actually block the delete. Ticket 1.1 today protects only against learner-status rows, not against referencing `CompetencyCriteria`. This ticket needs `CompetencyCriteria.competency_rule_profile` to be declared `on_delete=models.PROTECT` so that deleting a referenced profile raises `django.db.models.ProtectedError`. Set this in the data-model ticket; enforcing it at the ORM boundary protects admin/shell callers too and lets one exception handler compose both protections. If 1.1 cannot be extended, the fallback is a `.exists()` guard inside `cbe.api.delete_competency_rule_profile` — accepted only as a fallback, since it protects just the API path.

**Out of scope:**
- Non-`Grade` rule types.
- Cascade or soft-delete of referencing criteria (the delete is protected, not cascading; changing this is an ADR-0002 change).
- Protecting against fallback-scope usage (explicit FK references only).
- The full org/course/taxonomy permission model beyond the fixed all-null-is-staff rule (see Open Questions).
- Create, Get, and UI; the edx-platform URL mount (sibling ticket PLAT-1).

---

## Acceptance Criteria

These scenarios are verifiable via Postman against a local or dev environment (once PLAT-1 lands; before that, via openedx-core's API test client).

**Scenario 1: Updating a profile's rule payload**
```
Given an existing Competency Rule Profile
And a PATCH request that sets a new valid Grade rule_payload
When the endpoint processes the request
Then the response returns 200
And the response body reflects the updated rule_payload
```

**Scenario 2: Rejecting an invalid update**
```
Given an existing Competency Rule Profile
And a PATCH request with a malformed Grade rule_payload or a non-MVP rule_type
When the endpoint processes the request
Then the response returns 400
And the validation error identifies the invalid field
```

**Scenario 3: Deleting an unreferenced profile**
```
Given an existing Competency Rule Profile that is not referenced by any Competency Criteria
When a DELETE request is sent for that profile
Then the response returns 204
And a subsequent GET for that profile returns 404
```

**Scenario 4: Blocking deletion of a referenced profile**
```
Given a Competency Rule Profile referenced by one or more Competency Criteria via the explicit FK
When a DELETE request is sent for that profile
Then the response returns 409
And the profile is not deleted
And the referencing Competency Criteria are unchanged
```

**Scenario 5: Updating or deleting a non-existent profile**
```
Given a profile id that does not exist
When a PATCH or DELETE request is sent for that id
Then the response returns 404
```

**Scenario 6: Unauthorized update or delete (TBD, see Open Questions)**
```
Given a user who does not have permission to modify rule profiles for the profile's scope
When a PATCH or DELETE request is sent
Then the profile is not modified or deleted
And an authorization error is returned
```

---

## Technical Notes

### Files to Create

| File | Purpose |
| :---- | :---- |
| `src/openedx_learning/applets/cbe/rest_api/v1/exceptions.py` | `Conflict(APIException)` with `status_code = 409` (optional; may inline in views.py) |
| `src/openedx_learning/applets/cbe/rest_api/v1/tests/test_views_update_delete.py` | APIClient tests incl. the 409 protection |

### Modified Files

| File | Nature of modification |
| :---- | :---- |
| `src/openedx_learning/applets/cbe/rest_api/v1/views.py` | Add `UpdateModelMixin`/`DestroyModelMixin`; `perform_update`; `perform_destroy` catching `ProtectedError` → 409 |
| `src/openedx_learning/applets/cbe/api.py` | Add `update_competency_rule_profile()` and `delete_competency_rule_profile()` |

*(The FK change `on_delete=models.PROTECT` on `CompetencyCriteria.competency_rule_profile` is made in the data-model ticket per the coordination addendum above, not in this ticket's files.)*

### Implementation Notes

- **Update.** Add `mixins.UpdateModelMixin`; `perform_update` delegates to `cbe.api.update_competency_rule_profile(...)`, which calls `full_clean()` before save. The create serializer is reused, so the Grade-only `rule_type` and payload validation apply to PUT/PATCH automatically.
- **Delete protection.** Add `mixins.DestroyModelMixin`. `cbe.api.delete_competency_rule_profile(profile)` calls `profile.delete()` and lets `django.db.models.ProtectedError` propagate (raised by the `on_delete=PROTECT` FK from 1.1). Override `perform_destroy` to catch `ProtectedError` and raise a `Conflict(APIException)` with `status_code = 409` and a message naming the blocking dependents. This one handler composes both the criteria-reference protection and ADR-0002's learner-status protection (both surface as `ProtectedError`). On a blocked delete the transaction rolls back, so the profile is not deleted and criteria are unchanged.
- **No existing precedent for 409 in tagging.** `src/openedx_tagging/rest_api/v1/exception_handlers.py` shows how `APIException` subclasses pass through DRF's handler; follow that so the `Conflict` renders as a clean 409 body.

### Example Resolution Prompt

In `src/openedx_learning/applets/cbe/rest_api/v1/views.py`, add `mixins.UpdateModelMixin` and `mixins.DestroyModelMixin` to `CompetencyRuleProfileViewSet`. Add `perform_update` delegating to `cbe.api.update_competency_rule_profile(...)` (reusing `CompetencyRuleProfileSerializer`, so `View`/`MasteryLevel` still 400). Define `class Conflict(APIException): status_code = 409` (in `rest_api/v1/views.py` or a new `rest_api/v1/exceptions.py`) and override `perform_destroy` to `try: cbe.api.delete_competency_rule_profile(instance)` and `except django.db.models.ProtectedError: raise Conflict(...)` with a message listing the referencing criteria. In `api.py`, add `update_competency_rule_profile` (calls `full_clean()` then saves under `transaction.atomic()`) and `delete_competency_rule_profile` (calls `profile.delete()`, lets `ProtectedError` propagate). Coordinate with the data-model ticket to set `on_delete=models.PROTECT` on `CompetencyCriteria.competency_rule_profile`; if that FK is not PROTECT, instead guard in `delete_competency_rule_profile` with `CompetencyCriteria.objects.filter(competency_rule_profile=profile).exists()`. Do not use SET_NULL and do not touch referencing criteria. Add APIClient tests for 200 update, 400 bad type/payload via update, 409 on referenced delete (assert the profile still exists and the criterion is unchanged), 204 on unreferenced delete, 403 non-staff, 404 unknown id.

---

## Context

Prior art:
- `src/openedx_tagging/rest_api/v1/views.py` `ObjectTagView` — mixin composition (`RetrieveModelMixin, UpdateModelMixin, ListModelMixin, GenericViewSet`) and the `MethodNotAllowed` pattern if PATCH is to be constrained.
- `src/openedx_tagging/rest_api/v1/exception_handlers.py` `TaggingExceptionHandlerMixin` — how an `APIException` subclass renders through DRF's handler.

Delete-protection design: ADR-0002 (learner-status protection) and the data-model ticket's `delete()`-override / `PROTECT` notes. Dependencies: 6.1 (viewset scaffolding) and 1.1 (the `on_delete=PROTECT` FK, per the coordination addendum). Layering: `.importlinter`. Sibling ticket: PLAT-1 (URL mount) blocks Postman verification.

---

## Open Questions

- `[BLOCKING] Permission model for updating/deleting a scope-bearing profile — same question as 6.1; resolve once for the set. (why it matters: sets the permission class and the wording/status of Scenario 6.) Options: A) Global-staff-only for MVP (is_staff) [recommended: A] B) Pluggable permission hook the platform overrides (PLAT-2) C) Hybrid taxonomy-via-oel_tagging / org+course staff-only.`
- `[non-blocking] Who may update or delete the instance-wide default (all-null) profile? (why it matters: only its create rule was fixed as staff-only; update/delete should match.) Options: A) Global-staff-only, mirroring create [recommended: A] B) Fold into whatever the general permission model resolves to.`

# 6.3

## Use Case

As an operator or authoring UI configuring Competency Criteria, I need to retrieve a single Competency Rule Profile by id and list the profiles recorded at a given scope, so that the criteria editor and the profile-management UI (6.4/6.5) can show which default rule applies at a scope and let an operator choose one.

*Role note: same permission caveat as 6.1 (see Open Questions). Whether list results are filtered to the requesting user's permitted scopes depends on the unresolved permission model.*

---

## Description

Build the REST retrieve (`GET /{id}/`) and list (`GET /`) endpoints for `CompetencyRuleProfile`, extending the viewset and reusing the 6.1 serializer, URL collection, and permission class. List supports filtering by scope query params (`organization`, `course`, `competency_taxonomy`) so a caller can ask "which profiles are recorded at this scope." A response row returns the profile's `id`, scope fields, `rule_type`, and `rule_payload`.

List returns the rows matching the filter literally, including the instance-wide default (all-null) row in an unfiltered list. **Resolving the single *effective* default for a criterion** when several profiles match (scope precedence and, since scoped duplicates are allowed, tie-breaking) is criteria-resolution logic used by evaluation and by the UC-5 criteria editor — it is not this endpoint's job and is out of scope here (see Open Questions).

For MVP, with the safe `is_staff`-only default, staff see all profiles and no per-user scope filtering of results is required. Whether the list is additionally filtered to only the scopes the requesting user may see depends on the permission model (Open Questions). This ticket is the read half of the CRUD set; it is read-only and changes no write behavior or authorization of the other endpoints.

**Depends on** the data-model ticket (1.1 / ADR-0002) and on 6.1 (shared serializer, URL collection, permission class, viewset shell).

**Out of scope:**
- Create, Update, Delete, and UI; the edx-platform URL mount (sibling ticket PLAT-1).
- Resolving the effective/winning profile for a criterion (scope precedence, the ADR-0002 fallback lookup order) — criteria-resolution logic, not this endpoint.

---

## Acceptance Criteria

These scenarios are verifiable via Postman against a local or dev environment (once PLAT-1 lands; before that, via openedx-core's API test client).

**Scenario 1: Retrieving a profile by id**
```
Given an existing Competency Rule Profile
When I send GET for that profile's id
Then the response returns 200
And the body includes id, rule_type, rule_payload, and the scope fields
```

**Scenario 2: Listing profiles filtered by scope**
```
Given profiles exist scoped to different organizations, courses, and taxonomies
When I send GET to the list endpoint with a competency_taxonomy filter
Then the response returns 200
And every profile in the response has that competency_taxonomy value
```

**Scenario 3: Listing when no profiles match the filter**
```
Given no profile is scoped to the requested organization
When I send GET to the list endpoint with that organization filter
Then the response returns 200
And the results list is empty
```

**Scenario 4: Retrieving a non-existent profile**
```
Given a profile id that does not exist
When I send GET for that id
Then the response returns 404
```

**Scenario 5: Unauthorized read (TBD, see Open Questions)**
```
Given a user who does not have permission to view rule profiles for the requested scope
When I send GET for a profile or the list
Then the profile data is not returned
And an authorization error is returned
```

---

## Technical Notes

### Files to Create

| File | Purpose |
| :---- | :---- |
| `src/openedx_learning/applets/cbe/rest_api/v1/tests/test_views_get.py` | APIClient retrieve/list tests |

### Modified Files

| File | Nature of modification |
| :---- | :---- |
| `src/openedx_learning/applets/cbe/rest_api/v1/views.py` | Add `RetrieveModelMixin`/`ListModelMixin`; `get_queryset` + `select_related`; `pagination_class` |
| `src/openedx_learning/applets/cbe/api.py` | Add `get_competency_rule_profile()` and `get_competency_rule_profiles()` |

### Implementation Notes

- **Mixins.** Add `mixins.RetrieveModelMixin` and `mixins.ListModelMixin`, reusing `CompetencyRuleProfileSerializer` for both. `retrieve` returns one profile by `id` (URL `.../competency-rule-profiles/<int:pk>/`, already registered by 6.1's router). `list` returns the profiles the user may view.
- **N+1.** Set `get_queryset` to `CompetencyRuleProfile.objects.all()` with `.select_related(<competency_taxonomy>)` if the serializer reads the related taxonomy, mirroring the `select_related` note in ticket 1.3.
- **Pagination.** Add a `PageNumberPagination` subclass as `pagination_class`, mirroring `TaxonomyPagination`; an empty match returns a paginated empty result.
- **Scope filtering.** Filter the queryset by the `organization`/`course`/`competency_taxonomy` query params literally. Do not attempt effective-default resolution here.

### Example Resolution Prompt

In `src/openedx_learning/applets/cbe/rest_api/v1/views.py`, add `mixins.RetrieveModelMixin` and `mixins.ListModelMixin` to `CompetencyRuleProfileViewSet`, reusing `CompetencyRuleProfileSerializer`. Set `get_queryset` to `CompetencyRuleProfile.objects.all()`, add `.select_related(...)` for the taxonomy scope FK if the serializer reads it, and filter by the `organization`/`course`/`competency_taxonomy` query params. Add a `PageNumberPagination` subclass as `pagination_class` (mirror `TaxonomyPagination`). In `api.py`, add `get_competency_rule_profile(pk)` (raising the model `DoesNotExist` for a 404) and `get_competency_rule_profiles(**filters)` returning the queryset. The URL is already registered by 6.1's router, so `GET /.../competency-rule-profiles/` and `GET /.../competency-rule-profiles/<int:pk>/` come for free. Add APIClient tests for 200 retrieve, 404 unknown id, 200 list, empty-list, 403 non-staff, 401 anonymous, asserting `id`/scope/`rule_type`/`rule_payload` in the body.

---

## Context

Prior art: `src/openedx_tagging/rest_api/v1/views.py` `TaxonomyView.get_queryset` (query-param handling and `select_related`/annotation pattern) and `TaxonomyPagination` for the pagination class; ticket 1.3's `select_related` N+1 note. Dependencies: 6.1 (viewset + router) and 1.1 (model). Layering: `.importlinter`. Sibling ticket: PLAT-1 (URL mount) blocks Postman verification.

---

## Open Questions

- `[BLOCKING] Permission model for viewing/listing scope-bearing profiles, and whether list results are filtered to the user's permitted scopes — same question as 6.1/6.2; resolve once for the set. (why it matters: sets the permission class, whether Scenario 5 fires, and whether list results are scope-filtered per user.) Options: A) Global-staff-only for MVP (staff see all; no per-user scope filtering) [recommended: A] B) Pluggable permission hook the platform overrides (PLAT-2), filtering list results to the caller's permitted scopes C) Hybrid taxonomy-via-oel_tagging / org+course staff-only.`
- `[non-blocking, blocking for the evaluation/resolution work] Precedence when multiple profiles match a criterion's scope (an org-, a course-, and the all-null default all apply, or duplicates at one scope). (why it matters: 6.1-6.3 return rows literally and do not need this, but UC-5 criteria default-resolution and evaluation cannot compute a single effective rule without it.) Options: A) Most-specific-scope-wins with a defined tiebreak (e.g. most recently updated) among duplicates [recommended: A] B) Extend ADR-0002's fallback lookup order to cover multi-match and duplicates explicitly C) Disallow the ambiguity at write time via a uniqueness rule.`
- `[non-blocking] External handle: id vs uuid (as in 6.1). Options: A) id for MVP [recommended: A] B) add uuid via an ADR-0002 amendment.`  
