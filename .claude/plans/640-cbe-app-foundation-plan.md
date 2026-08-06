# Implementation plan: #640 — CBE app foundation + `CompetencyTaxonomy`

Ticket: <https://github.com/openedx/openedx-core/issues/640>
Parent: <https://github.com/openedx/openedx-core/issues/613>
Siblings: #641 (criteria models), #642 (mastery status + learner progress)
Branch: `jesperhodge/feat--640-cbe-app-foundation`

**Status: plan only, no code written yet.** The user asked me to answer my own open
questions as documented assumptions rather than block on them. Everything I decided on
their behalf is in the two tables below. Read those first; the rest of the plan follows
from them.

---

## 1. What this ticket delivers

Three things, in order of how much thought they need:

1. A new top-level Django app, `openedx_learning`, which today contains exactly one
   applet: `cbe`. This app does not exist in the repo yet.
2. One model, `CompetencyTaxonomy`, which marks an existing tagging `Taxonomy` as
   "this taxonomy holds competencies, so CBE features apply to it".
3. The wiring that makes both real: `INSTALLED_APPS`, an initial migration, an
   `.importlinter` layer entry, admin registration, and a PII annotation.

Nothing else in the CBE feature lands here. #641 and #642 are both blocked on this
merging, and can then proceed in parallel.

---

## 2. Assumptions I made on your behalf

The ticket has two explicit "confirm before starting" questions, and building it
surfaced five more. Here is every decision I made without asking, with the reasoning,
so you can override any of them cheaply.

| # | Question | Decision | Why | Cost to reverse |
|---|---|---|---|---|
| A1 | Ticket Open Q1: does *this* ticket create the `openedx_learning` umbrella app? | **Yes** | ADR-0001 is authoritative on placement and says `src/openedx_learning/applets/cbe/`. The Learning Pathways workstream that ADR-0001 assumed would create the umbrella has not started and has no date. Putting CBE under `openedx_content/applets/` instead is ADR-0001's explicitly rejected Alternative 3. There is no third option that is ADR-compliant. | High — it changes every path in the ticket |
| A2 | Ticket Open Q2: is `taxonomy_overrides_org` in scope? | **Yes, include it** | This question is now **stale**. The ticket says the field only exists on branch `jesperhodge/competency-adr-4`. It is on `main` today, merged in `5cd47f1` ("docs: cbe competency rule profile adr amendments (#636)"), as Decision 1 column 2 of ADR-0002. Since the ADR now defines exactly two columns for this table, and one AC is "no columns exist on any model that are not defined in the ADRs", the mirror of that AC applies: omitting an ADR-defined column would leave the model non-conformant. The field is inert this phase (read by no code path), which is exactly what the ADR says it should be. | Low — one field + one migration |
| A3 | Where do migrations live? | **`src/openedx_learning/migrations/`**, not `src/openedx_learning/applets/cbe/migrations/` as the ticket says | See conflict C1 below. The ticket's path cannot work. | n/a — forced |
| A4 | Where exactly in the `.importlinter` `src_layering` contract? | **At the top, above `openedx_content`** | The ticket's only load-bearing constraint is "above `openedx_tagging`", which several positions satisfy. Top is the least restrictive placement that meets it, and it leaves room for the Learning Pathways applet (which will need to reference content) without re-opening the contract later. It also asserts the correct direction: `openedx_content` must never import learning-domain code. | Low — move one line |
| A5 | The ticket says register the app in `test_settings.py`. Anywhere else? | **Also `projects/dev.py`** | `mypy.ini` sets `django_settings_module = "projects.dev"`. If the app is missing there, django-stubs does not see it and `mypy` (part of `make quality`) reports the new model as belonging to no installed app. The ticket missed this. | Low |
| A6 | App label / table prefix — does the `oel_` prefix apply? | **No prefix. `label = "openedx_learning"`, table `openedx_learning_competencytaxonomy`** | The `oel_` prefix rule is ADR-0004, marked Obsolete and superseded by ADR-0010. `openedx_content` and `openedx_catalog` both use their unprefixed name as the label. Only `openedx_tagging` keeps `oel_tagging`, for backwards compatibility with existing tables. | High once merged (table rename) |
| A7 | Which umbrella-level modules to create beyond the bare minimum? | `models.py`, `admin.py`, `models_api.py`, `py.typed`, **and `api.py`** | The first two are load-bearing, not decoration: Django only discovers models via `openedx_learning.models` and only autoloads admin via `openedx_learning.admin`, and both are one-line wildcard re-exports exactly as in `openedx_content`. `models_api.py` and `py.typed` are one-liners present in all four existing `src/` packages. **`api.py` was originally skipped as speculative; reversed at the user's direction** — it now carries the two functions that encapsulate the ADR-0013 relation name (step 5b, and see C4). | Trivial |
| A8 | PII annotation: inline docstring or `.annotation_safe_list.yml`? | **Inline `.. no_pii:` in the model docstring** | The repo does both, but the AC literally asks for the model to be "annotated `.. no_pii:`", and inline keeps the annotation next to the model so it cannot drift. The safe list is better reserved for models we do not own. | Trivial |
| A9 | Add a `learning_applet_layering` import-linter contract, mirroring `content_applet_layering`? | **No, not yet** | A `layers` contract with one layer constrains nothing. Add it when the second applet (Learning Pathways) arrives. | Trivial |
| A10 | Any `HistoricalRecords()` anywhere in this ticket? | **No** | ADR-0003 Decision 2 excludes `CompetencyTaxonomy` explicitly, and #640's AC restates it. `simple_history` therefore does not need to be added to `INSTALLED_APPS` here — that becomes #641's job. | n/a |

