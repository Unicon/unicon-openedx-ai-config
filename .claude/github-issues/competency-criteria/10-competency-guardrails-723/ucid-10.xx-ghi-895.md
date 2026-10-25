# [BE] Cascade content and tag deletes into competency criteria

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

In these scenarios, a rule is a competency criterion, and each rule measures a subsection through the tag association between that subsection and the competency. Deleting a tag association deletes its rule. When learner progress has been recorded through a tag association, #779 and #782 archive that association instead of deleting it, so its rule, the rule's groups, and all learner progress stay in place. A competency's rules sit in bottom-tier groups. The bottom-tier groups for a course sit under that course's one course-level group, and every course-level group for a competency sits under that competency's one shared root group. An empty group is a group with no rule and no group beneath it.

"Group cleanup" means the removal or archiving of emptied groups that this ticket performs after a tag association's deletion removes a rule. Group cleanup follows #674's rules: a group that learner progress has been recorded against, or that still holds an archived rule, is archived instead of removed, and a course-level group left holding only archived groups is archived too.

A course re-import deletes and recreates the tag association of every subsection that the export tags, even when nothing changed, so each of those subsections comes back tagged with its competency but without its rule, because the export carries no rules (#696 adds them). This ticket cleans up the groups those rules leave empty and does not bring the rules back.

The first scenario's examples leave out combinations whose outcome matches a row that is present: deleting a section or re-importing a course cleans up each subsection's rule exactly as deleting that subsection would, so each group state appears under one or two triggers, and learner progress recorded against the removed rule always leaves everything in place, so it appears once, for subsection U.

```
Scenario Outline: Deleting or re-importing tagged content cleans up the groups that its removed rules leave empty
  Given a rule for a competency measures subsection S, and no group of that competency is empty
    And <groups around S's rule>
    And <learner progress>
  When <trigger>
  Then <outcome>
    And all learner progress recorded for that competency is unchanged
    And the Competency Management page shows no empty group for that competency
    And the application log identifies every group that the group cleanup removed or archived, and records no group cleanup for any other group

  Examples:
    | trigger | groups around S's rule | learner progress | outcome |
    | an author deletes S in Studio | S's rule is the only rule in its bottom-tier group, and the course-level group above it requires all of its bottom-tier groups and holds one other bottom-tier group | no learner progress has been recorded for that competency | S's bottom-tier group no longer exists, and the course-level group still exists and holds only the other bottom-tier group |
    | an author deletes S in Studio | S's rule is the only rule in its bottom-tier group, that group is the only group in its course-level group, and another course has rules for the competency | no learner progress has been recorded for that competency | S's bottom-tier group and its course-level group no longer exist, and the shared root group and the other course's groups and rules are unchanged |
    | an author deletes S in Studio | S's bottom-tier group holds S's rule and one rule that was archived earlier, and nothing else, and the course-level group above it also holds another bottom-tier group whose rule is not archived | learner progress has been recorded against the archived rule and the groups above it only | S's rule no longer exists, S's bottom-tier group still exists in an archived state, and the course-level group and the shared root group are unchanged |
    | an author deletes the section that contains S in Studio | S's bottom-tier group holds S's rule and one rule that was archived earlier, and nothing else, that group is the only group in its course-level group, and another course has rules for the competency | learner progress has been recorded against the archived rule and the groups above it only | S's rule no longer exists, S's bottom-tier group and its course-level group still exist in an archived state, and the shared root group and the other course's groups are unchanged |
    | an author deletes the section that contains S in Studio | S's rule is the only rule in its bottom-tier group. The same section also contains subsection T, whose rule shares its bottom-tier group with a rule that measures a subsection in another section, and subsection U, whose rule is the only rule in its bottom-tier group. All three bottom-tier groups sit under one course-level group | learner progress has been recorded against U's rule and the groups above it only | S's rule and S's bottom-tier group no longer exist. T's rule no longer exists, and T's bottom-tier group still exists and holds only the other section's rule. U's rule, U's bottom-tier group, and the course-level group still exist |
    | the course is re-imported from an export that tags the same content with the same competencies and carries no rules | every rule that competency has in any course measures content in this course that the export tags | no learner progress has been recorded for that competency | none of the competency's rules exists any longer, and the competency has no groups left, including its shared root group |
    | the course is re-imported from an export that tags the same content with the same competencies and carries no rules | S's bottom-tier group holds one other rule, which measures subsection T | learner progress has been recorded against T's rule and the groups above it only | S's rule no longer exists, and T's rule, S's bottom-tier group, and every group above it still exist |

Scenario: Removing an emptied group lets a learner demonstrate a competency whose course-level group requires all of its groups
  Given the group rollup from #870 is in place
    And a course is the only course with rules for a competency, and its course-level group requires all of its bottom-tier groups
    And that course-level group holds two bottom-tier groups, one whose only rule measures subsection S and one whose only rule measures subsection T
    And no learner progress has been recorded for that competency
  When an author deletes S in Studio
    And a learner then demonstrates the rule that measures T
  Then the learner's status for the competency is Demonstrated

Scenario: One deletion cleans up the groups of every competency that measured the subsection
  Given subsection S is measured by one rule for competency A and one rule for competency B
    And S's rule for competency A is competency A's only rule in any course
    And S's rule for competency B shares its bottom-tier group with a rule that measures a different subsection
    And no learner progress has been recorded for either competency
  When an author deletes S in Studio
  Then competency A has no rules or groups left
    And competency B's bottom-tier group still exists and holds only its other rule
    And competency B's course-level group and shared root group are unchanged

Scenario Outline: Group cleanup does not depend on who caused the deletion
  Given a rule for a competency measures subsection S and is the only rule in its bottom-tier group, and that group is the only group in its course-level group
    And no learner progress has been recorded for that competency
  When <who causes it>
  Then S's bottom-tier group and the course-level group above it no longer exist

  Examples:
    | who causes it |
    | a course author who cannot manage that competency's rules on the Competency Management page deletes S in Studio |
    | a course import running as a background task re-imports the course from an export that tags the same content with the same competencies |

Scenario Outline: Deleting a course run removes the shared root group it leaves empty
  Given a competency has rules and groups in course run R, and no learner progress has been recorded for that competency in R
    And <other courses>
  When an administrator deletes course run R
  Then R's rules and groups for that competency no longer exist
    And <root outcome>

  Examples:
    | other courses | root outcome |
    | no other course has rules for that competency | the competency's shared root group no longer exists, and the application log records its removal |
    | another course has rules for that competency | the competency's shared root group and the other course's rules and groups are unchanged, and the application log records no group removal |

Scenario: Deleting a competency removes its rules and groups without a group cleanup
  Given a competency has rules and groups in a course, and no learner progress has been recorded for it
  When an administrator deletes the competency
  Then the deletion succeeds, and the competency has no rules or groups left
    And the application log records no group cleanup and no warning about group cleanup
```

<details>
<summary>Technical Details</summary>

This is a suggested approach, not the source of truth. The User Story, Description, and Acceptance Criteria define what must be true when the work is done.

**Summary**

In openedx-core, a `post_delete` receiver on `CompetencyCriterion` runs #674's upward pruning when deleting an ObjectTag cascades to a criterion, and a `post_delete` receiver on `CompetencyCriteriaGroup` removes a competency's shared root group when deleting a `CourseRun` leaves that root with no course-level group. In openedx-platform, deleting a block in Studio also deletes the tag associations of every block inside it, so deleting a section prunes exactly as deleting each of its subsections would, while openedx-core still knows nothing about block hierarchy. A course re-import deletes and recreates the association of every block listed in the export's tags.csv, so the existing foreign key cascade deletes the rule on each unlocked association and this ticket prunes the groups that leaves empty; the block stays tagged but loses its rule, because exports carry no rules until #696. There is no public API change, no new model, and no migration.

**Approach**

In openedx-core:

1. Add `src/openedx_learning/applets/cbe/signal_handlers.py` and load it from a new `LearningConfig.ready()` in `src/openedx_learning/apps.py`, with the same `unused-import,import-outside-toplevel` disable and comment as `src/openedx_tagging/apps.py`. The module imports from `cbe/api.py`, which imports the models, so it cannot live in the models package.
2. The criterion receiver, a `post_delete` receiver for `CompetencyCriterion`, acts only when the delete started on an `ObjectTag`. Django passes the instance or queryset that `.delete()` was called on as `origin`, so the check is `isinstance(origin, ObjectTag)`, or `isinstance(origin, QuerySet)` and `issubclass(origin.model, ObjectTag)`. It returns at once for every other origin: a criterion (#674's own `criterion.delete()`, whose own walk would otherwise read a group this receiver already removed), a group (#675, and the helper's own deletes), a `Tag` (the competency's whole group tree cascades with it, so nothing is left to prune), a `Taxonomy`, a `CourseRun` (step 4), or `None`. When #779 merges, confirm that its overridden `delete()` methods still delete unlocked rows through Django's collector with an ObjectTag instance or queryset as `origin`, because a raw delete would never reach this receiver.
3. The criterion receiver looks up the criterion's former group by `instance.group_id` and returns if that group no longer exists: Django deletes every row in a batch before it sends the first `post_delete`, so an earlier call may already have pruned it. It records the ids and `archived` flags of that group and each of its ancestors, then calls #674's `_cascade_from_group(group, "delete")` from `.api`, unchanged, which evaluates the group it is given and then each ancestor, removing or archiving each emptied group up to and including the shared root by #674's rules. Because that helper returns nothing, the receiver then re-reads the recorded groups and logs one info line for each group that is now gone or newly archived, naming the group, whether it was removed or archived, and the criterion and ObjectTag ids. When the criterion's group still has children, nothing changed and nothing is logged; logging per changed group rather than per deleted criterion matters because a course re-import deletes every unlocked rule in the course on every import. The helper's name and signature come from PR #879; confirm both once it merges.
4. The course run receiver, a `post_delete` receiver for `CompetencyCriteriaGroup`, acts only when `origin` is a `CourseRun` instance or queryset (from Django admin, or `delete_course_run()` in `src/openedx_catalog/api_impl.py`). For each deleted group it looks up `instance.parent_id` among groups with no parent. Every bottom-tier group's parent was deleted in the same batch, so the only group it finds is a course-level group's parent, the shared root. It calls `_cascade_from_group(root, "delete")`, which removes the root if no course-level group remains under it and archives it if it holds learner status, and, by the same before-and-after comparison as step 3, logs one info line naming the root, the action, and the course run only when the root is gone or newly archived. A course run whose groups or criteria hold learner status cannot be deleted at all, because learner status rows protect them, so this receiver never sees that case. The two receivers filter on different origins, and the helper's own `group.delete()` has a group as its origin, so neither receiver triggers the other.
5. Both receivers run the helper inside `transaction.atomic()`, which is a savepoint because Django's deletion collector already holds a transaction, wrapped in `try`/`except Exception` with the approved `broad-exception-caught` disable and a comment saying why, as `src/openedx_tagging/import_export/api.py` has. On error they log a warning with `exc_info` naming the group left in place and the criterion or course run ids, and return: the savepoint undoes any partial pruning, the triggering delete commits, and the empty group stays in place. Letting the error propagate would instead roll back the triggering delete. Course import's `set_exported_object_tags()` and `tag_object()` call the tagging API directly, so the import task or the author's request would fail. On Studio block deletion, both signals involved deliver through Django's `send_robust` in production (openedx-events `send_event` raises instead under `settings.DEBUG`), so the error would only be logged while the deleted blocks' associations and criteria stayed behind.

In openedx-platform:

6. In `openedx/core/djangoapps/content_tagging/handlers.py`, add a receiver for `SignalHandler.pre_item_delete`. Split modulestore sends this signal before it removes a block, while the subtree is still readable; `XBLOCK_DELETED` fires after the subtree is gone and carries only the deleted block's key. The receiver loads the block with `modulestore().get_item(usage_key.for_branch(None), depth=None)` so the subtree is fetched once, walks it with `get_children()`, and calls the existing `_delete_tags()` for each descendant. It skips the block itself, because `delete_tag_xblock` already deletes that block's tags after commit. On `ItemNotFoundError` it logs a warning and returns, as `handle_item_deleted` in `cms/djangoapps/contentstore/signals/handlers.py` does. It uses `get_children()` instead of that handler's `yield_dynamic_block_descendants`, because the dynamic walk returns no children for A/B test and library content blocks unless they are bound to a user, and blocks in Studio are not (inferred from `get_dynamic_block_children` in `common/djangoapps/util/block_utils.py`; the platform test below settles it). The receiver needs no branching for #779, because `delete_object_tags()` archives a locked association and deletes the rest. The block hierarchy stays in openedx-platform, and openedx-core sees only ObjectTag deletes.
7. The modulestore sends `pre_item_delete` through `send_robust`, so a failure in this receiver is logged and the block deletion proceeds. The receiver runs before the block is removed, which is the same tradeoff `handle_item_deleted` makes for gating and upstream links: if the modulestore delete then fails, the descendants' unlocked associations and rules are already gone. For sections and subsections the signal fires once per branch, and the second pass deletes nothing.

Tests in openedx-core, in `tests/openedx_learning/applets/cbe/test_signal_handlers.py`, on a tree of a root, a course-level group, and leaf groups:

- Removing a tag through `tag_object()` (an instance origin) prunes the leaf, the course-level group, and the root, and logs one info line naming each of the three. A sibling leaf that keeps a criterion stops the walk, and then nothing is logged.
- `delete_object_tags()` (a queryset origin, and the path both Studio deletion and course import use) on an ObjectTag measured by criteria in two leaves under one course-level group prunes both leaves, the course-level group, and the root, and logs one line per removed group.
- One ObjectTag measured by two criteria in the same leaf, a state built directly in the test, removes that leaf once: the second call finds it gone, the leaf's history records a single removal, and the leaf is logged once.
- A leaf that also holds a criterion archived earlier, and a leaf with its own `StudentCompetencyCriteriaGroupStatus` row, are each archived instead of removed, a course-level group left holding only archived groups is archived too, and each archived group is logged as archived.
- An ObjectTag measured by a criterion for competency A, alone in its leaf and course-level group, and by one for competency B, sharing its leaf: A's leaf and course-level group are removed and logged, and B's leaf keeps its other criterion and is not logged.
- A locked association (#782) passed to `delete_object_tags()` is archived, its criterion and groups are unchanged, the helper is not called, and nothing is logged.
- With the helper patched to remove the leaf and then raise, `delete_object_tags()` succeeds, the criterion is gone, the leaf and the groups above it still exist, and the warning names the leaf.
- Deleting a `CourseRun`, as an instance and as a queryset, whose course-level group is the root's only child removes the root and logs it. The root is unchanged and not logged when another course's group remains under it, and archived and logged as archived when it has its own `StudentCompetencyCriteriaGroupStatus` row. With the helper patched to raise, the course run delete succeeds and the root stays.
- Deletes that start on a criterion (including #674's `delete_competency_criterion()`), a group, a `Tag`, or a `Taxonomy` never call the helper and log nothing.

Tests in openedx-platform, in `openedx/core/djangoapps/content_tagging/tests/test_handlers.py` with `ENABLED_SIGNALS = ['pre_item_delete']`. They assert on ObjectTags only, so they do not need the CBE app installed:

- Deleting a section deletes the tags of its subsections, units, and components, including a component inside an A/B test block and one inside a library content block, and leaves tags on blocks outside the section.
- Deleting a unit deletes its components' tags.
- A locked descendant association is archived, not deleted.
- A failure in the new receiver is logged, and the block deletion still succeeds.

Out of scope:

- Any frontend change.
- Changing #779's archive-or-delete rule.
- What happens to criteria and groups when #779 archives a locked association instead of deleting it, which #817 owns.
- #826's display of unresolvable criteria.
- Taxonomy re-import. It deletes removed Tags, which either takes a competency's whole group tree with them or leaves associations in place with a null tag, so it leaves nothing to prune.
- Deleting a whole course in Studio. It goes through split's `delete_course` rather than `delete_item`, so neither `pre_item_delete` nor `XBLOCK_DELETED` fires, and the course's associations, criteria, groups, and `CourseRun` all remain.
- Backfilling groups that are already empty.

**Files to create and modify**

| Repo | File | Change |
| --- | --- | --- |
| openedx-core | src/openedx_learning/applets/cbe/signal_handlers.py | new: the criterion and course run receivers |
| openedx-core | src/openedx_learning/apps.py | modified: add `LearningConfig.ready()` |
| openedx-core | tests/openedx_learning/applets/cbe/test_signal_handlers.py | new |
| openedx-platform | openedx/core/djangoapps/content_tagging/handlers.py | modified: add the `pre_item_delete` receiver |
| openedx-platform | openedx/core/djangoapps/content_tagging/tests/test_handlers.py | modified |

**Additional context**

- Prior art: `src/openedx_content/applets/publishing/signal_handlers.py` is a `post_delete` receiver loaded from `ContentConfig.ready()`, and `_is_explicit_tag_delete` in `src/openedx_tagging/signal_handlers.py` filters on `origin`. In openedx-platform, `handle_item_deleted` in `cms/djangoapps/contentstore/signals/handlers.py` is the existing `pre_item_delete` receiver that walks descendants.
- ADR 0002 (`docs/openedx_learning/decisions/0002-competency-criteria-model.rst`), Decision 2, says persisted criteria definitions must not contain empty groups.
- For #817: #779 archives a locked association with a bulk `.update()`, which sends no Django signal, so nothing in CBE can see it happen. The smallest seam is a plain Django `Signal` defined in `openedx_tagging` (for example `object_tags_archived`, carrying the archived ObjectTag ids), sent synchronously from #779's archive branch inside the same transaction; it announces a tagging fact and tells tagging nothing about CBE. #817's receiver would sit next to this ticket's receivers, archive the live criteria on those ids, and call `_cascade_from_group(group, "archive")` once per distinct group under the same savepoint guard and the same per-changed-group logging. #817 also needs a rule for the reverse direction: a course re-import archives every locked association and then un-archives it when it re-applies the tag, so a receiver that archives criteria only on archive would leave every locked rule archived after an unchanged re-import. Section deletion can also archive the same locked descendant twice (once per branch), so that receiver must be idempotent.
- For #696: on re-import, tag import runs before #696's rule import. This ticket's pruning can archive a course-level group whose remaining children are all archived, and then the shared root; #696 reactivates either one only when its file adds a live rule beneath it.
- For #675 and #817: both can hard-delete ObjectTags inside their own flows, and the criterion receiver treats those deletes as starting on an ObjectTag. They should delete criteria before ObjectTags, and can then expect this receiver to do nothing.
- For #826: a course re-import deletes and recreates associations only for blocks listed in tags.csv, so a block missing from that file keeps its associations, and therefore its rules.

</details>
