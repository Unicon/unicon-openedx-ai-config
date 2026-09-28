# [BE] openedx-core - Accept taxonomy_type on Create & Import endpoints

GitHub: https://github.com/openedx/openedx-core/issues/628 (#628, CLOSED)
Cached: 2026-09-25

Part of #614. See parent for use case, acceptance criteria, and architecture rationale.

**Depends on:** data model ticket (CompetencyTaxonomy model must exist) #613 

### Files to modify

| File | Change |
| :---- | :---- |
| `src/openedx_tagging/rest_api/v1/serializers.py` | Add `taxonomy_type` as `write_only=True` `ChoiceField` with `required=False`, `choices=["tags", "competency"]`. Define the valid-value constants in a shared location so this field and the CBE dispatch logic below can't drift apart. |
| `src/openedx_tagging/rest_api/v1/views.py` | Update `perform_create()` and `create_import()` to surface `taxonomy_type` from validated data. Do not call `CompetencyTaxonomy` from this layer. |
| `openedx_learning/applets/cbe/api.py` | Add `create_competency_taxonomy()`: call `create_taxonomy()` then create the linked `CompetencyTaxonomy` row in `transaction.atomic()`. |

### Key constraint

`openedx_tagging` must not import from `openedx_learning`. The dispatch to
`create_competency_taxonomy()` must happen at a layer that can see both packages — a
CBE-provided view mixin overriding `perform_create()` is one viable approach.

#### Example Resolution Prompt

In `src/openedx_tagging/rest_api/v1/serializers.py`, add `taxonomy_type` as a
write-only `ChoiceField` with `required=False` and `choices=["tags", "competency"]`;
define the valid-value constants (e.g. `TAXONOMY_TYPE_COMPETENCY = "competency"`) in a
shared location so this field and the CBE dispatch logic below stay in sync. In
`src/openedx_tagging/rest_api/v1/views.py`, update both `perform_create()` (around line
262) and the `create_import()` action to surface `taxonomy_type` from validated data —
do not call `CompetencyTaxonomy` directly from this layer. In
`openedx_learning/applets/cbe/api.py`, add `create_competency_taxonomy()`: call
`create_taxonomy()` from `openedx_tagging`, then create the linked `CompetencyTaxonomy`
row wrapped in `transaction.atomic()`. Wire the dispatch to
`create_competency_taxonomy()` at a layer that can see both packages — a CBE-provided
view mixin overriding `perform_create()` is one viable approach.

