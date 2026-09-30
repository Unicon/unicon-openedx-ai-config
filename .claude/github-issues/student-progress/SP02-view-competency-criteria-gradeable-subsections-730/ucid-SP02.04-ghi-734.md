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

## UX Design

@illiphilli, please add the UX design screenshot(s) and the Figma link for this ticket.

- Figma: TBD
- Screenshots: TBD

## Acceptance Criteria

These scenarios use the following terms:

- A group is one of the course's bottom-tier groups under a tag. Its group line says whether all or any of the group's subsections are required.
- When every criterion in a group has the same rule, the group line also states that rule's score, for example "COMPLETE ALL OF THE FOLLOWING AT 80% OR BETTER", and the subsections appear directly under the group line.
- When a group's criteria have more than one rule, each rule gets its own rule line under the group line, such as "AT 75% OR BETTER", with the subsections that share that rule under it.
- A subsection hidden from the learner is one that only staff can see, one restricted to a content group the learner isn't in, or one the author has hidden from the course outline.

```gherkin
Scenario: The panel appears above the Grades card in a course with competency criteria
  Given a course with competency criteria on subsections the learner can see
  When the learner opens the course's Progress tab
  Then the competency criteria panel appears in the main column, above the Grades card
  And the panel has no title of its own above its first card or taxonomy heading
  And the Grades card, the grade summary, and the detailed grades table still appear, unchanged

Scenario: A top-level tag with criteria is its own card
  Given the course's only competency criteria are on "Communication", a tag at the top level of its taxonomy
  When the learner opens the course's Progress tab
  Then one card appears, headed "Communication"
  And a target icon appears immediately before the heading
  And Communication's groups and subsections appear directly under the heading
  And no breadcrumb appears above the heading

Scenario: A second-level tag appears in a card headed by its parent
  Given "Analysis", "Evaluation", and "Inference" are children of "Critical Thinking", a top-level tag
  And the course has competency criteria on "Analysis" and "Inference", and none on "Evaluation"
  When the learner opens the course's Progress tab
  Then one card appears, headed "Critical Thinking", with no target icon and no breadcrumb
  And "Analysis" and "Inference" appear inside that card, each with a target icon immediately before its name and its own groups and subsections under it
  And "Evaluation" does not appear

Scenario: A tag two or more levels deep appears under its parent, with the parent's ancestors as a breadcrumb
  Given "Root Cause Analysis" is a child of "Problem Definition", which is a child of "Problem Solving", a top-level tag
  And the course has competency criteria on "Root Cause Analysis"
  When the learner opens the course's Progress tab
  Then a card appears, headed "Problem Definition", with no target icon on the heading
  And "Problem Solving" appears as a breadcrumb above the heading, as plain text rather than a link
  And "Root Cause Analysis" appears inside the card, with a target icon and its groups and subsections under it

Scenario: The breadcrumb lists every ancestor in a six-level taxonomy
  Given a taxonomy six levels deep, with one tag at each level, named "Level 1" at the top through "Level 6" at the bottom
  And the course has competency criteria on "Level 6"
  When the learner opens the course's Progress tab
  Then a card appears, headed "Level 5"
  And the breadcrumb above the heading shows "Level 1", "Level 2", "Level 3", and "Level 4", in that order
  And "Level 6" appears inside the card, with a target icon

Scenario: The course in the Description's example shows three cards
  Given the taxonomy and the course criteria from the Description's example
  When the learner opens the course's Progress tab
  Then exactly three cards appear
  And the "Communication" card has a target icon on its heading and Communication's groups and subsections under it
  And the "Critical Thinking" card contains "Analysis" and "Inference" and does not contain "Evaluation"
  And the "Problem Definition" card has a "Problem Solving" breadcrumb and contains "Root Cause Analysis"

Scenario: One tag can head one card and appear in another card's breadcrumb
  Given "Problem Definition" and "Strategy Selection" are children of "Problem Solving", a top-level tag, and "Root Cause Analysis" is a child of "Problem Definition"
  And the course has competency criteria on "Strategy Selection" and "Root Cause Analysis"
  When the learner opens the course's Progress tab
  Then a card headed "Problem Solving" contains "Strategy Selection"
  And a separate card headed "Problem Definition", with a "Problem Solving" breadcrumb, contains "Root Cause Analysis"

Scenario: A tag whose parent also has criteria appears under the parent's own requirements
  Given "Critical Thinking", a top-level tag, and its child "Analysis" both have criteria in this course, which can happen when a taxonomy is re-imported with a tag moved under a new parent after the criteria were created
  When the learner opens the course's Progress tab
  Then one card appears, headed "Critical Thinking", with a target icon immediately before the heading
  And Critical Thinking's groups and subsections appear directly under the heading, before "Analysis"
  And "Analysis" appears inside the same card, with a target icon and its own groups and subsections under it

Scenario: A tag that heads its own card isn't repeated in its parent's card
  Given "Problem Definition" is a child of "Problem Solving", a top-level tag, and "Root Cause Analysis" is a child of "Problem Definition"
  And both "Problem Definition" and "Root Cause Analysis" have criteria in this course
  And no other child of "Problem Solving" has criteria in this course
  When the learner opens the course's Progress tab
  Then a card headed "Problem Definition" appears, with a target icon before the heading and a "Problem Solving" breadcrumb
  And Problem Definition's groups and subsections appear directly under that heading, before "Root Cause Analysis"
  And Problem Definition's groups and subsections appear nowhere else in the panel
  And no card headed "Problem Solving" appears

Scenario Outline: The group line says whether all or any of the group's subsections are required
  Given a tag with one group in this course, whose criteria all require 80% or better, and that group <setting>
  When the learner opens the course's Progress tab
  Then the group line reads "<text>"

  Examples:
    | setting                                                       | text                                           |
    | requires all of its criteria                                  | COMPLETE ALL OF THE FOLLOWING AT 80% OR BETTER |
    | requires any one of its criteria                              | COMPLETE ANY OF THE FOLLOWING AT 80% OR BETTER |
    | has no combining choice, because it holds a single criterion  | COMPLETE ANY OF THE FOLLOWING AT 80% OR BETTER |

Scenario: A group whose criteria share one rule states it on the group line
  Given a group that requires all of its criteria, on "Quiz 1" and "Quiz 2", each requiring 80% or better, with Quiz 1's threshold coming from a rule profile and Quiz 2's set on the criterion itself
  When the learner opens the course's Progress tab
  Then the group line reads "COMPLETE ALL OF THE FOLLOWING AT 80% OR BETTER"
  And "Quiz 1" and "Quiz 2" appear directly under the group line, with no separate rule line

Scenario: A group whose criteria have more than one rule shows a rule line for each
  Given a group that requires all of its criteria, with "Quiz 1" and "Quiz 2" each requiring 75% or better and "Final Project" requiring 90% or better
  When the learner opens the course's Progress tab
  Then the group line reads "COMPLETE ALL OF THE FOLLOWING", with no score
  And a rule line reading "AT 75% OR BETTER" has "Quiz 1" and "Quiz 2" under it
  And a rule line reading "AT 90% OR BETTER" has "Final Project" under it
  And no AND or OR appears between the two rule lines

Scenario Outline: The rule states the score the subsections require
  Given a group that requires all of its criteria, each of which requires a score <comparison> <threshold>%
  When the learner opens the course's Progress tab
  Then the group line reads "COMPLETE ALL OF THE FOLLOWING <rule>"

  Examples:
    | comparison       | threshold | rule             |
    | at or above      | 82        | AT 82% OR BETTER |
    | at or below      | 40        | AT 40% OR LOWER  |
    | exactly equal to | 100       | AT EXACTLY 100%  |

Scenario: A criterion with a rule the panel doesn't recognize still shows its subsection
  Given a criterion whose rule is not a score at or above, at or below, or exactly equal to a threshold
  When the learner opens the course's Progress tab
  Then its subsection still appears in its group
  And no score is stated for that criterion's rule
  And the unrecognized rule is reported to the site's logging service

Scenario Outline: A tag's groups in this course are joined by AND or OR
  Given a tag with three groups in this course, and the course requires <requirement> of those groups
  When the learner opens the course's Progress tab
  Then "<word>" appears between the first and second groups, and again between the second and third
  And no AND or OR appears before the first group or after the last

  Examples:
    | requirement | word |
    | all         | AND  |
    | any one     | OR   |

Scenario: A tag with one group in this course shows no AND or OR
  Given a tag with exactly one group in this course
  And that competency can also be demonstrated through criteria in other courses
  When the learner opens the course's Progress tab
  Then no AND or OR appears under that tag

Scenario: A course using two taxonomies shows each taxonomy's name above its own cards
  Given a course with competency criteria on tags from "Workplace Skills" and from "Accounting Standards"
  When the learner opens the course's Progress tab
  Then an "Accounting Standards" heading appears first, followed by that taxonomy's cards
  And a "Workplace Skills" heading appears after them, followed by that taxonomy's cards

Scenario: A course using one taxonomy shows no taxonomy heading
  Given a course whose competency criteria all use tags from one taxonomy
  When the learner opens the course's Progress tab
  Then that taxonomy's name does not appear as a heading

Scenario: Tags with the same name in two taxonomies stay separate
  Given two taxonomies that each have a top-level tag named "Communication", and the course has criteria on both
  When the learner opens the course's Progress tab
  Then a "Communication" card appears under each taxonomy's heading
  And each card shows only the groups and subsections of its own taxonomy's tag

Scenario: A taxonomy heading appears only when cards from more than one taxonomy are shown
  Given a course with criteria from two taxonomies
  And every criterion from one of them is on a subsection hidden from the learner
  When the learner opens the course's Progress tab
  Then the other taxonomy's cards appear, with no taxonomy heading

Scenario: Tag and subsection names appear as plain text
  Given a course with competency criteria
  When the learner opens the course's Progress tab
  Then each tag and subsection appears under the name it has in its taxonomy or in the course
  And no tag name, breadcrumb entry, or subsection name is a link

Scenario: Subsection rows can't be expanded
  Given a course with competency criteria
  When the learner opens the course's Progress tab
  Then no subsection row has a chevron or any other control that expands it
  And selecting a subsection row reveals nothing further

Scenario: The panel shows what is required, not the learner's progress
  Given a learner who has already earned scores on some of the subsections that have criteria
  When the learner opens the course's Progress tab
  Then nothing in the panel shows the learner's score, grade, attempts, completion, or mastery status
  And every subsection in the panel looks the same, whether or not the learner has attempted it

Scenario: A course with no competency criteria shows no panel
  Given a course with no competency criteria
  When the learner opens the course's Progress tab
  Then no card, heading, message, or empty space from the panel appears
  And the main column shows the same content it shows on a site without the plugin

Scenario: Nothing from the panel appears while it is loading
  Given a course with competency criteria
  And the criteria or the course's subsection names are still loading
  When the learner opens the course's Progress tab
  Then no card, loading indicator, or placeholder from the panel appears
  And the Grades card and the rest of the Progress tab appear without waiting for the panel

Scenario: The panel stays hidden when the course's criteria can't be loaded
  Given the request for the course's competency criteria fails, for example because the site hasn't deployed that endpoint, the server returns an error, or the request is refused
  When the learner opens the course's Progress tab
  Then nothing from the panel appears, and no error message is shown to the learner
  And the failure is reported to the site's logging service
  And the Grades card and the rest of the Progress tab appear as usual

Scenario: The panel stays hidden when the subsection names can't be loaded
  Given the course's competency criteria load
  And the request for the course outline fails
  When the learner opens the course's Progress tab
  Then nothing from the panel appears, including any criterion without its subsection's name
  And the failure is reported to the site's logging service
  And the Grades card and the rest of the Progress tab appear as usual

Scenario: Criteria on subsections hidden from the learner are left out
  Given a group with criteria on "Quiz 1", which every learner can see, "Instructor Review", which only staff can see, "Group B Project", which is restricted to a content group the learner isn't in, and "Bonus Case Study", which the author has hidden from the course outline
  When the learner opens the course's Progress tab
  Then "Quiz 1" appears in the group
  And "Instructor Review", "Group B Project", and "Bonus Case Study" don't appear anywhere in the panel

Scenario: Anything left empty after those criteria are removed is removed too
  Given "Analysis" and "Inference" are children of "Critical Thinking", and each has criteria in this course
  And every criterion under "Inference" is on a subsection hidden from the learner
  When the learner opens the course's Progress tab
  Then the "Critical Thinking" card shows "Analysis" and doesn't show "Inference"
  And no rule line, group, tag, card, or taxonomy heading appears with nothing under it

Scenario: A removed group leaves no stray AND or OR
  Given a tag with three groups in this course, joined by AND
  And every criterion in the second group is on a subsection hidden from the learner
  When the learner opens the course's Progress tab
  Then the first and third groups appear, with a single AND between them

Scenario: A group left with one rule after hidden criteria are removed states that rule on the group line
  Given a group that requires all of its criteria, with "Quiz 1" requiring 75% or better and "Bonus Case Study", which is hidden from the learner, requiring 90% or better
  When the learner opens the course's Progress tab
  Then the group line reads "COMPLETE ALL OF THE FOLLOWING AT 75% OR BETTER"
  And "Quiz 1" appears directly under the group line
  And "AT 90% OR BETTER" doesn't appear

Scenario: A course whose criteria are all on subsections hidden from the learner shows no panel
  Given a course with competency criteria
  And every criterion is on a subsection hidden from the learner
  When the learner opens the course's Progress tab
  Then no card, heading, message, or empty space from the panel appears

Scenario: Criteria on deleted subsections are left out for everyone
  Given a criterion on a subsection that has since been deleted from the course
  When a learner or a member of course staff opens the course's Progress tab
  Then that criterion doesn't appear, and nothing appears in place of the deleted subsection

Scenario: Criteria on subsections that aren't released yet are shown
  Given a criterion on "Unit 5 Exam", a subsection whose release date is in the future
  When the learner opens the course's Progress tab
  Then "Unit 5 Exam" appears by name in its group

# Depends on the (architect, final review) question about what staff see for subsections hidden from the course outline.
Scenario: Course staff viewing a learner's progress see criteria on subsections visible to staff
  Given a course with criteria on "Quiz 1", which every learner can see, "Instructor Review", which only staff can see, and "Bonus Case Study", which the author has hidden from the course outline
  When a member of course staff opens a specific learner's progress page, for example from the instructor dashboard
  Then the panel appears on that learner's progress page
  And "Quiz 1", "Instructor Review", and "Bonus Case Study" all appear in it

Scenario: Course staff viewing the course as a specific learner see what that learner sees
  Given a course with criteria on "Quiz 1", which every learner can see, "Instructor Review", which only staff can see, and "Group B Project", which is restricted to content group B
  When a member of course staff views the Progress tab as a specific learner who is in content group A
  Then "Quiz 1" appears
  And "Instructor Review" and "Group B Project" don't appear

Scenario: A screen reader user hears the panel in the order it appears on screen
  Given a course with competency criteria
  When a screen reader user moves through the panel
  Then they hear each taxonomy heading, breadcrumb, card heading, tag name, group line, AND or OR, rule line, and subsection name in the order it appears on screen
  And they can jump between card headings and tag names by moving between headings
  And the target icon is either announced with a text alternative or skipped, and is never read out as an unlabeled image

Scenario: The panel reflows on a small screen
  Given a course with competency criteria
  When the learner opens the course's Progress tab at a phone-sized viewport
  Then the cards fill the width of the main column and stack one above another
  And long tag names, breadcrumbs, group lines, rule lines, and subsection names wrap onto more lines instead of being cut off
  And the page doesn't scroll horizontally
```

