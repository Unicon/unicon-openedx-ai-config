# [Placeholder for UXD] Create UX Design for managing Competency Rule Profiles at Organization, Course, or Taxonomy levels.

GitHub: https://github.com/openedx/openedx-core/issues/645 (#645, OPEN)
Cached: 2026-09-21

**Blocked on:** Team discussion in [this Slack thread](https://openedx.slack.com/archives/C09A1BN1CSE/p1783010480321229?thread_ts=1783010474.048009&cid=C09A1BN1CSE), which raises open questions about the CompetencyRuleProfile data model and permission model — most relevant here: whether the taxonomy scope can be null (affecting how "system default" and org/course-only profiles are filtered and listed), whether a reverse lookup from a profile to the content it governs belongs on this endpoint or a separate one, and the platform-admin/org-staff read/write permission split. Also depends on https://github.com/openedx/openedx-core/issues/613 (CBE core data models) landing first. Write the full ticket immediately after these are resolved and documented.

**Use Case**
As an instance administrator, I want a clear UX for creating, editing, and viewing a Competency Rule Profile at the organization, course, or taxonomy level, so that I can define reusable rule defaults once instead of duplicating rule configuration on every criterion, and so anyone authoring criteria can tell at a glance which level's rule actually applies.

**Description**
Current state: No CompetencyRuleProfile UI exists. The model is defined only in proposal-status ADRs as "a reusable rule definition (rule type plus payload) scoped to an org/course/taxonomy, so criteria can share a profile and override it when needed." This is greenfield: no backend API, no authoring surface, nothing to reference visually.

Requested change: produce UX design artifacts for the three CRUD-ish flows (create, edit, view) of a rule profile at each of the three scope levels, plus a way to show the fallback/precedence order when levels overlap. Out of scope: any backend or frontend implementation, profile versioning, and delete.

**Acceptance Criteria**
This is a design spike. The deliverable is design artifacts and documented decisions, not working code. There is no Gherkin and no QA path.

- [ ] Figma flow: create a rule profile at org, course, and taxonomy scope
- [ ] Figma flow: edit and view an existing profile at each scope
- [ ] Wireframe/annotation showing how precedence is surfaced when an org, course, and taxonomy profile could all apply to the same criterion
- [ ] Each Open Question below resolved and documented with rationale
- [ ] Handoff notes for the dependent frontend implementation ticket

**Open Questions**
- [BLOCKING] Who can manage a profile at each level — instance admin only, or can course authors manage course-level profiles? (Determines permission-gating in the design.) Options: A) admin-only at all levels, B) admin for org/taxonomy, course author for course-level. Recommended: B, matches the existing taxonomy admin/course-author read-only split noted in cbe-project-context.md.
- [non-blocking] Does "managing" include delete, or is this create/edit/view only for now? Recommended: create/edit/view only; deleting a profile that criteria already reference likely needs its own confirmation-flow ticket.
