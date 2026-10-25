# [BE] Delete Orphan CompetencyCriteriaGroups on ObjectTag Hard Delete

GitHub: https://github.com/openedx/openedx-core/issues/895 (#895, OPEN)
Cached: 2026-10-20

## User Story
As a course author, when I delete a subsection or re-import a course that results in the deletion of a tag association, I want the competency criteria group that held the rule for that content to be cleaned up the same way it would if I had removed the rule on the Competency Management page, in order to never be left with an empty group on the page that I cannot explain or remove, and that can block learners from being able to demonstrate the related competency in my course.

## Description
Add a listener to the CBE applet for Django's built-in post_delete signal that fires when an ObjectTag hard deletes a criterion and use the code written for #674 to walk up the hierarchy from the deleted criterion to also delete any CompetencyCriteriaGroups that would have been orphaned. This will prevent these orphans from existing for the cases of a block being deleted or a course re-import causing deletions.


## Context
- Blocked by #674, which implements the upward pruning for a criterion removed on the Competency Management page.
- #779 makes every tagging-layer delete path archive an association that learner mastery depends on and hard-delete the rest. This ticket covers what the hard-delete branch does to the criteria on that association.

## Acceptance Criteria

In these scenarios, a rule is a competency criterion. A competency's rules sit in bottom-tier groups. The bottom-tier groups for a course sit under that course's one course-level group, and every course-level group for a competency sits under that competency's one shared root group. "Group cleanup" means the removal or archiving of groups that this ticket adds after deleting a tag association removes a rule. Scenarios tagged `@unit-test-only` need a state or a failure that no product flow produces, and are exercised by constructing it directly in a test.