<details>
<summary>Technical Details</summary>

This is a suggested approach, not the source of truth. The User Story, Description, and Acceptance Criteria define what must be true when the work is done.

**Summary**

The panel makes two requests through a react-query client the plugin owns: #733's criteria for the course and, only when that response has criteria, the learner's course outline from the learning_sequences API, which supplies the subsection names. One pure function joins the two responses, drops criteria on subsections the outline doesn't list, prunes whatever is left empty, and returns the cards grouped by taxonomy. The components render that result from plain props and use no slot or fetching APIs, so frontend-app-learning#1905's move to frontend-base's `Slot` API should only change the registration.

**Approach**

1. **Requests.** `src/data/api.js` has `getCourseCompetencyCriteria(courseId)`, which calls #733's LMS route, and `getCourseOutline(courseId)`, which calls `GET {LMS_BASE_URL}/api/learning_sequences/v1/course_outline/{courseId}`. Both go through `getAuthenticatedHttpClient()`.
   - If #733 takes the course key as a query parameter, pass it through axios `params`, because a literal `+` in a query string decodes as a space.
   - Don't run `camelCaseObject` over the outline response. `outline.sequences` is keyed by usage key, and `camelCaseObject` would rewrite those keys.
2. **Outline source.** The learning_sequences outline fits this panel for four reasons:
   - It keeps unreleased subsections, each with its `effective_start`, so a release-date marker needs no extra request if the UX design adds one.
   - It returns each subsection's plain `title`.
   - For learners, it already removes what they may not know exists: staff-only, `hide_from_toc`, content-group, cohort and enrollment-track restricted, and deleted content. The join therefore needs no visibility logic of its own.
   - It honors masquerade.

   The Course Home Outline API can't be the source. For learners, its `StartDateTransformer` drops subsections that aren't released yet, and it appends "(N Questions)" to graded subsection names.
