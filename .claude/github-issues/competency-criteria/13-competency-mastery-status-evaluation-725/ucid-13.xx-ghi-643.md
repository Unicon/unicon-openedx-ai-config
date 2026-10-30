# [BE] Roll up a learner's competency status from criterion to competency after a grade is recorded

GitHub: https://github.com/openedx/openedx-core/issues/643 (#643, OPEN)
Cached: 2026-10-29

## User Story

As a learner, I want my competency mastery to settle on the right value after any of my subsection grades changes, including when several pieces of my work are graded at the same time and including for the parent competencies above the one I was assessed on, in order to trust what the platform tells me and my institution I have mastered.

## Acceptance Criteria

Scenarios tagged `@unit-test-only` describe a data state that no authoring endpoint can produce. They're included for coverage, but can only be exercised by constructing the state directly in a test, not by reaching it through the product UI or API.

```
Scenario: Completing the last requirement demonstrates the competency
  Given a competency requires two assignments together
    And a learner has demonstrated the criterion for the first assignment
  When the learner's grade for the second assignment is recorded as demonstrated
  Then that learner's overall status for the competency reports "demonstrated"

Scenario: Completing one of several requirements shows progress
  Given a competency requires two assignments together
    And a learner has no status for either
  When the learner's grade for the first assignment meets its threshold
  Then that learner's overall status for the competency reports "partially attempted"

Scenario: Attempting every requirement and failing one shows the failure
  Given a competency requires two assignments together
  When a learner has attempted both and met the threshold for only one
  Then that learner's status for the criteria group reports
    "attempted but not demonstrated"

Scenario: Either alternative route demonstrates the competency
  Given a competency can be demonstrated by either of two alternative routes
  When a learner demonstrates every requirement of one route
  Then that learner's overall status for the competency reports "demonstrated"
    And the other route is not required

Scenario: Attempting some alternative routes without succeeding shows progress
  Given a competency can be demonstrated by either of two alternative routes
  When a learner has attempted one route without meeting its threshold
    And has not attempted the other route at all
  Then that learner's status for the criteria group reports "partially attempted"

Scenario: Failing every alternative route shows the failure
  Given a competency can be demonstrated by either of two alternative routes
  When a learner has attempted both routes and met the threshold for neither
  Then that learner's status for the criteria group reports
    "attempted but not demonstrated"

Scenario: A group with nothing attempted beneath it has no status
  Given a criteria group whose requirements a learner has not attempted at all
  When that learner's statuses are recomputed
  Then no status is reported for that learner at that group

@unit-test-only
Scenario: A root group still evaluates correctly if authored as AND
  Given a competency's root group combines its children with AND, a state no
    authoring endpoint can produce
  When a learner demonstrates every child of that root group
  Then that learner's overall status for the competency reports "demonstrated"

Scenario: Nested criteria groups roll up level by level
  Given a competency's root group has a course-level group as one of its branches
    And that course-level group requires a bottom-tier group of two assignments together
  When a learner demonstrates both assignments in that bottom-tier group
  Then that learner's status for the bottom-tier group, the course-level group,
    and the competency all report "demonstrated"

Scenario: Two assignments graded at the same time both count
  Given a competency requires two assignments together
    And a learner has no status for either
  When grades for both assignments are recorded for that learner at the same time
    And both recordings have completed
  Then that learner's overall status for the competency reports the value that
    reflects both grades, not the value either grade alone would imply

Scenario: Repeated or out-of-order recomputation never sets a learner back
  Given a learner's statuses report their current values
  When the recomputation for that learner runs again, or runs in a different order
    than the grades were recorded
  Then no status for that learner reports a lower value than it did before

Scenario: A recomputation that fails partway reaches the right answer on retry
  Given a recomputation for a learner does not complete
  When it is retried
  Then that learner's statuses report the same values a single completed
    recomputation would have produced

Scenario: A failed root group is not reported as a failed competency
  Given a learner's status at a competency's root group reports "attempted but not
    demonstrated"
  When the computation for that learner completes
  Then that learner's overall status for that competency reports "partially attempted"

Scenario: A level whose value does not change is left alone
  Given a learner's status at a criteria group already reports the value the
    recomputation would produce
  When the recomputation for that learner completes
  Then that group's status reports the same value
    And its last-changed time is unchanged

Scenario: A parent competency is demonstrated by its own requirements alone
  Given a parent competency has its own requirements and three sub-competencies
  When a learner meets the parent's own requirements
    But has not demonstrated every sub-competency
  Then that learner's status for the parent competency reports "demonstrated"

Scenario: A parent competency is demonstrated by its sub-competencies alone
  Given a parent competency has its own requirements and three sub-competencies
  When a learner has not met the parent's own requirements
    But every one of those sub-competencies reports "demonstrated" for that learner
  Then that learner's status for the parent competency reports "demonstrated"

Scenario: A parent competency shows progress when neither source is complete
  Given a parent competency has its own requirements and three sub-competencies
  When a learner has not met the parent's own requirements
    And has demonstrated only some of those sub-competencies
  Then that learner's status for the parent competency reports "partially attempted"

Scenario: An unearnable sub-competency does not block a parent with its own requirements
  Given a parent competency has its own requirements and two sub-competencies
    And one of those sub-competencies has no requirements attached anywhere beneath it
  When a learner meets the parent's own requirements
  Then that learner's status for the parent competency reports "demonstrated"

Scenario: A sub-competency nobody can earn permanently blocks its parent
  Given a parent competency has two sub-competencies
    And one of them has no requirements attached anywhere beneath it
  When a learner demonstrates the other sub-competency
    And the parent has no requirements of its own
  Then that learner's status for the parent competency reports "partially attempted"

Scenario: Rollup reaches the top of the competency hierarchy
  Given a competency sits three levels below the top of its framework
  When a learner demonstrates that competency
  Then every ancestor competency above it has its status brought up to date
    And the recomputation stops at the top of the framework
```

