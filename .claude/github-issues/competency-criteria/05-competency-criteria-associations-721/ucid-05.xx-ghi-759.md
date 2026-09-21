# [BE] Build Update endpoint to handle a user de-selecting a Competency Criteria association.

GitHub: https://github.com/openedx/openedx-core/issues/759 (#759, OPEN)
Cached: 2026-09-21

## User Story

As a Platform Administrator, I want to change the rule that a set of Competency Criteria are evaluated by in one request, in order to correct a mastery threshold shared across several assignments without editing each Competency Criterion individually.

## Acceptance Criteria

Every outcome below is observable in the response to the update itself, in the learner status tables, or in each criterion's change history.

```
# Changing where a batch of criteria's rule comes from

Scenario: Apply rule values of its own to a batch of criteria
  Given a set of Competency Criteria, in any mix of current rule sources
  And the requesting user has studio write access to the group's course and view access to the competency's taxonomy
  When the user updates them together with rule values of its own
  Then the update succeeds
  And the response reports every named criterion as carrying those rule values and following no rule profile

Scenario: Apply a named rule profile to a batch of criteria
  Given a set of Competency Criteria, in any mix of current rule sources
  When the user updates them together to follow a named rule profile
  Then the update succeeds
  And the response reports every named criterion as following that rule profile and carrying no rule values of its own
  # Reachable via the API only. In this phase the only rule profile that exists is the system default,
  # and Studio does not expose a control for naming a profile directly; a Studio author reaches the
  # same end state by editing rule values to match the applicable default (the scenario below).

Scenario: Rule values applied to a batch that match the applicable default are treated as returning to it
  Given a set of Competency Criteria
  When the user updates them together with rule values of its own that exactly match the rule of the profile that currently applies to a given criterion
  Then the update succeeds
  And the response reports that criterion as following that rule profile and carrying no rule values of its own

# Rejecting a rule the system cannot store or evaluate

Scenario: Reject a batch update naming both a rule profile and rule values of its own
  Given a set of Competency Criteria
  When the user submits an update naming a rule profile and supplying rule values of its own in the same request
  Then the update is rejected
  And the response identifies the two as mutually exclusive
  And no named criterion is changed

Scenario: Reject a batch update that supplies neither form
  Given a set of Competency Criteria
  When the user submits an update naming no rule profile and supplying no rule values of its own
  Then the update is rejected
  And no named criterion is changed

Scenario: Reject a batch update naming a rule profile that does not exist or has been retired
  Given a set of Competency Criteria
  When the user submits an update naming a rule profile that does not exist, or one that has been retired
  Then the update is rejected
  And no named criterion is changed

Scenario: Reject an incompletely specified rule for a batch
  Given a set of Competency Criteria
  When the user submits an update naming a rule type without the threshold it is evaluated against
  Then the update is rejected
  And the response identifies the rule as incompletely specified
  And no named criterion is changed

Scenario: Reject a rule the system cannot evaluate, for a batch
  Given a set of Competency Criteria
  When the user submits an update whose rule has a threshold outside the range permitted for its rule type, or a comparison the system does not support, or a rule type that exists in the system's vocabulary but is not yet implemented
  Then the update is rejected
  And no named criterion is changed

# Rejecting a request that identifies the wrong criteria

Scenario: Reject a batch update naming no criteria
  Given a Competency Criteria Group
  When the user submits an update naming an empty list of criteria
  Then the update is rejected

Scenario: Reject a batch update naming the same criterion more than once
  Given a Competency Criteria Group
  When the user submits an update naming one criterion twice in the same list
  Then the update is rejected

Scenario: Reject a batch update if any named criterion does not belong to the request's group, or does not exist
  Given a Competency Criteria Group, and one criterion that does not belong to it or does not exist at all
  When the user submits an update naming that criterion alongside others that do belong to the group
  Then the request is treated as addressing something that does not exist
  And no named criterion is changed

Scenario: Reject a batch update if any named criterion has been retired
  Given a Competency Criteria Group containing one criterion that has been retired
  When the user submits an update naming that criterion alongside others that have not been retired
  Then the update is refused as conflicting with the state of the batch
  And no named criterion is changed

# Leaving unaffected criteria alone

Scenario: A batch update that leaves some criteria unchanged still succeeds for the rest
  Given a Competency Criteria Group where one criterion already carries the rule being applied and another does not
  When the user submits a batch update applying that rule to both
  Then the update succeeds
  And no new entry is added to the unchanged criterion's change history
  And a new entry is added to the changed criterion's change history

# Requests that come from someone who may not make them

Scenario: Reject a batch update from a user without permission
  Given a user who lacks studio write access to the Competency Criteria Group's course, or lacks view access to the taxonomy owning its competency
  When that user submits a batch update naming criteria in that group
  Then the request is refused
  And no named criterion is changed
```