3. **Query client.** `src/data/queryClient.js` creates one `QueryClient` lazily on first use, so the package entry point still does no work at import time. Configure it with a `QueryCache` whose `onError` calls `logError` from `@edx/frontend-platform/logging`, no retry on a 4xx response, and `refetchOnWindowFocus: false`. Set `staleTime` explicitly; its value is the implementer's choice. Every hook passes this client as `useQuery`'s second argument instead of reading one from React context, because of the host: frontend-app-learning's release/ulmo branch has no react-query and no `QueryClientProvider`, and master's provider logs every failed query itself. Reading the host's client would therefore break on release/ulmo and log every failure twice on master. Passing the client explicitly also lets #839's wrapper share the cache without putting a provider around the host's stock Grades card.
4. **Hooks.** `src/data/apiHooks.js` exports four things:
   - `useCourseCompetencyCriteria(courseId)`.
   - `useCourseOutline(courseId, { enabled })`.
   - `hasCompetencyCriteria(data)`, which is true when #733's criteria array is non-empty.
   - `useCompetencyCards(courseId)`, which runs the transform below inside `useMemo`.

   Enable the outline query only when `hasCompetencyCriteria` is true, so a course without competency criteria costs one request. Leave `targetUserId` out of both query keys, because neither response depends on which learner is being viewed. #839's "in place of" option is out of scope; #839 reuses `useCourseCompetencyCriteria` and `hasCompetencyCriteria`.