## Description

Once a learner's status at an individual competency criterion has been recorded alongside their grade, everything above that criterion is out of date: each criteria group containing it, the competency itself, and every parent competency above that one. Nothing recomputes those levels today.

This ticket adds the function that does. It runs after the grade has committed, from the Celery task \#701 adds, and it reads the criterion statuses \#642 stores. Splitting the work this way is deliberate: two grade changes for the same learner can be in flight at once, and letting each recompute shared parent nodes inside its own grade transaction is what would make both of them wrong.

<details>
<summary>Technical Details</summary>

This section is background and a suggested approach, not the ticket's source of truth. The User Story and Acceptance Criteria define what must be true when the work is done.

### In short

**What runs, and when.** This function recomputes every level above a changed criterion. It runs asynchronously, after the grade has committed, from a Celery task in the LMS. It has two phases: first upward through the criteria groups to the competency the graded content was attached to, then upward again through that competency's parents to the top of the framework.

**Why it runs in no transaction at all.** Each level commits before the next level is read. A writer therefore only ever reads values that have finished, so whichever of two concurrent writers reads a parent last sees all of that parent's children at their final values and computes the right answer. Wrapping the walk in a transaction would defeat exactly this, by hiding each writer's changes from the other until both had finished, which is the original problem moved one level up the tree and made harder to diagnose. So this function must not open a transaction and must not take a lock, and there is a test that fails if someone adds one.

**How a criteria group's status is computed.** A group combines its children with AND or OR, and its children are evaluated in the group's stored ordering so the result is deterministic and can be settled early. An AND group is demonstrated when every child is; it is attempted-and-not-demonstrated as soon as any child is, which is what lets evaluation stop before reading later siblings; otherwise, if any child has a status at all, it is partially attempted. An OR group is demonstrated as soon as any child is; it is attempted-and-not-demonstrated only when every child is; otherwise it is partially attempted. A group with no attempted children at all gets no row, because nothing beneath it has been attempted.

**The competency level is narrower than the group level.** The record for a competency holds only demonstrated or partially attempted. Attempted-and-not-demonstrated is deliberately excluded there, because deciding that a learner has run out of ways to earn a competency depends on which courses they are or could still be enrolled in, which this code cannot know. So a root group that is attempted-and-not-demonstrated maps up to partially attempted.

**How a parent competency's status is computed.** Competencies are hierarchical, so recording a status for the competency a graded assignment was attached to is not the end of the work. A parent competency is demonstrated when either of two sources of evidence is fully satisfied: its own requirements, where it has criteria attached directly, or every one of its sub-competencies, the same either-suffices pattern already used for two alternative routes within a criteria group. Every sub-competency counts toward that second source, including one that has no requirements attached anywhere in its own subtree; such a sub-competency can never be demonstrated by anyone, so it permanently keeps the sub-competency route from succeeding, though a parent that also has its own requirements can still be demonstrated through that route alone. An unattached sub-competency is treated as an authoring gap, not a valid organizational marker: it stays in the aggregate rather than being silently excluded, and it does not raise an exception. Reporting the gap to a human is out of scope here. Where a parent has only one of the two sources, that source alone decides it, and where neither source is fully satisfied, the parent is partially attempted as soon as either one shows any progress.

