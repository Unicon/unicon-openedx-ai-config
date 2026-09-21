# [ARCH] Plan for scaling Competency Criteria Group associations across recurring course runs

GitHub: https://github.com/openedx/openedx-core/issues/676 (#676, CLOSED)
Cached: 2026-09-21

## Use Case

As an instance operator running Open edX with courses that rerun every term, I want a validated backend design for handling the accumulation of `CompetencyCriteriaGroup` records across course reruns, so that the competency authoring API, and any other consumer of the same data (Studio, Competency Management, future Libraries integration, plugin developers calling the API directly), stays performant as terms accumulate.

## Description

**Current behavior:** No CBE code exists yet; this is greenfield work. Per `docs/openedx_learning/decisions/0002-competency-criteria-model.rst` (Decision 2), a competency's full criteria expression (`CompetencyAchievementCriteria`) is a tree of `CompetencyCriteriaGroup` nodes: one root group plus descendant groups and leaf `CompetencyCriteria` rows, nested up to a frontend-enforced depth of 3 (root, course-scope, leaf/group). A group is scoped to zero courses (`course_id` null) or to exactly one course run (`course_id` is a foreign key to `openedx_catalog_courserun`, a specific run, not a parent course). Because of this nesting, a single course-scoped criteria subtree is not one row: it can already contain multiple `CompetencyCriteriaGroup` rows.

It is intentional design, not an open question, that a course rerun gets its own new `CompetencyCriteriaGroup` rows and child `CompetencyCriteria` rows: these must associate to that specific course run. Every rerun of a course therefore multiplies the number of groups already present for a given competency. A heavily-reused competency, for example a college-wide Gen Ed competency attached to many courses that all rerun every term, can accumulate a large and continuously growing number of groups.

ADR 0002 Decision 2 already commits to: no DB-level row cap on `CompetencyCriteriaGroup` (growth is expected), pagination being available for authoring/list APIs, and evaluation/read paths being windowed by course run dates by default. What is not yet designed is the concrete backend mechanism needed to keep the Studio authoring panel that lists a competency's groups (see companion UX ticket) both performant and usable at this scale.

**Requested change:** This spike's central deliverable is a backend implementation plan that can deliver whatever the companion UX design spike decides the authoring panel needs: windowing, filtering, sorting, pagination, some combination of these, or another mechanism entirely. Concretely:

1. Once the companion UX spike's decision is documented, translate it into a concrete backend design: the query shape, any index changes, and the API contract (parameters and response shape) needed to deliver it. This is the central question this spike exists to answer.
2. Independent of that decision, review whether ADR 0002 Decision 5's proposed indexes (`CompetencyCriteriaGroup(oel_tagging_tag_id, course_id)`, `(parent_id)`) are sufficient for the general "list every group for a competency" access pattern, and document any gaps.
3. Provide a rough order-of-magnitude estimate of how large this can get in the worst case (for example, the Gen Ed scenario), so the design in (1) is checked against a realistic scale, not just the common case.

**Out of scope:**
- Implementing the design. This spike documents the plan; a future ticket implements it.
- Evaluation-time recomputation performance: a separate read path per ADR 0002 Decision 2, already addressed there.
- The authoring panel's own frontend implementation. The companion UX ticket documents the interaction design; building it is a separate, later frontend-app-authoring ticket.
- Load testing or benchmarking against synthetic or production-scale data. Not required by this project's contractual scope.

## Acceptance Criteria

This is a design spike. The deliverable is design artifacts and documented decisions, not working code. There is no Gherkin and no QA path.

- [ ] Document a concrete backend design (query shape, index changes if any, API contract covering parameters and response shape) that delivers the mechanism decided by the companion UX ticket (windowing, filtering, sorting, pagination, or a combination).
- [ ] Review ADR 0002 Decision 5's proposed indexes against the general "list every group for a competency" access pattern; document any gaps.
- [ ] Document a rough order-of-magnitude estimate of worst-case group count (for example, the Gen Ed scenario), stating assumptions.
- [ ] Decide whether the authoring/list endpoint reuses ADR 0002's evaluation-path date-windowing default or needs its own, with rationale.
- [ ] Document the decision, and note whether an ADR 0002 amendment is warranted to record it.
- [ ] Resolve and document every entry in Open Questions below.
- [ ] Do not include load testing, benchmarking, or a proof-of-concept in this spike's scope.

## Open Questions

- **[BLOCKING, depends on companion UX ticket]** What mechanism does the frontend need: windowing, filtering, sorting, pagination, or a combination? Most of this ticket's design work cannot proceed until that decision is documented. (owner: designer, via companion ticket)
- Is an ADR 0002 amendment warranted to record the finalized backend design? (owner: architect)

## Context for the Architect

Most of this spike's substantive design work is gated on the companion UX ticket's decision (see Open Questions, above). The index review and the rough sizing estimate can proceed in parallel; the concrete query/API design cannot be finalized until the UX decision lands.

Existing precedent worth reviewing once that decision is known, not a prescribed solution: `src/openedx_tagging/` already solves a structurally similar problem (a taxonomy with a large number of tags).
- `src/openedx_tagging/rest_api/paginators.py` defines multiple pagination classes tuned to different list sizes (`TaxonomyPagination`, `TagsPagination`, `DisabledTagsPagination`), and `TaxonomyTagsView` (`src/openedx_tagging/rest_api/v1/views.py`, roughly lines 659-880) switches between them at request time based on a caller-supplied size threshold.
- `src/openedx_tagging/api.py`'s in-process functions return lazy, unmaterialized querysets with `select_related` at hot paths, leaving pagination to the REST view layer.
- `docs/openedx_tagging/decisions/0003-tagging-tree-data-arch.rst` addresses a similar tree-scaling question for the tagging model.

Which of these patterns fits, if any, depends entirely on the companion ticket's UX decision. Don't assume a specific technique (caching, for example) is available or the right fit without first confirming it against how this instance of Open edX actually handles comparable problems today.

## Context

- `docs/openedx_learning/decisions/0002-competency-criteria-model.rst` (Decision 2, Decision 5)
- `docs/openedx_learning/decisions/0001-competency-criteria-location.rst` (code location: `src/openedx_learning/applets/cbe`)
- `src/openedx_tagging/rest_api/paginators.py`, `src/openedx_tagging/rest_api/v1/views.py` (`TaxonomyTagsView`) — precedent referenced above
- `docs/openedx_tagging/decisions/0003-tagging-tree-data-arch.rst`
- Companion ticket: UX design spike for the "Demonstrate Mastery For" panel's interaction design. Most of this ticket's design work depends on that ticket's decision. Link the two as a GitHub parent/child issue pair once both are created; this is the parent.
