# [BE] Finish competency criteria hierarchy cleanup on course, section, subsection, & tag deletion

GitHub: https://github.com/openedx/openedx-core/issues/895 (#895, OPEN)
Cached: 2026-10-20

## User Story
As a course author, when I delete a subsection, a section, or a whole course in Studio, or re-import a course, and that deletes or archives a tag association, I want the competency criteria and groups behind that content to be cleaned up the same way they would be if I had removed the rule on the Competency Management page, in order to never be left with an empty group on the page that I cannot explain or remove, and that can block learners from being able to demonstrate the related competency in my course.

As a platform administrator, when I delete a course run, or re-import a taxonomy in a way that deletes or archives a competency tag, or archive a whole taxonomy, I want that competency's criteria and groups to be removed or archived to match, in order to never leave rules behind that point at a tag or a course that no longer exists.

## Description
When a course author deletes a subsection, this fires a "block-deleted" event, which is heard by the Tagging code, which then deletes any relevant ObjectTag records, or archives them instead when a learner status depends on them (#779 and #782).
1. If there was no learner status related to that association, then this also deletes the relevant CompetencyCriteria, through the existing cascade. The CompetencyCriteriaGroups they leave empty are not touched today. **This ticket adds a criterion-deleted listener** in the CBE applet on the CompetencyCriterion's post_delete signal that reuses #674's upward walk to delete those groups, or archive them per #674's rules.
2. If there is a learner status related to that association, the ObjectTag is archived instead (#779), and today nothing archives the CompetencyCriterion behind it or its groups. **This ticket adds an association-archived listener** that reacts when an association is archived, archives its CompetencyCriteria, and archives each group above them that is left with no unarchived children, per #674's rules. An archived rule stays archived if #779 later revives the association.

When a course author deletes a section, Studio deletes every subsection inside it, but the Tagging code has a bug that makes it only delete the ObjectTags associated with that section and does not also remove the ObjectTags associated with its subsections. **This ticket adds a section-delete handler** in openedx-platform that runs before the section is removed, while its contents can still be read, and deletes the ObjectTag records of every block inside it. From there, the algorithm described above runs for each subsection exactly as if it had been deleted on its own.

When a course author deletes a course in Studio, Studio deletes the course without deleting its content, which also means that all of its ObjectTag records continue existing, which is the same bug as the section case above. **This ticket adds a course-delete handler** in openedx-platform that runs when a course is deleted and deletes every ObjectTag record belonging to that course. From there, the algorithm described above runs for each tagged subsection exactly as if it had been deleted on its own.

A CourseRun is a record in openedx-core's catalog app as opposed to the course and its content ("blocks"), which are records in modulestore. Deleting a course in Studio also deletes its CourseRun record, unless learner status recorded in that course refuses the delete, and a Django admin can delete a CourseRun directly. Deleting a CourseRun already deletes that course's course-level CompetencyCriteriaGroup, every group beneath it, and the CompetencyCriteria in them, by cascade. It leaves two things behind:
1. The ObjectTags stay on their subsections, which still exist in Studio when an administrator deleted only the course run, with no rule behind them. **This ticket removes those associations too**, when no other CompetencyCriterion still uses them, so a subsection does not keep showing a competency tag that nothing backs.
2. The competency's shared root group may be left with nothing beneath it, and nothing cleans it up today, because the criteria were deleted through their groups rather than through an ObjectTag, so the listener described above never ran. **This ticket adds a group-deleted listener**, on the CompetencyCriteriaGroup's delete signals, that removes that root group, or archives it per #674's rules.

When a course author re-imports a course, the tag import today removes and re-applies the tags of every tagged block, even when nothing changed. With no un-archiving in scope, that would permanently archive every rule with learner progress on every re-import, and it deletes every rule without learner progress for no reason. **This ticket changes the course tag import** in openedx-platform to apply only the differences between the export and the course, so an unchanged re-import touches no association. Only a tag the export dropped is removed or archived, and the criterion-deleted and association-archived listeners handle it as they would any other removal.

When someone re-imports a taxonomy and the import omits a competency tag that is associated with a subsection:
1. If no learner status depends on any of that tag's associations, the Tag is deleted, and because the CompetencyCriteriaGroup's foreign key to the Tag cascades, the competency's entire group tree and every CompetencyCriterion in it are deleted with it. The ObjectTags are not deleted and stay on their subsections with their tag reference cleared, which is existing Tagging behavior. Nothing is left for this ticket to clean up; **the criterion-deleted listener** must ignore deletions that start from a Tag.
2. If a learner status depends on one of its associations, today the learner status protection refuses the delete and the import fails at that tag. #780 changes that to archive the Tag instead, which leaves the competency's groups and rules live. **This ticket adds a tag-archived listener** that reacts when #780 archives a competency tag, or a whole taxonomy of competencies, and archives every CompetencyCriterion for each affected competency and every group in its tree. The listener needs #780's archive path to announce which tags or taxonomies it archived, the same kind of hook the association-archived listener needs from #779. #780 as written branches only in the taxonomy's delete-tags method and the taxonomy delete endpoint, and the taxonomy import removes tags through a different call. This ticket also routes the import's tag removal through that method, so #780's branch applies on re-import.

**In conclusion, this ticket will build:**
**In openedx-core:**
1. **The criterion-deleted listener**: when an ObjectTag delete cascades to a CompetencyCriterion, delete the groups it leaves empty, up to the shared root, or archive them per #674's rules.
2. **The association-archived listener**: when #779 archives an association, archive its CompetencyCriteria and the groups left with no unarchived children. #779's archive path gains a signal so this listener can react.
3. **The group-deleted listener**: when a CourseRun delete cascades away a course's groups, remove the shared root if nothing is left beneath it, or archive it per #674's rules, and remove the ObjectTags no remaining CompetencyCriterion uses.
4. **The tag-archived listener**: when #780 archives a competency tag or a whole taxonomy, archive each affected competency's CompetencyCriteria and whole group tree. #780's archive paths gain a signal, and the taxonomy import's tag removal is routed through the method #780 branches in.
**In openedx-platform:**
5. **The section-delete handler**: deleting a block in Studio also deletes the ObjectTags of every block inside it.
6. **The course-delete handler**: deleting a course in Studio deletes every ObjectTag in it.
7. **The course tag import change**: re-importing a course applies only the differences between the export and the course, so an unchanged re-import touches no association.

A taxonomy re-import with no learner status needs nothing of its own: the existing cascade from the Tag removes the competency's groups and rules. Nothing this ticket archives is ever restored; un-archiving is out of scope for MVP, apart from #872's reactivation of a root group.

## Context
- Blocked by #674, which implements the upward walk that removes or archives emptied groups when a criterion is removed on the Competency Management page. Every listener in this ticket reuses that walk rather than reimplementing it.
- Blocked by #779 and #782. #782 locks a tag association when a learner status is written through it, and #779 makes every tagging-layer delete path archive a locked association and hard-delete the rest, reviving an archived association in place when the same tag is re-applied. This ticket covers what happens to the criteria and groups on both branches. #779 archives with a bulk update that fires no Django signal, so this ticket adds a signal to #779's archive path for the association-archived listener to react to.
- Blocked by #780, which archives a tag or taxonomy instead of deleting it when a locked association sits beneath it. #780 also archives with a bulk update, so this ticket adds a signal to its tag and taxonomy archive paths for the tag-archived listener, and routes the taxonomy import's tag removal through the method #780 branches in, because the import deletes tags through a different call today.
- #817 runs in the opposite direction from the association-archived listener: when an author archives a rule on the Competency Management page, #817 archives or removes the association behind it. The two must not undo each other, so the association-archived listener has to be a no-op for an archive that #817 caused.
- Un-archiving is out of scope for MVP. Nothing this ticket archives is restored, and #872's reactivation of an archived root group is the only un-archive path.
- #870's group rollup is needed to verify the scenario where removing an emptied group lets a learner demonstrate a competency whose course-level group requires all of its groups.

## Acceptance Criteria

In these scenarios, a rule is a competency criterion. Each rule applies to one subsection through a tag association, which is the link between that subsection and the competency's tag. A competency's rules sit in bottom-tier groups. A course's bottom-tier groups for a competency sit under that course's one course-level group, and every course-level group for a competency sits under the competency's one shared root group. A rule is alone in its bottom-tier group when that group holds nothing else. An empty group is a group with no rule and no group beneath it.

Learner progress decides whether something is deleted or archived. When no learner progress has been recorded against a rule, removing the rule's tag association deletes the association, and the rule is deleted with it. When learner progress has been recorded against a rule, #782 has locked its tag association, so #779 archives the association in place instead of deleting it. An archived rule or group keeps all of its learner progress, is not shown as in use on the Competency Management page, and does not count toward a learner's status (#815, #816).

"Group cleanup" is what this ticket does after one of those changes. It removes the groups that a deleted rule leaves empty. It archives a rule whose tag association was archived, along with each group above that rule that is left with no unarchived rule or group beneath it. It archives every rule and group of a competency whose tag, or whose whole taxonomy, is archived. Group cleanup follows #674's rules: a group that learner progress has been recorded against, or that holds an archived rule, is archived instead of removed, and a course-level group left holding only archived groups is archived too. Nothing that this ticket archives is restored later, not even when the same tag is applied to the subsection again and #779 revives the archived association. The application log identifies each group that group cleanup removes or archives, one line for each change, and records nothing when group cleanup changes no group. If group cleanup fails, the deletion or import that triggered it still completes, the group stays as it was, and the application log records a warning naming that group. Only a test can force that failure, so the Technical Details test list covers it, together with data states that no product path can produce.

A course re-import applies only the differences between the export's tags and the course's tags. A tag that the export keeps for a subsection keeps its association and its rule, and a tag that the export drops for a subsection is removed from it like any other removal. A subsection that the export's tag file does not list at all is treated as untagged, so its competency tags are removed like any other dropped tag. An export with no tag file changes no tags.

The scenarios are grouped by what triggers the change.

### Deleting content in Studio

```
Scenario Outline: Deleting tagged content in Studio cleans up the groups behind each tagged subsection inside it
  Given a rule for a competency applies to subsection S, and no group of that competency is empty
    And <groups around S's rule>
    And <learner progress>
  When an author deletes <deleted content> in Studio
  Then <outcome>
    And all learner progress recorded for that competency is unchanged
    And the Competency Management page shows no empty group for that competency
    And the application log identifies each group that group cleanup removed or archived, one line per change, and records no group cleanup for any other group

  Examples:
    | groups around S's rule | learner progress | deleted content | outcome |
    | S's bottom-tier group also holds a rule that applies to subsection T | no learner progress has been recorded for that competency | S | S's rule no longer exists, S's bottom-tier group still exists and holds only T's rule, and every group above it is unchanged |
    | S's bottom-tier group also holds a rule that applies to subsection T, which is in a different section | learner progress has been recorded against T's rule and the groups above it, and against no other rule | the section that contains S | S's rule no longer exists, and T's rule, S's bottom-tier group, and every group above it are unchanged |
    | S's rule is alone in its bottom-tier group, and the course-level group above it requires all of its bottom-tier groups and holds one other bottom-tier group | no learner progress has been recorded for that competency | S | S's bottom-tier group no longer exists, and the course-level group still exists and holds only the other bottom-tier group |
    | S's rule is alone in its bottom-tier group, that group is the only group in its course-level group, and another course has rules for the competency | no learner progress has been recorded for that competency | S | S's bottom-tier group and its course-level group no longer exist, and the shared root group and the other course's rules and groups are unchanged |
    | S's bottom-tier group holds S's rule and one rule that was archived earlier, and nothing else, and the course-level group above it also holds another bottom-tier group whose rule is unarchived | learner progress has been recorded against the archived rule and the groups above it, and against no other rule | S | S's rule no longer exists, S's bottom-tier group is archived, and the course-level group and the shared root group are unchanged |
    | S's bottom-tier group holds S's rule and one rule that was archived earlier, and nothing else, that group is the only group in its course-level group, and another course has rules for the competency | learner progress has been recorded against the archived rule and the groups above it, and against no other rule | the section that contains S | S's rule no longer exists, S's bottom-tier group and its course-level group are archived, and the shared root group and the other course's rules and groups are unchanged |
    | S's bottom-tier group also holds a rule that applies to subsection T | learner progress has been recorded against S's rule and the groups above it, and against no other rule | S | S's rule is archived, and T's rule, S's bottom-tier group, and every group above it are unchanged |
    | S's rule is alone in its bottom-tier group, and the course-level group above it requires all of its bottom-tier groups and holds one other bottom-tier group | learner progress has been recorded against S's rule and the groups above it, and against no other rule | S | S's rule and S's bottom-tier group are archived, and the course-level group is unchanged and still holds the other bottom-tier group, unarchived |
    | S's rule is the competency's only rule in any course | learner progress has been recorded against S's rule and the groups above it | the course that contains S | S's rule and every group of that competency, including the shared root group, are archived, and none of them is removed |

Scenario: Deleting a section cleans up each subsection inside it according to that subsection's own rule
  Given a section contains subsections S, T, and U, and a rule for one competency applies to each of them
    And S's rule is alone in its bottom-tier group
    And T's rule shares its bottom-tier group with a rule that applies to subsection V, which is in a different section
    And U's rule is alone in its bottom-tier group, and learner progress has been recorded against U's rule and the groups above it, and against no other rule
    And all three bottom-tier groups sit under the same course-level group
  When an author deletes the section in Studio
  Then S's rule and S's bottom-tier group no longer exist
    And T's rule no longer exists, and T's bottom-tier group still exists and holds only V's rule
    And U's rule and U's bottom-tier group are archived
    And the course-level group and the shared root group are unchanged
    And all learner progress recorded for that competency is unchanged
    And the application log identifies S's bottom-tier group as removed and U's bottom-tier group as archived, and records no group cleanup for any other group

Scenario: Deleting a course with learner progress in Studio cleans up every tagged subsection in it
  Given a course contains subsections S, T, U, and V, and a rule for one competency applies to each of them
    And S's rule is alone in its bottom-tier group, T's and U's rules share a second bottom-tier group, and V's rule is alone in a third bottom-tier group
    And learner progress has been recorded against V's rule and the groups above it, and against no other rule
    And another course has rules for the competency
  When an author deletes the course in Studio
  Then S's, T's, and U's rules and the two bottom-tier groups that held them no longer exist
    And V's rule, V's bottom-tier group, and the course's course-level group are archived
    And the shared root group and the other course's rules and groups are unchanged
    And the course's course run record still exists, because learner progress in the course refuses its deletion
    And all learner progress recorded for that competency is unchanged
    And the application log identifies the two removed groups and the two archived groups, and records no group cleanup for any other group

Scenario Outline: Deleting a course with no learner progress in Studio removes its rules, its groups, and its course run record
  Given a course contains subsections S and T, and a rule for a competency applies to each of them from its own bottom-tier group
    And no learner progress has been recorded for that competency
    And <other courses>
  When an author deletes the course in Studio
  Then the rules that applied to S and T, their bottom-tier groups, and the course's course-level group no longer exist
    And the course's course run record no longer exists
    And <shared root group outcome>

  Examples:
    | other courses | shared root group outcome |
    | no other course has rules for that competency | the competency's shared root group no longer exists |
    | another course has rules for that competency | the competency's shared root group and the other course's rules and groups are unchanged |

Scenario: One deletion cleans up the groups of every competency with a rule on the subsection
  Given subsection S has one rule for competency A and one rule for competency B
    And S's rule for competency A is competency A's only rule in any course
    And S's rule for competency B shares its bottom-tier group with a rule that applies to a different subsection
    And no learner progress has been recorded for either competency
  When an author deletes S in Studio
  Then competency A has no rules or groups left
    And competency B's bottom-tier group still exists and holds only its other rule
    And competency B's course-level group and shared root group are unchanged
    And the application log identifies competency A's three removed groups, and records no group cleanup for competency B

Scenario: Removing an emptied group lets a learner demonstrate a competency whose course-level group requires all of its groups
  Given the group rollup from #870 is in place
    And a course is the only course with rules for a competency, and its course-level group requires all of its bottom-tier groups
    And that course-level group holds two bottom-tier groups, one whose only rule applies to subsection S and one whose only rule applies to subsection T
    And no learner progress has been recorded for that competency
  When an author deletes S in Studio
    And a learner then demonstrates the rule that applies to T
  Then the learner's status for the competency is Demonstrated
```

### Re-importing a course, or tagging content again

```
Scenario Outline: Re-importing a course from an export that drops a competency tag from a subsection cleans up the groups behind that subsection's rule
  Given a rule for a competency applies to subsection S in a course, and no group of that competency is empty
    And <groups around S's rule>
    And <learner progress>
  When the course is re-imported from an export that matches the course except that it no longer tags S with that competency
  Then <outcome>
    And all learner progress recorded for that competency is unchanged
    And the Competency Management page shows no empty group for that competency
    And the application log identifies each group that group cleanup removed or archived, one line per change, and records no group cleanup for any other group

  Examples:
    | groups around S's rule | learner progress | outcome |
    | S's bottom-tier group also holds a rule that applies to subsection T in the same course | no learner progress has been recorded for that competency | S's rule no longer exists, S's bottom-tier group still exists and holds only T's rule, and every group above it is unchanged |
    | S's rule is alone in its bottom-tier group, and the course-level group above it requires all of its bottom-tier groups and holds one other bottom-tier group | no learner progress has been recorded for that competency | S's bottom-tier group no longer exists, and the course-level group still exists and holds only the other bottom-tier group |
    | S's rule is the competency's only rule in any course | no learner progress has been recorded for that competency | the competency has no rules or groups left, including its shared root group |
    | S's bottom-tier group holds S's rule and one rule that was archived earlier, and nothing else, and the course-level group above it also holds another bottom-tier group whose rule is unarchived | learner progress has been recorded against the archived rule and the groups above it, and against no other rule | S's rule no longer exists, S's bottom-tier group is archived, and the course-level group and the shared root group are unchanged |
    | S's rule is alone in its bottom-tier group, and the course-level group above it requires all of its bottom-tier groups and holds one other bottom-tier group | learner progress has been recorded against S's rule and the groups above it, and against no other rule | S's rule and S's bottom-tier group are archived, and the course-level group is unchanged and still holds the other bottom-tier group, unarchived |

Scenario: An unchanged course re-import changes no tag, rule, or group
  Given a course's course-level group for a competency holds three bottom-tier groups
    And the first bottom-tier group holds only the rule that applies to subsection S, and learner progress has been recorded against that rule and the groups above it
    And the second bottom-tier group holds only the rule that applies to subsection T, and no learner progress has been recorded against that rule or that group
    And the third bottom-tier group holds only a rule that was archived earlier, and that group is archived too
  When the course is re-imported from an export that tags the same content with the same competencies
  Then S and T are still tagged with that competency
    And S's rule, T's rule, their bottom-tier groups, and every group above them still exist, unarchived, exactly as they were before the import
    And the rule that was archived earlier, and its bottom-tier group, are still archived
    And all learner progress recorded for that competency is unchanged
    And the application log records no group cleanup

Scenario: A subsection that the export's tag file does not list loses its tag and its rule
  Given a rule for a competency applies to subsection S in a course, and that rule is alone in its bottom-tier group
    And no learner progress has been recorded for that competency
  When the course is re-imported from an export whose tag file lists other subsections of the course but not S
  Then S is no longer tagged with that competency, and S's rule and S's bottom-tier group no longer exist
    And the application log identifies S's bottom-tier group as removed

Scenario Outline: A rule that was archived stays archived when its subsection is tagged with the same competency again
  Given learner progress has been recorded against the only rule that applies to subsection S for a competency
  When <the rule is archived>
    And <S is tagged again>
  Then the rule is still archived, and its learner progress is unchanged
    And every group of that competency is in the same state it was in right after the rule was archived
    And the application log records no group cleanup when S is tagged again

  Examples:
    | the rule is archived | S is tagged again |
    | the course is re-imported from an export that matches the course except that it no longer tags S with that competency | the course is later re-imported from an export that tags S with that competency again |
    | an author removes the rule on the Competency Management page, which archives the rule because learner progress has been recorded against it | an author later tags S with that competency again in Studio |
```

### Removing a competency's tag or a whole taxonomy

```
Scenario Outline: Removing a competency's tag from its taxonomy removes or archives all of that competency's rules and groups
  Given a competency has rules and groups in two courses, and one of its rules applies to subsection S
    And another competency in the same taxonomy has its own rules and groups
    And <learner progress>
  When <removal>
  Then <outcome>
    And all learner progress recorded for that competency is unchanged
    And the other competency's rules and groups are unchanged
    And <application log>

  Examples:
    | removal | learner progress | outcome | application log |
    | an administrator deletes the competency's tag | no learner progress has been recorded for that competency | the deletion completes, and the competency has no rules or groups left | the application log records no group cleanup and no warning about group cleanup |
    | the taxonomy is re-imported from a file that omits the competency's tag | no learner progress has been recorded for that competency | the import completes, and the competency has no rules or groups left | the application log records no group cleanup and no warning about group cleanup |
    | an administrator deletes the competency's tag | learner progress has been recorded against S's rule and the groups above it, and against no other rule | the competency's tag still exists in an archived state, and every rule and group of the competency in both courses, including rules with no learner progress of their own and the shared root group, is archived, and none of them is removed | the application log identifies each group that group cleanup archived, one line per group |
    | the taxonomy is re-imported from a file that omits the competency's tag | learner progress has been recorded against S's rule and the groups above it, and against no other rule | the import completes, the competency's tag still exists in an archived state, and every rule and group of the competency in both courses, including rules with no learner progress of their own and the shared root group, is archived, and none of them is removed | the application log identifies each group that group cleanup archived, one line per group |

Scenario Outline: Deleting a taxonomy removes or archives the rules and groups of every competency in it
  Given a taxonomy has two competencies, and each of them has rules and groups in a course
    And a competency in another taxonomy has its own rules and groups
    And <learner progress>
  When an administrator deletes the first taxonomy
  Then <outcome>
    And all learner progress recorded for every competency is unchanged
    And the other taxonomy's competency and its rules and groups are unchanged
    And <application log>

  Examples:
    | learner progress | outcome | application log |
    | no learner progress has been recorded for either competency in the first taxonomy | the deletion completes, and neither competency has any rules or groups left | the application log records no group cleanup and no warning about group cleanup |
    | learner progress has been recorded against one rule of the first competency and the groups above it, and against no other rule | every rule and group of both competencies, including rules with no learner progress of their own and both shared root groups, is archived, and none of them is removed | the application log identifies each group that group cleanup archived, one line per group |
```

### Deleting a course run

```
Scenario Outline: Deleting a course run removes the shared root group and the competency tags that it leaves without a rule
  Given a competency has rules and groups in course run R, and no learner progress has been recorded for that competency in R
    And one of R's rules applies to subsection S of R's course, and no other rule applies to S for that competency
    And <other courses>
  When an administrator deletes course run R
  Then R's rules and groups for that competency no longer exist
    And S still exists in Studio and is no longer tagged with that competency
    And <shared root group outcome>

  Examples:
    | other courses | shared root group outcome |
    | no other course has rules for that competency | the competency's shared root group no longer exists, and the application log records its removal |
    | another course has rules for that competency | the competency's shared root group and the other course's rules and groups are unchanged, and the application log records no group cleanup |

Scenario: A course run with learner progress beneath it cannot be deleted
  Given learner progress has been recorded against one of course run R's rules for a competency
  When an administrator tries to delete course run R
  Then the deletion is refused
    And R's rules and groups, the competency's shared root group, and the competency tags on R's subsections are unchanged
    And the application log records no group cleanup
```

### Who causes the change

```
Scenario Outline: Group cleanup does not depend on who caused the change
  Given a rule for a competency applies to subsection S and is alone in its bottom-tier group, and that group is the only group in its course-level group
    And another course has rules for that competency
    And no learner progress has been recorded for that competency
  When <who causes it>
  Then S's bottom-tier group and the course-level group above it no longer exist
    And the shared root group is unchanged

  Examples:
    | who causes it |
    | a course author who cannot manage that competency's rules on the Competency Management page deletes S in Studio |
    | a course import running as a background task re-imports S's course from an export that matches the course except that it no longer tags S with that competency |
```

<details>
<summary>Technical Details</summary>

This is a suggested approach, not the source of truth. The User Story, Description, and Acceptance Criteria define what must be true when the work is done.

**Summary**

In openedx-core, four listeners in a new CBE `signal_handlers.py` keep competency criteria and groups consistent with the tagging and catalog layers. The criterion-deleted and group-deleted listeners react to Django deletes that cascade into CBE. The association-archived and tag-archived listeners react to new tagging signals that #779 and #780 send when they archive an association, a tag, or a taxonomy. Nothing this ticket archives is ever un-archived. In openedx-platform, the section-delete and course-delete handlers make deleting a section or a whole course in Studio delete the ObjectTags of everything inside it. Course tag import applies only the differences in tags.csv, so an unchanged re-import leaves every rule in place.

Suggested split:

- PR A is the openedx-core deletion side (items 1 and 3), and needs only #674.
- PR B is the three openedx-platform changes. It needs nothing new from openedx-core to merge, and ships with #779 and no later than PR C.
- PR C is the openedx-core archive side (items 2 and 4, the tagging signals, and the taxonomy import change), and waits for #779 and #780.

**Approach**

PR A, openedx-core: the criterion-deleted and group-deleted listeners.

1. **Module and loading.** Add `src/openedx_learning/applets/cbe/signal_handlers.py` for all four listeners, and load it from a new `LearningConfig.ready()` in `src/openedx_learning/apps.py`. Use the same `unused-import,import-outside-toplevel` disable and comment as `src/openedx_tagging/apps.py`. The module imports from `cbe/api.py`, which imports the models, so it cannot live in the models package.
2. **Error handling and logging, shared by every listener.**
   - Every listener runs its work inside `transaction.atomic()`, which is a savepoint inside the transaction that triggered it. That block is wrapped in `try`/`except Exception` with the approved `broad-exception-caught` disable and a comment saying why, as `src/openedx_tagging/import_export/api.py` has.
   - On error, the listener logs a warning with `exc_info` that names the groups it left in place and the triggering ids, then returns. The savepoint undoes any partial work, and the triggering delete, archive, or import still completes.
   - Letting the error propagate would roll back the trigger. Course import calls the tagging API directly, so the import itself would fail.
   - #674's `_cascade_from_group()` returns nothing. A listener therefore records the ids and `archived` flags of the groups it may touch before calling it, and re-reads them afterward.
   - It logs one info line per group that is now gone or newly archived, naming the group, the action, and the triggering ids. It never logs per criterion, because one Studio deletion can remove many rules at once.
3. **The criterion-deleted listener.** This is a `post_delete` receiver for `CompetencyCriterion` that acts only when the delete started on an `ObjectTag`.
   - **The origin check.** Django passes the instance or queryset that `.delete()` was called on as `origin`. The check is `isinstance(origin, ObjectTag)`, or `isinstance(origin, QuerySet)` and `issubclass(origin.model, ObjectTag)`.
   - **Origins it ignores.** Every other origin returns at once:
     - A criterion: #674's `delete_competency_criterion()` runs its own walk.
     - A group: #675, and the helper's own deletes.
     - A `Tag` or `Taxonomy`: the competency's whole group tree cascades with the tag, so nothing is left to clean up.
     - A `CourseRun`: the group-deleted listener handles it.
   - **What it does.** It looks up the criterion's former group by `instance.group_id`. If that group is already gone, it returns, because an earlier call or the other listener may have removed it. Otherwise it calls `_cascade_from_group(group, "delete")` from `.api`, unchanged.
   - **Check when #779 merges.** Confirm that #779's overridden `delete()` methods still hard-delete unlocked rows through Django's collector with an ObjectTag origin. A raw SQL delete would never reach this receiver.
4. **The group-deleted listener.** This is a `post_delete` receiver for `CompetencyCriteriaGroup` that acts only when `origin` is a `CourseRun` instance or queryset. That happens from Django admin, and from `delete_course_run()` when a course is deleted in Studio (step 7). `CourseRun.catalog_course` is `PROTECT`, so no other delete cascades into a course run.
   - **What it does.** For each deleted course-level group (the one with `course_id` set), it calls `_cascade_from_group()` with `"delete"` on that group's parent. The parent is the shared root, which survives the delete. It then removes the ObjectTags that no remaining criterion uses.
   - **Why it needs a `pre_delete` partner.** Django deletes the criteria before the groups, so the `post_delete` instance has no criteria left to read. A `pre_delete` receiver on the same model, with the same filter, reads the `object_tag_id` of every criterion beneath the course-level group and stores the ids on the instance. Django passes that same instance to `post_delete`.
   - **How the ObjectTags are removed.** The removal reuses #817's `_reconcile_object_tags()`. That helper skips ids that any non-archived criterion still uses, and removes the rest through `openedx_tagging.api.tag_object()`. If #817 has not merged yet, this PR adds the helper with #817's semantics.
   - **Tolerating the other listener.** Both steps must cope with the course-delete handler having run first. The listener looks up the root with `filter(...).first()`, and the helper reads its candidates with `filter(id__in=...)`, never `get()`, so ids that are already gone are skipped.
   - **No locked associations here.** A course run whose groups or criteria hold learner status cannot be deleted, because the status rows protect them. So no association reached here is locked.

PR B, openedx-platform: the section-delete handler, the course-delete handler, and the course tag import change, all in `openedx/core/djangoapps/content_tagging/`.

5. **The section-delete handler.** This is a receiver for `SignalHandler.pre_item_delete`, in `handlers.py`. Split modulestore sends that signal before it removes a block, while the subtree is still readable. `XBLOCK_DELETED` fires only after the subtree is gone, and carries only the deleted block's key.
   - **What it does.** It loads the block with `modulestore().get_item(usage_key.for_branch(None), depth=None)`, walks it with `get_children()`, and calls the existing `_delete_tags()` for each descendant. It skips the block itself, whose tags `delete_tag_xblock` already deletes.
   - **Missing block.** On `ItemNotFoundError` it logs a warning and returns, as `handle_item_deleted` in `cms/djangoapps/contentstore/signals/handlers.py` does.
   - **Why `get_children()`.** That handler uses `yield_dynamic_block_descendants`, which appears to return no children for A/B test and library content blocks unless they are bound to a user. This is inferred from `get_dynamic_block_children` in `common/djangoapps/util/block_utils.py`, and a test below settles it.
   - **Firing twice.** The signal fires once per branch for sections and subsections, and the second pass finds nothing left to delete.
   - **The cost of running early.** This is the same tradeoff `handle_item_deleted` makes: if the modulestore delete then fails, the descendants' unlocked associations and rules are already gone.
6. **The course-delete handler.** This is a receiver for `SignalHandler.course_deleted`, in `handlers.py`. Split's `delete_course()` sends that signal after it removes the course index. It is the only signal course deletion sends, because course deletion never calls `delete_item`.
   - **Finding the course's tags.** The course structure is unreadable by then, so the handler finds the course's tagged objects in the tagging tables. It takes the distinct `object_id` values of `ObjectTag` rows that equal the course key, which are course-level tags, or that start with `str(course_key).replace("course-v1:", "block-v1:", 1) + "+type@"`.
   - **Why the `+type@` delimiter.** Without it, deleting `course-v1:A+B+C` would also match the blocks of `course-v1:A+B+C2`.
   - **Deleting them.** It calls `api.delete_object_tags()` once per object id, and logs one line for the course.
   - **No new openedx-core API.** Querying `ObjectTag` directly follows `get_all_object_tags()` in `api.py`, which does the same because the tagging API has no by-course lookup.
7. **The two receivers of a Studio course deletion.** The same `course_deleted` signal also reaches `_listen_for_course_delete` in `openedx/core/djangoapps/content/course_overviews/signals.py`, which deletes the course's `CourseRun` through `delete_course_run()`. The order of the two receivers is not guaranteed, and the end state is the same either way.
   - **If the CourseRun is deleted first.** Its cascade deletes the course's rules and its course-level and bottom-tier groups directly. The group-deleted listener then removes or archives the root, and removes the rules' ObjectTags. The course-delete handler then deletes the remaining tags, which have no rule behind them.
   - **If the course-delete handler runs first.** The criterion-deleted listener removes each emptied group up to the root, and the CourseRun delete then finds no groups.
   - **What the log records.** The log records only cleanup, never groups that a CourseRun delete cascades away directly. So the first order logs only the root, and the second order logs every removed group.
   - **When the course has learner status.** `delete_course_run()` raises `ProtectedError`, which `send_robust` logs. The course deletion completes and the `CourseRun` row stays. What remains under it is the rules that hold learner status and the groups above them, archived by the association-archived listener.
   - **Failures.** All of these signals use `send_robust`, so a failure in either handler is logged and the deletion proceeds.
   - **Shipping with #779.** Until #779 ships, deleting the ObjectTag of a rule that holds learner status raises `ProtectedError`, which stops either handler at that block.
8. **The course tag import change.** `set_exported_object_tags()` in `api.py`, which course import calls once per tags.csv row, applies only the differences instead of deleting every tag on the block and re-applying them.
   - **What changes.** Drop its opening `oel_tagging.delete_object_tags(content_key_str)`. The loop after it already calls `oel_tagging.tag_object()` once per taxonomy in the row. `tag_object()` keeps the associations whose values are listed, adds new ones, and removes only the omitted ones through #779's archive-or-delete branch.
   - **Taxonomies the row no longer carries.** For each taxonomy the block still has tags in that the row does not list, call `oel_tagging.tag_object(object_id, taxonomy, [], taxonomy_export_id=...)`. Find those taxonomies with `oel_tagging.get_object_tags()`, matched by export id. This keeps today's rule that an import replaces a block's tags. The tagging API has no taxonomy-scoped `delete_object_tags()`, and `tag_object()` with an empty list does that job.
   - **Result.** An unchanged re-import deletes and archives nothing, so no rule or group changes. A re-import still removes the associations the export no longer carries, and the criterion-deleted and association-archived listeners follow those removals. Blocks that tags.csv does not list are treated as untagged: after the rows are processed, the import finds the course's remaining tagged objects with the same prefix query the course-delete handler uses, and calls `oel_tagging.delete_object_tags()` for each one the file did not list. An export with no tags.csv keeps today's behavior and changes nothing.
   - **Why.** Without this change, every re-import would delete every rule without learner status and permanently archive every rule with it. #779 revives the association when the tag is re-applied, but nothing un-archives a rule.

PR C, openedx-core: the association-archived and tag-archived listeners, after #779 and #780. The tagging hooks below land in `openedx_tagging` code, but they are this ticket's work.

9. **The tagging signals.** Add `src/openedx_tagging/signals.py` with three Django signals:
   - `object_tags_archived` carries `object_tag_ids`. Send it from the one function that #779 routes both `delete()` overrides through.
   - `tags_archived` carries `tag_ids`. Send it from #780's archive branch in `Taxonomy.delete_tags()`.
   - `taxonomies_archived` carries `taxonomy_ids`. Send it from #780's taxonomy archive branch behind `TaxonomyView.perform_destroy()`. It is a separate signal because archiving a taxonomy does not set `archived` on its tags (#780). A `tags_archived` payload for it would state something untrue, and #781 needs to tell the two cases apart.

   Rules for all three signals:
   - Each is sent with `send()` right after its bulk `.update()`, inside the same transaction, so a rollback also undoes the CBE changes.
   - Each carries only the ids whose `archived` value actually changed, and is not sent when none did.
   - The signals state a tagging fact and know nothing about competencies.
   - They are new public surface of `openedx_tagging`, so their docstrings define the payload.
10. **The taxonomy import change.** In `src/openedx_tagging/import_export/actions.py`, `DeleteTag.execute()` looks the tag up with `_get_tag()`, returning as today when it no longer exists. It then calls `self.taxonomy.delete_tags([tag.value], with_subtags=True)`, so #780's archive-or-delete branch also applies on re-import.
    - **Why `with_subtags=True`.** It matches today's cascade. An earlier `UpdateParentTag` action in the same plan has already moved every child that the file keeps, so only children that the file also omits are removed with the tag.
    - **Tags already archived.** A tag that #780 already archived earlier in the same import must be skipped, not deleted again. #778 is expected to hide it from `_get_tag()`; confirm that.
    - **Search events.** The existing `pre_delete` receiver in `src/openedx_tagging/signal_handlers.py` already handles a queryset origin, so search events are unchanged.
11. **The association-archived listener.** It receives `object_tags_archived`.
    - **Archiving the rules.** It archives the non-archived criteria on those ObjectTags with simple-history's `bulk_update_with_history()` and a change reason, never `QuerySet.update()`, so history records the archive (ADR 0003, Decision 1).
    - **Archiving the groups.** It then calls `_cascade_from_group(group, "archive")` once per distinct group. That walk stops at the first group that still has a live child.
    - **When there is nothing to do.** It finds nothing to do when the criteria are already archived. That covers an archive #817 caused, because #817 archives the criterion before it calls `tag_object()`. It also covers a section delete that archives the same association once per branch.
    - **When the association is revived.** When #779 later revives the association because an author re-applied the tag, nothing reacts. The rule and its groups stay archived, and the author creates a new rule, as #817 already expects.
12. **The tag-archived listener.** It receives `tags_archived` and `taxonomies_archived`. It archives every non-archived criterion and group whose competency tag is one of those tags, or belongs to one of those taxonomies, writes them as in step 11, and logs each group. It filters on `tag_id` and `tag__taxonomy_id`, which #778's hiding of archived tags and taxonomies from reads does not affect.

Tests in openedx-core for PR A, in `tests/openedx_learning/applets/cbe/test_signal_handlers.py`, on a tree of a root, a course-level group, and leaf groups:

- **Instance origin.** Removing a tag through `tag_object()` removes the leaf, the course-level group, and the root, and logs one line for each of the three. A sibling leaf that keeps a criterion stops the walk, and then nothing is logged.
- **Queryset origin.** `delete_object_tags()` is used by Studio deletion. On an ObjectTag that has criteria in two leaves under one course-level group, it removes both leaves, the course-level group, and the root, and logs one line per removed group.
- **Two criteria, one leaf.** One ObjectTag that has two criteria in the same leaf removes and logs that leaf once.
- **Archive instead of remove.** A leaf that also holds a criterion archived earlier is archived instead of removed. So is a leaf with its own `StudentCompetencyCriteriaGroupStatus` row. A course-level group left holding only archived groups is archived too.
- **Two competencies, one ObjectTag.** The ObjectTag has a criterion for competency A, alone in its leaf and course-level group, and one for competency B that shares its leaf. Deleting it removes and logs A's leaf and course-level group. B's leaf keeps its other criterion and is not logged.
- **Course run delete.** Delete a `CourseRun`, as an instance and as a queryset, whose course-level group is the root's only child. The root is removed and logged.
  - The root is unchanged and not logged when another course's group remains under it.
  - The root is archived and logged when it has its own status row.
  - ObjectTags used only by the deleted run's criteria are removed. One that a criterion in another course run also uses is kept.
- **Both orders of a Studio course deletion end with the same rows.**
  - Deleting the course's ObjectTags and then its `CourseRun` logs each removed group, and the `CourseRun` delete finds nothing to do.
  - Deleting the `CourseRun` and then the remaining ObjectTags logs only the root.
  - Neither order raises or logs a warning.
- **Helper failure.** With the helper patched to raise, `delete_object_tags()` and the course run delete both succeed, the groups stay, and the warning names them.
- **Ignored origins.** Deletes that start on a criterion (including `delete_competency_criterion()`), a group, a `Tag`, or a `Taxonomy` never call the helper, and log nothing.

Tests in openedx-platform for PR B. They assert on ObjectTags only.

- **In `tests/test_handlers.py`, with `ENABLED_SIGNALS = ['pre_item_delete', 'course_deleted']`:**
  - Deleting a section deletes the tags of its subsections, units, and components, including a component inside an A/B test block and one inside a library content block. Tags on blocks outside the section stay.
  - Deleting a unit deletes its components' tags.
  - Deleting course `course-v1:A+B+C` deletes the tags on every block in it and on the course key itself. Tags on the blocks of `course-v1:A+B+C2` stay.
  - A failure in either handler is logged, and the deletion still succeeds.
- **In `tests/test_api.py`:**
  - Importing a course's own tags.csv back into it leaves every ObjectTag row in place, with the same ids.
  - A tag the row no longer carries is removed from that block.
  - A taxonomy the row no longer carries is removed from that block.
  - A block absent from the file loses its tags, and an export with no tags.csv changes nothing.
- **Once #779 is released:** a locked association inside a deleted section or course, or dropped by an import, is archived, not deleted.

Tests in openedx-core for PR C, in the same CBE module and in `tests/openedx_tagging/`:

- **Signals.** Each tagging signal is sent once per operation, after its update, with only the ids whose state changed. It is not sent when nothing changed.
- **Archiving a locked association.** Removing it with `tag_object()` archives its criterion and each group left with no live children, and logs each archived group.
- **Revival.** Re-applying the tag revives the association, and leaves the criterion and groups archived.
- **#817 no-op.** Take a criterion archived through `delete_competency_criterion()` whose association is then archived. Nothing more changes and nothing is logged.
- **Idempotence.** Sending `object_tags_archived` twice for the same ids changes and logs nothing the second time.
- **Taxonomy import.**
  - An import with replace that omits a competency tag with a locked association completes, archives the tag, and archives that competency's tree.
  - Omitting an unlocked tag still deletes it and its tree, and no listener logs.
  - Omitting a parent and its child in the same file succeeds.
- **Taxonomy archive.** Archiving a taxonomy through the taxonomy delete endpoint archives every competency tree in it, and leaves criteria and groups that were already archived unchanged.
- **Listener failure.** With a listener patched to raise, the triggering archive commits, the criteria are unchanged, and the warning is logged.

Out of scope:

- Any frontend change.
- Changing #779's or #780's archive-or-delete rules. This ticket only adds signals to them.
- Un-archiving anything this ticket archives, when #779 revives an association or when a tag or taxonomy is un-archived. #872's reactivation of an archived root is unaffected.
- #826's display of unresolvable criteria.
- Backfilling groups that are already empty.
- ObjectTags left with a null tag after a Tag is hard-deleted, which is existing tagging behavior.

**Files to create and modify**

| Repo | File | Change |
| --- | --- | --- |
| openedx-core | src/openedx_learning/apps.py | modified (PR A): add `LearningConfig.ready()` |
| openedx-core | src/openedx_learning/applets/cbe/signal_handlers.py | new (PR A, extended in PR C): the four listeners |
| openedx-core | src/openedx_learning/applets/cbe/api.py | modified (PR A): `_reconcile_object_tags()`, only if #817 has not added it |
| openedx-core | tests/openedx_learning/applets/cbe/test_signal_handlers.py | new (PR A, extended in PR C) |
| openedx-core | src/openedx_tagging/signals.py | new (PR C): the three tagging signals |
| openedx-core | src/openedx_tagging/models/base.py | modified (PR C): send from #779's archive function and #780's `delete_tags()` |
| openedx-core | src/openedx_tagging/rest_api/v1/views.py | modified (PR C): send from #780's taxonomy archive branch |
| openedx-core | src/openedx_tagging/import_export/actions.py | modified (PR C): `DeleteTag.execute()` |
| openedx-core | tests/openedx_tagging/ | modified (PR C): signal, import, and taxonomy archive tests |
| openedx-platform | openedx/core/djangoapps/content_tagging/handlers.py | modified (PR B): the two handlers |
| openedx-platform | openedx/core/djangoapps/content_tagging/api.py | modified (PR B): `set_exported_object_tags()` |
| openedx-platform | openedx/core/djangoapps/content_tagging/tests/test_handlers.py | modified (PR B) |
| openedx-platform | openedx/core/djangoapps/content_tagging/tests/test_api.py | modified (PR B) |

**Additional context**

- **Prior art.**
  - `src/openedx_content/applets/publishing/signal_handlers.py` is a `post_delete` receiver loaded from `ContentConfig.ready()`.
  - `_is_explicit_tag_delete` in `src/openedx_tagging/signal_handlers.py` filters on `origin`.
  - In openedx-platform, `handle_item_deleted` in `cms/djangoapps/contentstore/signals/handlers.py` walks descendants on `pre_item_delete`.
  - `set_all_object_tags()` in `content_tagging/api.py` already applies tags through `tag_object()` without deleting first.
- **Where the listeners run.** The CMS installs `openedx_learning`, so the CBE listeners run inside Studio's deletes and imports.
- **ADR.** ADR 0002 (`docs/openedx_learning/decisions/0002-competency-criteria-model.rst`), Decision 2, says persisted criteria definitions must not contain empty groups.
- **For #696.** #696's rule import runs after the tag import. With the course tag import change, an unchanged re-import leaves every association, rule, and group in place, so #696 finds each group and skips each rule it already has. A rule this ticket archived stays archived. When its association is live again, #696 creates a new rule beside it.
- **For #675 and #817.** Both can hard-delete ObjectTags inside their own flows, and the criterion-deleted listener treats those deletes as starting on an ObjectTag. They should delete criteria before ObjectTags, and can then expect the listener to do nothing.
- **For #781.** It can connect to `tags_archived` and `taxonomies_archived` for its search-index update instead of adding its own hooks.

</details>
