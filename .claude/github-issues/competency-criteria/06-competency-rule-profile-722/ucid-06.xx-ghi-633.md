# [BE] Build Get endpoint for a Competency Rule Profile (scoped to user's permissions)

GitHub: https://github.com/openedx/openedx-core/issues/633 (#633, OPEN)
Cached: 2026-09-21

**Blocked by:** \#613/\#641 (data model), and \#631's shared scaffolding (`RuleProfileSerializer`, `is_rule_profile_in_use`, the `rest_api/v1/` package). Also the one-time `openedx-platform` wiring from \#664.

Repo: `openedx-core`.

## Use Case

As a Platform Administrator (or the Manage & Apply Competencies UI on their behalf), I want to fetch the rule profile that applies to a taxonomy — its own taxonomy-scoped profile if one exists, otherwise the system default — so that the UI can display the effective mastery rule and whether it's the inherited default or a taxonomy override.

## Description

**Current state**

No `CompetencyRuleProfile` API exists. Per the merged ADR, MVP has exactly two profile scopes: the single **system-default** (seeded, all-null scope) and **one taxonomy-scoped** profile per taxonomy; org/course are deferred. The frontend needs to show a taxonomy's *effective* rule, which is the taxonomy-scoped profile when present and the system default otherwise — and must visually distinguish an **inherited default** from a **taxonomy override**. This endpoint supplies the data behind that distinction.

**Requested change**

A read endpoint for rule profiles:

-   
- **Get a taxonomy's effective profile:** `GET /cbe/rest_api/v1/taxonomies/<taxonomy_id>/rule-profile/` → the taxonomy-scoped profile if one exists, else the system default, with a field indicating **which** (e.g. `source: "taxonomy" | "system_default"`) so the UI can render inherited-vs-overridden without a second call. Include `is_in_use`.  
    
- Permission: `can_change_taxonomy` on the referenced taxonomy for the taxonomy route.

**Explicitly out of scope**

- Create (\#631), Update/Archive (\#632).  
- **Deletability metadata** on the response — that ("determine whether each is deletable and include this metadata") is a separate guardrails ticket in **UC10** (task 10.4), not this one. Don't add it here.  
- Organization/course-scoped profiles (deferred) and their fields.  
- A standalone system-default GET endpoint.  
- Any UI (6.5).

## Acceptance Criteria

Verifiable via Postman.

```
Scenario: Get a taxonomy's effective profile when it has its own
  Given a taxonomy has a (non-archived) taxonomy-scoped profile, requester has can_change_taxonomy
  When GET /taxonomies/<id>/rule-profile/ is called
  Then the response is 200 with that profile's fields and "source": "taxonomy"

Scenario: Get a taxonomy's effective profile when it has none (falls back to system default)
  Given a taxonomy has no taxonomy-scoped profile (or only an archived one)
  When GET /taxonomies/<id>/rule-profile/ is called
  Then the response returns the system-default rule with "source": "system_default"

Scenario: is_in_use is reported
  Given a profile with at least one assigned CompetencyCriterion that has a StudentCompetencyCriteriaStatus row
  When the profile is fetched
  Then "is_in_use" is true

Scenario: Reject without permission / nonexistent taxonomy
  Given the requester lacks the applicable permission, or the taxonomy_id doesn't resolve to a CompetencyTaxonomy
  Then the response is 403 or 404
```

## Open Questions

- **\[non-blocking, owner: implementer\] `source` field naming.** Confirm the field/values used to signal inherited-default vs. taxonomy-override, so 6.5's UI and this contract match.

## Context

- Merged ADR (0002/0003, PR \#636): system-default identity (all-null scope); one taxonomy-scoped profile per taxonomy; `is_in_use` per ADR 0003 Decision 4\.  
- 07-14 meeting: MVP \= system \+ taxonomy; the inherited-vs-overridden visual distinction is a required capability the UI needs data for.  
- UC10 task 10.4 (spreadsheet): the separate "is this deletable" metadata work — deliberately NOT in this Get endpoint.  
- \#631: shared `RuleProfileSerializer`, `is_rule_profile_in_use`, scaffolding, permission reuse.  
- `src/openedx_tagging/rest_api/v1/views.py` (`ObjectTagCountsView` precedent for a plain-`Response` read), `rules.py`/`permissions.py` for gating.

## Technical Notes

### Files to Modify

| File | Nature |
| :---- | :---- |
| `src/openedx_learning/applets/cbe/api.py` | add `get_system_default_rule_profile()` (internal helper only, no dedicated view; query all-null scope, not by `scope_code` string) and `get_effective_rule_profile(competency_taxonomy_id)` (taxonomy-scoped if present & non-archived, else system default via the helper above; returns the profile \+ which source) |
| `src/openedx_learning/applets/cbe/rest_api/v1/views.py` | add `TaxonomyEffectiveRuleProfileView` (GET); reuse `RuleProfileSerializer`, add `source` to its output |
| `src/openedx_learning/applets/cbe/rest_api/v1/urls.py` | register `taxonomies/<int:taxonomy_id>/rule-profile/` |
| `.../rest_api/v1/tests/test_views.py`, `.../tests/test_api.py` | get / fallback-to-default / is\_in\_use / permission tests |

### Implementation Notes

`get_system_default_rule_profile()` queries `organization_id__isnull=True, course_id__isnull=True, competency_taxonomy_id__isnull=True` — never the `scope_code` string (the ADR marks that column internal-only). It's an internal helper only, no view calls it directly. `get_effective_rule_profile(taxonomy_id)` returns the taxonomy's non-archived profile if present, else the system default via that helper, tagging the result so the view can emit `source`. Do **not** compute or return deletability (UC10.4). Views are thin: resolve via the `api.py` function, serialize, return; `is_in_use` via the shared helper.

### Example Resolution Prompt

> In `openedx-core`, add a read endpoint for `CompetencyRuleProfile` (reusing \#631's `RuleProfileSerializer` and `is_rule_profile_in_use`). Add `get_system_default_rule_profile()` (internal helper, query the all-null-scope row, not the `scope_code` string) and `get_effective_rule_profile(competency_taxonomy_id)` (return the taxonomy's non-archived profile if present, else the system default via that helper, tagged with its source) to `applets/cbe/api.py`. Add `TaxonomyEffectiveRuleProfileView` at `taxonomies/<int:taxonomy_id>/rule-profile/` (GET, `can_change_taxonomy`) that returns the effective profile plus a `source` field ("taxonomy" | "system\_default") and `is_in_use`. No standalone system-default endpoint. Do NOT include deletability metadata (that's UC10.4). Return 200/403/404 per the AC.
