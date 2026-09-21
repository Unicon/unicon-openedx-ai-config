# [BE] Return taxonomy type on the per-object tag endpoint

GitHub: https://github.com/openedx/openedx-core/issues/783 (#783, OPEN)
Cached: 2026-09-21

## User Story

As a course author, I want the pages that show a content object's tags to be able to tell a competency apart from an ordinary tag, in order to be shown the right controls for each and not be offered actions that would damage competency configuration.

## Acceptance Criteria

```
Scenario: A competency tag on a content object reports its taxonomy type
  Given a content object tagged from a competency taxonomy
  When that object's tags are requested
  Then each tag from that taxonomy reports a taxonomy type of competency

Scenario: An ordinary tag on a content object reports its taxonomy type
  Given a content object tagged from a taxonomy that is not a competency taxonomy
  When that object's tags are requested
  Then each tag from that taxonomy reports a taxonomy type that is not competency

Scenario: An object carrying both kinds reports each correctly
  Given a content object tagged from both a competency taxonomy and an ordinary one
  When that object's tags are requested
  Then the tags are distinguishable by their reported taxonomy type

Scenario: An object with no tags succeeds and reports nothing extra
  Given a content object with no tags
  When that object's tags are requested
  Then the response succeeds
    And it contains no taxonomy type information

Scenario: Reading tags for many objects does not slow down with the number of taxonomies
  Given several content objects tagged from several taxonomies
  When their tags are requested in one call
  Then the number of database queries does not grow with the number of taxonomies involved

Scenario: Existing consumers are unaffected
  Given a client reading the per-object tag endpoint that knows nothing of taxonomy type
  When it reads an object's tags
  Then every field it already relied on is unchanged
```

## Description

**This ticket's implementation belongs entirely in `openedx-platform`, not `openedx-core`.** Per ADR 0013 (`docs/openedx_tagging/decisions/0013-competency-taxonomy-detection.rst`), nothing about "is this a competency taxonomy" may be added to `openedx_tagging` or the CBE app. \#618 establishes this same boundary for the taxonomy endpoints: `taxonomy_type` is planned to live entirely in `openedx-platform`'s `TaxonomyOrgSerializer`/`TaxonomyOrgView` (`openedx/core/djangoapps/content_tagging/rest_api/v1/`), subclassing `openedx_tagging`'s generic base classes rather than adding anything to them. This ticket follows the same pattern for the equivalent per-object classes, `ObjectTagOrgByTaxonomySerializer`/`ObjectTagOrgView`, in that same `openedx-platform` app. Nothing here touches `openedx_tagging`'s own `ObjectTagsByTaxonomySerializer`/`ObjectTagView` in `openedx-core`.

**\#618 is still in development, not merged.** Checked directly against the live `openedx-platform` code, not assumed: `taxonomy_type`, `get_taxonomy_type`, and `competencytaxonomy` do not appear anywhere in the current `serializers.py`. So today, taxonomy type is not actually returned on the taxonomy endpoints yet either — this ticket depends on \#618 landing first, not on an already-shipped precedent to extend.

The endpoint that returns the tags applied to a specific content object does not return taxonomy type, so the Course Outline page and the Libraries page cannot tell whether a tag on a subsection is a competency or an ordinary tag. That leaves those pages unable to hide the controls that must not be offered for competency tags. \#784 is the frontend work that consumes this.

<details>
<summary>Technical Details</summary>

This section is background and a suggested approach, not the ticket's source of truth. The User Story and Acceptance Criteria define what must be true when the work is done.

### In short

**What this ticket does and does not decide.** The rule for deciding whether a taxonomy is a competency taxonomy is \#618's call to make, not this ticket's, and this ticket does not redecide it, reimplement it, or move it. Once \#618 lands, this ticket follows its `hasattr(taxonomy, "competencytaxonomy")` check, applied to one more `openedx-platform` serializer, the one that returns a content object's tags.

**Why the per-object endpoint is the one that matters.** The Course Outline page and the Libraries page do not fetch the full taxonomy list to render a unit's tags. They fetch the tags applied to that object, and each tag arrives with its taxonomy identified but not typed. Without the type on that payload, the frontend would have to make a second request per taxonomy to decide whether to show a delete control, which is why \#784 cannot be built until this lands.

