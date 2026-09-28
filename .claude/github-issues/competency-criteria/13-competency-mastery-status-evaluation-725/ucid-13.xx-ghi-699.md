# [BE] Evaluate learner’s criterion status for grade

GitHub: https://github.com/openedx/openedx-core/issues/699 (#699, OPEN)
Cached: 2026-09-25

## User Story

As a learner, I want each competency criterion tied to the subsection (assignment) I was just graded on to be checked as part of recording that grade, in order to have the mastery I just earned recorded at the same time the grade is.

## Acceptance Criteria

Scenarios tagged `@unit-test-only` describe a data state that normal authoring should prevent from arising. They're included for coverage, but can only be exercised by constructing the state directly in a test, not by reaching it through the product UI or API.

```
Scenario: A grade that meets a criterion's threshold demonstrates it
  Given a subsection is associated with a competency
    And a criterion for that competency requires at least 75% on that subsection
  When a grade of 80% for that subsection is recorded for a learner
  Then reading that learner's status for that criterion reports "demonstrated"

Scenario: A grade below a criterion's threshold does not demonstrate it
  Given the same criterion
  When a grade of 60% for that subsection is recorded for a learner
  Then reading that learner's status for that criterion reports that it is
    attempted but not demonstrated

Scenario: Content with no competency criteria is unaffected
  Given a subsection has no competency criteria associated with it
  When a grade for that subsection is recorded for a learner
  Then the grade is recorded
    And no competency status is created or changed for that learner

Scenario: A subsection tagged with an unrelated tag is unaffected
  Given a subsection is tagged with a tag that has no competency criteria associated with it
  When a grade for that subsection is recorded for a learner
  Then the grade is recorded
    And no competency status is created or changed for that learner

Scenario: One grade satisfies several criteria on their own terms
  Given the same subsection is used by two criteria belonging to different competencies
    And the two criteria require different grade thresholds
  When a single grade for that subsection is recorded for a learner
  Then each of the two criteria reports the status its own threshold implies

Scenario: A later lower grade does not take away a demonstrated criterion
  Given a learner's status for a criterion reports "demonstrated"
  When a lower grade for the same subsection is recorded for that learner
  Then that learner's status for that criterion still reports "demonstrated"

@unit-test-only
Scenario: A criterion whose rule cannot be applied is passed over
  Given a subsection is associated with two competency criteria
    And one of those criteria carries a rule that cannot be applied
  When a grade for that subsection is recorded for a learner
  Then the grade is recorded
    And the other criterion reports the status its threshold implies
    And the criterion that could not be applied is reported for investigation
      without preventing the grade from being recorded

@unit-test-only
Scenario: A criterion attached to a tag outside a competency taxonomy is not evaluated
  Given a competency criterion is associated with a tag that does not belong to a competency taxonomy
  When a grade for the associated subsection is recorded for a learner
  Then the grade is recorded
    And no competency status is created for that learner and criterion

Scenario: A subsection worth zero points produces no status
  Given a subsection associated with a competency is worth zero points, so a learner's
    score on it cannot be turned into a fraction of what was available
  When a grade for that subsection is recorded for a learner
  Then the grade is recorded
    And no status is created for the criteria associated with that subsection
    And the caller is not required to decide what a score out of zero total points means

Scenario: A grade that is not saved leaves no competency status behind
  Given a subsection is associated with a competency
  When a grade for that subsection is recorded for a learner
    and the recording of that grade does not complete
  Then no competency status exists for that learner and criterion

Scenario: Repeating an identical evaluation changes nothing
  Given a learner's status for a criterion already reports the value a grade implies
  When the same grade is recorded again for that learner
  Then that learner's status for that criterion is unchanged
    And the caller is told that nothing changed
```

## Description

Recording a grade in the LMS today saves the grade and nothing else, so a learner who earns a passing score on content carrying competency criteria gets no competency record. This ticket adds the function that works out and records the learner's status at the criteria attached to the graded content. \#642 provides the storage it writes to, and \#701 is the call from the grade write itself.

The LMS already converts a learner's score on a subsection into a decimal between zero and one representing the percent earned, and passes that value to this function. Each criterion already carries the rule it is judged against, either the rule profile assigned to it or its own overrides, so deciding which rule profile applies to a criterion is not part of this work. Computing the criteria groups and the competency above the criterion is \#643.

<details>
<summary>Technical Details</summary>

This section is background and a suggested approach, not the ticket's source of truth. The User Story and Acceptance Criteria define what must be true when the work is done.

### In short

