# [BE] Branch tag association deletes between archiving and hard delete

GitHub: https://github.com/openedx/openedx-core/issues/779 (#779, OPEN)
Cached: 2026-09-21

## User Story

As a course author, I want to keep the mastery already recorded against it when I remove a competency tag from content, so I don't destroy learners' earned competency history when tidying up a course.

## Acceptance Criteria

Tag associations are removed through several existing code paths: editing an object's tags, deleting the content object itself, re-importing an object's tags, and copying tags between objects. Every one of them must follow the same rule, so testability differs by category below.

### Ordinary path — testable now via Postman or the existing Studio tagging UI

No lock involved; this is exactly today's tag add/remove behavior.

```
Scenario: Removing an association nothing depends on deletes it outright
  Given a content object tagged with a tag that no learner has been evaluated against
  When that tag is removed from the object
  Then the association no longer exists
    And it behaves exactly as removing a tag does today

Scenario: Applying a tag that was never associated creates a new association
  Given a content object that has never been tagged with a given tag
  When that tag is applied to the object
  Then a new association is created
    And it is not archived
```

### Locked path — testable via Postman or the UI, but needs a manufactured fixture

Nothing sets `deletion_locked=True` in production yet; \#782 is what does. Exercising any of these today means creating that state directly first (Django admin, shell, or a test fixture).

```
Scenario: Removing an association that learner mastery depends on archives it instead
  Given a content object tagged with a tag that a learner has been evaluated against
  When that tag is removed from the object
  Then the association still exists but is archived
    And the learner's mastery status still resolves through it

Scenario: Re-applying an archived tag brings the original association back
  Given a content object whose association with a tag is archived
  When that same tag is applied to that object again
  Then the association is no longer archived
    And it is the same association as before, not a new one

Scenario: Re-applying an archived tag keeps its mastery history attached
  Given an archived association that a learner was evaluated against
  When that same tag is applied to that object again
  Then the learner's existing mastery status is still attached to that association

Scenario: Replacing an object's tags archives only the depended-upon ones
  Given a content object with two tags, one depended upon by learner mastery and one not
  When the object's tags are replaced with a list containing neither
  Then the depended-upon association is archived
    And the other association no longer exists

Scenario: Deleting a content object archives the associations learner mastery depends on
  Given a content object with two tags, one depended upon by learner mastery and one not
  When the content object itself is deleted in Studio
  Then the depended-upon association still exists but is archived
    And the other association no longer exists
```

### Internal distinction — unit-test only, never observable via the API or UI

Whether a removed association was archived or hard-deleted is, by design, never visible in the response or the UI. Confirming which one actually happened requires inspecting the database directly, in a test.

```
Scenario: The caller cannot tell which of the two happened
  Given two content objects, one whose association is depended upon and one whose is not
  When the same tag is removed from each
  Then both requests report success in the same way

Scenario: Re-importing an object's tags keeps the associations learner mastery depends on
  Given a content object with a depended-upon association
  When that object's tags are cleared and set again from an import that still includes that tag
  Then the association is the same one as before and is not archived
    And the learner's existing mastery status is still attached to it

Scenario: Syncing from a library archives a depended-upon tag the library no longer has
  Given a course block linked to a library block, with a depended-upon tag copied from that library block
  When the course block syncs from a library block whose tags no longer include that tag
  Then the course block's association still exists but is archived

Scenario: Syncing from a library keeps a depended-upon tag the library still has
  Given a course block linked to a library block, with a depended-upon tag copied from that library block
  When the course block syncs from a library block whose tags still include that tag
  Then the association is the same one as before and is not archived

Scenario: A delete that bypasses the tagging API still archives instead of deleting
  Given a depended-upon association
  When code deletes it directly, either as a single record or as part of a bulk delete, without going through any tagging API function
  Then the association still exists but is archived
```

## Description

Removing a tag from a content object today deletes the association row outright. Once competency mastery is recorded against that association, deleting it would leave the learner's status pointing at nothing. `ObjectTag` gains an `archived` field in \#776 and a `deletion_locked` field that \#782 sets, and this ticket makes every removal path use them.

Tag associations are deleted from several places today: when an author edits an object's tags, when the content object itself is deleted, when an object's tags are re-imported, and when tags are copied between objects. Every one of those paths, and any added later, must archive an association that learner mastery depends on instead of deleting it.

<details>
<summary>Technical Details</summary>

This section is background and a suggested approach, not the ticket's source of truth. The User Story and Acceptance Criteria define what must be true when the work is done.

### In short

**Why the branch goes in the model layer rather than in one API function.** `ObjectTag` rows are deleted from several places in `src/openedx_tagging/api.py` today. `tag_object()` deletes the associations missing from a submitted tag list. `delete_object_tags()` deletes every association on an object, and openedx-platform calls it both when Studio deletes a block, course, or library and when an import clears an object's tags before setting them again. `copy_tags()` deletes a destination object's copied associations before copying new ones. A check placed in only one of these functions leaves the others, and any delete path added later, free to hard-delete a locked association. Putting the branch on `ObjectTag` itself makes every delete path follow it.

**What the branch decides.** For each association being deleted, if it is locked against deletion it is archived instead, and if it is not, it is deleted exactly as today. The rule is deliberately narrow: without a lock, nothing about today's behavior changes. A locked delete archives rather than raising an error, because the callers in openedx-platform, such as the handler that runs when a block is deleted, expect the delete to succeed.

