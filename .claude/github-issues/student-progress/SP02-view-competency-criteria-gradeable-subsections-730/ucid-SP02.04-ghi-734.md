# [FE] Build cards displaying Competency Criteria on the Course Progress page

GitHub: https://github.com/openedx/openedx-core/issues/734 (#734, OPEN)
Cached: 2026-09-22

## User Story
As a learner, when I view the Progress tab of my course, I want to see a table of the competencies and subcompetencies that shows which subsections correspond to each competency and what the rule is to demonstrate mastery with these subsections so that I can understand what's required for me to demonstrate mastery.

## Description

This ticket builds the foundation of the CBE course progress page, which goes in the `ProgressTabCourseGradeSlot` above the default Course Grades view.

A course can have its content associated with more than one level of the competency taxonomy hierarchy (#666 only blocks a tag and its own ancestor or descendant in the same course; sibling branches of the competency taxonomy hierarchy can be applied in this course at different levels).

Each card's layout will depend on the level of its tags, based on the following cases:
- If a tag with competency criteria in this course is at the topmost level of its taxonomy, then display a card with that tag's name as the heading and the rules and subsections underneath.
- If a tag with competency criteria in this course is right below the topmost level, then display a card with the tag's parent as the heading and the tag (along with any sibling tags that also have criteria in this course) as a child with the rules and subsections underneath it.
- If that parent is itself below the topmost level, then add a breadcrumb above the card heading with each of the parent's ancestors.

**Example:**
```
Given the following taxonomy and a course with the indicated criteria associations:
- Critical Thinking
    - Analysis (Criteria association here)
    - Evaluation
    - Inference (Criteria association here)
- Communication (Criteria association here)
    - Written Communication
    - Oral Communication
    - Audience Awareness
- Problem Solving
    - Problem Definition
        - Root Cause Analysis (Criteria association here)
    - Strategy Selection
    - Solution Testing
None of these tags is an ancestor or descendant of another, so they can all coexist in this course even though they are at different levels. This course would get three cards:
- A "Communication" card, with Communication's rules and subsections underneath.
- A "Critical Thinking" card, with Analysis and Inference as children. Evaluation isn't shown, because it has no criteria in this course.
- A "Problem Definition" card, with Root Cause Analysis as a child and a "Problem Solving" breadcrumb above the heading.

This course could not also have criteria on Critical Thinking itself, because Critical Thinking is the parent of Analysis and Inference.
```

The tags with competency criteria in this course should have the target icon to the left of them.

Under each of these tags, display this course's bottom-tier groups the way the Competency Management page does: "COMPLETE ANY/ALL OF THE FOLLOWING" per group, then "AT XX% OR BETTER" with the subsections underneath for each set of criteria that share a rule. If there is more than one group, then display an "AND" or "OR" in between them.

If this course uses more than one taxonomy, then display each taxonomy's name as a heading above its cards.

If this course has no CompetencyCriteria (if an empty array comes back from #733's endpoint), then display nothing.

**Out of Scope (will be implemented in future tickets):**
- Sunburst
- Right hand column (`ProgressTabRelatedLinksSlot`)
- Displaying grades in the cards
- Displaying competency statuses in the cards

## Context
- This is the frontend counterpart to #733. 

## Notes for drafting

### From the human

Happy path Figma: https://www.figma.com/design/VqDdtf3NOsUihle6SNS6Kw/-Course-Level----Student-Progress?node-id=983-3817&t=eJLFBvoAFbCnde7b-4

6 deep taxonomy Figma: https://www.figma.com/design/VqDdtf3NOsUihle6SNS6Kw/-Course-Level----Student-Progress?node-id=1089-4395&t=eJLFBvoAFbCnde7b-4

Take note of Adolfo's comment here: https://github.com/openedx/openedx-core/issues/810#issuecomment-5795543382 "The idea is solid, but hold off on any technical details as this work is still blocked by https://github.com/openedx/frontend-app-learning/issues/1905.  In other words, let's wait for Learning's frontend-base conversion to land, first." I don't think we should hold off on the technical details altogether but maybe just try to take into account that we're building a plugin for a repo that will be getting converted to using frontend-base but also take our technical details with more of a grain of salt if it's unclear what the impacts of this will be.

### Decisions from the pre-handoff check

- Tag ancestors: #733 returns each competency tag with its `lineage`, the list of tag values from the top of its taxonomy down to and including the tag itself. #734 reads it by position: the last entry is the tag, the one before it is the card heading, and the rest form the breadcrumb. A tag whose lineage has one entry is top-level and is its own card. No separate tags endpoint is needed.
- Placement: #734 renders the panel above the stock "Grades" card, the default content of `ProgressTabCourseGradeSlot`, as #829 already does. The operator's "in place of" option is a separate follow-up ticket, drafted as a placeholder in `ucid-SP02.09-ghi-pending.md`, and belongs in Out of Scope.
- Size: kept as one ticket, accepting roughly 2.5 to 3 dev-days.
- Subsection data: the slot passes no props, so after #733 returns a non-empty result, the plugin fetches the LMS Course Home Outline API itself (`/api/course_home/outline/{courseId}`) through the app's react-query `QueryClientProvider`, and joins each subsection's usage key and `display_name` to each criterion's `object_id`. The Outline API is used rather than the Progress tab API because the Progress tab's subsection list is filtered per learner and leaves out unreleased subsections, while the Outline API keeps them, by design: the learning_sequences `ScheduleOutlineProcessor` never hides content because of start or due dates (`openedx/core/djangoapps/content/learning_sequences/api/processors/schedule.py:24-27`).
- Staff view: in the Progress tab's view of another learner (`progress/{courseId}/{student_id}`), the Outline API returns the staff member's outline, because it has no route for another learner, so staff may also see criteria on subsections that learner can't know exist (staff-only or another content group's). This is accepted. Masquerading as the learner gives the exact learner view, because the Outline API honors masquerade (`outline/views.py:204`).
- Subsections the learner can't see: #733 returns every stored criterion, unfiltered. Criteria on unreleased subsections are shown, because the Outline API returns their names. #734 drops any criterion whose `object_id` doesn't match a subsection in the Outline API's list, which covers only content the learner isn't allowed to know exists (staff-only or hidden from the table of contents, content-group or cohort restricted, and deleted), then removes anything left empty. Whether an unreleased subsection gets a visual marker (for example its release date or a "not yet released" label) is @illiphilli's call through the UX Design placeholder.
- Mixed depths: #666 blocks only an ancestor/descendant pair in one course. Tags at different depths on different branches of one taxonomy can coexist, for example "Inference" (depth 1) and "Communication" (depth 0). So the layout is decided per card. Each associated tag is a target-icon row in a card headed by its parent, with the parent's ancestors as a breadcrumb. An associated tag with no parent is its own card, and its heading gets the target icon. The Description's three depth cases are outcomes of this rule.
- Rule display mirrors the Competency Management page: each bottom-tier group shows "COMPLETE ALL/ANY OF THE FOLLOWING", then one line per rule box (criteria sharing one effective rule) with its threshold and its subsections underneath. The course-level group's operator is shown as AND or OR between bottom-tier groups. The root group's operator is never shown. Authoring's copy reads "75% or higher" while the Progress Figma reads "OR BETTER", so @illiphilli confirms the copy.
- Rule text: gte reads "AT XX% OR BETTER", lte reads "AT XX% OR LOWER", eq reads "AT EXACTLY XX%". Thresholds are shown as stored (for example 82%). An unknown rule type shows the line without a threshold and is logged. Confirmed: the authoring API accepts all three operators, and Grade is the only rule type.
- Operator mapping: a bottom-tier group's `logic_operator` AND reads ALL, OR reads ANY, and null reads ANY.
- Unhappy paths: while loading, and on any fetch failure (including a 404 when #733's route isn't deployed), render nothing and log the error. The fetch catches its own errors. Empty rule boxes, then empty groups, competencies and cards are removed; if nothing is left, render nothing. In staff view, the panel renders for the learner being viewed.
- Multiple taxonomies: taxonomies are ordered by name, each with a taxonomy heading above its cards.
- A parent card lists only the child tags that have criteria in this course.
- The breadcrumb shows every ancestor as plain text, not links. There are at most 4, because taxonomies cap at 6 levels.
- Subsection names are plain text, not links.
- i18n: the plugin's own fixed strings (rule text, AND/OR labels) use `@edx/frontend-platform/i18n` messages, with the translation pipeline in a later ticket. Tag values and subsection names display exactly as the backend returns them.
- Figma gaps (the top-level case, the AND/OR separator, rule boxes, neutral pill styling while statuses are out of scope, breadcrumb content, mobile width): the BA drafts the AC with the defaults above, and @illiphilli confirms or corrects them through the UX Design placeholder.
- frontend-base: frontend-app-learning#1905 is open and blocked on #1946. It moves all plugin slots to frontend-base's `Slot` API with no promise that slot IDs are kept. Technical Details should hold the slot wiring loosely, per the note above.
- Implementer-owned: ordering within a card (taxonomy tree order by lineage, bottom-tier groups by `ordering`, subsections in course outline order), the Paragon icon for the target, and heading levels.

### Known scope, decided while drafting SP02.06/07/08

Not yet drafted as a real ticket. These are commitments made while scoping the plugin starter tickets that land here when #734 is actually written:

- Replaces the `CompetencyProgressPanel` placeholder (from SP02.08) with the real collapsible competency criteria table, in the main-column Progress tab slot.
- Owns gating: calls #733's endpoint to decide whether the course has competency criteria, and renders nothing when it does not. That check runs on every Progress tab render for every course on the site, including the large majority with no competency data, so #733 should be specified knowing it has this consumer (candidates: the criteria response itself doubles as the answer, or the Progress tab's existing course metadata carries a boolean, cheaper on the hot path but needs an `openedx-platform` change).
- Owns the operator's placement choice: render the panel above the stock Grade Summary card (the only option SP02.08 ships) or in place of it. "In place of" needs `PLUGIN_OPERATIONS.Wrap` on `default_contents` with a wrapper that renders the stock card only in non-competency courses, confirmed feasible against the Frontend Plugin Framework source. Extends SP02.07's Tutor plugin registration, already written as a data-driven mapping for exactly this, rather than rewriting it.
- Whoever adds the gating fetch must catch its own failures and report them explicitly; a React error boundary does not catch errors thrown from async callbacks.
- Sizing flag from the architect's review: the table, the gate, and the operator placement choice together read as more than a 1-2 day ticket. Worth splitting when this is actually scoped.

Depends on #733, SP02.07, and SP02.08.
