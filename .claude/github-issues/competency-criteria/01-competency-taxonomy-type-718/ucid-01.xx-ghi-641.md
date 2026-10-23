# Competency criteria models (authoring/definition layer)

GitHub: https://github.com/openedx/openedx-core/issues/641 (#641, CLOSED)
Cached: 2026-10-22

# Competency criteria models (authoring/definition layer)

## User Story

As a course author, I want a competency's completion requirements stored as an ordered
AND/OR tree of criteria, in order to express a rule like "pass the final and either lab"
rather than a single flat threshold.

## Acceptance Criteria

- [ ] `CompetencyTaxonomy` has the `taxonomy_overrides_org` boolean, default `false`. The model itself shipped in PR #712 without this column.
- [ ] `CompetencyCriteriaGroup` has all required columns: `id`, `parent_id` (nullable self-FK), `oel_tagging_tag_id`, `course_id` (nullable `ForeignKey` to `openedx_catalog.CourseRun`), `name`, `ordering`, `logic_operator` (AND/OR/null).
- [ ] `openedx_catalog` is added to `.importlinter`'s `root_packages` and placed in the `src_layering` contract below `openedx_learning`. Today it appears in neither, so the first `openedx_learning` to `openedx_catalog` import would pass unexamined. `lint-imports` passes with no rule loosened. It is placed as an independent sibling of `openedx_content`, written `openedx_content | openedx_catalog`, rather than as a layer of its own above or below it: `layers` is a strict total order, so a layer of its own would also decide the catalog-to-content direction that `src/openedx_catalog/ARCHITECTURE.md` records as undecided. #613's wording says only "below `openedx_learning`" and needs the same clarification.
- [ ] `logic_operator` accepts AND, OR or null, per ADR-0002 Decision 2, and nothing at the data layer constrains it by child count. That rule cannot hold here: a group's children need its primary key, so the group's own `clean()` always sees zero children, and adding a child later calls the child's `clean()`, never the parent's. Whatever rule governs null is enforced in the authoring API, when a tree is saved as a unit.
- [ ] No `UniqueConstraint` on `(parent_id, ordering)` is added. ADR-0002 requires none, and it would settle only half the ordering question: a group's children are both child groups and leaf `CompetencyCriteria` rows, and the leaf model has no `ordering` column at all, so sibling order among leaves would stay undefined while looking solved.
- [ ] `CompetencyRuleProfile` has every column from ADR-0002 Decision 3: `id`, `organization_id`, `course_id`, `competency_taxonomy_id`, `scope_code`, `rule_type`, `rule_payload`, `archived`. `rule_payload` is a validated JSON field with shape enforced per `rule_type`.
- [ ] `scope_code` is a generated, never-null column in the format `"org:X,course:Y,taxonomy:Z"`, non-null for the system-default row where all three scope columns are null, with a unique constraint on `scope_code` alone.
- [ ] The `scope_code` migration is applied against MySQL, not only the SQLite used for local runs. ADR-0002 Rejected Alternative 6 records that the obvious substitute, a conditional `UniqueConstraint` over the three nullable columns, compiles to a partial index that MySQL does not support: Django emits a `models.W036` warning, skips the constraint, and SQLite supports partial indexes so local tests stay green. A passing local suite is not evidence here.
- [ ] A check constraint enforces that at most one of `organization_id`, `course_id` and `competency_taxonomy_id` is non-null, with a test for each rejected two-column combination.
- [ ] A data migration seeds the single system-default `CompetencyRuleProfile`, the row where all three scope fields are null. It is seeded with `archived` false, `rule_type` `"Grade"`, and `rule_payload` `{"op": "gte", "value": 0.8, "scale": "percent"}`, which means "a grade of 80% or higher". Note that `value` is a fraction between 0.0 and 1.0, not a number out of 100 (ADR-0002 Decision 3), so 80% is written `0.8`. This is the rule every competency criterion falls back to when nothing more specific applies, so a deployment that installs this app and adds no profiles of its own gets an 80% threshold.
- [ ] `CompetencyRuleProfile` scope fields are immutable after creation; editing a profile may change `rule_type` and `rule_payload` only, so that criteria already resolved to a profile are never silently re-scoped.
- [ ] The leaf model has all required columns, including nullable `competency_rule_profile_id`, `rule_type_override` and `rule_payload_override`, with the same validation contract. Its class name is `CompetencyCriterion`, singular, matching ADR-0002 Decision 4, which calls one leaf a criterion. No `Meta.db_table` override is added, so the table is `openedx_learning_competencycriteria`; see "The three criteria models" above for why. #613 still asks for `Meta.db_table = "CompetencyCriteria"` and needs the same correction.
- [ ] A check constraint enforces ADR-0002 Decision 4's invariant: either `competency_rule_profile_id` is set and both override fields are null, or `competency_rule_profile_id` is null and both override fields are set. Never both, never neither. A test covers each of the two invalid states.
- [ ] Nothing resolves `competency_rule_profile_id` at read time. ADR-0002 Decision 4 assigns it at four named write events and stores the result, and says the FK is never re-resolved dynamically at evaluation time. The assignment computation itself is API-layer work and is out of scope here.
- [ ] `rule_payload` and `rule_payload_override` shape validation is enforced in `clean()`, reached via `full_clean()`; a test must call `full_clean()` with an invalid payload and assert `ValidationError` is raised. `clean()` is a convenience for the admin and for tests, not an enforcement layer: Django's `ModelForm` calls `full_clean()`, but DRF's `ModelSerializer` never does, and neither does `QuerySet.update()` or `bulk_create()`.
- [ ] The indexes from ADR-0002 Decision 5 that belong to these models are present: 1 (`CompetencyCriteriaGroup(oel_tagging_tag_id, course_id)`), 2 (`CompetencyCriteriaGroup(parent_id)`), 4 (`CompetencyCriteria(oel_tagging_objecttag_id)`), 5 (`CompetencyCriteria(competency_criteria_group_id)`) and 9 (`CompetencyRuleProfile(scope_code)`). Index 9 must be unique; a plain index there fails this criterion. Index 3, `oel_tagging_objecttag(object_id)`, is already satisfied by the existing `db_index=True` on `ObjectTag.object_id` (`src/openedx_tagging/models/base.py`), so no work is required for it here. Indexes 6, 7, 8 and 10 come from #642, which verifies all ten end to end.
- [ ] `CompetencyCriteriaGroup`, `CompetencyCriterion` and `CompetencyRuleProfile` each carry a `uuid` external identifier alongside the internal `id`, following this repo's identifier convention, so that the REST APIs and events built on them are never forced to expose an integer primary key.
- [ ] The models added here are registered in `.annotation_safe_list.yml` (or annotated inline) as `.. no_pii:`, including the three models `django-simple-history` generates: `HistoricalCompetencyCriteriaGroup`, `HistoricalCompetencyCriterion` and `HistoricalCompetencyRuleProfile`. Those are real Django models and the annotation scan counts them; this is the first use of `django-simple-history` anywhere in `src/`, so nothing in this repo has hit that before. #642, as the last ticket to merge, carries the `make pii_check` 100% coverage gate for the feature as a whole.
- [ ] `django-simple-history` (`HistoricalRecords()`) is applied to `CompetencyCriteriaGroup`, `CompetencyCriterion` and `CompetencyRuleProfile`.
- [ ] `django-simple-history` is **not** applied to `oel_tagging_tag`, `oel_tagging_taxonomy`, or `CompetencyTaxonomy`.
- [ ] Migrations are present and apply cleanly on top of #640's migration.
- [ ] No column exists on the models added here beyond those in ADR-0002 Decisions 1 through 4, the constraints, identifiers and timestamps this ticket lists, and the columns `django-simple-history` generates. One exception, listed again under Deletions below: the `archived` column that the 2026-09-01 amendment added to Decisions 2 and 4 is **not** added here, because #716 owns it.
- [ ] All FK relationships match the ADR definitions exactly, targets included: `course_id` points at `openedx_catalog.CourseRun`.

