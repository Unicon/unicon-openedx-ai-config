# [OOS - BE] Reassign existing Competency Criteria when a taxonomy-level rule profile is created

GitHub: https://github.com/openedx/openedx-core/issues/679 (#679, OPEN)
Cached: 2026-09-21

This ticket still requires internal review by Unicon. It is now considered out of scop for the current project, but may be picked by up as future work.

**Issue \#679.** Backend, `openedx-core` (single repo). Implements the write-time reassignment behavior triggered by creating a taxonomy-level `CompetencyRuleProfile`: existing criteria that were resolving to the system default get reassigned to the newly created, more-specific taxonomy profile.

**Blocked by:** \#613 (the CBE data model) and \#631 (creates the taxonomy-level rule profile whose creation triggers this reassignment; this behavior hooks into that create flow — see Open Questions on whether it lands inside \#631 or as a service it calls). Related: \#665 (sets a criterion's initial rule-profile FK at creation), \#632 (update/archive), \#646 (the authoring UI that surfaces the in-use warning this reassignment can require).

Repo: `openedx-core`. No `openedx-platform` change.

## Use Case

As a taxonomy or course author, when I create a taxonomy-level default rule profile, I want the competency criteria that were relying on the platform-wide system default to start using my new taxonomy default going forward, so that setting a taxonomy default actually takes effect for criteria already authored under that taxonomy, without me having to touch each criterion by hand.

## Description

**Current state**

Per ADR 0002 Decision 4, a `CompetencyCriterion`'s applicable rule profile is stored as an FK (`competency_rule_profile_id`) that is **computed and written at explicit write-time events, never re-resolved dynamically at evaluation time**. When a criterion is created (\#665) it is assigned the most-specific profile that exists at that moment (in MVP: the taxonomy profile if one exists, otherwise the system default), unless it carries a per-criterion override. ADR 0002 Decision 4 also specifies that when a *more specific* profile is created later, existing criteria that currently resolve to a less-specific profile must be **reassigned** to it, and ADR 0003 Decision 4 says that reassignment is treated as an edit for the in-use warning. No logic implements that reassignment yet: as drafted, \#631 creates a taxonomy profile but leaves existing criteria pointing at the system default, so the new taxonomy default would not take effect for already-authored criteria.

**Requested change**

