# [BE] Update/Edit Competency Criteria Group

GitHub: https://github.com/openedx/openedx-core/issues/760 (#760, OPEN)
Cached: 2026-09-21

## User Story

As a Platform Administrator, I want to change how a Competency Criteria Group combines the criteria and groups beneath it, in order to correct the logic of a mastery rule without removing the whole branch and rebuilding everything under it.

## Acceptance Criteria

Every outcome below is observable in the response to the update itself, in the learner status tables, or in the group's change history.

```
# Changing how a group combines its children

Scenario: Change a group from requiring all of its children to requiring any one
  Given a Competency Criteria Group that requires all of its children
  And the requesting user has studio write access to the group's course and view access to the competency's taxonomy
  When the user updates the group to require any one of its children
  Then the update succeeds
  And the response reports the group as requiring any one of its children

Scenario: Change a group from requiring any one of its children to requiring all of them
  Given a Competency Criteria Group that requires any one of its children
  When the user updates the group to require all of its children
  Then the update succeeds
  And the response reports the group as requiring all of its children

# Rejecting a request the system cannot store

Scenario: Reject a way of combining children that the system cannot store
  Given a Competency Criteria Group
  When the user submits an update that names no way of combining the group's children, or names one the system does not support
  Then the update is rejected
  And the group still combines its children the same way as before the request

# Leaving alone what this endpoint does not change

Scenario: An update leaves everything else about the group and its branch untouched
  Given a Competency Criteria Group with a name, a competency, a course scope, and a position in its tree
  When the user updates how the group combines its children
  Then the update succeeds
  And the response reports the group's name, competency, course scope, and position in its tree unchanged
  And every group and criterion beneath it is unchanged

Scenario: Reject an update that would change anything other than how the group combines its children
  Given a Competency Criteria Group
  When the user submits an update that would change the group's name, its evaluation order among its siblings, its competency, its course scope, or its parent
  Then the update is rejected
  And the response names the attribute that may not be changed
  And the group is unchanged

Scenario: Accept an update that repeats attributes it may not change, when their values match
  Given a Competency Criteria Group
  When the user submits an update that restates the group's name and competency, matching what is stored, alongside a new way of combining its children
  Then the update succeeds
  And the response reports the new way of combining its children

Scenario: An update that changes nothing leaves no audit entry
  Given a Competency Criteria Group
  When the user submits an update carrying the way of combining children that the group already has
  Then the update succeeds
  And no new entry is added to the group's change history

# Requests that address nothing, or come from someone who may not make them

Scenario: Reject an update to an archived group
  Given a Competency Criteria Group that has been archived
  When the user submits an update to it
  Then the update is refused as conflicting with the group's current state
  And the group remains archived and otherwise unchanged

Scenario: Reject an update addressing a group under the wrong competency
  Given a Competency Criteria Group that belongs to one competency
  When the user submits an update addressing that group as though it belonged to a different competency
  Then the request is treated as addressing something that does not exist
  And no group is changed

Scenario: Reject an update to a group that does not exist
  Given no Competency Criteria Group exists for the identifier in the request
  When the user submits an update for it
  Then the request is treated as addressing something that does not exist
  And nothing is changed

Scenario: Reject targeting a root group
  Given the supplied group_id resolves to a root group (course_id and parent_id both null)
  When a PATCH request supplies that group_id
  Then the response returns status code 400
  And the response body identifies that root groups cannot be targeted directly
  And the group is unchanged

Scenario: Reject an update from a user without permission
  Given a user who lacks studio write access to the group's course, or lacks view access to the competency's taxonomy
  When that user submits an update to the group
  Then the request is refused
  And the group is unchanged
```

## Description

