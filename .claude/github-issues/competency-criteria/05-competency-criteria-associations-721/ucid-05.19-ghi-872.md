# [BE] Enforce one root Competency Criteria Group per competency in the database

GitHub: https://github.com/openedx/openedx-core/issues/872 (#872, Open)
Cached: 2026-10-15

## User Story

As a platform maintainer, I want the uniqueness of root and course-level `CompetencyCriteriaGroup` rows enforced by a database constraint, in order to keep the criteria tree consistent even when a code path creates groups without taking the competency's Tag row lock.

## Description

`CompetencyCriteriaGroup` has one unconditional unique constraint on `(tag, course, parent)`, added in #847. It keeps one course-level group per competency and course, but it doesn't constrain roots: a unique index treats each NULL as distinct, and a root has both `course` and `parent` NULL. MySQL has no partial unique indexes, so "one root per tag" can't be written as a conditional constraint either. Today one root per tag relies entirely on the `select_for_update()` lock that `associate_competency_criterion()` takes on the competency's `Tag` row.

`CompetencyRuleProfile` solved the same problem with a derived `scope_code` column (ADR-0002 Decision 3). We need to apply that pattern to `CompetencyCriteriaGroup`: a derived code that is set for root groups, null for every other group, and covered by an unconditional unique constraint, while the existing `(tag, course, parent)` constraint keeps protecting course-level groups.

## Context

- Follow-up to #665, requested in the #847 review: https://github.com/openedx/openedx-core/pull/847#discussion_r4285673720.
- Blocked by PR #847, which adds the constraint and migration this ticket builds on.
- #674 and #675 archive groups; #717 defines what creation does with an archived group.

## Acceptance Criteria

These scenarios are verifiable through the PR's tests or a Django shell against MySQL; no request to the create-criterion endpoint behaves differently.

```
Scenario: Reject a second root group for a competency
  Given a competency already has a root CompetencyCriteriaGroup
  When a second root CompetencyCriteriaGroup is saved for the same competency, outside the create-criterion flow and without the competency's lock
  Then the database rejects it
  And the competency still has exactly one root group

Scenario: Reject a second root group when the existing root is archived
  Given a competency's only root CompetencyCriteriaGroup is archived
  When a second root CompetencyCriteriaGroup is saved for the same competency
  Then the database rejects it
  And the archived root is unchanged

Scenario: Reject a second course-level group for the same competency and course
  Given a competency has a course-level CompetencyCriteriaGroup for Course X, live or archived
  When a second course-level group for the same competency and Course X is saved, individually or in a bulk insert
  Then the database rejects it

Scenario: Archive a root or course-level group with no extra step
  Given a competency has a live root and a live course-level group for Course X
  When either group is archived, individually or in a bulk update that only marks it archived
  Then the archive succeeds
  And a second root, or a second course-level group for Course X, is still rejected

Scenario: Reactivate an archived root
  Given a competency's only root CompetencyCriteriaGroup is archived
  When the root is reactivated
  Then the reactivation succeeds
  And the reactivated root is still the competency's only root group

Scenario: A hard-deleted root frees its place
  Given a competency has a root CompetencyCriteriaGroup with course-level and leaf groups under it
  When the root is hard-deleted
  Then the root and all of its descendant groups are deleted
  And a new root CompetencyCriteriaGroup can then be saved for that competency

Scenario: Delete a course run that has course-level groups
  Given a course run has course-level CompetencyCriteriaGroups with leaf groups under them
  When the course run is deleted
  Then the deletion succeeds, and the course-level groups and their leaves are deleted with it

Scenario: Courses and leaves are not limited
  Given a competency has a root CompetencyCriteriaGroup
  When course-level groups are saved for several different courses, and several leaf groups, live or archived, are saved under one course-level group
  Then every one of them is saved
```

ADR-0002 is amended by a person to describe the new rule and how it is enforced.

<details>
<summary>Technical Details</summary>

This is a suggested approach, not the source of truth. The User Story, Description, and Acceptance Criteria define what must be true when the work is done.

**Summary**

`CompetencyCriteriaGroup` gets a `scope_code` column that is set only for root groups, computed in `save()` the way `CompetencyRuleProfile` computes its own, and covered by an unconditional unique constraint. An archived root keeps its code, so it keeps blocking a second root, which matches #717 reactivating archived roots in place. The `(tag, course, parent)` constraint from #847 stays and keeps protecting course-level groups on every write path. One migration checks existing data for duplicate roots before changing anything, then adds and backfills the column.

**Approach**

