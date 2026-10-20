# [BE] Prune criteria groups emptied when tagging code deletes a criterion's association

GitHub: pending
Cached: 2026-10-20

## User Story
As a course author, when I delete a subsection, or a competency tag is otherwise removed from content outside the Competency Management page before any learner has been graded on it, I want the competency rule that pointed at that content to be removed the same way it would be if I had removed it on the Competency Management page, in order to never leave behind an empty criteria group that makes the competency impossible to earn in my course without telling anyone why.

## Description
A competency criterion points at an ObjectTag to connect it to a subsection. The ObjectTag cascades on delete, but it will only cascade delete the criterion, not the parent CompetencyCriteriaGroup. This can happen when Studio deletes a block or a course re-import re-sets a block's tags. When these deletes happen, the group that held the criterion is never checked, so it can be left as an orphan with no criteria at all. This would result in an empty group showing on the Competency Management page, and the learner status rollup would skip it, potentially causing the competency to no longer be earnable in that course. In this ticket, we need to make a criterion deletion from any path run the same upward pruning that #674 runs when a criterion is removed on the Competency Management page.

At a high level:

```
the CBE applet registers a listener for Django's built-in post_delete signal on its own criterion model
  (Django fires this signal for every criterion row it deletes, including rows removed by a cascade from a tag association, so tagging code stays unaware of CBE and nothing new is emitted)
when the listener fires:
  walk upward from the deleted criterion's group using #674's existing pruning: a group left with no live criteria and no live child groups is deleted, or archived if a learner has a recorded status for it, and the walk continues to its parent
```

## Context
- #674 implements the upward pruning for a criterion removed on the Competency Management page.
- #779 makes every tagging-layer delete path archive an association that learner mastery depends on and hard-delete the rest. This ticket covers what the hard-delete branch does to the criteria on that association.

## Notes for drafting

- Verified facts (2026-10-20): `CompetencyCriterion.object_tag` is `on_delete=CASCADE` (`cbe/models/criteria.py` ~286-292). `StudentCompetencyCriterionStatus.criterion` is `on_delete=PROTECT`, so a cascade onto a criterion with learner status raises `ProtectedError`; after #779 that case no longer arises from tagging code, because the association is archived instead. No `post_delete`, `pre_delete`, or `@receiver` exists anywhere under `cbe/` today.
- Tagging-layer paths that hard-delete associations, all in or called from `src/openedx_tagging/api.py`: `delete_object_tags()` (a bulk queryset `.delete()`, `api.py` ~285-291, no taxonomy filter), called by openedx-platform's `content_tagging/handlers.py` `delete_tag_xblock` on `XBLOCK_DELETED` and by `content_tagging/api.py` `set_exported_object_tags()` on course import; `tag_object()`'s reconcile step; `copy_tags()`. #784 hides competency-tag removal on the Course Outline, so block deletion and re-import are the realistic triggers.
- #674's helper in PR #879: `_cascade_from_group(group, event)` in `cbe/api.py`, recursive on `group.parent`, returns early if the group has any live criterion or child group, hard-deletes on a "delete" event unless a `StudentCompetencyCriteriaGroupStatus` row exists (then archives), archives when only archived children remain. `delete_competency_criterion` calls it after `criterion.delete()`. Reuse it; do not duplicate it.
- Re-entrancy to design for: #674's own hard-delete path removes the now-unused `ObjectTag` by calling `tag_object()` without that tag value, so any hook on criterion deletion also fires during #674's own flow (the criterion is already gone by then, so the hook sees no criterion, but confirm it is harmless and does not double-process).
- Mechanism candidates for the architect pass: (A) a `post_delete` receiver on `CompetencyCriterion` in the cbe applet; Django's deletion collector sends `post_delete` for every cascaded row when a receiver is connected, and skips its fast-delete shortcut for that model, so a queryset `.delete()` on `ObjectTag` reaches it. (B) a custom `on_delete` callable on the foreign key that prunes before cascading. (C) overriding `CompetencyCriterion.delete()`, which queryset cascades bypass, so it does not cover this case. Expected recommendation: A.
- Verified 2026-10-20, evaluation side: the merged leaf-status PR #862 records only a criterion's own status and never evaluates groups. The group rollup is PR #870 (open, not merged, so this is its current draft): it reads existing status rows and does not compute AND/OR over a group's children, so an empty group has no rows and is skipped, neither satisfied nor failed; a competency with nothing beneath it logs a warning that it "has no criteria beneath it and can never be demonstrated". No crash, no wrong status, just a competency that cannot be earned in that course.
- Verified 2026-10-20, display side (#672's two PRs, openedx/frontend-app-authoring#3275 and the fork PR AShatsila/frontend-app-authoring#1): a group with zero criteria renders its "By completing any/all" header with an empty body; the criterion list component returns null on an empty list with a comment that empty groups are "not expected for a persisted box per ADR 0002"; no remove control exists in that view. #672 is effectively done and cannot take a follow-up.
- Why this is not the same as the author removing a criterion: #674's path prunes the group when its last criterion goes. The cascade path does not, so only the cascade path can produce an empty group. A group thinned but not emptied by the cascade matches what #674 would do and is not a defect.
- Research for the draft pass: how the merged group evaluation (PR #862 upstream, not on the local `cbe-642b-criteria-status` checkout) treats a group with zero live criteria and zero child groups, to state the user-visible harm precisely in the AC.
- Out of scope: any frontend change; changing #779's archive-or-delete rule; #826's unresolvable-criterion display; pruning groups emptied by paths that already prune (#674, #675).
