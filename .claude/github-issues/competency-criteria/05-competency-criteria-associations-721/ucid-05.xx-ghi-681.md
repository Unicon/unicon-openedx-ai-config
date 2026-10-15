# [BE] GET Competency Criteria & Groups

GitHub: https://github.com/openedx/openedx-core/issues/681 (#681, OPEN)
Cached: 2026-09-21

**Blocked by** \#613 (the CBE data model), \#665 (creates the `CompetencyCriterion` rows this endpoint reads, and the field shapes it serializes), \#674 and \#675 (both explicitly assume this endpoint filters `archived=False` by default; \#675 also establishes the `competencies/<int:competency_tag_id>/criteria-groups/` URL prefix this endpoint's GET route shares), and the archived-field migration ticket (adds the `archived` column this endpoint filters on).

Repo: `openedx-core`, single-repo. No `openedx-platform` changes — this route registers inside the same `rest_api/v1/urls.py` \#665 already wired into Studio.

## Use Case

As a course author using the Manage & Apply Competencies authoring flow, I want to fetch the current `CompetencyCriteriaGroup` tree (root, course-level, and leaf groups) and the `CompetencyCriterion` leaves under it for a competency I'm managing, so that the authoring UI can render what's actually already associated — existing groups, existing criteria, which subsections are already tagged — from persisted backend state, rather than tracking or guessing at that state client-side, and so that my next write action (add or remove an association) acts against ground truth instead of a stale local copy.

## Description

This ticket adds a single GET endpoint returning every non-archived `CompetencyCriteriaGroup` and `CompetencyCriterion` for one competency, as two flat lists. It is the read-side counterpart to the write-side family already drafted: \#665 (create a criterion), \#674 (remove a criterion), and \#675 (remove a group subtree).

**Current state**

No endpoint exists today to retrieve `CompetencyCriteriaGroup` or `CompetencyCriterion` rows. \#674 and \#675 were both written assuming this endpoint filters archived rows out by default (their own lookups deliberately do not, "unlike the future read/list path"), so that expectation is a settled input to this ticket, not an open question.

**Requested change**

`GET /api/cbe/v1/competencies/<int:competency_tag_id>/criteria-groups/` returns, for a given competency: every `CompetencyCriteriaGroup` in that competency's tree with `archived=False` (root, every course-level group, every leaf, across every course at once — no `course_id` or date-window scoping parameter), and every `CompetencyCriterion` with `archived=False` under those groups. The response is two flat arrays, `groups` and `criteria`, each row carrying its own `parent_id`/`competency_criteria_group_id` for client-side reconstruction, matching this repo's existing tree-shaped GET precedent (`TaxonomyTagsView`) rather than introducing a nested/recursive serializer this codebase has never used. A competency with no criteria structure yet returns 200 with two empty arrays, not a 404\. Windowing by course-run dates and pagination for competencies with many associations are explicitly deferred to \#682, not built here — see Explicitly out of scope.

Each criterion in the `criteria` array also carries an `object_id` field: the subsection usage-key string the criterion points at, resolved from its `oel_tagging_objecttag_id` FK. A caller today can only see which `ObjectTag` row a criterion references, not what subsection that row tags; this closes that gap so a consumer can tell which subsections a competency already uses without a second, per-criterion lookup.

**Explicitly out of scope**

- Any write behavior (create, update, archive, delete) — covered by \#665, \#674, \#675.  
- Windowing by course-run date and pagination for large result sets — \#682's scope. This ticket returns the whole non-archived tree unconditionally, correct for now per ADR 0002's own note that `course_id is null` branches are expected to stay small.  
- Any convenience signal indicating whether a row can be safely removed without a warning (e.g. a `deletable` field). Not built here: Studio currently has no way to know this without attempting the delete and observing whether it archives instead. Revisit if a future ADR settles on a concrete mechanism for this.  
- An explicit audit endpoint or parameter for retrieving archived rows. Default-exclude is the behavior for MVP; no consumer has asked for archived visibility.  
- Learner progress/mastery status (`StudentCompetency*Status` tables) — this endpoint returns authoring structure only, not evaluation results.  
- Any UI.

