# \[BE\] Build listener that checks when an assignment or course is completed and upon completion if there is a competency criteria associated with it, then calculate and update the learner's competency statuses.

# Add competency mastery-evaluation API (openedx-core side)

**Dependency:** The upstream event, `PERSISTENT_SUBSECTION_GRADE_CHANGED`, is being defined in openedx-events (PR [\#545](https://github.com/openedx/openedx-events/pull/545) / [\#587](https://github.com/openedx/openedx-events/pull/587), nearly complete but not yet merged). Those PRs only add the event and its payload (`PersistentSubsectionGradeData`); they don't emit it from a call site or listen for it.

**Scope of this ticket:** This ticket is to build the listener itself, the `openedx-core` receiver that subscribes to `PERSISTENT_SUBSECTION_GRADE_CHANGED`, calculates competency status from the event's payload, and persists it (`Student*Status` / `CompetencyMasteryStatuses` tables per ADR-0002/0003). This ticket owns the full subscribe → calculate → persist flow.

**Coordination:** Because PR \#545/\#587 aren't merged yet, this ticket's input contract is that event's payload shape, not a downstream API signature. Confirm the final `PersistentSubsectionGradeData` fields (`user_id`, `course`, `subsection_edited_timestamp`, `grading_policy_hash`, `usage_key`, `weighted_graded_earned/possible`, `weighted_total_earned/possible`, `first_attempted`) before merge, and re-check if either PR's schema changes before this ticket ships.

*Status: blocked on ticket 1.1 (CBE data model). Fully specified; ready to implement once 1.1 merges.*

## Use Case

As a **learner**, when I receive a grade for an assignment (gradeable subsection) that has a competency criterion attached, I want the platform to evaluate whether I have demonstrated the associated competency and persist my mastery status, so that my demonstrated competencies are recorded automatically and can be surfaced to me, to instructors, and to downstream credentialing without anyone manually reviewing my grades.

## Description

**Current state.** Traditional grades and material completion are the only way for a learner’s progress to be recorded in the platform.  Today nothing turns a grade into a competency status.

Competency Criteria will exist in the platform in a hierarchical fashion via the `CompetencyCriteriaGroup` and `CompetencyCriteria` tables. The topmost `CompetencyCriteriaGroup` is for the competency tag itself. Each child of it consists of groups for the courses containing subsections associated to the competency or for custom groupings defined by the platform administrator. Each `CompetencyCriteriaGroup` defines the `logic_operator` (AND or OR) by which its associated `CompetencyCriteria` should evaluate at its level. Each `CompetencyCriteria` is associated to a specific subsection that is used as an instrument for measuring the learner’s mastery status via the `rule_payload`. The `rule_payload` contains the operation (e.g. `gte` for “greater than”) and threshold value (e.g. 0.75 for 75%) that indicate whether the learner has demonstrated mastery on this subsection assignment. These models will come into existence as part of \#613. This provides the scaffolding needed for the development done for this ticket to be able to perform mastery status calculations. This is an example visual representation:  
![][image1]

**Requested change.** Add a listener to `openedx-core` that is notified when a learner’s grade has changed for a subsection. This listener will then (a) find the `CompetencyCriteria` attached to that content, (b) evaluate each leaf criterion against its resolved rule, (c) rolls leaf criterion results up the AND/OR `CompetencyCriteriaGroup` tree by boolean logic, and (d) appends rows to `StudentCompetencyCriteriaStatus`, `StudentCompetencyCriteriaGroupStatus`, and `StudentCompetencyStatus` — appending only when the computed status differs from the learner's latest row. openedx-core owns all CBE-model knowledge; the platform owns all grading knowledge.

**Out of scope (this ticket):** 

* the `openedx-events` production of subsection grade changed events  
* rule types other than `Grade` (`View`/`MasteryLevel` deferred — a non-Grade rule raises `NotImplementedError` during MVP)  
* criteria on courses, sections, units, or problems (MVP subsection only)  
* course-run-date windowing  
* re-evaluation on later criteria changes or regrades, and any lowering of a status (forward-only per decision — a separate follow-up)  
* any REST/UI surface.

## Acceptance Criteria

There is no HTTP or UI surface, so QA/Postman do not apply. Acceptance is determined by a PR reviewer confirming these scenarios are covered by automated unit tests exercising the API function directly; each Then names an observable result (return value or the specific row appended).

```
Scenario: Leaf criterion met
  Given a CompetencyCriteria on content C with a rule override {"op":"gte","value":75,"scale":"percent"}
  When learner L earns a grade of 80% on content C
  Then a StudentCompetencyCriteriaStatus row is appended for (L, that criterion) with status Demonstrated

Scenario: Leaf criterion attempted below threshold
  Given a CompetencyCriteria on content C with a rule override
  When learner L earns a grade of 60% on content C
  Then a StudentCompetencyCriteriaStatus row is appended for (L, that criterion) with status AttemptedNotDemonstrated

Scenario: Content has no associated criteria (clean no-op)
  Given content C with no CompetencyCriteria attached
  When learner L earns any grade on content C
  Then no rows are appended to any status table
  And the call returns without error

Scenario: Rule resolved via CompetencyRuleProfile fallback chain
  Given a criterion with no rule override and a CompetencyRuleProfile at the taxonomy level
  When the API evaluates that criterion
  Then the taxonomy-level profile is used (fallback order taxonomy -> course -> org -> system default)

Scenario: AND group fully satisfied
  Given a CompetencyCriteriaGroup with logic_operator AND over two leaf criteria, both Demonstrated for L
  When the group is evaluated
  Then a StudentCompetencyCriteriaGroupStatus row is appended with status Demonstrated
  And a StudentCompetencyStatus row is appended with status Demonstrated

Scenario: AND group partially attempted
  Given an AND group over two leaf criteria where one is Demonstrated and one has no status yet for L
  When the group is evaluated
  Then a StudentCompetencyCriteriaGroupStatus row is appended with status PartiallyAttempted
  And the StudentCompetencyStatus row appended is PartiallyAttempted

Scenario: OR group satisfied by one child
  Given an OR group over two leaf criteria where at least one is Demonstrated for L
  When the group is evaluated
  Then a StudentCompetencyCriteriaGroupStatus row is appended with status Demonstrated

Scenario: AND group fully not demonstrated
  Given an AND group over two leaf criteria, both AttemptedNotDemonstrated for L
  When the group is evaluated
  Then a StudentCompetencyCriteriaGroupStatus row is appended with status AttemptedNotDemonstrated
  And no StudentCompetencyStatus row is appended (competency-level table never records AttemptedNotDemonstrated)

Scenario: OR group fully not demonstrated
  Given an OR group over two leaf criteria, both AttemptedNotDemonstrated for L
  When the group is evaluated
  Then a StudentCompetencyCriteriaGroupStatus row is appended with status AttemptedNotDemonstrated
  And no StudentCompetencyStatus row is appended

Scenario: OR group partially attempted with one failed leaf
  Given an OR group over two leaf criteria where one is AttemptedNotDemonstrated and one has no status yet for L
  When the group is evaluated
  Then a StudentCompetencyCriteriaGroupStatus row is appended with status PartiallyAttempted

Scenario: Competency level never records AttemptedNotDemonstrated
  Given a top-level group that evaluates to AttemptedNotDemonstrated for L (all attempted, rule unmet)
  When the competency-level status is written
  Then no StudentCompetencyStatus row is written (the table is constrained to Demonstrated/PartiallyAttempted)
  And no database constraint is violated

Scenario: Duplicate identical evaluation is suppressed
  Given learner L already has a latest StudentCompetencyCriteriaStatus of Demonstrated for a criterion
  When the API is called again with a grade that yields Demonstrated
  Then no new row is appended for that criterion (append only on change)

Scenario: One content item feeding multiple competencies
  Given content C referenced by criteria in two different competencies for L
  When the API is called for L, content C, with a grade
  Then both competencies' trees are recomputed and their status rows appended as applicable

Scenario: Non-Grade rule type during MVP
  Given a resolved criterion whose rule_type is View or MasteryLevel
  When the API evaluates it
  Then NotImplementedError is raised (only Grade is supported in MVP)
```

## Context

- **Blocking dependency:** ticket **1.1** (CBE data model, ADRs 0002/0003). All models live at `src/openedx_learning/applets/cbe/models.py` after 1.1. Note 1.1's text uses a stale path (`openedx_learning/apps/competencies/`); ADR 0001 governs and the correct path is `src/openedx_learning/applets/cbe/`.  
- **Producer:** the openedx-events grade/completion emitter (already in development) that this listener waits for. Confirm the  `GradeResult` shape match what that listener already calls before finalizing.  
- **ADRs to read first:** `docs/openedx_learning/decisions/0001-competency-criteria-location.rst` (rejected alt \#8 — why the listener is not here), `0002-competency-criteria-model.rst` (the model, the bottom-up recompute, the competency-level status constraint), `0003-competency-criteria-versioning.rst` (append-only: current status \= latest row, persist only changes), and the new 0004 (this ticket).  
- **Technical Design Document:** [https://openedx.atlassian.net/wiki/spaces/OEPM/pages/5604573185/Competency+Criteria+Technical+Design+Document](https://openedx.atlassian.net/wiki/spaces/OEPM/pages/5604573185/Competency+Criteria+Technical+Design+Document)   
- **Prior art — public API pattern:** `src/openedx_tagging/api.py` (module docstring: callers use the API, not the models; no permission enforcement here — the caller authorizes) and the applet-facade pattern in `src/openedx_content/api.py` re-exporting each applet's `api.py`.  
- **Prior art — content \<-\> competency mapping:** a competency is a `Tag` in a `CompetencyTaxonomy`; the association is an `oel_tagging_objecttag` row whose `object_id` is an opaque, non-FK string (`src/openedx_tagging/models/base.py`). Criterion \-\> one objecttag \+ rule.  
- 

# Old Implementation Notes

Recommended approach: a synchronous evaluate-and-write API. The platform-side receiver + Celery task is already being built separately; this repo stays grading-agnostic and Celery-free. Match this API's signature to what that in-flight listener calls (confirm against its call site before merge).

Single public entry point in applets/cbe/api.py, keyword-only per house style: evaluate_and_record_competency_status(*, user_id: int, content_key: str, grade: GradeResult) -> Sequence[StudentCompetencyStatus]. content_key matches ObjectTag.object_id by string equality only (no opaque_keys import). GradeResult is a frozen dataclass in data.py carrying earned_percent: Decimal (named so future rule types extend it without a signature break). Wrap the whole body in one transaction.atomic().

Steps: (1) resolve CompetencyCriteria where the related oel_tagging_objecttag.object_id == content_key; (2) per criterion resolve the rule from rule_type_override/rule_payload_override if set, else the CompetencyRuleProfile fallback chain taxonomy -> course -> org -> system default (MVP rule_type == "Grade" only; other types raise NotImplementedError); (3) evaluate rule_payload {op, value, scale} against grade.earned_percent -> a CompetencyMasteryStatuses value (leaf is binary Demonstrated / AttemptedNotDemonstrated); (4) append StudentCompetencyCriteriaStatus only if it differs from the learner's latest row; (5) walk CompetencyCriteriaGroup.parent_id from each affected leaf to root, recomputing each group over children in ordering order with AND/OR boolean short-circuit (AND = Demonstrated iff all children Demonstrated; OR = iff any; PartiallyAttempted when some children are unattempted), appending StudentCompetencyCriteriaGroupStatus only on change; (6) map the root result to StudentCompetencyStatus (Demonstrated or PartiallyAttempted only — never AttemptedNotDemonstrated), appending only on change.

Idempotency is the ADR-0003 "current = latest row, persist only changes" rule: redelivery of the same grade computes the same status and appends nothing. Concurrency (two same-user events at once) is a known edge; serialization is the platform Celery task's job (per-user routing), not this API's.

Ship the entry point marked UNSTABLE so the input shape can absorb View/MasteryLevel rule types during MVP without a DEPR cycle. No permission checks here (per the openedx_tagging/api.py contract); the caller enforces authorization. New code needs tests — that is the acceptance bar since there is no QA path.
Example Resolution Prompt
In openedx-core (repo at openedx-core/), implement the CBE mastery-evaluation public API in the openedx_learning.applets.cbe applet. The data model already exists from ticket 1.1 per ADR 0002 — do not create or modify models or migrations. Create src/openedx_learning/applets/cbe/api.py with one public, keyword-only function evaluate_and_record_competency_status(*, user_id: int, content_key: str, grade: GradeResult) -> Sequence[StudentCompetencyStatus], declared in __all__ and marked UNSTABLE. Create src/openedx_learning/applets/cbe/data.py with a frozen GradeResult dataclass holding earned_percent: Decimal. Inside one transaction.atomic(), the function must: (1) find every CompetencyCriteria whose related oel_tagging_objecttag.object_id string-equals content_key (no opaque_keys parsing); (2) resolve each criterion's rule from rule_type_override/rule_payload_override when set, else from CompetencyRuleProfile via fallback taxonomy -> course -> org -> system default, supporting only rule_type == "Grade" (raise NotImplementedError for View/MasteryLevel); (3) evaluate the Grade rule_payload {"op","value","scale"} against grade.earned_percent to a CompetencyMasteryStatuses value; (4) append a StudentCompetencyCriteriaStatus row only if it differs from the learner's latest row for that criterion; (5) walk CompetencyCriteriaGroup.parent_id from each affected leaf to the root, recomputing each group over its children in ordering order with AND/OR boolean short-circuit and appending StudentCompetencyCriteriaGroupStatus only on change; (6) map the root result to StudentCompetencyStatus, which may only be Demonstrated or PartiallyAttempted (never AttemptedNotDemonstrated), appending only on change. Never import from openedx-platform, opaque_keys, or grading; enforce no permissions (callers do). Re-export the function from src/openedx_learning/api.py. Add tests/openedx_learning/applets/cbe/test_api.py covering fallback resolution, each Grade operator, nested AND/OR short-circuit, redelivery-is-a-no-op idempotency, the competency-level status constraint, and non-Grade raising. Verify with pytest tests/openedx_learning/applets/cbe/ -p no:cov and lint-imports.



Aspects team is dependant on this being completed so they can work on the instructor portion
