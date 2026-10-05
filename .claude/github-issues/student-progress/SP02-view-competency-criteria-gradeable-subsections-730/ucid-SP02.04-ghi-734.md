# [FE] Build cards displaying Competency Criteria on the Course Progress page

GitHub: https://github.com/openedx/openedx-core/issues/734 (#734, OPEN)
Cached: 2026-09-22

## User Story
As a learner, when I view the Progress tab of my course, I want to see cards of the competencies and subcompetencies that show which subsections correspond to each competency and what the rule is to demonstrate mastery with these subsections so that I can understand what's required for me to demonstrate mastery.

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

Note that this course could not also have criteria on Critical Thinking itself, because Critical Thinking is the parent of Analysis and Inference.
```

The tags with competency criteria in this course should have the target icon before them.

Under each of these tags, display this course's bottom-tier groups the way the Competency Management page does: "COMPLETE ANY/ALL OF THE FOLLOWING" per group, then "AT XX% OR BETTER" with the subsections underneath for each set of criteria that share a rule. If there is more than one group, then display an "AND" or "OR" in between them.

Display each taxonomy's name as a heading above its cards.

Because transparency to students is a critical tenet of CBE, subsections the learner can't see still appear, as a placeholder row such as "1 more subsection that isn't visible to you", so the learner knows they count.

If this course has no CompetencyCriteria (if an empty array comes back from #733's endpoint), then display nothing.

**Out of Scope (will be implemented in future tickets):**
- Sunburst
- Right hand column (`ProgressTabRelatedLinksSlot`)
- Displaying grades in the cards
- Displaying competency statuses in the cards
- Expanding a subsection row to show attempts and score feedback
- Rendering the panel in place of the Grades card (#839)

## Context
- This is the frontend counterpart to #733. 
- Blocked by #733 and #829.
- [frontend-app-learning#1905](https://github.com/openedx/frontend-app-learning/issues/1905) will move the Learning MFE's plugin slots to frontend-base's `Slot` API, which may change how this plugin registers.

## UX Design

@illiphilli, please add the UX design screenshot(s) and the Figma link for this ticket.

- Figma (happy path): https://www.figma.com/design/VqDdtf3NOsUihle6SNS6Kw/-Course-Level----Student-Progress?node-id=983-3817&t=eJLFBvoAFbCnde7b-4
- Figma (six-level taxonomy): https://www.figma.com/design/VqDdtf3NOsUihle6SNS6Kw/-Course-Level----Student-Progress?node-id=1089-4395&t=eJLFBvoAFbCnde7b-4
- Screenshots: TBD

## Acceptance Criteria

These scenarios use the following terms:

- A group is one of the course's bottom-tier groups under a tag. Its group line says whether all or any of the group's subsections are required.
- When every criterion in a group has the same rule, the group line also states that rule's score, for example "COMPLETE ALL OF THE FOLLOWING AT 80% OR BETTER", and the subsections appear directly under the group line.
- When a group's criteria have more than one rule, each rule gets its own rule line under the group line, such as "AT 75% OR BETTER", with the subsections that share that rule under it.
- A subsection hidden from the learner is one that isn't in the learner's course outline: one that only staff can see, one restricted to a content group the learner isn't in, one the author has hidden from the course outline, or one deleted from the course.
- A placeholder row stands in for the subsections under one rule that are hidden from the viewer. It reads "1 more subsection that isn't visible to you", or "N more subsections that aren't visible to you" when there is more than one, and it comes after that rule's named subsections.

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

Scenario: A course using one taxonomy still shows that taxonomy's heading
  Given a course whose competency criteria all use tags from "Workplace Skills"
  When the learner opens the course's Progress tab
  Then a "Workplace Skills" heading appears above that taxonomy's cards

Scenario: Tags with the same name in two taxonomies stay separate
  Given two taxonomies that each have a top-level tag named "Communication", and the course has criteria on both
  When the learner opens the course's Progress tab
  Then a "Communication" card appears under each taxonomy's heading
  And each card shows only the groups and subsections of its own taxonomy's tag

Scenario: Tag and subsection names appear as plain text
  Given a course with competency criteria
  When the learner opens the course's Progress tab
  Then each tag and subsection appears under the name it has in its taxonomy or in the course
  And no tag name, breadcrumb entry, or subsection name is a link

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

Scenario: Subsections hidden from the learner appear as a placeholder row
  Given a group that requires all of its criteria, each requiring 80% or better, on "Quiz 1", which every learner can see, "Instructor Review", which only staff can see, "Group B Project", which is restricted to a content group the learner isn't in, and "Bonus Case Study", which the author has hidden from the course outline
  When the learner opens the course's Progress tab
  Then "Quiz 1" appears by name in the group
  And a placeholder row reading "3 more subsections that aren't visible to you" appears after it, in the same group
  And "Instructor Review", "Group B Project", and "Bonus Case Study" don't appear by name anywhere in the panel

Scenario: A hidden subsection keeps its rule line
  Given a group that requires all of its criteria, with "Quiz 1" requiring 75% or better and "Bonus Case Study", which is hidden from the learner, requiring 90% or better
  When the learner opens the course's Progress tab
  Then the group line reads "COMPLETE ALL OF THE FOLLOWING", with no score
  And a rule line reading "AT 75% OR BETTER" has "Quiz 1" under it
  And a rule line reading "AT 90% OR BETTER" has a placeholder row reading "1 more subsection that isn't visible to you" under it

Scenario: A group whose subsections are all hidden keeps its place
  Given a tag with three groups in this course, joined by AND
  And every criterion in the second group is on a subsection hidden from the learner
  When the learner opens the course's Progress tab
  Then all three groups appear, with AND between the first and second and between the second and third
  And the second group shows its group line with only a placeholder row under it

Scenario: A tag whose subsections are all hidden still appears
  Given "Analysis" and "Inference" are children of "Critical Thinking", and each has criteria in this course
  And every criterion under "Inference" is on a subsection hidden from the learner
  When the learner opens the course's Progress tab
  Then the "Critical Thinking" card shows "Analysis" with its named subsections
  And the card shows "Inference" with its groups and rule lines, each with only a placeholder row under it

Scenario: A course whose subsections are all hidden still shows the panel
  Given a course with competency criteria
  And every criterion is on a subsection hidden from the learner
  When the learner opens the course's Progress tab
  Then the panel appears with its taxonomy headings, cards, tags, group lines, and rule lines
  And every subsection row in it is a placeholder row

Scenario: A deleted subsection appears as a placeholder row for everyone
  Given a criterion on a subsection that has since been deleted from the course
  When a learner or a member of course staff opens the course's Progress tab
  Then a placeholder row reading "1 more subsection that isn't visible to you" appears in that criterion's place

Scenario: Criteria on subsections that aren't released yet are shown
  Given a criterion on "Unit 5 Exam", a subsection whose release date is in the future
  When the learner opens the course's Progress tab
  Then "Unit 5 Exam" appears by name in its group

Scenario: Course staff viewing a learner's progress see criteria on subsections visible to staff
  Given a course with criteria on "Quiz 1", which every learner can see, "Instructor Review", which only staff can see, "Group B Project", which is restricted to content group B, and "Bonus Case Study", which the author has hidden from the course outline
  When a member of course staff opens a specific learner's progress page, for example from the instructor dashboard
  Then the panel appears on that learner's progress page
  And "Quiz 1", "Instructor Review", "Group B Project", and "Bonus Case Study" all appear by name, with no placeholder row

Scenario: Course staff viewing the course as a specific learner see what that learner sees
  Given a course with criteria on "Quiz 1", which every learner can see, "Instructor Review", which only staff can see, and "Group B Project", which is restricted to content group B
  When a member of course staff views the Progress tab as a specific learner who is in content group A
  Then "Quiz 1" appears by name
  And a placeholder row reading "2 more subsections that aren't visible to you" appears in place of "Instructor Review" and "Group B Project"

Scenario: A screen reader user hears the panel in the order it appears on screen
  Given a course with competency criteria
  When a screen reader user moves through the panel
  Then they hear each taxonomy heading, breadcrumb, card heading, tag name, group line, AND or OR, rule line, subsection name, and placeholder row in the order it appears on screen
  And they can jump between card headings and tag names by moving between headings
  And the target icon is announced with a text alternative

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

The panel makes two requests through a react-query client the plugin owns: #733's criteria for the course and, only when that response has criteria, the learner's course outline from the learning_sequences API, which supplies the subsection names. One pure function joins the two responses, counts criteria on subsections the outline doesn't list into placeholder rows, and returns the cards grouped by taxonomy. The components render that result from plain props and use no slot or fetching APIs, so frontend-app-learning#1905's move to frontend-base's `Slot` API should only change the registration.

**Approach**

1. **Requests.** `src/data/api.js` has `getCourseCompetencyCriteria(courseId)`, which calls #733's LMS route, and `getCourseOutline(courseId)`, which calls `GET {LMS_BASE_URL}/api/learning_sequences/v1/course_outline/{courseId}`. Both go through `getAuthenticatedHttpClient()`.
   - If #733 takes the course key as a query parameter, pass it through axios `params`, because a literal `+` in a query string decodes as a space.
   - Don't run `camelCaseObject` over the outline response. `outline.sequences` is keyed by usage key, and `camelCaseObject` would rewrite those keys.
2. **Outline source.** The learning_sequences outline fits this panel for four reasons:
   - It keeps unreleased subsections, each with its `effective_start`, so a release-date marker needs no extra request if the UX design adds one.
   - It returns each subsection's plain `title`.
   - For learners, it already removes what they may not know exists: staff-only, `hide_from_toc`, content-group, cohort and enrollment-track restricted, and deleted content. The join therefore makes no visibility decision of its own: a criterion whose subsection is missing from the outline becomes part of a placeholder count.
   - It honors masquerade.

   The Course Home Outline API can't be the source. For learners, its `StartDateTransformer` drops subsections that aren't released yet, and it appends "(N Questions)" to graded subsection names.
3. **Query client.** `src/data/queryClient.js` creates one `QueryClient` lazily on first use, so the package entry point still does no work at import time. Configure it with a `QueryCache` whose `onError` calls `logError` from `@edx/frontend-platform/logging`, no retry on a 4xx response, and `refetchOnWindowFocus: false`. Set `staleTime` explicitly; its value is the implementer's choice. Every hook passes this client as `useQuery`'s second argument instead of reading one from React context, because of the host: frontend-app-learning's release/ulmo branch has no react-query and no `QueryClientProvider`, and master's provider logs every failed query itself. Reading the host's client would therefore break on release/ulmo and log every failure twice on master. Passing the client explicitly also lets #839's wrapper share the cache without putting a provider around the host's stock Grades card.
4. **Hooks.** `src/data/apiHooks.js` exports four things:
   - `useCourseCompetencyCriteria(courseId)`.
   - `useCourseOutline(courseId, { enabled })`.
   - `hasCompetencyCriteria(data)`, which is true when #733's criteria array is non-empty.
   - `useCompetencyCards(courseId)`, which runs the transform below inside `useMemo`.

   Enable the outline query only when `hasCompetencyCriteria` is true, so a course without competency criteria costs one request. Leave `targetUserId` out of both query keys, because neither response depends on which learner is being viewed. #839's "in place of" option is out of scope; #839 reuses `useCourseCompetencyCriteria` and `hasCompetencyCriteria`.
5. **Transform.** `buildCompetencyCards(criteriaResponse, outline)` lives in `src/data/buildCompetencyCards.js` and works in five steps:
   1. Walk `outline.sections`, and each section's `sequence_ids`, in order. Index each usage key found in `outline.sequences` with its `title` and its position in the outline.
   2. Mark every criterion whose `object_id` isn't in that index as hidden. Hidden criteria are counted, never dropped, and the outline can't say why one is missing, so a deleted subsection counts the same as a hidden one.
   3. The bottom-tier groups are the course-level group's direct children, ordered by `ordering`. In each bottom-tier group, group the criteria into rule boxes by effective rule, the same identity #672 gives rule boxes on the Competency Management page, and order the boxes by their lowest criterion `id`, as #672 does. Order each rule box's visible subsections by outline position, and give the box a hidden count for its placeholder row. #665 creates only three levels of groups, with the bottom tier as the lowest, so how a deeper tree displays is left to #731 and #732.
   4. Build the cards from each tag's `lineage`. A top-level tag heads its own card, and any other tag is a row in the card headed by its parent. When a tag is also the parent of another tag in the response, that tag heads the card and gets the target icon: its own groups go under the heading, ahead of the child rows, and it is not also a row in its own parent's card. Each `lineage` entry carries the tag's `id` and `value` (#733), ordered from the top of the taxonomy. The breadcrumb is the `value` of each entry in the heading's lineage without the heading. Key cards by the heading's tag `id`, and carry that `id` on the card and each row's tag `id` on the row, so #740 can attach competency statuses by tag id.
   5. Group the cards into taxonomy sections, ordered by taxonomy name. Every section gets its taxonomy heading, including when there is only one.

   Visibility removes nothing, because #733 already prunes every branch with no criterion, so every layout decision comes straight from #733's response: which tags head cards, whether a group's single rule sits on the group line, and where an AND/OR separator appears. The test fixtures should cover the Description's example, a tag with criteria alongside its own ancestor, a rule box mixing a profile-based criterion and an override criterion with the same effective rule (the backend normalizes this case away, but the grouping must key on the effective rule, not the profile ID), an unrecognized rule type or `op` (the subsection still appears, the line has no threshold, and the rule is logged), a rule box whose subsections are all hidden, a course whose subsections are all hidden, and placeholder counts of one and of several.
6. **Rule text.** `formatRuleText(rule, intl)` in `src/ruleText.js` maps `gte`, `lte`, and `eq` to their messages.
   - Format the threshold with `intl.formatNumber(value, { style: 'percent', maximumFractionDigits: 2 })`, which scales the stored 0.0 to 1.0 fraction and absorbs floating-point error. A hand-rolled `0.29 * 100` gives `28.999999999999996`.
   - For an unknown rule type or `op`, the function returns null, so that line renders without a threshold, and the transform logs the unknown rule once.
   - A bottom-tier group's `logic_operator` reads AND as "all", and OR or null as "any". The course-level group's operator appears between bottom-tier groups, with null read as OR, per ADR 0002.
   - The placeholder row's text is one ICU plural message, so translators control the singular and plural forms.
   - Write the strings in `src/messages.js` in sentence case, and uppercase them with Paragon's `text-uppercase` class, so translators don't receive all-caps source strings.
7. **Components.** `CompetencyProgressPanel` keeps its name and takes no props. It reads `courseId` from `useProgressRouteParams` and calls `useCompetencyCards`. It returns null unless both queries have data and the criteria response is non-empty; that single check covers loading, either request failing, and an empty result. `CompetencyCard` and `CriteriaGroupList` take the transform's output as plain props. The transform needs no try/catch, because the slot's error boundary and #829's `SilentErrorFallback` already contain a render-time throw.
8. **Packaging and wiring.** Add `@tanstack/react-query` to `package.json` as a peer dependency at `"*"`, like #810's other peers. The Learning MFE on master reuses its own v5 copy, and npm installs one where the MFE has none. The `competency_progress_panel` registration stays as it is. Remove the `competency_progress_summary` registration from `example.env.config.jsx` and from the Tutor plugin's slot mapping, keeping the two files identical, so learners don't see #829's sidebar placeholder before #743 replaces it.

**Files to create and modify**

Paths are relative to the root of the plugin repository from #810.

| File | Change |
| --- | --- |
| `src/CompetencyProgressPanel.jsx` | modified: the real panel replaces #829's placeholder |
| `src/CompetencyCard.jsx` | new: breadcrumb, heading, heading's own groups, child rows |
| `src/CriteriaGroupList.jsx` | new: bottom-tier groups, separators, rule lines, subsections, placeholder rows |
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
