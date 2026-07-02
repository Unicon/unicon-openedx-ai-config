# Feasibility: Decomposing #613 / #613b (CBE core data models) into smaller issues

## Context

This document answers a follow-up question to the [2.12 issue re-organization plan](have-a-look-at-cozy-owl.md):
that plan's **Option B** proposed splitting GitHub issue #613 into **#613a** (a tiny
`CompetencyTaxonomy` MTI marker for this sprint) and **#613b** (the full CBE
criteria/rule/learner-status data-model tree, deferred). The open worry: **#613b is still
epic-sized.** This is a feasibility evaluation of whether #613b — and by extension the whole
CBE data-model layer — can be sliced into ~1–2 developer-day issues arranged so they block
each other *less*. It is an "is this even a good option?" analysis, not a commitment to split.

Grounded against the real code: the three CBE ADRs (`docs/openedx_learning/decisions/0001–0003`),
`.importlinter`, `requirements/base.txt`, and the #613 issue body.

---

## Verdict up front

**Fine-grained decomposition is NOT worth it.** The CBE core is a tightly FK-coupled tree
living in one Django app, and Django migration ordering forces a mostly-linear spine that no
amount of slicing can flatten. Splitting into 7+ tiny issues would create more coordination cost
(shared `models.py`, shared migration chain, merge contention, migration-number collisions) than
it removes, and would tempt migration gymnastics that violate KISS. The right shape is
**3 medium issues (~1.5–2.5 dev-days each)** along the natural FK layers, with cross-cutting
hygiene folded into the slice that introduces each model rather than pulled out separately.

---

## 1. Model dependency map

All models live in one app (`src/openedx_learning/applets/cbe/`, per ADR-0001), sharing one
`models.py` and one migration chain. FK targets, with what each *hard-requires to exist first*:

| Model | FKs / relations | Hard prerequisite (forces ordering) | External vs in-app |
|---|---|---|---|
| `CompetencyTaxonomy` | MTI parent = `Taxonomy` (`taxonomy_ptr_id` is PK+FK) | `openedx_tagging.Taxonomy` (already exists) | external, already migrated |
| `CompetencyRuleProfile` | `competency_taxonomy_id` → `CompetencyTaxonomy`; `course_id` → `openedx_catalog.CourseRun`; `organization_id` | `CompetencyTaxonomy` (in-app); `CourseRun` (exists) | mixed |
| `CompetencyCriteriaGroup` | self-FK `parent_id`; `oel_tagging_tag_id` → `Tag`; `course_id` → `CourseRun` | self-ref (no ordering issue); `Tag`, `CourseRun` (exist) | mixed |
| `CompetencyCriteria` (leaf) | `competency_criteria_group_id` → `CompetencyCriteriaGroup`; `oel_tagging_objecttag_id` → `ObjectTag`; `competency_rule_profile_id` → `CompetencyRuleProfile` (nullable) | `CompetencyCriteriaGroup` **and** `CompetencyRuleProfile` (both in-app) | mixed |
| `CompetencyMasteryStatuses` | none (leaf lookup) | nothing | standalone |
| `StudentCompetencyCriteriaStatus` | `competency_criteria_id` → `CompetencyCriteria` (PROTECT); `user_id` → `AUTH_USER_MODEL`; `status_id` → `CompetencyMasteryStatuses` | `CompetencyCriteria` + `CompetencyMasteryStatuses` | mixed |
| `StudentCompetencyCriteriaGroupStatus` | `competency_criteria_group_id` → `CompetencyCriteriaGroup` (PROTECT); `user_id`; `status_id` → `CompetencyMasteryStatuses` | `CompetencyCriteriaGroup` + `CompetencyMasteryStatuses` | mixed |
| `StudentCompetencyStatus` | `oel_tagging_tag_id` → `Tag`; `user_id`; `status_id` → `CompetencyMasteryStatuses` (constrained values) | `CompetencyMasteryStatuses`; `Tag` | mixed |

