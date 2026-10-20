# [Placeholder] Make tag import reconcile a block's tags instead of deleting and re-creating them

GitHub: pending
Cached: 2026-10-20

## User Story

## Description

## Context

## Notes for drafting

- Origin (2026-10-20): raised during the pre-handoff checks of #696 (course import of competency criteria) and the Epic 10 ticket for pruning criteria groups emptied by a tag association delete (`10-competency-guardrails-723/ucid-10.xx-ghi-pending.md`). Nice-to-have, Epic 11 (#724), `[NTH - BE]` prefix.
- Verified facts: on course import, openedx-platform's `content_tagging/api.py` `set_exported_object_tags()` (~299) calls `openedx_tagging.api.delete_object_tags(object_id)` before re-tagging; that function runs `ObjectTag.objects.filter(object_id=object_id).delete()` with no taxonomy filter (`src/openedx_tagging/api.py` ~285-291), so every association on the block in every taxonomy is removed, then `tag_object()` re-creates only the taxonomies the `tags.csv` row carries. An unchanged tag therefore gets a new row id. `CompetencyCriterion.object_tag` is `on_delete=CASCADE`, so every criterion on the old row is deleted with it; with #779, an association that learner mastery depends on is archived and restored in place instead, so only ungraded criteria are lost. `import_tags` runs inside `store.bulk_operations` with only `FileNotFoundError` and `ValueError` caught and no `transaction.atomic` of its own (`xmodule/modulestore/xml_importer.py` ~593-600).
- Suggested fix at decision altitude: reconcile per taxonomy through `tag_object()`, which keeps rows still listed, adds new ones, and removes missing ones. To keep today's "the CSV is the full picture" behavior, pass an empty list for any taxonomy the block has but the CSV omits. Unchanged rows, and the criteria on them, then survive. Real removals go through the archive-or-delete step #779 adds, so the graded case depends on #779.
- Why not #779: #779 changes only `openedx_tagging`; this fix is in openedx-platform's `content_tagging`, which must stay unaware of CBE. Why not #696: the loss happens on any re-import of a course with criteria, with or without a criteria file.
- Related: #696 (its find-or-create merge refills criteria the wipe removed when the archive carries a criteria file; this ticket makes that refill unnecessary for unchanged tags), #695, #779, #782, #652 (docs), and the Epic 10 pruning ticket above (which treats re-import as a trigger and leaves the rule loss to this ticket).
