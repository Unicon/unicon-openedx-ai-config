# [BE] Exclude archived tagging records from read paths and block edits to them

GitHub: https://github.com/openedx/openedx-core/issues/778 (#778, OPEN)
Cached: 2026-09-21

## User Story

As a course author, I want a retired taxonomy, tag, or tag association to stop appearing anywhere I work, in order to not see or pick something that is no longer in use while the learner mastery history behind it stays intact.

## Acceptance Criteria

Testable directly via Postman against the existing REST endpoints listed under Implementation specifics below. These same endpoints already back Studio's Taxonomies page, tag search/autocomplete, and content-tagging drawer, so once an archived row exists, this should also be visible in the existing frontend with no new frontend ticket needed. The one practical caveat: see the "Nothing sets `archived=True` yet" note below — testing any of this today means creating an archived row directly (via the Django admin, shell, or a test fixture), since no shipped ticket yet produces one through ordinary use.

```
Scenario: An archived tag does not appear when listing a taxonomy's tags
  Given a taxonomy with one archived tag and two that are not archived
  When its tags are listed
  Then only the two that are not archived are returned

Scenario: An archived tag does not appear in tag search or autocomplete
  Given an archived tag whose value matches a search term
  When a search or autocomplete request uses that term
  Then the archived tag is not among the results

Scenario: An archived child tag does not appear beneath its parent
  Given a tag with one archived child and one that is not archived
  When that tag's children are listed
  Then only the child that is not archived is returned

Scenario: An archived tag association does not appear on the object it tagged
  Given a content object with one archived tag association and one that is not
  When that object's tag associations are listed
  Then only the association that is not archived is returned

Scenario: An archived association is not counted in a usage count
  Given a tag whose only remaining association is archived
  When usage counts are read for that taxonomy
  Then that tag reports a usage count of zero

Scenario: An archived tag is not included in a taxonomy export
  Given a taxonomy with one archived tag
  When the taxonomy is exported
  Then the archived tag is absent from the exported output

Scenario: An archived taxonomy does not appear when listing taxonomies
  Given one archived taxonomy and one that is not archived
  When taxonomies are listed
  Then only the one that is not archived is returned

Scenario: Retrieving an archived record directly reports that it is not available
  Given an archived tag
  When it is requested directly by its identifier
  Then the request reports that it is not available

Scenario: An archived record cannot be edited
  Given an archived tag
  When an edit to it is submitted
  Then the edit is refused with an explanation
    And the tag is unchanged

Scenario: Archiving one record does not hide its unarchived siblings
  Given a taxonomy with several tags, one of which is archived
  When the taxonomy and its tags are read
  Then the taxonomy and every unarchived tag are returned as before

Scenario: An archived taxonomy hides its own unarchived tags from read paths
  Given a taxonomy that is archived, whose tags are not themselves marked archived
  When those tags are listed, searched, or retrieved directly
  Then they are excluded exactly as if each were archived itself

Scenario: An archived taxonomy hides tag associations through its unarchived tags
  Given a content object tagged with a tag whose taxonomy is archived, though neither the tag nor the association is itself marked archived
  When that object's tag associations are listed
  Then that association is excluded exactly as if it were archived itself
```

## Description

`Taxonomy`, `Tag`, and `ObjectTag` gain an `archived` field in \#776, but nothing reads it, so an archived record would still be listed, searched, exported, counted, and editable exactly as before. Archiving would then hide nothing.

This ticket makes an archived record inert. It stops appearing on every read path in `openedx_tagging`, and every write path refuses to change it. The row stays in the database so that learner mastery statuses referencing it remain traceable, which is the whole reason archiving exists rather than deleting.

<details>
<summary>Technical Details</summary>

This section is background and a suggested approach, not the ticket's source of truth. The User Story and Acceptance Criteria define what must be true when the work is done.

### In short

**Nothing sets `archived=True` yet, and this ticket does not need anything to.** \#779 (`ObjectTag`) and \#780 (`Tag`/`Taxonomy`) are what sets `archived=True`, when a locked delete happens. This ticket's own tests don't depend on either: they create rows with `archived=True` directly to exercise these read and write paths in isolation, the same way a filter is normally tested. What \#779/\#780 provide is the only way an admin-facing action ever produces an archived row in production, so until they also land, this ticket's filtering has nothing real to filter against, even though it is fully buildable, reviewable, and testable on its own right now. Not a blocking dependency, just worth naming so the sequencing is explicit.

**What "inert" means here.** An archived record is still in the database and still resolvable by a foreign key, so anything already pointing at it keeps working. What changes is that the tagging app stops offering it: it is absent from lists, searches, autocompletes, children, exports, and usage counts, a direct fetch reports it as unavailable, and any attempt to edit it is refused.

**Why every read path and not just the obvious ones.** The purpose of archiving is that an author stops encountering a retired record. A single missed path defeats that in a way that is hard to notice: an author who cannot see an archived tag in a list but can still pick it from an autocomplete will tag content with it and create fresh associations to something retired. So the work is a sweep, and the acceptance criteria enumerate the paths deliberately.

**"Tag search or autocomplete" here means this app's own database query, not a search engine.** The scenario above exercises `search_tags()` in `openedx_tagging/api.py`, a plain queryset filter local to this repo. It has no dependency on Meilisearch or any other search-engine integration, and nothing in this ticket's scope touches one. Keeping a separate content search index in sync when a taxonomy is archived is a different concern, handled by \#781's event fan-out, and is explicitly out of scope here.

