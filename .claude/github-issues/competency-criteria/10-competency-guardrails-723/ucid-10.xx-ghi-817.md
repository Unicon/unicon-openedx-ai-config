# [BE] Stop an assignment showing as tagged when the last competency rule measuring it is archived

GitHub: https://github.com/openedx/openedx-core/issues/817 (#817, OPEN)
Cached: 2026-09-21

## User Story

As a course author, I want an assignment to stop showing as tagged with a competency once the last mastery rule measuring it against that competency is archived, in order to see competency tags only on content something is actually measuring.

## Acceptance Criteria

Scenarios tagged `@unit-test-only` describe a data state that no authoring endpoint can produce, or an outcome that no endpoint exposes for reading. They're included for coverage, but can only be exercised by constructing the state, or reading the result, directly in a test rather than through the product UI or REST API. Every other scenario here is verifiable via Postman, apart from the steps that record a grade, which is driven from `openedx-platform` rather than from this repo's own endpoints.

```
Scenario: Archiving the last rule measuring an assignment stops it showing as tagged
  Given an assignment tagged with a competency and measured by exactly one mastery rule
    And learner mastery has been recorded against that rule, so it is archived rather than deleted
  When that rule is archived
  Then the assignment no longer appears tagged with that competency

@unit-test-only
Scenario: An assignment another active rule still measures stays tagged
  Given an assignment tagged with a competency and measured by two mastery rules, a state no
    authoring endpoint can produce
  When one of those two rules is archived
  Then the assignment still appears tagged with that competency
    And the remaining rule still records mastery when a grade for that assignment is recorded

Scenario: Archiving a group of rules stops every assignment under it showing as tagged
  Given a nested group of mastery rules beneath a competency's course-level group
    And that nested group holds two rules, each measuring a different tagged assignment
    And no rule outside that nested group measures either assignment
  When that nested group is archived
  Then neither assignment appears tagged with that competency any more

@unit-test-only
Scenario: Archiving a group leaves an assignment tagged if an active rule outside it still measures it
  Given a nested group of mastery rules beneath a competency's course-level group
    And a rule inside that nested group and a rule in another group that stays active both measure
    the same tagged assignment, a state no authoring endpoint can produce
  When that nested group is archived
  Then the assignment still appears tagged with that competency

@unit-test-only
Scenario: Learner mastery still traces back to the assignment that earned it
  Given a learner's mastery recorded through a mastery rule whose assignment stopped showing as
    tagged when that rule was archived
  When that learner's mastery record is read back
  Then it still identifies the assignment and the competency it was earned against

Scenario: The same assignment can be tagged with the same competency again after archiving
  Given an assignment that stopped showing as tagged with a competency when its own mastery rule
    was archived
    And that competency still has another active mastery rule in the same course, so the groups
    above the archived rule are still active
  When an author tags that assignment with that competency again and creates a new mastery rule for it
  Then the tagging succeeds without the author being asked to restore or reactivate anything
    And the assignment appears tagged with that competency once, not twice

Scenario: Tagging an assignment again leaves the earlier archived rule archived
  Given an assignment that was tagged with a competency again under a new mastery rule after its
    only previous rule was archived
  When a grade for that assignment is recorded for a learner
  Then mastery is recorded for that learner against the new rule only
    And the archived rule is still archived, with the mastery recorded against it before archiving
    unchanged

Scenario: Deleting a rule no learner has been measured against still removes the tag outright
  Given an assignment tagged with a competency and measured by exactly one mastery rule
    And no learner mastery has been recorded against that rule
  When that rule is deleted
  Then the assignment no longer appears tagged with that competency
    And neither the rule nor its tag association is left behind in an archived state
```

## Description

A mastery rule a learner has already been measured against is archived rather than deleted, and today archiving it leaves the assignment still showing as tagged with a competency nothing is measuring any more. This ticket makes the archive path tell the tagging layer, the same way the delete path already does, once no active rule anywhere still uses the association; the tagging layer retires it rather than deleting it, so mastery a learner already earned still traces back to the assignment and competency that produced it. Tagging the same assignment with the same competency again brings that association back instead of adding a second one, so an author just tags the content and creates a new rule as usual.

<details>
<summary>Technical Details</summary>

This section is background and a suggested approach, not the source of truth. The User Story and Acceptance Criteria define what must be true when the work is done.