**What truly forces ordering** (in-app FKs that must exist in an earlier migration state):
- `CompetencyTaxonomy` before `CompetencyRuleProfile`.
- `CompetencyCriteriaGroup` + `CompetencyRuleProfile` before `CompetencyCriteria`.
- `CompetencyCriteria`, `CompetencyCriteriaGroup`, `CompetencyMasteryStatuses` before their `Student*Status` tables.
- `CompetencyMasteryStatuses` table before its seed-data migration.

**What is merely thematically grouped, not ordering-forced:**
- `CompetencyMasteryStatuses` has no dependencies; it can be created at any migration state.
- The three `Student*Status` tables do not depend on each other; grouped only by lifecycle.
- External FK targets (`Taxonomy`, `Tag`, `ObjectTag`, `CourseRun`, `AUTH_USER_MODEL`) already
  exist and are migrated; they impose a migration `dependencies` declaration but no in-repo
  sequencing. (`CourseRun` is in `openedx_catalog`; Taxonomy/Tag/ObjectTag in `openedx_tagging`.)

**Two facts that shrink the "extra" work:**
- `django-simple-history==3.12.0` is **already a base dependency** (`requirements/base.txt:60`),
  so #613's "add it if not present" is a no-op. Simple-history wiring is
  `history = HistoricalRecords()` on three models plus auto-generated `Historical*` tables inside
  the same `0001_initial` migration — **not** separable work.
- One index (`oel_tagging_objecttag(object_id)`) is on an **existing tagging table** in a different
  app, so it is arguably a separable micro-task, but trivial (one `AddIndex`).

---

## 2. Candidate finest-grain slices (to show why most collapse)

| Candidate slice | Scope (one line) | Size | Ordering constraint |
|---|---|---|---|
| A. App scaffold + layering | Create `applets/cbe/`, add to `INSTALLED_APPS`, add `openedx_learning` to `.importlinter` | 0.5–1 d | Must be first |
| B. Taxonomy marker | `CompetencyTaxonomy` MTI + `no_pii` + admin | 0.5 d | After A; before D, E |
| C. Rule profile | `CompetencyRuleProfile` + JSON `full_clean()` + history + `no_pii` + 1 index | 1–1.5 d | After A, B; before leaf |
| D. Criteria group | `CompetencyCriteriaGroup` self-ref tree, `clean()`, `UniqueConstraint`, history, 2 indexes, `no_pii` | 1.5 d | After A; before E |
| E. Criteria leaf | `CompetencyCriteria` + JSON validation + history + 2 indexes + `no_pii` | 1 d | After C **and** D |
| F. Mastery status + seed | `CompetencyMasteryStatuses` + data migration + 1 index | 0.5 d | Independent of B–E |
| G. Learner status tables | 3 `Student*Status` append-only tables, PROTECT FKs, value constraint, 3 indexes, `pii` | 1.5–2 d | After D, E, F |
| H. objecttag index | Add index on existing `oel_tagging_objecttag` | 0.25 d | Fully independent |

**Do not pull these out as separate issues** — they are one-line-per-model concerns that belong
in the slice creating each model: **simple-history wiring** (regenerating three models' migrations
in a second pass is pure overhead), **PII annotations** (`make pii_check` requires 100% coverage,
so the app can't land green without them), **delete protection** (`on_delete=PROTECT` is a
parameter on the slice-G FKs).

**Genuinely independent slices:** only **F** (mastery statuses + seed) and **H** (objecttag index).
Everything else is chained: **A → B → {C, D} → E → G**.

---

## 3. How dependencies reduce — and where they can't

**FK topology and Django's single per-app migration chain impose hard sequencing that
decomposition cannot remove.** Every `Student*Status` FK targets a definition model; every
definition model except the taxonomy marker targets another. `CompetencyCriteria` sits at the
confluence of two parents, so it can never be first. Because all models share one `models.py` and
one migration directory, splitting them across issues means:
- **Serialized merges:** issue N's migration numbering and `dependencies` must be known before N+1
  is authored; parallel PRs collide on migration numbers and `models.py` hunks.