**What this function does and where it is called from.** Given a learner and one or more graded subsections with the fraction the learner scored on each, it finds the competency criteria attached to those subsections, decides whether each criterion is now demonstrated, and writes the learner's leaf status rows. The LMS calls it from inside the same database transaction as the grade write, so the grade and the leaf status commit or fail together, which is the guarantee Decision 1 of the concurrency decision record exists to provide. \#701 makes those calls. Nothing in this repository calls this function.

**Why the caller passes a fraction rather than points.** `openedx-core` cannot read grades and must never try to. It also should not decide what a subsection percentage means, because the grades app already owns that, including the case where a subsection is worth zero points and the case where a staff member has overridden a score. So the contract is a small frozen data class carrying an opaque object id and a fraction between zero and one, and `openedx-core` compares that fraction against the criterion's rule. This also lets the same function serve any subsection grade without needing to know anything else about the subsection, which matters because the link from content to criteria is string equality on an opaque object id rather than a foreign key.

**Finding the criteria, and the common case where there are none.** A graded object is linked to a competency by an `ObjectTag` row on a tag that belongs to a competency taxonomy, and a criterion points at one such row. So resolving criteria is a single indexed query joining criteria to object tags on the object id, filtered to tags in a competency taxonomy, and on the overwhelming majority of grade writes it returns nothing and the function returns immediately. That fast path matters, because this code runs on one of the hottest write paths in the LMS. The taxonomy filter is defense in depth: authoring is expected to prevent a `CompetencyCriteria` from ever being created against a tag outside a competency taxonomy, but this function does not trust that guarantee and excludes such a criterion from evaluation rather than acting on it.

**Deciding a leaf's status.** Each criterion evaluates against either the rule profile assigned to it or its own per-criterion override, never both, and exactly one of those is always populated. For the rule type in scope, the rule is an operator and a threshold, and the criterion is demonstrated when the learner's fraction satisfies it. A leaf therefore takes only two of the three status values, Demonstrated or AttemptedNotDemonstrated. "Partially attempted" describes a group with some of its children done and never applies to a single graded object.

**A criterion whose rule cannot be applied does not stop the grade.** Because the grade and the leaf status share a transaction, an exception raised here rolls back the learner's grade. One malformed rule payload must therefore not be able to halt grading for a piece of content. An individual criterion whose rule type is unrecognized or whose payload fails validation is skipped and logged, and the remaining criteria for that object are still evaluated. The shared failure of Decision 1 is reserved for genuine storage failures, where the leaf genuinely cannot be written.

**Writing the status so two concurrent writers cannot disagree.** Decision 4 of the concurrency decision record says an automatic write may raise a status but never lower it, so the write is a single conditional `UPDATE` that fires only when the stored status is strictly lower than the newly computed one. The database evaluates the condition and the write together, so no lock and no retry loop is needed, and a write that loses a race simply affects zero rows. The function returns how many leaf rows it created or raised, which is what lets \#701 skip enqueuing a rollup when nothing actually changed.

### Implementation specifics

