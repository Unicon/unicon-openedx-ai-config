# [BE] Build endpoint for creating a Competency Criteria Group

GitHub: https://github.com/openedx/openedx-core/issues/664 (#664, CLOSED)
Cached: 2026-09-21

## Use Case

As a Platform Administrator, I want to create a named Competency Criteria Group scoped to a specific competency — either as a root group or nested under an existing group for that same competency — so that I have a container in place to organize the Competency Criteria I'll attach next.

## Acceptance Criteria

These scenarios are verifiable via Postman.

```
Scenario: Create a root Competency Criteria Group for a competency
  Given a valid competency (a tag in a Competency Taxonomy) exists
  And the requesting user has can_change_taxonomy permission on that taxonomy
  When a POST request is sent to the create-group endpoint with a valid "name" and "logic_operator" for that competency, no "course_id", and no "parent"
  Then the response returns status code 201
  And the response body includes the new group's "id", "oel_tagging_tag_id" matching the competency, "name", "logic_operator", "course_id" as null, and "parent" as null

Scenario: Create a course-scoped Competency Criteria Group
  Given a valid competency exists
  When a POST request is sent to the create-group endpoint with a valid "name", "logic_operator", and a "course_id"
  Then the response returns status code 201
  And the response body's "course_id" matches the supplied value

Scenario: Create a nested child group under an existing parent
  Given a Competency Criteria Group already exists for a competency
  When a POST request is sent to the create-group endpoint for that same competency, with "parent" set to the existing group's id
  Then the response returns status code 201
  And the response body's "parent" matches the supplied id

Scenario: Reject a parent group that belongs to a different competency
  Given a Competency Criteria Group exists for competency A
  When a POST request is sent to the create-group endpoint for competency B, with "parent" set to competency A's group id
  Then the response returns status code 400
  And the response body identifies the parent/competency mismatch
  # Containment validation: a supplied parent must belong to the same competency (oel_tagging_tag_id) as the group being created. Not explicitly stated in ADR 0002, but the obvious data-integrity requirement once nesting is in scope — see Open Questions.

Scenario: Reject creation with a missing required field
  Given a POST request to the create-group endpoint omits "name" or "logic_operator"
  When the request is processed
  Then the response returns status code 400
  And the response body identifies the missing field by name

Scenario: Reject creation for a competency that does not exist
  Given the referenced competency tag id does not exist, or exists but is not a tag within a Competency Taxonomy
  When a POST request is sent to the create-group endpoint referencing that id
  Then the response returns status code 404

Scenario: Reject creation without permission
  Given the requesting user does not have can_change_taxonomy permission on the referenced competency's taxonomy
  When a POST request is sent to the create-group endpoint
  Then the response returns status code 403
```

## Description

**Current state**

No endpoint exists today to create a `CompetencyCriteriaGroup`. Per ADR 0002, the model is an internal node in a competency's criteria tree, with columns `id`, `parent_id` (nullable self-FK; null \= root), `oel_tagging_tag_id` (FK to the competency tag), `course_id` (nullable FK to a course run), `name`, `ordering`, and `logic_operator` (`AND`/`OR`/null). No `unique_together` constraint is specified — only a plain index on `(oel_tagging_tag_id, course_id)` — so nothing in the model itself limits a competency to one group.

**Requested change**

A new endpoint, scoped under the competency (tag) it belongs to, that creates a `CompetencyCriteriaGroup`. It accepts:

