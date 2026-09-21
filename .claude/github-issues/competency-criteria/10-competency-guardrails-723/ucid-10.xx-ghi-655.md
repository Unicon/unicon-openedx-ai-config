# [Arch] Implementation approach for competency data delete/edit guardrails

GitHub: https://github.com/openedx/openedx-core/issues/655 (#655, CLOSED)
Cached: 2026-09-21

## Context

`docs/openedx_learning/decisions/0002-competency-criteria-model.rst` (Decision 7, "Delete protection boundaries") and `0003-competency-criteria-versioning.rst` (Decision 4, "Authoring guardrails must warn on potentially impactful edits") already decide what should happen when a Platform Administrator or Course Author tries to change competency taxonomy data once a related learner mastery status exists:

- Hard delete is blocked once any related `StudentCompetencyStatus`, `StudentCompetencyCriteriaGroupStatus`, or `StudentCompetencyCriteriaStatus` row exists, for `Taxonomy`/`CompetencyTaxonomy`, `Tag`, `ObjectTag`, `CompetencyCriteriaGroup`, and `CompetencyCriteria`.
- `CompetencyRuleProfile` is never hard-deletable, with or without learner status.
- Edits are allowed even after learner status exists, but must warn the user and require explicit confirmation.

What's not yet decided is **how to implement this**: how to compute and surface a "can this be deleted" signal on the relevant GET endpoints without introducing N+1 queries, and where the corresponding write-path validation should live so the rule is actually enforced, not just hinted at in the UI.

## Ask

Agree on the implementation approach below before opening execution tickets against it. See the proposal in the comment.

## Scope

In scope:
- `CompetencyCriteria`, `CompetencyCriteriaGroup`, `CompetencyRuleProfile`, `Tag`, `Taxonomy`/`CompetencyTaxonomy`, `ObjectTag`

Out of scope for this MVP (raised as an open question in the proposal, not silently assumed):
- Gradeable subsection edit/delete behavior when a subsection has contributed to a learner's competency status. No existing Open edX precedent blocks or warns on this today; the proposal recommends staying at parity with current behavior for now.
- Archiving/restore UI beyond what ADR-0002/0003 already require for delete-protected records.