## Acceptance Criteria

These scenarios are verifiable via Postman.

```
Scenario: Fetch a competency's minimal tree — root, one course-level group, one leaf, one criterion
  Given a competency tag_id has a root CompetencyCriteriaGroup, one course-level CompetencyCriteriaGroup under it, one leaf CompetencyCriteriaGroup under that, and one CompetencyCriterion under the leaf, none archived
  And the requesting user has view access to the taxonomy owning the competency tag
  When a GET request is sent to the criteria-groups endpoint for that tag_id
  Then the response returns status code 200
  And the response body's "groups" array includes all three groups (root, course-level, leaf), each with the correct "parent_id" linkage, and the root's "parent_id" and "course_key" both null
  And the response body's "criteria" array includes the one criterion, with "competency_criteria_group_id" matching the leaf

Scenario: Fetch returns groups and criteria across multiple courses in one response, unscoped
  Given a competency has a root group, course-level groups for both Course X and Course Y, and a leaf group with one CompetencyCriterion under each
  When a GET request is sent for that tag_id
  Then the response returns status code 200
  And the response body's "groups" array includes the root group and both course-level and leaf groups for Course X and Course Y together
  And the response body's "criteria" array includes both criteria, each carrying its "competency_criteria_group_id"

Scenario: Archived groups and criteria are excluded by default
  Given a leaf CompetencyCriteriaGroup has archived=true and a CompetencyCriterion under it has archived=true
  When a GET request is sent for the owning tag_id
  Then the response returns status code 200
  And neither the archived group's "id" nor the archived criterion's "id" appears anywhere in the response body

Scenario: Competency has no criteria structure yet
  Given tag_id is a valid Competency Taxonomy tag with no CompetencyCriteriaGroup rows at all
  When a GET request is sent for that tag_id
  Then the response returns status code 200
  And the response body's "groups" and "criteria" arrays are both empty

Scenario: Reject a tag_id that isn't a Competency Taxonomy tag
  Given the referenced tag_id does not exist, or exists but is not a tag within a CompetencyTaxonomy
  When a GET request is sent referencing that id
  Then the response returns status code 404

Scenario: Reject without permission
  Given the requesting user lacks view access to the taxonomy owning the competency tag
  When a GET request is sent to the endpoint
  Then the response returns status code 403

Scenario: CompetencyCriterion fields match the canonical shape
  Given a non-archived CompetencyCriterion exists under a returned leaf group
  When a GET request is sent for the owning tag_id
  Then the response body's matching criterion entry includes "id", "competency_criteria_group_id", "oel_tagging_objecttag_id", "object_id", "competency_rule_profile_id", "rule_type_override", and "rule_payload_override"

Scenario: object_id resolves to the criterion's tagged subsection
  Given a CompetencyCriterion points, via its oel_tagging_objecttag_id, at an ObjectTag whose object_id is a subsection usage key
  When a GET request is sent for the owning tag_id
  Then the response body's matching criterion entry's "object_id" equals that subsection usage key
```

<details>
<summary>Technical Details</summary>

**Data Structures**

