# [BE] Strip competency tags from duplicated content

GitHub: https://github.com/openedx/openedx-core/issues/808 (#808, OPEN)
Cached: 2026-09-21

## User Story

As a course author, I want a duplicate of a section or subsection to start with no competency tags, even if the section or subsection it was copied from had some, in order to keep duplication a plain content-editing action rather than something that silently changes what counts toward a competency's mastery.

## Acceptance Criteria

```
Scenario: Duplicating content strips any competency tag
  Given a section or subsection is tagged with a competency
  When I duplicate it
  Then the duplicate carries no tag from that competency's taxonomy
  And the original's tag is unchanged

Scenario: Regular, non-competency tags still carry over
  Given a section or subsection is tagged with both a competency and a tag from a regular, non-competency taxonomy
  When I duplicate it
  Then the duplicate keeps the regular tag
  And the duplicate carries no competency tag

Scenario: No competency criteria appear on the duplicate
  Given a subsection is tagged with a competency and has a mastery rule attached
  When I duplicate that subsection
  Then no competency criteria group or rule references the duplicate
  And the original subsection's rule is unaffected
  And I see no error

Scenario: Tags from more than one competency taxonomy are all stripped
  Given a section or subsection is tagged with competencies from two different competency taxonomies
  When I duplicate it
  Then the duplicate carries no tag from either competency taxonomy

Scenario: Duplicating content with no competency tags is unaffected
  Given a section or subsection has only tags from regular, non-competency taxonomies
  When I duplicate it
  Then the duplicate carries the same regular tags
  And I see no error

Scenario: Duplicating a section strips competency tags from every subsection beneath it
  Given a section contains a subsection tagged with a competency
  When I duplicate that section
  Then the duplicated section and every duplicated subsection beneath it carry no competency tag
  And their regular tags are unaffected

Scenario: A failure while stripping tags does not cost me the duplicated content
  Given a section or subsection tagged with a competency
  When I duplicate it and stripping the competency tag fails
  Then the duplicate still appears in my course outline with its regular tags
  And the duplicate may still carry the competency tag, since the removal did not complete
  And the failure is recorded so an operator can find it

Scenario: No extra permission is needed beyond the permission to duplicate
  Given I am a course author who can edit my course outline
  And I have no competency-authoring rights on the competency taxonomy involved
  When I duplicate a section or subsection tagged with a competency
  Then the duplicate is created without the competency tag
  And the duplication is not blocked
```

Technical Details This section is background and a suggested approach, not the source of truth. The User Story and Acceptance Criteria define what must be true when the work is done; what follows exists to save the implementer some thinking.

### In short

**What already happens, and what this adds.** Today, `content_tagging.handlers.duplicate_tags` (`@receiver(XBLOCK_DUPLICATED)`) copies every tag from every taxonomy onto a duplicated block, synchronously, via `copy_object_tags`. That stays exactly as it is; nothing in `content_tagging` changes. This ticket adds a second, independent reaction to the same event, in Studio's own signal handlers rather than in `content_tagging`, that strips competency tags back off the duplicate afterward. `content_tagging` and `openedx_tagging` never learn that competencies exist.

**How a competency taxonomy is detected without the tagging app knowing about CBE.** `openedx_learning.api.is_competency_taxonomy()` and its bulk companion `select_competency_taxonomies()` already exist for exactly this purpose (ADR 0013, Accepted): they let `openedx-platform` ask "is this taxonomy a competency taxonomy" by checking for a related `CompetencyTaxonomy` row, with no field, method, or CBE-specific concept added to `openedx_tagging` itself.

**How the tags are removed.** `content_tagging.api.tag_object(object_id, taxonomy, tags=[])` replaces one taxonomy's tags on an object with an empty set, leaving every other taxonomy's tags untouched. The new task calls this once per competency taxonomy found on the duplicate.

**Why the task is enqueued via `transaction.on_commit`.** This app sets `ATOMIC_REQUESTS: True`, so the whole duplicate request, including `duplicate_tags`'s synchronous tag copy, is one open database transaction until the view returns. The new receiver enqueues the stripping task inside `transaction.on_commit(...)`, so the task starts only once that transaction has committed and the copied tags are visible to it, the same pattern this file's own `listen_for_course_publish` receiver already uses for its own tasks.

**Why nothing in `openedx-core` needs to change.** A `CompetencyCriterion` always points at an existing `ObjectTag` row; if a competency tag never lands on the duplicate, there is nothing for any criterion to attach to. No new `CompetencyCriteriaGroup`, no placement logic, and no data-model change are needed anywhere.