```
Scenario Outline: Deleting a subsection removes the groups its deletion leaves empty
  Given a bottom-tier group holds exactly one rule, and that rule measures a subsection
    And <what else the competency has>
    And no learner progress has been recorded against any of that competency's rules or groups
  When an author deletes that subsection in Studio
  Then that bottom-tier group no longer exists
    And <what happens above it>
    And no group with nothing beneath it remains anywhere in that competency's rules
    And the Competency Management page shows <what the page shows>
    And the application log records the group cleanup for the deleted rule

  Examples:
    | what else the competency has | what happens above it | what the page shows |
    | the course-level group above it requires all of its bottom-tier groups, and holds one other bottom-tier group with a rule | the course-level group still exists and holds only the other bottom-tier group | the other bottom-tier group and its rule for that course |
    | the course-level group above it holds nothing else, and another course has rules for the competency | the course-level group no longer exists, and the shared root group and the other course's groups are unchanged | the other course's groups and rules, and nothing for the first course |
    | the course-level group above it holds nothing else, and no other course has rules for the competency | the course-level group and the shared root group no longer exist | the same empty state it shows for a competency that has never had rules |

Scenario: Removing an emptied group lets a learner demonstrate a competency that requires all of its groups
  Given the course-level group for a competency requires all of its bottom-tier groups
    And it holds two bottom-tier groups, each with one rule, one measuring subsection S and the other measuring subsection T
    And no learner progress has been recorded against any of that competency's rules or groups
  When an author deletes subsection S in Studio
    And a learner then demonstrates the rule that measures subsection T, using the group rollup #870 adds
  Then the learner's status for the competency is Demonstrated

Scenario: Deleting a subsection that leaves other rules in its group removes no group
  Given a bottom-tier group holds two rules that measure two different subsections
    And no learner progress has been recorded against either rule
  When an author deletes one of those subsections in Studio
  Then the bottom-tier group still exists and holds the other rule
    And the course-level group and the shared root group above it are unchanged
    And the application log records no group cleanup

Scenario: Deleting the section that contains a tagged subsection leaves that subsection's rule alone
  Given a subsection is measured by a rule that is the only rule in its bottom-tier group
    And no learner progress has been recorded against that rule
  When an author deletes the section that contains that subsection in Studio
  Then that subsection's rule and its bottom-tier group still exist, unchanged
    And the rule is still listed in its group on the Competency Management page
    And the application log records no group cleanup

Scenario Outline: A group that holds learner history is archived instead of removed
  Given a bottom-tier group's only live rule measures a subsection, and no learner progress has been recorded against that rule
    And <the learner history the group holds>
  When an author deletes that subsection in Studio
  Then that bottom-tier group still exists in an archived state
    And it is no longer among the course's groups in use on the Competency Management page
    And all learner progress recorded against that group and the rules under it is unchanged
    And if the course-level group above it now holds only archived groups, the course-level group is archived too rather than removed

  Examples:
    | the learner history the group holds |
    | the group also holds a rule that was archived earlier because learner progress had been recorded against it |

  @unit-test-only
  Examples:
    | the learner history the group holds |
    | learner progress has been recorded against the group itself, though not against any rule in it |

Scenario: One deletion removes rules for several competencies
  Given a subsection is measured by one rule for competency A and one rule for competency B
    And competency A's rule is the only rule in its bottom-tier group, and that group's course-level group holds nothing else
    And competency B's rule shares its bottom-tier group with a rule that measures a different subsection
    And no learner progress has been recorded against any rule or group of either competency
  When an author deletes that subsection in Studio
  Then competency A's bottom-tier group and course-level group no longer exist
    And competency B's bottom-tier group still exists and holds only its other rule
    And competency B's course-level group and shared root group are unchanged

@unit-test-only
Scenario: Two rules in one group removed by the same deletion are cleaned up once
  Given one tag association on a subsection is measured by two rules in the same bottom-tier group, a state no authoring endpoint produces
    And that bottom-tier group holds nothing else, and no learner progress has been recorded against it or its rules
  When that subsection is deleted
  Then the bottom-tier group no longer exists, and its change history records a single removal
    And the application log records no group cleanup failure

Scenario: Re-importing a course removes the groups its tag import leaves empty
  Given a course's subsection is measured by a rule that is the only rule in its bottom-tier group
    And no learner progress has been recorded against that rule
  When the course is re-imported from an export that still tags that subsection with that competency but carries no competency rules
  Then the import completes, and the subsection is tagged with that competency
    And that rule no longer exists
    And that bottom-tier group, and every group above it that the rule's removal leaves empty, no longer exist
    And the Competency Management page shows no empty group for that course

Scenario Outline: A rule with learner progress keeps its group when its content's tags are deleted
  Given a subsection is measured by a rule that is the only rule in its bottom-tier group
    And learner progress has been recorded against that rule
  When <the deletion>
  Then the rule and its bottom-tier group still exist
    And the learner progress recorded against that rule is unchanged
    And the application log records no group cleanup

  Examples:
    | the deletion |
    | an author deletes that subsection in Studio |
    | the course is re-imported from an export that still tags that subsection with that competency |

Scenario Outline: Rule deletions that do not start from deleting a tag association are left to their own flow
  Given a competency with rules and groups in a course, and no learner progress recorded against any of them
  When <the deletion>
  Then <the outcome>
    And the application log records no group cleanup and no group cleanup failure for it

  Examples:
    | the deletion | the outcome |
    | an author removes the last rule in a bottom-tier group on the Competency Management page | the removal succeeds, and that group and every group above it left empty are removed |
    | an author removes a bottom-tier group and its rules on the Competency Management page | the removal succeeds, and the group, its rules, and every group above it left empty are removed |
    | an administrator deletes the competency | the deletion succeeds, and the competency's groups and rules are removed with it |
    | a course run that has rules for the competency is deleted from the catalog | the deletion succeeds |

@unit-test-only
Scenario Outline: A group cleanup failure leaves the groups in place and does not fail the deletion
  Given a subsection is measured by a rule that is the only rule in its bottom-tier group, with no learner progress recorded against it
    And the group cleanup is forced to fail after it has removed that bottom-tier group
  When <the deletion>
  Then the deletion or import completes, and that rule no longer exists
    And the bottom-tier group remains in place, empty, and every group above it is unchanged
    And the application log records a warning that identifies the group left in place

  Examples:
    | the deletion |
    | that subsection is deleted |
    | the course is re-imported from an export that still tags that subsection with that competency |

Scenario Outline: Group cleanup does not depend on who caused the deletion
  Given a subsection is measured by a rule that is the only rule in its bottom-tier group, with no learner progress recorded against it
  When <who> deletes that rule's tag association
  Then that bottom-tier group, and every group above it left empty, no longer exist

  Examples:
    | who |
    | a course author who cannot manage that competency's rules on the Competency Management page, by deleting the subsection in Studio |
    | a course import running as a background task, by re-importing the course |
```

