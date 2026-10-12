# [BE] Build endpoint for removing a Competency Criteria Group

GitHub: https://github.com/openedx/openedx-core/issues/675 (#675, OPEN)
Cached: 2026-09-21

**Blocked by:** \#613 (the CBE data model), \#665 (creates `CompetencyCriteriaGroup`/`CompetencyCriterion` rows — group creation happens implicitly via `resolve_or_create_leaf_group()`/`resolve_supplied_leaf_group()` as a side effect of criterion creation; there's no separate group-creation endpoint, \#664's scope was eliminated by \#665's redesign), \#674 (remove-criterion, whose ancestor-cascade helper this ticket reuses for the levels above the removed subtree), and the archived-field ticket (no GitHub issue yet — adds `archived` to both `CompetencyCriteriaGroup` and `CompetencyCriterion` in one migration, so this ticket and \#674 don't have to race to add it themselves).

Repo: `openedx-core`, single-repo. No `openedx-platform` changes — this ticket's route registers inside the same `rest_api/v1/urls.py` that \#665 wires into Studio.

## Use Case

As a Platform Administrator, I want to remove a Competency Criteria Group — including its descendant groups and all criteria beneath it — in one action, so that I can retire an entire branch of a competency's mastery rule without having to remove each nested criterion and group individually, while any learner progress already recorded anywhere in that branch is preserved rather than destroyed.

## Description

**Current state**

No endpoint exists today to remove a `CompetencyCriteriaGroup`. Per ADR 0002 Decision 2, a group can have child groups and leaf `CompetencyCriterion` rows nested beneath it to unbounded depth (current frontend authoring caps depth at 3, but the backend does not). Per Decision 7, hard delete of a `CompetencyCriteriaGroup` is allowed only while no learner status rows exist anywhere in the tree being removed; once any exist, retirement must be archive-only. The same protection extends to whatever ancestor groups already sit above the removed subtree, per \#674.

**Requested change**

A new endpoint, identified by the group and the competency (tag) it belongs to, that removes a `CompetencyCriteriaGroup` and everything beneath it:

- Resolves the target group from the URL (`competency_tag_id`, `group_id`); 404 if it doesn't exist, or exists but does not belong to the given `competency_tag_id`.  
- Rejects with a 400 if the resolved target group is a root group (`course_id` and `parent_id` both null): a root's subtree can span multiple course-level children in different courses, so there is no single course to check permission against, and one course's write access wouldn't justify deleting a different course's content under the same root anyway.  
- Walks the full subtree: the target group, every descendant `CompetencyCriteriaGroup` at any depth, and every `CompetencyCriterion` under any of those groups.  
- Checks whether **any** node in that subtree has a referencing learner-status row (`StudentCompetencyCriteriaGroupStatus` for a group node, `StudentCompetencyCriteriaStatus` for a criterion leaf).  
  - If none exists anywhere in the subtree: hard-deletes the entire subtree (all descendant criteria, then all descendant groups, then the target group) in one transaction.  
  - If any exists anywhere in the subtree: archives the entire subtree instead — every group and every criterion in it gets `archived=True` — in one transaction. The subtree is never partially hard-deleted and partially archived; a single status row anywhere in the branch retires the whole branch to archive-only, keeping the tree internally consistent.  