```py
@dataclass
class CompetencyCriteriaTree:
    groups: list[CompetencyCriteriaGroup]     # all non-archived groups for the tag: root, course-level, leaf
    criteria: list[CompetencyCriterion]       # all non-archived criteria under those groups

class CompetencyCriteriaGroupSerializer(serializers.ModelSerializer):
    # Resolves through the group's course_id FK to the related CourseRun's course_key, per the CourseRun model's
    # own contract that only the string course key, never the integer PK, is exposed in APIs. Null-safe: DRF
    # emits null automatically when the FK itself is null, with no extra handling needed here.
    course_key = serializers.SlugRelatedField(source="course_id", slug_field="course_key", read_only=True)

    class Meta:
        model = CompetencyCriteriaGroup
        fields = ["id", "parent_id", "oel_tagging_tag_id", "course_key", "name", "ordering", "logic_operator", "archived"]

# CompetencyCriterionSerializer: extends #665/#674's version with one added field:
#   object_id = serializers.CharField(source="oel_tagging_objecttag.object_id", read_only=True)
# Every other field, including `archived`, is unchanged from #665/#674.

class CompetencyReadPermission(permissions.BasePermission):
    """has_object_permission checks rules.has_perm("oel_tagging.view_tag", request.user, tag).
    Distinct from the write-side `oel_tagging.can_tag_object`: no studio-write component,
    since a read has no target object to tag. `view_tag` delegates to `can_view_taxonomy`,
    which is permissive by design (anyone can view an enabled taxonomy)."""
```

**Logic**

1. `CompetencyCriteriaTreeView(generics.GenericAPIView).get()`: resolve the competency `Tag` from the URL's `competency_tag_id` via `get_object_or_404`; 404 if missing or not backed by a `CompetencyTaxonomy` — same resolution and 404 semantics as \#665's step 1\.  
2. Call `self.check_object_permissions(request, tag)` against `CompetencyReadPermission`; 403 on failure. DRF's default exception handling already returns clean 404/403 responses for `Http404`/`PermissionDenied` with no custom mixin needed.  
3. Call `api.get_competency_criteria_tree(tag.id)`:  
   - `CompetencyCriteriaGroup.objects.filter(oel_tagging_tag_id=tag_id, archived=False).select_related("course_id")` — one query returns every level (root, course-level, leaf), since a group belongs to exactly one competency regardless of depth. The `select_related("course_id")` is required once the serializer resolves `course_key` through this FK (see Data Structures): without it, serializing N groups issues N extra queries against `CourseRun`, one per group, instead of the single join this line adds.  
   - `CompetencyCriterion.objects.filter(competency_criteria_group__in=groups, archived=False)`.  
   - Return `CompetencyCriteriaTree(groups=groups, criteria=criteria)`. An empty tree (tag exists, nothing authored yet) is a valid 200 with two empty lists, not a 404 — 404 is reserved for tag resolution failure only.  
4. Serialize both lists with `CompetencyCriteriaGroupSerializer`/`CompetencyCriterionSerializer`, return `Response({"groups": [...], "criteria": [...]}, status=200)`. No pagination in this ticket; \#682 owns that. Fetch criteria with `select_related("oel_tagging_objecttag")` so serializing each row's `object_id` costs no extra query per criterion.

Public-API impact: one additive function in `applets/cbe/api.py`, and one added field on the `CompetencyCriterionSerializer` \#665/\#674 already created. No breaking changes; greenfield. No migration.