5. **Transform.** `buildCompetencyCards(criteriaResponse, outline)` lives in `src/data/buildCompetencyCards.js` and works in six steps:
   1. Walk `outline.sections`, and each section's `sequence_ids`, in order. Index each usage key found in `outline.sequences` with its `title` and its position in the outline.
   2. Drop every criterion whose `object_id` isn't in that index.
   3. The bottom-tier groups are the course-level group's direct children, ordered by `ordering`. In each bottom-tier group, group the criteria into rule boxes by effective rule, the same identity #672 gives rule boxes on the Competency Management page, and order the boxes by their lowest criterion `id`, as #672 does. Order the subsections by outline position. #665 creates only three levels of groups, with the bottom tier as the lowest, so how a deeper tree displays is left to #731 and #732.
   4. Remove empty rule boxes, then empty groups, then competencies with no groups left.
   5. Build the cards from each surviving tag's `lineage`. A top-level tag heads its own card, and any other tag is a row in the card headed by its parent. When a surviving tag is also the parent of another surviving tag, that tag heads the card and gets the target icon: its own groups go under the heading, ahead of the child rows, and it is not also a row in its own parent's card. The breadcrumb is the heading's lineage without the heading. Key cards by taxonomy ID and heading value, which is unique within a taxonomy.
   6. Group the cards into taxonomy sections, ordered by taxonomy name.

   Base every layout decision on what survives pruning, not on #733's raw payload. That covers which tags head cards, whether a group's single rule sits on the group line, whether an AND/OR separator appears, and whether taxonomy headings appear. The test fixtures should cover the Description's example, a tag with criteria alongside its own ancestor, a two-rule group pruned down to one rule, a course whose criteria are all pruned, and two taxonomies where one is pruned away entirely.
