# Manual verification guide: #640 — CBE app foundation + `CompetencyTaxonomy`

Audience: a reviewer who knows Python and a little Django, but not this codebase.
Goal: prove, by hand, that each of #640's nine acceptance criteria is met, and that the
result is architecturally sound rather than merely passing.

Ticket: <https://github.com/openedx/openedx-core/issues/640>
Implementation plan (source of truth): `.claude/plans/640-cbe-app-foundation-plan.md`

Every check below has four parts:

1. **The AC** — quoted verbatim from the ticket.
2. **How the code satisfies it** — what was actually built, and where.
3. **Your manual check** — commands to run, with the output you should see.
4. **Why this is sufficient** — why passing this check means the AC is genuinely met and
   the design is correct, not just that a test went green.

Some checks deliberately break something on purpose and then put it back. Those are
marked **[destructive-then-revert]**. There are no REST endpoints or UI in this ticket, so
a few checks use a Django shell or the Django admin instead. That is expected.

How this is organised:

| Part | What it covers |
|---|---|
| 0 | Setup, and the two concepts you need |
| 1 | The nine acceptance criteria, one at a time |
| 2 | Architectural checks the ACs don't cover |
| 3 | What is deliberately absent, so you don't read it as a gap |
| 4 | The automated tests and linters |
| 5 | **End-to-end integration test in your tutor environment**, using the companion edx-platform branch |
| 6-7 | Cleanup, and a sign-off checklist |

**Every command and expected output in Parts 1-4 was actually executed against this
branch**, so what you see printed here is real output, not a guess. Part 5 is the one
exception, and says so where it starts.

If you only have twenty minutes: do AC 1, AC 6, B.1, B.2, and Part 4. Those five cover the
schema, the architecture rule, the lifecycle, the cross-repo contract, and the test suite.

---

## Part 0 — Setup (about 5 minutes)

### 0.1 Two virtualenvs, do not mix them

| Venv | Purpose | Use it for |
|---|---|---|
| `~/.virtualenvs/tutor` | Your **tutor / openedx runtime** env | Nothing in this guide. Leave it alone. |
| `<repo>/.venv` | Repo-local **tooling** env, created for this review. Gitignored. | Everything in this guide. |

The tooling venv already exists. Confirm it, from the repo root:

```bash
cd /Users/jesperhodge/openedx/openedx-core
.venv/bin/python -c "import django, openedx_learning; print(django.get_version())"
```