- **No real parallelism on the spine:** a dev on slice E is blocked until C and D merge, or carries
  their models locally — which is just doing C+D+E as one unit with extra ceremony.

**What decomposition genuinely CAN parallelize:** slice F (zero FK deps, mergeable any time) and
slice H (different app entirely). The seed migration, PII pass, and admin registrations are cheap
enough that folding them in beats coordinating them out.

**Resulting graph shape (the ceiling on parallelism, decomposition or not):**

```
        A (scaffold + importlinter)
        |
        B (CompetencyTaxonomy)
       / \
      C   D          F (mastery + seed)   H (objecttag index)
   (profile)(group)  [independent]        [independent]
       \  /
        E (criteria leaf)
        |
        G (3 learner-status tables) --- needs D, E, and F
```

A **diamond with a long tail**: a linear spine with one internal fork (C, D are peers) and two
detached nodes (F, H). Minimum wall-clock is bounded by spine *depth* (4 sequential waves), not by
issue *count* — so making more issues buys nothing on schedule.

---

## 4. Recommendation

**Three medium issues (~1.5–2.5 dev-days each), plus optionally one independent micro-task** —
cut along the domain's natural cleave line (**authoring definitions vs. learner status**), not
per-model:

- **#613b-1 — App + authoring definition models** (~2–2.5 d): scaffold `applets/cbe/`, add
  `openedx_learning` to `.importlinter` layering + `INSTALLED_APPS`; implement `CompetencyTaxonomy`
  (MTI), `CompetencyRuleProfile`, `CompetencyCriteriaGroup`, `CompetencyCriteria` with their
  validation, `UniqueConstraint`, `HistoricalRecords()`, `no_pii` annotations, admin, and the
  authoring-side indexes in one `0001_initial`. Splitting this fights Django.
- **#613b-2 — Mastery statuses + learner status** (~2 d): `CompetencyMasteryStatuses` + seed
  migration, the three `Student*Status` append-only tables with `PROTECT` FKs, the value
  constraint, `pii` annotations, learner-side indexes. Depends on #613b-1.
- **#613b-3 (optional micro) — `oel_tagging_objecttag(object_id)` index** (~0.25 d): the one
  cross-app index. Fully independent; land any time, or fold into #613b-1's migration `dependencies`.

**Tradeoff, plainly:** two-to-three medium issues trade a little "bigger than 1 day" against a lot
of avoided coordination and migration risk. ADR-0001 deliberately kept authoring + learner status
in **one app** (rejecting the two-app split precisely to avoid cross-app FK/migration ordering);
decomposing back into many tightly-coupled sub-issues re-imports exactly the coordination cost that
placement decision was made to avoid. The natural cleave is the governance boundary ADR-0003 already
draws: history-tracked mutable definitions vs. append-only learner rows. **Cut there, not per-model.**

**Flag for whoever writes #613b-1:** adding `openedx_learning` (and confirming `openedx_catalog`) to
`.importlinter` `root_packages` and the `src_layering` contract is real, non-obvious design work.
Neither is in the layering today, and `openedx_learning` depending on both `openedx_tagging` and
`openedx_catalog` needs deliberate layer placement, not a casual append. That decision belongs in
the scaffold issue, not deferred.

---

## Key files consulted

- `docs/openedx_learning/decisions/0001-competency-criteria-location.rst` — single-app placement rationale
- `docs/openedx_learning/decisions/0002-competency-criteria-model.rst` — FK topology, indexes, delete protection
- `docs/openedx_learning/decisions/0003-competency-criteria-versioning.rst` — history on 3 authoring models; learner tables append-only
- `.importlinter` — `openedx_learning`/`openedx_catalog` not yet in layering
- `src/openedx_catalog/models/course_run.py:30` — `CourseRun` FK target
- `src/openedx_tagging/models/base.py` — `Taxonomy` MTI parent
- `requirements/base.txt:60` — `django-simple-history` already present
