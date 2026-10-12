# [BE] Fan out the content-tag-changed event when a taxonomy is archived

GitHub: https://github.com/openedx/openedx-core/issues/781 (#781, OPEN)
Cached: 2026-09-21

## User Story

As a course author, I want search and content listings to stop showing a retired competency framework's tags so I don't see or filter by competencies that are no longer in use.

## Acceptance Criteria

No REST endpoint or UI here; this is Celery task/event wiring, checked by asserting the task fired, not through Postman or a UI. End-to-end, the natural manual check is the Libraries or Studio search UI, once `openedx-platform` and Meilisearch are both involved.

```
Scenario: Archiving a taxonomy notifies every affected content object
  Given an archived-eligible taxonomy whose tags are applied to three content objects
  When the taxonomy is archived
  Then a content-tag-changed notification is emitted once for each of those three objects

Scenario: Archiving a tag notifies every affected content object, even without archiving its taxonomy
  Given a tag, not its whole taxonomy, whose associations are locked and applied to two content objects
  When that tag is archived by a tag-level delete request
  Then a content-tag-changed notification is emitted once for each of those two objects

Scenario: Search stops returning an archived framework's tags
  Given content indexed with tags from a taxonomy
  When that taxonomy is archived and the notifications are processed
  Then searching no longer returns those tags for that content

Scenario: Archiving a taxonomy with no tagged content emits nothing
  Given a taxonomy whose tags are applied to no content
  When the taxonomy is archived
  Then no content-tag-changed notification is emitted
    And the archive completes successfully

Scenario: Archiving a tag with no tagged content emits nothing
  Given a tag whose associations are locked but applied to no content
  When that tag is archived by a tag-level delete request
  Then no content-tag-changed notification is emitted

Scenario: Each affected object is notified once, however many tags are involved
  Given a content object carrying four tags, all being archived in the same request, whether from one taxonomy-level archive or one tag-level bulk delete
  Then exactly one content-tag-changed notification is emitted for that object

Scenario: Hard-deleting a taxonomy or a tag still behaves as it does today
  Given a taxonomy, or a tag, that nothing depends on
  When it is deleted outright
  Then notification behaves exactly as it does today

Scenario: A failure to notify does not undo the archive
  Given a taxonomy or a tag that is archived
  When the notification cannot be delivered
  Then the archive stands
    And the failure is retried
```

## Description

Archiving a taxonomy or a tag hides it from the tagging app's own read paths once \#778 lands, but the search index is a separate store populated from events. Nothing currently tells it that an archive happened, so it would keep serving stale tags on every affected content object indefinitely.

**Both archive branches need this.** `openedx_tagging` already emits a content-tag-changed event for an ordinary tag *edit* or *hard delete*, through `Tag`'s existing `post_save`/`pre_delete` signals. Those signals do not fire for a bulk `.update()`, which is exactly how \#780 sets `archived=True`, on a `Taxonomy` in `TaxonomyView.perform_destroy()` and on one or more `Tag`s in `Taxonomy.delete_tags()`. Both are the same gap: a state change that removes nothing and triggers no existing signal, so both need this ticket's explicit event.

<details>
<summary>Technical Details</summary>

This section is background and a suggested approach, not the ticket's source of truth. The User Story and Acceptance Criteria define what must be true when the work is done.

### In short

**Why archiving needs an event when deleting already has one.** A hard delete removes rows via a `QuerySet.delete()`, which still fires `pre_delete` per row and reaches the existing signal handler. An archive is a bulk `.update()`, which Django does not fire any signal for at all. Without an explicit event, the index has no way to learn anything happened.

**Fan out per content object, not per tag.** The index is keyed by content object, and one object can carry several tags being archived in the same request, whether that's several tags under one archived taxonomy or several tags archived together in one bulk `delete_tags()` call. Emitting per tag would reindex the same object repeatedly for no benefit, so the set of affected object ids is collected and deduplicated first and one event is emitted for each.

**Reuse the existing object-ids task for both triggers.** `src/openedx_tagging/tasks.py` already has `emit_content_object_associations_changed_for_object_ids_task`, used today by the hard-delete signal. Both the taxonomy branch and the tag branch collect their own affected object ids and hand them to this same task; neither needs a new event or a new task.

**The event is emitted after the archive commits, not inside it.** The archive is the thing that must succeed; notifying the index is a follow-up that Celery retries. Emitting inside the transaction would announce an archive that could still roll back, and a delivery failure must not undo the archive.

**Finding the affected objects means reading archived rows.** By the time this runs, \#778 has made archived records invisible to the normal read paths, and \#780's ancestor archiving may have archived several tags in the same request. Use the opt-out \#778 documents — likely a keyword like `include_archived=True` on the relevant `openedx_tagging.api` read function, or a queryset method, though \#778 hasn't pinned down the exact shape yet — so this ticket's queries see archived rows while ordinary callers keep the default filtered view.

