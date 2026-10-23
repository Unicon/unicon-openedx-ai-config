# Mastery status lookup + learner progress models

GitHub: https://github.com/openedx/openedx-core/issues/642 (#642, CLOSED)
Cached: 2026-10-22

# Mastery status lookup + learner progress models

## User Story

As a learner, I want my current mastery status recorded for each competency, criteria
group, and individual criterion, in order to see which requirements I have already met and
which are still outstanding.

## Acceptance Criteria

- [ ] The three mastery status values, `AttemptedNotDemonstrated`, `PartiallyAttempted` and `Demonstrated`, exist and their order is available to the database, so that raising a status can be written as one conditional `UPDATE` rather than a read followed by a write. A test asserts that a write of a lower value against a higher stored value changes no row, using a single statement.
- [ ] `StudentCompetencyStatus` rejects `AttemptedNotDemonstrated` and accepts only `Demonstrated` and `PartiallyAttempted`. The rejection holds on every write path, including `QuerySet.update()` and `bulk_create()`, which never call `clean()`. Tests cover a direct save and a bulk write.
- [ ] Learner status rows are updated in place, one row per learner and node under a unique constraint, per ADR-0003 Decision 5 and ADR-0002 Decision 6, which lists `created` and `modified` on all three tables. Each table carries both `created` (`auto_now_add=True`) and `modified` (`auto_now=True`). No history package is applied. #613 cites this as "ADR-0003 Decision 5 as amended on 2026-07-27"; that changelog entry no longer exists, because ADR-0003 Decision 5 was rewritten again afterwards. The requirement is unchanged, only the citation.
- [ ] No monotone-write logic and no staff-edit path land here. The models accept any status value the caller writes; the rules that decide which writes are allowed, that an automatic write may raise a status but never lower it and that a staff correction may lower one, are enforced in the API layer. Those two rules now live only in ADR-0004 Decisions 4 and 6. #613 also attributes them to ADR-0003 Decision 5, which no longer contains them.
- [ ] The indexes from ADR-0002 Decision 5 that belong to these models are present and unique: 6 (`StudentCompetencyCriteriaStatus(user_id, competency_criteria_id)`), 7 (`StudentCompetencyCriteriaGroupStatus(user_id, competency_criteria_group_id)`), 8 (`StudentCompetencyStatus(user_id, oel_tagging_tag_id)`) and 10 (`CompetencyMasteryStatuses(status)`). All four are unique; a plain index in any of those positions fails this criterion. For 6, 7 and 8 the uniqueness is not a performance detail: it is what makes "one row per learner and node" true, which is the precondition for the in-place updates above.
- [ ] The models added here are registered in `.annotation_safe_list.yml` (or annotated inline) as `.. no_pii:`. Each of the three `StudentCompetency*Status` models stores a user foreign key and a status value and no personal data of its own, which is how every existing openedx-core model with a user foreign key is annotated, `openedx_content.PublishableEntity` and `Collection` among them. `pii_retirement: consumer_api` is not used, because it asserts a consumer-facing retirement API that openedx-core does not have.
- [ ] No column exists on the models added here beyond those in ADR-0002 Decision 6, plus the constraints and the `created` and `modified` timestamps this ticket lists.
- [ ] All FK relationships match the ADR definitions exactly, targets included: the learner `user_id` points at `settings.AUTH_USER_MODEL` rather than `auth.User`, with `migrations.swappable_dependency` declared in the migration, so that deployments with a swapped user model still work.

### Deletions

