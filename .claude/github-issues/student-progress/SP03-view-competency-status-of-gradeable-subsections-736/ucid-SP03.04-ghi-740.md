# [FE] Display Competency Statuses for Learner in Course

GitHub: https://github.com/openedx/openedx-core/issues/740 (#740, OPEN)
Cached: 2026-09-21

## User Story
As a learner, I need to know my mastery status for each competency in my course in order to understand what I need to work on improving and how I can speak about my skills.

## Description
This ticket implements the oval status indicator display for each competency in the CBE progress cards on the Course Progress page.

This implementation reads the competency statuses from the endpoint built in #738. The status shown is the learner's overall status for the competency across all courses, not only this course.

For each competency tag serving as a card title (a card heading, at any depth), if the learner's status is:
- Not yet recorded (no status row), then display the "Available" oval in blue/white with the corresponding icon.
- PartiallyAttempted, then display the "Partially Attempted" oval in blue with the corresponding icon.
- Demonstrated, then display the "Demonstrated" oval in green with the checkmark icon.

For each competency tag serving as a card subtitle (a tag row inside a card), with the row's pill tinted by status as in the design, if the learner's status is:
- Not yet recorded (no status row), then display "Available" after the pipe next to the tag name.
- PartiallyAttempted, then display "Partially Attempted" after the pipe next to the tag name.
- Demonstrated, then display "Demonstrated" after the pipe next to the tag name.

Breadcrumb entries above a card heading show no status.