## Description

A Competency Criteria Group can present several Competency Criteria under one shared rule in Studio: for example, several tagged assignments all evaluated at "75% or higher" within one "complete any of the following" group. Each of those criteria stores its rule independently, so correcting the shared threshold today means editing every criterion in the group one at a time, and because learner statuses are recorded against each criterion individually, an author has no single action that updates the whole group's threshold at once. This ticket adds one request that applies one rule to a named set of criteria atomically, so a threshold correction that Studio displays as a single number is a single write.

<details>
<summary>Technical Details</summary>

This section is background and a suggested approach, not the source of truth. The User Story and Acceptance Criteria define what must be true when the work is done; the notes below exist to save the implementer some thinking.

### In short

**What an author edits.** The only thing this endpoint changes about a named set of existing Competency Criteria is where each one's evaluation rule comes from. The criteria group each belongs to and the tagged content each measures both stay fixed; this endpoint's request body carries no field that could name either, only the ids of the criteria to touch and the one rule to apply to them. That is not a judgment about how much power to give an author: the create endpoint (\#665) does not accept those fields either, taking the group from the URL and building the tag association itself from the group's own competency tag. A batch endpoint that accepted them per criterion would invent request surface with no counterpart on the create side, and would let a client break a consistency that creation currently guarantees.

**One rule, applied identically to every named criterion.** A single request names one rule source, in exactly the same two mutually exclusive forms a single-criterion update would use: name a rule profile by id, or supply a complete pair of rule values. Never both, never neither, never half of a rule-value pair. There is no way to give different criteria in the same batch different rules; a caller wanting that submits separate requests, one per rule. This is the same rule-source shape this endpoint would need if more profiles existed later: the caller always names the profile it wants by id, and in this phase the only id that exists to name is the system default's.

**Every named criterion must belong to the group in the URL.** `criterion_ids` is a non-empty list with no duplicates. Naming an id that does not belong to that group, or does not exist at all, is treated as addressing something that does not exist for the whole request, the same way a single-criterion endpoint would treat a group mismatch.

**The rule source is one indivisible concern per criterion, not independently patchable fields.** Naming a profile clears any rule values a criterion was carrying, and supplying rule values clears the profile link, for every named criterion. That is unusual for a partial update, so it is worth stating plainly. ADR 0002 Decision 4 requires a criterion to either link to a profile with both override fields empty, or carry both override fields with no profile link, and the create path (\#665) checks only that at least one of the two was supplied, so nothing today stops a criterion from carrying both. This endpoint validates the whole rule once and writes all three columns together on every named criterion, so an edit can never leave one in a mixed or empty state.

**Rules about the profile being named.** The named profile must exist and must not be archived, because an archived profile is retired and ADR 0002 Decision 3 keeps archived profiles out of new associations. This is checked once for the whole batch, since the named profile is the same for every criterion in the request. The endpoint does not judge whether the named profile is the most appropriate one for any named criterion's scope. In this phase only the system-default profile can be named at all, since no other profile exists yet.

**Naming a profile is explicit, and returning to one is also inferred in one narrow case, decided independently per criterion.** A caller that wants a criterion to follow a specific profile names it by id, for the whole batch at once. Separately, if the rule values submitted for the batch exactly match the rule of the profile currently applicable to a given criterion, the endpoint treats that criterion as returning to that profile: it stores that criterion as following it, with its override fields cleared, rather than as carrying redundant values equal to it. ADR 0002 Decision 4's fourth write-event trigger requires exactly this. This comparison is evaluated separately for each named criterion, not once for the whole batch: ADR 0002 Decision 4 resolves the profile applicable to a criterion from that criterion's own context (the scope the authoring screen that created it supplied), independently of which Competency Criteria Group it happens to sit in today, so two criteria in the same group are not guaranteed to share the same applicable default. Two criteria in one batch that receive the exact same submitted values can therefore end up in different stored states: one reassigned to a profile, another still carrying the override values, and that is correct behavior rather than an inconsistency to fix. "Exactly match" compares the parsed rule, not the raw stored JSON: the applicable profile's `rule_type` equals the submitted `rule_type_override`, and every field of the parsed payload (`op`, `value`, and `scale` for `Grade`) matches value-for-value. Key order or formatting differences between the two stored payloads never matter, since the comparison is never done on raw text.

**One state of a criterion stops the whole batch outright.** If any named criterion has been retired by \#674, no criterion in the batch is editable and the whole request is refused; there is no confirmation or override for that. This endpoint does not check whether any learner has a recorded status against any named criterion. ADR 0003 Decision 4's warning-and-confirmation workflow for that case is a Studio-side responsibility that \#723 (Epic 10\) owns, not this endpoint's.

**Learner status is never read and never written by this endpoint.** This endpoint does not create, update, or delete any `StudentCompetency*Status` row for any named criterion, and it does not query them either: whether a learner has a recorded status plays no part in whether the batch is accepted. Once \#723 builds a confirmation workflow in front of this endpoint, a confirmed edit will still apply going forward only; ADR 0003 Decision 5 makes the status tables append-only, and this endpoint writing rows in the criteria table is what makes that forward-only guarantee true by construction rather than by convention.

**What this endpoint does not validate, and where that lives instead.** The internal shape of a rule payload, meaning the allowed comparisons and the requirement that a threshold be a fraction between 0.0 and 1.0, belongs at the model layer so that create and update share one definition. \#631 owns getting it there. This endpoint asks the model to validate itself before saving rather than restating the contract, so there is no second copy to drift, and it validates the submitted rule once rather than once per named criterion, since the rule is identical for all of them.

**Where the logic lives, and how the audit trail stays honest.** The endpoint is a thin adapter: resolve the group and criteria from the URL and request body, check permissions, validate the request's shape, delegate to a function in the applet's `api.py`, serialize the results. Keeping the refusals and the audit attribution in that API function means an in-process Studio caller behaves identically to an HTTP one. ADR 0003 Decision 1 puts `django-simple-history` on this model, so each row's save produces one historical snapshot. A logical edit to one criterion must therefore be exactly one save for that row, because writing the profile link and the rule values separately would record an intermediate state that violates the invariant above, and a criterion whose edit changes nothing must not save at all; all the saves in one batch happen inside one transaction, so a failure anywhere in validation rolls every criterion in the request back to its prior state.

### Implementation specifics

- **Endpoint.** `PATCH /cbe/rest_api/v1/criteria-groups/<int:group_id>/criteria/bulk-update/`, a new action-style route alongside the collection and detail routes \#665 and \#674 register; it does not modify or replace either. New view class `CompetencyCriterionBulkUpdateView`. Set `http_method_names` so only `PATCH` is offered. `PATCH` matches this codebase's only comparable precedent, `TaxonomyView.update_import` (`src/openedx_tagging/rest_api/v1/views.py:336`, `PUT`, replaces many child rows under one parent); `PATCH` fits better than `PUT` here since this updates a named subset of a parent's children rather than the full set.  
- **API function.** `bulk_update_competency_criteria(criterion_ids: list[int], competency_criteria_group_id: int, *, competency_rule_profile_id: int | None = None, rule_type_override: str | None = None, rule_payload_override: dict | None = None, user) -> list[CompetencyCriterion]` in `src/openedx_learning/applets/cbe/api.py`, added to that module's `__all__`. The umbrella `src/openedx_learning/api.py` re-exports by wildcard, so it needs no edit.  
- **Request body contract.** `criterion_ids`: required, non-empty list of integers with no duplicates. Alongside it, exactly one of `competency_rule_profile_id` alone, or both `rule_type_override` and `rule_payload_override` together. Reject with 400 a body supplying an empty or duplicate-containing `criterion_ids`, both rule forms, neither rule form, one half of the rule-value pair, or any unrecognized key. There is no confirmation field on this request; this endpoint does not gate on learner status (\#723 owns that workflow).  
- **Validating the batch's identity.** Every id in `criterion_ids` must resolve to a `CompetencyCriterion` whose `competency_criteria_group_id` matches the URL's `group_id`. If any does not, or does not exist at all, treat the whole request as addressing something that does not exist (404), matching \#674's convention that a parent mismatch is a resource-identification failure rather than a validation error.  
- **Validating a named profile.** If `competency_rule_profile_id` is supplied, it must reference an existing, non-archived `CompetencyRuleProfile`; reject with 400 for the whole batch if it does not exist or is archived. This is one check, not one per named criterion. In this phase the only value that can satisfy it is the system default's id.  
- **Determining the profile currently applicable, per criterion, for the matching check.** For each named criterion independently, this calls the shared resolution helper \#679 builds, which in this phase always returns the system-default profile for every criterion. Do not reimplement that rule inline, and do not assume the result is the same across every criterion in the batch once more than one profile exists (see the "In short" note above on why it can differ within a group). This lookup is internal to the matching check; it plays no part in validating a profile id the caller explicitly named.  
- **Determining an exact match, per criterion.** For each named criterion, compare the parsed rule, never the raw JSON text, against that criterion's own applicable profile: `rule_type` must be equal, and every field of the parsed payload (`op`, `value`, and `scale` for `Grade`) must match value-for-value. Deserialize both payloads and compare the resulting dicts (or their sorted-key equivalents); do not compare serialized strings, since key order and formatting are not significant.  
- **Payload and enum validation.** Do not write a payload validator here. Call `full_clean()` once, on an unsaved instance carrying the submitted rule, so it picks up the model-layer validation \#613 and \#641 land per \#631's requirement, and translate `django.core.exceptions.ValidationError` into DRF's `ValidationError`, the same translation `TaxonomyView.perform_create` performs in `src/openedx_tagging/rest_api/v1/views.py`. The contract the tests assert against is `rule_type` limited to the model's declared choices with only `Grade` implemented, the comparison in `gte`/`lte`/`eq`, and the threshold a fraction in `[0.0, 1.0]` inclusive.  
- **Check order.** Resolve the group and check permissions; validate the request's shape (400, including that every named id belongs to the group and, if a profile was named, that it exists and is not archived); refuse the whole batch if any named criterion is retired (409); for each named criterion, resolve whether the submitted rule matches its own applicable profile, and skip the save for any criterion whose resulting state matches what it already has; save the rest. All of the above runs inside one `transaction.atomic()` block, so a failure at any point leaves every named criterion exactly as it was.  
- **Single atomic write per changed criterion, all within one transaction.** For each criterion whose resulting state differs from its current one, write `competency_rule_profile_id`, `rule_type_override`, and `rule_payload_override` in one `.save(update_fields=[...])`, setting the unused side to null explicitly. Do not use `queryset.update()`: it does not fire `post_save` and would write no history row.  
- **History attribution.** Set `instance._history_user` from the `user` argument before saving each changed row, so attribution does not depend on the consumer installing `simple_history.middleware.HistoryRequestMiddleware`. No model in this repo uses `HistoricalRecords()` yet, so this establishes the convention rather than following one; `django-simple-history` is already a declared dependency in `requirements/base.txt`. Optionally set `_change_reason` to distinguish "rule values set" from "reassigned to profile" per row, since the two outcomes are otherwise distinguishable only by diffing three columns.  
- **No learner status read or write.** Do not create, update, or delete any `StudentCompetency*Status` row for any named criterion, and do not query them either. There is no in-use check in this ticket.  
- **Response.** 200 with a list of `CompetencyCriterionSerializer` representations, one per named criterion, echoing all three rule columns exactly as stored for each, which is what makes the profile-versus-own-values outcome observable per criterion from the response alone. `CompetencyRuleProfile`'s internal primary key is accepted as intentionally surfacing on the wire here; confirm no Open edX community objection before this is published.  
- **Status codes.** A 400 means the request is malformed, self-contradictory, or references a row it may not use; a 409 means the request is well formed but the state of the batch blocks it. So a request naming an unknown or archived profile, an empty or duplicate-containing id list, or a self-contradictory rule is 400, while a batch containing a retired criterion is 409\. In full: 200 on success, including when some or all named criteria are no-ops; 400 on any body-contract violation or a payload the model rejects; 404 if any named criterion does not exist or does not belong to the URL's `group_id`; 409 if any named criterion is retired; 403 without `oel_tagging.can_tag_object` (studio write access to the group's course plus taxonomy view access on the competency's taxonomy); 405 on unsupported methods.  
- **Permissions.** Check `oel_tagging.can_tag_object` inline: `user.has_perm("oel_tagging.can_tag_object", ObjectTagPermissionItem(taxonomy=<the group's competency tag's taxonomy>, object_id=<that course's key as a string>))`, called from inside the `api.py` function rather than from a `permission_classes` attribute on the view. Since a group holding `CompetencyCriterion` rows directly is always a leaf group (ADR 0002: `course_id` is set only on course-level groups, never on leaf groups), resolve the course via the URL's group's parent (`group.parent.course_id`) to get the `CourseRun`, not from the group itself. This composite means studio write access to that course plus taxonomy view access on the competency's taxonomy, not "permitted to manage the taxonomy that owns the competency." Reuse the same inline `has_perm('oel_tagging.can_tag_object', ObjectTagPermissionItem(...))` check pattern \#665 uses in `associate_competency_criterion()` — there is no permission class \#664 or \#665 landed to reuse; \#665's own check is this same inline call inside its `api.py` function, not a DRF permission class.  
- **No migration, no new model, no new field.** This ticket depends on \#716 for `archived` on this model, and on \#613 and \#641 for the models, the model-layer payload validation, and whether a database check constraint backs the exactly-one-of rule; if \#613/\#641 don't land the payload validation, \#665 is the fallback owner. Confirm before implementing rather than assuming.  
- **Layering.** Lives in `src/openedx_learning/applets/cbe/`, imports only from `openedx_tagging` and Django or DRF, and adds no import beyond what \#664 and \#665 establish. `openedx_learning` is not yet among `.importlinter`'s root packages; adding it belongs to \#613.  
- **Out of scope.**  
  - Removing or retiring a criterion, including setting `archived` (\#674), and removing a group (\#675).  
  - Retiring or archiving a `CompetencyRuleProfile`; no such action is built in this phase, since only the never-archived system default exists.  
  - Applying different rules to different criteria in one request. A caller wanting that submits separate requests.  
  - Bulk-creating or bulk-deleting criteria; this ticket only changes the rule on criteria that already exist.  
  - Implicitly updating every criterion in a group without the caller naming them. The caller always names the criteria explicitly; there is no "update the whole group" mode that infers membership from the group id alone.  
  - Checking whether a learner has a recorded status against any named criterion, and any confirmation or warning workflow for it. Owned by \#723 (Epic 10).  
  - Defining or restating the rule-payload contract, owned by \#631 with its home at the model layer in \#613 and \#641.  
  - Re-pointing the tag association or re-parenting a criterion, both of which are a removal plus a create through \#674 and \#665.  
  - Any `ObjectTag` write, whose lifecycle stays with `openedx_tagging`.  
  - \#666's containment validator, which is private, creation-path-only, and a function of the group and the tagged object, so this edit cannot invalidate it.  
  - Reporting on a read path whether a criterion is in use (\#684).  
  - The authoring interface's warning copy and confirmation dialog (\#723).  
- **Tests, in `tests/openedx_learning/applets/cbe/test_api.py`.**  
  - Applying rule values to a batch, clearing the profile link on every named criterion regardless of each one's starting state; applying a named profile to a batch, clearing override fields on every named criterion.  
  - The applicable-profile lookup used by the matching check resolving to the system-default profile for a given criterion; rule values applied to a batch that match that criterion's applicable profile reassigning that specific criterion to it, with both override fields cleared, rather than being stored as rule values, while other named criteria in the same batch whose applicable profile does not match keep their submitted rule values as an override.  
  - Rejections for an empty id list, a duplicate id, both rule forms, neither rule form, a half rule-value pair, an unknown profile id, and an archived profile id, each asserting no named criterion changed.  
  - A batch containing one criterion from a different group, and a batch containing one nonexistent id, each rejected with no named criterion changed.  
  - A batch containing one retired criterion refused, with no named criterion changed, even when the rest of the batch would otherwise be accepted.  
  - A batch where one named criterion already carries the submitted rule and another does not: the unchanged one gets no new history row, the changed one gets exactly one.  
  - No learner status row created, updated, or deleted, and none queried, for any named criterion on any path; the exactly-one-of invariant holding for every named criterion after every accepted path.  
  - A payload with an unsupported comparison, and one with a threshold outside `[0.0, 1.0]`, both rejected. This is the test that fails and points at \#613 and \#641 if the model-layer validation is not yet in place.  
- **Tests, in `tests/openedx_learning/applets/cbe/test_views.py`.** 200 for each of the two accepted forms across a multi-criterion batch, with every named criterion's row echoed in the response; 400 for each malformed case (empty list, duplicate id, both/neither rule forms, half pair, unknown or archived profile); 404 for a batch naming an id from a different group or a nonexistent id; 409 for a batch naming a retired criterion; 403 without `oel_tagging.can_tag_object` (studio write access to the group's course plus taxonomy view access on the competency's taxonomy); 405 on unsupported methods.

Files to create and modify **Modified files**

| File | Nature of modification |
| :---- | :---- |
| src/openedx\_learning/applets/cbe/api.py | add `bulk_update_competency_criteria()` |
| src/openedx\_learning/applets/cbe/rest\_api/v1/serializers.py | add the bulk-update request-body serializer |
| src/openedx\_learning/applets/cbe/rest\_api/v1/views.py | add `CompetencyCriterionBulkUpdateView` |
| src/openedx\_learning/applets/cbe/rest\_api/v1/urls.py | register the bulk-update route |
| tests/openedx\_learning/applets/cbe/test\_api.py | api-level tests for the two request forms, rejections, and per-criterion history behavior |
| tests/openedx\_learning/applets/cbe/test\_views.py | endpoint tests for the success, validation, conflict, permission, and not-found cases |

- Context ADR 0002, `docs/openedx_learning/decisions/0002-competency-criteria-model.rst`: Decision 4 for the criterion's fields, the exactly-one-of invariant, and the write events that change the profile assignment, including the fourth trigger (matching values reassigning to the applicable profile) that this endpoint now implements per criterion; Decision 3 for the rule-payload contract and for archived profiles being kept out of new associations, which this endpoint enforces whenever a profile id is named. Only the system-default profile exists in this phase, narrower than both decisions' MVP notes, which describe taxonomy-scoped profiles as also being created; confirm with the architect whether those are simply deferred or the MVP notes need correcting. Decision 4's four listed write events also don't cover this endpoint's caller-names-a-profile-directly case, and this ticket's explicit-id-list design leaves open a separate gap in Decision 4's trigger-3 example (a group's default rule cascading to its criteria, with no column to store one); both are open ADR-documentation questions for the architect.  
- ADR 0003, `docs/openedx_learning/decisions/0003-competency-criteria-versioning.rst`: Decision 1 for `django-simple-history` on this model; Decision 4 for the warning-and-confirmation workflow, which \#723 (Epic 10\) implements in front of this endpoint rather than this endpoint itself; Decision 5 for learner status tables being append-only.  
- ADR 0001, `docs/openedx_learning/decisions/0001-competency-criteria-location.rst`: places CBE code in `src/openedx_learning/applets/`, which is where every path above sits.  
- Prior art for the thin-view-plus-api-function shape and the Django-to-DRF validation-error translation this ticket follows: `src/openedx_tagging/rest_api/v1/views.py` (`TaxonomyTagsView.update` and `TaxonomyView.perform_create`) and `src/openedx_tagging/api.py` (`update_tag_in_taxonomy`).  
- Permission machinery: `oel_tagging.can_tag_object`, checked inline via `has_perm()` against an `ObjectTagPermissionItem`, the same composite (studio write access to the course plus taxonomy view access) \#665 relies on and `openedx-platform`'s `content_tagging/rules.py` registers globally; not a DRF permission class.  
- The applet-api convention this function is published through: `docs/openedx_content/decisions/0010-merge-authoring-apps-into-openedx-content.rst`, with `src/openedx_content/api.py` as the working example.  
- Related work: \#613 and \#641 (data model, model-layer payload validation, constraints); \#631 (shared payload validation this ticket's `full_clean()` call depends on); \#665 (creates criteria and the REST scaffolding this extends, and whose rule-source contract this one mirrors); \#666 (containment validation on the create path); \#674 (removes a criterion and owns `archived` as a retirement action); \#679 (the shared rule-profile resolution helper this ticket calls); \#681 and \#684 (read endpoints); \#709 and \#710 (frontend counterparts); \#716 (adds the `archived` field this ticket refuses to edit); \#723 (owns the confirmation-and-warning workflow this ticket deliberately does not implement); \#760 (the group-level update sibling, which edits a Competency Criteria Group's own fields such as name, ordering, or logic\_operator, not its child criteria's rules).  
- A backend GET endpoint exposing the system-default rule profile to the frontend appears to be missing from the backlog. Confirm whether one exists; if not, get it ticketed.

</details>
