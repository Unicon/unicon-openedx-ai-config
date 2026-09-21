# [UXD] Interaction design for large numbers of Competency Criteria Groups in the "Demonstrate Mastery For" panel

GitHub: https://github.com/openedx/openedx-core/issues/677 (#677, CLOSED)
Cached: 2026-09-21

## Use Case

As a course author using the "Manage & Apply Competencies" screen in Studio, I want the list of Competency Criteria Groups for a competency to stay navigable when a heavily-reused competency has accumulated many groups across course reruns, so that I can find, review, and edit the groups relevant to my current work without wading through obsolete or unrelated entries.

## Description

**Current behavior:** The original design intent for the right-hand "Demonstrate Mastery For `<competency>`" panel loads every `CompetencyCriteriaGroup` and its child `CompetencyCriteria` for the selected competency, unpaginated and unfiltered. No Figma or code yet reflects a different behavior. It is intentional design for the backend that a course rerun creates its own new `CompetencyCriteriaGroup` rows, scoped to that specific run; for a competency reused across many frequently-rerunning courses (for example, a college-wide Gen Ed competency), the panel could end up rendering a very large, unbounded list.

"Manage & Apply Competencies" exists as its own instance-wide screen, rather than living inside the Course Outline page, because platform administrators are expected to plan and manage a competency taxonomy at an instance-wide, institution-wide, and/or program-wide level, not per course. This matters directly for this spike: **filtering by a single course is unlikely to be a sufficient solution on its own.** Even an author who thinks about competencies at the course level typically has several parallel course runs active at once for that course, so a course-only filter would often still leave a large list. The design should account for this rather than treat "pick one course" as the primary narrowing mechanism.

The longer-term ideal may be filtering by program, or by a construct that groups a course's parallel runs together, since that would match how administrators actually plan competency coverage. Open edX has no program or pathway feature implemented today; a pathways/programs feature is in parallel development but is explicitly not to be merged with CBE work until after this release. This spike cannot design against a feature that does not exist yet, but should avoid foreclosing it: note where a future program/pathway-level filter could slot in, without building toward it now.

**Requested change:** Decide and document how this panel should handle a competency with many groups, altogether: whether through windowing (for example, current/future terms only), filtering, sorting, pagination, some combination of these, or something else. This includes the default view a course author sees, and any controls offered to narrow, sort, or page through the list, while not degrading the common case of a competency with only a few groups. This decision is a prerequisite for most of the companion backend architecture spike's design work: that ticket needs to know what mechanism to build for before it can specify the concrete query, index, and API contract.

**Out of scope:**
- The left-hand competency taxonomy tree's own scaling behavior.
- Backend query, index, or pagination-limit implementation (companion ticket).
- Implementing the chosen design (a future ticket, once both this spike and the companion backend spike close).
- Designing for program- or pathway-level filtering. Open edX has no such feature today; a pathways/programs feature is planned in parallel but out of scope to integrate with until after this release.

## Acceptance Criteria

This is a design spike. The deliverable is design artifacts and documented decisions, not working code. There is no Gherkin and no QA path.

- [ ] Document how the panel should handle a competency with many groups: windowing, filtering, sorting, pagination, a combination of these, or another approach, with rationale for what's included versus deferred.
- [ ] Document the default view a course author sees (for example, term-windowed, recency-sorted, or a full list with pagination), with rationale.
- [ ] If filtering by course run recency is part of the design, document how "past" is defined and whether it's on by default or a candidate the author can toggle, evaluated alongside the other options above, not assumed as a given.
- [ ] Document any filter, search, and/or sort controls offered to the course author, with rationale for what's included versus deferred, and rationale for why a course-only filter is or isn't sufficient given that authors commonly have several parallel course runs active at once.
- [ ] Confirm the chosen design does not degrade the common case: a competency with only a few groups should not require extra clicks or controls to use.
- [ ] Update or note required updates to the relevant Figma file(s) for this screen.
- [ ] Resolve and document every entry in Open Questions below.

## Open Questions

- What should the panel do, altogether, when a competency has many groups: windowing, filtering, sorting, pagination, a combination, or something else? (owner: designer)
- What is the default view a course author sees? (owner: designer)
- Should course runs that are in the past be excluded by default, and if so, by what definition of "past"? Evaluate as one candidate among the options above, not a locked decision. (owner: designer)
- What filter, search, and/or sort controls does the course author actually need? (owner: designer)
- Does the answer differ for a heavily-reused competency versus the common case, or should one consistent pattern cover both? (owner: designer)
- Is a course-level filter worth including at all, given that authors commonly have several parallel runs of the same course active at once and it may not meaningfully narrow the list? (owner: designer)

## Context for the Designer

Current screen: "Manage & Apply Competencies." Left pane: the competency taxonomy tree. Right pane, "Demonstrate Mastery For `<competency>`": a list of Competency Criteria Groups (for example, named after a course, such as "Project Management Fundamentals" or "Introduction to Applied Problem Solving"), each internally combining criteria against course content with AND/OR logic, with groups themselves OR-ed together by default.

Backend precedent for a "small enough, show everything; otherwise force pagination" pattern already exists in this repo's tagging API: `TaxonomyTagsView` (`src/openedx_tagging/rest_api/v1/views.py`) switches pagination behavior based on a caller-supplied size threshold. The frontend component(s) in `frontend-app-authoring` that consume this pattern for tag selection have not been confirmed as part of this spike's prep; locating the actual UI component (if one exists) is a reasonable starting point for this spike's own research, not something to assume without checking.

This spike's output is a documented decision (default view, escape hatches, filter/sort/pagination controls) that the companion backend architecture spike consumes as a required input to its query and API contract design. It is a prerequisite to most of that ticket's work, not just one detail of it.

Keep in mind why this screen is instance-wide rather than course-scoped: administrators plan competency taxonomies at an institution- or program-wide level, so a course-only filter is unlikely to be the answer by itself. A future program/pathway-level filter is a plausible longer-term direction once Open edX has that feature (not yet built, and out of scope to integrate with until after this release); don't design in a way that would make adding such a dimension later awkward, but don't build toward it now either.

## Context

- Companion ticket: backend architecture spike for scaling `CompetencyCriteriaGroup` associations. Most of that ticket's design work depends on this ticket's decision. Link the two as a GitHub parent/child issue pair once both are created; this is the child.
- `docs/openedx_learning/decisions/0002-competency-criteria-model.rst` (Decision 2): the data model background for why group counts grow with course reruns.
- `.claude/frontend-app-authoring-architecture-overview.md`: architecture and conventions for the Studio MFE where this panel lives.