A Competency Criteria Group can be created (\#664) and archived together with everything beneath it (\#675), but not changed once it exists. Correcting a group that combines its children the wrong way therefore means removing the whole branch and rebuilding every group and criterion under it. Where learners already have progress in that branch, \#675 archives the branch rather than deleting it, so the rebuild leaves their recorded progress attached to archived rows.

This ticket makes exactly one thing editable in place: how the group combines the criteria and groups beneath it. The rule an individual criterion is evaluated by is edited on that criterion (\#759), not here.

<details>
<summary>Technical Details</summary>

This section is background and a suggested approach, not the source of truth. The User Story and Acceptance Criteria define what must be true when the work is done; the notes below exist to save the implementer some thinking.

### In short

**What an author edits.** One field: the AND/OR operator that decides how the group combines its children. That operator is the substance of a criteria group, and changing it changes how mastery is computed for every learner evaluated from that point forward.

**Archiving is the only state that stops an edit.** A group archived by \#675 is not editable at all, and no confirmation can override that.

**Where the logic lives, and how the audit trail stays honest.** The endpoint is a thin adapter: resolve the group from the URL, check permissions, validate the request's shape, delegate to a function in the applet's `api.py`, serialize the result. Keeping the refusals and the audit attribution in the api function means an in-process Studio caller behaves identically to an HTTP one. ADR 0003 Decision 1 puts `django-simple-history` on this model, so an edit that changes nothing must not save at all, or the history fills with entries that record no change.

### Implementation specifics

- **Endpoint.** `PATCH /cbe/rest_api/v1/competencies/<int:competency_tag_id>/criteria-groups/<int:group_id>/`. DRF routes methods on one view class per path, so add a `patch()` method to the class \#675 registers at that detail path rather than a second class, renaming it to `CompetencyCriteriaGroupDetailView` if it landed as `CompetencyCriteriaGroupDeleteView`; if \#675 has not landed, register the detail route here and let \#675 add `delete()` to this class. Set `http_method_names` so `PUT` is not offered. Resolve the group with `get_object_or_404(..., pk=group_id, oel_tagging_tag_id=competency_tag_id)`, matching \#675's convention. The create route (`competency-criteria-group-create`, `CompetencyCriteriaGroupCreateView`) is on the collection path and is untouched.  
- **Api function.** `update_competency_criteria_group(group_id: int, *, logic_operator: str, user) -> CompetencyCriteriaGroup` in `src/openedx_learning/applets/cbe/api.py`, added to that module's `__all__`. The umbrella `src/openedx_learning/api.py` re-exports by wildcard, so it needs no edit. `logic_operator` is a required keyword because it is the only editable field, so there is no partial-update case to model.  
- **Accepted body.** `logic_operator`, required. For `name`, `ordering`, `parent_id`, `course_id`, `oel_tagging_tag_id`, and `archived`: when one is present and its value matches what is stored, ignore it so a read-modify-write client can send the whole object back; when it differs, reject and name the field, rather than silently ignoring a failed authoring intent. Reject unrecognized keys.  
- **Field validation.** Accept only the model's `AND` and `OR` values, and not null, derived from the model field's `choices` so the check comes from one place. \#664 describes `logic_operator` as both required and defaulting to `OR` without reconciling the two; this endpoint requires an explicit `AND` or `OR` either way, so it does not depend on how that is resolved. Do not validate the group's child count: setting the operator on a group with no children or one child is accepted. Studio's authoring flow does not call this endpoint before a group has its first child, though; the operator choice on a still-childless group is held client-side and flows through the child's create request instead.  
- **Check order.** Resolve the group; reject if it resolves to a root group (`course_id` and `parent_id` both null); check permissions; validate the request's shape; refuse an archived group; detect a no-op and return success without saving; save. The root-group check runs before the permission check because it doesn't depend on the caller's identity and, unlike a course-scoped group, a root group has no single course to check permission against in the first place. Archiving precedes the no-op check because an archived row is not editable at all and a success response would imply the edit was accepted.  
- **Status codes.** 400 means the request is malformed or self-contradictory. 409 means the request is well formed but the state of the group blocks it.

| Code | When |
| :---- | :---- |
| 200 | The operator changed, or the request was a no-op. Body is the group representation from `CompetencyCriteriaGroupSerializer`, echoing `logic_operator`. |
| 400 | `logic_operator` missing, null, or not `AND`/`OR`; an unrecognized key; an attempt to change a field that is not editable; or the supplied `group_id` resolves to a root group. |
| 403 | The user lacks `oel_tagging.can_tag_object` (studio write access to the group's course, plus taxonomy view access on the competency's taxonomy). |
| 404 | No group for that id, or the group does not belong to the URL's `competency_tag_id`. |
| 405 | `PUT`. |
| 409 | The group is archived. |

- **Single atomic write.** Inside `transaction.atomic()`, one `.save(update_fields=["logic_operator"])`. Do not use `queryset.update()`: it does not fire `post_save` and would write no history row.  
- **History attribution.** Set `instance._history_user` from the `user` argument before saving, so attribution does not depend on the consumer installing `simple_history.middleware.HistoryRequestMiddleware`. No model in this repo uses `HistoricalRecords()` yet, so this establishes the convention rather than following one; `django-simple-history` is already a declared dependency in `requirements/base.txt`.  
- **No learner status read or write.** Do not create, update, or delete any `StudentCompetency*Status` row on any path, and do not query them either. There is no in-use check in this ticket.  
- **Permissions.** Gate on `oel_tagging.can_tag_object`, not `can_change_taxonomy`: studio write access to the group's course, plus taxonomy view access on the competency's taxonomy. This is not a DRF permission class; it's an inline `user.has_perm("oel_tagging.can_tag_object", ObjectTagPermissionItem(taxonomy=tag.taxonomy, object_id=<course key>))` call inside the api function, the same mechanism \#665's `associate_competency_criterion()` uses. Resolve which course to check against from the target group: if it's course-level (`course_id` set), use it directly; if it's a leaf (`course_id` null, has a parent), use `group.parent.course_id`. The reject-root-group check below runs first and guarantees the group is one of these two shapes, so exactly one course is always found.  
- **Reject root groups.** Before the permission check, and before any other validation or DB write: if `group.parent_id is None and group.course_id is None`, the group is a root, and the request is rejected with a 400 identifying that root groups cannot be targeted directly. A root's subtree can span multiple course-level children in different courses, so there is no single course to resolve for the permission check above.  
- **No migration, no new model, no new field.** This ticket depends on \#716 for `archived` (a boolean field) on this model, and on \#613 for the models. Confirm \#613 before implementing rather than assuming.  
- **Layering.** Lives in `src/openedx_learning/applets/cbe/`, imports only from `openedx_tagging` and Django or DRF, and adds no import beyond what \#664 establishes. `openedx_learning` is not yet among `.importlinter`'s root packages; adding it belongs to \#613.  
- **Out of scope.**  
  - Removing or archiving a group or its subtree, including setting `archived` (\#675).  
  - Updating a criterion's rule source (\#759).  
  - Renaming a group, which has no authoring control yet (\#671).  
  - Setting the sibling sequence number, which has no defined semantics and no consumer.  
  - Re-parenting a group. No frontend ticket asks for it, so no companion ticket is proposed until one does.  
  - Changing `course_id` or `oel_tagging_tag_id`, which are fixed at creation.  
  - Cascading a rule onto every criterion under the group, which is a multi-row write with no authoring control yet and no column on a criteria group to drive it.  
  - Guarding against empty groups: creation and deletion are responsible for that, and this ticket never changes group membership.  
  - Reporting on a read path whether a group is in use (\#685).  
  - Checking whether a learner has a recorded status for the group or anything beneath it, and any confirmation or warning workflow for it. Owned by \#723 (Epic 10).  
- **Tests.** One test per Acceptance Criteria scenario, plus the cases the scenarios do not reach. In `tests/openedx_learning/applets/cbe/test_api.py`: exactly one history row per real edit, and none for a no-op; an archived group refused even when the request is otherwise a no-op, which is what pins the check order; a root group rejected with 400 before any permission check or write; the permission-check course correctly resolved from both a course-level group's own `course_id` and a leaf group's `parent.course_id`; the operator accepted on a group with exactly one child; no `StudentCompetency*Status` row created, updated, or deleted, and none queried, on any path; the group's sequence number and parent unchanged by every path. In `tests/openedx_learning/applets/cbe/test_views.py`: one test per row of the status-code table above, including a body changing `name`, `parent_id`, or `course_id`.

Files to create and modify **Modified files**

| File | Nature of modification |
| :---- | :---- |
| src/openedx\_learning/applets/cbe/api.py | add `update_competency_criteria_group()` and list it in `__all__` |
| src/openedx\_learning/applets/cbe/rest\_api/v1/serializers.py | add the update request-body serializer |
| src/openedx\_learning/applets/cbe/rest\_api/v1/views.py | add `patch()` to the group detail view and restrict `http_method_names` |
| src/openedx\_learning/applets/cbe/rest\_api/v1/urls.py | register the group detail route if \#675 has not already |
| tests/openedx\_learning/applets/cbe/test\_api.py | api-level tests |
| tests/openedx\_learning/applets/cbe/test\_views.py | endpoint-level tests |

- Context ADR 0002, `docs/openedx_learning/decisions/0002-competency-criteria-model.rst`: Decision 2 for the group's fields, the empty-group rule, the sibling-ordering purpose of the sequence number, and the course-run date windowing that the course scope drives; Decision 3 for the precedent that a row's scope fields are immutable after creation.  
- ADR 0003, `docs/openedx_learning/decisions/0003-competency-criteria-versioning.rst`: Decision 1 for `django-simple-history` on this model; Decision 4 for the warning-and-confirmation workflow, which \#723 (Epic 10\) implements in front of this endpoint rather than this endpoint itself; Decision 5 for learner status tables being append-only.  
- Prior art for the thin-view-plus-api-function shape and the error translation this ticket follows: `src/openedx_tagging/rest_api/v1/views.py` (`TaxonomyTagsView.update`) and `src/openedx_tagging/api.py` (`update_tag_in_taxonomy`).  
- Permission machinery: `oel_tagging.can_tag_object` (studio write access to a course, plus taxonomy view access), checked via an inline `has_perm()` call in the api function rather than a DRF permission class. See \#665's `associate_competency_criterion()` for the `ObjectTagPermissionItem` pattern this reuses.  
- The applet-api convention this function is published through: `docs/openedx_content/decisions/0010-merge-authoring-apps-into-openedx-content.rst`, with `src/openedx_content/api.py` as the working example.  
- Related work: \#613 (data model); \#664 (creates groups and the REST scaffolding this extends); \#671 (the frontend counterpart that requires an editable operator and states the group name is system-managed); \#675 (removes a group and its subtree and owns `archived` as an archiving action); \#681 and \#685 (read endpoints); \#716 (the `archived` field); \#723 (the guardrails these confirmations serve); \#759 (the criterion-level update sibling).

</details>
