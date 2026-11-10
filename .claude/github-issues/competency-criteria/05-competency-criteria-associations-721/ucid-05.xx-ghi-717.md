# [BE] Enforce archived in Competency Criteria creation

GitHub: https://github.com/openedx/openedx-core/issues/717 (#717, OPEN)
Cached: 2026-11-10

**Blocked by:** \#665.

**Repo:** `openedx-core`, single-repo. No `openedx-platform` changes: no new endpoint, this only adds validation inside \#665's existing create-criterion flow.

## Use Case

As a course author adding content to a competency's rules:
- I want to be stopped if I try to add content to a course whose competency rules were archived, so that archived rules stay archived.
- I want to be able to add content from another course to a competency after every earlier course's rules under it were archived, so that archiving the last course never locks the whole competency against other courses.

## Description

This ticket makes `archived` mean what ADR 0002 promises for new Competency Criteria authoring: \#665's group-resolution functions must reject creating against an archived course-level group or leaf, and reactivate an archived root instead of rejecting it. The duplicate-association check already treats an archived criterion as blocking, and this ticket keeps that, adding only a rejection message that says so.

**Current state**

Once \#716 adds `archived` to `CompetencyCriteriaGroup`/`CompetencyCriterion`, a branch or a criterion can be permanently archived (cascade-archived, or archived directly) when a learner-status row blocks hard deletion. ADR 0002 Decision 7 names `CompetencyCriteriaGroup` and `CompetencyCriteria` directly among the models whose archiving "may be archive-only (hidden from authoring and new associations)", the same guarantee Decision 3 already gives `CompetencyRuleProfile.archived`. \#665 predates `archived` and gets that guarantee wrong for groups:

- `resolve_supplied_leaf_group()` validates only that the supplied `group_id` names a leaf belonging to the right tag and course; `resolve_or_create_leaf_group()`'s `get_or_create()` calls for the root and course-level groups return an existing row regardless of its `archived` state. An author can explicitly target an archived leaf, or unknowingly derive into and grow an archived root or course-level branch.  
- The duplicate-association check rejects a `(tag_id, object_id)` pairing when a `CompetencyCriterion` in the target group (or, with no `group_id`, anywhere under the competency) references the existing `ObjectTag`, active or archived. An archived criterion's `ObjectTag` is deliberately preserved (per \#674's ADR 0002 Decision 7 protection, so its history stays resolvable), so an archived criterion keeps blocking a new one for the same content in the same group. That block is intended and stays (see Explicitly out of scope). The gap is only that the rejection reads like an active duplicate, while the author sees no such content in that group.

**Requested change**