### Deletions

- [ ] The four foreign keys that carry Django's collector down the criteria tree are `CASCADE`: `CompetencyCriteriaGroup.tag`, `CompetencyCriteriaGroup.parent`, `CompetencyCriterion.group` and `CompetencyCriterion.object_tag`. These are what make ADR-0002 Decision 7's delete protection work, because the `PROTECT` that blocks a delete lives on #642's `Student*Status` foreign keys, two of which point at rows one and two levels below the tag, and Django reaches them only by walking down foreign keys marked `CASCADE`.
- [ ] `CompetencyRuleProfile.competency_taxonomy` is `CASCADE`, not `PROTECT`, so a rule profile is never the reason a taxonomy delete fails. Blocking a taxonomy delete when learner data is connected to it is an application-layer requirement, not a database constraint; see the requirement above and #613.
- [ ] The other four are `PROTECT`: `CompetencyCriterion.rule_profile`, `CompetencyCriteriaGroup.course`, `CompetencyRuleProfile.course` and `CompetencyRuleProfile.organization`. No `TODO` comment is attached to any of the nine; all nine values are final.
- [ ] Only the cascade half of each delete case is tested here. Every matching `ProtectedError` case belongs to #642, because asserting one requires a `Student*Status` row and #642 is the ticket that creates those three tables. This ticket merges first, so the rows those assertions need do not exist yet.
- [ ] Deleting an `oel_tagging_tag` succeeds and removes the whole criteria tree beneath it: every `CompetencyCriteriaGroup` for that tag, every descendant group, and every `CompetencyCriterion` under any of them.
- [ ] Deleting a `CompetencyCriteriaGroup` at depth succeeds and removes the target, every descendant group, and every criterion under any of them.
- [ ] Deleting an `oel_tagging_objecttag` succeeds and cascades its criteria away, leaving the parent group behind.
- [ ] Deleting an `oel_tagging_taxonomy` succeeds and removes the criteria trees of every tag beneath it. `Tag.taxonomy` is already `CASCADE` in `openedx_tagging`, which is what makes the tag case above hold transitively from the taxonomy.
- [ ] No `delete()` override, no archive-versus-delete branch, and no deletion-lock field lands in this ticket. The cascade is declared on the foreign keys and nothing here implements deletion behavior in code. #655's approved design enforces archive-versus-delete entirely at the application layer, driven by a persisted lock flag on `oel_tagging_objecttag`, which changes `openedx_tagging` as well as CBE.
- [ ] `CompetencyRuleProfile.archived` exists as a column defaulting to false, per the ADR-0002 Decision 3 criterion above. Nothing in this ticket enforces that a profile is only archived and never deleted. #655 resolves that differently rather than deferring it: the model gets no DELETE endpoint at all, and only the single system-default row exists in MVP.
- [ ] No `archived` column is added to `CompetencyCriteriaGroup` or `CompetencyCriterion`. ADR-0002 Decisions 2 and 4 now list one on each, added by the 2026-09-01 amendment for #655, but #716 owns landing it. Read the "no column beyond ADR-0002 Decisions 1 through 4" criterion above with that carve-out.

