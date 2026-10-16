# [BE] Create CompetencyCriteria

GitHub: https://github.com/openedx/openedx-core/issues/665 (#665, OPEN)
Cached: 2026-10-15

**Blocked by** \#613 (the CBE data model): `CompetencyCriteriaGroup`/`CompetencyCriterion` exist only as approved design in ADR 0002, not yet in code.

Repo: `openedx-core` (endpoint plus a constraints migration) and `openedx-platform` (CMS-side wiring).

## Use Case

As a course author associating (or re-associating) a gradable subsection with a competency in a course, via the Manage & Apply Competencies authoring flow (\#671), I want the system to attach a Competency Criterion, either into a specific existing Criteria Group I already have in hand, or by deriving and creating whatever part of the group hierarchy (root, course-level, leaf) doesn't yet exist for this competency and course, so that this subsection's grade becomes a concrete, evaluable rule toward the learner's mastery of this competency, without me ever having to see or manage the underlying group structure unless I am explicitly targeting one.

## Acceptance Criteria

These scenarios are verifiable via Postman.

```
Scenario: No group supplied, no existing groups at all for this tag and course
  Given a competency exists with no CompetencyCriteriaGroup rows at all
  And the requesting user has studio write access to the subsection's course and view access to the competency's taxonomy
  When a POST request is sent to the create-criterion endpoint for that competency with a valid gradeable-subsection object_id and no group_id
  Then the response returns status code 201
  And a root CompetencyCriteriaGroup is created for the competency (course_id null, parent null)
  And a course-level CompetencyCriteriaGroup is created, parented under the root, scoped to object_id's parsed course, named from the competency's value and the course's display name
  And a new leaf CompetencyCriteriaGroup is created, parented under the course-level group, with an empty name
  And a CompetencyCriterion is created, associated with that new leaf CompetencyCriteriaGroup
  And the response body's "group_id" refers to that new leaf group
  And the response body includes the criterion's "id", "group_id", "object_tag_id", "rule_profile_id", and any supplied "rule_type_override"/"rule_payload_override"

Scenario: No group supplied, logic_operator provided
  Given a competency exists with no CompetencyCriteriaGroup rows at all
  When a POST request is sent to the create-criterion endpoint with a valid gradeable-subsection object_id, no group_id, and logic_operator "AND"
  Then the response returns status code 201
  And the newly created leaf CompetencyCriteriaGroup's logic_operator is "AND"

Scenario: No group supplied, logic_operator omitted
  Given a competency exists with no CompetencyCriteriaGroup rows at all
  When a POST request is sent to the create-criterion endpoint with a valid gradeable-subsection object_id, no group_id, and no logic_operator
  Then the response returns status code 201
  And the newly created leaf CompetencyCriteriaGroup's logic_operator defaults to "OR"

Scenario: Reject group_id and logic_operator supplied together
  Given a leaf CompetencyCriteriaGroup already exists for a competency, scoped to Course X
  When a POST request to that competency's endpoint supplies the leaf's group_id, a matching object_id, and a logic_operator
  Then the response returns status code 400
  And the response body identifies that group_id and logic_operator cannot be supplied together
  And no CompetencyCriterion is created

Scenario: No group supplied, a course-level group already exists for this tag and course
  Given a competency already has a root group and a course-level group for Course X
  When a POST request associates a second gradeable subsection, also in Course X, with the same competency and no group_id
  Then the response returns status code 201
  And no new root or course-level group is created — the existing course-level group's id is unchanged
  And a new leaf CompetencyCriteriaGroup is created as a sibling under that same course-level group
  And a CompetencyCriterion is created, associated with that new sibling leaf CompetencyCriteriaGroup

Scenario: No group supplied, a different course than any existing group for this tag
  Given a competency already has a root group and a course-level group for Course X
  When a POST request associates a gradeable subsection in Course Y (a different course) with the same competency and no group_id
  Then the response returns status code 201
  And the existing root is reused — no new root group is created
  And a new course-level CompetencyCriteriaGroup is created for Course Y, parented under the existing root
  And a new leaf CompetencyCriteriaGroup is created under that new Course Y course-level group
  And a CompetencyCriterion is created, associated with that new leaf CompetencyCriteriaGroup

Scenario: Group supplied, targeting an existing leaf whose competency and course both match
  Given a leaf CompetencyCriteriaGroup already exists for a competency, scoped to Course X
  When a POST request to that competency's endpoint supplies the leaf's group_id together with an object_id whose parsed course is Course X
  Then the response returns status code 201
  And no CompetencyCriteriaGroup rows are created at any level
  And a CompetencyCriterion is created, associated with the supplied leaf CompetencyCriteriaGroup
  And the response body's "group_id" matches the supplied group's id

Scenario: Group supplied but resolves to a root or course-level group, not a leaf
  Given the supplied group_id belongs to a root or course-level CompetencyCriteriaGroup rather than a leaf
  When a POST request supplies that group_id
  Then the response returns status code 400
  And the response body identifies that only a leaf group may be targeted

Scenario: Group supplied but belongs to a different competency than the URL's tag_id
  Given a leaf CompetencyCriteriaGroup exists for competency A
  When a POST request to competency B's endpoint supplies competency A's leaf group_id
  Then the response returns status code 400
  And the response body identifies the group/competency mismatch

Scenario: Group supplied, is a leaf and belongs to the right competency, but its course scope doesn't match the submitted subsection
  Given a leaf CompetencyCriteriaGroup is scoped, via its course-level ancestor, to Course X
  When a POST request supplies that leaf's group_id together with an object_id whose parsed course is Course Y
  Then the response returns status code 400
  And the response body identifies the course mismatch

Scenario: Reject duplicate association, same group re-targeted
  Given a CompetencyCriterion already exists associating object_id X with tag_id T, attached to leaf group G
  When a POST request to competency T's endpoint supplies group_id G together with the same object_id X
  Then the response returns status code 400
  And the response body identifies the duplicate tag_id/object_id association
  And no new CompetencyCriterion is created

Scenario: Group supplied, targeting a different existing leaf group already used by this tag/object pair
  Given a CompetencyCriterion already exists associating object_id X with tag_id T, attached to leaf group G
  And a sibling leaf group G2 also exists for tag_id T under the same course-level group as G
  When a POST request to competency T's endpoint supplies group_id G2 together with the same object_id X
  Then the response returns status code 201
  And no CompetencyCriteriaGroup rows are created at any level
  And a second CompetencyCriterion is created, associated with G2
  And the tag_id/object_id association now participates in both G and G2

Scenario: Reject duplicate association via the derive-or-create path
  Given a CompetencyCriterion already exists associating object_id X with tag_id T, attached to some leaf group elsewhere for the same competency
  When a POST request to competency T's endpoint supplies object_id X and no group_id
  Then the response returns status code 400
  And the response body identifies the duplicate tag_id/object_id association
  And no new CompetencyCriteriaGroup or CompetencyCriterion rows are created

Scenario: Create a criterion with no rule fields supplied
  Given a competency and a valid gradeable-subsection object_id
  And no rule profile is scoped to that competency's taxonomy
  When a POST request creates a criterion with no rule_profile_id, rule_type_override, or rule_payload_override supplied
  Then the response returns status code 201
  And the created criterion's "rule_profile_id" is the system default competency rule profile
  And its "rule_type_override" and "rule_payload_override" are both null

Scenario: A taxonomy-scoped rule profile is assigned ahead of the system default
  Given a competency whose taxonomy has its own rule profile
  And a valid gradeable-subsection object_id
  When a POST request creates a criterion with no rule_profile_id, rule_type_override, or rule_payload_override supplied
  Then the response returns status code 201
  And the created criterion's "rule_profile_id" is that taxonomy's rule profile, not the system default
  And its "rule_type_override" and "rule_payload_override" are both null

Scenario: A criterion is never created without a rule source
  Given a criterion created through this endpoint by any combination of supplied fields
  When it is read back
  Then it either has a "rule_profile_id" with both override fields null, or has both override fields set with "rule_profile_id" null
  And it is never all three null

Scenario: Reusing a subsection already tagged with a different competency preserves both tags
  Given a gradeable subsection is already tagged with competency A via a prior CompetencyCriterion
  When a POST request creates a criterion associating that same subsection with competency B
  Then the response returns status code 201
  And a CompetencyCriterion is created, associated with the resolved leaf CompetencyCriteriaGroup for competency B
  And the subsection's object tags still include both competency A and competency B afterward

Scenario: Reject creation for a competency that does not exist
  Given the referenced competency tag id does not exist, or exists but is not a tag within a Competency Taxonomy
  When a POST request is sent to the create-criterion endpoint referencing that id
  Then the response returns status code 404

Scenario: Reject a supplied group_id that does not exist
  Given the referenced group_id does not exist
  When a POST request supplies that id
  Then the response returns status code 404

Scenario: Reject creation with a missing or malformed object_id
  Given a POST request omits "object_id", or supplies a value that doesn't parse as a subsection usage key
  When the request is processed
  Then the response returns status code 400
  And the response body identifies the invalid or missing field

Scenario: Reject creation when object_id's parsed course has no matching CourseRun
  Given a POST request supplies an object_id that parses as a valid usage key, but its course key resolves to no CourseRun row
  When the request is processed
  Then the response returns status code 400
  And the response body identifies the course as unresolvable

Scenario: Reject creation without permission
  Given the requesting user lacks studio write access to the subsection's course, or lacks view access to the taxonomy owning the competency tag
  When a POST request is sent to the create-criterion endpoint
  Then the response returns status code 403
```

## Description

This ticket adds a single POST endpoint that creates a `CompetencyCriterion`, either by attaching it into an already-existing leaf `CompetencyCriteriaGroup` or by deriving/creating whatever part of the 3-level group hierarchy (root, course-level, leaf) doesn't already exist, in one request/response contract.

**Current state**

No endpoint exists today to create a `CompetencyCriterion`. Per ADR 0002, `CompetencyCriteriaGroup` is a self-referential tree node (`id`, nullable self-FK `parent_id`, `oel_tagging_tag_id` FK to the competency tag, nullable `course_id` FK to a course run, `name`, `ordering`, `logic_operator`), and `CompetencyCriterion` is the leaf rule (`id`, `group_id` FK, `oel_tagging_objecttag_id` FK to the tag/object association, nullable `rule_profile_id`, nullable `rule_type_override`/`rule_payload_override`).

**Requested change**

`POST /api/cbe/v1/competencies/<int:tag_id>/criteria/` accepts a required `object_id` (subsection usage-key string) and an optional `group_id` (an existing leaf group's id). There is no separate `course_id` or `taxonomy_id` field: the course is derived by parsing `object_id` and resolving its course key to a `CourseRun`, and the taxonomy is derived from `tag_id` alone.

This URL follows the [Open edX REST API Conventions](https://openedx.atlassian.net/wiki/spaces/AC/pages/18350757/Open+edX+REST+API+Conventions) and the in-progress update at openedx/openedx-platform#39003.

If `group_id` is supplied, the endpoint validates it names a leaf group belonging to the right competency and course, then attaches the criterion directly and creates no groups. If `group_id` is omitted, the endpoint gets-or-creates the root and course-level groups for this competency and course, always creates a fresh leaf under them, and attaches the criterion there. Root and course-level resolution is race-safe via two new partial `UniqueConstraint`s on `CompetencyCriteriaGroup` (one root per competency; one course-level group per competency+course), rather than `select_for_update` or catch-and-retry, neither of which appears in this codebase. See Technical Details for the exact validation order and status codes.

An optional `logic_operator` field is accepted alongside `object_id`, defaulting to `"OR"` when omitted. It applies only on the derive-or-create path, to the newly created leaf group (the leaf is a fresh row every time `group_id` is omitted, so this never overwrites another criterion's group). Supplying `logic_operator` together with `group_id` is rejected with a 400: an existing leaf group's `logic_operator` was set when the group was created, and updating it is #675's scope, not this endpoint's, so the two fields are mutually exclusive rather than one silently overriding or being ignored by the other. This closes a gap where the calling UI's AND/OR choice for a new leaf group had nowhere to go and was silently discarded.

`rule_profile_id`, `rule_type_override`, and `rule_payload_override` may all be omitted together in the same request: that is a valid, complete request, not an incomplete one. The created `CompetencyCriterion` row is persisted with all three fields null, and that all-null state is itself the signal that the system default competency rule profile applies. This ticket does not resolve or store a concrete default profile at creation time; it only accepts and persists the all-null state as meaningful. Interpreting null as "apply the system default" is a downstream evaluation-time concern, out of scope here.

Either way, tagging the object is a read-merge-write: the object's existing tags in this taxonomy are preserved and the competency tag is unioned in, never overwritten.

The endpoint also rejects creating a second `CompetencyCriterion` for a `tag_id`/`object_id` pairing that already has one, with a 400, whether the request re-targets the same leaf group, targets a different existing leaf group, or would otherwise go through the derive-or-create path. This check runs before any group creation, so a rejected duplicate never leaves an orphaned empty group behind (ADR 0002 forbids persisting empty groups).

The endpoint rejects a `tag_id` that isn't a Competency Taxonomy tag (404), and requires `oel_tagging.can_tag_object`: studio write access to the subsection's course plus taxonomy view access, not a staff-only check, since the actor is an ordinary course author tagging their own content.

This ticket also adds the `openedx-platform` wiring (`INSTALLED_APPS` entries, the `cms/urls.py` include) needed to reach this REST API surface, since no other ticket does: an earlier standalone group-creation endpoint (\#664, \#646) was superseded by this ticket resolving or creating the group hierarchy internally, so there's no separate ticket left to own that wiring.

**Explicitly out of scope**

- Choosing which leaf to target when appending: the calling UI's job (\#672).  
- Updating or deleting a `CompetencyCriteriaGroup` (\#675).  
- Parent-competency dominance validation. Tracked in \#666, which also resolved that two of the three originally-scoped containment rules (duplicate-path overlap, group/course isolation) don't need separate implementation given this ticket's subsection-only scope. This ticket only reserves the `_validate_containment(group, object_id)` insertion point.  
- Validating that `object_id` refers to a gradeable subsection. Considered and dropped: grading configuration lives in `openedx-platform`, and `openedx-core`'s own catalog model (`CourseRun`) explicitly does not yet model grading policy, so there is no data in this repo to validate against. See Open Questions.  
- Listing or retrieving criteria or groups (\#681).  
- Any UI (\#671, \#672, and the broader Manage & Apply Competencies frontend epic).  
- Course-level (final-grade) association: this ticket accepts a subsection-usage-key `object_id` only.

<details>
<summary>Open Questions</summary>

- **\[non-blocking, owner: implementer\]** Should the two new `UniqueConstraint`s (one root per competency; one course-level group per competency+course) land in this ticket's own follow-up migration, or fold into \#613's initial migration if it hasn't merged yet? Recommended: an independent follow-up migration here, to keep the tickets decoupled.  
- **\[non-blocking, owner: implementer\]** Naming convention for the root and course-level groups, which are never shown in the UI but likely need a non-null `name` per ADR 0002's field list. Recommended: a deterministic placeholder such as `f"{tag.value} (root)"` / `f"{tag.value} — {course_run.title}"`, to aid admin/debug visibility.  
- **\[non-blocking, owner: architect/future\]** `object_id` currently must resolve to a `CourseRun` (400 otherwise). Future library-subsection support may need this to loosen; no action needed now.  
- **\[non-blocking, owner: architect/future\]** Validating that `object_id` is gradeable was dropped: `openedx-core` has no grading data to check against (`CourseGradingPolicy` isn't built yet; grading lives in `openedx-platform`, never imported here). If needed later, it'll need a sync mechanism into `openedx_catalog` or enforcement at another layer (frontend, or the evaluation handler). Not resolved here.  
- **\[non-blocking, owner: architect/future\]** This ticket builds only the 3-level hierarchy (root/course-level/leaf), no richer author-defined grouping. If added later, `resolve_supplied_leaf_group`'s leaf-shape test (`parent_id` set, `course_id` null) breaks, since a new grouping node would have the same shape. Fix needs either an explicit node-type field or a relationship-based check (child groups vs. a `CompetencyCriterion`). Not resolved here; flagged so a future ticket doesn't rediscover it.
- **\[non-blocking, owner: implementer\]** Whether to keep the `urls.py` → `rest_api/urls.py` → `rest_api/v1/urls.py` indirection when this app currently has only one URL to register. Raised as a minor review quibble; not blocking, and trivial to collapse to fewer files in the PR if the implementer prefers a flatter structure.
</details>
<details>
<summary>Technical Details</summary>

**Data Structures**

```
CompetencyCriteriaGroup (ADR 0002 fields, unchanged) gains two partial unique constraints:
  UniqueConstraint(fields=["oel_tagging_tag_id"], condition=Q(parent_id__isnull=True))
      # at most one root group per competency
  UniqueConstraint(fields=["oel_tagging_tag_id", "course_id", "parent_id"], condition=Q(course_id__isnull=False))
      # at most one course-level group per (competency, course) under a given parent
```

These constraints make root/course-level resolution race-safe via plain `get_or_create()` inside `transaction.atomic()`, the pattern this repo already uses elsewhere for constraint-backed `get_or_create()` calls, rather than `select_for_update` or catch-and-retry, neither of which appears in this codebase. A leaf group never sets `course_id` and always has a non-null `parent_id`, so it never matches either constraint's condition: no new depth/level column is needed, since `(parent_id, course_id)` alone identifies root, course-level, and leaf.

```py
def create_competency_criterion(
    group: CompetencyCriteriaGroup,
    object_id: str,
    rule_profile_id: int | None = None,
    rule_type_override: str | None = None,
    rule_payload_override: dict | None = None,
) -> CompetencyCriterion:
    """Read-merge-write the ObjectTag, call the reserved _validate_containment(group,
    object_id) seam (implemented by #666, not here), then create and return the
    CompetencyCriterion row under group."""

def resolve_or_create_leaf_group(
    tag: Tag, course_run: CourseRun, logic_operator: str | None = None,
) -> CompetencyCriteriaGroup:
    """Get-or-create the root and course-level groups for this competency/course, then
    always create and return a fresh leaf group parented under the course-level group,
    with logic_operator set from the argument, defaulting to "OR" if None."""

def resolve_supplied_leaf_group(group_id: int, tag: Tag, course_run: CourseRun) -> CompetencyCriteriaGroup:
    """Resolve group_id via get_object_or_404 (this app has no custom exception-handling
    mixin, so a bare .get() would surface as an unhandled 500, not a 404). Validate, in
    order: it is a leaf (parent_id not null, course_id null); it belongs to tag; its
    course-level parent's course_id matches course_run. Raise a field-level 400 on the
    first failure that doesn't hold; otherwise return the group unchanged."""

def associate_competency_criterion(
    tag_id: int,
    object_id: str,
    group_id: int | None = None,
    logic_operator: str | None = None,
    rule_profile_id: int | None = None,
    rule_type_override: str | None = None,
    rule_payload_override: dict | None = None,
) -> CompetencyCriterion:
    """The single public entry point. Resolves the competency Tag and the CourseRun from
    object_id's parsed course key, rejects a duplicate (tag_id, object_id) association
    regardless of group_id, then branches on whether group_id was supplied
    (resolve_supplied_leaf_group vs. resolve_or_create_leaf_group), then calls
    create_competency_criterion() on the resulting leaf, all inside one
    transaction.atomic() block. Rejects with a 400 if group_id and logic_operator are
    both supplied, since logic_operator only ever applies to a leaf group this call
    creates, and updating an existing leaf's logic_operator is #675's scope. When
    logic_operator is supplied without group_id, it is threaded into
    resolve_or_create_leaf_group."""
```

**Logic**

1. Resolve the competency `Tag` from the URL's `tag_id`; 404 if missing or not backed by a `CompetencyTaxonomy`.  
2. Parse `object_id` via `UsageKey.from_string`; 400 with a field-level error if it doesn't parse.  
3. Resolve the `CourseRun` from the parsed key's course key via `openedx_catalog.api.get_course_run()`; 400 if no matching row. This `course_run` is the single source of truth for course: it drives the course-scope check, whichever branch runs.  
4. Permission check: build the taxonomy/object-id permission object and check `oel_tagging.can_tag_object`; 403 on failure. This composite (studio write access to the subsection's course plus taxonomy view access) is already registered globally by `openedx-platform`'s `content_tagging` app, so no new predicate is needed.  
5. **Duplicate check**: look up `ObjectTag.objects.filter(object_id=object_id, taxonomy_id=tag.taxonomy_id, tag_id=tag.id).first()`. If found, check whether any `CompetencyCriterion` already references it (`CompetencyCriterion.objects.filter(oel_tagging_objecttag=existing_object_tag).exists()`); if so, reject with a 400 `ValidationError` (this repo's existing pattern for uniqueness violations — see `src/openedx_tagging/rest_api/v1/serializers.py`'s `validate_tag_value`; there is no 409 usage anywhere in this codebase's REST API). If no `ObjectTag` exists yet for this tag on this object, there is nothing to conflict with; proceed. This check runs before any group creation, regardless of whether `group_id` was supplied, so a duplicate attempt via the derive-or-create path doesn't leave behind an orphaned empty group (ADR 0002 forbids persisting empty groups).  
6. **`group_id`/`logic_operator` exclusivity check**: if both `group_id` and `logic_operator` are supplied, reject with a 400 `ValidationError` naming the conflict, before resolving or creating anything. `logic_operator` only ever sets a newly created leaf's operator; an existing leaf's operator is #675's to change, not this endpoint's, so the two fields together are a client error rather than an ambiguity for this endpoint to resolve on its own.  
7. Branch on `group_id`: if supplied, call `resolve_supplied_leaf_group()`; if not, call `resolve_or_create_leaf_group()`, passing `logic_operator` through so the newly created leaf's `logic_operator` column is set from it, defaulting to `"OR"` if omitted. Both return a `CompetencyCriteriaGroup` guaranteed to be a valid, course-matched leaf (see Data Structures for the supplied-group validation order).  
8. Inside one `transaction.atomic()` block covering steps 7-8: call `create_competency_criterion()` on the resolved/created leaf. Keeping this inside the same atomic block as group resolution matters for the no-`group_id` branch: if criterion creation fails (a containment violation from \#666's seam, an invalid override), the rollback must also undo any newly-created root/course-level/leaf groups, since ADR 0002 forbids persisting empty groups. `create_competency_criterion()`'s own read-merge-write step will re-resolve the same `ObjectTag` row checked in step 5 (or find none, on a first association) — an implementer may thread the already-resolved `ObjectTag` through to avoid a redundant query, but this is an optimization, not a correctness requirement.  
9. Return 201 with the created criterion's representation, including `group_id` referring to whichever leaf was used.

Public-API impact: additive functions in `applets/cbe/api.py`, reusing `openedx_tagging.api.get_object_tags`/`tag_object` and `openedx_catalog.api.get_course_run` unchanged. No breaking changes: greenfield work, no shipped callers. `.importlinter` needs `openedx_catalog` and `openedx_learning` added to its layering contract if \#613 hasn't already, since this ticket's course-run lookup crosses into `openedx_catalog`.

Test strategy: unit tests for `associate_competency_criterion` covering both branches (derive-or-create: first association, same-course reuse, different-course reuse, a concurrent-request race not producing duplicate root/course-level rows, `logic_operator` supplied vs. defaulted to `"OR"`; supplied-group: happy path, non-leaf rejection, ownership-mismatch rejection, course-mismatch rejection, not-found) plus the three duplicate-association rejection cases (same group, different existing group, derive-path) plus the `group_id`/`logic_operator` mutual-exclusion rejection plus DRF integration tests for every acceptance criterion above.

### Example Resolution Prompt

Implement `POST /api/cbe/v1/competencies/<int:tag_id>/criteria/` per the Data Structures and Logic above: request body `{object_id, group_id?, logic_operator?, rule_profile_id?, rule_type_override?, rule_payload_override?}`. Assume \#613 has landed `CompetencyCriteriaGroup`/`CompetencyCriterion` matching ADR `docs/openedx_learning/decisions/0002-competency-criteria-model.rst`; code goes under `src/openedx_learning/applets/cbe/` per ADR 0001\.

Build `associate_competency_criterion()` as the single `api.py` entry point, following the Technical Details signatures and call order exactly: course/tag resolution, the permission check, the duplicate-association check, the `group_id` branch, then the shared atomic block. One `CompetencyCriterionSerializer`, no variant needed, with `group_id` genuinely optional, mirroring the existing optional-field-driven-branching pattern in this repo's `TaxonomyTagsView` tag-creation body (see Context). Reuse the existing `oel_tagging.can_tag_object` permission; no new predicate. Do not validate gradeability of `object_id` — deliberately out of scope, see Open Questions. Do not implement containment/isolation-rule validation — that is \#666's scope, not this ticket's.

Verify against every scenario in Acceptance Criteria above.

## Context

- **Namespace:** `/api/cbe/v1/` is one combined namespace, deliberately not split into authoring vs. learner API paths, even if a learner-facing CBE endpoint is added under this app later.  
- **\#671:** source of the course-author actor and the reuse-vs-create branching this ticket implements.  
- **\#666:** implements the parent-competency dominance validation via the `_validate_containment(group, object_id)` seam this ticket reserves (see Explicitly out of scope above for its resolved scope).  
- **\#672:** eventual UI consumer of this endpoint; no contract dependency.  
- **\#675:** update/delete of a `CompetencyCriteriaGroup`.  
- **\#681:** GET endpoint for groups \+ criteria.  
- **Companion ticket, `openedx-platform` (not yet numbered):** this ticket's `oel_tagging.can_tag_object` check (step 4 above) currently resolves course objects through a legacy-only role check that never consults the new authorization service, even after a course has switched over to it, unlike Studio's own tag-editing endpoint, which already handles that switch correctly. The companion ticket fixes the shared permission check itself; this ticket needs no code change once it lands, since `has_perm('oel_tagging.can_tag_object', ...)` will simply start returning the right answer.  
- ADR 0002 (`docs/openedx_learning/decisions/0002-competency-criteria-model.rst`): canonical field lists and tree semantics for both models; its rule against persisting empty groups is why group creation and criterion creation share one transaction.  
- ADR 0001: places this ticket's code at `src/openedx_learning/applets/cbe/`.  
- `openedx-platform`'s `content_tagging/rules.py`: overrides `oel_tagging.can_tag_object` with the permission composite this ticket relies on.  
- `src/openedx_tagging/rest_api/v1/views.py`'s `TaxonomyTagsView`: precedent for an optional request field (`parent_tag_value`) branching create logic downstream, the pattern `group_id` follows.  
- `src/openedx_tagging/rest_api/v1/exception_handlers.py`: only `APIException`/`Http404`/ `PermissionDenied` map to a clean response, hence `get_object_or_404` over a bare `.get()` for the supplied-`group_id` path.  
- `src/openedx_tagging/rest_api/v1/serializers.py`'s `validate_tag_value`: this repo's only existing uniqueness-violation precedent, a 400 `ValidationError`, the pattern the duplicate-association check follows. No 409 usage exists anywhere in this codebase's REST API.  
- `src/openedx_tagging/models/base.py`'s `ObjectTag`: `unique_together` on `(object_id, taxonomy, tag_id)`, which the duplicate-association check relies on.  
- `src/openedx_tagging/api.py` (`get_object_tags`, `tag_object`): the two public functions this ticket's read-merge-write logic composes.  
- `openedx_catalog.api.get_course_run()`: resolves the `CourseRun` from a course key. See Open Questions for why gradeable-subsection validation isn't checked against it.

## Files to create and modify

**New files**

| File | Purpose |
| :---- | :---- |
| `src/openedx_learning/applets/cbe/migrations/0002_criteria_group_unique_constraints.py` | adds the two partial `UniqueConstraint`s on `CompetencyCriteriaGroup` |
| `src/openedx_learning/applets/cbe/rest_api/v1/serializers.py` | `CompetencyCriterionSerializer` (`object_id` required; `group_id` genuinely optional; optional `logic_operator`, rule, and profile fields) |
| `src/openedx_learning/applets/cbe/rest_api/v1/views.py` | `CompetencyCriterionCreateView(generics.CreateAPIView)`, the single merged view |
| `src/openedx_learning/applets/cbe/rest_api/v1/urls.py` | registers `competencies/<int:tag_id>/criteria/` only |
| `src/openedx_learning/applets/cbe/rest_api/v1/tests/test_views.py` | integration tests covering every acceptance criterion above, both branches |
| `src/openedx_learning/applets/cbe/tests/test_api.py` | unit tests for `associate_competency_criterion`, `resolve_or_create_leaf_group`, `resolve_supplied_leaf_group` |

**Modified files**

| File | Nature of modification |
| :---- | :---- |
| `src/openedx_learning/applets/cbe/api.py` | add `resolve_or_create_leaf_group`, `resolve_supplied_leaf_group`, `create_competency_criterion`, `associate_competency_criterion` (create the file first if \#613 hasn't already) |
| `src/openedx_learning/urls.py`, `rest_api/urls.py`, `rest_api/v1/__init__.py` | package scaffolding, if \#613 hasn't already added it. The path segments each file contributes must chain to the URL `api/cbe/v1/...`, not `api/cbe/rest_api/v1/...`: `rest_api` stays a directory/file-path convention, never a URL segment. |
| `.importlinter` | add `openedx_catalog` and `openedx_learning` to the layering contract, if \#613 didn't already |
| `cms/envs/common.py` (openedx-platform) | add `'openedx_learning'` to `INSTALLED_APPS` |
| `lms/envs/common.py` (openedx-platform) | same, for shared-database migration consistency; no LMS route is added |
| `cms/urls.py` (openedx-platform) | add `path('api/cbe/', include('openedx_learning.urls'))`, so the endpoint resolves at `/api/cbe/v1/...` |
</details>
