# [BE] Add an archived field to Tag, Taxonomy, and ObjectTag, and a deletion_locked field to ObjectTag

GitHub: https://github.com/openedx/openedx-core/issues/776 (#776, OPEN)
Cached: 2026-09-21

## User Story

As a platform administrator, I want the tagging data that competency mastery depends on to be able to record that it has been archived, and to record which tag associations something depends on, in order to have my deletions preserve learner mastery history instead of destroying it.

## Acceptance Criteria

There is no manual QA path. Acceptance is determined by a PR reviewer verifying the following against the model code, migration, and tests:

- [ ] `archived = models.BooleanField(default=False)` exists on `Taxonomy`, `Tag`, and `ObjectTag` in `src/openedx_tagging/models/base.py`.  
- [ ] `deletion_locked = models.BooleanField(default=False)` exists on `ObjectTag` only; `Tag` and `Taxonomy` do not get their own `deletion_locked` field.  
- [ ] One additive migration adds all four columns; no data migration or backfill is included.  
- [ ] The migration applies cleanly against a database holding existing taxonomies, tags, and tag associations, and every existing row reads back as `archived=False` (and, for `ObjectTag`, `deletion_locked=False`) with no other field changed.  
- [ ] `archived` and `deletion_locked` can be set independently on an `ObjectTag` (one `True` while the other stays `False`) with no other field affected.  
- [ ] No `archived_at` or `locked_at` companion field was added.  
- [ ] Both fields are registered as non-PII; `make pii_check` passes.  
- [ ] No read path, write path, filter, or delete branch anywhere reads or checks either field; the fields are inert on merge.  
- [ ] Field definitions and `help_text` match \#716's shape for `CompetencyCriteriaGroup.archived`/`CompetencyCriterion.archived`, for consistency across the feature.

## Description

`Taxonomy`, `Tag`, and `ObjectTag` in `openedx_tagging` can only be hard-deleted today. There is no way to archive one while keeping it readable, and no way for the tagging app to know that something outside it depends on a record. Both are needed before a delete can branch between removing a record and archiving it.

`deletion_locked=True` on an `ObjectTag` records that a learner status now depends on it: it means any future delete request against that association must archive it instead of removing the row. `Tag` and `Taxonomy` don't carry their own `deletion_locked` field; whether either one is locked is derived from whether any of the `ObjectTag`s beneath it are locked. `archived=True`, on any of the three models, means a record has already been archived along that path: it is hidden from active use, but its row and the learner history pointing to it stay in place.

This ticket adds the four fields and nothing else. They are inert on merge: \#777 adds the API that sets and reads the lock, \#778 makes archived records inert on read and write paths, and \#779 through \#781 add the delete branches that use both.

<details>
<summary>Technical Details</summary>

This section is background and a suggested approach, not the ticket's source of truth. The User Story and Acceptance Criteria define what must be true when the work is done.

### In short

**Why `archived` goes on all three but `deletion_locked` goes on only one.** Any of the three record types can be archived, so all three need somewhere to record that. But only a tag association is ever depended upon directly: competency mastery is earned through the association between a competency and a piece of content, and that association is the thing whose removal would orphan a learner's status. A tag or a taxonomy matters only because associations exist beneath it, so their answer to "is anything depending on this" is derived from those associations rather than stored separately. \#777 provides that derivation.

**Why deriving beats storing for the upper two.** A stored flag on a tag would have to be kept correct as associations come and go beneath it, which means either clearing it when the last association is unlocked, and getting that wrong loses learner history, or never clearing it, and then it only ever accumulates and stops meaning anything. One association carrying the fact, and the levels above reading down to it, has no such bookkeeping.

**Why a stored flag on the association rather than a lookup at delete time.** `openedx_tagging` must not know that competency-based education exists, and must not query another app's tables to decide whether a delete is safe. Storing the answer on the association row lets the owning feature push it in, and makes "is this in use" answerable inside the tagging app alone. The pushing side is \#777 and \#782.

**No timestamp companions.** Neither field gets an `archived_at` or `locked_at`. Nothing in the approved approach reads one, and a column no query uses is not free on tables this size.

### Implementation specifics

- **`archived = models.BooleanField(default=False)`** on `Taxonomy`, `Tag`, and `ObjectTag` in `src/openedx_tagging/models/base.py`.  
- **`deletion_locked = models.BooleanField(default=False)`** on `ObjectTag` only. Do not add it to `Tag` or `Taxonomy`; their in-use answer is derived in \#777.  
- **Mirror the field definition \#716 introduces** for `CompetencyCriteriaGroup` and `CompetencyCriterion`, so both sides of the feature look the same to a reader. Match its `help_text` wording and its `db_index` choice.  
- **Index for the queries that will actually run.** \#778 filters every tag and association read path on `archived`, and \#780 answers "is any association beneath this tag or taxonomy locked", so an index on `Tag.archived`, on `ObjectTag.archived`, and on `ObjectTag.deletion_locked`, or a composite covering the derivation query, is likely warranted, and `Taxonomy.archived` likely is not given how few taxonomy rows exist. Confirm against the queries \#778 and \#780 add rather than indexing everything by default.  
- **One additive schema migration**, no data migration. Both fields default to `False`, so existing rows need no backfill.  
- **PII:** both fields are non-PII. These three models already carry their annotations, so confirm with `make pii_check` that adding these fields does not change the outcome rather than adding new annotations.  
- **Do not change any read or write path here.** Adding a filter or a delete branch would collide with \#778 through \#781. The fields must be inert on merge.  
- **Tests** in the existing `openedx_tagging` model tests: all three models default `archived` to `False`; `ObjectTag` defaults `deletion_locked` to `False`; the two fields on `ObjectTag` can be set independently; the migration applies cleanly against a database holding existing taxonomies, tags, and associations and leaves them unarchived and unlocked.  
- **Out of scope:** the lock API and the derived in-use query (\#777), read and write inertness (\#778), every delete branch (\#779, \#780), the archive event fan-out (\#781), and any REST exposure of either field.

## Files to modify

| File | Nature of modification |
| :---- | :---- |
| src/openedx\_tagging/models/base.py | add `archived` to `Taxonomy`, `Tag`, and `ObjectTag`; add `deletion_locked` to `ObjectTag` only |
| src/openedx\_tagging/migrations/ | one additive schema migration for the four new columns and any indexes |
| tests/openedx\_tagging/ | default-value, independence, and migration tests in the existing model test module |

## Context

- The approved implementation approach for competency delete and edit guardrails, on \#655: the archive-versus-delete rule and why the lock is pushed in rather than looked up. Specifically the exchange starting at [this comment](https://github.com/openedx/openedx-core/issues/655#issuecomment-5361338847) and continuing through the `deletion_locked`\-only-on-`ObjectTag` resolution.  
- \#716 adds the equivalent `archived` field to `CompetencyCriteriaGroup` and `CompetencyCriterion`; match its shape.  
- `docs/openedx_learning/decisions/0003-competency-criteria-versioning.rst`, Decision 3, for the rule that a tag association becomes archive-only once a learner status references it.  
- Consumed by \#777, \#778, \#779, \#780, and \#781.

</details>