Expected: a Django version (`5.2.x`) and no `ImportError`. If `.venv` is missing, rebuild it:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -U pip setuptools
.venv/bin/python -m pip install -r requirements/quality.txt
.venv/bin/python -m pip install -e . --no-deps
```

Every command below uses `.venv/bin/...` explicitly, so you never need to `activate`
anything. That is on purpose: it keeps your tutor venv untouched.

### 0.2 Two settings modules

This repo is a **library**, so it ships two throwaway Django "projects" purely so that
Django can be booted at all:

| Settings module | Database | Used by |
|---|---|---|
| `test_settings` | in-memory sqlite (vanishes each run) | `pytest` |
| `projects.dev` | file-backed sqlite at `./dev.db` | `manage.py` (this is `manage.py`'s default) |

Because `projects.dev` writes a real file, you can open it with `sqlite3` and look at the
actual tables. That is what makes the schema checks below possible.

Two harmless bits of noise you will see repeatedly and can ignore:

- `manage.py shell -c` prints `52 objects imported automatically (use -v 2 for details).`
  before your output. That is Django's shell auto-import banner, not part of the result.
- `manage.py` commands print two `models.W042` warnings about the third-party
  `organizations` app. Those are on `main` too.

### 0.3 Start from a clean database

`dev.db` is a scratch file. Back it up anyway, so you can restore it if you had anything
in it:

```bash
[ -f dev.db ] && mv dev.db dev.db.bak
```

### 0.4 The 90-second concept briefing

You need two ideas to read the rest of this document.

**Idea 1: umbrella app + applets.** In this repo, one *Django app* can be split into
several *Python subpackages*, called "applets", purely for human organisation.
`openedx_content` already does this: one `AppConfig`, one `migrations/` directory, one app
label, but nine applets under `openedx_content/applets/`. Django only finds the models
because `openedx_content/models.py` wildcard-imports each applet's models, and only finds
the admin classes because `openedx_content/admin.py` wildcard-imports each applet's admin.

This ticket copies that shape exactly: a new app `openedx_learning`, with one applet,
`cbe`. So `src/openedx_learning/models.py` is a one-line re-export, not where the model is
defined. The model lives at `src/openedx_learning/applets/cbe/models.py`.

**Idea 2: multi-table inheritance (MTI).** When a Django model subclasses a *concrete*
model (not an abstract one, not a proxy), Django creates a **second table** for the child.
The child's table holds only the child's own columns, plus a `OneToOneField` back to the
parent row which doubles as the child's primary key:

```
oel_tagging_taxonomy                 openedx_learning_competencytaxonomy
+----+---------+------------+        +-----------------+------------------------+
| id | name    | export_id  |        | taxonomy_ptr_id | taxonomy_overrides_org |
+----+---------+------------+        +-----------------+------------------------+
| 42 | Nursing | nursing-v1 |  <---- | 42              | 1                      |
+----+---------+------------+        +-----------------+------------------------+
```

Consequences that matter here, all of them free (no code implements them):

- `taxonomy_ptr_id` is created by Django. We must **not** declare it.
- On a child instance, parent fields read through transparently: `ct.name` works.
- On a **parent** instance, the child is reachable at `taxonomy.competencytaxonomy`. If
  there is no child row, touching it raises `RelatedObjectDoesNotExist`. **That existence
  check is the entire cross-repo contract** described below.
- `Taxonomy.objects.all()` returns plain `Taxonomy` objects, never `CompetencyTaxonomy`
  ones, even for rows that have a child.
- Deleting either row deletes the other.

**Why the accessor name is a big deal.** A separate, already-accepted decision record,
`docs/openedx_tagging/decisions/0013-competency-taxonomy-detection.rst`, says that
**openedx-platform** (a different repo, Studio) will detect a competency taxonomy by
checking for that related child row. Django derives the accessor name
`competencytaxonomy` automatically from our class name. So if someone renames our model,
Studio breaks and **nothing in this repo fails**. To stop that, this ticket wraps the name
in two functions in `openedx_learning.api` so it is written down in exactly one place.
Checks A.6 and B.2 below are what prove that wrapper actually works.

---

## Part 1 — Acceptance criteria, one at a time

### AC 1 — MTI, and `taxonomy_ptr_id` is both PK and FK

> `CompetencyTaxonomy` uses Django MTI (not a `taxonomy_type` column); `taxonomy_ptr_id`
> is both the PK and FK to `oel_tagging_taxonomy.id`

**How the code satisfies it.** `src/openedx_learning/applets/cbe/models.py` declares
`class CompetencyTaxonomy(Taxonomy)` where `Taxonomy` is the real, concrete model from
`openedx_tagging`. There is no `proxy = True` and no `abstract = True`, so Django uses
MTI. The pointer field is *not* declared in our source at all: Django generates it. And
nothing was added to `openedx_tagging`, so no `taxonomy_type` column exists.

**Your manual check.**

Step 1 — apply the migrations to a fresh database:

```bash
.venv/bin/python manage.py migrate
```

Expected: a long list of `Applying ...  OK` lines, ending with (among others)
`Applying openedx_learning.0001_initial... OK`. No errors, no prompts.

Step 2 — look at the real table that was created:

```bash
sqlite3 dev.db ".schema openedx_learning_competencytaxonomy"
```

Expected (sqlite prints it on one long line; wrapped here for readability):

```sql
CREATE TABLE IF NOT EXISTS "openedx_learning_competencytaxonomy" (
    "taxonomy_ptr_id" bigint NOT NULL PRIMARY KEY
        REFERENCES "oel_tagging_taxonomy" ("id") DEFERRABLE INITIALLY DEFERRED,
    "taxonomy_overrides_org" bool NOT NULL
);
```

Read that output carefully. It is the whole AC in one place:

- the table **exists** and is separate from `oel_tagging_taxonomy` → MTI, not a column;
- `taxonomy_ptr_id ... PRIMARY KEY` → it is the PK;
- `REFERENCES "oel_tagging_taxonomy" ("id")` → it is also the FK, pointing at exactly the
  column the AC names.

Step 3 — confirm the negative half of the AC, that no `taxonomy_type` column was added to
the tagging table:

```bash
sqlite3 dev.db "PRAGMA table_info(oel_tagging_taxonomy);" | grep -i "taxonomy_type" || echo "PASS: no taxonomy_type column"
```

Expected: `PASS: no taxonomy_type column`.

Step 4 — confirm Django itself agrees about PK/FK identity, rather than us reading SQL:

```bash
.venv/bin/python manage.py shell -c "
from openedx_learning.models import CompetencyTaxonomy
pk = CompetencyTaxonomy._meta.pk
print('pk field name      :', pk.name)
print('pk is the parent link:', pk.remote_field.parent_link)
print('pk points at       :', pk.related_model._meta.db_table + '.' + pk.target_field.column)
print('declared in our src:', [f.name for f in CompetencyTaxonomy._meta.local_fields])
"
```

Expected:

```
pk field name      : taxonomy_ptr
pk is the parent link: True
pk points at       : oel_tagging_taxonomy.id
declared in our src: ['taxonomy_ptr', 'taxonomy_overrides_org']
```

`taxonomy_ptr` appears in `local_fields` because Django auto-created it on the model; the
point of the check is that it is `parent_link=True` and that we did not write it.

**Why this is sufficient.** The AC is a statement about the database shape and the
relationship type. Reading the generated DDL is the most direct possible evidence: it is
what will actually run against MySQL in production, not an approximation. Step 4 adds
Django's own view of the field, which rules out the subtle failure where the SQL looks
right but the model was declared as a proxy or with a hand-rolled `OneToOneField` (either
would change the accessor name and silently break Studio, see B.2).

---

### AC 2 — `django-simple-history` is not applied here

> `django-simple-history` is **not** applied to `oel_tagging_tag`, `oel_tagging_taxonomy`,
> or `CompetencyTaxonomy`

**How the code satisfies it.** By omission, deliberately. `CompetencyTaxonomy` has no
`HistoricalRecords()` field, `simple_history` is not in `INSTALLED_APPS`, and this ticket
changes no file under `src/openedx_tagging/`. Decision record ADR-0003 Decision 2
excludes all three of these models from history tracking, so the correct implementation
is to add nothing.

**Your manual check.**

Step 1 — no history declaration anywhere in the new app:

```bash
grep -rn "HistoricalRecords\|simple_history" src/openedx_learning/ && echo "FAIL" || echo "PASS: no history tracking in openedx_learning"
```

Expected: `PASS: no history tracking in openedx_learning`.

Step 2 — no history tables were created for any of the three named models:

```bash
sqlite3 dev.db ".tables" | tr -s ' ' '\n' | grep -i "histor" || echo "PASS: no historical tables at all"
```

Expected: `PASS: no historical tables at all`.

Step 3 — confirm the tagging app was not touched by this branch at all:

```bash
git diff main...HEAD --stat -- src/openedx_tagging/ || true
```

Expected: empty output (no files listed).

**Why this is sufficient.** `django-simple-history` works by adding a `HistoricalRecords`
descriptor to a model, which creates a `historical<modelname>` table. Step 1 proves the
descriptor is absent from our source, and step 2 proves the consequence is absent from the
database, so this is verified at both ends rather than by inspection alone. Step 3 closes
the only remaining route by which the AC could be violated: a change to `oel_tagging`'s
own models. Note that some *other* installed app may legitimately have history tables in a
real deployment; step 2 passing here just confirms nothing in this repo's app set does.

---

### AC 3 — No columns that the ADRs do not define

> No columns exist on any model that are not defined in the ADRs

**How the code satisfies it.** ADR-0002 Decision 1 defines exactly two things on this
table: the MTI parent link, and `taxonomy_overrides_org` (a boolean, default false, the
org-versus-taxonomy tiebreak used later by the rule-profile work). The model declares
exactly those and nothing else.

Note this is the one AC where the plan **overrode the ticket**. The ticket's "Open
questions" asks whether `taxonomy_overrides_org` is in scope, saying it exists only on an
unmerged branch. That is stale: it is on `main`, merged in `5cd47f1`. Since the ADR now
defines the column, *omitting* it would have failed this same AC from the other direction.
See plan assumption A2.

**Your manual check.**

```bash
sqlite3 dev.db "PRAGMA table_info(openedx_learning_competencytaxonomy);"
```

Expected exactly two rows, nothing more:

```
0|taxonomy_ptr_id|bigint|1||1
1|taxonomy_overrides_org|bool|1||0
```

Then cross-check against the ADR text with your own eyes:

```bash
grep -n -A 30 "Decision 1" docs/openedx_learning/decisions/0002-*.rst | head -60
```

Look for the `CompetencyTaxonomy` description and confirm it lists the parent link and
`taxonomy_overrides_org`, and no third column.

Optionally, see the exact DDL the migration will emit:

```bash
.venv/bin/python manage.py sqlmigrate openedx_learning 0001
```

**Why this is sufficient.** `PRAGMA table_info` enumerates the physical columns, so
nothing can hide: a stray field, an auto-added `id`, or a leftover from a copied model
would all show up as a third row. Two rows out, two columns in the ADR, and you have read
both. The `sqlmigrate` output is a useful extra because it is the literal SQL that will be
replayed on every environment, including MySQL in production.

One thing that is *not* a column and so does not affect this AC: the model's `Meta` sets
`verbose_name` and `verbose_name_plural`. Those only change display strings in the admin
(without them Django renders the plural as "Competency taxonomys"). Confirm they added no
column by re-reading the two-row output above.

---

### AC 4 — All FK relationships match the ADRs exactly

> All FK relationships match the ADR definitions exactly

**How the code satisfies it.** There is exactly one relationship in this ticket: the
implicit MTI parent link from `CompetencyTaxonomy` to `oel_tagging_taxonomy.id`. ADR-0002
Decision 1 defines that and nothing else for this model. The three criteria models with
richer FKs (`CompetencyCriteriaGroup`, `CompetencyCriteria`, `CompetencyRuleProfile`) are
issue #641, not this ticket.

**Your manual check.**

```bash
.venv/bin/python manage.py shell -c "
from openedx_learning.models import CompetencyTaxonomy
rels = [
    (f.name, f.get_internal_type(), f.related_model._meta.db_table, f.remote_field.on_delete.__name__)
    for f in CompetencyTaxonomy._meta.local_fields if f.remote_field
]
for r in rels:
    print(r)