- On a hard-delete, also removes each `oel_tagging_objecttag` row the subtree's criteria pointed to, but only for an `ObjectTag` no `CompetencyCriterion` outside the subtree still references (same rule as \#674; the underlying `Tag` — the competency definition — is never touched, only the association). On an archive, no `ObjectTag` is touched at all, for the same ADR 0002 Decision 7 reason \#674 documents.  
- After the subtree is resolved, walks upward from the target group's own parent using \#674's ancestor-cascade logic, reused rather than reimplemented here: an archive event keeps archiving ancestors with no remaining non-archived children; a hard-delete event keeps deleting ancestors with no children left (archiving instead if one has its own `StudentCompetencyCriteriaGroupStatus`, or if its only remaining children are archived), stopping once a level still has active content. The response reports only the target subtree's own outcome (`id`, `archived`, cascade counts); it doesn't report what happened above the target, same as \#674.  
- Gates on `oel_tagging.can_tag_object`: studio write access to the target group's own course, plus taxonomy view access on the competency's taxonomy. Resolved from the target group itself: its own `course_id` if it's course-level, or `parent.course_id` if it's a leaf. One check suffices for the whole request; the reject-root-group rule above guarantees the target group resolves to exactly one course, the same course whose content this request deletes.  
- Is idempotent for an already-archived group: a repeat `DELETE` returns the same 200 result. A repeat `DELETE` on a hard-deleted (now-gone) group returns 404\.

**Explicitly out of scope**