## Description

This is one of three tickets implementing #613's model layer, and the first of the three
to merge. Every criterion above is one of #613's, or one of #613's narrowed to this
ticket's models. Nothing here is additional to the parent.

<details>
<summary>Technical Details</summary>

Background and a suggested approach, not the source of truth. The Acceptance Criteria
above define what must be true when the work is done; this section exists so an
implementer does not have to rediscover the surrounding context first.

### In short

**The three criteria models.** A competency is a `Tag` in a competency-enabled taxonomy.
Hanging off that tag is a tree: `CompetencyCriteriaGroup` rows are the internal AND/OR
nodes, and `CompetencyCriterion` rows are the leaves. Each leaf points at an `ObjectTag`,
meaning one specific piece of tagged content, and takes its pass rule either from a shared
`CompetencyRuleProfile` or from its own inline override pair. A `CompetencyRuleProfile` is
a reusable set of evaluation settings scoped to exactly one of an organization, a course,
or a taxonomy, plus one system-default row scoped to none of them. The leaf keeps the
default table name because ADR-0002's heading, "`CompetencyCriterion` concept
(`CompetencyCriteria` database table)", names the domain concept the way every other
heading in that ADR does rather than instructing a rename; no model in `src/` overrides
`db_table` today, and an unprefixed CamelCase table name would risk a collision, because
openedx-core's tables share a MySQL schema with openedx-platform's. Today
`src/openedx_learning/applets/cbe/models.py` is a single module holding only
`CompetencyTaxonomy`; this ticket turns it into a `models/` package, since the three new
models form one connected structure and want a module of their own.

