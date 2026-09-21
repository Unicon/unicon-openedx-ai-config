# [BE] Build Create endpoint for a Competency Rule Profile (scoped to user's permissions)

GitHub: https://github.com/openedx/openedx-core/issues/631 (#631, OPEN)
Cached: 2026-09-21

**Blocked by:** \#613/\#641 (the CBE data model, incl. PR \#636's `CompetencyRuleProfile` additions. Also depends on the one-time `openedx-platform` wiring ticket \#664 establishes (`INSTALLED_APPS` in `cms/envs/common.py`/`lms/envs/common.py` \+ the `cms/urls.py` include registering `openedx_learning.urls`); this endpoint registers inside the same `rest_api/v1/urls.py`, no repeated platform change. Also depends on \*\*6.8\*\* (\`CompetencyCriterion\` reassignment mechanics) for the function this endpoint calls to reassign existing criteria on create.

Repo: `openedx-core`.

## Use Case

As a Platform Administrator (or taxonomy/course author with taxonomy-edit rights), I want to create a Competency Rule Profile scoped to a specific Competency Taxonomy, so that criteria under that taxonomy inherit a default mastery rule (e.g. "score 75% or higher") instead of being configured one by one.

## Description

**Current state**

No `CompetencyRuleProfile` API exists. Per the merged ADR (0002/0003, PR \#636), a rule profile has three nullable scope columns (`organization_id`, `course_id`, `competency_taxonomy_id`, at most one set — enforced by a CHECK constraint and a unique `scope_code`), plus `rule_type`, `rule_payload`, and `archived`. The **system-default** profile is the single all-null-scope row, seeded via migration — it is never created through the API. **Only system-default and taxonomy-scoped profiles are in MVP; organization and course scopes are deferred** (their columns exist but no code creates or reads them yet — `taxonomy_overrides_org` is provisioned but dormant).

**Requested change**

A Create endpoint for a **taxonomy-scoped** rule profile (the only user-created scope in MVP):

- `POST /cbe/rest_api/v1/taxonomies/<taxonomy_id>/rule-profiles/` (competency taxonomy in the URL, not the body).  
- Requires `rule_type` (only `"Grade"` is supported now) and a valid `rule_payload` (for `Grade`: `op` in `gte`/`lte`/`eq`, `value` a 0.0–1.0 fraction).  
- **One profile per taxonomy** Reject a second non-archived profile for the same taxonomy with a clean 400/409, not a raw `IntegrityError` from the `scope_code` unique constraint.  
- Permission: `can_change_taxonomy` on the referenced taxonomy (reuses `openedx_tagging`'s existing predicate; "scoped to user's permissions" per the task title). No new permission class.

**Explicitly out of scope**

- Creating the system-default profile (seeded via migration only) — and organization/course-scoped profiles (deferred; omit those fields from the request/response schema entirely, not present-but-rejected).  
- Update, delete/archive (\#632) and Get (\#633).  
- The actual reassignment mechanics on affected `CompetencyCriterion` rows (the criteria ticket cluster owns that); this endpoint only gates creation behind the warning.  
- Any UI (6.5).

## Acceptance Criteria

Verifiable via Postman.

```
Scenario: Create a taxonomy-scoped profile (no in-use criteria)
  Given a Competency Taxonomy with no existing rule profile and no in-use criteria
  And the requesting user has can_change_taxonomy on that taxonomy
  When a POST is sent with "rule_type": "Grade" and a valid "rule_payload"
  Then the response is 201
  And the body includes "id", "competency_taxonomy_id", "rule_type", "rule_payload", "archived" (false), "is_in_use" (false)



Scenario: Reject a second profile for the same taxonomy
  Given a non-archived taxonomy-scoped profile already exists for the taxonomy
  When a POST is sent for that taxonomy
  Then the response is 400/409 (surfaced cleanly, not a raw IntegrityError)

Scenario: Reject an unsupported rule_type or invalid payload
  Given a POST sets "rule_type" to "Unknown", or a Grade payload with value outside 0.0-1.0 or op not in gte/lte/eq
  Then the response is 400

Scenario: Reject without permission / nonexistent taxonomy
  Given the user lacks can_change_taxonomy, or the taxonomy_id doesn't resolve to a CompetencyTaxonomy
  Then the response is 403 (permission) or 404 (nonexistent)
```

## Open Questions

-   
- **\[non-blocking, owner: implementer\]** `rule_payload` op/value validation belongs at the model layer (\#613/\#641) so create/update share it. Confirm it's there, else add a serializer validator.

## Context

- Merged ADR (`docs/openedx_learning/decisions/0002-competency-criteria-model.rst`, `0003-competency-criteria-versioning.rst`, PR \#636): scope columns \+ CHECK constraint \+ `scope_code` uniqueness; system-default seeded-not-created; `Grade` payload 0.0–1.0 with op in gte/lte/eq; ADR 0003 Decision 4 in-use warning triggers (Studio-level, per `0003-competency-criteria-versioning.rst:40-43`).  
- \#632 and \#633: sibling endpoints; whichever lands first creates the shared `rest_api/v1/` scaffolding, `RuleProfileSerializer`, and `is_rule_profile_in_use` helper — the others extend it.

## Technical Notes

### Files to Create / Modify

| File | Nature |
| :---- | :---- |
| `src/openedx_learning/applets/cbe/api.py` | add `create_rule_profile(competency_taxonomy_id, *, rule_type, rule_payload)`, which calls 6.8's reassignment function unconditionally (+ the shared `is_rule_profile_in_use` if \#632/\#633 haven't landed it) |
| `src/openedx_learning/applets/cbe/rest_api/v1/serializers.py` | `RuleProfileSerializer` base (id, rule\_type, rule\_payload, archived, is\_in\_use) \+ `TaxonomyScopedRuleProfileSerializer` (competency\_taxonomy\_id read-only) |
| `src/openedx_learning/applets/cbe/rest_api/v1/views.py` | `TaxonomyScopedRuleProfileCreateView(generics.CreateAPIView)` |
| `src/openedx_learning/applets/cbe/rest_api/v1/permissions.py` | reuse `TaxonomyObjectPermissions`/`can_change_taxonomy` scoped to the URL taxonomy |
| `src/openedx_learning/applets/cbe/rest_api/v1/urls.py` | register `taxonomies/<int:taxonomy_id>/rule-profiles/` |
| `.../rest_api/v1/tests/test_views.py`, `.../tests/test_api.py` | create \+ reassignment \+ duplicate \+ permission tests |

### Implementation Notes

`perform_create`: resolve the taxonomy from the URL and call `create_rule_profile(taxonomy_id, **validated_data)` — never `serializer.save()` directly (mirrors `TaxonomyView.perform_create` → `create_taxonomy`). `create_rule_profile` reassigns any existing criteria under the taxonomy to the new profile as part of the same transaction (Ticket 8's mechanics), unconditionally — no confirmation gate; the in-use warning is Studio's responsibility (ADR 0003 Decision 4), not this endpoint's. Pre-check duplicate scope with a query for a clean 400 rather than letting the `scope_code` unique constraint raise a raw `IntegrityError`. No model/migration/PII work here (that's \#613/\#641).

### Example Resolution Prompt

In `openedx-core`, add a Create endpoint for a taxonomy-scoped `CompetencyRuleProfile` (assume \#613/\#641 landed the model per ADR 0002/0003 PR \#636, \#664 landed the `openedx_learning.applets.cbe` REST scaffolding \+ platform wiring, and Ticket 8 landed a reassignment function for `CompetencyCriterion` rows). Add `create_rule_profile(competency_taxonomy_id, *, rule_type, rule_payload)` to `applets/cbe/api.py`, which unconditionally reassigns existing criteria under the taxonomy to the new profile via Ticket 8's function. Add `TaxonomyScopedRuleProfileCreateView(generics.CreateAPIView)` at `taxonomies/<int:taxonomy_id>/rule-profiles/`, gated by `can_change_taxonomy` on the URL taxonomy. Reject a second profile per taxonomy cleanly (400/409, not a raw IntegrityError), reject rule\_type other than "Grade" (400), reject Grade payloads with value outside 0.0-1.0 or op not in gte/lte/eq (400), 403 without permission, 404 for a nonexistent/non-competency taxonomy. Omit organization/course fields entirely. No confirmation flag anywhere in this endpoint. Tests per the AC.