A note on manually verifying this end-to-end. This repo has no UI of its own to check this in. Once openedx-platform and Meilisearch are both involved, the Libraries search/filter UI is a reasonable place to confirm an archived tag stops appearing, since it's a straightforward consumer of the same per-object tags data this event refreshes. That's a devstack-level check across repos, not part of this ticket's own automated tests.

### Implementation specifics

- **Taxonomy branch: trigger from the archive branch \#780 adds** to `TaxonomyView.perform_destroy`, registered with `transaction.on_commit` so it fires only once the archive has committed. Do not emit from inside the archive write.  
- **Tag branch: trigger from the archive branch \#780 adds** to `Taxonomy.delete_tags()`, registered with `transaction.on_commit` the same way, right after the `.update(archived=True)` call over the computed archive set.  
- **Collect the affected object ids per branch:**  
  - Taxonomy branch: the distinct `object_id` values of `ObjectTag` rows whose tag belongs to the archived taxonomy.  
  - Tag branch: the distinct `object_id` values of `ObjectTag` rows whose tag is in the set of tag ids just archived by that one `delete_tags()` call.  
- Both using the documented opt-out from \#778 so archived rows are included. One query per branch, not a query per tag.**Hand them to the existing task** `emit_content_object_associations_changed_for_object_ids_task` in `src/openedx_tagging/tasks.py`, called the way `src/openedx_tagging/signal_handlers.py` already calls it for the hard-delete tag-change case. Do not define a new event or a second emission path.  
- **Deduplicate before emitting.** The existing task emits once per distinct object id; make sure the id set handed to it is already distinct so the guarantee does not depend on the task.  
- **Batch a large fan-out.** A framework-wide taxonomy, or a large `with_subtags` archive, can affect a great many objects, so chunk the id list rather than passing an unbounded list in one task payload. Follow whatever batching the neighbouring tasks in that module already use, and if they use none, say so on the issue rather than inventing a batch size silently.  
- **Do not change the hard-delete path.** It already notifies through the existing signal handling, and adding a second emission would double-reindex.  
- **Retry is Celery's job.** The task already runs asynchronously; do not catch and swallow a delivery failure in either archive path, and do not make either archive conditional on it.  
- **Tests** in the existing `openedx_tagging` task and signal tests: one event per affected object, for each branch; exactly one event for an object carrying several archived tags at once, for each branch; no event when nothing is tagged, for each branch; a query-count assertion showing the object ids are gathered in a constant number of queries; the archive survives a task failure, for each branch; the hard-delete path emits exactly what it emits today and no more, for both a tag and a taxonomy.  
- **Out of scope:** the archive branches themselves (\#780), read-path exclusion (\#778), the `ObjectTag`\-level archive branch (\#779, already covered by `openedx-platform`'s existing `tag_object()` wrapper, confirmed while reviewing this ticket), and anything in the search index implementation, which lives outside this repository.  
- 

## Files to modify

| File | Nature of modification |
| :---- | :---- |
| src/openedx\_tagging/rest\_api/v1/views.py | register the post-commit fan-out from the taxonomy archive branch |
| src/openedx\_tagging/models/base.py | register the post-commit fan-out from the tag archive branch in `delete_tags()`  |
| tests/openedx\_tagging/ | per-object emission, deduplication, empty case, query-count, and retry tests, for both branches |

## Context 

- The approved implementation approach on \#655, for why an archived taxonomy or tag must not keep being served by the index.  
- `src/openedx_tagging/tasks.py` for `emit_content_object_associations_changed_for_object_ids_task` and the `CONTENT_OBJECT_ASSOCIATIONS_CHANGED` event it sends.  
- `src/openedx_tagging/signal_handlers.py` for how the existing hard-delete case calls that task, and why a bulk `update()` doesn’t reach it.  
- `openedx-platform`'s `openedx/core/djangoapps/content/search/handlers.py` and `documents.py`, for the confirmed-unaffected consumer side: it rebuilds a content object's tags from `get_object_tags()` on receiving this event, so it needs no changes once \#778 lands.  
- `openedx-platform`'s `openedx/core/djangoapps/content_tagging/api.py`, `tag_object()`, for the confirmed-unaffected `ObjectTag`\-level wrapper that already emits this event unconditionally, covering \#779. Between this and the point above, no other repo-side gap was found once this ships — the only missing piece was the trigger for the two archive branches this ticket adds.  
- Depends on \#780 for both archive branches it hooks into and \#778 for the opt-out that lets it read archived rows. Sequence alongside \#780 so no released version archives a taxonomy or a tag without notifying the index.

</details>
