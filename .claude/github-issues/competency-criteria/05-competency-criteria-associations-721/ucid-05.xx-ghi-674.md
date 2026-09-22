# [BE] Build endpoint for removing a Competency Criterion

GitHub: https://github.com/openedx/openedx-core/issues/674 (#674, OPEN)
Cached: 2026-09-21

**Blocked by:** \#613 (the CBE data model, including `StudentCompetencyCriteriaGroupStatus`, which this ticket's cascade logic queries), \#665 (creates the `CompetencyCriterion` rows this ticket removes — resolving or creating the group hierarchy as needed via `resolve_or_create_leaf_group()`/`resolve_supplied_leaf_group()`, there's no separate group-creation endpoint — plus the REST scaffolding and `openedx-platform` wiring this ticket relies on), and the archived-field ticket (no GitHub issue yet — adds `archived` to both `CompetencyCriteriaGroup` and `CompetencyCriterion` in one migration, so this ticket and \#675 don't have to race to add it themselves).

Repo: `openedx-core`, single-repo. No `openedx-platform` changes — this ticket's route registers inside the same `rest_api/v1/urls.py` that \#665 wires into Studio.

## Use Case

As a Platform Administrator, I want to remove a single Competency Criterion (a gradeable-subsection association) from a Competency Criteria Group, so that I can correct or retire a mastery rule without having to rebuild the whole group, while learner progress already recorded against that criterion remains intact and auditable.

## Description

**Current state**

No endpoint exists today to remove a `CompetencyCriterion`. Per ADR 0002 Decision 7, a `CompetencyCriterion` (table `CompetencyCriteria`) may be hard-deleted only while no `StudentCompetencyCriteriaStatus` row references it; once one exists, the criterion must be retired by archiving rather than deleting, and existing learner statuses are retained unchanged. The same delete protection applies one level up: `CompetencyCriteriaGroup` cannot be hard-deleted while a `StudentCompetencyCriteriaGroupStatus` row references it, or while it still holds any row (active or archived) underneath it. Per ADR 0003 Decision 4, if the criterion is already in use by learner status, the authoring UI must warn before the change is applied — this ticket's endpoint is the mechanism that enforces the actual archive-vs-delete branch; the UI-side warning and confirmation step is out of scope here (a frontend concern).

**Requested change**

A new endpoint, nested under the existing criterion's group, that removes a `CompetencyCriterion`:

- Resolves the criterion from the URL (`group_id` and `criterion_id`); 404 if the criterion doesn't exist, or exists but does not belong to the given `group_id`.  
- Checks whether any `StudentCompetencyCriteriaStatus` row references this criterion.  
  - If none exists: hard-deletes the `CompetencyCriterion` row.  
  - If any exists: sets `archived=True` on the row instead (no hard delete), leaving it in place for learner-status traceability.  
- On a hard-delete, also removes the underlying `oel_tagging_objecttag` row, but only if no other `CompetencyCriterion` still references it.  
  - Per ADR 0002's own worked example, one `ObjectTag` can be referenced by multiple `CompetencyCriterion` rows (the same tagged assignment used in two different groups); if another criterion still references it, the tagging association is left untouched.  
  - **Assumption:** removing the last criterion referencing an `ObjectTag` removes the `ObjectTag` itself, un-tagging the content, rather than leaving it in place with no criterion behind it for the author to clean up separately in the tagging UI.  
  - This only removes the `ObjectTag`. The underlying `Tag` (the competency definition itself) is never deleted; it continues to exist in the taxonomy regardless.  
