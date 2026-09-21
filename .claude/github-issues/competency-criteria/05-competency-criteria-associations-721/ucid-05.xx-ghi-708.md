# [UXD Spike] Manage & Apply Competencies: clarify multi-box combining-operator UX and distinguish group levels visually

GitHub: https://github.com/openedx/openedx-core/issues/708 (#708, OPEN)
Cached: 2026-09-21

## Use Case

As a UX designer producing the Figma designs for the Manage & Apply Competencies authoring page, I want to clarify the combining-operator treatment for clusters of Competency Criteria Group boxes and add a visual way to distinguish a leaf box from a course-level grouping of boxes from the overall competency-wide grouping, so that course authors are never shown a UI implying an independent logic choice per adjacent pair of boxes when the real mechanism is one shared choice per cluster, so that they can tell at a glance which boxes are grouped together and at which level, and so that \#671's engineers get an unambiguous, signed-off spec instead of having to guess at the intended behavior.

## Acceptance Criteria

This is a design spike. The deliverable is design artifacts and documented decisions, not working code.

- [ ] Updated Figma frame(s) showing 3+ sibling Competency Criteria Group boxes within a single course, each with its own delete/trash affordance, combined by one shared operator control rather than independently-set per-pair dropdowns.  
- [ ] Updated Figma frame(s) showing 2+ courses' box-clusters combining with each other via one shared operator control at the cross-course tier.  
- [ ] Updated visual treatment for the shared-operator control itself, replacing the current per-pair "Or ▾" connector, at both tiers.  
- [ ] A visual treatment distinguishing a leaf box, a course-level cluster of sibling leaf boxes, and the root-level cluster of course-level clusters, applied consistently across the updated frames above.  
- [ ] A short written note for \#671's implementer translating the finalized frames into unambiguous guidance: which control maps to which tier's shared operator, and how the leaf/course/root visual distinctions map to the underlying group hierarchy.  
- [ ] Sign-off recorded against \#648 (or its successor), consistent with this program's existing design sign-off practice.

## Description

This ticket asks a designer to produce updated Figma frames that clarify how the Manage & Apply Competencies page represents a shared AND/OR combining operator across multiple Competency Criteria Group boxes, and that add a visual treatment distinguishing the leaf, course, and root levels of the group hierarchy, none of which the current designs show today.

**Current behavior**