**Deletion, and the two facts most likely to be misread.** #655 fixed all nine `on_delete`
values on 2026-09-02, they are final, and the criteria above say why the four `CASCADE`
links are load-bearing rather than a relaxation. Two consequences are easy to get wrong.
First, `on_delete` governs deletion of the row a foreign key points *at*, never the row
holding the foreign key, so `CompetencyCriterion.rule_profile` being `PROTECT` does not
block a tag delete that cascades criteria away; it only stops a rule profile from being
deleted while a criterion still references it. Second, `PROTECT` is evaluated on every row
Django's collector reaches, not only on the row passed to `delete()`, which is what makes
the transitive cases work at all. One consequence of splitting this work from #642: until
#642 merges, `main` carries a `CASCADE` chain with no `PROTECT` at the bottom, so deleting
a tag removes the whole authored tree and nothing objects. That window is expected and
harmless, because the learner status tables do not exist yet.

**Several plausible additions are excluded on purpose,** worth knowing up front so they are
not added and then removed in review: no constraint tying a group's `logic_operator` to its
child count and no rejection of empty groups, because a group has no children at the moment
it is validated and saving a child later runs the child's `clean()` rather than the
parent's; no `UniqueConstraint` on `(parent, ordering)`, because leaves carry no `ordering`
column and sibling order among them would stay undefined while looking solved; and nothing
that resolves a criterion's rule profile at read time, because ADR-0002 Decision 4 assigns
that foreign key at four named write events and stores the result. All three belong to the
authoring API, which no ticket owns yet. Relatedly, `clean()` is a convenience for the admin
and for tests rather than an enforcement layer, which is why this ticket's two invariants
are database check constraints instead.

### Implementation specifics

- **Migrations live in `src/openedx_learning/migrations/`.** The `cbe` applet has no
  migrations package of its own. #640's `0001_initial` is there, so this ticket's two
  migrations are `0002` and `0003`, and #642 renumbers onto them.
- **`django-simple-history` is not a declared dependency yet.** It is pinned in the
  compiled requirements only as a transitive dependency of `edx-organizations`, and
  `simple_history` is absent from `INSTALLED_APPS`. Add it to `requirements/base.in` and
  register the app in `test_settings.py` and `projects/dev.py` before `HistoricalRecords()`
  will work.
- **The `Grade` rule payload shape** is `{"op": "gte", "value": 0.8, "scale": "percent"}`,
  where `op` is one of `gte`, `lte`, `eq` and `value` is a fraction from 0.0 to 1.0 rather
  than a number out of 100. `Grade` is the only `rule_type` supported now.
- **Why `taxonomy_overrides_org` ships although nothing reads it.** It settles a tiebreak
  that cannot arise yet: when a criterion could inherit its rule from an organization-scoped
  profile or from a taxonomy-scoped one, this flag decides which wins. Organization-scoped
  profiles do not exist. Adding the column now avoids a later migration against a table that
  by then has learner data hanging off it.