- [ ] The foreign key from each of the three status models to its definition row (`CompetencyCriterion`, `CompetencyCriteriaGroup`, or `oel_tagging_tag`) is `PROTECT`, with no `TODO` comment attached. Two of the three point into #641's tables and the third points into `openedx_tagging`. This is the mechanism that stops #641's `CASCADE` chain, so it is load-bearing rather than defensive.
- [ ] The `user` foreign key on all three models is `CASCADE`. `StudentCompetencyStatus.tag` and the `status` foreign key to the mastery status lookup table are `PROTECT`.
- [ ] This ticket owns every `ProtectedError` case in #613, including the ones #641's prose describes, because asserting one needs a `Student*Status` row and this is the ticket that creates those three tables. #641 tests only the cascade half of each case. The transitive cases are tested, not only the direct ones, since `PROTECT` is evaluated on every row the collector reaches rather than only on the row passed to `delete()`.
- [ ] Deleting an `oel_tagging_tag` with a status row anywhere beneath it raises `ProtectedError`. Deleting one with no status rows beneath it still succeeds and removes the whole criteria tree.
- [ ] Deleting a `CompetencyCriteriaGroup` at depth with a leaf status row anywhere beneath it raises `ProtectedError`, and deleting one with no status rows beneath it succeeds.
- [ ] Deleting an `oel_tagging_objecttag` whose criterion has a leaf status row raises `ProtectedError`, and deleting one whose criterion has none succeeds and cascades that criterion away.
- [ ] Deleting an `oel_tagging_taxonomy` raises `ProtectedError` when a status row exists beneath any of its tags. `Tag.taxonomy` is already `CASCADE` in `openedx_tagging`, so the collector reaches every tag beneath the taxonomy and the tag case above holds transitively.
- [ ] Deleting a user row removes that user's status rows across all three models, and a test covers it.
- [ ] No `delete()` override, no archive-versus-delete branch, and no deletion-lock field lands in this ticket. Nothing here implements deletion behavior in code. #655's approved design enforces archive-versus-delete entirely at the application layer, driven by a persisted lock flag on `oel_tagging_objecttag`, which changes `openedx_tagging` as well as CBE.

### Whole-feature gates

- [ ] Migrations apply cleanly on top of #641's migrations, and #613's "apply cleanly from scratch" is verified end to end across the three merged tickets.
- [ ] All ten indexes from ADR-0002 Decision 5 are present across the merged tickets: 1, 2, 4, 5 and 9 from #641, 3 already satisfied by the existing `db_index=True` on `ObjectTag.object_id`, and 6, 7, 8 and 10 from this ticket.
- [ ] `make pii_check` passes with 100% coverage across every model #613 adds, not only the ones in this ticket. That count includes the three models `django-simple-history` generates for #641 (`HistoricalCompetencyCriteriaGroup`, `HistoricalCompetencyCriterion` and `HistoricalCompetencyRuleProfile`), which are real Django models the annotation scan counts.

## Description

This is one of three tickets implementing #613's model layer, and the last of the three to
merge, which is why it also carries the three gates that span the whole feature. Every
criterion above is one of #613's, or one of #613's narrowed to this ticket's models.
Nothing here is additional to the parent.

<details>
<summary>Technical Details</summary>

Background and a suggested approach, not the source of truth. The Acceptance Criteria
above define what must be true when the work is done; this section exists so an
implementer does not have to rediscover the surrounding context first.

### In short

**What these tables hold, and where the code goes.** `CompetencyMasteryStatuses` is a small
lookup of the three possible status values. The other three tables record one learner's
mastery at the leaf, group, and competency levels of the tree #641 defines. They hold one
row per learner and node, updated in place, so finding a learner's current status is a
lookup of a single row rather than a query for the most recent of several. Earlier drafts
of this ticket described them as append-only; ADR-0003 Decision 5 has since been rewritten
and no longer does, on grounds of scale and because no pilot partner needs status history
for MVP. #641 turns `src/openedx_learning/applets/cbe/models.py` into a `models/` package;
put these four models in a new `models/learner_status.py` inside it and export them from
`models/__init__.py`. Do not add a top-level `models.py`: after #641 that path is a
directory, and a branch still treating it as a file conflicts irreconcilably rather than
merging.

**Why the status ordering has to be visible to the database.** ADR-0004 Decision 4 says an
automatic update stores whichever is higher, the value already stored or the newly computed
one. Written as read, then compare in Python, then write, two concurrent tasks can both
read the old value and the later write lowers what the earlier one raised. Written as a
single `UPDATE ... WHERE current_status < new_status` that race cannot happen, and a
database can only make that comparison if the ordering lives in a column it can sort rather
than in a Python constant. Whether you express that as a rank column or as deliberately
ordered primary keys is your call. This ticket only has to make the comparison expressible;
the rule about which writes are allowed is API-layer work and is out of scope.

**Deletion, beyond what the criteria already state.** The `user` foreign key is `CASCADE`
because `PROTECT` there would let this library veto `User.delete()` platform-wide from code
in openedx-platform that has no reason to know CBE rows exist, and because a learner status
row is a derived fact about that learner. `SET_NULL` was never a candidate: a null `user_id`
would break the `(user_id, node_id)` uniqueness the whole in-place-update design rests on.
Separately, the three `PROTECT` values into the definition tables are deliberately stricter
than the predicate the application layer uses. ADR-0002 Decision 7, as amended on
2026-09-01, names the leaf table as the single table that determines whether a record is
protected and treats the two roll-up tables as derived from it. The database makes no such
distinction. A roll-up row with no leaf row beneath it should never occur, but if one ever
does, the delete fails with `ProtectedError` rather than succeeding, and failing closed is
the right default for a backstop.

