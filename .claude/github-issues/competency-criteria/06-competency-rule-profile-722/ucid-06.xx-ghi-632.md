# [BE] Build Update / Delete (archive) endpoint for a Competency Rule Profile (scoped to user's permissions)

GitHub: https://github.com/openedx/openedx-core/issues/632 (#632, OPEN)
Cached: 2026-09-21

**Blocked by:** \#613/\#641 (data model), and \#631's shared scaffolding (`RuleProfileSerializer`, `is_rule_profile_in_use`, the `rest_api/v1/` package) — whichever of \#631/\#632/\#633 lands first creates it. Also the one-time `openedx-platform` wiring from \#664.

Repo: `openedx-core`.

## Use Case

As a Platform Administrator, I want to update a Competency Rule Profile's rule (and archive a taxonomy-scoped one I no longer want), so that I can adjust the default mastery threshold — while being warned before a change affects learners who already have recorded statuses, and without ever hard-deleting a profile that learner history depends on.

## Description

**Current state**

No `CompetencyRuleProfile` API exists. Per the merged ADR: a profile's scope fields are **immutable after creation** — only `rule_type`/`rule_payload` may be edited. Retirement is **archive-only, never a hard delete**, even pre-use (a carve-out from the general delete-protection rule) via the `archived` column; archived profiles remain queryable so existing criteria and learner history stay resolvable. The **system-default** profile is **not edited through this API at all** (6.7, Django admin only) — this ticket covers **taxonomy-scoped** profiles exclusively.

**Requested change**