---

## 3. Conflicts and stale facts found

These are things where the ticket text, the ADRs, and the repo disagree. I resolved each
in favour of what actually works, but you should know they exist.

| # | Conflict | Resolution |
|---|---|---|
| **C1** | The ticket lists `src/openedx_learning/applets/cbe/migrations/0001_initial.py`. Django resolves an app's migrations from `<AppConfig.name>.migrations`. With one `AppConfig` whose `name = "openedx_learning"` (which the same ticket requires), that is `openedx_learning.migrations`. A `migrations/` package nested inside an applet would be silently ignored, and `makemigrations` would write to the umbrella location anyway. Prior art agrees: `src/openedx_content/` has one `migrations/` dir at umbrella level and **zero** per-applet ones, across nine applets. | Use `src/openedx_learning/migrations/`. The ticket text is wrong and should be corrected so #641 and #642 do not repeat it. |
| **C2** | The ticket's Open Q2 describes `taxonomy_overrides_org` as living only on an unmerged branch. It is on `main`. | See assumption A2. The ticket's Open Q2 can be closed as resolved. |
| **C3** | The ticket says `django-simple-history==3.12.0` is already in `requirements/base.txt`. The actual pin is `3.13.0`. | Cosmetic. The ticket's conclusion ("no requirements work needed") still holds. |
| **C4** | ADR-0013 (`openedx_tagging/decisions/0013-competency-taxonomy-detection.rst`, Accepted, merged after this ticket family was written) builds a **cross-repo contract on top of this model**: openedx-platform detects a competency taxonomy by checking for a related `CompetencyTaxonomy` row on an already-fetched `Taxonomy`, and `select_related`s it. | Not a conflict, but a constraint this ticket must not break: the multi-table-inheritance parent link must keep its **default** accessor name, `competencytaxonomy`. Do not declare an explicit `parent_link` field, and do not set `related_name`. **Rather than leave that name as a bare string duplicated across two repos, this plan encapsulates it behind two functions in CBE's public API (step 5b), so it is written down in exactly one place.** That needs a small ADR-0013 amendment — see C7. |
| **C5** | `Taxonomy` carries an existing subclass-dispatch mechanism — a `_taxonomy_class` column plus `cast()`/`copy()` — which every current `Taxonomy` subclass in the repo uses. ADR-0013 states that pattern is planned for removal, and that `cast()` would silently misbehave for a true MTI subclass: it copies a hardcoded list of base `Taxonomy` fields in Python and never queries the subclass's own table, so it would hand back a `CompetencyTaxonomy` with `taxonomy_overrides_org` unset. | `CompetencyTaxonomy` is the repo's **first true MTI subclass of `Taxonomy`**. Do not set `_taxonomy_class` on it and do not route it through `cast()`. MTI is the decided pattern (ADR-0002 Decision 1); the existing mechanism is simply not part of it. |
| **C6** | `openedx_catalog` is not in `.importlinter` `root_packages` at all, so nothing about it is enforced. | Pre-existing gap, out of scope here. Worth noting for #641, whose `CompetencyCriteriaGroup.course_id` points at `openedx_catalog_courserun` — that import will be unanalyzed rather than validated. |
| **C7** | ADR-0013's Decision says to report taxonomy type "*without adding any field, method, or enum value to `openedx_tagging` **or the CBE app***". Step 5b adds two functions to the CBE app's public API. | **Needs a decision from the ADR-0013 author (merged as #662).** The load-bearing constraint in ADR-0013 is that `openedx_tagging` must stay unaware of CBE, and step 5b does not touch `openedx_tagging` at all: no field, no enum, no import, no new query cost. The "or the CBE app" clause reads as aimed at the rejected `Taxonomy.get_type()` override, which would have put a method on the shared model class. A module-level function in `openedx_learning.api`, in the app that owns the relation, is a different thing. Recommended: amend ADR-0013's Decision to say the relation name is encapsulated behind CBE's public API and openedx-platform calls that instead of spelling the accessor. Fallback if the author disagrees: export only the constant, not the functions (see "alternatives" in step 5b). |

---

## 4. Background a junior engineer needs before reading step 5

**Umbrella app + applets.** In this repo a "Django app" and a "Python package" are not
one-to-one. `openedx_content` is a single Django app (one `AppConfig`, one `migrations/`
dir, one app label) whose code is split into nine `applets/` subpackages purely for
human organisation. Django finds the models because `openedx_content/models.py`
wildcard-imports every applet's models; Django's admin autodiscovery finds the admin
classes because `openedx_content/admin.py` wildcard-imports every applet's admin. We are
copying that shape exactly, with `openedx_learning` as the app and `cbe` as its only
applet so far.

**Multi-table inheritance (MTI).** When a Django model subclasses a concrete model
(rather than an abstract one or a proxy), Django creates a *second* table for the child
holding only the child's own columns, plus an implicit `OneToOneField` back to the parent
row that doubles as the child's primary key. So:

```
oel_tagging_taxonomy                 openedx_learning_competencytaxonomy
+----+---------+------------+        +-----------------+------------------------+
| id | name    | export_id  |        | taxonomy_ptr_id | taxonomy_overrides_org |
+----+---------+------------+        +-----------------+------------------------+
| 42 | Nursing | nursing-v1 |  <---- | 42              | true                   |
+----+---------+------------+        +-----------------+------------------------+
```

Practical consequences, all of which we rely on and none of which need code:

- `taxonomy_ptr_id` is created for us. **Do not declare it.** The ticket says this too.
- From a child instance, every parent field is transparently available:
  `competency_taxonomy.name` works.
- From a parent instance, the child is reachable as `taxonomy.competencytaxonomy`, and
  raises `RelatedObjectDoesNotExist` when there is no child row. That is precisely the
  existence check ADR-0013 has openedx-platform perform, and why C4's naming constraint
  matters.
- `Taxonomy.objects.all()` returns plain `Taxonomy` instances, **not** `CompetencyTaxonomy`
  ones, even for rows that have a child. This is normal MTI behaviour and is why ADR-0013
  rejected an overridable `get_type()` method.
- Deleting either row deletes both: the parent link cascades downward by default, and
  Django's MTI delete of a child also removes its parent row. ADR-0002 Decision 1's
  lifecycle rule ("deleting either representation ... removes both rows") is therefore
  satisfied by default behaviour with no code. Decision 7's *delete protection* is a
  separate concern and belongs to #642.
- Creating a `CompetencyTaxonomy` writes both rows in one `save()`, inside a transaction.
  ADR-0002 Decision 1's "in one transaction" rule is likewise free.

**Import-linter `layers` contracts.** In `.importlinter`, the module listed **first is
the highest layer**. A higher layer may import a lower one; a lower layer importing a
higher one is a build failure. `openedx_learning` must sit above `openedx_tagging`
because `CompetencyTaxonomy` subclasses `Taxonomy`, and the whole point of the rule is
that `openedx_tagging` must never learn that CBE exists (agreed in #613's comments, and
the same principle ADR-0013 enforces on the openedx-platform side).

---

## 5. Files

### Create

```
src/openedx_learning/
├── __init__.py                        empty
├── py.typed                           empty marker, as in all four existing src packages
├── apps.py                            LearningConfig(AppConfig)
├── models.py                          from .applets.cbe.models import *
├── admin.py                           from .applets.cbe.admin import *
├── api.py                             from .applets.cbe.api import *
├── models_api.py                      from .models import CompetencyTaxonomy
├── migrations/
│   ├── __init__.py
│   └── 0001_initial.py                generated, then reviewed by hand
└── applets/
    ├── __init__.py
    └── cbe/
        ├── __init__.py
        ├── models.py                  CompetencyTaxonomy
        ├── api.py                     is_competency_taxonomy, select_competency_taxonomies
        └── admin.py                   CompetencyTaxonomyAdmin

tests/openedx_learning/
├── __init__.py
└── applets/
    ├── __init__.py
    └── cbe/
        ├── __init__.py
        └── test_models.py
```

### Modify

| File | Change |
|---|---|
| `test_settings.py` | add `"openedx_learning"` to `INSTALLED_APPS`, after `"openedx_catalog"` |
| `projects/dev.py` | same (assumption A5) |
| `.importlinter` | add `openedx_learning` to `root_packages`; add it as the top layer of `src_layering`; update the now-stale "Content is currently the highest-level thing in this repo" comment |

---

## 6. Steps

### Step 1 — package skeleton

Create the directory tree above with empty `__init__.py` files and an empty `py.typed`.
Every module needs a module docstring — `pydocstyle` runs over `src` in the quality gate.

### Step 2 — `apps.py`

One `AppConfig` for the whole app. Individual applets do not get their own; that is the
ticket's explicit instruction and matches `openedx_content`.

```python
"""
App Config for our umbrella openedx_learning app.
"""
from django.apps import AppConfig


class LearningConfig(AppConfig):
    """
    Initialization for all applets must happen in here.
    """

    name = "openedx_learning"
    verbose_name = "Open edX Core > Learning"
    default_auto_field = "django.db.models.BigAutoField"
    label = "openedx_learning"
```

No `ready()` — there are no signal handlers or registrations yet. `verbose_name` follows
the `"Open edX Core > X"` pattern used by Content, Tagging, and Catalog.

### Step 3 — `applets/cbe/models.py`

```python
"""
Models for Competency-Based Education (CBE).
"""
from django.db import models
from django.utils.translation import gettext_lazy as _

from openedx_tagging.models import Taxonomy

__all__ = [
    "CompetencyTaxonomy",
]


class CompetencyTaxonomy(Taxonomy):
    """
    Marks a Taxonomy as competency-enabled, so CBE features apply to its tags.

    ... (see step 3 notes for the full docstring contract)

    .. no_pii:
    """

    taxonomy_overrides_org = models.BooleanField(
        default=False,
        help_text=_(
            "When both an organization-scoped and a taxonomy-scoped rule profile "
            "could apply to a criterion, this decides which one is assigned: false "
            "assigns the organization's, true assigns this taxonomy's."
        ),
    )

    class Meta:
        verbose_name = "Competency Taxonomy"
        verbose_name_plural = "Competency Taxonomies"
```

Points that are easy to get wrong:

- **No `taxonomy_ptr` declaration.** MTI creates it. Declaring it by hand is the mistake
  the ticket and ADR-0002 both warn about.
- **No `proxy = True`.** MTI is what ADR-0002 Decision 1 requires and a proxy cannot do
  the job — no table, no column, no `competencytaxonomy` accessor. Mentioned only because
  the four neighbouring subclasses in `src/openedx_tagging/models/system_defined.py` are
  all proxies and there is no MTI example in the repo to pattern-match against.
- **No `related_name` and no explicit `parent_link`**, so the reverse accessor stays
  `taxonomy.competencytaxonomy` (see C4).
- **No `HistoricalRecords()`** (ADR-0003 Decision 2).
- `verbose_name_plural` is set because MTI children do not inherit their parent's `Meta`;
  without it, Django admin says "Competency taxonomys". It adds no column, so the
  "no columns beyond the ADR" AC is unaffected.
- `.. no_pii:` goes inside the class docstring, where `code_annotations` finds it.
- The docstring should state the *contract* per ADR-0002 Decision 1 — what being listed
  in this table means (shown in competency criteria and progress views, constrained
  associated objects) versus not — not the implementation.

### Step 4 — `applets/cbe/admin.py`

Minimal registration, matching `CollectionAdmin`'s shape in
`src/openedx_content/applets/collections/admin.py`:

```python
"""
Django Admin pages for CBE models.
"""
from django.contrib import admin

from .models import CompetencyTaxonomy


class CompetencyTaxonomyAdmin(admin.ModelAdmin):
    """
    The CompetencyTaxonomy model admin.
    """
    list_display = ["name", "export_id", "enabled", "taxonomy_overrides_org"]
    list_filter = ["enabled", "taxonomy_overrides_org"]


admin.site.register(CompetencyTaxonomy, CompetencyTaxonomyAdmin)
```

`name`, `export_id`, and `enabled` come from the parent `Taxonomy` and are available on
the child through MTI.

### Step 5 — umbrella aggregators

Three one-line modules, each with a docstring, copied in spirit from `openedx_content`:

- `models.py` — `from .applets.cbe.models import *` (with the
  `# pylint: disable=wildcard-import` comment the existing file carries). Without this,
  Django registers no models for the app.
- `admin.py` — `from .applets.cbe.admin import *`. Without this,
  `django.contrib.admin` autodiscovery never imports the applet's admin module.
- `models_api.py` — `from .models import CompetencyTaxonomy`, the stable import point for
  downstream consumers (openedx-platform will need the class to *create* competency
  taxonomies, even though ADR-0013's read-side check only needs the relation name).

### Step 5b — make the ADR-0013 relation name an explicit contract

ADR-0013 has openedx-platform detect a competency taxonomy by checking for the related
child row. Left as-is, that means the string `"competencytaxonomy"` — a name Django
generates for us from our class name — gets hardcoded in another repo, where renaming our
model or declaring the parent link by hand would break Studio with **nothing failing in
this repo**. Encapsulate it instead, so the name is written down once, in the app that
owns the relation.

`src/openedx_learning/applets/cbe/api.py`:

```python
"""
Public API for Competency-Based Education (CBE).
"""
from __future__ import annotations

from django.db.models import QuerySet

from openedx_tagging.models import Taxonomy

__all__ = [
    "is_competency_taxonomy",
    "select_competency_taxonomies",
]

# The accessor Django generates for the multi-table-inheritance link from Taxonomy to
# CompetencyTaxonomy. Deliberately private: callers use the functions below rather than
# spelling this out, so a model rename is a one-line change here and nowhere else.
_COMPETENCY_TAXONOMY_RELATION = "competencytaxonomy"


def is_competency_taxonomy(taxonomy: Taxonomy) -> bool:
    """
    Return True if ``taxonomy`` is competency-enabled, i.e. has a CompetencyTaxonomy row.

    Costs one query per call unless ``taxonomy`` came from a queryset passed through
    :func:`select_competency_taxonomies`.
    """
    return hasattr(taxonomy, _COMPETENCY_TAXONOMY_RELATION)


def select_competency_taxonomies(taxonomies: QuerySet[Taxonomy]) -> QuerySet[Taxonomy]:
    """
    Return ``taxonomies`` with each CompetencyTaxonomy row joined in.

    Pair this with :func:`is_competency_taxonomy` when checking more than one taxonomy,
    so the check costs no additional query per row.
    """
    return taxonomies.select_related(_COMPETENCY_TAXONOMY_RELATION)
```

`src/openedx_learning/api.py` re-exports it, matching `openedx_content/api.py`:

```python
"""
This is the public API for learning-domain features in Open edX Core.
"""
# This wildcard import is okay because the applet api module declares __all__.
# pylint: disable=wildcard-import
from .applets.cbe.api import *
```

openedx-platform then never types the relation name:

```python
from openedx_learning.api import is_competency_taxonomy, select_competency_taxonomies

queryset = select_competency_taxonomies(Taxonomy.objects.all())

def get_taxonomy_type(self, taxonomy):
    return "competency" if is_competency_taxonomy(taxonomy) else "tags"
```

Notes:

- The two functions ship **together on purpose**. `hasattr` without `select_related` is
  exactly the N+1 that ADR-0013 flagged as a risk; putting the fix next to the check makes
  it discoverable rather than a footnote in a doc.
- `_COMPETENCY_TAXONOMY_RELATION` stays private. Exporting the constant would just invite
  callers to spell the string themselves again, which is the thing we are removing.
- **Alternatives considered.** (a) Export only the constant, not the functions: weaker,
  since platform still reimplements the check and the N+1 pairing, but it is strictly a
  data export and so is the safest fallback if the ADR-0013 author objects to C7.
  (b) Derive the name at runtime from `CompetencyTaxonomy._meta.pk.remote_field.get_accessor_name()`:
  removes the last literal but reaches into Django internals for a name that is stable
  anyway — not worth it. (c) Declare the parent link by hand with an explicit
  `related_name`: pins the name in our source but does nothing for platform, and directly
  contradicts ADR-0002 and this ticket's "do not declare `taxonomy_ptr_id` manually".
- This is **beyond #640's stated ACs**. The ticket lists no API surface. It does not
  contradict the ticket either — "Out of scope" names REST API and UI work, not a Python
  API. Added at the user's direction; flagged here so a reviewer knows it was deliberate.

### Step 6 — register the app

Add `"openedx_learning"` to `INSTALLED_APPS` in both `test_settings.py` and
`projects/dev.py`, after `"openedx_catalog"`, under the existing "Our own apps" comment.
Ordering relative to `openedx_tagging` does not matter to Django; the migration
dependency handles table creation order.

### Step 7 — migration

```
python manage.py makemigrations openedx_learning
```

Then **read** the generated file rather than trusting it. It should be a single
`CreateModel` with exactly two fields — the auto-created `taxonomy_ptr` one-to-one and
`taxonomy_overrides_org` — plus `bases=('oel_tagging.taxonomy',)`, and a dependency on
the current leaf migration of `oel_tagging`. If it contains anything else, something in
step 3 is wrong. Do not hand-edit the dependency; let the autodetector compute it, since
`oel_tagging` has a squashed migration and two `0006_*` files, which makes hand-picking a
leaf error-prone.

### Step 8 — `.importlinter`

```ini
[importlinter]
root_packages =
    openedx_learning
    openedx_content
    openedx_tagging
    openedx_django_lib
    openedx_core

[importlinter:contract:src_layering]
name = "top-level source folders are layered correctly"
type = layers
layers =
    # Learning-domain features (currently CBE; Learning Pathways to follow).
    # May build on content and tagging. Nothing below may import it — in
    # particular, openedx_tagging must never know that CBE exists.
    openedx_learning

    # Content: authoring-side models and APIs.
    openedx_content

    # Tagging is very simple & fundamental. Should probably not depend on any other Django apps.
    openedx_tagging
    ...
```

The existing comment on `openedx_content` ("Content is currently the highest-level thing
in this repo. Over time, we may add apps 'above' or 'below' this") becomes false with this
change and must be rewritten, not left in place.

### Step 9 — tests

`tests/openedx_learning/applets/cbe/test_models.py`, following the style of
`tests/openedx_catalog/test_models.py` (pytest, `pytestmark = pytest.mark.django_db`).
Cover the things that would actually break:

1. Creating a `CompetencyTaxonomy` writes both rows, and the parent is a real `Taxonomy`
   row. `Taxonomy.export_id` is required and unique and `name` is required, so every
   fixture must supply both.
2. `taxonomy_overrides_org` defaults to `False`.
3. The MTI relationship works in both directions — `competency_taxonomy.name` reads the
   parent's field, and `Taxonomy.objects.get(...).competencytaxonomy` returns the child.
4. A plain `Taxonomy` raises `Taxonomy.competencytaxonomy.RelatedObjectDoesNotExist`.
5. Deleting the parent `Taxonomy` removes the `CompetencyTaxonomy` row (ADR-0002
   Decision 1 lifecycle). Deleting the child removes the parent row too.

Plus, in `test_api.py`, the ADR-0013 contract via the step 5b functions rather than the
raw accessor — these are what stop a model rename from silently breaking Studio:

6. `is_competency_taxonomy()` is True for a competency taxonomy, False for a plain one.
7. `is_competency_taxonomy()` also returns True when handed a `CompetencyTaxonomy`
   instance directly, not just a parent `Taxonomy` fetched from the DB. Worth an explicit
   assertion: the child class inherits the reverse descriptor from its parent, so this
   should hold, but it is the kind of thing that is cheaper to pin than to reason about.
8. `select_competency_taxonomies()` makes `is_competency_taxonomy()` free — assert with
   `django_assert_num_queries` that iterating N taxonomies costs one query, not N+1.
   This is the regression test for ADR-0013's stated N+1 concern.

There is no validation logic in this ticket to test, because there is none in the model —
everything above is either an ADR lifecycle rule or the ADR-0013 contract.

---

## 7. Verification

Run these before calling it done. Per CLAUDE.md, run the linters directly rather than
`make validate`, and pytest without coverage on just the new tests.

```bash
source ~/.virtualenvs/tutor/bin/activate

# migration is complete and nothing else drifted
python manage.py makemigrations --check --dry-run

# the new tests
pytest tests/openedx_learning -p no:cacheprovider --no-cov

# the layering rule actually passes, without loosening it
lint-imports

# PII coverage
code_annotations django_find_annotations --config_file .pii_annotations.yml --lint --report --coverage

# type check (this is the one that needs projects/dev.py to be updated)
mypy

# sanity: the app boots and the table is created from scratch
python manage.py migrate --run-syncdb --noinput   # against the sqlite test settings
```

**Environment note:** the `~/.virtualenvs/tutor` venv has `pytest`, `mypy`,
`lint-imports`, `code_annotations`, and `doc8`, but **not** `pylint`, `pycodestyle`,
`pydocstyle`, or `isort`. Those four need `pip install -r requirements/quality.txt` (or
`tox -e quality`) before the style half of the quality gate can be run locally. Worth
doing, since `pydocstyle` over `src` is what will catch a missing module docstring in one
of the eight new `__init__.py` files.

---

## 8. Acceptance criteria traceability

| AC | Where it is satisfied |
|---|---|
| MTI, not a `taxonomy_type` column; `taxonomy_ptr_id` is PK and FK | Step 3 — by subclassing `Taxonomy` and *not* declaring the pointer. Verified by test 3. |
| `django-simple-history` not applied to `oel_tagging_tag`, `oel_tagging_taxonomy`, `CompetencyTaxonomy` | Step 3 — no `HistoricalRecords()`; no changes to `openedx_tagging` at all. `simple_history` is not even in `INSTALLED_APPS`. |
| No columns not defined in the ADRs | Step 3 — exactly `taxonomy_ptr` (implicit) and `taxonomy_overrides_org`, which are ADR-0002 Decision 1's two columns. Reviewed against the generated migration in step 7. |
| All FK relationships match the ADRs | Step 3 — the only FK is the implicit parent link to `oel_tagging_taxonomy.id`. |
| App exists at `src/openedx_learning/applets/cbe/`, single `AppConfig`, registered in `test_settings.py` | Steps 1, 2, 6 |
| `.importlinter` updated, `lint-imports` passes, rules not loosened | Step 8 + verification |
| `0001_initial.py` creates the table and applies cleanly against an empty DB | Step 7 + `migrate --run-syncdb` in verification |
| `CompetencyTaxonomy` annotated `.. no_pii:` | Step 3 + `code_annotations` in verification |
| No ADR-0002 Decision 5 index lands here | Correct — none of the ten target `CompetencyTaxonomy`. Nothing to do; stated here so a reviewer does not read it as an omission. |

---

## 9. Downstream: what edx-platform needs (not in this ticket)

#640's ACs cannot cover this — it is a different repo — but the app is **inert in a real
deployment** until edx-platform registers it, so this needs a follow-up platform PR. All
four items below were verified against the local `../edx-platform` checkout.

| # | Change | File | Why |
|---|---|---|---|
| 1 | Add `"openedx_learning"` to `INSTALLED_APPS` | `lms/envs/common.py` (~2114) and `cms/envs/common.py` (~902), next to `"openedx_content"` | Without it the model is never registered and no table is created |
| 2 | Add `openedx_learning.CompetencyTaxonomy:` / `".. no_pii:": "No PII"` | `.annotation_safe_list.yml` | edx-platform's `.pii_annotations.yml` uses `source_path: ./`, so it never reads docstrings inside installed site-packages. Our inline annotation does **not** satisfy it. Verified: `openedx_content.PublishableEntity` has an inline `.. no_pii:` in openedx-core and is still safelisted there; 30 openedx-core models are listed for this reason. Miss it and platform's `pii_check` drops below its 100% target. |
| 3 | Bump the `openedx-core` pin | `requirements/edx/kernel.in`, `requirements/edx/base.txt` | **Ordering constraint:** openedx-core must merge and release *before* platform registers the app, or `INSTALLED_APPS` names an uninstalled module and every management command fails. (The local checkout currently pins a git branch, `@braden/remove-system-defined`.) |
| 4 | *Recommended:* add `"openedx_learning"` to the `isolated_apps` contract | `pyproject.toml` | That contract already lists `openedx_catalog` with `allowed_modules = ["api", "models_api", "data", "tests"]`. Adding ours makes "platform may only import `openedx_learning.api`" CI-enforced, so the ADR-0013 relation name encapsulated in step 5b cannot leak back into platform code. |

Migrations need no platform-side code: `manage.py lms migrate` / `tutor dev do init` picks
up the new app's migration automatically once it is in `INSTALLED_APPS`.

## 10. Notes handed forward

- **#641 will need `"simple_history"` added to `INSTALLED_APPS`** in both
  `test_settings.py` and `projects/dev.py`. It is pinned in requirements (`3.13.0`) but
  not currently installed as an app, because nothing uses it yet.
- **#641 and #642 must put their migrations in `src/openedx_learning/migrations/`**, not
  under the applet. Their ticket text has the same wrong path as #640's (C1).
- **#640's Open Q2 is answerable now** and should be closed on the ticket: the field is
  on `main`.
- **ADR-0013 was accepted after this ticket family was written** and depends on the
  default MTI accessor name established here. Step 5b turns that from an implicit
  convention into an explicit two-function contract, which needs the ADR-0013 amendment
  described in C7. **This is the open item that needs someone else's sign-off** — the
  amendment should land with, or just before, this ticket, and openedx-platform's
  serializer work should call `openedx_learning.api` rather than the raw accessor.