- **The requirement referenced by the `competency_taxonomy` criterion above.** Once a rule
  profile can be scoped to a taxonomy, deleting that taxonomy must be blocked when learner
  data is connected to it and must otherwise succeed, matching #655's approved behavior for
  every other record. That guardrail is application-layer Python, is not designed yet, and is
  not this ticket's work. This ticket only keeps the database from pre-empting the decision,
  by leaving `PROTECT` off `CompetencyRuleProfile.competency_taxonomy`.
- **Two accepted cascade consequences, so neither reads as a defect in review.** Deleting an
  `ObjectTag` outside #674 and #675 cascades its criteria away and can leave an empty parent
  group behind, which is reachable only for an ungraded criterion. Deleting a `Tag` leaves
  its `ObjectTag` rows with a null `tag`, since `ObjectTag.tag` is `SET_NULL`, which dangles
  nothing because every criterion pointing at those rows is cascaded away in the same
  operation. Neither cascade is silent: `django-simple-history` connects `post_delete`, so a
  `history_type='-'` row is written for every group and criterion removed.
- **`CompetencyRuleProfile.organization` needs no requirements change.** `edx-organizations`
  is already in `requirements/base.in`, and `src/openedx_catalog/models/catalog_course.py`
  already imports `Organization` for `CatalogCourse.org`.
- **Out of scope:** #642's learner status models; all archive-versus-delete enforcement,
  which #655 governs and which lands in #674, #675, #716, #776 and #778, with #799 closed
  as superseded; the app skeleton, delivered by PR #712 for #640; and any REST API or UI
  work.

</details>

<details>
<summary>Files to create and modify</summary>

**New files**

| File | Purpose |
| --- | --- |
| src/openedx_learning/applets/cbe/models/__init__.py | re-export the CBE models |
| src/openedx_learning/applets/cbe/models/competency_taxonomy.py | CompetencyTaxonomy, moved from models.py, plus taxonomy_overrides_org |
| src/openedx_learning/applets/cbe/models/criteria.py | CompetencyCriteriaGroup, CompetencyRuleProfile, CompetencyCriterion |
| src/openedx_learning/migrations/0002_competency_criteria.py | schema migration |
| src/openedx_learning/migrations/0003_seed_default_rule_profile.py | seeds the system-default rule profile |

**Modified files**

| File | Nature of modification |
| --- | --- |
| src/openedx_learning/applets/cbe/models.py | removed, replaced by the models/ package above |
| tests/openedx_learning/applets/cbe/test_models.py | constraint, index, validation and cascade tests |
| .importlinter | register openedx_catalog in root_packages and in the src_layering contract |
| .annotation_safe_list.yml | annotate the three new models and the three Historical* models |
| requirements/base.in | declare django-simple-history directly |
| test_settings.py | add simple_history to INSTALLED_APPS |

</details>

<details>
<summary>Context</summary>

- Parent issue: #613. ADR-0002 Decisions 1 through 5 and 7, and ADR-0003, define this model layer.
- #655 records the approved archive-versus-delete design and the nine final `on_delete` values.
- #642 adds the learner status models and carries the gates that span both tickets. This ticket
  can be developed in parallel with it but must merge first.
- #640, delivered by PR #712, created the app and `CompetencyTaxonomy`. `openedx_catalog.CourseRun`
  already exists in this repo.
- `src/openedx_catalog/ARCHITECTURE.md` records the catalog-to-content import direction as
  undecided. `.importlinter` already uses the sibling form for
  `openedx_content.applets.components | openedx_content.applets.containers`.

</details>

## Open Questions

- Once taxonomy-scoped `CompetencyRuleProfile` rows exist, does `CompetencyCriterion.rule_profile`
  still want `PROTECT`? Owner: whoever designs the application-layer guardrail described in
  Technical Details. Not settled here; see #613.