**Both pages read the same endpoint, confirmed against the frontend code.** Course Outline's tag display and the Libraries pages' tag display both go through the same shared `content-tags-drawer` module in `frontend-app-authoring`: the same `useContentTaxonomyTagsData()` hook, calling the same `api/content_tagging/v1/object_tags/{contentId}/` endpoint. There is one serializer to change, not two.

**The performance shape to watch.** A content object can carry tags from several taxonomies, and a Course Outline request covers many objects at once. Computing the type per tag by fetching its taxonomy would be an N+1 on one of the more heavily used authoring reads. The taxonomies involved must be fetched once for the whole response.

**This is a purely additive change.** The field is added; nothing existing is removed or renamed, so clients that do not know about it are unaffected.

### Implementation specifics

- **Confirm \#618 has landed before starting.** `TaxonomyOrgSerializer.get_taxonomy_type()` doesn't exist yet as of this writing; this ticket has nothing to reuse until it does.  
- **Once \#618 lands, reuse its exact computation rather than duplicating the rule.** `TaxonomyOrgSerializer.get_taxonomy_type()` (`openedx/core/djangoapps/content_tagging/rest_api/v1/serializers.py`) is planned to return `"competency"` if `hasattr(obj, "competencytaxonomy")`, `"tags"` otherwise. Call the same check, or extract it to a shared helper both serializers call, and say in the PR description which you did.  
- **Add the field to ObjectTagOrgByTaxonomySerializer, in that same openedx-platform file, alongside TaxonomyOrgSerializer. This backs ObjectTagOrgView (views.py, same directory), which serves**  (`api/content_tagging/v1/object_tags/{contentId}/`, confirmed the single endpoint both Course Outline and Libraries read). Expose the field on each tag in the response, alongside the taxonomy identity already present.  
- **Do not add anything to `openedx_tagging`'s own `ObjectTagsByTaxonomySerializer`/`ObjectTagView` in `openedx-core`.** `ObjectTagOrgByTaxonomySerializer` already subclasses it; this ticket only adds to the subclass, the same relationship \#618 establishes for the taxonomy endpoints.  
- **Avoid the N+1.** Use `select_related` on the tag's taxonomy (and its `competencytaxonomy` relation, mirroring \#618's planned `TaxonomyOrgView.get_queryset()` change) in `ObjectTagOrgView`'s queryset so the taxonomies come back with the tags, and assert it with a query-count test rather than trusting inspection.  
-   
- **Do not change any other field, and do not change the endpoint's shape.** Additive only.  
- **Tests:** a competency tag reports the competency type; an ordinary tag does not; an object carrying both is distinguishable; an untagged object succeeds; a query-count assertion over an object carrying tags from several taxonomies; a regression assertion that the previously existing fields are unchanged.  
- **Out of scope:** the frontend consumption (\#784), any change to the taxonomy endpoints (\#618’s own scope), and any change to how taxonomy type is decided.

## Files to modify 

| File | Nature of modification |
| :---- | :---- |
| `openedx/core/djangoapps/content_tagging/rest_api/v1/serializers.py` | add `taxonomy_type` to `ObjectTagOrgByTaxonomySerializer`, reusing `TaxonomyOrgSerializer`'s computation once \#618 lands |
| `openedx/core/djangoapps/content_tagging/rest_api/v1/views.py` | add `select_related` on the tag's taxonomy (and its `competencytaxonomy` relation) to `ObjectTagOrgView`'s queryset, to avoid the N+1 |
| the corresponding tests | type-per-tag, mixed-object, empty, query-count, and additive-only regression tests |

## Context

- ADR 0013 (docs/openedx\_tagging/decisions/0013-competency-taxonomy-detection.rst), for the rule this follows and why it must not move into openedx\_tagging.  
- \#618, for the identical pattern planned for the taxonomy endpoints (TaxonomyOrgSerializer/TaxonomyOrgView): entirely in openedx-platform, nothing added to openedx\_tagging or the CBE app. Still in development as of this writing; checked directly against the live code, not assumed.  
- The approved implementation approach on \#655, for why the frontend needs to distinguish competency tags.  
- `frontend-app-authoring`'s `content-tags-drawer/data/api.ts` and `apiHooks.ts`, for the shared hook and endpoint both Course Outline and Libraries read.  
- Consumed by \#784. Depends on \#618.

</details>