print('relationship count:', len(rels))
"
```

Expected:

```
('taxonomy_ptr', 'OneToOneField', 'oel_tagging_taxonomy', 'CASCADE')
relationship count: 1
```

Then confirm the database enforces it:

```bash
sqlite3 dev.db "SELECT sql FROM sqlite_master WHERE name='openedx_learning_competencytaxonomy';" | grep -i references
```

Expected: a line containing `REFERENCES "oel_tagging_taxonomy" ("id")`.

**Why this is sufficient.** Enumerating `local_fields` where `remote_field` is set is an
exhaustive list of this model's outgoing relationships as Django understands them, so
"count: 1" is a completeness statement, not a spot check. `CASCADE` is what makes the
lifecycle rule in AC 4's sibling decision work (delete one row, both go), which you verify
behaviourally in check A.5.

---

### AC 5 — The app exists in the right place, with one `AppConfig`, and is registered

> The app exists at `src/openedx_learning/applets/cbe/` per ADR-0001, with a single
> `AppConfig` for `openedx_learning`, and is registered in `test_settings.py`
> `INSTALLED_APPS`.

**How the code satisfies it.** The tree was created exactly at the ADR-0001 path. There is
one `AppConfig`, `LearningConfig` in `src/openedx_learning/apps.py`; the `cbe` applet
intentionally has **no** `apps.py` of its own, matching how `openedx_content`'s nine
applets work. The app is registered in `test_settings.py`, and also in `projects/dev.py`
(plan assumption A5: `mypy.ini` points django-stubs at `projects.dev`, so leaving it out
there would break `mypy`).

**Your manual check.**

Step 1 — the paths are what ADR-0001 requires:

```bash
find src/openedx_learning -name "*.py" -o -name "py.typed" | sort
```

Expected:

```
src/openedx_learning/__init__.py
src/openedx_learning/admin.py
src/openedx_learning/api.py
src/openedx_learning/applets/__init__.py
src/openedx_learning/applets/cbe/__init__.py
src/openedx_learning/applets/cbe/admin.py
src/openedx_learning/applets/cbe/api.py
src/openedx_learning/applets/cbe/models.py
src/openedx_learning/apps.py
src/openedx_learning/migrations/0001_initial.py
src/openedx_learning/migrations/__init__.py
src/openedx_learning/models.py
src/openedx_learning/models_api.py
src/openedx_learning/py.typed
```

Step 2 — exactly one `AppConfig` in the whole app:

```bash
grep -rn "AppConfig" src/openedx_learning/
```

Expected: two lines, both in `apps.py` (the import and the class definition). Nothing
under `applets/`.

Step 3 — Django agrees there is one app, with the label and models we expect:

```bash
.venv/bin/python manage.py shell -c "
from django.apps import apps
cfg = apps.get_app_config('openedx_learning')
print('class      :', type(cfg).__name__)
print('name       :', cfg.name)
print('label      :', cfg.label)
print('verbose    :', cfg.verbose_name)
print('models     :', [m.__name__ for m in cfg.get_models()])
"
```

Expected:

```
class      : LearningConfig
name       : openedx_learning
label      : openedx_learning
verbose    : Open edX Core > Learning
models     : ['CompetencyTaxonomy']
```

Step 4 — registered in both settings modules:

```bash
grep -n "openedx_learning" test_settings.py projects/dev.py
```

Expected: one hit in each file, inside `INSTALLED_APPS`.

**Why this is sufficient.** Step 1 is the literal path claim in the AC. Step 3 is the one
that matters most architecturally: `apps.get_app_config(...)` succeeding at all proves the
app is installed and importable, `models: ['CompetencyTaxonomy']` proves the umbrella
`models.py` re-export chain actually works (if that one-line file were missing, Django
would register **zero** models and this list would be empty while everything else still
looked fine), and a single `AppConfig` class proves the applet did not sprout its own,
which would have created a second Django app and a second migration history.

---

### AC 6 — `.importlinter` updated, `lint-imports` passes, rules not loosened

> `.importlinter` is updated: `openedx_learning` added to `root_packages` and placed in
> `src_layering` above `openedx_tagging`. `lint-imports` passes. The rules are not
> loosened to make it pass.

**How the code satisfies it.** `openedx_learning` was added to `root_packages` and placed
as the **top** layer of the `src_layering` contract, above `openedx_content` and therefore
above `openedx_tagging`. In an import-linter `layers` contract, the module listed first is
the highest layer; a higher layer may import a lower one, and a lower layer importing a
higher one fails the build. The stale comment that used to say `openedx_content` was "the
highest-level thing in this repo" was rewritten, since this change makes it false.

**Your manual check.**

Step 1 — read the diff of the config and satisfy yourself nothing was weakened:

```bash
git diff main...HEAD -- .importlinter
```

You should see only additions: `openedx_learning` in `root_packages`, a new top layer with
its comment, and the reworded `openedx_content` comment. Watch specifically for things
that would count as "loosening": a removed layer, a `|` joining two previously separate
layers (that makes them siblings, allowed to import each other), an added
`ignore_imports`, or a contract switched to `type = forbidden`. None of those should be
present.

Step 2 — the contracts pass:

```bash
.venv/bin/lint-imports
```

Expected, ending with:

```
Contracts: 2 kept, 0 broken.
```

Step 3 — **[destructive-then-revert]** prove the rule actually has teeth. A passing linter
tells you nothing if the rule is unenforceable. Add an illegal import to the *lower* layer
and confirm the build breaks:

```bash
# Deliberately violate the layering: make tagging import from learning.
printf '\nfrom openedx_learning.models import CompetencyTaxonomy  # TEMPORARY\n' >> src/openedx_tagging/models/__init__.py
.venv/bin/lint-imports
```

Expected: the run **fails**, printing exactly this (verified):

```
----------------
Broken contracts
----------------

"top-level source folders are layered correctly"
------------------------------------------------

openedx_tagging is not allowed to import openedx_learning:

