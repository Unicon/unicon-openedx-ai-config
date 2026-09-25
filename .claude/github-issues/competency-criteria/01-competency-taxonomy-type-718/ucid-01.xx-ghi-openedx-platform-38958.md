# Register the openedx_learning app so CBE competency models are active

GitHub: https://github.com/openedx/openedx-platform/issues/38958 (#38958, CLOSED)
Cached: 2026-09-25

## Background

openedx-core is adding a new top-level Django app, `openedx_learning`, whose first applet
(`cbe`) holds the Competency-Based Education models. Its first model,
`CompetencyTaxonomy`, is a Django multi-table-inheritance subclass of `openedx_tagging`'s
`Taxonomy` that marks a taxonomy as competency-enabled.

That app is inert in a real deployment until this repo registers it: no table is created
and the model is never loaded. This issue covers the platform-side wiring.

Upstream work this depends on:

- openedx/openedx-core#613 — parent issue, the full CBE data model
- openedx/openedx-core#640 — the app foundation and `CompetencyTaxonomy` model

## What to do

**1. Register the app.** Add `"openedx_learning"` to `INSTALLED_APPS` in both
`lms/envs/common.py` and `cms/envs/common.py`, alongside the existing `"openedx_catalog"`
and `"openedx_content"` entries.

**2. Add the model to `.annotation_safe_list.yml`:**

```yaml
openedx_learning.CompetencyTaxonomy:
  ".. no_pii:": "No PII"
```

This is required *even though* the model carries an inline `.. no_pii:` annotation
upstream. This repo's `.pii_annotations.yml` sets `source_path: ./`, so the annotation
scan only reads this repo's tree and never looks inside installed site-packages. Every
openedx-core model is safelisted here for the same reason — `openedx_content.PublishableEntity`
is annotated inline upstream and still needs an entry here. Without it, `pii_check` drops
below its 100% coverage target.

**3. Bump the `openedx-core` pin** in `requirements/edx/kernel.in` and
`requirements/edx/base.txt` to a released version that contains the new app.

**4. Add `"openedx_learning"` to the `isolated_apps` import-linter contract** in
`pyproject.toml`, alongside the existing `openedx_catalog` entry. That contract limits
imports to `api`, `models_api`, `data`, and `tests`, keeping platform code off the app's
internals.

Item 4 carries more weight than usual here. Studio detects a competency taxonomy by
checking for a related `CompetencyTaxonomy` row on a `Taxonomy`, per the competency
taxonomy detection decision recorded in openedx-core. The name of that relation is a
Django-generated default, and hardcoding it in this repo would mean a rename upstream
breaks Studio with nothing failing in either repo's tests. openedx-core therefore
encapsulates it behind two public functions, and platform code should call those:

```python
from openedx_learning.api import is_competency_taxonomy, select_competency_taxonomies
```

Pair them when checking more than one taxonomy — `select_competency_taxonomies()` joins
the child rows in so `is_competency_taxonomy()` costs no extra query per row. The
import-linter contract makes using the public API mechanical rather than a convention.

## Ordering constraint

openedx/openedx-core#640 must merge and be released **before** this lands. If
`INSTALLED_APPS` names a module that is not installed, every management command fails.

## Acceptance criteria

- [ ] `openedx_learning` is in `INSTALLED_APPS` for both LMS and CMS
- [ ] `openedx_learning.CompetencyTaxonomy` is in `.annotation_safe_list.yml`, and
      `make pii_check` passes at 100% coverage
- [ ] The `openedx-core` pin resolves to a version containing the `openedx_learning` app
- [ ] `make check_migrations` passes and the app's migration applies cleanly
- [ ] `openedx_learning` is in the `isolated_apps` contract and `lint-imports` passes

## Out of scope

The REST API change that reports a `taxonomy_type` value on the taxonomy GET endpoints.
That is separate work built on top of this registration.

