# openedx/openedx-core PR #847: Alezconsultant/665 criterion endpoint on 846

Author: alezconsultant. Base: main. Head branch: alezconsultant/665-criterion-endpoint-on-846 (fork alezconsultant/openedx-core). Created 2026-10-02T15:03:13Z. Body as of 2026-10-02T15:03:13Z.

---

## Description

Stacked on #846 ; review only the last commit

Adds the create-criterion endpoint from openedx/openedx-core#665: `POST
/api/cbe/v1/competencies/<int:tag_id>/criteria/`, letting a course author associate a
gradeable subsection with a competency, either by attaching it into an existing leaf
`CompetencyCriteriaGroup` or by deriving/creating whatever part of the root/course-level/leaf
group hierarchy doesn't yet exist for this competency and course.

## Changes

- `src/openedx_learning/migrations/0004_criteria_group_unique_constraints.py` (new): two
  partial `UniqueConstraint`s on `CompetencyCriteriaGroup` — one root per `tag`
  (`condition=Q(parent__isnull=True)`), one course-level group per `(tag, course, parent)`
  (`condition=Q(course__isnull=False)`). Matching constraints added to
  `CompetencyCriteriaGroup.Meta` in `models/criteria.py`.
- `src/openedx_learning/applets/cbe/api.py`: adds `resolve_competency_tag()`,
  `resolve_or_create_leaf_group()`, `resolve_supplied_leaf_group()`,
  `create_competency_criterion()`, and `associate_competency_criterion()` (the single public
  entry point this ticket's view calls).
- `src/openedx_learning/applets/cbe/rest_api/v1/serializers.py`: adds
  `CompetencyCriterionSerializer` alongside the existing `CompetencyRuleProfileSerializer`.
  `object_id`/`group_id`/`logic_operator` are plain write-only fields (none of them are
  `CompetencyCriterion` model fields); `competency_rule_profile_id`,
  `competency_criteria_group_id`, and `oel_tagging_objecttag_id` are the ticket's contracted
  JSON names, mapped via explicit `source=` to the model's actual attributes
  (`rule_profile_id`, `group_id`, `object_tag_id`).
- `src/openedx_learning/applets/cbe/rest_api/v1/views.py`: adds
  `CompetencyCriterionCreateView(generics.CreateAPIView)` alongside the existing
  `CompetencyRuleProfileView`.
- `src/openedx_learning/applets/cbe/rest_api/v1/urls.py`: adds
  `competencies/<int:tag_id>/criteria/`, a plain `path()` (not a second router
  registration — the URL carries a path parameter mid-route, so it isn't a flat
  router-friendly resource like `rule_profiles`).
- `tests/openedx_learning/applets/cbe/test_api.py`, `test_views.py`,
  `test_criteria_models.py`: unit and DRF integration tests (see Tests below); one
  pre-existing test in `test_criteria_models.py` updated to use two tags instead of one,
  since it previously created two root groups for the same tag, which the new constraint
  now correctly rejects.

## Tests

One test per scenario in #665's Acceptance Criteria (all 20): the full-hierarchy derivation
and reuse scenarios, `logic_operator` provided/defaulted, the `group_id`/`logic_operator`
mutual-exclusion rejection, every supplied-group validation rejection (non-leaf, wrong
competency, wrong course), all three duplicate-association rejections, the all-null-rule-
fields deviation above, the same-taxonomy tag-preservation scenario, every not-found/malformed
scenario, and the permission rejection. Plus unit tests for `resolve_or_create_leaf_group()`
and `resolve_supplied_leaf_group()` directly, including two tests that pre-commit a
competing row out-of-band to prove the constraint-backed `get_or_create()` fallback (standing
in for a real concurrent request), two tests proving the constraints themselves exist via a
direct `IntegrityError`, and one test proving the atomic block rolls back newly-created groups
when the final `CompetencyCriterion.objects.create()` call fails.

## Depends on

openedx-core#9 (openedx/openedx-core#773), which this branch is based on and which already
adds the CBE REST scaffolding (`openedx_learning/urls.py`, the `rest_api/` package,
`serializers.py`/`views.py`/`urls.py`) this PR extends rather than creates. That PR is itself
based on #641/#613's `CompetencyCriteriaGroup`/`CompetencyCriterion`/`CompetencyRuleProfile`
models.

## Companion PR

A one-line `openedx-platform` change (`cms/urls.py`: `path('api/cbe/',
include('openedx_learning.urls'))`, mirroring the existing `content_tagging` mount) is a
separate PR against that repo, not included here.

## Verification

- `pytest tests/openedx_learning/applets/cbe/ --no-cov`: 147 passed.
- `pylint`, `mypy`, `pycodestyle`, `isort --check-only`, `pydocstyle`: all clean on every
  changed file.
- `lint-imports`: 2 contracts kept, 0 broken.
- The underlying `make pii_check` check: 2 pre-existing, unrelated failures only
  (`openedx_content.Draft`/`PublishableEntityVersion`, confirmed via `git stash` to predate
  this branch). Both models this PR touches already carry `.. no_pii:`; the migration adds no
  new fields.
- Also verified against a live devstack running the real `openedx-platform` permission chain
  (a real `CourseStaffRole` holder granted access, an unpermitted user refused), isolated from
  an unrelated, pre-existing import failure elsewhere in that repo's `content_tagging` app —
  see the companion PR for details.

Related to openedx/openedx-core#665

Created with the help of Claude