6. **Rule text.** `formatRuleText(rule, intl)` in `src/ruleText.js` maps `gte`, `lte`, and `eq` to their messages.
   - Format the threshold with `intl.formatNumber(value, { style: 'percent', maximumFractionDigits: 2 })`, which scales the stored 0.0 to 1.0 fraction and absorbs floating-point error. A hand-rolled `0.29 * 100` gives `28.999999999999996`.
   - For an unknown rule type or `op`, the function returns null, so that line renders without a threshold, and the transform logs the unknown rule once.
   - A bottom-tier group's `logic_operator` reads AND as "all", and OR or null as "any". The course-level group's operator appears between bottom-tier groups, with null read as OR, per ADR 0002.
   - Write the strings in `src/messages.js` in sentence case, and uppercase them with Paragon's `text-uppercase` class, so translators don't receive all-caps source strings.
7. **Components.** `CompetencyProgressPanel` keeps its name and takes no props. It reads `courseId` from `useProgressRouteParams` and calls `useCompetencyCards`. It returns null unless both queries have data and at least one card survives; that single check covers loading, either request failing, and an empty result. `CompetencyCard` and `CriteriaGroupList` take the transform's output as plain props. The transform needs no try/catch, because the slot's error boundary and #829's `SilentErrorFallback` already contain a render-time throw.
8. **Packaging and wiring.** Add `@tanstack/react-query` to `package.json` as a peer dependency at `"*"`, like #810's other peers. The Learning MFE on master reuses its own v5 copy, and npm installs one where the MFE has none. The `competency_progress_panel` registration stays as it is. Remove the `competency_progress_summary` registration from `example.env.config.jsx` and from the Tutor plugin's slot mapping, keeping the two files identical, so learners don't see #829's sidebar placeholder before #743 replaces it.

