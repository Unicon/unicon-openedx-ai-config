# [BE] Add Competency hierarchy dominance validation to Competency Criteria Creation

GitHub: https://github.com/openedx/openedx-core/issues/666 (#666, OPEN)
Cached: 2026-09-21

The stub listed three business rules paraphrased from the Confluence "Competency Criteria Technical Design Document." That [TD document](https://openedx.atlassian.net/wiki/x/AQAPTgE) predates \#665's narrowing to subsection-only associations. Resolved:

- **"No overlap in containment paths" — dropped entirely.** It described a competency being double-counted across nested LMS content levels (its own worked example used course→subsection→unit codes). \#665 now only ever accepts a subsection `object_id`, so there's no second level left to overlap with. A same-`(group, object_id)` duplicate check isn't a valid substitute either: `CompetencyCriterion.rule_type_override`/`rule_payload_override` can legitimately differ per leaf (ADR 0002 Decision 4), so two rows sharing a group and object aren't self-evidently invalid. If a future ticket adds course-level criteria, this rule may need to be revisited then — not owned here.  
- **"Parent competencies dominate scope" — this ticket's actual scope.** "Parent"/"children" means competency **tags** in the taxonomy hierarchy (sub-competencies), not a `CompetencyCriteriaGroup` node. Scope is same-course only (\#664 already established one `CompetencyCriteriaGroup` tree covers exactly one tag, so a same-*group* violation is structurally impossible). Full ancestor/descendant chain is blocked; siblings are allowed.  
- **"Groups and courses are isolation boundaries" — assumed purely descriptive for now**, summarizing the scope of the rule above rather than adding independent logic. No separate implementation here. Revisit if evidence surfaces that it means something more.

**Blocked by:** \#613 (the CBE data model) and \#665 — this ticket implements the `_validate_containment(group, object_id)` seam \#665 already reserves and calls, but does not implement.

Repo: `openedx-core`, single-repo. No `openedx-platform` changes — pure validation logic inside `create_competency_criterion()`.

## Use Case

As a Platform Administrator authoring Competency Criteria, I want the system to reject a new Competency Criterion whose competency tag is a taxonomy ancestor or descendant of another tag that already has a criterion in the same course, so that the (future) evaluation pipeline never has to reconcile two independently-authored, overlapping mastery rules for hierarchically related competencies in one course, where there is no defined precedence for whether the parent's own criterion or a rollup from the child's should govern.

## Description

**Current state**

\#665 creates a `CompetencyCriterion` with only baseline referential-integrity checks (group exists, group/competency match, group/course match, `object_id` parses as a subsection `UsageKey`). It exposes `_validate_containment(group, object_id)` as an insertion point but does not call it. Nothing today stops two hierarchically related competency tags from each independently accumulating criteria in the same course.

**Requested change**

Before a `CompetencyCriterion` is created, resolve the group's competency tag's full ancestor chain and full descendant subtree in the taxonomy. If any tag in that ancestor-or-descendant set already has an existing `CompetencyCriterion` whose subsection resolves to the same course as this new criterion's subsection, reject with 400\. Sibling tags (sharing a common ancestor, neither ancestor nor descendant of each other) may coexist in the same course without restriction, and the same tag may have any number of criteria in the same course — this is normal per ADR 0002's own worked example (lines 336-349), where one tag has criteria in two different groups.

**The course-lookup this validation needs must be built as a public, shared function, not inlined into the check.** A separate, sibling ticket (not yet numbered — see Context) adds a read-only endpoint that answers a related but distinct question proactively: given a competency, which courses are already blocked for it, so the authoring frontend can gray out ineligible content before an author attempts an invalid association. That endpoint needs the exact same "given a set of relative tag ids, find every course that already has a criterion under one of them" logic this ticket already has to build for its own write-time check — just returning the whole result set instead of stopping at the first match. Building it as a private, inline step here would mean a second ticket has to reach back into this one's already-merged code to extract it later; building it as a public function now means both tickets share one implementation from the start, and the read (a gray-out hint) and the write (this ticket's actual enforcement) can never disagree.

**Explicitly out of scope**