1. A base competency tree, built by \#680 (out of scope here): nested competency/sub-competency rows with tag codes, e.g. "Critical Thinking" (CCRS-1) containing "Analysis" (CCRS-1.1), "Evaluation" (CCRS-1.2), "Inference" (CCRS-1.3).  
2. Clicking a competency tag opens a right-hand "Demonstrate Mastery For" panel with a "Manage Groups" link and a "+" add-group button top-right, a Competency Criteria Group box below it reading "By Scoring 75% or better within all of the following ▾" with an empty "Selected Content" placeholder, and a course-browse list below that (built by \#670, out of scope here).  
3. Expanding a course in the browse list reveals its sections and gradeable subsections, each with a select affordance (\#670's browse content, out of scope here).  
4. Selecting a subsection associates it into the currently open box, shown as a chip with an X (this select/deselect interaction is \#672's scope, not this spike's).  
5. With two boxes open at once, one per course ("Introduction to Applied Problem Solving" and "Project Management Fundamentals"), a connector between them currently reads "Or ▾", drawn as its own independently-editable dropdown, and nothing distinguishes that these two boxes belong to different courses versus what it would look like if they were siblings within the same course.

**Requested change**

Two related but separate problems need the designer's attention:

**1\. Combining-operator clarity.** The connector in step 5 needs updating: it is drawn as if the operator between any given adjacent pair of boxes is set independently. It is not. Whenever two or more boxes share a combining relationship, whether multiple sibling boxes within the same course or multiple different courses' box-clusters combining with each other, that relationship is a single shared value governing the whole cluster, effectively its own "any/all" choice at the cluster level, the same way the box-internal operator already works at the box level. The designer must produce updated frames that:

- Show 3+ sibling Competency Criteria Group boxes within one course, each with its own delete/trash affordance (clicking "+" always adds another box, default OR), combined by one shared operator control, not N-1 independently-set dropdowns.  
- Show 2+ courses' box-clusters combining with each other via one shared operator control at that tier, same principle.  
- Replace the current "Or ▾" per-pair connector's visual treatment with a control that unambiguously reads as "one choice for this whole cluster."

**2\. Group-level visibility.** Nothing in the current designs lets an author tell, at a glance, whether a set of boxes are siblings within the same course-level grouping, boxes from a different course, or how a given course's grouping relates to the overall competency-wide (root) grouping of all its courses. The designer must produce a visual treatment (e.g. a container, a label, spacing, color, or another Paragon-consistent pattern) that distinguishes these three levels: a leaf box itself, a course-level cluster of one or more sibling leaf boxes, and the root-level cluster of one or more course-level clusters for the competency being viewed.

<details>
<summary>Out of scope</summary>

- Whether a shared operator becomes locked or stays editable under any condition, and any visual treatment for a locked state: covered by \#685/\#655, not this ticket. Do not scope a locking mechanism or its triggers into this spike's deliverables.  
- The filtering bar ("Showing 10 of 208 Courses...", filter icon): a separate, already-in-progress design spike, GitHub issue \#677 (backend \#682, frontend \#683). Do not touch it even though it appears adjacent in the same screenshots.  
- Genuine mixed/varying combining logic within one cluster (some pairs AND, others OR): a distinct, larger future direction, not this spike's job. This spike covers exactly two combining tiers beyond a box's own internal any/all: one shared operator for sibling boxes within one course, one shared operator for different courses' clusters combining. No arbitrary nested/parenthetical grouping UI.  
- \#672's select/deselect-subsection UI, the Selected Content list, and blocked/dominance-conflict indication.  
- \#671's actual implementation: this spike produces the spec \#671 builds against, not code.  
- The box-internal any/all operator itself: already settled and unaffected by this spike.
</details>

<details>
<summary>Open Questions</summary>

- **\[non-blocking, owner: designer\]** What specific visual treatment (container styling, labels, spacing, color, or another Paragon-consistent pattern) should distinguish a leaf box from a course-level cluster from the root-level, all-courses cluster? This is genuinely open design work the spike must resolve and document, not something to decide here.  
- **\[non-blocking, owner: designer\]** Does the course-level and root-level visual treatment need to hold up when a course-level cluster has only one box (no shared operator to show), or is the level-distinction treatment only relevant once 2+ boxes/clusters exist at that tier? Worth confirming so the frames cover the single-box case explicitly rather than leaving it implied.
</details>

<details>
<summary>Context for the Designer</summary>

**Background reading:** two Claude artifacts walk through the group hierarchy (root, course-level, leaf) this spike's visual-distinction work needs to represent, showing both the author-facing view and the underlying backend tree side by side for each scenario:

- [https://claude.ai/code/artifact/80ad382f-bc63-4698-9c39-f2bb127f6bd8](https://claude.ai/code/artifact/80ad382f-bc63-4698-9c39-f2bb127f6bd8) — Scenarios 1-6 are this spike's actual scope (the flat, no-nested-grouping shape). Scenario 7 onward covers a deliberately out-of-scope future direction (arbitrary mixed-logic grouping) — don't design against those.  
- [https://claude.ai/code/artifact/1db1cf33-60c6-40fa-ab9e-f8df723d00ee?via=auto\_preview](https://claude.ai/code/artifact/1db1cf33-60c6-40fa-ab9e-f8df723d00ee?via=auto_preview) — "Option 1" in this artifact is this spike's scope. Options 2-4 cover that same out-of-scope future direction at various depths — don't design against those either.

**Constraints the design must respect:** same two-tier operator scope and the same exclusions as Description → Explicitly out of scope above (exactly two combining tiers beyond the already-settled box-internal operator; no locking mechanism, that's \#685/\#655; no touching the \#677 filtering bar; no genuine mixed-logic clusters). See that section for the full list and rationale; nothing here supersedes it.

**Relationship to other work:** Feeds \#671: its group-creation/removal implementation should not proceed on the multi-box clustering, shared-operator, and level-distinction pieces until this spike's decisions are documented. Extends the parent design \#648. See Description → Explicitly out of scope for the full list of adjacent tickets this spike does not touch.
</details>