**Files to create and modify**

Paths are relative to the root of the plugin repository from #810.

| File | Change |
| --- | --- |
| `src/CompetencyProgressPanel.jsx` | modified: the real panel replaces #829's placeholder |
| `src/CompetencyCard.jsx` | new: breadcrumb, heading, heading's own groups, child rows |
| `src/CriteriaGroupList.jsx` | new: bottom-tier groups, separators, rule lines, subsections |
| `src/ruleText.js` | new: `formatRuleText` |
| `src/messages.js` | new |
| `src/data/api.js` | new |
| `src/data/queryClient.js` | new |
| `src/data/apiHooks.js` | new |
| `src/data/buildCompetencyCards.js` | new |
| `package.json` | modified: `@tanstack/react-query` peer dependency |
| `example.env.config.jsx` | modified: sidebar registration removed |
| `tutor-contrib-<repository-name>/<module-name>/plugin.py` | modified: sidebar registration removed |

**Additional context**

- ADR 0002 in openedx-core, `docs/openedx_learning/decisions/0002-competency-criteria-model.rst`, is the source for the Grade rule payload and the `logic_operator` semantics.
- #672 defines how the Competency Management page derives and orders rule boxes. Its code lives in frontend-app-authoring's `src/taxonomy/competency-management/`.
- In openedx-platform, `openedx/core/djangoapps/content/learning_sequences/views.py` (`CourseOutlineView`) defines the outline response, and `openedx/core/djangoapps/content/learning_sequences/api/processors/` defines what a learner's outline leaves out.

</details>

## Open Questions

- (architect, final review) Should the subsection names come from the learning_sequences course outline instead of the Course Home Outline API that the pre-handoff check chose? For learners, the Course Home Outline API removes subsections that aren't released yet, because its `StartDateTransformer` runs before the outline is returned. That breaks the decided rule that criteria on unreleased subsections are shown. The Course Home Outline API also appends a localized "(N Questions)" to graded subsection names. Options:
  - A) Use `/api/learning_sequences/v1/course_outline/{courseId}`, which keeps unreleased subsections, returns plain titles, applies the same learner filtering, and honors masquerade. Recommended, and the Technical Details assume it.
  - B) Keep the Course Home Outline API, and change the requirement so criteria on unreleased subsections stay hidden until release.

  The same premise, that the Course Home Outline API is the source, appears in the notes for #733 and #839, which would need the same correction.
