# [UXD Spike] Confirmation dialogs for competency criteria edits and deletes

GitHub: https://github.com/openedx/openedx-core/issues/775 (#775, OPEN)
Cached: 2026-09-21

This is a design spike. The deliverable is design artifacts and documented decisions, not working code.

## User Story

As a course author or platform administrator, I want to be warned before I change or remove competency configuration, in order to understand what my change will and will not do to learners who have already been evaluated.

## Delivery checklist

- [ ] Design the confirmation dialog shown on every **edit** of a `CompetencyCriteria` or `CompetencyCriteriaGroup`. Starting text to refine: "Change this rule? Changing this will only affect future evaluations of this competency. Learners who have already been evaluated against the current rule will keep their existing status." Buttons: Cancel / Save Changes.  
- [ ] Design the confirmation dialog shown on every **delete** of a `CompetencyCriteria` or `CompetencyCriteriaGroup`. Starting text to refine: "Delete this \[criterion/group\]? This action cannot be undone from this screen. Existing learner mastery statuses will not be affected." Buttons: Cancel / Delete.  
- [ ] Design the confirmation dialog shown when deleting an `ObjectTag` association from the Competency Management page. Starting text to refine: "Delete this tag association? This action cannot be undone from this screen. Existing learner mastery statuses will not be affected." Buttons: Cancel / Delete.  
- [ ] Confirm all three read correctly for an author who does not know, and is not meant to know, whether the record will be archived or hard-deleted underneath.  
- [ ] Specify responsive and small-screen behavior for each dialog.  
- [ ] Specify accessible behavior for each: focus on open and on close, what a screen reader announces, keyboard dismissal, and which button takes initial focus.  
- [ ] Update the Competency Criteria Figma file with all three dialogs and link it here.  
- [ ] Document each resolved open question below as a decision with its rationale, in a form the implementation tickets can quote.

## Description

Deleting or editing competency configuration on the Competency Management page happens immediately today, with no confirmation step at all. Underneath, a delete will soon either remove the record or retire it, depending on whether any learner has already been evaluated against it, and the author is deliberately not told which. One wording therefore has to be true in both cases.

\#785 implements the edit dialog. The delete dialog for CompetencyCriteria/CompetencyCriteriaGroup is implemented by \#709 and \#710, which need updating to add it. \#786 implements the ObjectTag association-delete dialog.

## Context for the Designer

**How the two outcomes differ underneath, and why the dialog cannot say which applies.** When no learner has been evaluated against a record, deleting it removes it outright. Once any learner has a mastery status against it, deleting it hides it instead and keeps the row so learner statuses stay traceable. The author cannot tell which case they are in, and product decided they should not need to. So the wording can promise that existing learner statuses are unaffected, and that the action cannot be undone from this screen, without claiming the record is destroyed.

**Edits behave differently from deletes.** An edit never removes anything and never changes a learner's already-recorded status. Changes apply only to evaluations that happen afterwards. That is why the edit wording talks about future evaluations rather than about data loss.

**The edit warning is unconditional**, appearing on every criteria and group edit rather than only when learner statuses already exist. Product chose this so behavior is consistent rather than a dialog that appears unpredictably.

**The edit dialog has no "do not show this again" option.** Letting an author silence it after one click would recreate the same unpredictability product chose the unconditional warning to avoid. If this needs revisiting, it is a scope change for product to approve, not something the designer decides here.

**Tag and Taxonomy edits get no warning at all.** Renaming a tag or editing taxonomy metadata does not change how mastery is computed, so those flows are out of this spike.

**Related tickets.** \#785 implements the edit dialog. The delete dialog for `CompetencyCriteria`/`CompetencyCriteriaGroup` is implemented by existing tickets \#709 (group delete) and \#710 (criterion delete), which currently delete with no confirmation step and need updating to match this spike. \#786 implements the ObjectTag association-delete dialog.

## Open Questions

- Should the delete wording differ between a `CompetencyCriteria` and a `CompetencyCriteriaGroup`? Deleting a group also removes every association inside it, which is materially more destructive, and the current single wording does not say so. Owner: designer, with the BA.  
- Is one shared dialog component right for all three, or should edit and delete look visibly different so an author does not confuse them? Owner: designer.  
- Does the association-delete dialog need to name which competency and which content object the association joins, so an author deleting one of several can tell them apart? Owner: designer.