- **Update** `PATCH /cbe/rest_api/v1/rule-profiles/<pk>/` — edits `rule_type`/`rule_payload` only, for  a **taxonomy-scoped** profile (permission: `can_change_taxonomy` on its taxonomy; the system default is 6.7/Django-admin only, not this endpoint) and to the **system-default** profile (permission: `is_taxonomy_admin`/platform-admin only. Attempting to change any scope field returns 400 (never silently ignored). **No backend in-use gate** (2026-07-20): ADR 0003 Decision 4's warning/confirmation requirement is a Studio-level guardrail (`0003-competency-criteria-versioning.rst:40-43`), not an API requirement — this endpoint applies the update unconditionally; the warning dialog lives in Studio (6.5).  
-   
- **Delete \= archive** `POST /cbe/rest_api/v1/rule-profiles/<pk>/archive/` — sets `archived = true`, idempotent. Taxonomy-scoped only; the system-default cannot be archived/deleted. **No in-use gate on archive** — archiving doesn't retroactively change what already-resolved criteria point to (ADR 0003 Decision 4 lists edit / reassignment / override-switching as the warning triggers; archiving is not among them). Never a hard delete; no `DELETE` verb.

**Explicitly out of scope**

- Creating profiles (\#631) and Get (\#633).  
- Organization/course-scoped profiles (deferred) and their fields.  
- **System-default profile updates** (2026-07-20: Ticket 7, Django admin only — not this endpoint).  
- Un-archive/reactivation.  
- Reassignment mechanics on `CompetencyCriterion` rows (6.8 owns it).  
- Any UI (6.5).

## Acceptance Criteria

Verifiable via Postman.

```
Scenario: Update a taxonomy-scoped profile's rule when not in use
  Given a taxonomy-scoped profile exists and is not in use, requester has can_change_taxonomy
  When a PATCH updates "rule_type"/"rule_payload"
  Then the response is 200 and the change is applied

Scenario: In-use edit requires confirmation
  Given a taxonomy-scoped (or system-default) profile is in use
  When a PATCH changes a rule field  Then the response is 200 and the change is applied

Scenario: Reject a scope-field change
  Given any profile exists
  When a PATCH includes "competency_taxonomy_id" (or organization_id/course_id)
  Then the response is 400 identifying the scope field as immutable


Scenario: Archive a taxonomy-scoped profile (no in-use gate)
  Given a taxonomy-scoped profile, in use or not
  When an archive request is sent (no confirm flag)
  Then the response is 200 and the profile is archived
  And a subsequent read shows "archived": true, and the row + referencing criteria remain resolvable

Scenario: System-default cannot be archived
  When an archive request targets the system-default profile
  Then the response is 400/403 (archiving the seeded default is not allowed)

Scenario: No hard delete
  When a DELETE verb is sent to the profile endpoint
  Then the response is 405

Scenario: Reject update/archive without permission
  Given the requester lacks the applicable permission
  Then update and archive return 403
```

- 

## Context

- Merged ADR (0002 Decisions 3 & 7, 0003 Decision 4, PR \#636): scope immutability; archive-only, never hard-delete; the three in-use warning triggers (edit, reassignment, override-switch) — archive is not one.  
- 07-14 meeting: system-level rule "people in these areas will not be able to edit"; taxonomy-level editable by taxonomy/course authors.  
- \#631: shared scaffolding, `RuleProfileSerializer`, `is_rule_profile_in_use`, permission reuse.  
- `src/openedx_tagging/rules.py` (`is_taxonomy_admin`, `can_change_taxonomy`), `rest_api/v1/permissions.py` (`TaxonomyObjectPermissions`).

## Technical Notes

### Files to Modify

| File | Nature |
| :---- | :---- |
| `src/openedx_learning/applets/cbe/api.py` | add `update_rule_profile(profile_id, *, rule_type=None, rule_payload=None)` and `archive_rule_profile(profile_id)` (idempotent) |
| `src/openedx_learning/applets/cbe/rest_api/v1/views.py` | add `RuleProfileDetailView(generics.RetrieveUpdateAPIView)` (patch only for writes here; get is \#633) and `RuleProfileArchiveView(generics.GenericAPIView)` |
| `src/openedx_learning/applets/cbe/rest_api/v1/permissions.py` | `can_change_taxonomy` for taxonomy-scoped |
| `src/openedx_learning/applets/cbe/rest_api/v1/urls.py` | register `rule-profiles/<int:pk>/` (patch) and `rule-profiles/<int:pk>/archive/` (post) |
| `.../rest_api/v1/tests/test_views.py` | update / immutable-scope / archive / no-hard-delete / permission tests |

### Implementation Notes

Archive is a **dedicated `POST .../archive/` action**, not `PATCH {"archived": true}` — keeps rule-editing and lifecycle archiving on separate code paths, legible from the URL (neither is backend in-use-gated, only frontend in-use-gated). `perform_update`: reject any scope-field key (400); else call `update_rule_profile(...)` unconditionally (never `serializer.save()` directly; no in-use confirmation gate). Resolve the applicable permission via `can_change_taxonomy` on the target row's taxonomy (system-default is out of scope for this endpoint so no platform-admin branch is needed here). `archive_rule_profile` refuses the system-default. `http_method_names` excludes `delete` on the detail view (→ 405).

### Example Resolution Prompt

In `openedx-core`, add Update and Archive for `CompetencyRuleProfile` (reusing \#631's `RuleProfileSerializer`, `is_rule_profile_in_use`). Add `update_rule_profile(profile_id, *, rule_type=None, rule_payload=None)` and `archive_rule_profile(profile_id)` (idempotent; refuses the system-default) to `applets/cbe/api.py`. Add `RuleProfileDetailView(generics.RetrieveUpdateAPIView)` at `rule-profiles/<int:pk>/` (`http_method_names` excludes delete) whose `perform_update` rejects scope-field changes (400) and calls `update_rule_profile` unconditionally (no in-use confirmation gate). Add `RuleProfileArchiveView` at `rule-profiles/<int:pk>/archive/` (POST, no in-use gate). Gate taxonomy-scoped edits to `can_change_taxonomy`; system-default is out of scope for this endpoint (6.7, Django admin) and its archive is disallowed. Return 200/400/403/405 per the AC. Never implement a hard delete.