**An archived taxonomy hides its tags too, without the field cascading onto them.** A tag's own `archived` field never gets set just because its taxonomy was archived, per the approved design in [this \#655 comment](https://github.com/openedx/openedx-core/issues/655#issuecomment-5433022795) ("Archiving doesn't cascade `archived=True` onto child `Tag` rows, and filtering doesn't need it to"). But the read-path filter this ticket adds must still exclude a tag whose taxonomy is archived, computed at query time, the same as if the tag were archived itself: an author has no reason to see a tag left behind under a retired taxonomy. The same applies one level further down: an `ObjectTag` association must be excluded if its tag's taxonomy is archived, even when neither the association nor the tag carries `archived=True`. This is a real cost, not a free extension of the existing filter: excluding on `Tag.archived` alone is a flat field check, while this also needs a join or subquery up to `Taxonomy.archived` for every tag read, and up through both levels for every association read.

**Usage counts and exports are read paths too.** A usage count that includes archived associations tells an author a tag is in use when nothing visible uses it. An export that includes archived tags reintroduces them on the next import into another instance. Both are easy to overlook because neither looks like a list endpoint.

**Blocking edits is the write-path half.** Nothing should be able to rename, re-parent, or otherwise modify a record that has been retired, because doing so changes what a learner mastery status points at. Deletes are a separate concern and are handled by \#779 and \#780.

### Implementation specifics

- **Prefer filtering in one shared place over touching each call site.** The read paths in `src/openedx_tagging/api.py` largely funnel through a small number of querysets, so a default manager or queryset method excluding `archived=True` will cover more ground with less duplication than a per-function filter, and is far harder to forget on a future path. Confirm whether the existing `TagDataQuerySet` and the model managers give a single choke point before editing functions one by one; if they do not, say so on the issue rather than scattering filters silently.  
- **The tag exclusion is `archived=True` OR its taxonomy is archived; the association exclusion is `archived=True` OR its tag is excluded by that same rule.** Neither `Tag.archived` nor `ObjectTag.archived` is set just because an ancestor was archived, so the choke point must check the ancestor's field too, not only the record's own.  
- **The API read paths to cover**, all in `src/openedx_tagging/api.py`: `get_taxonomies`, `get_taxonomy`, `get_taxonomy_by_export_id`, `get_tags`, `get_root_tags`, `search_tags`, `get_children_tags`, `get_object_tags`, `get_object_tag_counts`, and `add_usage_counts`.  
- **The REST read paths to cover**, in `src/openedx_tagging/rest_api/v1/views.py`: the list and retrieve actions on `TaxonomyView`, `TaxonomyTagsView`, `ObjectTagView`, and `ObjectTagCountsView`, and the export action on `TaxonomyView`.  
- **The export path** also runs through `src/openedx_tagging/import_export/api.py` (`export_tags`); an archived tag must not appear in either output format.  
- **A direct retrieve of an archived record returns the standard not-found response** rather than a new error type, so callers need no new handling. Confirm this against `src/openedx_tagging/rest_api/v1/exception_handlers.py` conventions.  
- **Write paths to block**, refusing an edit to an already-archived record with a validation error: `update_tag_in_taxonomy` and the update actions on `TaxonomyView` and `TaxonomyTagsView`. `tag_object` is deliberately excluded here, because \#779 gives it archive and un-archive behavior of its own; do not add a blanket block there.  
- **Do not filter the paths the delete branches rely on.** \#779 and \#780 need to find an archived `ObjectTag` in order to un-archive it, and \#781 needs to find an archived taxonomy's associations in order to fan out its event. Whatever choke point this ticket adds must offer a documented way to opt out, and that escape hatch must be named on this issue so the later tickets can use it rather than reinventing one.  
- **Watch the N+1 risk on usage counts.** Excluding archived associations from `get_object_tag_counts` and `add_usage_counts` must stay a single aggregate query, not a count per tag. Add a query-count assertion to the tests for those two.  
- **Tests** in the existing `openedx_tagging` API and REST test modules, one per acceptance scenario, plus: a query-count assertion on the two counting paths; a test that a foreign key to an archived record still resolves; and a test that the documented opt-out returns archived records, since \#779 through \#781 depend on it.  
- **Out of scope:** the delete branches (\#779, \#780), the archive event fan-out (\#781), and any UI change.

## Files to modify 

| File | Nature of modification |
| :---- | :---- |
| src/openedx\_tagging/models/base.py | queryset or manager choke point excluding archived records, with a documented opt-out |
| src/openedx\_tagging/api.py | exclude archived records from the read paths listed above; refuse edits to archived records |
| src/openedx\_tagging/rest\_api/v1/views.py | exclude archived records from list, retrieve, and export actions; refuse updates to archived records |
| src/openedx\_tagging/import\_export/api.py | exclude archived tags from export output |
| tests/openedx\_tagging/ | one test per scenario, query-count assertions on the counting paths, and an opt-out test |

### Context 

- The approved implementation approach on \#655, for what archiving is meant to achieve.  
- `src/openedx_tagging/api.py` for the read paths and the module contract.  
- `src/openedx_tagging/models/base.py` for `TagDataQuerySet` and the existing managers, the likely home for the shared filter.  
- Depends on \#776 for the `archived` field. \#779, \#780, and \#781 depend on the opt-out this ticket documents.

</details>
