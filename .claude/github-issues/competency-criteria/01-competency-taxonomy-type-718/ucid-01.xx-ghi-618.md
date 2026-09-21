# [BE] Update Get endpoint to return Taxonomy Type.

GitHub: https://github.com/openedx/openedx-core/issues/618 (#618, CLOSED)
Cached: 2026-09-21

## Use Case

As a Platform Administrator, I want the taxonomy retrieval API to report each taxonomy's type ("tags" or "competency"), so that the Taxonomies page can support displaying a badge for Competency Taxonomies and correctly gate access to the Competency Management page.

## Description

This ticket's implementation is entirely in **openedx-platform**, not openedx-core: `TaxonomyOrgSerializer` and `TaxonomyOrgView` (`openedx/core/djangoapps/content_tagging/rest_api/v1/`) gain a `taxonomy_type` field computed by checking for a related `CompetencyTaxonomy` row. No field, method, or enum is added to `openedx_tagging` or the CBE app, per [ADR 0013](../../docs/openedx_tagging/decisions/0013-competency-taxonomy-detection.rst) (merged via #662).

**Current behavior**

1. The frontend Taxonomies page reads taxonomy data from `GET /api/content_tagging/v1/taxonomies/{id}/` and `GET /api/content_tagging/v1/taxonomies/`, served by `TaxonomyOrgSerializer` (a subclass of openedx-tagging's `TaxonomySerializer`). Currently, nothing identifies whether a taxonomy is a Competency Taxonomy.
2. openedx-tagging's own `TaxonomySerializer` and its raw `/api/tagging/v1/taxonomies/...` endpoints have no knowledge of Competency Taxonomies and, per this ticket, never will.

**Requested change**

1. Add a read-only `taxonomy_type` `SerializerMethodField` to `TaxonomyOrgSerializer`, following the same additive pattern already used for `orgs`/`all_orgs` (`Meta.fields = TaxonomySerializer.Meta.fields + [...]`). Returned on both the single-taxonomy and list GET endpoints.
2. Value is `"competency"` if the `Taxonomy` instance has a related `CompetencyTaxonomy` row, `"tags"` otherwise. Never `null`.
3. `TaxonomyOrgView.get_queryset()` fetches the related `CompetencyTaxonomy` row alongside the `Taxonomy` queryset (via `select_related`) so the list endpoint costs no extra query per row.

**Depends on:**

- **#640** (CompetencyTaxonomy model, part of #613's CBE core data models) — hard blocker. Confirmed by repo search on 2026-07-29: the `CompetencyTaxonomy` model does not exist in code yet, only in ADR form (ADR 0002). This ticket cannot be finished, and its exact relation-name cannot be confirmed, until that model lands.
- **#614 / #628** (Create/Import endpoint accepting `taxonomy_type`) — soft dependency, needed only for the Postman-verifiable acceptance criteria's realistic end-to-end flow (creating a Competency Taxonomy through the API). A `CompetencyTaxonomy` row created directly (fixture, shell, admin) would also satisfy this ticket's AC.

**Explicitly out of scope**

- No "competency only" / "non-competency only" filter or query parameter on Get/List. The list endpoint keeps returning all taxonomy types together, undifferentiated.
- No change to content-tagging surfaces (Course Outline, Libraries). Tagging content with a Competency Taxonomy without linking Competency Criteria shall stay possible; this ticket adds no restriction there.
- No change to openedx-tagging's own `/api/tagging/v1/taxonomies/...` endpoints. Per ADR 0013, only openedx-platform's `/api/content_tagging/v1/taxonomies/...` endpoints gain `taxonomy_type`.
- No new field, method, or enum in `openedx_tagging` or the CBE app.

## Acceptance Criteria

These scenarios are verifiable via Postman, against openedx-platform's endpoints.

```
Scenario: Get a single Competency Taxonomy
  Given a Competency Taxonomy exists (a Taxonomy with a related CompetencyTaxonomy row)
  When a client sends GET /api/content_tagging/v1/taxonomies/{id}/ for that taxonomy
  Then the response has status code 200
  And the response body's "taxonomy_type" field equals "competency"

Scenario: Get a single standard tag taxonomy
  Given a standard (non-competency) taxonomy exists
  When a client sends GET /api/content_tagging/v1/taxonomies/{id}/ for that taxonomy
  Then the response has status code 200
  And the response body's "taxonomy_type" field equals "tags"
  And the field is never null

Scenario: List taxonomies of mixed type
  Given at least one Competency Taxonomy and at least one standard taxonomy exist
  When a client sends GET /api/content_tagging/v1/taxonomies/
  Then every Competency Taxonomy entry has "taxonomy_type" equal to "competency"
  And every other entry has "taxonomy_type" equal to "tags"
  And no entry's "taxonomy_type" is null
  And entries of both types are returned together, unfiltered
  And the list endpoint issues no additional query per row to determine taxonomy_type
```

## Open Questions

- The exact reverse-relation accessor Django generates on `Taxonomy` for `CompetencyTaxonomy` (e.g. `taxonomy.competencytaxonomy`, the MTI default) is unconfirmed until #640 lands with a concrete model and migration. Implementer: confirm against the actual model rather than assuming the default name, in case a custom `related_name` is used. Owner: implementer, once #640 merges.

## Technical Details

### Recommended Approach

Add `taxonomy_type` as a `SerializerMethodField` on `TaxonomyOrgSerializer`, the same shape already used for `orgs` and `all_orgs`:

```py
# openedx/core/djangoapps/content_tagging/rest_api/v1/serializers.py

class TaxonomyOrgSerializer(TaxonomySerializer):
    orgs = serializers.SerializerMethodField()
    all_orgs = serializers.SerializerMethodField()
    taxonomy_type = serializers.SerializerMethodField()

    class Meta:
        model = TaxonomySerializer.Meta.model
        fields = TaxonomySerializer.Meta.fields + ["orgs", "all_orgs", "taxonomy_type"]
        read_only_fields = ["orgs", "all_orgs", "taxonomy_type"]

    def get_taxonomy_type(self, obj) -> str:
        return "competency" if hasattr(obj, "competencytaxonomy") else "tags"
```

(Confirm the `competencytaxonomy` accessor name against #640's actual model before implementing; the right existence check depends on the concrete relation type #640 lands with, verified against the real model rather than assumed.)

`TaxonomyOrgView.get_queryset()` needs the matching `select_related` alongside its existing `prefetch_related("taxonomyorg_set__org")`, so the list endpoint's per-row check costs no extra query:

```py
# openedx/core/djangoapps/content_tagging/rest_api/v1/views.py
queryset = queryset.select_related("competencytaxonomy")
```

Per ADR 0013, this is the entire change. Nothing in `openedx_tagging`'s `Taxonomy` model, its base `TaxonomySerializer`, or the CBE app should reference this concept.

### Example Resolution Prompt

In `edx-platform`, add a read-only `taxonomy_type` field to `TaxonomyOrgSerializer` (`openedx/core/djangoapps/content_tagging/rest_api/v1/serializers.py`), following ADR 0013 (`openedx-core` `docs/openedx_tagging/decisions/0013-competency-taxonomy-detection.rst`): a `SerializerMethodField` returning `"competency"` if the `Taxonomy` instance has a related `CompetencyTaxonomy` row, `"tags"` otherwise, added to `Meta.fields` the same way `orgs`/`all_orgs` already are. Confirm the exact reverse-relation accessor name against the `CompetencyTaxonomy` model introduced by #640 (do not assume `competencytaxonomy` without checking, since #640 may not have landed yet — this ticket is blocked until it does). Update `TaxonomyOrgView.get_queryset()` to `select_related` that relation alongside its existing `prefetch_related("taxonomyorg_set__org")` so list responses issue no extra query per row. Do not touch `openedx_tagging`'s `Taxonomy` model or base `TaxonomySerializer` in openedx-core — the whole point of ADR 0013 is that this concept never appears there. Verify against the Acceptance Criteria above and add regression tests to the existing `TaxonomyOrgSerializer`/`TaxonomyOrgView` test coverage.

## Context

- [ADR 0013](https://github.com/openedx/openedx-core/blob/main/docs/openedx_tagging/decisions/0013-competency-taxonomy-detection.rst) (openedx-core, merged via #662) — the decision this ticket implements, including its Rejected Alternatives (an enum field on `Taxonomy`, an in-`openedx_tagging` relation check, and an overridable `get_type()` method).
- #640 — implements the `CompetencyTaxonomy` model this ticket detects; hard blocker.
- #613 — parent CBE core data model ticket.
- #614 / #628 — Create/Import endpoint accepting `taxonomy_type` on write; this ticket's read-side value ("tags"/"competency") matches those, but the two are otherwise independent under ADR 0013.
- #634 — Remove Taxonomy subclasses + system-level taxonomies; its planned removal of `Taxonomy._taxonomy_class`/`.cast()` is part of why ADR 0013 rejected an overridable `get_type()` method.
- `openedx/core/djangoapps/content_tagging/rest_api/v1/serializers.py:70` — current `TaxonomyOrgSerializer`, showing the `orgs`/`all_orgs` pattern this ticket mirrors.
- `openedx/core/djangoapps/content_tagging/rest_api/v1/views.py:50-100` — current `TaxonomyOrgView.get_queryset()`, showing the existing `prefetch_related`/`annotate` this ticket adds to.

## Files to create and modify

**Modified files**

| File | Nature of modification |
| :---- | :---- |
| `openedx/core/djangoapps/content_tagging/rest_api/v1/serializers.py` | Add `taxonomy_type` `SerializerMethodField` to `TaxonomyOrgSerializer`, appended to `Meta.fields` |
| `openedx/core/djangoapps/content_tagging/rest_api/v1/views.py` | Add `select_related` for the `CompetencyTaxonomy` relation to `TaxonomyOrgView.get_queryset()` |
| `openedx/core/djangoapps/content_tagging/rest_api/v1/tests/...` (confirm exact path) | Add coverage for a competency taxonomy, and a standard taxonomy, across both detail and list endpoints |
