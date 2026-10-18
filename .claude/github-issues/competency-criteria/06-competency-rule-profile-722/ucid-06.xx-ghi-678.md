# [OOS - BE] Register CompetencyRuleProfile in Django Admin (system-level default management)

GitHub: https://github.com/openedx/openedx-core/issues/678 (#678, OPEN)
Cached: 2026-09-21

This ticket still requires internal review by Unicon. It is now considered out of scope for the current project, but may be picked by up as future work.

**Issue \#678.** Backend, `openedx-core` (single repo). Gives platform administrators a management surface for the **system-level** rule profile — the platform-wide default that \#646 deliberately keeps read-only in the authoring UI.

**Blocked by:** \#613 (the CBE data model, which defines `CompetencyRuleProfile`). Related: \#631/\#632/\#633 (the REST endpoints; this admin surface is independent of them), and \#646 (the authoring UI that shows the system default read-only and points its editing here).

Repo: `openedx-core`. The registration lives in the CBE applet; it surfaces in Studio's admin site automatically because the app is already in `INSTALLED_APPS` (wired by \#631). No `openedx-platform` change.

## Use Case

As a platform administrator, I want to view and edit the system-level default Competency Rule Profile through Django Admin, so that I can set the platform-wide mastery default (e.g. "score 70% or better") that new competency criteria inherit, without a bespoke authoring screen — since the taxonomy authoring UI intentionally does not expose editing of the system default.

## Description

**Current state**

`CompetencyRuleProfile` (per ADR 0002 Decision 3\) has three nullable scope columns (all null \= the single system-level default), a generated `scope_code`, `rule_type`, `rule_payload`, and `archived`. The system default is seeded via migration and is never created or deleted through the REST API; its `rule_type`/`rule_payload` are editable like any profile. \#646 renders it read-only in the taxonomy authoring UI and explicitly defers editing the platform-wide default to a platform-admin surface outside authoring. No Django Admin registration exists for the CBE applet's models today.

**Requested change**

Register `CompetencyRuleProfile` in the CBE applet's Django Admin so a platform administrator can:

- See the existing rule profiles in a list, with the system-level default (all-null scope) clearly identifiable.  
- Edit the system-level default's rule (`rule_type`, `rule_payload`), which is the primary purpose of this surface.  
- View the scope columns and generated `scope_code` as **read-only** (scope is structural and, for the system default, always null; `scope_code` is generated).

**Explicitly out of scope**