- On the archive path, the `ObjectTag` is never touched. This isn't optional: ADR 0002 Decision 7 extends the same learner-status delete protection to `oel_tagging_objecttag`, so deleting it while an archived criterion still references it would violate the ADR (and risks cascading away the row being preserved, or orphaning its reference, depending on the FK's `on_delete`).  
  - Practical effect: a retired criterion's tag can still appear associated with the content wherever the tagging system surfaces object tags, effectively demoting it from a competency tag to a regular tag. Whether that specifically surfaces on the Course Outline page depends on a separate open question outside the scope of this Github Issue about whether competency tags should display on the Course Outline page at all (that page is out of MVP scope); either way, the tag stays visible in the tagging system's own views.  
  - Accepted for MVP: hard-delete, the higher-frequency path during authoring, already removes the association cleanly. Revisit only if not removing the `ObjectTag` association on the archive path causes real author confusion post-launch.  
- Removing a criterion can leave its parent group, and potentially several ancestor groups above it, with no remaining active content. This endpoint walks the ancestor chain and resolves each level, so no empty group is ever left persisted, per ADR 0002 Decision 2 ("backend validation must reject" persisted empty groups):  
  - Starting from the removed/archived criterion's immediate group, and continuing upward through `parent_id` for as long as a level changes state:  
    - **If the triggering event below was an archive** (the criterion, or an ancestor group, was archived rather than removed): if this group has no remaining non-archived children, archive this group too, then continue the walk one level up, again checking for non-archived children.  
    - **If the triggering event below was a hard-delete**: if this group has no children left at all, hard-delete it too (unless a `StudentCompetencyCriteriaGroupStatus` row references it directly, in which case archive it instead per the same delete-protection rule that already applies to criteria) and continue the walk one level up as a hard-delete event. If this group's only remaining children are archived, archive this group instead and continue the walk one level up, now as an archive event. If this group still has at least one non-archived child, stop.  
  - This matches what the frontend already assumes: the \#709/\#710 frontend tickets document \#674 (this ticket) as cascading an emptied group away server-side, and both rely on the existing "zero real groups → placeholder" fallback (\#671/\#672) to keep the page renderable even if the walk empties the competency's entire tree.  
- Requires `oel_tagging.can_tag_object`: studio write access to the criterion's course plus taxonomy view access on the competency's taxonomy, checked inline via `has_perm()` inside `delete_competency_criterion()`, the same pattern \#665 uses in `associate_competency_criterion()`, not a DRF permission class.  
- Is idempotent for an already-archived criterion: a repeat `DELETE` on an archived row returns the same 200 response rather than a 404 or error, since the row still exists and is already in its terminal state. A repeat `DELETE` on a hard-deleted (now-gone) row returns 404, since the row is genuinely gone.

**Explicitly out of scope**