- `resolve_supplied_leaf_group()` rejects with a 400 when the resolved leaf is archived.  
- `resolve_or_create_leaf_group()` reactivates the root group it would reuse when that root is archived (sets `archived=False`), then continues resolving the course-level group under it. The root is archived only when every course-level group under it is archived (\#674/\#675's upward cascade), so without this, archiving the competency's last course would lock the whole competency against new criteria. Reactivating the root does not touch any of its archived children.  
- `resolve_or_create_leaf_group()` rejects with a 400 when the course-level group it would reuse is archived. It does not fall back to creating a fresh course-level group: hitting an archived course-level group is always a rejection, never a silent substitution.  
- The derive path's leaf creation needs no new check: a leaf is always freshly created there, never reused, so it's never already archived.  
- The duplicate-association check keeps counting archived criteria. When the criterion that blocks the request is archived, the rejection says the content was previously associated with this competency in this group and archived, instead of the plain duplicate message.  
- Every rejection this ticket adds returns a message distinguishable from \#665's other 400 causes (non-leaf, competency mismatch, course mismatch, duplicate association), not just "some validation failed."

**Explicitly out of scope**

- Reactivating (unarchiving) an archived course-level group, leaf, or criterion. Archiving is one-directional for everything below the root; once a course-level group is archived, new criteria for that course under this competency are rejected. Accepted as permanent for MVP, matching `CompetencyRuleProfile`'s own archive-only, no-unarchive precedent. The root is the one exception, reactivated as described above. This covers the one-course case too: when a competency's only course loses its last criterion to an archive cascade, that course-level group is archived with it, and content from that course is rejected from then on, even though content from a different course reactivates the root.  
- Letting an archived criterion stop counting as a duplicate. An archived criterion keeps blocking a new association for the same content in the same group (and, on the derive path, anywhere under the competency), the same permanence ADR 0002 gives every archived row below the root. Learners keep every status they already hold either way. An author who removed content by mistake can add it to a different group, which \#665 already allows as a deliberate second association. Keeping at most one criterion row per content per group, archived or not, also leaves the data ready if unarchival is added after MVP.  
- Any change to \#665's `UniqueConstraint`s. This ticket assumes they stand as defined.  
- Rejecting a `group_id` that doesn't exist or was hard-deleted: already a 404 via \#665's existing `get_object_or_404`, unaffected by this ticket.  
- Surfacing archived state on any GET/list endpoint. \#681's GET excludes archived rows, and reporting which courses have an archived course-level group is 10.22, a separate ticket under epic \#723 with no GitHub issue yet. This ticket only changes create-time behavior.

## Acceptance Criteria

These scenarios are verifiable via Postman.

```
Scenario: Reject supplied-group creation targeting an archived leaf
  Given a leaf CompetencyCriteriaGroup exists for a competency and course, with archived=true
  And the requesting user has studio write access to the subsection's course and view access to the competency's taxonomy
  When a POST request to the create-criterion endpoint supplies that leaf's group_id together with a matching object_id
  Then the response returns status code 400
  And the response body identifies the group as archived and no longer eligible for new associations
  And no CompetencyCriterion is created

Scenario: Derive-path creation reactivates an archived root group
  Given a competency's root CompetencyCriteriaGroup exists with archived=true, and its only course-level group, for Course X, is archived=true
  When a POST request to the create-criterion endpoint for that competency supplies an object_id whose parsed course is Course Y, and no group_id
  Then the response returns status code 201
  And the root CompetencyCriteriaGroup now has archived=false, and no second root was created
  And a new course-level CompetencyCriteriaGroup is created for Course Y under that root, with a new leaf CompetencyCriteriaGroup and CompetencyCriterion under it
  And the course-level group for Course X is still archived=true

Scenario: An archived course-level group is rejected even when its root would have been reactivated
  Given a competency's root CompetencyCriteriaGroup and its only course-level group, for Course X, are both archived=true
  When a POST request to the create-criterion endpoint for that competency supplies an object_id whose parsed course is Course X, and no group_id
  Then the response returns status code 400
  And the response body identifies the course-level branch as archived
  And the root CompetencyCriteriaGroup is still archived=true, since the transaction rolled back
  And no new CompetencyCriteriaGroup or CompetencyCriterion rows are created

Scenario: Reject derive-path creation when the course-level group for the target course is archived
  Given a competency's root group is active (archived=false), but its course-level group for Course X is archived=true
  When a POST request to the create-criterion endpoint for that competency supplies an object_id whose parsed course is Course X, and no group_id
  Then the response returns status code 400
  And the response body identifies the course-level branch as archived
  And no new CompetencyCriteriaGroup or CompetencyCriterion rows are created

Scenario: Derive-path creation still succeeds for a different, non-archived course under the same competency
  Given a competency's root group is active, its course-level group for Course X is archived=true, and it has no existing group for Course Y
  When a POST request to the create-criterion endpoint for that competency supplies an object_id whose parsed course is Course Y, and no group_id
  Then the response returns status code 201
  And a new course-level CompetencyCriteriaGroup is created for Course Y, parented under the existing active root
  And a new leaf CompetencyCriteriaGroup and CompetencyCriterion are created under it

Scenario: Supplied-group creation still succeeds for a non-archived leaf in a partially-archived tree
  Given a competency's course-level group has two leaf groups: one archived=true, one archived=false
  When a POST request to the create-criterion endpoint supplies the non-archived leaf's group_id together with a matching object_id
  Then the response returns status code 201
  And a CompetencyCriterion is created, associated with that non-archived leaf group

Scenario: Re-adding content to the group its archived criterion sits in is rejected
  Given a CompetencyCriterion previously associated object_id X with tag_id T in leaf group G, was later archived (archived=true) rather than deleted, and its oel_tagging_objecttag row is still in place
  And G is still archived=false, because another criterion in G kept it active
  When a POST request to competency T's endpoint supplies object_id X together with group_id G
  Then the response returns status code 400
  And the response body says the content was previously associated with this competency in this group and archived
  And no new CompetencyCriterion is created, and the archived CompetencyCriterion is unaffected

Scenario: Adding the same content to a different group after its earlier criterion was archived succeeds
  Given the archived CompetencyCriterion for object_id X in leaf group G from the previous scenario
  And another leaf group H, archived=false, exists under the same competency and course
  When a POST request to competency T's endpoint supplies object_id X together with group_id H
  Then the response returns status code 201
  And a new CompetencyCriterion is created in H, associated with the existing oel_tagging_objecttag row
```

## Technical Details

**Data Structures**

No new types. This depends on `CompetencyCriteriaGroup.archived` and `CompetencyCriterion.archived` (both `BooleanField`s, added by \#716) and reuses \#665's `resolve_or_create_leaf_group()`, `resolve_supplied_leaf_group()`, and the duplicate-association check inside `associate_competency_criterion()`, all with signatures unchanged.

**Logic**

Add a private `_reject_if_archived(group: CompetencyCriteriaGroup) -> None` helper that raises `rest_framework.exceptions.ValidationError` when `group.archived` is `True`, identifying the group's id and that archived groups can't accept new associations. It must be DRF's `ValidationError`, not Django's core one: this app's exception handling (`src/openedx_tagging/rest_api/v1/exception_handlers.py`) only maps `APIException`/`Http404`/`PermissionDenied` to a clean response, so the wrong type would surface as an unhandled 500\. Its message must be distinguishable from \#665's other 400 causes (non-leaf, competency mismatch, course mismatch, duplicate association) — do not key it `archived`, since that's already the model's boolean-state field name in this backlog's success responses (\#674/\#675); a distinct message string, or a differently-named key, is enough.

- In `resolve_or_create_leaf_group()`: immediately after the root `get_or_create()`, if the root is archived, set `archived=False` and save it. Then call the helper immediately after the course-level `get_or_create()`, before the leaf is touched. A course-level branch can be archived while the root and its other course-level siblings stay active, per \#675's own "cascade stops at an ancestor with a surviving sibling" behavior, so the course-level check is needed even when the root was never archived. Do not add a "create a fresh sibling instead" fallback for the course-level group: \#665's own partial `UniqueConstraint`s (one root per competency; one course-level group per competency+course) make that schema-illegal. The leaf itself is always freshly created here and never needs the check.  
- In `resolve_supplied_leaf_group()`: add one more step to the existing ordered validation (after leaf-shape, tag-match, course-match) calling `_reject_if_archived()` on the resolved group. No ancestor walk needed: given \#674/\#675's cascade semantics (an ancestor archives only once every child is already archived), a leaf can never be non-archived while an ancestor is archived.  
- In the duplicate-association check: keep matching archived criteria. When the matching criterion in the target group is archived, raise the same DRF `ValidationError` with a message saying the content was previously associated with this competency in this group and archived, so the author learns why a group that shows no such content rejects it.  
- All three checks run inside `associate_competency_criterion()`'s existing `transaction.atomic()` block (already true, since they sit inside the functions it calls), so a rejection on the course-level group also rolls back a root reactivation made earlier in the same request.

No public-API signature changes: both functions keep \#665's exact contracts, this only adds a root reactivation and rejection paths inside them. No migration, no new endpoint, no serializer or view changes, no `.importlinter` impact.

Test strategy: unit tests for `resolve_or_create_leaf_group()` (archived root reactivated and a new course-level group created under it; archived course-level group rejected, with an active root and with a just-reactivated root that rolls back; happy path unaffected), `resolve_supplied_leaf_group()` (archived leaf rejected; happy path unaffected), and the duplicate-association check (an archived criterion in the same group still blocks, with the archived message; the same content in a different group is accepted), plus DRF integration tests on the create-criterion endpoint for the supplied-archived-leaf 400, the derive-path archived-course-level-group 400, the derive-path archived-root reactivation 201, and the archived-criterion same-group re-add 400\.

### Example Resolution Prompt

> Implement the archived-branch protections described in Technical Details for `resolve_or_create_leaf_group()`, `resolve_supplied_leaf_group()`, and the duplicate-association check, all in `src/openedx_learning/applets/cbe/api.py`. Assume \#665 has landed all three and `associate_competency_criterion()` as scoped, and that \#716 has already added `archived = models.BooleanField(default=False)` to both `CompetencyCriteriaGroup` and `CompetencyCriterion`.  
>   
> Follow Technical Details for the root reactivation, the `_reject_if_archived()` helper's behavior and exception type, where each function calls it, the no-fallback / no-ancestor-walk invariants, the duplicate-check's archived message, and the distinguishable-message requirement. Follow the Acceptance Criteria for the exact response shape and scenario coverage. Stay inside `api.py`: no signature, migration, serializer, or view changes.  
>   
> Add unit tests to `src/openedx_learning/applets/cbe/tests/test_api.py` and DRF integration tests to `src/openedx_learning/applets/cbe/rest_api/v1/tests/test_views.py` per the Acceptance Criteria, and confirm none of \#665's existing happy-path scenarios regress.

## Context

- **\#665:** defines `resolve_or_create_leaf_group()`, `resolve_supplied_leaf_group()`, and `associate_competency_criterion()`, the functions this ticket modifies, plus the two partial `UniqueConstraint`s (one root per competency; one course-level group per competency+course) that make "create a fresh sibling instead of erroring" schema-illegal once the existing row is archived. Also the source of this ticket's actor and permission model (`oel_tagging.can_tag_object`), unchanged here.  
- **\#716:** adds the `archived` field this ticket checks, ahead of \#674 and \#675 too.  
- **\#674 / \#675:** their cascade mechanics (an ancestor archives only once every child is already archived) are in Technical Details, where they justify this ticket's check placement.  
- **ADR 0002 Decision 7** (`docs/openedx_learning/decisions/0002-competency-criteria-model.rst`): names `CompetencyCriteriaGroup`/`CompetencyCriteria` directly under archive-only, hidden-from-new-associations archiving, the primary citation for this ticket.  
- **ADR 0002 Decision 3**: the same guarantee already implemented for `CompetencyRuleProfile.archived`, the precedent this ticket extends, including its own no-unarchive-path precedent, with the root reactivation as the one exception.  
- **ADR 0002 Decision 2**: a persisted group is never empty. An archived root still holds its archived children, so reactivating it never leaves an empty group, and stopping the cascade below the root instead would leave an empty root whenever the last course-level group is hard-deleted.
- `src/openedx_tagging/rest_api/v1/exception_handlers.py`: confirms only `APIException`/`Http404`/`PermissionDenied` become clean error responses here, why the new check must raise `rest_framework.exceptions.ValidationError`, not Django's core one.  
- `src/openedx_tagging/rest_api/v1/serializers.py`'s `validate_tag_value`: this repo's existing state/uniqueness-rejection precedent, a 400 (no 409 usage anywhere in this codebase).

## Files to create and modify

**Modified files**

| File | Nature of modification |
| :---- | :---- |
| `src/openedx_learning/applets/cbe/api.py` | Reactivate an archived root in `resolve_or_create_leaf_group()`, add the `_reject_if_archived()` helper, call it from `resolve_or_create_leaf_group()` and `resolve_supplied_leaf_group()`, and add the archived message to the duplicate-association check, per Technical Details. |
| `src/openedx_learning/applets/cbe/tests/test_api.py` | Unit tests: archived root reactivated, archived course-level group rejected (active root, and reactivated root rolled back), archived supplied leaf rejected, archived criterion in the same group still blocks with the archived message, same content in a different group accepted, happy paths unaffected. |
| `src/openedx_learning/applets/cbe/rest_api/v1/tests/test_views.py` | DRF integration tests: POST to the create-criterion endpoint returns 400 for a supplied archived leaf and for a derive-path archived course-level group, 201 with the root reactivated for a derive-path archived root, and 400 with the archived message when re-adding content to the group its archived criterion sits in. |

## Open questions

- [non-blocking, owner: architect/reviewer] Reactivating the root leaves any `StudentCompetencyCriteriaGroupStatus` rows on it in place, computed against the course-level groups that are now archived. Confirm the next evaluation recomputes them rather than a learner's old competency-level status carrying over to the rebuilt rules.