- Editing the system default through the authoring UI (\#646) — this admin surface is the platform-admin path instead.  
- The REST endpoints (\#631/\#632/\#633).  
- Creating or deleting the system-level default (seeded via migration; archiving is archive-only per ADR 0002 Decision 7).  
- Organization- and course-level rule profiles (deferred).  
- Any in-use edit warning/confirmation flow — Django Admin does not carry the authoring warning; whether admin should surface one is an Open Question, not built here by default.

## Acceptance Criteria

Verifiable via the Django Admin site.

```
Scenario: The rule profile list is visible to a platform admin
  Given a platform administrator is logged into the Django Admin site
  When they open the CompetencyRuleProfile admin list
  Then existing rule profiles are listed
  And the system-level default (all scope fields null) is identifiable in the list

Scenario: Edit the system-level default's rule
  Given the system-level default CompetencyRuleProfile exists
  When the admin opens it and changes its rule_payload (e.g. the threshold) to a valid value and saves
  Then the change is persisted
  And subsequent evaluations resolve to the updated default (no retroactive change to recorded learner statuses)

Scenario: Scope and scope_code are read-only
  Given the admin is editing a CompetencyRuleProfile
  Then the scope columns and the generated scope_code are shown read-only
  And they cannot be edited through the admin form

Scenario: A non-admin cannot reach the surface
  Given a user without Django Admin / staff access
  When they attempt to open the CompetencyRuleProfile admin
  Then access is denied per the standard admin permission gate
```

## Open Questions

- **\[non-blocking, owner: architect/BA\] In-use edits via admin.** Editing an in-use profile is forward-only per ADR 0003 (existing learner statuses unchanged, no recompute), and the authoring UI (\#646) surfaces a warning/confirmation. Django Admin has no equivalent gate. Confirm whether that's acceptable for the platform-admin path (admins are trusted and the semantics are the same either way) or whether a `readonly`/warning treatment is wanted in admin.  
- **\[non-blocking, owner: BA\] Scope of the registration.** This registers the model, so all profiles (including any taxonomy-level ones) become visible/editable in admin, with the system default as the intended target. Confirm whether that's desired, or whether the admin should constrain the changelist to the system default only.  
- **\[non-blocking, owner: implementer\] Archive toggle.** Whether the `archived` boolean should be editable in admin (it's archive-only via the API per ADR 0002 Decision 7; admin could either expose it or leave it read-only).

## Context

- ADR 0002 (`docs/openedx_learning/decisions/0002-competency-criteria-model.rst`), Decision 3: `CompetencyRuleProfile` fields (scope columns, generated `scope_code`, `rule_type`, `rule_payload`, `archived`); the system default is the single all-null-scope row, seeded via migration, API-editable but never API-created/deleted.  
- ADR 0003 (`docs/openedx_learning/decisions/0003-competency-criteria-versioning.rst`), Decision 4: editing an in-use profile is forward-only; no retroactive change to recorded statuses.  
- \#646: the taxonomy authoring UI that shows the system default read-only and points its editing to a platform-admin surface (this ticket).  
- \#613: the data model this depends on.  
- Admin-registration precedent: `openedx_tagging`'s admin registration (`src/openedx_tagging/admin.py`) — mirror its `ModelAdmin` conventions (list display, `readonly_fields`) for this new registration.

## Technical Notes

### Files to Create

*Conditional — check first whether \#613 already created an `admin.py` for the applet:*

| File | Purpose |
| :---- | :---- |
| `src/openedx_learning/applets/cbe/admin.py` | Register `CompetencyRuleProfile` with a `ModelAdmin`; if the file already exists, add the registration to it rather than creating a second. |
| `src/openedx_learning/applets/cbe/tests/test_admin.py` | Admin tests: the changelist loads, the system default is editable, scope/`scope_code` are read-only, permission gate holds. |

### Files to Modify

| File | Nature |
| :---- | :---- |
| `src/openedx_learning/applets/cbe/admin.py` | If \#613 already created this file, add the `CompetencyRuleProfile` registration here. |

### Implementation Notes

Register `CompetencyRuleProfile` via a `ModelAdmin` in the CBE applet's `admin.py`, mirroring `openedx_tagging`'s admin conventions. Set `readonly_fields` for the scope columns and the generated `scope_code` (structural / generated, never hand-edited); leave `rule_type` and `rule_payload` editable. Give `list_display` enough to distinguish the system default (all-null scope) from any scoped profiles at a glance. Editing is a direct model save — the forward-only semantics come from the model/evaluation, not from admin logic; do not add recompute or status-mutation here. No new migration, model change, or REST work belongs in this ticket. No PII annotation change (`CompetencyRuleProfile` is non-personal configuration).

### Example Resolution Prompt

> In `openedx-core`, register `CompetencyRuleProfile` in the CBE applet's Django Admin. In `src/openedx_learning/applets/cbe/admin.py` (create it if \#613 hasn't), add a `ModelAdmin` for `CompetencyRuleProfile` mirroring `src/openedx_tagging/admin.py`'s conventions: a `list_display` that makes the system-level default (all scope fields null) identifiable, and `readonly_fields` covering the scope columns and the generated `scope_code`, with `rule_type` and `rule_payload` editable. Editing saves directly (forward-only semantics are inherent to evaluation, not enforced here; no recompute). Add `src/openedx_learning/applets/cbe/tests/test_admin.py`: the changelist loads for a staff user, the system default's `rule_payload` can be edited and persists, scope/`scope_code` are read-only, and a non-staff user is denied. Do not build any REST endpoint, migration, or model change; do not expose creating or deleting the system default. The app is already in `INSTALLED_APPS`, so no `openedx-platform` change is needed for the registration to appear in Studio's admin site.
