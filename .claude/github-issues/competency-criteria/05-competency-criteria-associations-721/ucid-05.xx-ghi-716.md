# [BE] Add archived field to CompetencyCriteriaGroup and CompetencyCriterion

GitHub: https://github.com/openedx/openedx-core/issues/716 (#716, OPEN)
Cached: 2026-09-21

**Blocked by:** \#613 (the CBE data model these two models belong to).

Repo: `openedx-core`, single-repo. No `openedx-platform` changes.

## Use Case

As a developer implementing CBE's archive-vs-delete behavior across several tickets (\#674, \#675, the create-side archived-branch guard, and eventually \#681), I want `CompetencyCriteriaGroup` and `CompetencyCriterion` to have a settled `archived` field from the start, so that none of those tickets has to race to add it themselves or coordinate around who lands first.

## Description

**Current state**

Neither `CompetencyCriteriaGroup` nor `CompetencyCriterion` has an `archived` field. Multiple downstream tickets each need it to implement ADR 0002 Decision 7's archive-only retirement rule, and were drafted with "whichever lands first adds it" coordination language instead of a single owner.

**Requested change**

Add `archived = models.BooleanField(default=False)` to both `CompetencyCriteriaGroup` and `CompetencyCriterion`, in one migration. No `archived_at` companion field: `django-simple-history` (already applied per ADR 0003\) covers the "when." This ticket makes no behavior changes: nothing here sets the field to `True` or reads/filters on it, that's downstream tickets' scope.

**Explicitly out of scope**

- Setting `archived=True` anywhere.  
- Filtering or checking `archived` anywhere.  
- Any UI.

## Acceptance Criteria

There is no manual QA path. Acceptance is determined by a PR reviewer verifying the following against ADR 0002 and ADR 0003:

- [ ] `archived = models.BooleanField(default=False)` exists on both `CompetencyCriteriaGroup` and `CompetencyCriterion`.  
- [ ] One migration adds both columns.  
- [ ] No `archived_at` column was added.  
- [ ] `django-simple-history` already tracks both models (per ADR 0003); the new field is captured in the history table without further changes.  
- [ ] `archived` is registered as non-PII, matching `CompetencyRuleProfile.archived`'s existing category; `make pii_check` passes.  
- [ ] No backfill needed: greenfield field, no existing rows depend on a different default.

## Context

- \#613: the model definitions this ticket adds a field to.  
- Downstream consumers: \#674 and \#675 (set `archived=True` on the archive-vs-hard-delete branch), the archived-branch authoring-guard ticket (no GitHub issue yet; rejects new authoring against an archived row), and \#681 (not yet drafted; expected to filter `archived=False` by default).  
- ADR 0002 Decision 3 (`docs/openedx_learning/decisions/0002-competency-criteria-model.rst`): the `CompetencyRuleProfile.archived` precedent this field matches (boolean, no `archived_at`, non-PII).  
- ADR 0003 (`docs/openedx_learning/decisions/0003-competency-criteria-versioning.rst`): `django-simple-history` already applied to both models, answering the "when" without a separate timestamp field.

## Technical Details

**Data Structures**

```
CompetencyCriteriaGroup.archived: models.BooleanField(default=False)
CompetencyCriterion.archived: models.BooleanField(default=False)
```

**Logic**

None. This ticket only adds the columns and their migration; no function, view, or serializer changes.

### Example Resolution Prompt

> Add `archived = models.BooleanField(default=False)` to both `CompetencyCriteriaGroup` and `CompetencyCriterion` in `src/openedx_learning/applets/cbe/models.py`, and generate one migration for both. No `archived_at` companion field. Register `archived` as non-PII, matching `CompetencyRuleProfile.archived`'s existing annotation. Do not add any logic that sets, reads, or filters on the field, that belongs to downstream tickets, not this one.

## Files to create and modify

**New files**

| File | Purpose |
| :---- | :---- |
| `src/openedx_learning/applets/cbe/migrations/000X_add_archived_field.py` | Adds `archived` to both models in one migration. |

**Modified files**

| File | Nature of modification |
| :---- | :---- |
| `src/openedx_learning/applets/cbe/models.py` | Add `archived = models.BooleanField(default=False)` to `CompetencyCriteriaGroup` and `CompetencyCriterion`. |
| PII annotation registry (per \#613's own PII acceptance criteria) | Register `archived` as non-PII on both models. |