- Removing or archiving a `CompetencyCriteriaGroup` directly (\#675).  
- A general-purpose "reject empty groups" validation applied to other write paths (e.g. group creation); this ticket only prevents empty groups via the cascade walk on its own removal path.  
- Touching an `oel_tagging_objecttag` row still referenced by another `CompetencyCriterion` — shared references are always preserved.  
- Any UI, including the in-use warning/confirmation flow ADR 0003 Decision 4 requires in Studio.  
- Updating `rule_type_override`/`rule_payload_override`/`competency_rule_profile_id` on an existing criterion (that's an edit, not a removal — a separate ticket if needed).  
- Listing or retrieving criteria (a separate GET/list ticket).

## Acceptance Criteria

These scenarios are verifiable via Postman.

```
Scenario: Hard-delete a criterion with no learner status
  Given a CompetencyCriterion exists under a group, with no StudentCompetencyCriteriaStatus row referencing it
  And the requesting user has studio write access to the criterion's course and view access to the competency's taxonomy
  When a DELETE request is sent to the remove-criterion endpoint for that criterion's group_id and criterion_id
  Then the response returns status code 200
  And the response body includes "id" matching the removed criterion and "archived" as false
  And a subsequent DELETE to the same URL returns status code 404

Scenario: Archive instead of hard-delete when learner status exists
  Given a CompetencyCriterion exists and a StudentCompetencyCriteriaStatus row references it
  When a DELETE request is sent to the remove-criterion endpoint for that criterion
  Then the response returns status code 200
  And the response body includes "id" matching the criterion and "archived" as true
  And the CompetencyCriterion row still exists in the database with archived=true

Scenario: Repeat removal of an already-archived criterion is idempotent
  Given a CompetencyCriterion was previously archived via this endpoint
  When a DELETE request is sent again to the same criterion's URL
  Then the response returns status code 200
  And the response body is unchanged ("archived" still true)

Scenario: A shared tagged-object association survives when another criterion still references it
  Given a gradeable subsection is tagged with a competency and referenced by two CompetencyCriterion rows in two different groups
  When a DELETE request removes one of those two CompetencyCriterion rows
  Then the response returns status code 200
  And the other CompetencyCriterion row referencing the same oel_tagging_objecttag is unaffected
  And the underlying oel_tagging_objecttag row still exists

Scenario: Hard-deleting the last criterion referencing an ObjectTag also removes that ObjectTag
  Given a CompetencyCriterion exists, no other CompetencyCriterion references its oel_tagging_objecttag, and no StudentCompetencyCriteriaStatus row references the criterion
  When a DELETE request removes that criterion
  Then the response returns status code 200
  And the CompetencyCriterion row no longer exists
  And the oel_tagging_objecttag row it referenced no longer exists

Scenario: Archiving (not hard-deleting) a criterion never touches its tagged object
  Given a CompetencyCriterion exists and a StudentCompetencyCriteriaStatus row references it
  When a DELETE request removes that criterion
  Then the response returns status code 200
  And the oel_tagging_objecttag row it references still exists, whether or not any other criterion references it

Scenario: Hard-deleting a group's only criterion cascade-deletes the now-empty group
  Given a CompetencyCriteriaGroup has exactly one CompetencyCriterion, no StudentCompetencyCriteriaStatus row references it, and no StudentCompetencyCriteriaGroupStatus row references the group
  When a DELETE request removes that criterion
  Then the response returns status code 200
  And the CompetencyCriteriaGroup row no longer exists in the database
  And a subsequent POST to the create-criterion endpoint for that group_id returns status code 404

Scenario: Cascade-delete propagates through multiple empty ancestor groups
  Given a root CompetencyCriteriaGroup's only child is a leaf CompetencyCriteriaGroup, which has exactly one CompetencyCriterion, and no learner status of any kind references the criterion or either group
  When a DELETE request removes that criterion
  Then the response returns status code 200
  And the leaf CompetencyCriteriaGroup row no longer exists in the database
  And the root CompetencyCriteriaGroup row no longer exists in the database

Scenario: Cascade stops at an ancestor with a surviving sibling
  Given a root CompetencyCriteriaGroup has two child leaf groups, each with one CompetencyCriterion, and no learner status references either criterion
  When a DELETE request removes one leaf group's criterion
  Then the response returns status code 200
  And that leaf CompetencyCriteriaGroup row no longer exists in the database
  And the root CompetencyCriteriaGroup row still exists in the database, since its other leaf group is still active

Scenario: Archiving a group's only criterion also archives the group
  Given a CompetencyCriteriaGroup has exactly one CompetencyCriterion, and a StudentCompetencyCriteriaStatus row references it
  When a DELETE request removes that criterion
  Then the response returns status code 200
  And the response body's "archived" is true
  And the CompetencyCriteriaGroup row still exists in the database with archived=true

Scenario: An archive cascades upward through an ancestor with no other active content
  Given a root CompetencyCriteriaGroup's only child is a leaf CompetencyCriteriaGroup, which has exactly one CompetencyCriterion referenced by a StudentCompetencyCriteriaStatus row
  When a DELETE request removes that criterion
  Then the response returns status code 200
  And the leaf CompetencyCriteriaGroup row still exists in the database with archived=true
  And the root CompetencyCriteriaGroup row still exists in the database with archived=true

Scenario: A group with its own direct learner status is archived, not hard-deleted, even with zero remaining children
  Given a CompetencyCriteriaGroup has exactly one CompetencyCriterion, no StudentCompetencyCriteriaStatus row references the criterion, and a StudentCompetencyCriteriaGroupStatus row directly references the group
  When a DELETE request removes that criterion
  Then the response returns status code 200
  And the response body's "archived" is false (the criterion itself was hard-deleted)
  And the CompetencyCriteriaGroup row still exists in the database with archived=true

Scenario: Reject removal for a criterion/group mismatch
  Given a CompetencyCriterion exists under group A
  When a DELETE request is sent to the remove-criterion endpoint using group B's id and that criterion's id
  Then the response returns status code 404

Scenario: Reject removal for a criterion that does not exist
  Given the referenced criterion id does not exist
  When a DELETE request is sent referencing that id
  Then the response returns status code 404

Scenario: Reject removal without permission
  Given the requesting user lacks studio write access to the criterion's course, or lacks view access to the taxonomy owning the competency
  When a DELETE request is sent to the remove-criterion endpoint
  Then the response returns status code 403
```

<details>
<summary>Open Questions</summary>

- **\[non-blocking, owner: implementer\] `on_delete` on the group/criterion FKs.** Confirm the `on_delete` behavior \#613 assigns to `CompetencyCriterion.competency_criteria_group` and `CompetencyCriteriaGroup.parent` (`PROTECT` vs `CASCADE`). This ticket's hard-delete paths assume a direct `.delete()` at each level is safe once the code has already confirmed no rows or protecting status remain — but confirm against the landed model, since a `CASCADE` FK could make the manual per-level emptiness checks partly redundant (and a stray `PROTECT` could raise where this ticket expects a clean delete).  
- **\[non-blocking, owner: implementer\] Error convention.** Confirm what exception type/shape \#665's own validation raises (e.g. for its group/competency mismatch check), so this ticket's 404 paths surface errors the same way rather than introducing a second convention.

</details>
<details>
<summary>Context</summary>

- **\#665:** creates the `CompetencyCriterion` rows this ticket removes, and the `CompetencyCriterionSerializer` / `CompetencyCriterionCreateView` / `rest_api/v1/urls.py` this ticket extends. Its read-merge-write `ObjectTag` handling via `openedx_tagging.api.tag_object()` (`src/openedx_tagging/api.py:176-214, 325-429`) is the same mechanism this ticket reuses in reverse, to remove an `oel_tagging_objecttag` row once no `CompetencyCriterion` references it. \#665 also establishes the inline `has_perm("oel_tagging.can_tag_object", ObjectTagPermissionItem(...))` check inside its `api.py` function (not a DRF permission class) and the `openedx-platform` wiring (`INSTALLED_APPS`, `cms/urls.py`) this ticket's new route inherits without further changes (\#664's scope was eliminated by \#665's redesign).  
- **\#675:** the group-level counterpart (direct group deletion via the UI's trash affordance). It needs the same ancestor-cascade walk this ticket implements for its own case (deleting a group directly can empty that group's own parent); the two tickets will likely converge on the same internal helper once both exist.  
- **\#709 / \#710:** the frontend tickets ("delete a Competency Criteria Group" and "delete a Competency Criteria Association") that already assume this ticket (\#674) cascades an emptied group away server-side, and fall back to the existing placeholder rendering (\#671/\#672) when that empties a competency's last group.  
- **ADR 0002** (`docs/openedx_learning/decisions/0002-competency-criteria-model.rst`): empty-group rule (lines 107-113 — "backend validation must reject" persisted empty groups), Decision 4 field list (146-181), `StudentCompetencyCriteriaGroupStatus` (lines 244, 256, 284-290), Decision 7 delete protection including its explicit extension to `oel_tagging_objecttag` (lines 300-306), and the worked example showing one `ObjectTag` shared across multiple criteria (314-349).  
- **ADR 0003** (`docs/openedx_learning/decisions/0003-competency-criteria-versioning.rst`): simple-history on `CompetencyCriteriaGroup`/`CompetencyCriteria` (22-28); post-use archive rules and the in-use warning that Studio, not this endpoint, is responsible for surfacing (34-45).  
- Reused permission machinery: `oel_tagging.can_tag_object`, checked inline via `has_perm()` against an `ObjectTagPermissionItem`, the same composite (studio write access to the course plus taxonomy view access) \#665 relies on and `openedx-platform`'s `content_tagging/rules.py` registers globally; not a DRF permission class.
</details>
<details>
<summary>Technical Notes</summary>

### Files to Modify

| File | Nature |
| :---- | :---- |
| `src/openedx_learning/applets/cbe/api.py` | Add `delete_competency_criterion(criterion_id: int, user) -> CriterionDeletionResult`, plus an internal ancestor-cascade helper that walks `parent_id` deciding hard-delete vs. archive vs. stop at each level, and the `oel_tagging_objecttag` removal on the hard-delete path. |
| `src/openedx_learning/applets/cbe/rest_api/v1/serializers.py` | Add `archived` as a read-only field on `CompetencyCriterionSerializer`. |
| `src/openedx_learning/applets/cbe/rest_api/v1/views.py` | Add `CompetencyCriterionDeleteView(generics.GenericAPIView)`. |
| `src/openedx_learning/applets/cbe/rest_api/v1/urls.py` | Register `criteria-groups/<int:group_id>/criteria/<int:criterion_id>/`. |
| `src/openedx_learning/applets/cbe/rest_api/v1/tests/test_views.py` | Extend with removal / archive / cascade / idempotency / permission / 404 tests. |

### Implementation Notes

`delete_competency_criterion(criterion_id, user)` in `api.py`: resolve the `CompetencyCriterion` (raise `DoesNotExist` if missing). Resolve the course for the permission check from the criterion's own `ObjectTag.object_id`: parse it via `UsageKey.from_string`, then resolve the `CourseRun` via `openedx_catalog.api.get_course_run()`, exactly the same parse-and-resolve \#665 already does for creation. Build `ObjectTagPermissionItem(taxonomy=<the criterion's group's competency tag's taxonomy>, object_id=<that course's key as a string>)` and check `user.has_perm("oel_tagging.can_tag_object", ...)` inline, raising `PermissionDenied` on failure; this is the same inline check \#665 makes in `associate_competency_criterion()`, not a DRF permission class. Check `StudentCompetencyCriteriaStatus.objects.filter(competency_criteria_id=criterion_id).exists()`.

- If `False` (hard-delete path), inside one `transaction.atomic()` block: capture the criterion's `competency_criteria_group_id` and `oel_tagging_objecttag_id`, call `.delete()` on the criterion row, then:  
  - If no other `CompetencyCriterion` still references the same `oel_tagging_objecttag_id`, remove it via `openedx_tagging.api.tag_object()`'s read-merge-write (the taxonomy's current tag list for that object, minus this tag's value) — not `delete_object_tags()`, which removes every tag on the object across all taxonomies, and not a raw `.delete()`, which bypasses `tag_object()`'s validation.  
  - Call the ancestor-cascade helper on the criterion's former group, as a hard-delete event (see below).  
  - Return `CriterionDeletionResult(id=criterion_id, archived=False)`.  
- If `True` (archive path), set `archived=True`, save, then call the ancestor-cascade helper on the criterion's group, as an archive event. Never touch the `oel_tagging_objecttag`. Return `CriterionDeletionResult(id=criterion_id, archived=True)`.

Ancestor-cascade helper (walks `parent_id` upward one group at a time, stopping as soon as a level requires no change):

- **On an archive event** at group `G`: if `G` has any remaining non-archived child (criterion or child group), stop. Otherwise, set `G.archived = True`, save, and recurse on `G.parent` (if any) as an archive event.  
- **On a hard-delete event** at group `G`: if `G` has at least one non-archived child remaining, stop. If `G`'s only remaining children are archived, set `G.archived = True`, save, and recurse on `G.parent` as an archive event. If `G` has zero children left at all: check `StudentCompetencyCriteriaGroupStatus.objects.filter(competency_criteria_group_id=G.id).exists()` — if a row exists, archive `G` (same as above) and recurse as an archive event; otherwise `.delete()` `G` and recurse on `G.parent` (if any) as a hard-delete event.

`CompetencyCriterionDeleteView(generics.GenericAPIView)` at `DELETE /api/cbe/v1/criteria-groups/<int:group_id>/criteria/<int:criterion_id>/`: resolve the criterion scoped to `group_id` (`get_object_or_404(CompetencyCriterion, pk=criterion_id, competency_criteria_group_id=group_id)` — a mismatch between the URL's `group_id` and the criterion's actual group is a 404, not a 400, since it's a resource-identification failure, not a payload-validation one), then call `api.delete_competency_criterion(criterion_id, request.user)` and return `Response({"id": result.id, "archived": result.archived}, status=200)`. The view does not call `self.check_object_permissions()`: `oel_tagging.can_tag_object` is checked inline inside `delete_competency_criterion()`, the same pattern \#665 uses in `associate_competency_criterion()`, not a DRF permission class.

The lookup queryset used to find the criterion for this view deliberately does **not** filter `archived=False` — unlike the future read/list path, this endpoint must be able to find an already-archived row to make the idempotent-repeat-DELETE case work (return the same 200 rather than a 404).

The `DELETE` verb is used for both outcomes; the archive-vs-hard-delete choice is a server-side detail driven by learner-status presence, not something the client selects. A separate `PATCH .../archive/` action was considered and rejected, since the client has no reliable way to know in advance which action applies without racing the same check the server already has to do. The response is `200 OK` with a small body in both cases (not the DRF-default `204 No Content`) specifically so the archive/hard-delete distinction and the resource id are Postman-observable without a GET endpoint. The response body only ever reports the criterion's own `id`/`archived`; it does not report what happened to ancestor groups, since no ticket has yet defined a GET/list contract for groups this endpoint's caller could reconcile against (see \#665's own Open Questions precedent for "not built yet, don't invent it here").

Permission check: `oel_tagging.can_tag_object`, checked inline via `user.has_perm("oel_tagging.can_tag_object", ObjectTagPermissionItem(taxonomy=<the criterion's group's competency tag's taxonomy>, object_id=<course key resolved from the criterion's ObjectTag.object_id>))` inside `delete_competency_criterion()` — the same inline pattern \#665 uses in `associate_competency_criterion()`, not a DRF permission class. Resolve the course by parsing the criterion's `ObjectTag.object_id` via `UsageKey.from_string` and resolving the `CourseRun` via `openedx_catalog.api.get_course_run()`, exactly the same parse-and-resolve \#665 already does for creation.

No PII annotation work: `archived` is a non-personal authoring-metadata field, same category as `CompetencyRuleProfile.archived`.

Test strategy: unit tests for `delete_competency_criterion()` (hard-delete path, archive path, repeat-call-on-archived idempotency, shared-`ObjectTag` non-interference, orphaned-`ObjectTag` removal, `ObjectTag` preserved on archive) plus unit tests for the ancestor-cascade helper in isolation (single-level delete, single-level archive, multi-level delete propagation, multi-level archive propagation, stop-at-surviving-sibling, direct-group-status protection forcing archive over delete) plus DRF integration tests for the view (200 hard-delete, 200 archive, 200 idempotent repeat, 404 unknown id, 404 group/criterion mismatch, 403 without permission).

### Example Resolution Prompt

> Implement \#674: a `DELETE`\-only endpoint that removes a `CompetencyCriterion`, in `openedx-core`. Assume \#613 has landed `CompetencyCriteriaGroup`/`CompetencyCriterion`/`StudentCompetencyCriteriaGroupStatus` models, the archived-field ticket has landed `archived` on both `CompetencyCriteriaGroup` and `CompetencyCriterion`, and \#665 has landed `create_competency_criterion()`, `CompetencyCriterionSerializer`, `CompetencyCriterionCreateView`, and `rest_api/v1/urls.py` registering `criteria-groups/<int:group_id>/criteria/`.  
> 

> 1. In `src/openedx_learning/applets/cbe/api.py`, add `delete_competency_criterion(criterion_id: int, user)`. Resolve the `CompetencyCriterion` (let `DoesNotExist` propagate). Resolve the course by parsing the criterion's `ObjectTag.object_id` via `UsageKey.from_string` and resolving the `CourseRun` via `openedx_catalog.api.get_course_run()`, the same parse-and-resolve \#665 already does for creation; build `ObjectTagPermissionItem(taxonomy=<the criterion's group's competency tag's taxonomy>, object_id=<that course's key>)` and check `user.has_perm("oel_tagging.can_tag_object", ...)` inline, raising `PermissionDenied` on failure. If no `StudentCompetencyCriteriaStatus` row references `criterion_id`: inside `transaction.atomic()`, delete the criterion, remove its `oel_tagging_objecttag` via `openedx_tagging.api.tag_object()`'s read-merge-write if no other `CompetencyCriterion` still references it, then run the ancestor-cascade walk starting at the criterion's former group as a hard-delete event. Otherwise, set `archived = True`, save, touch neither the `ObjectTag` nor the group directly, and run the ancestor-cascade walk starting at the criterion's group as an archive event. The walk: on an archive event, if the current group has no non-archived children left, archive it and recurse upward as an archive event, else stop; on a hard-delete event, if the group has zero children left, archive it instead of deleting it when a `StudentCompetencyCriteriaGroupStatus` references it directly, else delete it and recurse upward as a hard-delete event; if the group's only remaining children are archived, archive it and recurse upward as an archive event; if it still has a non-archived child, stop. Return a small result carrying `id` and `archived` (the criterion's own values only).  
> 2. In `src/openedx_learning/applets/cbe/rest_api/v1/views.py`, add `CompetencyCriterionDeleteView(generics.GenericAPIView)`. Implement `delete()`: resolve the criterion via `get_object_or_404(CompetencyCriterion, pk=self.kwargs["criterion_id"], competency_criteria_group_id=self.kwargs["group_id"])` (this makes a group/criterion mismatch a 404), call `api.delete_competency_criterion(criterion_id, request.user)`, return `Response({"id": result.id, "archived": result.archived}, status=200)`. Do not call `self.check_object_permissions()`: `oel_tagging.can_tag_object` is checked inline inside `delete_competency_criterion()`, the same pattern \#665 uses in `associate_competency_criterion()`, not a DRF permission class.  
> 3. In `src/openedx_learning/applets/cbe/rest_api/v1/urls.py`, register `path("criteria-groups/<int:group_id>/criteria/<int:criterion_id>/", views.CompetencyCriterionDeleteView.as_view(), name="competency-criterion-delete")`.  
> 4. In `src/openedx_learning/applets/cbe/rest_api/v1/serializers.py`, add `archived` as a read-only field on `CompetencyCriterionSerializer` so it appears in the create endpoint's response too.

>   
> Return 200 with `{"id": ..., "archived": false}` on hard-delete, 200 with `{"id": ..., "archived": true}` on archive, 200 (same body) on a repeat call against an already-archived row, 404 if the criterion doesn't exist or doesn't belong to `group_id`, 403 if the caller lacks `oel_tagging.can_tag_object` (studio write access to the criterion's course plus taxonomy view access on the competency's taxonomy). The ancestor-cascade walk must run all the way to the root group, not just the immediate parent, stopping only once a level still has active content of its own.

</details>
