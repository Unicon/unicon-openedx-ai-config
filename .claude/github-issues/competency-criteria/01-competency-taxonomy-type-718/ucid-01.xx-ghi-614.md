# [BE] Update taxonomy Create & Import endpoints to accept Taxonomy Type

GitHub: https://github.com/openedx/openedx-core/issues/614 (#614, CLOSED)
Cached: 2026-09-21

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
    
- **Coordination with \#618 (GET responses).** This ticket owns the write side of `taxonomy_type`: a `write_only=True` `ChoiceField` on `openedx_tagging`'s serializer. Issue \#618 owns the read side, implemented separately in openedx-platform's `TaxonomyOrgSerializer` per ADR 0013 (`docs/openedx_tagging/decisions/0013-competency-taxonomy-detection.rst`) — a different serializer in a different repo, not a second field on this one. The two don't share code or constants: \#618 derives its value directly from the `CompetencyTaxonomy` relation rather than reading anything this ticket writes.  
    
- **`create_import()` action.** Locate this action in `TaxonomyView` in `views.py` and apply the same `taxonomy_type` handling as `perform_create()`. The openedx-platform `TaxonomyOrgView.create_import()` calls `super().create_import()`, so if the parent handles `taxonomy_type`, the platform layer likely requires no code changes — only verification that the field is not stripped before the `super()` call.

### Example Resolution Prompt

Across openedx-core and openedx-platform, add `taxonomy_type` support to taxonomy creation and import. In `openedx-core/src/openedx_tagging/rest_api/v1/serializers.py`, add `taxonomy_type` as a write-only `ChoiceField` with `required=False` and `choices=["tags", "competency"]`. In `src/openedx_tagging/rest_api/v1/views.py`, update both `perform_create()` (around line 262\) and the `create_import()` action to surface `taxonomy_type` from validated data for use by higher layers — do not call `CompetencyTaxonomy` directly from this layer. In `openedx_learning/applets/cbe/api.py`, add `create_competency_taxonomy()`: call `create_taxonomy()` from `openedx_tagging`, then create the linked `CompetencyTaxonomy` row, wrapped in `transaction.atomic()`. Wire the dispatch to `create_competency_taxonomy()` at a layer that can see both `openedx_tagging` and the CBE applet — a CBE-provided view mixin overriding `perform_create()` is one viable approach. In `openedx-platform/openedx/core/djangoapps/content_tagging/rest_api/v1/views.py`, verify that `TaxonomyOrgView.create_import()` (lines 109–133) does not strip `taxonomy_type` before calling `super().create_import()`; patch if needed. Reject `"system"` and all other unsupported values with a 400 on both endpoints.  