- **Public signature**, in `src/openedx_learning/applets/cbe/api.py` and added to its `__all__`: `def record_graded_object_statuses(*, user_id: int, scores: Sequence[GradedObjectScore]) -> int`. It returns the number of `StudentCompetencyCriteriaStatus` rows created or raised. Its docstring must state that the caller is required to be inside a transaction that also contains the grade write.  
- **The data class**, in `src/openedx_learning/applets/cbe/data.py`: a frozen dataclass `GradedObjectScore` with `object_id: str` and `fraction: Decimal`. Export it alongside the function.  
- **State the fraction's definition in the docstring, not just its range.** `fraction` is the caller's authoritative, override-adjusted score for the object as a value between zero and one. This function validates the range and nothing else; it cannot detect a caller that passed an unadjusted value, so the docstring is the only place that contract is expressible. A fraction outside zero to one raises `ValueError`.  
- **Keep the zero-possible case out of the library.** `openedx-core` has no notion of points, so a caller with nothing available to earn omits the object rather than passing `Decimal("0")`. Say so in the docstring next to the range check.  
- **This function must not open its own transaction** and must not swallow storage exceptions. An inner `atomic()` block would commit independently of the grade, and a caught storage error would commit a grade without its leaf. Both break Decision 1\.  
- **Criteria resolution** is one query, `CompetencyCriteria.objects.filter(<object tag field>__object_id__in=[...], <object tag field>__tag__taxonomy__<competency-taxonomy indicator>=True).select_related(<object tag field>, "competency_rule_profile")`, backed by the object-tag and criteria indexes in the model decision record. The exact field names for the `ObjectTag` foreign key and for identifying a competency taxonomy are whatever the criteria and taxonomy definition models define. The taxonomy filter is defense in depth: authoring is expected to prevent a `CompetencyCriteria` from ever being created against a tag outside a competency taxonomy, but this function does not trust that guarantee and excludes such a criterion from the query rather than evaluating it. Criteria whose `ObjectTag` is archived are also skipped, using the soft-delete field Decision 3 of the versioning decision record requires; if that field does not exist yet, note the gap on the issue rather than inventing one.  
- **Rule resolution and evaluation go in a new internal module** `src/openedx_learning/applets/cbe/rules.py`, not in `api.py`, with a function returning the effective rule type and payload for a criterion and a function mapping a rule and a fraction to a `MasteryStatus`. Keep both out of `__all__`: the authoring validation work will reuse the payload validator from inside the same applet, and an internal function is free to change while a published one is not.  
- **Supported rule and payload:** `rule_type` `"Grade"` with `{"op": "gte"|"lte"|"eq", "value": <0.0-1.0>, "scale": "percent"}`. An unrecognized `rule_type` or a payload failing validation is skipped and logged at warning level, with the criterion id and the reason in the log line, and evaluation continues with the remaining criteria.  
- **The monotone write** is `get_or_create` on `(user_id, competency_criteria_id)` with the computed status as the default, then, when the row already existed, `.filter(pk=..., status_id__in=<ids strictly below the computed status>).update(status_id=..., modified=now)`. Do not read the row into Python and compare there: two writers would both read the old value and the later write could lower it. A zero-row update result is a normal outcome, not an error.  
- **Do not write a row for an object the learner has not attempted.** The caller is responsible for not passing them; this function writes a row for every score it is given.  
- **Tests** in `tests/openedx_learning/applets/cbe/test_leaf_status_api.py`: an object with no criteria returns zero and issues no writes; one object referenced by criteria in two different groups writes two leaf rows; a criterion using an assigned profile and one using a per-criterion override both evaluate against the right threshold; each of the three operators at, just below, and just above the threshold; a fraction outside zero to one raises `ValueError`; a second call with a lower fraction leaves an already-demonstrated row unchanged and returns zero; a second call with the same fraction returns zero; a criterion with an invalid payload is skipped and logged while its sibling criterion is still evaluated; a criterion whose tag belongs to a taxonomy that is not a competency taxonomy is excluded from resolution and produces no status, even though authoring is expected to prevent this state from arising. Rule resolution and payload validation get their own tests in `tests/openedx_learning/applets/cbe/test_rules.py`.  
- **Out of scope:** course-level criteria, since this function only evaluates criteria attached to a subsection; the rollup above the leaf is \#643; the platform-side transaction and call sites are \#701; and rule profile scope precedence never runs at evaluation time because a criterion's assigned profile is decided when the criterion is authored.

Files to create and modify **New files**

| File | Purpose |
| :---- | :---- |
| src/openedx\_learning/applets/cbe/rules.py | resolve a criterion's effective rule and evaluate a fraction against it |
| tests/openedx\_learning/applets/cbe/test\_leaf\_status\_api.py | evaluation, override precedence, and monotone-write tests |
| tests/openedx\_learning/applets/cbe/test\_rules.py | rule resolution and payload validation tests |

**Modified files**

| File | Nature of modification |
| :---- | :---- |
| src/openedx\_learning/applets/cbe/api.py | add `record_graded_object_statuses` and `GradedObjectScore` to the public surface |
| src/openedx\_learning/applets/cbe/data.py | add the `GradedObjectScore` frozen data class |

- Context `docs/openedx_learning/decisions/0004-competency-mastery-concurrency.rst`, Decisions 1 and 4 for the shared transaction and the raise-only rule, and Rejected Alternatives 1, 2, and 7 for why there is no lock and no retry loop.  
- `docs/openedx_learning/decisions/0002-competency-criteria-model.rst`, Decisions 3 and 4, for the rule profile, the override rules, and the payload shape.  
- `docs/openedx_learning/decisions/0003-competency-criteria-versioning.rst`, Decision 3, for the archived object-tag rule.  
- Public-API pattern: `src/openedx_content/api.py` for the umbrella wildcard import over applet `api.py` modules declaring `__all__`, and `src/openedx_tagging/api.py` whose module docstring states that consumers use the API rather than the models and that the caller enforces authorization.  
- `src/openedx_tagging/models/base.py` for `ObjectTag` and its polymorphic, non-foreign-key `object_id`.  
- Depends on \#642 for the status models and `MasteryStatus`. Consumed by \#701. Documented by \#729.
</details>