### Implementation specifics

- **Migration numbering.** Migrations live in `src/openedx_learning/migrations/`. #641 adds
  `0002_competency_criteria` and `0003_seed_default_rule_profile`, so number these `0004`
  (schema) and `0005` (seed) and set the first one's `dependencies` to #641's last
  migration. Developing off `main` will naturally produce a clashing `0002` and `0003`;
  renumber before merging or the app ends up with two migration leaves.
- **Seed via a dedicated data migration,** not fixtures or application code, and run it
  after the schema migration rather than folding it in.
- **`settings.AUTH_USER_MODEL` precedent** for both the foreign key and the
  `swappable_dependency` declaration: `src/openedx_content/migrations/0001_initial.py`.
  ADR-0002 Decision 6 says "`auth_user` table", but that wording is loose; a deployment can
  swap its user model.
- **Companion work in openedx-platform, which no issue owns yet.** That repo lists every
  openedx-core model individually in its own `.annotation_safe_list.yml`, because its
  `.pii_annotations.yml` sets `source_path: ./` and the annotation scan never reads
  installed site-packages. Its only `openedx_learning` entry today is `CompetencyTaxonomy`,
  so the first openedx-core pin bump including #641 and this ticket drops that repo's
  `pii_check` below its 100% target until ten entries are added: the seven models the two
  tickets create, plus the three `Historical*` models `django-simple-history` generates for
  #641. File an issue there before the pin is bumped.
- **Out of scope:** the monotone-write rule and the staff-correction path (ADR-0004
  Decisions 4 and 6); the rollup celery task and the manual recovery command (ADR-0004
  Decisions 2, 3 and 5); all archive-versus-delete enforcement, which #655 governs and
  which lands in #674, #675, #716, #776 and #778, with #799 closed as superseded; #641's
  criteria models; and #640's taxonomy model, delivered by PR #712.

</details>

<details>
<summary>Files to create and modify</summary>

**New files**

| File | Purpose |
| --- | --- |
| src/openedx_learning/applets/cbe/models/learner_status.py | CompetencyMasteryStatuses and the three Student*Status models |
| src/openedx_learning/migrations/0004_learner_status.py | schema migration |
| src/openedx_learning/migrations/0005_seed_mastery_statuses.py | seeds the three status rows in rank order |

**Modified files**

| File | Nature of modification |
| --- | --- |
| src/openedx_learning/applets/cbe/models/__init__.py | export the four new models |
| tests/openedx_learning/applets/cbe/test_models.py | constraint, index and ProtectedError tests, including the transitive cases |
| .annotation_safe_list.yml | annotate the four new models as no_pii |

</details>

<details>
<summary>Context</summary>

- Parent issue: #613. ADR-0002 Decisions 5, 6 and 7; ADR-0003 Decision 5; ADR-0004
  Decisions 4 and 6.
- Depends on #641, which creates the tables two of these foreign keys point at, and on
  #640, delivered by PR #712, for the app itself.
- Draft PR #802 already delivers part of this work: the lookup table,
  `StudentCompetencyStatus`, indexes 8 and 10, both migrations, read-only admin pages, and
  eleven tests run against both SQLite and MySQL 8.4. What remains is
  `StudentCompetencyCriteriaStatus`, `StudentCompetencyCriteriaGroupStatus`, indexes 6 and
  7, and the three whole-feature gates, none of which can be verified until #641's tables
  exist.
- #802 diverges from three of the criteria above deliberately, each argued in that pull
  request: `manual_date_time_field()` in place of `auto_now_add` and `auto_now`, because
  `DateTimeField.pre_save` runs only on `Model.save()` and would leave `modified` stale on
  exactly the conditional-`UPDATE` path this ticket exists to enable; the singular class
  name `CompetencyMasteryStatus`; and idiomatic foreign key field names, so index 8 lands
  on `(user_id, tag_id)` rather than the ADR's literal `(user_id, oel_tagging_tag_id)`.

</details>

## Open Questions

- Do the three criteria #802 diverges from get amended to match it, or does #802 change to
  match them? The three are the `created` and `modified` field type, the singular
  `CompetencyMasteryStatus` class name, and the idiomatic foreign key field names, each
  argued in that pull request. Owner: whoever reviews #802.