Test strategy: unit tests for `get_competency_criteria_tree` (empty tree, root+course-level+leaf together, archived rows excluded, multiple courses under one root) plus DRF integration tests (200 with full tree, 200 empty, 404 unknown/non-competency tag, 403 without view access, a criterion's `object_id` resolves to its tagged subsection).

### Example Resolution Prompt

Implement `GET /api/cbe/v1/competencies/<int:competency_tag_id>/criteria-groups/` per the Data Structures and Logic above. Assume \#613, \#665, \#674, \#675, and the archived-field migration have all landed: `CompetencyCriteriaGroup`/`CompetencyCriterion` both carry `archived`, and `rest_api/v1/{views,serializers,urls}.py` / `applets/cbe/api.py` already exist with \#665's `CompetencyCriterionSerializer` and \#675's `criteria-groups/<int:group_id>/` DELETE route. Add `get_competency_criteria_tree(tag_id: int) -> CompetencyCriteriaTree` to `api.py` following the two-query approach exactly — return flat filtered lists, matching this repo's existing `TaxonomyTagsView` idiom, not a nested/recursive serializer. Add `CompetencyCriteriaGroupSerializer` to `serializers.py` (this ticket is the first to create it), and add an `object_id` field to the existing `CompetencyCriterionSerializer`, sourced from `oel_tagging_objecttag.object_id`. Add a new `CompetencyReadPermission` checking `rules.has_perm("oel_tagging.view_tag", ...)`, not the write-side `can_tag_object`. Register the GET view at the same `competencies/<int:competency_tag_id>/criteria-groups/` prefix \#675 already uses for its `<int:group_id>/` DELETE route, so the two share one collection resource. Do not implement windowing or pagination — that's \#682. Verify against \#674/\#675's explicit assumption that this endpoint filters `archived=False` by default.

## Context

- **\#665:** canonical field lists for both models, creates `CompetencyCriterionSerializer` and `rest_api/v1/urls.py`, and the tag-resolution/404 convention this ticket's step 1 reuses.  
- **\#672:** consumes this endpoint's `criteria` array to mark subsections a competency already uses and to build each rule box's chips; needs a criterion's `object_id` directly rather than resolving `oel_tagging_objecttag_id` itself, which this ticket's added field provides.  
- **\#674, \#675:** both explicitly assume this ticket filters `archived=False` by default; \#675 established the `competencies/<int:competency_tag_id>/criteria-groups/` URL prefix this ticket's GET route shares.  
- **The archived-field migration ticket** (no GitHub Issue number yet): adds the `archived` column this endpoint filters on.  
- **\#682:** owns windowing by course-run date and pagination for large result sets; deliberately not built here.  
- ADR 0002 (`docs/openedx_learning/decisions/0002-competency-criteria-model.rst`), "Retrieval scope": `course_id is null` branches are expected to stay small — the basis for returning the whole tree unwindowed in this ticket.  
- `src/openedx_tagging/rest_api/v1/views.py`'s `TaxonomyTagsView` and `serializers.py`'s `TagDataSerializer`: this repo's only existing tree-shaped GET precedent — flat list, parent pointer, no nested/recursive serializer exists anywhere in the codebase.  
- `src/openedx_tagging/rules.py`'s `can_view_tag`/`oel_tagging.view_tag` and `can_view_taxonomy`: the read-side predicate this ticket's permission class checks, structurally distinct from the write-side `can_tag_object`.  
- `src/openedx_tagging/rest_api/v1/exception_handlers.py`: confirms only `APIException`/ `Http404`/`PermissionDenied` need clean mapping, both handled by DRF's default handler.

## Files to create and modify

**New files:** none — every piece extends a file already scoped by \#665/\#674/\#675.

**Modified files**

| File | Nature of modification |
| :---- | :---- |
| `src/openedx_learning/applets/cbe/api.py` | Add `get_competency_criteria_tree(tag_id: int) -> CompetencyCriteriaTree`. |
| `src/openedx_learning/applets/cbe/rest_api/v1/serializers.py` | Add `CompetencyCriteriaGroupSerializer` (first created here); add an `object_id` field to the existing `CompetencyCriterionSerializer`. |
| `src/openedx_learning/applets/cbe/rest_api/v1/permissions.py` | Add `CompetencyReadPermission`, checking `oel_tagging.view_tag` via `rules.has_perm`. Create this file if \#665 didn't already. |
| `src/openedx_learning/applets/cbe/rest_api/v1/views.py` | Add `CompetencyCriteriaTreeView(generics.GenericAPIView)`. |
| `src/openedx_learning/applets/cbe/rest_api/v1/urls.py` | Register `competencies/<int:competency_tag_id>/criteria-groups/` (GET), sharing the collection prefix \#675 already uses for its `<int:group_id>/` item route. |
| `src/openedx_learning/applets/cbe/rest_api/v1/tests/test_views.py` | Extend with tree-fetch integration tests (empty, full, 404, 403). |
| `src/openedx_learning/applets/cbe/tests/test_api.py` | Extend with unit tests for `get_competency_criteria_tree`. |
</details>