1. In `CompetencyCriteriaGroup` (`src/openedx_learning/applets/cbe/models/criteria.py`), add `scope_code = CharField(max_length=255, null=True, editable=False)` and a `_compute_scope_code()` that returns `f"tag:{tag_id},course:"` for a root (`parent` is null) and `None` for every other group. The value does not depend on `archived`. The `"tag:…,course:"` format matches the profile's and leaves room to cover course-level groups later if product decides archived groups should be replaceable.
2. Add a `save()` that sets `scope_code` from `_compute_scope_code()` and adds `"scope_code"` to `update_fields` when the caller passes them. It does not need the profile's `full_clean()` call.
3. Add `UniqueConstraint(fields=["scope_code"])` and `CheckConstraint(condition=Q(scope_code__isnull=True) | Q(parent__isnull=True))`, so only a root can hold a code. Keep the `(tag, course, parent)` constraint unchanged. The check must stay one-directional ("a code implies a root"), not "every root has a code": on MySQL, Django's `CASCADE` first sets the nullable `parent` and `course` keys of the rows it is about to delete to NULL, so the reverse direction would make every child look like a root without a code and reject deleting a root.
4. Change `history` to `HistoricalRecords(excluded_fields=["scope_code"])`, as the profile does.
5. In migration `0016_criteria_group_scope_code.py`, run a read-only `RunPython` first that raises, naming the tag and group ids, if any tag has more than one root, live or archived. Then add the column, backfill it for roots with a second `RunPython` (the historical model has no custom `save()`, as `0005_seed_default_rule_profile.py` notes), and add both constraints. The duplicate check comes first because MySQL commits each schema change immediately, so an error raised after the column is added would leave it in place and the migration unrecorded.
6. In `associate_competency_criterion()` (`src/openedx_learning/applets/cbe/api.py`), keep the Tag row lock and `_create_leaf_group()` as they are, but rewrite the comment on the lock: one root per tag is now enforced by the database, and the lock stays because it serializes the duplicate-association check. A request without `group_id` creates a fresh leaf every time, so no unique index can catch two concurrent criteria for the same content in different leaves. After this ticket, every rule on the stored tree is enforced by the database, and the lock only serializes that request-level check: the same content may legitimately sit in two explicitly named groups, so the data itself can't forbid it.

`bulk_create()` skips `save()`, so a root inserted in bulk would get no code and no protection. No code creates roots in bulk today; #694's course copy reuses the existing root. Archiving needs no change: `scope_code` does not depend on `archived`, so the bulk archive in #675 and the root reactivation in #717 work as written.

Tests must cover a second root created directly without the lock, next to a live root and next to an archived one; deleting a root and a course run that have descendants on MySQL; and the migration's duplicate check and backfill over roots, course-level groups, leaves and archived rows. Existing tests that create two roots for one tag, such as the `logic_operator` test in `test_criteria_group.py`, need a second tag.

Out of scope: freeing an archived group's place for a replacement (#717 keeps archived groups permanent for MVP), and removing the Tag row lock.

**Files to create and modify**

| File | Change |
| --- | --- |
| src/openedx_learning/applets/cbe/models/criteria.py | modified: `scope_code`, `_compute_scope_code()`, `save()`, constraints, history exclusion |
| src/openedx_learning/migrations/0016_criteria_group_scope_code.py | new: duplicate check, column, backfill, constraints |
| src/openedx_learning/applets/cbe/api.py | modified: the comment on the Tag row lock |
| tests/openedx_learning/applets/cbe/test_criteria_group.py | modified: root constraint tests, and existing tests that create two roots for one tag |
| tests/openedx_learning/test_migrations.py | new: duplicate check and backfill |

**Additional context**

- `CompetencyRuleProfile.scope_code` in `src/openedx_learning/applets/cbe/models/criteria.py` is the precedent; ADR-0002 Decision 3 and Rejected Alternative 6 (`docs/openedx_learning/decisions/0002-competency-criteria-model.rst`) explain it.
- The ADR-0002 amendment covers the new column in Decision 2's field list and the new constraint in Decision 5's index list. It should also correct Decision 2's `course_id` line, which says every group in a course subtree carries the course; the code leaves a leaf's course empty, and this ticket relies on that.
- `tests/openedx_tagging/test_migrations.py` shows the `django_test_migrations` `migrator` fixture this repo uses to test a backfill.
- `tests/openedx_learning/applets/cbe/test_criteria_group_deletion.py` deletes a course run and a root with descendants, which guards step 3.

</details>