- `name` (required)  
- `logic_operator` (required, `AND` or `OR`, default to `OR`)  
- `course_id` (optional — omit for a competency-wide, course-agnostic group)  
- `parent` (optional — omit to create a root group; supply an existing group's id to nest this one under it)

The competency itself is identified by the URL, not the request body (`POST /competencies/<tag_id>/criteria-groups/`), mirroring this repo's existing nested-resource convention for tags-under-taxonomy.

Permission gating reuses this repo's existing taxonomy-level permission machinery (`can_change_taxonomy`, scoped to the taxonomy that owns the competency tag) rather than introducing a new CBE-specific permission class because competency taxonomies are instance-wide and admin-managed.

**Explicitly out of scope**

- Creating or attaching `CompetencyCriteria` rows within the group (ticket 5.6).  
- Listing or retrieving groups (5.7).  
- Updating or deleting a group (5.9).  
- Any UI (5.10/\#648).  
- A dedicated CBE-specific permission class — reusing existing taxonomy permission gating is the confirmed approach for this ticket.  
- An org-scoping wrapper layer analogous to `content_tagging`'s `TaxonomyOrgView`/`ObjectTagOrgView`. Not needed while Competency Taxonomies stay instance-wide, admin-managed per MVP scope; revisit only if/when org-scoped competency taxonomies are introduced.  
- Wiring `openedx_learning` into `lms/urls.py` or any LMS-facing endpoint. `content_tagging` itself is CMS-only; this ticket mirrors that. `openedx_learning` still needs an `INSTALLED_APPS` entry in both LMS and CMS settings (below), since LMS and CMS share one database and need matching app registries for migrations, but no LMS route is added here.

<details>
<summary>Open Questions</summary>

- **\[non-blocking, owner: implementer\]** ADR 0002 doesn't explicitly state that a supplied `parent` must belong to the same competency (and course scope) as the group being created. This ticket assumes yes (see the rejected-mismatch scenario above) as the obvious data-integrity requirement now that nested-group creation is in scope — confirm this against \#613's actual model constraints, and decide whether `course_id` must also match the parent's (or be null-compatible) at the same time.  
- **\[non-blocking, owner: implementer\]** Confirm \#613's landed model doesn't add a `unique_together` or other constraint beyond the plain `(oel_tagging_tag_id, course_id)` index this ticket assumes — multiplicity (multiple groups per competency/course) is intentionally unconstrained per the ADR's current text and the fact that a competency may have several groups.  
- **\[non-blocking, owner: implementer\]** URL prefix for the CMS-side include (`api/cbe/rest_api/` proposed below, mirroring `content_tagging`'s `api/content_tagging/`) is this ticket's proposal, not a confirmed platform convention for CBE specifically — confirm before implementation if a different prefix is preferred.

</details>
<details>
<summary>Context</summary>

- ADR 0002 (`docs/openedx_learning/decisions/0002-competency-criteria-model.rst:63-107`): canonical `CompetencyCriteriaGroup` field list and tree semantics. Its "no empty groups persisted" rule (line 104\) explicitly carves out that "authoring flows may temporarily create empty groups while editing" — so this endpoint creating a group with zero criteria is fine; that rule governs the evaluation-time tree, not the moment of creation.  
- ADR 0001 (`docs/openedx_learning/decisions/0001-competency-criteria-location.rst`): places CBE code at `src/openedx_learning/applets/cbe/`; explicitly rejects putting CBE code inside `openedx_tagging`, since that app must stay a standalone library with no Open edX-specific dependencies.  
- ADR 0003 (`docs/openedx_learning/decisions/0003-competency-criteria-versioning.rst`): `CompetencyCriteriaGroup` gets `django-simple-history` audit tracking, not draft/publish semantics — create/update/delete are direct, immediately-effective operations.  
- \#613 (5.1): the model/migration this ticket depends on.  
- 5.6: creates `CompetencyCriteria` rows inside a group once one exists; has its own open validation-scope question (containment/scope rules), not resolved here.  
- 5.7: GET endpoint for groups \+ criteria.  
- 5.10/\#648: the UI shell that will eventually call this endpoint.  
- `src/openedx_tagging/rules.py:43-50` (`can_change_taxonomy`) and `src/openedx_tagging/rest_api/v1/permissions.py:10-22` (`TaxonomyObjectPermissions`): the reused permission precedent.  
- `src/openedx_tagging/rest_api/v1/views.py:659` (`TaxonomyTagsView`) and `src/openedx_tagging/rest_api/v1/urls.py:17-21`: the nested-child-resource precedent (`taxonomies/<pk>/tags/`) this ticket's URL design mirrors.  
- `src/openedx_tagging/rest_api/v1/views.py:262` (`TaxonomyView.perform_create` calling `create_taxonomy(...)`): the precedent for calling a public `api.py` function from the view rather than `serializer.save()` directly.

**openedx-platform** (`openedx/core/djangoapps/content_tagging/rest_api/v1/urls.py:6-16`, `content_tagging/rest_api/urls.py:9`, `content_tagging/urls.py:9`): the wiring precedent for how a REST API in this repo becomes reachable from Studio. `content_tagging` selectively wraps specific `openedx_tagging` views in org-scoped subclasses and registers those on its own router. Included at `cms/urls.py:361`: `path('api/content_tagging/', include(('openedx.core.djangoapps.content_tagging.urls', 'content_tagging')))`. `openedx_tagging` and `content_tagging` are both listed in `INSTALLED_APPS` in `cms/envs/common.py:846-847` and `lms/envs/common.py:2022-2023`. This ticket's platform-side wiring is thinner than that precedent, since CBE needs no org-scoping subclassing for MVP — see Technical Notes.
</details>
<details>
<summary>Technical Notes</summary>

### Files to Create

| File | Purpose |
| :---- | :---- |
| `src/openedx_learning/applets/cbe/rest_api/__init__.py` | package init, mirrors `src/openedx_tagging/rest_api/__init__.py` |
| `src/openedx_learning/applets/cbe/rest_api/urls.py` | includes v1 urls, mirrors `src/openedx_tagging/rest_api/urls.py` |
| `src/openedx_learning/applets/cbe/rest_api/v1/__init__.py` | package init |
| `src/openedx_learning/applets/cbe/rest_api/v1/urls.py` | registers `competencies/<int:competency_tag_id>/criteria-groups/` |
| `src/openedx_learning/applets/cbe/rest_api/v1/serializers.py` | `CompetencyCriteriaGroupSerializer` |
| `src/openedx_learning/applets/cbe/rest_api/v1/views.py` | `CompetencyCriteriaGroupCreateView(generics.CreateAPIView)` |
| `src/openedx_learning/applets/cbe/rest_api/v1/tests/test_views.py` | View/permission/response-shape tests, including nested-parent and mismatched-parent cases |

*Conditional — check first whether \#613 already added these:*

| File | Purpose |
| :---- | :---- |
| `src/openedx_learning/urls.py` | top-level app urls.py |
| `src/openedx_learning/applets/cbe/api.py` | public API module |

### Files to Modify

| File | Repo | Nature of modification |
| :---- | :---- | :---- |
| `projects/urls.py` | openedx-core | add `path("cbe/rest_api/", include("openedx_learning.urls"))`, mirroring the existing tagging entry — for openedx-core's own local dev/test harness only |
| `src/openedx_learning/applets/cbe/api.py` | openedx-core | add `create_competency_criteria_group(...)` if \#613 already created this file with other functions |
| `cms/envs/common.py` | openedx-platform | add `'openedx_learning',` to `INSTALLED_APPS`, mirroring `openedx_tagging`'s entry (line \~846) |
| `lms/envs/common.py` | openedx-platform | add `'openedx_learning',` to `INSTALLED_APPS`, mirroring `openedx_tagging`'s entry (line \~2022) — needed because LMS and CMS share one database and must have matching app registries for migrations, even though no LMS route is added by this ticket |
| `cms/urls.py` | openedx-platform | add `path('api/cbe/rest_api/', include('openedx_learning.urls'))` near the existing `content_tagging` entry (line 361\) — a direct include, not a wrapper app; see Implementation Notes for why |

### Implementation Notes

Build a single-purpose `CreateAPIView` at `POST /cbe/rest_api/v1/competencies/<int:competency_tag_id>/criteria-groups/` — not a full `ModelViewSet`; this ticket asks for creation only. The competency is identified by `oel_tagging_tag.id` in the URL, not accepted in the POST body.

`CompetencyCriteriaGroupSerializer` is a `ModelSerializer` over `CompetencyCriteriaGroup` with writable fields `name`, `logic_operator` (both required), `course_id` and `parent` (both optional). It does not expose `oel_tagging_tag_id` as writable — that comes from the URL. In `perform_create`, resolve the competency tag from the URL kwarg, validate it belongs to a `CompetencyTaxonomy`, validate that a supplied `parent` belongs to the same competency (and reconcile `course_id` against the parent's, per the Open Question above), then call a public `create_competency_criteria_group()` function in `applets/cbe/api.py` — mirroring `TaxonomyView.perform_create` calling `create_taxonomy()` rather than saving the serializer inline.

Permission class: reuse `TaxonomyObjectPermissions` (or an equivalent thin wrapper around the existing `can_change_taxonomy` predicate), scoped to the taxonomy that owns the competency tag resolved from the URL — do not introduce a new Django model permission for this ticket.

No model, migration, or PII annotation work belongs in this ticket; it depends entirely on \#613 shipping `CompetencyCriteriaGroup` first.

**Platform wiring.** `content_tagging` wraps `openedx_tagging`'s views in org-scoped subclasses (`TaxonomyOrgView`, `ObjectTagOrgView`) because regular taxonomies/tags in Studio are org-scoped. Competency Taxonomies are explicitly instance-wide and admin-managed for MVP (this ticket already reuses the raw `can_change_taxonomy` predicate, not an org-aware one), so no equivalent wrapper app or view subclassing is needed here: `cms/urls.py` can `include()` `openedx_learning`'s own urls module directly, the same module this ticket already builds for `projects/urls.py`. If org-scoped competency taxonomies are introduced later, a `content_tagging`\-style wrapper can be added at that point without restructuring this endpoint.

Test strategy: unit tests for `create_competency_criteria_group()` (root creation, course-scoped creation, nested creation, mismatched-parent rejection) and DRF integration tests for the view (201 on valid payload, 400 on missing required field or mismatched parent, 403 for a user without `can_change_taxonomy`, 404 for an unknown `competency_tag_id`). Add one integration test in `openedx-platform` confirming the CMS-side URL (`api/cbe/rest_api/v1/...`) reaches the same view, per the new Acceptance Criteria scenario above.

### Example Resolution Prompt

Implement ticket 5.5: a POST-only endpoint to create a `CompetencyCriteriaGroup` scoped to a specific competency, in `openedx-core`, plus the `openedx-platform` wiring so Studio can reach it. Assume `#613` has already landed `src/openedx_learning/applets/cbe/models.py` with a `CompetencyCriteriaGroup` model matching ADR `docs/openedx_learning/decisions/0002-competency-criteria-model.rst:78-84` (fields: `id`, `parent` self-FK nullable, `oel_tagging_tag` FK to `Tag`, `course_id` nullable FK to `openedx_catalog.CourseRun`, `name`, `ordering`, `logic_operator` choices AND/OR/null), and that `src/openedx_learning/` is already registered in `INSTALLED_APPS` and `.importlinter` within `openedx-core`. If any of that scaffolding is missing, add only the minimal piece needed to route requests.

Build, in `openedx-core`:

1. `src/openedx_learning/applets/cbe/rest_api/v1/serializers.py`: `CompetencyCriteriaGroupSerializer(serializers.ModelSerializer)` over `CompetencyCriteriaGroup`, with `name` and `logic_operator` required, `course_id` and `parent` optional. Do NOT include the competency tag FK as a writable field.  
2. `src/openedx_learning/applets/cbe/rest_api/v1/views.py`: `CompetencyCriteriaGroupCreateView(generics.CreateAPIView)`. Resolve `competency_tag_id` from the URL kwarg in `perform_create`, look up the `Tag`, validate that a supplied `parent` group belongs to the same `Tag` (400 if not), and call a new `create_competency_criteria_group(competency_tag_id, **serializer.validated_data)` function in `src/openedx_learning/applets/cbe/api.py` (create this file if it doesn't exist) — do not call `serializer.save()` directly; mirror `TaxonomyView.perform_create` at `src/openedx_tagging/rest_api/v1/views.py:262`, which calls `create_taxonomy()` instead.  
3. Permission: reuse `TaxonomyObjectPermissions` (`src/openedx_tagging/rest_api/v1/permissions.py:10-22`) or an equivalent wrapper around `can_change_taxonomy` (`src/openedx_tagging/rules.py:43-50`), scoped to the taxonomy owning the resolved competency tag. Do not add a new Django model permission.  
4. `src/openedx_learning/applets/cbe/rest_api/v1/urls.py`: register `path("competencies/<int:competency_tag_id>/criteria-groups/", views.CompetencyCriteriaGroupCreateView.as_view(), name="competency-criteria-group-create")`, mirroring `src/openedx_tagging/rest_api/v1/urls.py:17-21` (`taxonomies/<str:pk>/tags/`).  
5. Wire `rest_api/urls.py` → `rest_api/v1/urls.py` → app-level `urls.py`, following `src/openedx_tagging/urls.py` and `src/openedx_tagging/rest_api/urls.py`, and add one line to `projects/urls.py`.

Then, in `openedx-platform`:

6. Add `'openedx_learning',` to `INSTALLED_APPS` in both `cms/envs/common.py` and `lms/envs/common.py`, mirroring `openedx_tagging`'s existing entries.  
7. Add `path('api/cbe/rest_api/', include('openedx_learning.urls'))` to `cms/urls.py` near the existing `content_tagging` entry (line 361). Do not add an LMS urls.py entry, and do not build a `content_tagging`\-style wrapper app: CBE needs no org-scoping for MVP, so a direct include of `openedx_learning`'s own urls module is sufficient.

Return 201 with the created group's representation on success; 400 if `name`/`logic_operator` is missing or `parent` belongs to a different competency; 404 if `competency_tag_id` doesn't resolve to a `Tag` under a `CompetencyTaxonomy`; 403 if the caller lacks `can_change_taxonomy` on that taxonomy. Do not implement GET/list/update/delete. Confirm the endpoint is reachable via the `openedx-platform` CMS URL, not just `openedx-core`'s own dev harness.  

**Blocked by:** \#613 (5.1, the CBE competency-criteria data model). Confirmed against the `openedx-core` checkout: `src/openedx_learning/` does not exist on disk, and there is zero code (models, migrations, serializers, viewsets) for `CompetencyCriteriaGroup` anywhere in the repository or its history. The model exists only as approved design in ADR 0002 (`docs/openedx_learning/decisions/0002-competency-criteria-model.rst:63-107`). This ticket is confirmed unblocked for **writing** (per the 2026-07-14 team meeting), but its implementation is blocked until \#613 lands the model and migration.

Repo: `openedx-core` (backend endpoint) plus `openedx-platform` (CMS-side wiring so Studio can actually reach it).

</details>