**Scope: sections and subsections only.** \#784 (in drafting) restricts new competency tagging to the subsection level, and is expected to land before this ships, so a unit or component should never carry a competency tag to begin with. The new receiver filters on the duplicated block being a `chapter` or `sequential`, rather than checking every duplicated block including units and components.

### Implementation specifics

- **New receiver.** Add a new `@receiver(XBLOCK_DUPLICATED)` to `cms/djangoapps/contentstore/signals/handlers.py`, guarding the payload the same way the file's existing `XBLOCK_DELETED`/`XBLOCK_UPDATED` receivers guard theirs, and returning early unless the duplicated block's type is `chapter` or `sequential`.  
- **Enqueue on commit.** `transaction.on_commit(lambda: strip_competency_tags_from_duplicate.delay(destination_content_key_str))`, matching this file's own `listen_for_course_publish` receiver, so the task starts only once the request's transaction, including `duplicate_tags`'s tag copy, has committed.  
- **New task.** Add `strip_competency_tags_from_duplicate(destination_content_key_str)` to `cms/djangoapps/contentstore/tasks.py`.  
- **Task logic.** Call `content_tagging.api.get_all_object_tags(destination_key)` to get the tags-by-taxonomy already copied onto the destination and the taxonomy dict. Run that taxonomy dict's values through `openedx_learning.api.select_competency_taxonomies()` (or check each with `is_competency_taxonomy()`) to find which are competency-enabled. For each one found with tags on the destination, call `content_tagging.api.tag_object(object_id=str(destination_key), taxonomy=that_taxonomy, tags=[])`.  
- **No object-id mapping needed.** Unlike \#694's design, this doesn't resolve a source-to-destination content id at all: it only inspects the destination's own tags after the copy has already happened, and the `XBLOCK_DUPLICATED` payload's usage key already gives the destination's usage key directly.  
- **Layering.** This ticket touches only `openedx-platform`. Nothing in `openedx-core` (`openedx_tagging`, `content_tagging`, or `openedx_learning`) is modified; their existing public API is only called.  
- **Idempotency.** `tag_object(..., tags=[])` on an object that already has no tags from that taxonomy is a no-op, so retrying this task after a failure is safe without any special-casing.  
- **Test cases.** Cover every scenario in Acceptance Criteria above, plus: retrying the task after a forced failure against a destination that already has no tags left for that taxonomy (the idempotency guarantee above); the receiver ignoring a duplicated `vertical` or component; and the receiver enqueuing via `transaction.on_commit`, checked with Django's `captureOnCommitCallbacks()` test helper, since a standard eager-Celery test setup can't exercise the race that guard is for.

Files to create and modify **Modified files**

| File | Nature of modification |
| :---- | :---- |
| `cms/djangoapps/contentstore/signals/handlers.py` (openedx-platform) | Add the `XBLOCK_DUPLICATED` receiver that enqueues the new task |
| `cms/djangoapps/contentstore/tasks.py` (openedx-platform) | Add `strip_competency_tags_from_duplicate` |
| `cms/djangoapps/contentstore/signals/tests/test_handlers.py` (openedx-platform) | Add receiver tests |
| `cms/djangoapps/contentstore/tests/test_tasks.py` (openedx-platform) | Add task tests |

- Context ADR 0013 (`docs/openedx_tagging/decisions/0013-competency-taxonomy-detection.rst`, Accepted): the detection mechanism this ticket calls, and why it lives in `openedx-platform` rather than in `openedx_tagging`.  
- `openedx/core/djangoapps/content_tagging/handlers.py` (openedx-platform): `duplicate_tags`, unchanged by this ticket, the existing tag copy this ticket's task reacts after.  
- `src/openedx_learning/applets/cbe/api.py` (openedx-core): `is_competency_taxonomy`, `select_competency_taxonomies`, already implemented and tested.  
- \#694 (copy competency criteria and content tags to a new course run): a deliberately different scope. A course rerun intentionally carries competency tags and mastery rules forward, since it's a new offering of the same course. This ticket's same-course duplication intentionally does not, since it's an authoring convenience copy, not a new offering.  
- \#784 (in drafting): restricts new competency tagging to the subsection level, which this ticket's `chapter`/`sequential` filter relies on landing first.  
- `cms/djangoapps/contentstore/signals/handlers.py`'s `listen_for_course_publish` receiver (openedx-platform): the existing `transaction.on_commit(lambda: task.delay(...))` pattern this ticket's new receiver follows.