- Rule 1 ("no overlap in containment paths") — dropped entirely. It described a competency being double-counted across nested LMS content levels (its own worked example used course→subsection→unit codes). \#665 now only ever accepts a subsection `object_id`, so there's no second level left to overlap with. A same-`(group, object_id)` duplicate check isn't a valid substitute either: `CompetencyCriterion.rule_type_override`/`rule_payload_override` can legitimately differ per leaf (ADR 0002 Decision 4), so two rows sharing a group and object aren't self-evidently invalid. If a future ticket adds course-level criteria, this rule may need to be revisited then — not owned here.  
- Rule 3 ("groups and courses are isolation boundaries") — assumed descriptive, no implementation, see the note above.  
- Reassessing or reindexing existing criteria retroactively when a taxonomy's parent/child structure changes after criteria already exist. This ticket validates only at criterion-creation time.  
- Course-level and unit-level `object_id` (already out of scope per \#665).  
- The read-only "which courses are blocked" endpoint itself — that's the sibling ticket, which only consumes the shared function this ticket builds.

## Acceptance Criteria

These scenarios are verifiable via Postman.

```
Scenario: Reject associating a descendant tag when its ancestor already has a criterion in the same course
  Given a CompetencyCriterion already exists associating tag "Critical Thinking" with a subsection in Course X
  When a POST request creates a criterion associating tag "Inference" (a descendant of "Critical Thinking") with a different subsection in Course X
  Then the response returns status code 400
  And the response body identifies the conflicting tag and Course X

Scenario: Reject associating an ancestor tag when a descendant already has a criterion in the same course
  Given a CompetencyCriterion already exists associating tag "Inference" with a subsection in Course X
  When a POST request creates a criterion associating tag "Critical Thinking" (an ancestor of "Inference") with a different subsection in Course X
  Then the response returns status code 400
  And the response body identifies the conflicting tag and Course X

Scenario: Reject across a multi-level chain, not just immediate parent/child
  Given "Cognitive Skills" is the parent of "Critical Thinking", which is the parent of "Inference"
  And a CompetencyCriterion already exists associating tag "Cognitive Skills" with a subsection in Course X
  When a POST request creates a criterion associating tag "Inference" with a different subsection in Course X
  Then the response returns status code 400
  And the response body identifies "Cognitive Skills" as the conflicting tag

Scenario: Allow sibling tags in the same course
  Given tags "Inference" and "Analysis" share the same parent tag and are neither ancestor nor descendant of each other
  And a CompetencyCriterion already exists associating "Inference" with a subsection in Course X
  When a POST request creates a criterion associating "Analysis" with a subsection in Course X
  Then the response returns status code 201

Scenario: Allow hierarchically related tags when scoped to different courses
  Given a CompetencyCriterion already exists associating tag "Critical Thinking" with a subsection in Course X
  When a POST request creates a criterion associating its descendant tag "Inference" with a subsection in Course Y
  Then the response returns status code 201

Scenario: Allow the same tag to have multiple criteria in the same course
  Given a CompetencyCriterion already exists associating tag "Inference" with a subsection in Course X
  When a POST request creates another criterion associating the same tag "Inference" with a different subsection in Course X
  Then the response returns status code 201
```

<details>
<summary>Open Questions</summary>

- **\[non-blocking, owner: implementer\]** \#665's own course-mismatch check must raise something the view layer maps to 400\. This ticket should raise the same exception type/shape rather than introducing a second error convention — confirm what \#665 actually lands on before implementing.  
- **\[non-blocking, owner: architect/reviewer\]** This ticket adds `get_ancestor_tags`/`get_descendant_tags` to `openedx_tagging/api.py`, a stable public-API surface other consumers rely on. Purely additive, no DEPR needed, but worth a naming/shape review before merge. The same review should cover the new `get_courses_with_relative_criteria` function below, since it's now also a public surface a sibling ticket depends on.

</details>
<details>
<summary>Context</summary>

- \#665: the creation endpoint this ticket attaches to, via the reserved `_validate_containment(group, object_id)` seam; also establishes the `UsageKey`/`.course_key` course-resolution pattern this ticket reuses rather than trusting `CompetencyCriteriaGroup.course_id` (which can be null even for a course-bound criterion — ADR 0002 Decision 2 scopes it to evaluation windowing, not rule assignment).  
- **Companion ticket, `openedx-core` (not yet numbered):** a read-only endpoint, `GET /cbe/rest_api/v1/competencies/<tag_id>/blocked-courses/`, that answers "which courses are blocked for this competency" proactively, so the authoring frontend can gray out ineligible content before an author attempts an association this ticket would reject. It depends entirely on this ticket's `get_courses_with_relative_criteria` function being public (see Description above) — no other new logic. This ticket needs no further change once that lands; the dependency runs one way.  
- ADR 0002 (`docs/openedx_learning/decisions/0002-competency-criteria-model.rst:68-113` Decision 2, `:146-181` Decision 4, `:314-349` worked example): the model this validation reads, and the precedent that one tag having criteria in multiple groups is intentional, not a duplicate to reject.  
- `src/openedx_tagging/models/base.py:34-91` (`Tag`: `parent`, `depth`, `lineage`, `TAXONOMY_MAX_DEPTH = 5`) and `:163-174` (`descendant_count`, the existing lineage-prefix pattern this ticket's descendant lookup mirrors); `:146-152` (`get_lineage`, the ancestor-values source).  
- `src/openedx_tagging/api.py:97-154` (`get_tags`, `get_root_tags`, `get_children_tags`): naming/shape precedent for the two new functions this ticket adds.  
- Source of the three original rules: [Confluence "Competency Criteria Technical Design Document,"](https://openedx.atlassian.net/wiki/x/AQAPTgE) "Business Rules and Evaluation Logic → Authoring-Time Validation and Permission Constraints" — predates \#665's subsection-only scope narrowing, per the stakeholder.
</details>
<details>
<summary>Technical Notes</summary>

### Files to Create

None.

### Files to Modify

| File | Nature of modification |
| :---- | :---- |
| `src/openedx_tagging/api.py` | add `get_ancestor_tags(tag)`, `get_descendant_tags(tag)` |
| `tests/openedx_tagging/test_api.py` | unit tests for the two new functions (ancestor chain, descendant subtree, empty/root cases) |
| `src/openedx_learning/applets/cbe/api.py` | add the public `get_courses_with_relative_criteria(tag_ids)` function; implement `_validate_containment(group, parsed_key)` on top of it; wire the call into `create_competency_criterion()` at the reserved insertion point |
| `src/openedx_learning/applets/cbe/rest_api/v1/tests/test_views.py` (or a sibling `test_api.py`, whichever \#665 lands) | unit tests for the dominance rule plus one integration 400 case, plus unit tests for `get_courses_with_relative_criteria` in isolation (single match, multiple matches across different relative tags, empty set) |

### Implementation Notes

**Data Structures**

```
# src/openedx_tagging/api.py — additive, non-breaking
def get_ancestor_tags(tag: Tag) -> QuerySet[Tag]:
    """Ancestor Tags of `tag` (parent up to root), excluding `tag` itself.
    Resolved from `tag.lineage` in one query; no recursion."""

def get_descendant_tags(tag: Tag) -> QuerySet[Tag]:
    """All descendant Tags of `tag` at any depth, excluding `tag` itself.
    Same lineage-prefix mechanism as Tag.descendant_count."""

# src/openedx_learning/applets/cbe/api.py
def get_courses_with_relative_criteria(tag_ids: Iterable[int]) -> dict[CourseKey, int]:
    """Public. For a set of tag ids, find every CompetencyCriterion attached to any of
    them, resolve each one's course by parsing its ObjectTag.object_id as a UsageKey
    (not CompetencyCriteriaGroup.course_id, which can be null — see #665's own course-
    resolution precedent), and return a mapping of course key to a conflicting tag id.
    Deterministic tie-break, mandatory not cosmetic (an unordered iteration here repeats
    the same footgun already caught in #773's pagination work): iterate tag_ids sorted
    ascending, and for a course claimed by more than one relative tag, keep the first
    (lowest id) one found. Shared by this ticket's own _validate_containment (below) and
    by the sibling blocked-courses endpoint, so the read and the write can never
    disagree about which courses are affected, or about which tag is named as the
    conflict for a course two relatives both claim."""

def _validate_containment(group: CompetencyCriteriaGroup, parsed_key: UsageKey) -> None:
    """Rejects associating group's competency tag with parsed_key's course if any
    ancestor or descendant of that tag already has a CompetencyCriterion resolving
    to the same course. Raises on violation; returns None otherwise. Implemented as a
    thin wrapper: build relative_ids (see Logic), call get_courses_with_relative_criteria,
    and raise if parsed_key.course_key is a key in the result."""
```

**Logic**

1. `_validate_containment` is the insertion point \#665 already reserved before its create step. Call it with the already-parsed `UsageKey` from \#665's own parsing step — do not re-parse.  
2. Resolve `tag = group.oel_tagging_tag`. Build `relative_ids = ancestor ids ∪ descendant ids` via the two new tagging functions above. If empty, return (nothing to conflict with).  
3. Call `get_courses_with_relative_criteria(relative_ids)`. This function does the work previously described as inline steps: find candidate groups (`CompetencyCriteriaGroup.objects.filter(oel_tagging_tag_id__in=relative_ids)`, not pre-filtered by `course_id` for correctness since it can be null — an optional narrowing pre-filter only, never a substitute for the per-criterion course resolution below), load their `CompetencyCriterion` rows joined to `ObjectTag`, and for each, parse `object_id` as a `UsageKey` (skip defensively if it doesn't parse — `ObjectTag.object_id` is polymorphic in general, even though this endpoint only ever writes one) and record `.course_key` against the tag id that produced it.  
4. `_validate_containment` checks whether `parsed_key.course_key` is a key in the returned mapping; if so, raise, naming the conflicting tag (the mapping's value) and course. No match → return normally. Siblings never appear in `relative_ids`, so they can't trigger this.  
5. Not built here: Rule 1 (dropped) and Rule 3 (assumed descriptive). Do not add a same-`(group, object_id)` duplicate check.

Public-API impact: purely additive functions on `openedx_tagging.api` and `openedx_learning.applets.cbe.api`; no signature change to `create_competency_criterion()` (\#665 already reserved the seam). `get_courses_with_relative_criteria` is a new public surface a sibling ticket depends on — treat its naming and return shape (a `dict[CourseKey, int]`, not a bare set) as part of this ticket's contract, not an implementation detail, since changing it later means changing two tickets instead of one. No migration, no PII surface — this is validation logic over existing fields only.

### Example Resolution Prompt

Implement ticket \#666 against \#665's landed `create_competency_criterion()` in `src/openedx_learning/applets/cbe/api.py`. Add `get_courses_with_relative_criteria(tag_ids: Iterable[int]) -> dict[CourseKey, int]` as a public function: given a set of tag ids, find `CompetencyCriteriaGroup` rows whose `oel_tagging_tag_id` is in that set, load their `CompetencyCriterion` rows with the related `ObjectTag`, parse each `object_id` as a `UsageKey` (skip ones that don't parse) and compare `.course_key`, returning a mapping of every course key found to the first tag id from `tag_ids` associated with it.

Add `_validate_containment(group: CompetencyCriteriaGroup, parsed_key: UsageKey) -> None` as a thin wrapper and call it at the reserved insertion point before the `CompetencyCriterion` row is created. It must: resolve `tag = group.oel_tagging_tag`; fetch that tag's ancestors and descendants via two new functions you add to `src/openedx_tagging/api.py` (`get_ancestor_tags(tag)` using `tag.get_lineage()[:-1]` then `Tag.objects.filter(taxonomy_id=tag.taxonomy_id, value__in=ancestor_values)`, and `get_descendant_tags(tag)` using `Tag.objects.filter(taxonomy_id=tag.taxonomy_id, depth__gt=tag.depth, lineage__startswith=tag.lineage)`, mirroring the existing `Tag.descendant_count` property at `src/openedx_tagging/models/base.py:163-174`); collect the union of those tag ids; call `get_courses_with_relative_criteria` with that set; raise (reuse whatever exception class \#665's own course-mismatch check raises, so both surface as 400 the same way) if `parsed_key.course_key` is a key in the result, naming the conflicting tag and course in the message.

Do not implement a same-`(group, object_id)` duplicate check (Rule 1, dropped) or any cross-group/cross-course isolation check (Rule 3, assumed descriptive) — both are explicitly out of scope. Add unit tests to `tests/openedx_tagging/test_api.py` for the two new tagging functions (ancestor chain, descendant subtree, empty/root cases), unit tests for `get_courses_with_relative_criteria` in isolation (single match, multiple matches across different relative tags, empty set), and unit tests for `_validate_containment` (ancestor conflict rejected, descendant conflict rejected, sibling allowed, same tag different course allowed, no-relatives happy path), plus one integration test proving `create_competency_criterion()` now surfaces the 400\.

</details>