- Removing a single `CompetencyCriterion` without removing its group (\#674).  
- Any check that an archived or hard-deleted group's id can no longer be reused or nested under by \#665's `resolve_or_create_leaf_group()`/`resolve_supplied_leaf_group()` — see Open Questions; a real gap the `archived` field creates but does not close.  
- Touching an `oel_tagging_objecttag` row still referenced by a `CompetencyCriterion` outside the removed subtree.  
- Listing or retrieving groups/criteria (a separate GET/list ticket).  
- Any UI, including the in-use warning/confirmation flow ADR 0003 Decision 4 requires in Studio.

## Acceptance Criteria

These scenarios are verifiable via Postman.

```
Scenario: Hard-delete a leaf group with no descendants and no learner status
  Given a CompetencyCriteriaGroup with no child groups and no criteria, no learner status referencing it, and a parent group with other active children
  And the requesting user has studio write access to the group's course and view access to the competency's taxonomy
  When a DELETE request is sent to the remove-group endpoint for that competency_tag_id and group_id
  Then the response returns status code 200
  And the response body includes "id" matching the group, "archived" as false, "cascaded_group_count" as 0, and "cascaded_criteria_count" as 0
  And a subsequent DELETE to the same URL returns status code 404

Scenario: Cascade hard-delete removes descendant groups and criteria
  Given a CompetencyCriteriaGroup has one child group, and that child group has two CompetencyCriterion rows, none referenced by any learner status
  When a DELETE request is sent to the remove-group endpoint for the parent group's id
  Then the response returns status code 200
  And the response body's "archived" is false, "cascaded_group_count" is 1, and "cascaded_criteria_count" is 2
  And a subsequent POST to the create-criteria endpoint targeting the deleted child group's id returns status code 404

Scenario: Archive instead of hard-delete when any node in the subtree has learner status
  Given a CompetencyCriteriaGroup has a child group with one CompetencyCriterion, and a StudentCompetencyCriteriaStatus row references that criterion
  When a DELETE request is sent to the remove-group endpoint for the parent group's id
  Then the response returns status code 200
  And the response body's "archived" is true
  And the parent group, the child group, and the criterion all still exist in the database with archived=true

Scenario: Repeat removal of an already-archived group is idempotent
  Given a CompetencyCriteriaGroup was previously archived via this endpoint
  When a DELETE request is sent again to the same group's URL
  Then the response returns status code 200
  And the response body is unchanged ("archived" still true)

Scenario: Hard-deleting a subtree removes a tagged object no longer referenced outside it
  Given a CompetencyCriteriaGroup subtree contains one CompetencyCriterion, its oel_tagging_objecttag is referenced by no CompetencyCriterion outside the subtree, and no learner status exists anywhere in the subtree
  When a DELETE request removes that group
  Then the response returns status code 200
  And the oel_tagging_objecttag row that criterion referenced no longer exists

Scenario: A tagged object shared outside the subtree survives a hard-delete
  Given a CompetencyCriteriaGroup subtree contains one CompetencyCriterion, and its oel_tagging_objecttag is also referenced by another CompetencyCriterion outside the subtree
  When a DELETE request hard-deletes that subtree
  Then the response returns status code 200
  And the oel_tagging_objecttag row still exists, and the criterion outside the subtree is unaffected

Scenario: Archiving a subtree never touches its tagged objects
  Given a CompetencyCriteriaGroup subtree has one CompetencyCriterion referenced by a StudentCompetencyCriteriaStatus row
  When a DELETE request removes that group
  Then the response returns status code 200
  And the oel_tagging_objecttag row that criterion references still exists

Scenario: Removing a subtree cascades upward through an empty ancestor
  Given a root CompetencyCriteriaGroup's only child is the target group, which has one CompetencyCriterion and no learner status anywhere in the subtree
  When a DELETE request removes the target group
  Then the response returns status code 200
  And the target group and its criterion no longer exist in the database
  And the root CompetencyCriteriaGroup row no longer exists in the database

Scenario: Cascade stops at an ancestor with a surviving sibling
  Given a root CompetencyCriteriaGroup has two child groups, the target group and a sibling group, and no learner status anywhere in the target's subtree
  When a DELETE request removes the target group
  Then the response returns status code 200
  And the target group no longer exists in the database
  And the root CompetencyCriteriaGroup row still exists in the database, since its sibling group is still active

Scenario: Archiving a subtree cascades an archive upward through an ancestor with no other active content
  Given a root CompetencyCriteriaGroup's only child is the target group, which has one CompetencyCriterion referenced by a StudentCompetencyCriteriaStatus row
  When a DELETE request removes the target group
  Then the response returns status code 200
  And the response body's "archived" is true
  And the target group's row still exists in the database with archived=true
  And the root CompetencyCriteriaGroup row still exists in the database with archived=true

Scenario: Reject a group that does not belong to the specified competency
  Given a CompetencyCriteriaGroup exists for competency A
  When a DELETE request is sent to the remove-group endpoint using competency B's tag id and competency A's group id
  Then the response returns status code 404

Scenario: Reject removal for a group that does not exist
  Given the referenced group id does not exist
  When a DELETE request is sent referencing that id
  Then the response returns status code 404

Scenario: Reject targeting a root group
  Given the supplied group_id resolves to a root group (course_id and parent_id both null)
  When a DELETE request is sent to the remove-group endpoint for that group_id
  Then the response returns status code 400
  And the response body identifies that root groups cannot be targeted directly
  And no group, criterion, or ObjectTag is deleted or archived

Scenario: Reject removal without permission
  Given the requesting user lacks studio write access to the group's course, or lacks view access to the competency's taxonomy
  When a DELETE request is sent to the remove-group endpoint
  Then the response returns status code 403
```

<details>
<summary>Open Questions</summary>

- **\[non-blocking, owner: implementer\] `on_delete` on the group/criterion FKs.** Confirm the `on_delete` behavior \#613 assigns to `CompetencyCriteriaGroup.parent` (self-FK) and `CompetencyCriterion.competency_criteria_group`. This ticket's hard-delete path assumes these are restrictive (e.g. `PROTECT`, not `CASCADE`) and that deletion order must therefore be explicit and bottom-up (criteria, then leaf groups, then the target group, then \#674's ancestor-cascade walk above it) inside one transaction, rather than relying on the ORM to cascade. Confirm against the landed model before implementing.  
- **\[non-blocking, owner: architect/reviewer\] Creating against an archived branch.** Once `archived` exists, \#665's `resolve_or_create_leaf_group()`/`resolve_supplied_leaf_group()` have no check preventing new authoring against an already-archived branch (deriving into, or explicitly targeting, an archived group). Not built by this ticket — it only removes/archives — but worth a small follow-up so "archived" actually means "hidden from new associations," the way ADR 0002 Decision 3 already promises for `CompetencyRuleProfile`.
</details>
<details>
<summary>Context</summary>

- **\#665:** creates the `CompetencyCriteriaGroup` and `CompetencyCriterion` rows this ticket removes. Group creation happens implicitly, via `resolve_or_create_leaf_group()`/`resolve_supplied_leaf_group()`, as a side effect of criterion creation; there's no standalone group-creation endpoint (\#664's scope was eliminated by \#665's redesign). Establishes that one `CompetencyCriteriaGroup` tree covers exactly one competency tag — the reason this ticket can resolve the owning taxonomy from any node in the subtree unambiguously.  
- **\#674:** the criterion-level counterpart. Shares the archive-vs-hard-delete branch and the ancestor-cascade-walk helper this ticket reuses for the levels above the target group. Read it first if implementing this standalone, since the per-row archive mechanism and the walk are identical, just applied to a subtree here instead of to one row.  
- **Archived-field ticket (no GitHub issue yet):** adds `archived` to both models in one migration, ahead of both this ticket and \#674, so neither has to add it itself.  
- **ADR 0002** (`docs/openedx_learning/decisions/0002-competency-criteria-model.rst`): Decision 2, group/child structure and empty-group rule (68-113); Decision 7, delete protection and archive-only mandate, explicitly naming `CompetencyCriteriaGroup`, `CompetencyCriteria`, and `oel_tagging_objecttag` (300-306).  
- **ADR 0003** (`docs/openedx_learning/decisions/0003-competency-criteria-versioning.rst`): simple-history on these models (22-28); the in-use warning Studio must show, not built here (40-45).  
- Reused permission machinery: `oel_tagging.can_tag_object` (studio write access to a course, plus taxonomy view access), checked via an inline `has_perm()` call in the api function rather than a DRF permission class. See \#665's `associate_competency_criterion()` for the `ObjectTagPermissionItem` pattern this reuses.
</details>
<details>
<summary>Technical Notes</summary>

### Files to Modify

| File | Nature |
| :---- | :---- |
| `src/openedx_learning/applets/cbe/api.py` | Add `delete_competency_criteria_group(group_id: int) -> GroupDeletionResult`, reusing \#674's ancestor-cascade helper for the levels above the target group. |
| `src/openedx_learning/applets/cbe/rest_api/v1/views.py` | Add `CompetencyCriteriaGroupDeleteView(generics.GenericAPIView)`. |
| `src/openedx_learning/applets/cbe/rest_api/v1/urls.py` | Register `competencies/<int:competency_tag_id>/criteria-groups/<int:group_id>/`. |
| `src/openedx_learning/applets/cbe/rest_api/v1/tests/test_views.py` | Extend with cascade / archive / idempotency / permission / 404 tests. |

### Implementation Notes

`delete_competency_criteria_group(group_id, *, user)` in `api.py`, inside `transaction.atomic()`:

1. Resolve the target group (raise `DoesNotExist` if missing).  
2. Reject with a 400 if the target group is a root (`parent_id` and `course_id` both null): root groups cannot be targeted directly, per the Requested change section above. This runs before the permission check and before any other validation or DB write, since a root group has no single course to resolve for that check.  
3. Resolve the course to check permission against: the target group's own `course_id` if it's course-level, else `target_group.parent.course_id` if it's a leaf (guaranteed to be one of these two shapes by step 2). Check `oel_tagging.can_tag_object` via an inline `user.has_perm("oel_tagging.can_tag_object", ObjectTagPermissionItem(taxonomy=<the competency's taxonomy>, object_id=<that course's key as a string>))` call; raise `PermissionDenied` on failure, matching \#665's `associate_competency_criterion()` pattern rather than a DRF permission class.  
4. Walk descendant groups breadth-first in Python (`CompetencyCriteriaGroup.objects.filter(parent_id__in=level_ids)`, looping level by level until a level returns empty) to collect the full set of descendant group ids — no raw recursive SQL, since Django's ORM has no first-class recursive-CTE support and this keeps the query portable across the project's supported backends. Include the target group's own id in the final set.  
5. Collect all `CompetencyCriterion` ids under that full group-id set, along with the distinct `oel_tagging_objecttag_id` values they reference.  
6. Check `StudentCompetencyCriteriaGroupStatus.objects.filter(competency_criteria_group_id__in=all_group_ids).exists() or StudentCompetencyCriteriaStatus.objects.filter(competency_criteria_id__in=all_criterion_ids).exists()`.  
7. If `False`: delete all `CompetencyCriterion` rows in the set, then, for each distinct `oel_tagging_objecttag_id` those criteria referenced, remove it via `openedx_tagging.api.tag_object()`'s read-merge-write if no `CompetencyCriterion` outside the subtree still references it, then delete all descendant `CompetencyCriteriaGroup` rows, then the target group itself — in that bottom-up order, regardless of the FKs' actual `on_delete` setting (see Open Questions).  
8. If `True`: set `archived=True` and bulk-save on every `CompetencyCriterion` and every `CompetencyCriteriaGroup` in the set (including the target group) — the whole subtree archives together, never a partial mix. No `ObjectTag` is touched on this path.  
9. Call \#674's ancestor-cascade helper on the target group's own parent (if any), as a hard-delete event if step 7 ran or an archive event if step 8 ran.  
10. Return `GroupDeletionResult(id=group_id, archived=<bool>, cascaded_group_count=<descendant group count, excluding the target>, cascaded_criteria_count=<criterion count>)` — scoped to the target subtree only; the ancestor walk's effects aren't reported.

`CompetencyCriteriaGroupDeleteView(generics.GenericAPIView)` at `DELETE /api/cbe/v1/competencies/<int:competency_tag_id>/criteria-groups/<int:group_id>/`: resolve the group scoped to `competency_tag_id` (`get_object_or_404(CompetencyCriteriaGroup, pk=group_id, oel_tagging_tag_id=competency_tag_id)` — a mismatch is 404, same convention as \#674), call `api.delete_competency_criteria_group(group_id, user=request.user)`, return `Response({"id": ..., "archived": ..., "cascaded_group_count": ..., "cascaded_criteria_count": ...}, status=200)`. The root-group rejection and the `oel_tagging.can_tag_object` permission check both happen inside `delete_competency_criteria_group()`, not in the view, per \#665's pattern.

As in \#674: `DELETE` is used for both outcomes (no separate `PATCH .../archive/` action — same rejected-alternative reasoning), and the response is `200 OK` with a body in both cases so the cascade counts and archive/hard-delete outcome are Postman-observable without a GET endpoint. The lookup queryset for this view does not filter `archived=False`, for the same idempotent-repeat-DELETE reason as \#674.

Permissions: not a DRF permission class. `oel_tagging.can_tag_object`, checked inline inside `delete_competency_criteria_group()` (studio write access to the target group's own course, plus taxonomy view access on the competency's taxonomy), the same mechanism \#665's `associate_competency_criterion()` uses.

No PII annotation work: `archived` is non-personal authoring metadata.

Test strategy: unit tests for `delete_competency_criteria_group()` (leaf-group hard-delete, multi-level cascade hard-delete, archive-on-any-status-anywhere-in-subtree including a status buried at a grandchild criterion, repeat-call idempotency, correct `cascaded_*_count` values, orphaned-`ObjectTag` removal, shared-`ObjectTag` survival, `ObjectTag` preserved on archive, ancestor-cascade propagation on both hard-delete and archive, cascade-stops-at-surviving-sibling, a root group rejected with 400 before any permission check or write, the permission-check course correctly resolved from both a course-level target group's own `course_id` and a leaf target group's `parent.course_id`) plus DRF integration tests (200 hard-delete, 200 cascade hard-delete, 200 archive, 200 idempotent repeat, 404 unknown/mismatched id, 400 root-group target, 403 without permission).

### Example Resolution Prompt

> Implement \#675: a `DELETE`\-only endpoint that removes a `CompetencyCriteriaGroup` and its full descendant subtree (child groups and criteria), in `openedx-core`. Assume \#613 has landed the models, the archived-field ticket has landed `archived` on both `CompetencyCriteriaGroup` and `CompetencyCriterion`, \#665 has landed `associate_competency_criterion()` (which resolves or creates the group hierarchy internally — there's no standalone group-creation endpoint) and `rest_api/v1/urls.py` registering `competencies/<int:tag_id>/criteria/`, and \#674 has landed its ancestor-cascade helper this ticket reuses for the levels above the target group.  
> 

> 1. In `src/openedx_learning/applets/cbe/api.py`, add `delete_competency_criteria_group(group_id: int, *, user)` wrapped in `transaction.atomic()`. Resolve the target group (let `DoesNotExist` propagate). Reject with a 400 if the target group is a root (`parent_id` and `course_id` both null) before doing anything else. Resolve the course to check permission against (the target group's own `course_id` if course-level, else `parent.course_id` if a leaf) and check `oel_tagging.can_tag_object` via an inline `user.has_perm(...)` call, matching \#665's `associate_competency_criterion()` pattern rather than a DRF permission class; raise `PermissionDenied` on failure. Then walk descendant groups breadth-first via repeated `CompetencyCriteriaGroup.objects.filter(parent_id__in=...)` queries (no raw recursive SQL) to build the full set of group ids in the subtree, including the target. Collect all `CompetencyCriterion` ids under that set, and the distinct `oel_tagging_objecttag_id` values they reference. Check for any `StudentCompetencyCriteriaGroupStatus` row on any group in the set or any `StudentCompetencyCriteriaStatus` row on any criterion in the set. If none: delete the criteria; for each distinct `oel_tagging_objecttag_id`, remove it via `openedx_tagging.api.tag_object()`'s read-merge-write if no `CompetencyCriterion` outside the subtree still references it; then delete the descendant groups, then the target group, bottom-up. If any exist: archive every group and criterion in the set instead (never touching any `ObjectTag`). Either way, call \#674's ancestor-cascade helper on the target group's former parent, as a hard-delete event or an archive event to match. Return an object/dict with `id`, `archived`, `cascaded_group_count` (descendants excluding the target), `cascaded_criteria_count` — scoped to the subtree only.  
> 2. In `src/openedx_learning/applets/cbe/rest_api/v1/views.py`, add `CompetencyCriteriaGroupDeleteView(generics.GenericAPIView)`. Implement `delete()`: resolve via `get_object_or_404(CompetencyCriteriaGroup, pk=self.kwargs["group_id"], oel_tagging_tag_id=self.kwargs["competency_tag_id"])`, call `api.delete_competency_criteria_group(group_id, user=request.user)`, return `Response({"id": result.id, "archived": result.archived, "cascaded_group_count": result.cascaded_group_count, "cascaded_criteria_count": result.cascaded_criteria_count}, status=200)`. No permission class on the view: the root-group rejection and the `oel_tagging.can_tag_object` check both happen inside `delete_competency_criteria_group()`.  
> 3. In `src/openedx_learning/applets/cbe/rest_api/v1/urls.py`, register `path("competencies/<int:competency_tag_id>/criteria-groups/<int:group_id>/", views.CompetencyCriteriaGroupDeleteView.as_view(), name="competency-criteria-group-delete")`.

>   
> Return 200 with `{"id", "archived": false, "cascaded_group_count", "cascaded_criteria_count"}` on hard-delete, 200 with `"archived": true` (same shape) when any status exists anywhere in the subtree, 200 (unchanged body) on a repeat call against an already-archived group, 404 if the group doesn't exist or doesn't belong to `competency_tag_id`, 400 if the target group resolves to a root group, 403 if the caller lacks `oel_tagging.can_tag_object`. The archive/hard-delete decision must be all-or-nothing across the whole subtree in one transaction, and the ancestor-cascade walk above the target group must run using \#674's same logic.

</details>
