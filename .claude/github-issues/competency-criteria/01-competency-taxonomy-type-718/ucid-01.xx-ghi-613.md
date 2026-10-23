# [BE] Implement CBE core data models (CompetencyTaxonomy, criteria, learner status)

GitHub: https://github.com/openedx/openedx-core/issues/613 (#613, CLOSED)
Cached: 2026-10-22

## Use Case

Competency-Based Education (CBE) programs require learners to *demonstrate* mastery of specific
competencies, not just complete coursework. Open edX currently has no way to define or evaluate the
rules that determine whether a learner has demonstrated a competency, for example "a learner must
score 80% or higher on Assignment 1 OR Assignment 2 to demonstrate the Writing Poetry competency."

This issue implements the foundational database layer that makes the following possible:

- Course Authors and Platform Administrators can define competency achievement criteria in Studio,
  specifying which course content (assignments, exams, etc.) a learner must complete, at what
  threshold, and with what AND/OR logic.
- The platform can track each learner's progress toward demonstrating each competency as they
  receive grades and completions.
- A history of criteria changes is preserved for audit and traceability.

Without this data model, no competency progress dashboards, automated competency evaluations, or
CBE-specific authoring tools can be built.

---

## Description

Implement the Django database models defined in
[ADR-0002 (Competency Criteria Model)](https://github.com/openedx/openedx-core/blob/main/docs/openedx_learning/decisions/0002-competency-criteria-model.rst),
[ADR-0003 (Competency Criteria Versioning)](https://github.com/openedx/openedx-core/blob/main/docs/openedx_learning/decisions/0003-competency-criteria-versioning.rst)
and
[ADR-0004 (Competency Mastery Concurrency)](https://github.com/openedx/openedx-core/blob/main/docs/openedx_learning/decisions/0004-competency-mastery-concurrency.rst).
This is a data-layer issue: no REST endpoints, no UI, and no business logic beyond schema
constraints and two seed migrations. Delete protection was originally moved out to #799 pending #655.
#655 closed on 2026-09-02 with an approved design, and #799 is now closed as superseded. The
`on_delete` values that design implies for this issue's foreign keys are set out in the Deletions
section below, since revised by an amendment to ADR-0002 Decision 7.

The code goes in `src/openedx_learning/applets/cbe/`, the app created by PR #712 per
[ADR-0001](https://github.com/openedx/openedx-core/blob/main/docs/openedx_learning/decisions/0001-competency-criteria-location.rst).

**Already delivered.** PR #712 added the `openedx_learning` app and the `CompetencyTaxonomy` model.
This issue adds the one column that PR left out, `taxonomy_overrides_org`.

**Authoring and definition models**

- `CompetencyTaxonomy`: extends `Taxonomy` via Django multi-table inheritance to mark a taxonomy as
  CBE-enabled. Already exists; needs `taxonomy_overrides_org` added.
- `CompetencyCriteriaGroup`: internal nodes of the AND/OR expression tree.
- `CompetencyRuleProfile`: reusable evaluation rule defaults, scoped by taxonomy, course, or
  organization.
- `CompetencyCriterion`: leaf nodes of the tree, linking a tag/object association either to a rule
  profile or to per-criterion overrides. The Python class is `CompetencyCriterion`, singular,
  because one leaf is one criterion. No `Meta.db_table` override is added, so the table is
  Django's default, `openedx_learning_competencycriterion`.

**Lookup data**

- `CompetencyMasteryStatuses`: the shared status values `AttemptedNotDemonstrated`,
  `PartiallyAttempted` and `Demonstrated`, in that order from lowest to highest. The order has to be
  readable by the database, not only by Python, for the reason given in the acceptance criteria.

**Learner progress models**

- `StudentCompetencyCriteriaStatus`
- `StudentCompetencyCriteriaGroupStatus`
- `StudentCompetencyStatus`

These hold one row per learner and node, updated in place under a unique constraint, each carrying
both `created` and `modified`. ADR-0003 Decision 5 originally specified append-only rows; it was
amended on 2026-07-27 for ADR-0004, which needs a single row per learner and node that a writer can
raise with one conditional `UPDATE`.

**Beyond the models**

- Two data migrations: one seeding the three `CompetencyMasteryStatuses` values, one seeding the
  single system-default `CompetencyRuleProfile` at a grade threshold of 80%.
- One `.importlinter` change: `openedx_catalog` added to `root_packages` and to the `src_layering`
  contract, since `CompetencyCriteriaGroup.course_id` is the first foreign key from
  `openedx_learning` into that app.

**History tracking**

Per ADR-0003, `django-simple-history` is applied to `CompetencyCriteriaGroup`,
`CompetencyCriterion` and `CompetencyRuleProfile` only. It is not applied to the tagging models, to
`CompetencyTaxonomy`, or to the learner status tables.

**Explicitly out of scope.** These rules from the ADRs are not implemented here. The first four belong
to the API layer, where each would either not work at the model layer or would be enforced at the wrong
moment. The fifth and sixth are deferred:

- Computing which `CompetencyRuleProfile` a criterion resolves to (ADR-0002 Decision 4). The models
  store the foreign key and nothing recomputes it at read time.
- The rule that an automatic status write may raise a status but never lower it, and that a staff
  correction may lower one (ADR-0003 Decision 5, ADR-0004 Decisions 4 and 6). The models accept any
  status value; this issue only has to make the comparison expressible in a single SQL statement.
- The rule that a group with more than one child needs a non-null `logic_operator` (ADR-0002
  Decision 2). A group has no children at the moment it is saved, because a child row needs its
  parent's primary key first, and saving a child later validates the child, never the parent. This
  can only be enforced where a whole tree is saved as a unit.
- Rejecting empty groups (ADR-0002 Decision 2), for the same reason.
- All archive-versus-delete enforcement logic (ADR-0002 Decision 7). #655 closed on 2026-09-02 with
  an approved design. The work it implies is split across #674 and #675 (the criterion and group
  removal endpoints), #716 (the `archived` column on `CompetencyCriteriaGroup` and
  `CompetencyCriterion`), and an `openedx_tagging` ticket not yet filed (the `archived` and
  `deletion_locked` columns on the tagging models, plus the lock functions CBE calls). See the
  Deletions section below for the nine `on_delete` values this issue sets, which are final rather than
  a placeholder for that future work to replace.
- Deciding what happens to a course that still relies on an organization-scoped `CompetencyRuleProfile`
  after that organization is deleted, since deleting an organization does not delete its courses along
  with it. The two options under consideration are falling that course back to the system-default
  profile, or cloning the organization's profile into a new course-scoped profile for that course, with
  the current lean toward the latter. Organization-scoped profiles don't exist yet in this MVP
  (Decision 3), so `CompetencyRuleProfile.organization` stays `PROTECT`; that decision, and the
  `on_delete` value it implies, is made together when organization-scoped profiles are built, not here.

**Verification note.** The `scope_code` unique constraint has to be verified against MySQL, not only
the SQLite used for quick local test runs. The acceptance criteria below explain why a green local
suite is not evidence for that one.

---

## Acceptance Criteria

**Note:** This issue delivers a data model, not a user-facing feature. There is no manual QA path.
Acceptance is determined by a PR reviewer verifying the following against ADR-0002, ADR-0003 and
ADR-0004, with the one exception of the MySQL check, which needs a real MySQL database.

**Schema Correctness (ADR-0002)**

- [ ] `CompetencyTaxonomy` uses Django MTI (not a `taxonomy_type` column); `taxonomy_ptr_id` is both the PK and FK to `oel_tagging_taxonomy.id`. Delivered by PR #712, so this ships already satisfied.
- [ ] `CompetencyTaxonomy` has the `taxonomy_overrides_org` boolean, default `false`.
- [ ] `CompetencyCriteriaGroup` has all required columns: `id`, `parent_id` (nullable self-FK), `oel_tagging_tag_id`, `course_id` (nullable `ForeignKey` to `openedx_catalog.CourseRun`), `name`, `ordering`, `logic_operator` (AND/OR/null).
- [ ] `openedx_catalog` is added to `.importlinter`'s `root_packages` and placed in the `src_layering` contract as an independent sibling of `openedx_content`, written `openedx_content | openedx_catalog`, rather than as a layer of its own above or below it. Today `openedx_catalog` appears in neither the `root_packages` list nor the contract, so the first `openedx_learning` to `openedx_catalog` import would pass unexamined. `layers` is a strict total order, so ranking `openedx_catalog` as a layer of its own above or below `openedx_content` would also settle the catalog-to-content import direction, which `src/openedx_catalog/ARCHITECTURE.md` records as undecided; the sibling form leaves that question open. `lint-imports` passes with no rule loosened.
- [ ] `logic_operator` accepts AND, OR or null, per ADR-0002 Decision 2, and nothing at the data layer constrains it by child count. That rule cannot hold here: a group's children need its primary key, so the group's own `clean()` always sees zero children, and adding a child later calls the child's `clean()`, never the parent's. Whatever rule governs null is enforced in the authoring API, when a tree is saved as a unit.
- [ ] No `UniqueConstraint` on `(parent_id, ordering)` is added. ADR-0002 requires none, and it would settle only half the ordering question: a group's children are both child groups and leaf `CompetencyCriteria` rows, and the leaf model has no `ordering` column at all, so sibling order among leaves would stay undefined while looking solved.
- [ ] `CompetencyRuleProfile` has every column from ADR-0002 Decision 3: `id`, `organization_id`, `course_id`, `competency_taxonomy_id`, `scope_code`, `rule_type`, `rule_payload`, `archived`. `rule_payload` is a validated JSON field with shape enforced per `rule_type`.
- [ ] `scope_code` is a plain column, computed by application code (not a database-generated column), in the format `"org:X,course:Y,taxonomy:Z"`, non-null for the system-default row where all three scope columns are null, with a unique constraint on `scope_code` alone.
- [ ] The `scope_code` migration is applied against MySQL, not only the SQLite used for local runs. ADR-0002 Rejected Alternative 6 records that the obvious substitute, a conditional `UniqueConstraint` over the three nullable columns, compiles to a partial index that MySQL does not support: Django emits a `models.W036` warning, skips the constraint, and SQLite supports partial indexes so local tests stay green. A passing local suite is not evidence here.
- [ ] A check constraint enforces that at most one of `organization_id`, `course_id` and `competency_taxonomy_id` is non-null, with a test for each rejected two-column combination.
- [ ] A data migration seeds the single system-default `CompetencyRuleProfile`, the row where all three scope fields are null. It is seeded with `archived` false, `rule_type` `"Grade"`, and `rule_payload` `{"op": "gte", "value": 0.8, "scale": "percent"}`, which means "a grade of 80% or higher". Note that `value` is a fraction between 0.0 and 1.0, not a number out of 100 (ADR-0002 Decision 3), so 80% is written `0.8`. This is the rule every competency criterion falls back to when nothing more specific applies, so a deployment that installs this app and adds no profiles of its own gets an 80% threshold.
- [ ] `CompetencyRuleProfile` scope fields are immutable after creation; editing a profile may change `rule_type` and `rule_payload` only, so that criteria already resolved to a profile are never silently re-scoped.
- [ ] The leaf model has all required columns, including nullable `competency_rule_profile_id`, `rule_type_override` and `rule_payload_override`, with the same validation contract. Its class name is `CompetencyCriterion`, singular, matching ADR-0002 Decision 4. No `Meta.db_table` override is added, so the table is Django's default, `openedx_learning_competencycriterion`.
- [ ] A check constraint enforces ADR-0002 Decision 4's invariant: either `competency_rule_profile_id` is set and both override fields are null, or `competency_rule_profile_id` is null and both override fields are set. Never both, never neither. A test covers each of the two invalid states.
- [ ] Nothing resolves `competency_rule_profile_id` at read time. ADR-0002 Decision 4 assigns it at four named write events and stores the result, and says the FK is never re-resolved dynamically at evaluation time. The assignment computation itself is API-layer work and is out of scope here.
- [ ] `rule_payload` and `rule_payload_override` shape validation is enforced in `clean()`, reached via `full_clean()`; a test must call `full_clean()` with an invalid payload and assert `ValidationError` is raised. `clean()` is a convenience for the admin and for tests, not an enforcement layer: Django's `ModelForm` calls `full_clean()`, but DRF's `ModelSerializer` never does, and neither does `QuerySet.update()` or `bulk_create()`.
- [ ] The three mastery status values, `AttemptedNotDemonstrated`, `PartiallyAttempted` and `Demonstrated`, exist and their order is available to the database, so that raising a status can be written as one conditional `UPDATE` rather than a read followed by a write. A test asserts that a write of a lower value against a higher stored value changes no row, using a single statement.
- [ ] `StudentCompetencyStatus` rejects `AttemptedNotDemonstrated` and accepts only `Demonstrated` and `PartiallyAttempted`. The rejection holds on every write path, including `QuerySet.update()` and `bulk_create()`, which never call `clean()`. Tests cover a direct save and a bulk write.
- [ ] Every index from ADR-0002 Decision 5 is present, and the unique ones are unique: indexes 6, 7 and 8 are unique on `(user_id, node_id)`, index 9 is unique on `scope_code`, and index 10 is unique on the status value. A plain index in any of those four positions fails this criterion.
- [ ] All new models are registered in `.annotation_safe_list.yml` (or inline docstrings) and `make pii_check` passes with 100% coverage. Every one of them, the three `StudentCompetency*Status` models included, is annotated `.. no_pii:`: each stores a user foreign key and a status value and no personal data of its own, which is how every existing openedx-core model with a user foreign key is annotated, `openedx_content.PublishableEntity` and `Collection` among them. `pii_retirement: consumer_api` is not used, because it asserts a consumer-facing retirement API that openedx-core does not have.
- [ ] `CompetencyCriteriaGroup`, `CompetencyCriterion` and `CompetencyRuleProfile` each carry a `uuid` external identifier alongside the internal `id`, following this repo's identifier convention, so that the REST APIs and events built on them are never forced to expose an integer primary key.

**Versioning (ADR-0003)**

- [ ] `django-simple-history` (`HistoricalRecords()`) is applied to `CompetencyCriteriaGroup`, `CompetencyCriterion`, and `CompetencyRuleProfile`.
- [ ] `django-simple-history` is **not** applied to `oel_tagging_tag`, `oel_tagging_taxonomy`, or `CompetencyTaxonomy`.
- [ ] Learner status rows are updated in place, one row per learner and node under a unique constraint, per ADR-0003 Decision 5 as amended on 2026-07-27. Each table carries both `created` (`auto_now_add=True`) and `modified` (`auto_now=True`). No history package is applied.
- [ ] No monotone-write logic and no staff-edit path land here. The models accept any status value the caller writes; the rules that decide which writes are allowed, that an automatic write may raise a status but never lower it and that a staff correction may lower one, are enforced in the API layer.

**Deletions**

All archive-versus-delete enforcement logic from ADR-0002 Decision 7 is out of scope here. #655 closed
on 2026-09-02 with an approved design for it, and the work that design implies is split across separate
issues as described above.

What this issue does own is the `on_delete` value on every new foreign key #641 and #642 add, decided
on #655 on 2026-09-02 and since revised by an amendment to ADR-0002 Decision 7, listed in the checkboxes
below. Three things make ADR-0002 Decision 7's guarantee, that a learner's demonstrated mastery can
never be silently invalidated, actually hold rather than merely state: #655's approved design keeps
`openedx_tagging` from ever calling into CBE to ask whether a tag is "in use," so the only way a
deletion can be stopped while a learner has mastery under it is for Django's own delete collector to
walk down into the criteria tree on its own, and Django only walks a foreign key marked `CASCADE`.

Seven foreign keys are `CASCADE` for that reason: four carry the collector down from the tag through
the tree (`CompetencyCriteriaGroup.tag`, `CompetencyCriteriaGroup.parent`, `CompetencyCriterion.group`,
`CompetencyCriterion.object_tag`), and three carry it down from a `CompetencyTaxonomy` or `CourseRun`
into anything scoped to it (`CompetencyCriteriaGroup.course`, `CompetencyRuleProfile.course`,
`CompetencyRuleProfile.competency_taxonomy`), safe because a taxonomy or course only ever hard-deletes
once nothing beneath it needs protecting. `CompetencyCriterion.rule_profile` is `RESTRICT` instead, so a
profile and the criteria using it can be removed together in the same delete, while a criterion outside
that delete still relying on the profile still stops it, a distinction flat `PROTECT` can't make.
`CompetencyRuleProfile.organization` stays `PROTECT`, deliberately: organization-scoped profiles don't
exist yet (Decision 3), and removing a shared one before deciding what happens to the courses still
using it would silently discard rule configuration they depend on, a decision made only once
organization-scoped profiles are built.

The three foreign keys from the `Student*Status` tables back up to their definition row are `PROTECT`,
and that is the actual stop, the only thing that turns the walk into a real block: a delete with no
learner status beneath it cascades away cleanly, and one with a status row anywhere beneath it raises
`ProtectedError` instead.

The `user_id` foreign key on all three `Student*Status` tables is `CASCADE`. A learner status
row is a derived fact about that user, not something a user's own account deletion should be blocked by.

- [ ] `CompetencyCriteriaGroup.tag`, `CompetencyCriteriaGroup.parent`, `CompetencyCriterion.group`,
  `CompetencyCriterion.object_tag`, `CompetencyCriteriaGroup.course`, `CompetencyRuleProfile.course`,
  and `CompetencyRuleProfile.competency_taxonomy` are `CASCADE`.
- [ ] `CompetencyCriterion.rule_profile` is `RESTRICT`.
- [ ] `CompetencyRuleProfile.organization` is `PROTECT`.
- [ ] The foreign key from each of the three `Student*Status` tables to its definition row
  (`CompetencyCriterion`, `CompetencyCriteriaGroup`, or `oel_tagging_tag`) is `PROTECT`. No `TODO`
  comment is attached to any of these nine `on_delete` values; all nine are final.
- [ ] The `user_id` foreign key on all three `Student*Status` tables is `CASCADE`. The `status_id`
  foreign key to `CompetencyMasteryStatuses` is `PROTECT`.
- [ ] The transitive cases are tested, not only the direct ones. Deleting an `oel_tagging_tag` with a
  learner status row anywhere beneath it raises `ProtectedError`, and deleting one with no status rows
  beneath it succeeds and cascades the whole criteria tree away. The same holds for deleting a
  `CompetencyCriteriaGroup` at depth and for deleting an `oel_tagging_objecttag`.
- [ ] Deleting a `CompetencyTaxonomy` or `CourseRun` with no learner status anywhere beneath it
  succeeds and removes its scoped `CompetencyRuleProfile` along with it. The same delete, when a
  `CompetencyCriterion` outside the tree being deleted still resolves to that profile, fails instead of
  silently deleting the profile out from under that criterion, since `CompetencyCriterion.rule_profile`
  is `RESTRICT`, not `CASCADE`. Tests cover both outcomes.
- [ ] Deleting a user row removes that user's status rows across all three `Student*Status` models,
  and a test covers it.
- [ ] No `delete()` override, no archive-versus-delete branch, and no deletion-lock field lands in this
  issue. The `CASCADE`, `RESTRICT`, and `PROTECT` values above are declared on the foreign keys;
  nothing here implements deletion behavior in code. #655's approved design enforces archive-versus-delete
  entirely at the application layer, driven by a persisted lock flag on `oel_tagging_objecttag`, which
  changes `openedx_tagging` as well as CBE and is not yet owned by a filed ticket.
- [ ] `CompetencyRuleProfile.archived` exists as a column defaulting to false, per the Decision 3
  criteria above. Nothing in this issue enforces that a profile is only archived and never deleted;
  #655 resolves this differently: the model gets no DELETE endpoint at all, and only the single
  system-default row exists in MVP.

**General**

- [ ] Migrations are present and apply cleanly from scratch.
- [ ] No column exists on any of these models beyond those in ADR-0002 Decisions 1 through 4 and 6, the constraints, identifiers and timestamps this issue lists, and the columns `django-simple-history` generates.
- [ ] All FK relationships match the ADR definitions exactly, targets included: `course_id` points at `openedx_catalog.CourseRun`, and the learner `user_id` points at `settings.AUTH_USER_MODEL` rather than `auth.User`, with `migrations.swappable_dependency` declared in the migration, so that deployments with a swapped user model still work.