- openedx_tagging.models -> openedx_learning.models (l.8)
```

Now put it back and confirm you are clean again:

```bash
git checkout -- src/openedx_tagging/models/__init__.py
.venv/bin/lint-imports
git status --porcelain src/openedx_tagging/
```

Expected: `Contracts: 2 kept, 0 broken.` and empty `git status` output.

Step 4 — confirm the direction of the dependency in the real code, not just in config:

```bash
grep -rn "openedx_learning\|[Cc]ompetency" src/openedx_tagging/ && echo "FAIL" || echo "PASS: openedx_tagging has no knowledge of CBE"
grep -rn "openedx_tagging" src/openedx_learning/
```

Expected: `PASS: openedx_tagging has no knowledge of CBE`, and the second command showing
that `openedx_learning` does import `openedx_tagging` (in `applets/cbe/models.py` and
`applets/cbe/api.py`). Dependencies point one way only.

**Why this is sufficient.** Steps 1 and 2 cover the letter of the AC. Step 3 covers its
intent, which the AC's own phrase "not loosened to make it pass" is reaching for: it
demonstrates the contract would actually catch the mistake it exists to prevent. This is
the single most valuable check in this document, because layering rules are easy to write
in a form that is technically present but vacuous. Step 4 confirms the real import graph
matches the declared architecture: CBE builds on tagging, and tagging stays ignorant of
CBE. That ignorance is exactly what lets tagging remain a low-level, broadly reusable app.

---

### AC 7 — `0001_initial.py` creates the table and applies cleanly against an empty DB

> `migrations/0001_initial.py` creates the `CompetencyTaxonomy` table and applies cleanly
> against an empty database.

**How the code satisfies it.** The migration was generated by `makemigrations`, not
hand-written, and then reviewed. It contains a single `CreateModel` with the two expected
fields, `bases=('oel_tagging.taxonomy',)`, and an autodetected dependency on
`oel_tagging`'s current leaf migration (`0020_tag_depth_and_lineage`). It lives at
`src/openedx_learning/migrations/`, **not** under the applet.

That last point contradicts the ticket, which lists
`src/openedx_learning/applets/cbe/migrations/0001_initial.py`. The ticket is wrong and the
plan overrode it (conflict C1): Django resolves migrations from `<AppConfig.name>.migrations`,
which is `openedx_learning.migrations`. A `migrations/` package nested inside an applet
would be **silently ignored**. `openedx_content` confirms this: one `migrations/` directory
at umbrella level, zero per-applet ones, across nine applets. If you are reviewing #641 and
#642 later, their ticket text has the same error.

**Your manual check.**

Step 1 — read the migration. It is short; read all of it:

```bash
cat src/openedx_learning/migrations/0001_initial.py
```

Check for: `initial = True`; `dependencies` naming `oel_tagging`; exactly one
`CreateModel`; exactly the fields `taxonomy_ptr` and `taxonomy_overrides_org`;
`bases=('oel_tagging.taxonomy',)`. Anything else means something is wrong upstream in the
model.

Step 2 — the dependency really is `oel_tagging`'s leaf, not an arbitrary older migration:

```bash
ls src/openedx_tagging/migrations/00*.py | tail -3
```

Expected: the highest-numbered file is `0020_tag_depth_and_lineage.py`, matching the
migration's `dependencies`.

Step 3 — apply it from genuinely nothing:

```bash
rm -f dev.db
.venv/bin/python manage.py migrate 2>&1 | tail -25
```

Expected: `Applying openedx_learning.0001_initial... OK`, no errors, and no interactive
prompts (a prompt would mean Django thinks it needs a default for something).

Step 4 — the table is really there and usable:

```bash
sqlite3 dev.db "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'openedx_learning%';"
sqlite3 dev.db "SELECT COUNT(*) FROM openedx_learning_competencytaxonomy;"
```

Expected: the table name, then `0`.

Step 5 — there is no undetected model/migration drift for our app:

```bash
.venv/bin/python manage.py makemigrations openedx_learning --check --dry-run; echo "exit code: $?"
```

Expected: `No changes detected in app 'openedx_learning'` and exit code `0`.

> Note: running `makemigrations --check --dry-run` **without** the app name reports a
> pre-existing, unrelated drift in the third-party `organizations` package
> (`historicalorganization.history_date`). That is present on `main` too and is not
> something this ticket introduced. Scoping the command to `openedx_learning` isolates
> our app, which is what this AC is about.
>
> **If you want to confirm any "pre-existing" claim in this document yourself, use
> `git stash -u`, not plain `git stash`.** Until this branch is committed,
> `src/openedx_learning/` and `tests/openedx_learning/` are *untracked*, and plain
> `git stash` leaves untracked files in place, so you would not actually be testing the
> baseline. The pattern is:
> ```bash
> git stash -u && <the command> ; git stash pop
> ```

**Why this is sufficient.** Step 3 against a deleted `dev.db` is literally the AC's
"empty database" scenario, run end to end, so there is no inference involved. Step 5 is
the complementary guarantee: `--check` fails if the model and the migration have drifted
apart, so passing it means the migration is a *complete* description of the model, not just
one that happens to apply. Step 2 matters because a wrong dependency is the classic way an
initial migration passes locally and then fails on a fresh CI database, where migration
order is not accidentally already satisfied.

---

### AC 8 — `CompetencyTaxonomy` is annotated `.. no_pii:`

> `CompetencyTaxonomy` is annotated `.. no_pii:`. This is this ticket's slice of #613's
> PII-annotation AC; the full `make pii_check` 100%-coverage gate is verified in #642.

**How the code satisfies it.** The annotation is inline in the model's class docstring
(plan assumption A8), where the `code_annotations` tool finds it. Inline was chosen over
`.annotation_safe_list.yml` so the annotation cannot drift away from the model; the safe
list is reserved for models this repo does not own.

**Your manual check.**

Step 1 — the annotation is present and inside the class docstring, not a loose comment:

```bash
grep -n -B 3 "no_pii" src/openedx_learning/applets/cbe/models.py
```

Expected: `.. no_pii:` appearing a few lines above the closing `"""` of the
`CompetencyTaxonomy` docstring.

Step 2 — the tool actually detects it. This is the part that matters, because the
annotation only counts if `code_annotations` parses it. Note the settings module: without
it the tool aborts with `ImproperlyConfigured`.

```bash
DJANGO_SETTINGS_MODULE=test_settings .venv/bin/code_annotations django_find_annotations \
  --config_file .pii_annotations.yml --report --coverage 2>&1 | tail -25
```

Confirm `openedx_learning.CompetencyTaxonomy` does **not** appear in the printed list of
uncovered models. Directly:

```bash
DJANGO_SETTINGS_MODULE=test_settings .venv/bin/code_annotations django_find_annotations \
  --config_file .pii_annotations.yml --report --coverage 2>&1 | grep -i "openedx_learning" \
  || echo "PASS: not in the uncovered list"
```

Expected: `PASS: not in the uncovered list`.

Now compare the counts against `main`:

```bash
DJANGO_SETTINGS_MODULE=test_settings .venv/bin/code_annotations django_find_annotations \
  --config_file .pii_annotations.yml --report --coverage 2>&1 | grep -iE "were eligible|Coverage is"
git stash -u
DJANGO_SETTINGS_MODULE=test_settings .venv/bin/code_annotations django_find_annotations \
  --config_file .pii_annotations.yml --report --coverage 2>&1 | grep -iE "were eligible|Coverage is"
git stash pop
```

Expected:

```
# with the branch
61 were eligible for annotation, 41 were annotated.
Coverage is 67.2%
# baseline (main)
60 were eligible for annotation, 40 were annotated.
Coverage is 66.7%
```

Both deltas being exactly `+1` is the signal: the new model was seen, **and** it was seen
as annotated. If the model were unannotated you would get `61 / 40`.

> **Do not be alarmed by `Coverage threshold not met! Needed 100.0, actually 67.2!`.**
> That failure is pre-existing: `main` is at 66.7%, with 20 unannotated models
> (`oel_publishing.*`, `openedx_catalog.*`, several `test_django_app.*` fixtures, and the
> third-party `organizations.*`). This branch moves coverage *up*, not down. The full
> 100% gate is #642's problem, which is why this ticket's AC is scoped to "the model is
> annotated" rather than "`pii_check` passes". Adding `--lint` additionally surfaces two
> pre-existing errors about `openedx_content.Draft` and `PublishableEntityVersion` being
> double-listed in the safe list; those are also on `main`.

**Why this is sufficient.** Step 1 alone would only prove a string exists in a file. Step 2
runs the exact tool that the `pii_check` gate runs, so it proves the annotation is in a
place and format the tool understands. The `+1 / +1` delta against `main` is stronger than
an absolute number, because it isolates this branch's contribution from the repo's
pre-existing annotation state.

> **Carry-forward, not a gap in this ticket:** this inline annotation does **not** satisfy
> edx-platform's own PII gate. That repo's `.pii_annotations.yml` uses `source_path: ./`,
> so it never reads docstrings inside installed site-packages, which is why 30 openedx-core
> models are already listed in edx-platform's `.annotation_safe_list.yml`. The follow-up
> platform PR must add `openedx_learning.CompetencyTaxonomy` there. See plan section 9,
> item 2.

---

### AC 9 — No ADR-0002 Decision 5 index lands here

> **No** index from ADR-0002 Decision 5 lands in this ticket: none of them target
> `CompetencyTaxonomy`. Called out so the whole-feature "all indexes present" gate
> (verified in #642) isn't read as a miss here.

**How the code satisfies it.** By correctly adding nothing. This AC exists so a reviewer
does not read the absence of indexes as an oversight.

**Your manual check.**

Step 1 — confirm the ADR's indexes genuinely do not target this model:

```bash
grep -n -A 25 "Decision 5" docs/openedx_learning/decisions/0002-*.rst
```

Read the list and confirm every index names one of the #641/#642 models
(`CompetencyCriteria`, `CompetencyCriteriaGroup`, `CompetencyRuleProfile`, the learner
status models), and none names `CompetencyTaxonomy`.

Step 2 — confirm we added no `indexes` or `Meta.constraints` of our own:

```bash
grep -rn "indexes\|constraints\|db_index" src/openedx_learning/ || echo "PASS: no index or constraint declarations"
```

Expected: `PASS: no index or constraint declarations`.

Step 3 — see what indexes the table does have:

```bash
sqlite3 dev.db "SELECT name, sql FROM sqlite_master WHERE type='index' AND tbl_name='openedx_learning_competencytaxonomy';"
```

Expected: empty, or at most an automatic index backing the primary key. Any *named*
index like `openedx_lea_..._idx` would mean an index was declared, contradicting the AC.

**Why this is sufficient.** This is a negative AC, so the check is a search for absence in
two places: our source (step 2) and the resulting schema (step 3). Step 1 is the part that
makes the absence *correct* rather than merely true: you have confirmed against the ADR
that no index was supposed to be here. Without step 1 you would only know we added none,
not that we should have added none.

---

## Part 2 — Architectural checks beyond the ACs

The ACs do not cover everything that matters. These four checks are where a
mechanically-correct implementation could still be architecturally wrong.

### B.1 — The MTI lifecycle behaves as ADR-0002 Decision 1 requires

**What is being claimed.** ADR-0002 Decision 1 says creating a competency taxonomy writes
both rows in one transaction, and deleting either representation removes both rows. The
plan claims this needs **no code**: it is Django's default MTI behaviour. Trust but verify,
because "we wrote no code for this" is only reassuring if the default really does it.

**Your manual check.** Run this whole block; it prints a verdict per claim.

```bash
.venv/bin/python manage.py shell -c "
from django.db import connection
from openedx_tagging.models import Taxonomy
from openedx_learning.models import CompetencyTaxonomy

CompetencyTaxonomy.objects.all().delete()
Taxonomy.objects.filter(export_id__startswith='mv-').delete()

# 1. Creating writes both rows.
ct = CompetencyTaxonomy.objects.create(name='Nursing', export_id='mv-nursing', taxonomy_overrides_org=True)
print('1 parent row exists     :', Taxonomy.objects.filter(pk=ct.pk).exists())
print('1 child row exists      :', CompetencyTaxonomy.objects.filter(pk=ct.pk).exists())
print('1 same primary key      :', ct.pk == ct.taxonomy_ptr_id)

# 2. Default is False.
plain_ct = CompetencyTaxonomy.objects.create(name='Welding', export_id='mv-welding')
print('2 default overrides_org :', plain_ct.taxonomy_overrides_org)

# 3. Parent fields read through the child; child reachable from parent.
print('3 child sees parent name:', CompetencyTaxonomy.objects.get(pk=ct.pk).name)
print('3 parent sees child     :', type(Taxonomy.objects.get(pk=ct.pk).competencytaxonomy).__name__)

# 4. Plain Taxonomy has no child.
plain = Taxonomy.objects.create(name='Plain', export_id='mv-plain')
try:
    plain.competencytaxonomy
    print('4 FAIL: expected RelatedObjectDoesNotExist')
except Taxonomy.competencytaxonomy.RelatedObjectDoesNotExist:
    print('4 plain raises DoesNotExist: True')

# 5a. Deleting the PARENT removes the child row.
Taxonomy.objects.get(pk=ct.pk).delete()
print('5a child gone after parent delete:', not CompetencyTaxonomy.objects.filter(pk=ct.pk).exists())

# 5b. Deleting the CHILD removes the parent row.
child_pk = plain_ct.pk
plain_ct.delete()
print('5b parent gone after child delete:', not Taxonomy.objects.filter(pk=child_pk).exists())

# 6. Querying the base class returns base instances, never children.
CompetencyTaxonomy.objects.create(name='Again', export_id='mv-again')
print('6 base queryset types   :', sorted({type(t).__name__ for t in Taxonomy.objects.filter(export_id__startswith=\"mv-\")}))

Taxonomy.objects.filter(export_id__startswith='mv-').delete()
print('cleanup done')
"
```

Expected output:

```
1 parent row exists     : True
1 child row exists      : True
1 same primary key      : True
2 default overrides_org : False
3 child sees parent name: Nursing
3 parent sees child     : CompetencyTaxonomy
4 plain raises DoesNotExist: True
5a child gone after parent delete: True
5b parent gone after child delete: True
6 base queryset types   : ['Taxonomy']
cleanup done
```

**Why this is sufficient.** Each line maps to a specific claim the plan makes and the
design leans on. Lines 5a and 5b together are the ADR's lifecycle rule, proven in both
directions, which is the interesting part: cascade from parent to child is obvious, but
child-delete-removes-parent is a Django MTI specific that many people do not expect. Line
6 looks like a curiosity but is load-bearing: it is *why* ADR-0013 could not simply put an
overridable `get_type()` method on `Taxonomy` and had to use a relation-existence check
instead. Seeing `['Taxonomy']` here is what justifies the whole API design in B.2.

### B.2 — The cross-repo contract is actually encapsulated

**What is being claimed.** ADR-0013 has openedx-platform (Studio) detect a competency
taxonomy via the related child row. The accessor name `competencytaxonomy` is generated by
Django from our class name, so hardcoding it in the other repo would mean a rename here
silently breaks Studio with nothing failing in CI. Plan step 5b therefore wraps it in
`is_competency_taxonomy()` and `select_competency_taxonomies()`, exported from
`openedx_learning.api`, so the string lives in exactly one place.

**Your manual check.**

Step 1 — the string appears exactly once in the repo, and it is private:

```bash
grep -rn "competencytaxonomy" src/ | grep -v "\.pyc"
```

Expected: a single hit, the `_COMPETENCY_TAXONOMY_RELATION` assignment in
`src/openedx_learning/applets/cbe/api.py`. The leading underscore means callers are meant
to use the functions, not the constant.

Step 2 — the public surface is importable from the umbrella `api`, which is what platform
will import:

```bash
.venv/bin/python manage.py shell -c "
import openedx_learning.api as api
print('exports:', sorted(n for n in dir(api) if not n.startswith('_')))
"
```

Expected to include `is_competency_taxonomy` and `select_competency_taxonomies`.

Step 3 — the functions work, and the `select_related` pairing really removes the N+1. This
is the regression test for ADR-0013's stated performance concern:

```bash
.venv/bin/python manage.py shell -c "
from django.db import connection, reset_queries
from django.conf import settings
settings.DEBUG = True
from openedx_tagging.models import Taxonomy
from openedx_learning.models import CompetencyTaxonomy
from openedx_learning.api import is_competency_taxonomy, select_competency_taxonomies

Taxonomy.objects.filter(export_id__startswith='n1-').delete()
CompetencyTaxonomy.objects.create(name='A', export_id='n1-a')
CompetencyTaxonomy.objects.create(name='B', export_id='n1-b')
Taxonomy.objects.create(name='C', export_id='n1-c')

qs = Taxonomy.objects.filter(export_id__startswith='n1-').order_by('export_id')

reset_queries()
naive = [is_competency_taxonomy(t) for t in qs]
print('naive  results:', naive, 'queries:', len(connection.queries))

reset_queries()
opt = [is_competency_taxonomy(t) for t in select_competency_taxonomies(qs)]
print('opt    results:', opt, 'queries:', len(connection.queries))

# The optimized path must still return the plain taxonomy (LEFT OUTER JOIN, not INNER).
print('row count preserved:', len(opt) == 3)
Taxonomy.objects.filter(export_id__startswith='n1-').delete()
"
```

Expected:

```
naive  results: [True, True, False] queries: 4
opt    results: [True, True, False] queries: 1
row count preserved: True
```

The naive path costs 1 query for the list plus 1 per taxonomy (4 total for 3 rows). The
optimized path costs exactly 1. Same answers either way.

Step 4 — prove the risk is real, without editing anything. Ask Django where the accessor
name comes from:

```bash
.venv/bin/python manage.py shell -c "
from openedx_learning.models import CompetencyTaxonomy
accessor = CompetencyTaxonomy._meta.pk.remote_field.get_accessor_name()
print('accessor Django generates :', accessor)
print('class name, lowercased    :', CompetencyTaxonomy.__name__.lower())
print('accessor is derived from the class name:', accessor == CompetencyTaxonomy.__name__.lower())
"
```

Expected:

```
accessor Django generates : competencytaxonomy
class name, lowercased    : competencytaxonomy
accessor is derived from the class name: True
```

That third line is the whole argument. The accessor name is not something we chose and
wrote down; Django derives it from the class name. So renaming `CompetencyTaxonomy` to
anything else silently changes the string that Studio would otherwise have hardcoded, and
no test in *this* repo would notice. Because `api.py` holds the name in one constant behind
two functions, that rename becomes a one-line edit here instead of a production break
there.

> Do **not** try to demonstrate this by actually renaming the class. `admin.py` and
> `models.py` both import `CompetencyTaxonomy` by name, so a partial rename breaks Django's
> admin autodiscovery at startup, and because `src/openedx_learning/` is still *untracked*
> until this branch is committed, `git checkout --` cannot restore it for you. The check
> above proves the same thing with no edits.

**Why this is sufficient.** Step 1 proves the duplication is gone (one occurrence, not
two repos' worth). Step 3 proves the API is correct *and* fast, and the `row count
preserved` line rules out the easy mistake of `select_related` accidentally filtering out
plain taxonomies. Step 4 is the interesting one: it demonstrates the exact failure mode the
design defends against, so you can see the defence is aimed at something real. Together
they show this is not speculative abstraction; it is removing a cross-repo string
duplication that no test in either repo would otherwise catch.

> **Resolved, previously an open question.** ADR-0013's Decision text used to say the
> taxonomy type should be reported "without adding any field, method, or enum value to
> `openedx_tagging` **or the CBE app**", which the two functions above arguably brushed
> against. That clause was a drafting error: the real constraint is on `openedx_tagging`,
> and the CBE app is precisely where this belongs, since it owns the relation. ADR-0013 has
> been amended, so the prohibition now names `openedx_tagging` alone and the Decision states
> that openedx-platform calls `openedx_learning.api` rather than spelling the accessor.
> Verify with:
>
> ```bash
> git diff main...HEAD -- docs/openedx_tagging/decisions/0013-competency-taxonomy-detection.rst
> ```

### B.3 — The admin page works end to end

**What is being claimed.** `CompetencyTaxonomyAdmin` is registered through the umbrella
`admin.py` re-export chain, and its `list_display` / `list_filter` reference fields that
exist (three of the four come from the parent `Taxonomy` via MTI, which is exactly the kind
of thing that breaks at runtime rather than at import time).

**Your manual check.**

Step 1 — Django's own system checks validate admin field references:

```bash
.venv/bin/python manage.py check
```

Expected: `System check identified some issues` with only pre-existing warnings
(`debug_toolbar.W001`, an `organizations` `W042`) and **zero** errors. Any `admin.E108`
/`E116` style error would mean a `list_display` or `list_filter` name is wrong.

Step 2 — see it in a browser, which is the only real UI this ticket has:

```bash
.venv/bin/python manage.py migrate
.venv/bin/python manage.py createsuperuser --username admin --email admin@example.com
.venv/bin/python manage.py runserver 8020
```

Open <http://127.0.0.1:8020/admin/>, log in, and confirm:

- a section **"Open edX Core > Learning"** appears (this is the `AppConfig.verbose_name`);
- inside it, **"Competency Taxonomies"** (plural spelled correctly, which is what the
  `verbose_name_plural` in `Meta` is for; without it Django renders "Competency taxonomys");
- click "Add", fill in `Name` = `Nursing`, `Export id` = `nursing-v1`, leave the rest
  alone, and save;
- the changelist shows columns `Name`, `Export id`, `Enabled`, `Taxonomy overrides org`,
  with filters for the last two in the right sidebar.

Stop the server with Ctrl-C.

Step 3 — confirm what the admin form just did, at the database level:

```bash
sqlite3 dev.db "SELECT id, name, export_id FROM oel_tagging_taxonomy WHERE export_id='nursing-v1';"
sqlite3 dev.db "SELECT taxonomy_ptr_id, taxonomy_overrides_org FROM openedx_learning_competencytaxonomy;"
```

Expected: the same id in both, proving one admin save wrote both tables.

**Why this is sufficient.** Step 1 is a genuine correctness gate, not a formality: Django's
admin checks resolve every `list_display` and `list_filter` name against the model, so
`Name`, `Export id` and `Enabled` passing proves MTI field inheritance works for the admin
too. Step 2 is the only human-visible surface this ticket produces, and it exercises the
full chain (`INSTALLED_APPS` → `AppConfig` → umbrella `admin.py` → applet `admin.py` →
`admin.site.register`); if any link were missing the section simply would not appear. Step
3 closes the loop by showing that a single user action produced the two-row MTI structure
from AC 1, through a real code path rather than a shell.

### B.4 — The pre-existing `cast()` / `_taxonomy_class` mechanism was correctly left alone

**What is being claimed.** `Taxonomy` already has a subclass-dispatch mechanism: a
`_taxonomy_class` column plus `cast()`/`copy()` methods. Every *existing* `Taxonomy`
subclass in this repo is a **proxy** model that uses it. `CompetencyTaxonomy` is the
repo's first true MTI subclass, and it must **not** use that mechanism: `cast()` copies a
hardcoded list of base `Taxonomy` fields in Python and never queries the subclass's own
table, so casting would hand back a `CompetencyTaxonomy` with `taxonomy_overrides_org`
unset. ADR-0013 notes that pattern is planned for removal.

**Your manual check.**

Step 1 — we neither set nor reference the old mechanism:

```bash
grep -rn "_taxonomy_class\|\.cast(\|taxonomy_class" src/openedx_learning/ || echo "PASS: CBE does not touch the cast mechanism"
```

Expected: `PASS: CBE does not touch the cast mechanism`.

Step 2 — confirm the neighbouring subclasses really are proxies, so you can see why this
was worth being careful about:

```bash
.venv/bin/python manage.py shell -c "
from openedx_tagging.models import Taxonomy
from openedx_learning.models import CompetencyTaxonomy
for cls in Taxonomy.__subclasses__():
    print(f'{cls.__name__:24} proxy={cls._meta.proxy}  own_table={cls._meta.db_table if not cls._meta.proxy else None}')
"
```

Expected (verified):

```
SystemDefinedTaxonomy    proxy=True  own_table=None
CompetencyTaxonomy       proxy=False  own_table=openedx_learning_competencytaxonomy
```

`__subclasses__()` only lists *direct* subclasses, which is why you see one proxy rather
than all of them; `LanguageTaxonomy` and friends sit under `SystemDefinedTaxonomy`. The
contrast is the point: every pre-existing subclass of `Taxonomy` in this repo is a proxy
with no table of its own, and ours is the first that is not.

Step 3 — confirm a stored competency taxonomy leaves `_taxonomy_class` null, so nothing
will later try to `cast()` it:

```bash
sqlite3 dev.db "SELECT export_id, _taxonomy_class IS NULL AS class_is_null FROM oel_tagging_taxonomy WHERE export_id='nursing-v1';"
```

Expected: `nursing-v1|1` (null, as it should be).

**Why this is sufficient.** This is a "did we avoid the trap" check rather than a feature
check, so the evidence is absence in our code (step 1) plus absence in the data (step 3).
Step 2 is what makes it meaningful: it shows that every nearby example in the codebase uses
the *other* pattern, so copying a neighbour would have produced a proxy model with no
table, no column, and no `competencytaxonomy` accessor, quietly breaking both AC 1 and the
ADR-0013 contract. Confirming we did not follow that path is worth a minute.

---

## Part 3 — What this ticket deliberately does not do

Do not read any of these as gaps. Each is scoped to another ticket, and each is checkable
as an intentional absence.

| Deliberately absent | Belongs to | Quick confirmation |
|---|---|---|
| The three criteria models (`CompetencyCriteriaGroup`, `CompetencyCriteria`, `CompetencyRuleProfile`) | #641 | `grep -rn "CompetencyCriteria\|RuleProfile" src/openedx_learning/` → no hits |
| Mastery status / learner progress models | #642 | same grep, no hits |
| `on_delete=PROTECT` delete protection | #642 | AC 4 check shows `CASCADE`, which is the ADR's current lifecycle rule |
| Any history tracking, `simple_history` in `INSTALLED_APPS` | #641 | AC 2 checks |
| Any REST API or UI | out of scope entirely | no `views.py`, `serializers.py`, or `urls.py` in `src/openedx_learning/` |
| A `learning_applet_layering` import-linter contract | when a 2nd applet exists | a one-layer `layers` contract constrains nothing (plan A9) |
| edx-platform registration | follow-up PR in that repo | see plan section 9; the app is inert in a real deployment until then |

The last row is the one worth remembering: **merging this alone changes nothing in a
running Open edX instance.** Four things are needed in edx-platform (`INSTALLED_APPS` in
both `lms/envs/common.py` and `cms/envs/common.py`, the PII safe-list entry, an
openedx-core version bump that must land *after* this releases, and ideally an
`isolated_apps` entry in `pyproject.toml`). Plan section 9 has the detail.

---

## Part 4 — Run the automated tests too

The manual checks above overlap the automated tests on purpose: the tests protect the
behaviour in CI, the manual checks let you confirm the same claims yourself.

```bash
DJANGO_SETTINGS_MODULE=test_settings .venv/bin/pytest tests/openedx_learning -p no:cacheprovider --no-cov -v
```

Expected: 8 passed. The eight map one-to-one onto the plan's Step 9 list:

| Test | Pins |
|---|---|
| `test_models.py::test_create_writes_both_rows` | Step 9.1 — both rows written |
| `test_models.py::test_taxonomy_overrides_org_defaults_false` | Step 9.2 — default is `False` |
| `test_models.py::test_mti_round_trip` | Step 9.3 — MTI works both directions |
| `test_models.py::test_plain_taxonomy_has_no_competencytaxonomy` | Step 9.4 — plain taxonomy raises |
| `test_models.py::test_delete_cascades_both_directions` | Step 9.5 — lifecycle, both directions |
| `test_api.py::test_is_competency_taxonomy` | Step 9.6 — True/False correctly |
| `test_api.py::test_is_competency_taxonomy_on_child_instance_directly` | Step 9.7 — works on the child too |
| `test_api.py::test_select_competency_taxonomies_avoids_n_plus_1` | Step 9.8 — the ADR-0013 N+1 regression test |

Then the whole suite, to confirm nothing regressed:

```bash
DJANGO_SETTINGS_MODULE=test_settings .venv/bin/pytest tests -p no:cacheprovider --no-cov -q
```

Expected: `823 passed, 1 skipped`. (`main` is 815 passed, 1 skipped; the 8 new tests are
the difference.)

And the style and type gates, all of which are currently clean:

```bash
.venv/bin/pylint src/openedx_learning tests/openedx_learning
.venv/bin/pycodestyle src/openedx_learning tests/openedx_learning
.venv/bin/pydocstyle src/openedx_learning
.venv/bin/isort --check-only --diff src/openedx_learning tests/openedx_learning test_settings.py
.venv/bin/mypy
```

Expected: silence from the first four, and `Success: no issues found in 281 source files`
from `mypy`.

> One pre-existing failure you will hit if you widen the `isort` command to include
> `projects/dev.py`: that file is missing a blank line after `from __future__ import
> annotations`. It fails on `main` too (check with `git stash -u`), and this branch only
> added a line to its `INSTALLED_APPS`, so fixing it was left alone as unrelated churn.

Note that there is deliberately **no** `# noqa`, `# pylint: disable=<check>` added to
silence a failure, or `# type: ignore` anywhere in this change. The three
`# pylint: disable` comments that do exist (`wildcard-import` twice, `unused-import` once)
are structural, mirroring the identical re-export pattern already merged in
`openedx_content` and `openedx_catalog`, not suppressions of a real problem. Worth spot
checking, since silencing a linter is the easy way to make a change look clean:

```bash
grep -rn "noqa\|type: ignore\|pylint: disable" src/openedx_learning tests/openedx_learning
```

Expected: exactly three hits, all `wildcard-import` / `unused-import` on re-export lines,
and no `# type: ignore` at all.

---

## Part 5 — End-to-end integration test in a real Open edX (tutor)

Everything in Parts 1-4 runs against this library in isolation. That proves the app is
correct, but **not** that it actually works inside Open edX, because openedx-core is a
library: merging #640 alone changes nothing in a running instance until edx-platform
registers the app.

So that you can integration test, the platform side has been implemented too, as a
minimal version of <https://github.com/openedx/openedx-platform/issues/38958>.

> **Honesty note about this Part.** Parts 1-4 were executed command by command and their
> expected outputs are copied from real runs. **Part 5 was not executed** — running it means
> a long Docker image rebuild against your local tutor environment, which is yours to
> drive. Treat the commands below as carefully constructed but unverified, and expect to
> adapt them.

### 5.1 What was prepared for you

In the sibling repo `../edx-platform`:

- Branch: `jesperhodge/feat--38958-register-openedx-learning`
- Commit: `3bac2e8d8c` (not pushed, no PR opened, `master` untouched)

| Change | File | Why |
|---|---|---|
| `"openedx_learning"` added to `INSTALLED_APPS` | `lms/envs/common.py` (line ~2115) and `cms/envs/common.py` (line ~918) | Without it Django never loads the model and never creates the table |
| `openedx_learning.CompetencyTaxonomy: ".. no_pii:": "No PII"` | `.annotation_safe_list.yml` | Platform's PII scan uses `source_path: ./` and never reads site-packages, so our inline annotation does not reach it |
| `openedx_learning` added to the `isolated_apps` contract **and** to `root_packages` | `pyproject.toml` | Makes "platform may only import `openedx_learning.api`" CI-enforced, protecting the ADR-0013 relation name |

**One deliberate omission.** Issue #38958 also asks for the `openedx-core` pin in
`requirements/edx/kernel.in` and `requirements/edx/base.txt` to be bumped. That was **not**
done, on purpose: `base.txt` pins `openedx-core==1.1.0`, and the version containing
`openedx_learning` does not exist on PyPI yet because #640 is still an unmerged branch.
Bumping to a nonexistent version would break `pip install` for everyone. It does not block
you: your tutor setup installs openedx-core as an editable bind mount
(`pip install -e /mnt/openedx-core` against `/Users/jesperhodge/openedx/openedx-core`),
which overrides the pin entirely. The pin bump has to happen after #640 merges and
releases, which is also the issue's own stated ordering constraint.

**One judgment call to eyeball.** The `root_packages` line was added beyond the literal
text of #38958. The reasoning: import-linter only walks a package's full submodule tree for
packages named in `root_packages`, and `openedx_catalog` (the entry `openedx_learning` was
modelled on) appears in both lists. Listing it only in `isolated_apps` risked a contract
that silently checks nothing. Worth thirty seconds of your review:

```bash
cd ../edx-platform && git show 3bac2e8d8c -- pyproject.toml
```

### 5.2 Check out both branches

```bash
cd /Users/jesperhodge/openedx/openedx-core && git status --porcelain   # the #640 work
cd ../edx-platform && git checkout jesperhodge/feat--38958-register-openedx-learning
```

Both repos are bind-mounted into tutor (`openedx-core` at `/mnt/openedx-core`,
`edx-platform` at `/openedx/edx-platform`), so whatever is checked out is what runs.

### 5.3 Rebuild and start

Per the workflow in your top-level `CLAUDE.md`, the image rebuild is what actually picks up
the editable install of openedx-core:

```bash
source ~/.virtualenvs/tutor/bin/activate
tutor images build openedx-dev
tutor dev start -d
tutor dev do init          # runs migrations across LMS and CMS
```

The rebuild is the slow step. If you want a faster loop and accept that it lasts only for
the current container's lifetime, you can instead
`tutor dev exec lms pip install -e /mnt/openedx-core` and then run migrations directly.

### 5.4 Confirm the app is live

Step 1 — Django sees the app in both LMS and CMS:

```bash
tutor dev exec lms python manage.py lms shell -c "
from django.apps import apps
cfg = apps.get_app_config('openedx_learning')
print('LMS:', cfg.label, [m.__name__ for m in cfg.get_models()])
"
tutor dev exec cms python manage.py cms shell -c "
from django.apps import apps
cfg = apps.get_app_config('openedx_learning')
print('CMS:', cfg.label, [m.__name__ for m in cfg.get_models()])
"
```

Expected: `openedx_learning ['CompetencyTaxonomy']` from both.

Step 2 — the migration ran and the table exists **in MySQL**, not just sqlite. This is the
one thing Parts 1-4 genuinely cannot tell you, since they only ever exercised sqlite:

```bash
tutor dev exec lms python manage.py lms showmigrations openedx_learning
tutor dev exec lms python manage.py lms dbshell -- -e "
  SHOW TABLES LIKE 'openedx_learning%';
  DESCRIBE openedx_learning_competencytaxonomy;
"
```

Expected: `[X] 0001_initial`, the table listed, and a `DESCRIBE` showing exactly two
columns — `taxonomy_ptr_id` (`bigint`, `PRI`) and `taxonomy_overrides_org` (`tinyint(1)`).
Confirming the MySQL column types is the real value here: MySQL renders Django's
`BooleanField` as `tinyint(1)` and the MTI pointer as a `bigint` primary key that is also a
foreign key, and a schema that applies on sqlite can still fail on MySQL.

Step 3 — the MTI round trip works against MySQL, through the public API that Studio will
use:

```bash
tutor dev exec lms python manage.py lms shell -c "
from openedx_tagging.models import Taxonomy
from openedx_learning.models import CompetencyTaxonomy
from openedx_learning.api import is_competency_taxonomy, select_competency_taxonomies

Taxonomy.objects.filter(export_id__startswith='it-').delete()
ct = CompetencyTaxonomy.objects.create(name='Nursing', export_id='it-nursing')
plain = Taxonomy.objects.create(name='Plain', export_id='it-plain')

print('child readable from parent :', type(Taxonomy.objects.get(pk=ct.pk).competencytaxonomy).__name__)
print('api says competency        :', is_competency_taxonomy(Taxonomy.objects.get(pk=ct.pk)))
print('api says plain             :', is_competency_taxonomy(plain))
qs = select_competency_taxonomies(Taxonomy.objects.filter(export_id__startswith='it-'))
print('select_related works       :', [is_competency_taxonomy(t) for t in qs])
Taxonomy.objects.filter(export_id__startswith='it-').delete()
print('cleanup done')
"
```

Expected: `CompetencyTaxonomy`, `True`, `False`, a two-element list containing one `True`
and one `False`, then `cleanup done`.

Step 4 — the admin page renders inside Studio/LMS. Go to
<http://local.openedx.io:8000/admin/> (LMS) or <http://studio.local.openedx.io:8001/admin/>
(CMS), log in as a superuser, and confirm the **"Open edX Core > Learning"** section with
**"Competency Taxonomies"** in it. Create one through the form and re-run the `DESCRIBE`
query's sibling:

```bash
tutor dev exec lms python manage.py lms dbshell -- -e "
  SELECT t.id, t.name, c.taxonomy_overrides_org
  FROM oel_tagging_taxonomy t
  JOIN openedx_learning_competencytaxonomy c ON c.taxonomy_ptr_id = t.id;
"
```

Expected: your row, joined across both tables — which is the MTI structure working end to
end through a real UI in a real deployment.

Step 5 — optional, the platform's own gates:

```bash
cd ../edx-platform
make pii_check        # slow; should report 100% coverage
lint-imports          # the isolated_apps contract, including the new entry
```

`pii_check` is the one that would catch a missing `.annotation_safe_list.yml` entry.

### 5.5 Integration cleanup

```bash
tutor dev exec lms python manage.py lms shell -c "
from openedx_tagging.models import Taxonomy
Taxonomy.objects.filter(export_id__startswith='it-').delete()
print('removed test taxonomies')
"
cd ../edx-platform && git checkout master    # if you want to park the platform branch
```

Nothing here writes data you need to keep. Note the platform branch is local only: it has
not been pushed and no PR was opened, so it is yours to amend, rename, or discard.

---

## Part 6 — Cleanup

```bash
rm -f dev.db
[ -f dev.db.bak ] && mv dev.db.bak dev.db
git status --porcelain          # should show only intended branch changes, no stray edits
```

Expected `git status --porcelain` output, assuming the branch is not yet committed:

```
 M .importlinter
 M projects/dev.py
 M test_settings.py
?? src/openedx_learning/
?? tests/openedx_learning/
```

Only one check in this document edits a file: A.6 step 3, which appends a line to
`src/openedx_tagging/models/__init__.py`. That file is tracked, so
`git checkout -- src/openedx_tagging/models/__init__.py` restores it. If
`src/openedx_tagging/` shows as modified in the output above, that revert did not happen.

---

## Part 7 — Sign-off checklist

| # | Check | AC / concern | Pass? |
|---|---|---|---|
| A.1 | MTI table exists; `taxonomy_ptr_id` is PK and FK to `oel_tagging_taxonomy.id`; no `taxonomy_type` column | AC 1 | ☐ |
| A.2 | No `HistoricalRecords`, no historical tables, `openedx_tagging` untouched | AC 2 | ☐ |
| A.3 | Exactly two columns, both ADR-defined | AC 3 | ☐ |
| A.4 | Exactly one relationship, the MTI parent link, `CASCADE` | AC 4 | ☐ |
| A.5 | Correct paths, one `AppConfig`, registered in both settings modules, one model discovered | AC 5 | ☐ |
| A.6 | `lint-imports` passes, rule has teeth, tagging has no CBE knowledge | AC 6 | ☐ |
| A.7 | Migration reviewed, applies to an empty DB, no drift | AC 7 | ☐ |
| A.8 | `code_annotations` sees the `.. no_pii:` annotation (+1/+1 vs `main`) | AC 8 | ☐ |
| A.9 | No indexes declared, and none were required | AC 9 | ☐ |
| B.1 | MTI lifecycle: both rows created, delete works both directions, base queryset returns base type | ADR-0002 D1 | ☐ |
| B.2 | Relation name appears once, API exported, N+1 removed, rename risk demonstrated | ADR-0013 | ☐ |
| B.3 | Admin section renders, a save writes both tables | usability / wiring | ☐ |
| B.4 | `cast()` / `_taxonomy_class` mechanism correctly untouched | plan C5 | ☐ |
| — | Automated tests, linters, and `mypy` clean; no suppressions added | quality gate | ☐ |
| 5.4 | App live in tutor: LMS + CMS load it, MySQL table has the right column types, admin works | integration | ☐ |
| — | Read the ADR-0013 amendment diff (B.2 note) | resolved | ☐ |
| — | Review the extra `root_packages` line in the platform commit (5.1) | judgment call | ☐ |
| — | Decide whether to bump the openedx-core pin in edx-platform after release (5.1) | sequencing | ☐ |

### What still needs a human, and what no longer does

**Resolved: the ADR-0013 wording (plan conflict C7).** The "or the CBE app" half of that
prohibition was a drafting error. The constraint that matters is on `openedx_tagging`,
which check A.6 step 4 proves is fully honoured, and the CBE app is exactly where this
belongs since it owns the relation. ADR-0013 has been amended in this branch: the
prohibition now names `openedx_tagging` alone, and the Decision records that
openedx-platform calls `openedx_learning.api` instead of spelling the accessor. Read the
diff rather than re-litigating the question.

**Still open:**

1. **Release ordering with edx-platform.** openedx-core #640 must merge and release before
   the platform branch can bump its pin and be merged, or `INSTALLED_APPS` will name an
   uninstalled module and every management command in Open edX will fail. This is why the
   platform branch deliberately skips the pin bump today.
2. **The extra `root_packages` line** in the platform commit, added beyond the literal text
   of #38958 with a documented rationale (see 5.1). One line, worth thirty seconds.