### In short

**What changes, and who decides archive vs. delete.** `delete_competency_criterion()` (\#674) and `delete_competency_criteria_group()` (\#675) each branch on whether learner mastery exists: the hard-delete branch already reconciles the tag association through `tag_object()`, removing it when no other criterion still needs it, but the archive branch does nothing to the association at all, which is why an assignment keeps showing as tagged after the last rule measuring it is archived. This ticket makes the archive branch run that same reconciliation call. Which outcome it produces, archive or delete, is not decided here: \#782 locks an association against deletion when a learner's mastery is recorded through it, and \#779 makes `tag_object()` retire a locked association instead of deleting it. So calling the same reconciliation from both branches gets the right result for free, and this ticket adds no archive-versus-delete logic of its own.

**This ticket adds one check: is the tag still needed at all?** Once this operation has finished archiving and hard-deleting whichever criteria it's removing, does any other active criterion still point at this association? If so, leave the association alone. If not, make the same `tag_object()` call described above to drop the tag. Checking after all the writes, rather than one criterion at a time, is what keeps a mixed subtree correct with no extra code.

**Nothing is needed for the re-tagging direction.** When an author tags the same assignment again, \#779 already makes `tag_object()` revive the existing retired association in place, automatically. The duplicate-association check in `associate_competency_criterion()` needs no change either: \#717 already scopes it to non-archived criteria, which is what lets the new criterion succeed even though the revived association is the same row the old archived criterion still points at. The work here is a regression test, not code.

### Implementation specifics

- **Where the change lands.** `src/openedx_learning/applets/cbe/api.py`, in `delete_competency_criterion()` (\#674) and `delete_competency_criteria_group()` (\#675), inside the `transaction.atomic()` block each function already opens.  
- **One shared helper, called by both branches.** Add a private helper in the same module, for example `_reconcile_object_tags(candidate_objecttag_ids: set[int]) -> None`, and move \#674's existing hard-delete-branch reconciliation onto it so both branches run identical code. Two parallel copies of this rule drift, and the mixed delete-plus-archive case inside a single \#675 subtree operation is only reliably correct when one pass evaluates the whole operation after all criteria writes have landed.  
- **Collect candidates before the criteria writes.** Build the candidate set from the `oel_tagging_objecttag_id` values of the `CompetencyCriterion` rows the operation is about to archive or delete, read before those rows are modified. A hard-deleted criterion no longer carries that reference afterwards.  
- **The still-in-use query.** `CompetencyCriterion.objects.filter(oel_tagging_objecttag_id__in=candidate_objecttag_ids, archived=False).values_list("oel_tagging_objecttag_id", flat=True)`. Every id it returns is dropped from the candidate set and left entirely untouched. The query is global: it is not filtered by group, subtree, course, or the operation's own scope.  
- **No ancestor-group walk is needed.** Filter on `CompetencyCriterion.archived` (\#716) only. \#675 archives every descendant criterion, not just the group row, in the same transaction, so a criterion under an archived group is itself archived and the criterion-level filter is sufficient. `CompetencyCriteriaGroup` carries no association reference of its own, so groups contribute no candidates.  
- **Grouping and call shape.** Group the surviving candidates by `(object_id, taxonomy_id)`. For each group: `values = [t.value for t in get_object_tags(object_id, taxonomy_id=taxonomy_id)]`, drop that group's affected values, then `openedx_tagging.api.tag_object(object_id, taxonomy, values)`. Read `object_id`, the `Taxonomy` object, and the tag value off each `ObjectTag` before calling `tag_object()`, because the call may delete the row.  
- **Scope every call to the association's own taxonomy.** Pass `taxonomy_id` to `get_object_tags()` and the matching `Taxonomy` to `tag_object()`, so no other taxonomy's tags on the same assignment are re-validated or replaced.  
- **Already-retired associations missing from the reduced list are harmless.** \#778 excludes retired associations from `get_object_tags()`, so an assignment that already has a retired association in the same taxonomy will have that value absent from the list handed to `tag_object()`. Under \#779 a locked association absent from the list is retired again, which is a no-op on a row already in that state, and reviving only happens for values that are present in the list, so an omission cannot bring anything back.  
- **No new code on the create path.** `associate_competency_criterion()` (\#665) gets no changes. It must keep creating associations through `openedx_tagging.api.tag_object()` rather than creating an `ObjectTag` directly, because only `tag_object()` revives an existing retired association in place; a direct create would leave a second association alongside the retired one and the assignment would show the tag twice.  
- **The duplicate check stays exactly as \#717 wrote it,** scoped to non-archived criteria. Cover it with a regression test rather than changing it.  
- **Out of scope, assumed already merged.** The `archived` and `deletion_locked` fields on the tagging models (\#776); the lock written when mastery is recorded (\#782); `tag_object()`'s retire-instead-of-delete and revive-on-re-apply behavior (\#779); the exclusion of retired associations from ordinary tagging reads and the read exemption that keeps learner mastery traceable (\#778); the `archived` fields on the competency criteria models (\#716). Do not reimplement any of these here.  
- **Layering.** `openedx_learning` sits above `openedx_tagging` in the `src_layering` contract in `.importlinter`, so calling `openedx_tagging.api` from the CBE applet is the sanctioned direction. Nothing in this ticket may add knowledge of competencies to `openedx_tagging`.  
- **Public API impact: none.** `delete_competency_criterion()` and `delete_competency_criteria_group()` keep their signatures, and the new helper is private. The only behavior change is on the archive branch.  
- **Tests,** in `tests/openedx_learning/applets/cbe/test_api.py`: archiving the last criterion when learner mastery exists retires the association rather than deleting it, and `get_object_tags()` stops returning it; archiving one of two criteria that share an association leaves the association untouched and the remaining criterion still evaluates; a group archive spanning two assignments produces exactly one `tag_object()` call per assignment; a group archive where an active criterion outside the subtree still references one of the assignments leaves that association untouched; a mixed subtree where one criterion is hard-deleted and another is archived, both pointing at the same association, reconciles that association exactly once and retires rather than deletes it; deleting a criterion no learner was measured against still removes the association outright, as a regression guard on \#674's existing behavior now routed through the shared helper; re-tagging after an archive revives the same association row rather than creating a second one, creates the new criterion successfully, and leaves the old criterion archived; a learner mastery row for an archived criterion still resolves back to its association.  
- **ADR alignment, no new ADR needed.** This implements the post-use archive rule and the traceability exemption already decided in `docs/openedx_learning/decisions/0003-competency-criteria-versioning.rst`, Decision 3\.

Files to create and modify **Modified files**

| File | Nature of modification |
| :---- | :---- |
| src/openedx\_learning/applets/cbe/api.py | Add a private reconciliation helper; call it from the archive branch of `delete_competency_criterion()` and `delete_competency_criteria_group()`, and move the hard-delete branch's existing reconciliation onto it |
| tests/openedx\_learning/applets/cbe/test\_api.py | Add the archive, shared-association, subtree, mixed delete-and-archive, re-tag, and traceability cases |

- Context \#674 adds `delete_competency_criterion()`, whose hard-delete branch already reconciles the association through `tag_object()` and whose archive branch is the gap this ticket closes.  
- \#675 adds `delete_competency_criteria_group()`, which archives or deletes a whole subtree of criteria across potentially many assignments in one transaction.  
- \#665 adds `associate_competency_criterion()`, the create path this ticket verifies but does not change.  
- \#776 adds the `archived` and `deletion_locked` fields to the tagging models, inert on merge.  
- \#782 sets the deletion lock on an association whenever learner mastery is recorded against the criterion evaluated through it.  
- \#779 makes `tag_object()` retire a locked association instead of deleting it, and revive a retired association in place when the same tag is applied again.  
- \#778 excludes retired associations from ordinary tagging reads and keeps the learner-mastery traceability read exempt.  
- \#716 adds `archived` to the competency criteria models; it is a separate field from the tagging models' own `archived` and the two should not be conflated.  
- \#717 scopes the duplicate-association check to non-archived criteria.  
- `src/openedx_tagging/api.py` holds `tag_object()` and `get_object_tags()`, the two functions this ticket calls.  
- `docs/openedx_learning/decisions/0003-competency-criteria-versioning.rst`, Decision 3, is the decision record for the post-use archive rule and the traceability exemption.  
- `.importlinter` defines the layering that puts `openedx_learning` above `openedx_tagging`.

</details>