When a taxonomy-level `CompetencyRuleProfile` is created (\#631), reassign existing `CompetencyCriterion` rows under that taxonomy's competencies, per ADR 0002 Decision 4:

- **Reassign** criteria that currently resolve to the **system default** (the all-null-scope profile) and belong to a competency in the taxonomy the new profile is scoped to. Reassignment updates the criterion's `competency_rule_profile_id` FK to the new taxonomy profile (a write-time change, consistent with "no dynamic re-resolution at evaluation").  
- **Do not reassign** a criterion that carries a per-criterion override (`rule_type_override` / `rule_payload_override`): overrides win and are mutually exclusive with a profile assignment.  
- **Do not reassign** a criterion already assigned to a *more* specific profile (e.g. a course-scoped one). Course/org scopes are deferred in MVP, but the reassignment must not clobber a more-specific assignment if one is present.  
- Treat a reassignment that touches an **in-use** criterion (one with a recorded `StudentCompetencyCriteriaStatus`) as an edit for the in-use warning (ADR 0003 Decision 4): it requires the same warning/confirmation as any in-use edit. The reassignment is forward-only, does not retroactively change recorded statuses, and triggers no recompute.  
- Perform the reassignment **atomically** with the profile creation (one transaction), so a taxonomy profile is never created with the reassignment half-applied.

**Explicitly out of scope**

- Reassignment triggered by any event other than **taxonomy-level profile creation** — ADR 0002 Decision 4 lists other write-time triggers (an override being set/cleared, or org/course profiles appearing); those are separate concerns, not this ticket.  
- Organization- and course-level scopes (deferred).  
- The authoring-UI warning/confirmation surface itself (\#646); this ticket produces the backend behavior and the in-use signal it depends on, not the dialog.  
- Creating the taxonomy profile (\#631) beyond hooking this reassignment into its create path.  
- Evaluation logic that consumes the FK.

## Acceptance Criteria

Verifiable via Postman / the create-taxonomy-profile flow.

```
Scenario: Criteria on the system default are reassigned to a new taxonomy profile
  Given competency criteria under a taxonomy currently resolve to the system-default rule profile
  And none of them carry a per-criterion override
  When a taxonomy-level rule profile is created for that taxonomy
  Then those criteria's competency_rule_profile_id is updated to the new taxonomy profile
  And the change is committed in the same transaction as the profile creation

Scenario: Criteria with a per-criterion override are not reassigned
  Given a competency criterion under the taxonomy carries a rule_type_override / rule_payload_override
  When a taxonomy-level rule profile is created for that taxonomy
  Then that criterion is left unchanged (its override still applies)

Scenario: Criteria already on a more-specific profile are not reassigned
  Given a competency criterion is already assigned to a more-specific (e.g. course-scoped) profile
  When a taxonomy-level rule profile is created
  Then that criterion keeps its more-specific assignment

Scenario: Reassigning an in-use criterion requires confirmation
  Given at least one criterion that would be reassigned is in use (has a recorded StudentCompetencyCriteriaStatus)
  When a taxonomy-level rule profile creation would reassign it
  Then the operation requires explicit confirmation before it is applied
  And once confirmed, the reassignment is applied going forward without changing already-recorded statuses

Scenario: Reassignment does not touch criteria outside the taxonomy
  Given criteria exist under a different taxonomy
  When a taxonomy-level rule profile is created for this taxonomy
  Then only this taxonomy's criteria are considered for reassignment
```

## Open Questions

- **\[BLOCKING, owner: architect/backend\] In-use confirmation mechanism.** Reassigning an in-use criterion is an edit requiring confirmation (ADR 0003 Decision 4), but the ADR defines no wire mechanism (no field, no status code) for surfacing "in use" — the same gap flagged for \#632/\#633/\#646. This ticket needs a concrete contract: does creating a taxonomy profile that would reassign in-use criteria return a distinguishable conflict (e.g. a 409 the client re-submits with a confirm flag), or is the confirmation gathered before the create call? Must be settled with \#631/\#632/\#633 before build.  
- **\[non-blocking, owner: architect\] Where this lands.** Confirm whether the reassignment is implemented inside \#631's create flow (preferred: it's an inseparable, atomic side-effect of creation) or as a separate service function \#631 calls. Either way it must share \#631's transaction.  
- **\[non-blocking, owner: architect\] "Resolves to the system default" detection.** Confirm how a criterion's current resolution is read for the reassignment scan — directly off its `competency_rule_profile_id` pointing at the all-null-scope row, versus recomputing via the precedence table. The FK is the source of truth per Decision 4, so scanning the FK is the intended approach; confirm against \#613's landed model.

## Context

- ADR 0002 (`docs/openedx_learning/decisions/0002-competency-criteria-model.rst`), Decision 4: the resolution/precedence table and the write-time FK model — `competency_rule_profile_id` is assigned at explicit write events (creation, a more-specific profile appearing later, override set/cleared) and never re-resolved at evaluation time; a more-specific profile created later reassigns existing criteria to it.  
- ADR 0003 (`docs/openedx_learning/decisions/0003-competency-criteria-versioning.rst`), Decision 4: reassignment caused by creating a more-specific profile is treated as an in-use edit — same forward-only warning and confirmation; recorded statuses are not retroactively changed.  
- \#631: creates the taxonomy-level rule profile; this behavior triggers on that creation.  
- \#665: sets a criterion's initial `competency_rule_profile_id` when the criterion is created.  
- \#632 / \#633 / \#646: the update/archive endpoint, the read endpoint, and the authoring UI — all share the same undefined in-use-signal contract this ticket also depends on.

## Technical Notes

### Files to Modify

| File | Nature |
| :---- | :---- |
| `src/openedx_learning/applets/cbe/api.py` | In (or called from) the create-taxonomy-profile function \#631 adds, run the reassignment inside the same `transaction.atomic()` block. |
| `src/openedx_learning/applets/cbe/rest_api/v1/views.py` | If the in-use confirmation is surfaced at the API boundary (per the Open Question), the create view for \#631 handles the confirm/conflict handshake. |
| `src/openedx_learning/applets/cbe/tests/test_api.py` / `rest_api/v1/tests/test_views.py` | Add reassignment coverage (see test strategy). |

### Files to Create

*Conditional — only if the team prefers a separate service over inlining in \#631's create function:*

| File | Purpose |
| :---- | :---- |
| `src/openedx_learning/applets/cbe/api.py` addition | `reassign_criteria_to_new_taxonomy_profile(profile)` helper, called within \#631's create transaction. |

### Implementation Notes

On taxonomy-profile creation, within \#631's create transaction: select `CompetencyCriterion` rows whose competency tag belongs to the taxonomy the new profile is scoped to, that currently point at the system-default profile row, and that have no per-criterion override; set their `competency_rule_profile_id` to the new profile. Skip criteria with an override or an already-more-specific assignment. Determine "in use" for the affected set (any `StudentCompetencyCriteriaStatus` referencing those criteria) and gate the operation on confirmation per the in-use contract (see Open Questions) — do not silently reassign in-use criteria without the confirmation ADR 0003 requires. Nothing here recomputes or mutates existing status rows; the reassignment is forward-only by construction (it only changes the FK future evaluations read). Keep the reassignment scan and the profile insert in one transaction so the two never diverge.

No model or migration work belongs here (that's \#613); no PII annotation change.

### Example Resolution Prompt

> In `openedx-core`, implement the taxonomy-profile-creation reassignment for issue \#679, hooked into \#631's create-taxonomy-rule-profile flow. Inside \#631's create `transaction.atomic()` block (in `src/openedx_learning/applets/cbe/api.py`), after inserting the new taxonomy-scoped `CompetencyRuleProfile`, select `CompetencyCriterion` rows whose competency tag is in that taxonomy, whose `competency_rule_profile_id` currently points at the system-default (all-null-scope) profile, and which have no `rule_type_override`/`rule_payload_override`; update their `competency_rule_profile_id` to the new profile. Do not touch criteria that carry an override or that already point at a more-specific profile. Detect whether any affected criterion is in use (has a `StudentCompetencyCriteriaStatus`); if so, require the in-use confirmation per ADR 0003 Decision 4 using whatever wire mechanism \#631/\#632/\#633 settle on (confirm-flag re-submit or pre-create confirmation — do not assume; flag if unset). Never mutate or recompute existing status rows — the reassignment only changes the FK that future evaluations read, and it must commit in the same transaction as the profile insert. Add tests: system-default criteria get reassigned; override-bearing criteria don't; already-more-specific criteria don't; in-use reassignment requires confirmation; criteria in other taxonomies are untouched.