- (architect, final review) Which react-query client does the plugin use? frontend-app-learning's release/ulmo branch has no react-query and no `QueryClientProvider`, so reading the host's client throws there. On master, the host's query cache already logs every failed query. Options:
  - A) A client the plugin owns, passed as `useQuery`'s second argument, which works on both branches. Recommended, and the Technical Details assume it.
  - B) The host's client, with the plugin supporting master and later only.
  - C) A plugin-owned `QueryClientProvider` around the panel, which #839's wrapper would then put around the host's stock Grades card.
- (architect, final review) Should this ticket deal with #829's sidebar placeholder? #829 says this ticket adds the has-criteria check to both of #829's placeholders. The right-hand column is out of scope here, so without a change the sidebar placeholder's throwaway text would show on every course until #743. Options:
  - A) Apply the same has-criteria check to the sidebar placeholder, about a quarter day. Learners in competency courses still see the placeholder text.
  - B) Leave the sidebar placeholder as it is.
  - C) Remove the sidebar registration until #743 re-adds it, about 15 minutes. Recommended, and the Technical Details assume it.
- (architect, final review) What do course staff see for subsections hidden from the course outline? The learning_sequences outline gives staff the unfiltered outline with no hidden flag, so staff see criteria on those subsections, the same way they already see staff-only ones. Learners never receive them. Options:
  - A) Accept this as part of the staff-view behavior already accepted. Recommended, and the staff scenario assumes it.
  - B) For staff only, also fetch the Course Home Outline API to filter on its `hide_from_toc` flag.
- (architect, final review) Please confirm three layout defaults that the BA's draft applied:
  - A group left with one rule after hidden criteria are removed states that rule on its group line.
  - A tag that heads its own card is not repeated as a row in its parent's card, and a parent card left with nothing is not shown.
  - Subsections hidden from the course outline are left out for learners and, under the staff question above, shown to staff.
- (architect, final review) Concerns about the human-written sections:
  - The User Story asks for "a table", while the Description and the AC build cards.
  - The Out of Scope list could add "Expanding a subsection row to show attempts and score feedback", because the Figma's subsection rows expand to show attempts and feedback, which are grade data. It could also add "Rendering the panel in place of the Grades card (#839)".
  - Context could name the blockers #733 and #829, say that this ticket replaces #829's main-column placeholder, and link frontend-app-learning#1905.
  - "To the left of them" in the Description could read "before them", so right-to-left languages are covered.

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

### Decisions from the draft pass (BA)

- Cards and tag rows are not collapsible. In the Figma, each subsection row expands to show attempts and score feedback, which are grade data, so in this ticket subsection rows are plain rows. The ticket that adds grades adds that expander, collapsed by default.
- When every criterion in a group shares one rule, the rule goes on the group line ("COMPLETE ALL OF THE FOLLOWING AT 80% OR BETTER"), as the Figma shows.
- A taxonomy heading appears only when cards from more than one taxonomy are shown after pruning.
- A tag and its ancestor can both have criteria after a taxonomy re-import re-parents a tag (`UpdateParentTag`). The heading tag then carries its own criteria, above its child rows.
- Criteria on subsections hidden from the course outline are left out for learners. No panel title.
- Verified in openedx-platform during the draft pass: the Course Home Outline API intersects its tree with the learner's learning_sequences outline (dropping staff-only and hide_from_toc subsections) and its `StartDateTransformer` drops unreleased subsections for learners. See the first Open Question.

### Suggested comment for @illiphilli after posting

Please confirm: the top-level tag card with the target icon on its heading; the heading tag that has its own criteria above its child rows; the AND/OR separator between groups; the single-rule group line; the layout for a group with more than one rule (group line with no score, then a rule line per rule); "OR BETTER" versus authoring's "or higher"; plain subsection rows with no expander while grades are out of scope; neutral subsection styling while statuses are out of scope; no panel title; breadcrumb content and style; phone-width layout; the target icon's accessible name; whether unreleased subsections get a marker (the learning_sequences outline provides `effective_start`).