**Deleting a `Tag` or `Taxonomy` does not delete associations.** `ObjectTag.tag` and `ObjectTag.taxonomy` use `on_delete=SET_NULL`, so deleting either parent leaves the association row in place with a null foreign key. \#780 covers that case: it archives a locked `Tag` or `Taxonomy` instead of deleting it, so a depended-upon association never loses its foreign key.

**Why re-applying un-archives in place rather than creating a new row.** An archived association still occupies its slot in the unique constraint on the object, taxonomy, and tag together. Creating a second row for the same three values would either violate that constraint or force it to be widened to include the archived flag, and widening it would let duplicate live associations exist. Un-archiving the existing row also keeps any competency criterion's foreign key pointing at a stable row rather than orphaning it against a superseded one.

- This is a distinct question from, and unaffected by, \#655's later "error rather than auto-unarchive" resolution about recreating a `Tag` with the same value as an archived one: that discussion concerns whether creating a *new* `Tag` row should silently resurrect an old one when the two might represent different competencies with a coincidentally shared name, an ambiguity that does not exist here, where the same `Tag` id is being reapplied to the same object id, not recreated.

**A consequence worth stating plainly.** Because the original row comes back, its mastery history comes back with it. An author who removes a competency tag and later re-adds it does not get a clean slate; the learners previously evaluated against that association are still evaluated against it. That is the intended behavior, and it is the reason the confirmation dialog in \#775 says the action cannot be undone from this screen rather than promising deletion.

### Implementation specifics

- **Cover both ways Django deletes a row.** Calling `.delete()` on a queryset deletes the matching rows in bulk without ever calling each model instance's `delete()` method. So overriding `ObjectTag.delete()` alone misses `delete_object_tags()` and `copy_tags()`, which both delete through a queryset. Override the instance `delete()` and the `ObjectTag` queryset's `delete()`, and route both through one shared function that does the split. Coordinate with \#778, which adds a manager or queryset to `ObjectTag` for its archived filter, so the two tickets extend the same class.  
- **Read the lock through the query function \#777 adds**, not by reading `deletion_locked` directly, so the delete branches in this ticket and \#780 ask the same question the same way.  
- **Resolve the removal set in bulk, then split it in two.** One `.update(archived=True)` over the locked ids and one real delete over the rest, rather than a per-association branch inside a loop. `tag_object()` currently calls `old_tag.delete()` once per removed association; with a lock check on the instance `delete()`, that loop would add a query per association, an N+1 on every content-tagging save. Switch that loop to a single queryset delete over the removal set.  
- **No new endpoint and no new public API function.** The existing callers keep calling what they call today.  
- **The un-archive step needs to see archived rows**, which \#778 filters out of the normal read paths. Use the documented opt-out that \#778 provides rather than adding a second one.  
- **Un-archive in place with `.update(archived=False)` on the existing row.** Do not delete and recreate, and do not touch the unique constraint on `(object_id, taxonomy, tag)`.  
- **Leave the lock alone when un-archiving.** A re-applied association is still depended upon by the same learner statuses, so clearing `deletion_locked` would make the next removal destroy them.  
- **The response shape does not change.** A caller must not be able to tell archiving from deletion, per the approved approach, so do not add a field reporting which happened.  
- **Paths that delete and then re-create must find the archived row.** `copy_tags()` deletes a destination's copied associations and then calls `update_or_create()` for each source tag, and openedx-platform's import path calls `delete_object_tags()` and then sets the tags again. Once the delete archives a locked row, the re-create step must un-archive that same row, not insert a second one, or it hits the unique constraint on `(object_id, taxonomy, tag)`. That means those re-create steps need \#778's opt-out to see archived rows. Also confirm that `copy_tags()` never copies the archived flag onto a new object.  
- **Check `resync_object_tags`** in the same module, which updates associations to match changes made to their taxonomies and tags. It should not resurrect an archived row unintentionally. State what it does in the PR description even if it needs no change.  
- **Tests** in the existing `openedx_tagging` API and model tests, one per scenario, plus: a query-count assertion showing the branch adds a constant number of queries rather than one per association; a test that the unique constraint is unchanged; a test that a competency criterion's foreign key still points at the same row after a remove-then-re-apply cycle.  
- **Out of scope:** setting the lock (\#782), tag and taxonomy deletes (\#780), the archive event fan-out (\#781), and the confirmation dialog (\#786).

## Files to modify

| File | Nature of modification |
| :---- | :---- |
| src/openedx\_tagging/models/base.py | modified: `ObjectTag.delete()` and the `ObjectTag` queryset's `delete()` branch between archive and real delete |
| src/openedx\_tagging/api.py | modified: `tag_object()` removes associations with one queryset delete and un-archives on re-apply; `copy_tags()` un-archives instead of re-creating |
| tests/openedx\_tagging/ | modified: one test per scenario, a query-count assertion, and a foreign-key stability test |

### Context 

- The approved implementation approach on \#655: archive only when a learner status row exists, un-archive in place on re-apply, and why the caller is not told which happened.  
- `src/openedx_tagging/api.py`: `tag_object()`, `delete_object_tags()`, and `copy_tags()` are today's association delete paths, and `resync_object_tags()` is a neighbouring path.  
- `src/openedx_tagging/models/base.py` for `ObjectTag`, its unique constraint, and its `SET_NULL` foreign keys.  
- openedx-platform's `openedx/core/djangoapps/content_tagging/handlers.py` (deleting tags when content is deleted) and `content_tagging/api.py`, `set_exported_object_tags()` (clearing and re-setting tags on import), the two callers of `delete_object_tags()`.  
- Depends on \#776 for both fields, \#777 for the lock query, and \#778 for the documented opt-out that lets this path see archived rows. The lock itself is set by \#782.

</details>