**Where the parent walk stops, and why its cost is bounded.** It follows each competency's parent until it reaches one with no parent. Taxonomies enforce a maximum depth, so this is a small fixed number of steps rather than an open-ended traversal, and because a tag's parents are always in the same taxonomy the walk cannot leave the competency framework it started in.

**Every write here raises or does nothing.** Each level's write is the same single conditional `UPDATE` that \#699 uses: it fires only when the stored value is strictly lower than the computed one. That is what makes this safe without locks, and it is also what makes Celery's repeated and out-of-order delivery harmless, so the task needs no deduplication and can be retried freely.

### Implementation specifics

- **Public signature**, in `src/openedx_learning/applets/cbe/api.py` and added to its `__all__`: `def roll_up_competency_statuses(*, user_id: int, object_ids: Sequence[str]) -> None`. Its docstring must state that the caller must not be inside a transaction, and that repeated calls with the same arguments are safe.  
- **Do not call `transaction.atomic()` anywhere in this code path**, and do not take a row lock. Add a test asserting the walk issues its writes as separate committed statements, for example under `TransactionTestCase` or by asserting no savepoint is opened.  
- **Resolve the affected criteria from `object_ids`** using the same indexed query \#699 uses, rather than accepting criterion row primary keys, so a redelivered or delayed task recomputes from committed state and its Celery log stays readable.  
- **Phase one walks one level at a time, deduplicating.** Collect the parent group ids of all affected criteria, compute and write that whole level, then collect their parents, and repeat until a group with a null parent. A group reached from two different affected criteria must be computed once per level, not twice.  
- **Read a group's children as a set of statuses**, combining child `StudentCompetencyCriteriaGroupStatus` rows and child `StudentCompetencyCriteriaStatus` rows, ordered by the child's `ordering`. Absence of a row is a distinct state from any of the three values and means not attempted.  
- **A null `logic_operator` is treated as OR**, per ADR 0002 Decision 2: null occurs only for a group with a single child, where the combining logic is moot, and the application layer treats it the same as OR. Rejecting null at the model level belongs to the criteria definition work, not here.  
- **At a root group**, additionally write `StudentCompetencyStatus` for that group's competency tag, mapping `AttemptedNotDemonstrated` to `PartiallyAttempted` so \#642's check constraint holds. A competency has exactly one root group: \#665's partial `UniqueConstraint` on `CompetencyCriteriaGroup` (one root per competency) makes a second one impossible to create, not merely unsupported by the UI, so combining multiple root groups needs no handling here.  
- **Phase two walks upward via `Tag.parent_id`**, stopping when it is null. `TAXONOMY_MAX_DEPTH` in `src/openedx_tagging/models/base.py` bounds the iterations. Deduplicate: two graded competencies under the same parent must recompute that parent once.  
- **A parent tag's status is the OR of two computed inputs**, the same combination already used for alternative routes within a criteria group. The first is the parent's own criteria result from phase one, where the parent has root criteria groups. The second is the child-tag aggregate over every direct sub-competency: `Demonstrated` when every direct sub-competency has a `StudentCompetencyStatus` row and all of them are `Demonstrated`; `PartiallyAttempted` when at least one has a row; no contribution when none does. A sub-competency whose entire subtree, itself and every descendant, owns no root criteria group anywhere can never receive a `StudentCompetencyStatus` row by either path: it has no criteria of its own, and none of its children can reach `Demonstrated` either, by this same rule one level down. Such a sub-competency permanently caps the child-tag aggregate below `Demonstrated`, without capping the parent's own-criteria input. A sub-competency that instead has criteria somewhere lower in its subtree, even with none of its own, can still reach `Demonstrated` through its own children. Where only one input is present, that input alone decides the parent. Where both are present, the parent is `Demonstrated` as soon as either one is, and `PartiallyAttempted` when neither is but at least one shows progress. Implement the combination in one named function with the rule stated in its docstring, so a later change is a one-place edit.  
- **`AttemptedNotDemonstrated` never appears at the tag level**, so the three-value group truth table does not recur in phase two.  
- **Use one shared monotone-write helper** for all three status tables, in `src/openedx_learning/applets/cbe/statuses.py`. Extract it in this ticket if \#699 left it inline; several call sites now need it, so extraction is warranted rather than premature. A zero-row `UPDATE` result is a normal outcome and must not be treated as an error, because a discarded too-low value is the mechanism working.  
- **Tests** in `tests/openedx_learning/applets/cbe/test_rollup_api.py` for phase one: a three-deep tree with OR at the root and AND beneath it produces the expected value at every level; a root group with `logic_operator` set to `AND` (constructed directly, since no authoring endpoint can produce it, per \#760's dedicated rejection of root-group updates) still evaluates correctly; a group with a null `logic_operator` and a single child evaluates the same as an explicit OR; an AND group with one attempted-and-not-demonstrated child settles without reading later siblings; a group with no attempted children gets no row; a group whose stored status is already higher than the recomputed one is left alone and the walk continues upward; two sequential calls simulating the concurrency case, where each writer sees only one of two required assignments finished, end with the group correct after both have run; the competency-level row never receives `AttemptedNotDemonstrated`; a call for an object with no criteria does nothing and does not raise.  
- **Tests** in `tests/openedx_learning/applets/cbe/test_tag_rollup.py` for phase two: a three-level tag tree where demonstrating the only sub-competency raises the parent and the grandparent; a parent whose own criteria are met but one sub-competency is outstanding resolves to `Demonstrated` through the own-requirements route alone; a parent whose own criteria are not met but every sub-competency is demonstrated resolves to `Demonstrated` through the sub-competency route alone; a parent with neither route complete but some progress on either resolves to `PartiallyAttempted`; a child whose entire subtree has no root criteria group permanently withholds `Demonstrated` from the sub-competency route, without blocking a parent whose own requirements are met; the same unearnable child permanently caps a parent that has no requirements of its own at `PartiallyAttempted`, since the sub-competency route is that parent's only source; a child with no criteria of its own but a grandchild that has some does participate; a parent whose stored status is already `Demonstrated` is not lowered when a sibling branch is only partially attempted; a tag at the taxonomy root terminates the walk; two graded competencies sharing a parent recompute that parent once.  
- **Amend the model decision record** in this ticket's PR: `StudentCompetencyStatus` may hold a row for any tag in a competency taxonomy's hierarchy, not only a tag that owns a criteria tree; a parent tag's status is the OR of its own criteria result and every one of its direct sub-competencies, with a sub-competency that owns no root criteria group anywhere in its subtree permanently unable to reach `Demonstrated` through the sub-competency route, though not blocking a parent that also has its own requirements; and the bottom-up materialization flow gains a fourth step continuing upward through `Tag.parent` to the taxonomy root.  
- **Out of scope:** combining more than one root group per competency, which \#665's `UniqueConstraint` makes impossible to create in the first place; the Celery task, its retry policy, and its queue are \#701. The operator recompute command is \#774, and reporting a sub-competency with no criteria anywhere beneath it to a human belongs there or in a later authoring-time check, not in the per-learner rollup. Staff corrections that lower a status, and their root-group lock, are not covered by any current work.

Files to create and modify **New files**

| File | Purpose |
| :---- | :---- |
| src/openedx\_learning/applets/cbe/rollup.py | both walk phases, AND/OR evaluation with ordered short-circuit, parent-competency combination |
| src/openedx\_learning/applets/cbe/statuses.py | the shared monotone conditional-update helper for all three status tables |
| tests/openedx\_learning/applets/cbe/test\_rollup\_api.py | tree-shape, short-circuit, concurrency, and no-transaction tests |
| tests/openedx\_learning/applets/cbe/test\_tag\_rollup.py | parent-competency walk, participating-child, and termination tests |

**Modified files**

| File | Nature of modification |
| :---- | :---- |
| src/openedx\_learning/applets/cbe/api.py | add `roll_up_competency_statuses` to the public surface |
| docs/openedx\_learning/decisions/0002-competency-criteria-model.rst | Decision 6: status rows for any tag in the hierarchy, the parent-competency rule, and the parent-tag step in the materialization flow |

- Context `docs/openedx_learning/decisions/0004-competency-mastery-concurrency.rst`, Decisions 2, 3, and 4, and Rejected Alternatives 2 and 8, for why each level commits before the next is read, why every write is raise-only, and why there is no read-after-write check.  
- `docs/openedx_learning/decisions/0002-competency-criteria-model.rst`, Decision 2, for `logic_operator`, `ordering`, the worked short-circuit example, and the maximum authoring depth, and Decision 6.4 for the two values allowed at the competency level.  
- `src/openedx_tagging/models/base.py` for `Tag.parent`, `Tag.depth`, and `TAXONOMY_MAX_DEPTH`.  
- `.claude/architecture-taxonomies-and-competencies.md` for how competencies sit on the tagging models.  
- Depends on \#642 for the status tables and \#699 for the criterion statuses it reads. Consumed by \#701. Documented by \#729.

</details>