If any subsection under a competency tag in this course shows "Available" because its score is hidden (see #739), that tag and every ancestor tag above it display "Available" too, so a competency status never reveals a hidden result.

## Context
- #738 is the backend counterpart to this ticket.
- Blocked by #734 and #739.

## UX Design

@illiphilli, please add the UX design screenshot(s) and the Figma link for this ticket.

- Figma: TBD
- Screenshots: TBD

## Acceptance Criteria

These scenarios use #734's terms (card heading, tag row, breadcrumb, placeholder row) and these:

- A learner's competency status for a tag is the overall status the platform has recorded for that learner and that competency, across all courses: Partially Attempted, Demonstrated, or none recorded.
- A card heading's status pill sits at the right end of the card header and shows a status icon and a status label.
- A tag row's status is the label that follows the pipe after the tag's name, inside the row's outlined pill.
- A subsection hides its score when the course hides that subsection's result from the learner on the Progress tab. On a named row, #739 shows this as an "Available" oval.
- Each status's colors are the ones in the attached design.
- Unless a scenario says otherwise, every subsection in the course shows its score to the learner, so no status is masked.

```gherkin
Scenario Outline: A card heading shows the learner's status for its competency
  Given "Communication", a top-level tag with criteria of its own in this course, heads its own card
  And the learner's competency status for "Communication" is <status>
  When the learner opens the course's Progress tab
  Then the "Communication" card header shows a "<label>" status pill at its right end, with the <icon> icon, in the design's colors for <label>

  Examples:
    | status              | label               | icon                |
    | none recorded       | Available           | empty circle        |
    | Partially Attempted | Partially Attempted | half-filled circle  |
    | Demonstrated        | Demonstrated        | circle with a check |

Scenario Outline: A tag row shows the learner's status after its name
  Given "Analysis", a tag with criteria in this course, appears as a tag row in the "Critical Thinking" card
  And the learner's competency status for "Analysis" is <status>
  When the learner opens the course's Progress tab
  Then the "Analysis" tag row shows the target icon, "Analysis", a pipe, and "<label>", inside one outlined pill tinted in the design's color for <label>

  Examples:
    | status              | label               |
    | none recorded       | Available           |
    | Partially Attempted | Partially Attempted |
    | Demonstrated        | Demonstrated        |

Scenario: A card heading with no criteria of its own shows its competency's own status, even when its rows differ
  Given "Analysis", "Evaluation", and "Inference" are children of "Critical Thinking", a top-level tag
  And this course has criteria on "Analysis" and "Inference", and none on "Critical Thinking" or "Evaluation"
  And the learner's competency status is Demonstrated for "Analysis" and "Inference", and Partially Attempted for "Critical Thinking", because "Evaluation", which has criteria only in another course, is not yet demonstrated
  When the learner opens the course's Progress tab
  Then the "Critical Thinking" card heading shows "Partially Attempted"
  And the "Analysis" and "Inference" tag rows each show "Demonstrated"

Scenario: A card heading below the top level shows its status, and its breadcrumb shows none
  Given "Root Cause Analysis" is a child of "Problem Definition", which is a child of "Problem Solving", a top-level tag
  And this course has criteria on "Root Cause Analysis"
  And the learner's competency status is Demonstrated for "Problem Solving", because the learner met "Problem Solving"'s own requirements in another course, and Partially Attempted for "Problem Definition"
  When the learner opens the course's Progress tab
  Then the "Problem Definition" card heading shows "Partially Attempted"
  And no breadcrumb entry above it, including "Problem Solving", shows a status

Scenario Outline: A hidden score masks its competency and every ancestor, wherever each appears
  Given "Problem Definition" and "Strategy Selection" are children of "Problem Solving", a top-level tag, and "Root Cause Analysis" is a child of "Problem Definition"
  And this course has criteria on "Strategy Selection" and "Root Cause Analysis", so a "Problem Solving" card contains "Strategy Selection", and a "Problem Definition" card with a "Problem Solving" breadcrumb contains "Root Cause Analysis"
  And the learner's competency status is Demonstrated for all four tags
  And "Final Exam", a subsection under "Root Cause Analysis" that the learner has not submitted, <hiding>
  When the learner opens the course's Progress tab
  Then the "Root Cause Analysis" tag row shows "Available"
  And the "Problem Definition" card heading shows "Available"
  And the "Problem Solving" card heading shows "Available"
  And the "Strategy Selection" tag row still shows "Demonstrated"
  And none of the masked tags shows "Demonstrated" at any point while the page loads

  Examples:
    | hiding                                                                                                     |
    | is set to show assessment results only once it is past due, and its due date hasn't passed                 |
    | is set to never show individual assessment results, but show overall assessment results after the due date |

Scenario Outline: A subsection with no result to hide never masks a competency
  Given "Inference" is a tag row in the "Critical Thinking" card
  And one of the subsections under "Inference" <reason>
  And the learner's competency status is Demonstrated for "Inference" and Partially Attempted for "Critical Thinking"
  When the learner opens the course's Progress tab
  Then the "Inference" tag row shows "Demonstrated"
  And the "Critical Thinking" card heading shows "Partially Attempted"

  Examples:
    | reason                                                                       |
    | is visible only to staff, so the learner sees it as a placeholder row        |
    | isn't released yet, so the learner sees it by name with an "Available" oval  |

Scenario: A subsection hidden from the course outline still masks its competency while its results are hidden
  Given "Bonus Case Study", a subsection under "Analysis" in the "Critical Thinking" card, is hidden from the course outline, so the learner sees it as a placeholder row
  And the learner reached it through a direct link and scored 19 of 20 points on it, so their competency status for "Analysis" is Demonstrated
  And "Bonus Case Study" is set to show assessment results only once it is past due, and its due date hasn't passed
  When the learner opens the course's Progress tab
  Then the "Analysis" tag row and the "Critical Thinking" card heading show "Available"

Scenario: Tags with the same name in two taxonomies each show their own status
  Given two taxonomies, "Workplace Skills" and "Accounting Standards", each have a top-level tag named "Communication", and this course has criteria on both tags
  And the learner's competency status is Demonstrated for the "Communication" tag in the "Workplace Skills" taxonomy, and none recorded for the "Communication" tag in the "Accounting Standards" taxonomy
  When the learner opens the course's Progress tab
  Then the "Communication" card under the "Workplace Skills" taxonomy heading shows "Demonstrated"
  And the "Communication" card under the "Accounting Standards" taxonomy heading shows "Available"

Scenario: No competency shows a status when the learner's statuses can't be loaded
  Given a course with competency criteria
  And the request for the learner's competency statuses fails, for example because the site's LMS doesn't provide #738's endpoint
  When the learner opens the course's Progress tab
  Then the cards appear with their headings and tag rows
  And no card heading shows a status pill, and no tag row shows a pipe or a status, not even "Available"
  And no error message appears in their place

Scenario Outline: A staff member viewing a learner's progress sees the same statuses the learner sees on their own Progress tab
  Given a learner in content group A, whose competency status is Demonstrated for "Communication" and for "Inference", a tag row in the "Critical Thinking" card
  And "Group B Project", a subsection under "Communication", is restricted to content group B, so the learner's own Progress tab shows it as a placeholder row and "Communication" as "Demonstrated"
  And "Unit 3 Quiz", a subsection under "Inference", is set to show assessment results only once it is past due, and its due date hasn't passed, so the learner's own Progress tab shows "Inference" and "Critical Thinking" as "Available"
  And the staff member has no competency statuses of their own
  When a member of course staff <view>
  Then "Group B Project" appears <appearance>
  And the "Communication" card heading shows "Demonstrated", as on the learner's own Progress tab
  And the "Inference" tag row and the "Critical Thinking" card heading show "Available", as on the learner's own Progress tab

  Examples:
    | view                                                                     | appearance                                                    |
    | opens that learner's progress page, for example from the instructor dashboard | by name, because #734 shows staff every subsection there |
    | views the Progress tab masquerading as that learner                      | as a placeholder row, as on the learner's own Progress tab    |

Scenario: A screen reader user hears each competency's name with its status
  Given the "Critical Thinking" card heading's status is Partially Attempted
  And its tag rows are "Analysis", whose status is Demonstrated, and "Inference", which has no recorded status
  When a screen reader user moves through the card, including by jumping between headings
  Then they hear "Critical Thinking" with "Partially Attempted", "Analysis" with "Demonstrated", and "Inference" with "Available"
  And they hear each status once, with nothing announced for the pipe and no second announcement from a status icon

Scenario: Status labels are legible against their background
  Given card headings and tag rows showing each of "Available", "Partially Attempted", and "Demonstrated"
  When a reviewer measures each status label's contrast against the background behind it
  Then every status label meets WCAG 2.1 AA contrast for its text size

Scenario: Statuses stay readable beside long names on a small screen
  Given a card whose heading and a tag row inside it both have names long enough to fill a phone-width card
  When the learner opens the course's Progress tab at a phone-sized viewport
  Then the heading's status pill wraps onto its own line when it doesn't fit beside the heading name
  And the tag row's pill wraps onto more lines, keeping the name, the pipe, and the status inside it
  And no name or status is cut off, overlaps another, or extends past the card's edge
```

<details>
<summary>Technical Details</summary>

This is a suggested approach, not the source of truth. The User Story, Description, and Acceptance Criteria define what must be true when the work is done.

**Summary**

Each card heading shows the learner's status for its tag in #739's `StatusOval`, which reads "Demonstrated" instead of a score when given none. Each tag row shows its status in a new `TagStatusPill`. #739's `buildCompetencyStatuses` supplies these statuses, and sets every tag above a masked subsection to "Available".

**Approach**

1. **Tag statuses.** Add `tags` to #739's `buildCompetencyStatuses` result, beside #739's `criteria`: a `Map` from tag `id` to a display status. Criterion ids and tag ids are different id spaces, so the two stay in separate maps. Consumers read both through #739's `useCompetencyStatuses`, whose shape is unchanged, so #743 and #745 get the same masked result. Cover every `id` in the `lineage` of every tag in #733's `tags`; that includes card headings with no criteria of their own. A tag shows its `student_competency_statuses` entry, or "Available" when it has none. A tag whose status is unknown is left out of the map, so it gets no pill and no pipe (#739 already logs the value).
2. **Propagation.** For each criterion that #739 marks `masked`, take its tag, which is the `tag_id` of its group's root as `buildCompetencyCards` resolves it. Mark every `id` in that tag's `lineage`, which runs from the top of the taxonomy down to the tag itself. A masked tag shows "Available" whatever its stored status, including an unknown one. Because the map is keyed by tag id, a masked tag reads "Available" everywhere it appears, including as the heading of a different card. Unreleased subsections are never `masked`, so they never mask the tags above them.
   - Placeholder rows: #739's `criteria` covers named rows only, so check each placeholder criterion here. A placeholder criterion masks its tag's lineage when its `object_id` is in the learner's `section_scores` index with `show_grades` false. A learner can reach a subsection hidden from the outline (`hide_from_toc`) through a direct link and submit it, so a hidden result can sit behind its recorded status. Other placeholder rows, such as staff-only or other-group subsections, aren't in the learner's `section_scores`, so they never mask.
3. **Staff route.** On the staff route, #734's outline is the staff member's, so a subsection the learner can't see is a named row there. For example, take "Group A Project" and "Group B Project", alternative paths joined by OR under "Communication", each restricted to its content group, for a Group A learner whose "Communication" status is Demonstrated:
   - On the learner's own page, "Group B Project" isn't in the learner's outline, so it is a placeholder row. Because it belongs to another group, the learner can't open it, and it isn't in the learner's `section_scores`. So, unlike a hidden-from-outline subsection with hidden results (step 2), its placeholder row doesn't mask the tags above it, and "Communication" reads "Demonstrated".
   - On the staff route, "Group B Project" is a named row. The Progress API leaves it out of the learner's `section_scores`, and #739's rule masks a named row that is missing from `section_scores`. That mask would spread to the tags above it, so "Communication" would read "Available".

   So when `targetUserId` is set, `buildCompetencyStatuses` leaves `masked` false for a named row that is missing from `section_scores`. Its oval still reads "Available", as #739 specifies. A row whose `show_grades` is false still masks, because the Progress API computes `show_grades` for the learner. Erring toward showing staff more is safe: masking exists so that some learners don't see results before others, and course staff can already see grades in the Gradebook. Masquerade needs nothing, because #734's outline is already the masqueraded learner's and `targetUserId` is unset.
4. **Headings.** `CompetencyCard` looks up the card's heading tag `id` (#734) and renders #739's `StatusOval` without `percentGraded`, so a Demonstrated heading reads "Demonstrated" rather than a score, inside the heading element at the right end of the header. That way a screen reader moving by heading hears the status together with the name. Breadcrumb entries show nothing.
5. **Tag rows.** `TagStatusPill` renders the target icon, the name, an `aria-hidden` pipe, and the status label as visible text, all inside one outlined pill tinted by status. Paragon has no component for this. `Chip` is the closest: without `onClick` it renders as a non-interactive `div`, and it supports `iconBefore`, but it has no tinted variants and its label never wraps (`.pgn__chip__label` sets `white-space: nowrap` with an ellipsis). Build `TagStatusPill` on `Chip`: per status, override its border and background custom properties and `--pgn-color-chip-label-base`, which also colors the icon, so the status text meets the contrast scenario; set `--pgn-size-chip-border-radius` to `var(--pgn-size-badge-border-radius-pill)`, because `Chip`'s default radius (`0.375rem`) is much squarer than the design's fully rounded pill; and let the label wrap. Without `onClick`, `Chip`'s `iconBefore` renders a plain `Icon` with no text alternative, so give the target icon its text alternative in an `sr-only` sibling, as #734 requires. Call out the Paragon gap in the PR description so it can be raised upstream.
6. **Failure.** When #739's hook returns null `statuses`, headings get no pill and rows get no pipe or status. That includes a Progress API failure while #738 succeeds: without the Progress API the mask can't be computed, and showing #738's statuses unmasked could reveal a hidden result.
7. **Test cases beyond the AC:**
   - When the Progress API fails while #738 succeeds, no tag status appears.
   - An unknown status shows no status on a heading or on a tag row.
   - A masked tag whose stored status is unknown shows "Available".
   - On the staff route, a named row missing from `section_scores` doesn't mask its tags, and a row whose `show_grades` is false still does.
   - A placeholder criterion whose subsection is in `section_scores` with `show_grades` false masks its tags. One whose subsection is missing from `section_scores`, such as a staff-only or other-group subsection, doesn't.

Out of scope:

- Subsection ovals and the per-subsection mask (#739).
- The Focus Areas sidebar (#743).

**Files to create and modify**

Paths are relative to the root of the plugin repository from #810.

| File | Change |
| --- | --- |
| `src/data/buildCompetencyStatuses.js` | modified: tag statuses, propagation, and the staff-route mask rule |
| `src/CompetencyCard.jsx` | modified: heading pill and tag row pills |
| `src/TagStatusPill.jsx` | new |
| `src/messages.js` | modified |

**Additional context**

- Known limitations:
  - A heading's status rolls up child tags the card doesn't show, so "Partially Attempted" can sit above rows that all read "Demonstrated".
  - Masking covers only this course's criteria, so a competency can read "Available" here and "Demonstrated" on another course's Progress tab.
  - A subsection whose results are hidden until its due date makes its competency and every ancestor read "Available" until that date passes. When its results are never shown, they read "Available" for the whole run. This applies even to competencies demonstrated in another course.
  - On the staff route, a subsection set to never show individual results (`never_but_include_grade`) doesn't mask its tags, because the Progress API leaves it out of `section_scores` the same way it leaves out subsections the learner can't see. Staff can therefore see a tag status that the learner sees as "Available". Masquerade matches the learner's page exactly.
- Statuses for tags with no criteria of their own, such as most card headings, come from #643's roll-up through `Tag.parent`. Until #643 ships, those headings read "Available".
- A distinct "results not released yet" state, instead of "Available" for a masked tag, is a possible UX follow-up with @illiphilli.

</details>
