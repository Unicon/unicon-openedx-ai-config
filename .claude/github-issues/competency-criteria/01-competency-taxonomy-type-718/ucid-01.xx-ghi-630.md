# [BE][edx-platform] Verify Taxonomy Type passes through TaxonomyOrgSerializer

GitHub: https://github.com/openedx/openedx-core/issues/630 (#630, CLOSED)
Cached: 2026-09-21

## Use Case

As a Platform Administrator viewing the Taxonomies page, I want the edx-platform taxonomy API to include `taxonomy_type` so the page can render the Competency Taxonomy badge and gate access to the Competency Management page, without the frontend calling openedx-tagging directly.

## Description

**Current behavior**

1. The frontend Taxonomies page reads taxonomy data from edx-platform's own endpoint, serialized by `TaxonomyOrgSerializer` (`openedx/core/djangoapps/content_tagging/rest_api/v1/serializers.py:70-99`), not from openedx-tagging's `/api/tagging/v1/taxonomies/` directly.  
2. `TaxonomyOrgSerializer(TaxonomySerializer)` builds `Meta.fields` **additively**: `TaxonomySerializer.Meta.fields + ["orgs", "all_orgs"]`. This means once \#618 adds `taxonomy_type` to the parent's `Meta.fields`, it is inherited automatically — confirmed by reading the actual class, not assumed.

**Requested change**

1. Confirm (regression-test, not manual-only) that `taxonomy_type` appears in `TaxonomyOrgSerializer`'s detail and list responses once \#618 ships the field, with correct values for a plain and a system-defined taxonomy.  
2. No production source change is expected. If investigation at implementation time finds `Meta.fields` has since been rewritten as an explicit allowlist, patch it to include `taxonomy_type`.

**Depends on:** \#618 merging first; this ticket verifies the contract \#618 defines, it doesn't define its own.

**Explicitly out of scope**

- No change to openedx-tagging or the `CompetencyTaxonomy` model.  
- No filtering by taxonomy type on this endpoint.  
- No frontend badge/gating UI — this ticket only ensures the field reaches the frontend.

## Acceptance Criteria

See Acceptance Criteria of parent Github Issue \#618.

## Technical Details

## Files to create and modify

**Modified files**

| File | Nature of modification |
| :---- | :---- |
| `openedx/core/djangoapps/content_tagging/rest_api/v1/tests/...` (confirm exact path) | Add assertions that `taxonomy_type` appears with correct values in detail/list responses |

### Recommended Approach

No source change. Add one or two assertions to the existing `TaxonomyOrgSerializer` test coverage confirming `taxonomy_type` appears with correct values, gated on \#618 being merged. This converts a one-time manual check into a permanent regression guard against a future contributor rewriting `Meta.fields` as an explicit allowlist (the more common DRF idiom, and a plausible future refactor that would silently drop the field again).

**Example Resolution Prompt**

In `edx-platform`, confirm `TaxonomyOrgSerializer` (`openedx/core/djangoapps/content_tagging/rest_api/v1/serializers.py:70-99`) surfaces `taxonomy_type` once \#618 ships it. It is additive (`Meta.fields = TaxonomySerializer.Meta.fields + ["orgs", "all_orgs"]`), so no source change to `serializers.py` is expected. Bump the `openedx-core` pin to a version including the field. Find the existing tests covering `TaxonomyOrgSerializer`'s GET responses (search `openedx/core/djangoapps/content_tagging/rest_api/v1/tests/`) and add assertions that detail and list responses include `"taxonomy_type"`, with correct values for a plain taxonomy (`"tags"`) and a system-defined taxonomy (`"tags"`, never null). Do not modify `Meta.fields`, `get_orgs`, or `get_all_orgs` unless investigation finds they've since changed to an explicit allowlist.