<details>
<summary>Technical Details</summary>

This is a suggested approach, not the source of truth. The User Story, Description, and Acceptance Criteria define what must be true when the work is done.

**Summary**

A new `post_delete` receiver on `CompetencyCriterion` runs #674's upward pruning whenever a criterion is deleted because its ObjectTag was deleted, which happens when an author deletes a tagged subsection or a course re-import replaces the course's tags. The receiver ignores every delete that starts anywhere else, so #674's and #675's own flows are unaffected. Pruning runs in a savepoint, so a failure logs a warning and leaves the empty group in place instead of failing the tagging delete. There is no public API change, no new model, and no migration.

**Approach**

1. Add `src/openedx_learning/applets/cbe/signal_handlers.py` holding a `post_delete` receiver for `CompetencyCriterion`, and load it from a new `LearningConfig.ready()` in `src/openedx_learning/apps.py`. The module imports from `cbe/api.py`, which imports the models, so it cannot live in the models package.
2. Act only when the delete started on an `ObjectTag`. Django passes the instance or queryset that `.delete()` was called on as the `origin` argument, so the check is `isinstance(origin, ObjectTag)`, or `isinstance(origin, QuerySet)` and `issubclass(origin.model, ObjectTag)`. Return at once for every other origin: a criterion (#674's own `criterion.delete()`), a group (#675), a `Tag` or `Taxonomy`, a `CourseRun`, or `None`. Without this filter the receiver would prune inside #674's `criterion.delete()`, and #674's own walk would then read a group that is already gone.
3. Look up the criterion's former group by `instance.group_id`, and return if it no longer exists. Django deletes every criterion row in a batch before it sends the first `post_delete`, so in a multi-row delete an earlier call may already have pruned this group. No per-batch state is needed.
4. Log one info line naming the criterion, ObjectTag, and group ids, then call #674's `_cascade_from_group(group, "delete")` unchanged, imported from `.api` as a private helper, inside `transaction.atomic()`. The helper's name and signature come from PR #879 and must be confirmed once it merges. Django's deletion collector already holds a transaction, so that `atomic()` is a savepoint. The helper removes or archives each emptied group up to and including the shared root, by the same rules #674 applies.
5. Wrap the savepoint in `try`/`except Exception`, with a `broad-exception-caught` disable and a comment saying why, as `src/openedx_tagging/import_export/api.py` has. On any error, log a warning with `exc_info` naming the same ids, and return. The savepoint rolls back any partial pruning, the tagging delete still commits, and the empty group stays in place. Letting the error propagate would roll back the whole tagging delete, and because openedx-platform sends `XBLOCK_DELETED` with `send_robust` after the block is already gone, that failure would only be logged while the block's ObjectTags and criteria stayed behind.

Criteria with learner status need no branch. Until #779 and #782 land, deleting an ObjectTag under such a criterion raises `ProtectedError` before any row is deleted. After they land, that association is archived instead. Either way nothing cascades and the receiver does not run.

Studio deletes only the deleted block's own ObjectTags, so this ticket acts when the subsection itself is deleted or its tags are re-imported. A subsection deleted along with its parent section keeps its association and its live criterion, and its groups are not pruned.

The tests build a tree of a root, a course-level group, and a leaf group, and cover:

- Removing the tag through `tag_object()` (an instance origin) prunes the leaf, the course-level group, and the root. A sibling leaf that keeps a criterion stops the walk.
- `delete_object_tags()` (a queryset origin) on an ObjectTag shared by criteria in two leaves under one course-level group prunes both leaves, the course-level group, and the root.
- A queryset delete of an ObjectTag measured by two criteria in the same leaf, a state built directly in the test, finds that leaf already gone on the second call, without error.
- A leaf with its own `StudentCompetencyCriteriaGroupStatus` row is archived, not deleted.
- With the helper patched to delete the leaf and then raise, the tagging delete succeeds, the leaf still exists, and the warning is logged.
- Deletes that start on a criterion, a group, a `Tag`, or a `CourseRun` never call the helper, and neither does #674's `delete_competency_criterion()`.

Out of scope:

- Any frontend change.
- Changing #779's archive-or-delete rule.
- #826's display of unresolvable criteria.
- The cascade from deleting a `CourseRun`, which can leave an empty root.
- Removing descendants' ObjectTags when a section is deleted.
- Backfilling groups that are already empty.

**Files to create and modify**

| File | Change |
| --- | --- |
| src/openedx_learning/applets/cbe/signal_handlers.py | new: the `post_delete` receiver on `CompetencyCriterion` |
| src/openedx_learning/apps.py | modified: add `LearningConfig.ready()` |
| tests/openedx_learning/applets/cbe/test_signal_handlers.py | new |

**Additional context**

- Prior art: `src/openedx_content/applets/publishing/signal_handlers.py` is a `post_delete` receiver loaded from `ContentConfig.ready()`, and `_is_explicit_tag_delete` in `src/openedx_tagging/signal_handlers.py` filters on `origin`.
- ADR 0002 (`docs/openedx_learning/decisions/0002-competency-criteria-model.rst`), Decision 2, says persisted criteria definitions must not contain empty groups.
- For #826: because Studio deletes only the deleted block's own ObjectTags (the section-deletion boundary above), #826's unresolvable display also surfaces ungraded criteria, not only graded ones, and #674 is how the author removes them.
- For #696: on re-import, tag import runs before #696. This ticket's pruning can archive a course-level group whose remaining children are all archived, and then the shared root. #696 reactivates either one only when its file adds a live rule beneath it, so the rule the tag import deleted is recreated; a course-level group whose archived groups match everything the file records for them stays archived.
- For #675 and #817: both can hard-delete ObjectTags inside their own flows, and this receiver treats those deletes as starting on an ObjectTag. They should delete criteria before ObjectTags, and can then expect this receiver to do nothing.

</details>

## Open Questions

- (architect, final review) Should the pylint suppressions this design needs be approved? They are `broad-exception-caught` on the savepoint guard in Approach step 5, plus `import-outside-toplevel` and `unused-import` on the `ready()` import, each with a comment saying why, matching `src/openedx_tagging/apps.py` and `src/openedx_tagging/import_export/api.py`. The alternative is to catch only `DatabaseError` and `ObjectDoesNotExist` with no disable, which accepts that a programming error in the helper rolls back a Studio block's tag cleanup. Recommended: approve the suppressions.
- (architect, final review) Is the section-deletion boundary acceptable? An author who deletes the section around a tagged subsection gets no pruning, because Studio deletes only the deleted block's own ObjectTags, and is left with a live rule that can never be met until #674 removes it. The alternative is an openedx-platform ticket that removes descendants' tags on block deletion, which needs a new hook in the modulestore delete path because `XBLOCK_DELETED` fires after the subtree is gone. Recommended: accept the boundary; #826 surfaces those rules.
