# [FE] Right Side Course Competency Progress

GitHub: https://github.com/openedx/openedx-core/issues/743 (#743, OPEN)
Cached: 2026-09-21

## User Story
As a learner, I want to be able to see a high level summary of my overall status on the competencies assessed in my course in order to understand the big picture of my progress.

## Description
This ticket replaces the placeholder in the right column of the Progress tab with the real "Course Progress" card, which has a "Focus Areas" subtitle. Under that subtitle is one row per card in #734's competency criteria panel, in the same order as the cards, showing the card's heading name and the status #740 shows on that heading. In a course with no competency criteria, nothing from this ticket renders in the right column.

## Context
- #734 decides which competency heads each card in the competency criteria panel. This ticket shows one row per card, so it adds no rule of its own for which competencies appear.
- #740 decides which status each card heading shows. Each row shows the same status.
- #829 registers the right-column widget and renders the placeholder this ticket replaces.
- Displaying the Recommended Next Action is out of scope for this ticket because it will be handled in #755.
Blocked by #734, #739, #740, and #829. The tutor-mfe pin bump at the end of this ticket also waits for #828.

## UX Design

@illiphilli, please add the UX design screenshot(s) and the Figma link for this ticket.

- Figma: TBD
- Screenshots: TBD

## Acceptance Criteria

These scenarios use #734's terms (competency criteria panel, card, card heading, breadcrumb), #740's terms (tag row, status pill), and these terms:

- The Course Progress card is the card this ticket adds to the top of the Progress tab's right column. Anything another ticket renders inside it, such as #755's Recommended Next Action notice, is part of the card.
- A Focus Area row is one entry under the card's "Focus Areas" heading. It shows a competency's name and that competency's status pill. It has no target icon.
- A card heading's status is what #740 shows at the right end of that card's header in the competency criteria panel. It is "Available" when a hidden score masks the competency, and there is no pill when the learner's status can't be loaded.
- The scenarios use this taxonomy, "Workplace Skills":
  - Critical Thinking
      - Analysis
      - Evaluation
      - Inference
  - Communication
  - Problem Solving
      - Problem Definition
        - Root Cause Analysis
      - Strategy Selection
- Unless a scenario says otherwise:
  - The course's criteria use tags from "Workplace Skills" only.
  - Every subsection shows its score to the learner, so no status is masked.
  - The learner views the Progress tab at a desktop width, where the main column and the right column sit side by side.

```gherkin
Scenario Outline: Each row reads the heading of one card, which can be a tag above the one with criteria
  Given the course has competency criteria on <criteria>, and on no other tag
  When the learner opens the course's Progress tab
  Then the competency criteria panel shows one card, headed "<heading>"
  And the Course Progress card shows exactly one Focus Area row, reading "<heading>"
  And that row shows the name and a status pill, with no target icon, even when the card heading has one

  Examples:
    | case                                                                            | criteria                                       | heading            |
    | a top-level tag with criteria                                                   | "Communication"                                | Communication      |
    | second-level tags under one parent                                              | "Analysis" and "Inference"                     | Critical Thinking  |
    | a tag two levels deep, whose card has a breadcrumb                              | "Root Cause Analysis"                          | Problem Definition |
    | two branches that merge into one card                                           | "Strategy Selection" and "Root Cause Analysis" | Problem Solving    |

Scenario: The rows follow the cards' order
  Given the course has competency criteria on "Communication", "Analysis", "Inference", and "Root Cause Analysis"
  When the learner opens the course's Progress tab
  Then the competency criteria panel shows three cards, headed "Communication", "Critical Thinking", and "Problem Definition"
  And the Course Progress card shows exactly three Focus Area rows, with the same three names in the same order as the cards
  And no Focus Area row reads "Analysis", "Inference", "Root Cause Analysis", or "Problem Solving"

Scenario: Each row shows its card heading's own status, the same way the card heading shows it
  Given the course has competency criteria on "Communication", "Analysis", "Inference", and "Root Cause Analysis", so its cards are headed "Communication", "Critical Thinking", and "Problem Definition"
  And the learner's competency status is Demonstrated for "Communication", "Analysis", and "Inference", none recorded for "Problem Definition", and Partially Attempted for "Critical Thinking", because "Evaluation", which has criteria only in another course, is not yet demonstrated
  When the learner opens the course's Progress tab
  Then each Focus Area row shows the same status pill as its card heading, with the same icon, label, and colors
  And the "Communication" row reads "Demonstrated", with no score
  And the "Critical Thinking" row reads "Partially Attempted", even though both tags inside its card read "Demonstrated"
  And the "Problem Definition" row reads "Available"

Scenario: A hidden score masks a row the same way it masks the card heading
  Given the course has competency criteria on "Root Cause Analysis" only, so its card is headed "Problem Definition"
  And the learner's competency status is Demonstrated for "Problem Definition" and for "Root Cause Analysis"
  And "Final Exam", a subsection under "Root Cause Analysis" that the learner has not submitted, is set to show assessment results only once it is past due, and its due date hasn't passed
  When the learner opens the course's Progress tab
  Then the "Problem Definition" Focus Area row shows "Available", the same as the "Problem Definition" card heading
  And the row doesn't show "Demonstrated" at any point while the page loads

Scenario: A course with no competency criteria shows no Course Progress card
  Given a course with no competency criteria
  When the learner opens the course's Progress tab
  Then no Course Progress card, heading, message, or empty space appears in the right column
  And the right column shows the same content it shows on a site without the plugin

Scenario: Nothing from the Course Progress card appears while the competency criteria panel is loading
  Given a course with competency criteria
  And the course's competency criteria or its course outline is still loading
  When the learner opens the course's Progress tab
  Then no card, heading, row, loading indicator, or placeholder from the Course Progress card appears
  And the certificate status panel and the related links appear without waiting for it

Scenario Outline: Rows show their names without statuses when the learner's statuses can't be loaded
  Given a course with competency criteria
  And <failure>
  When the learner opens the course's Progress tab
  Then the Course Progress card appears with its headings and every row's name
  And no row shows a status pill, not even "Available"
  And no error message appears

  Examples:
    | failure                                                                                                                  |
    | the request for the learner's competency statuses fails, for example because the site's LMS doesn't provide #738's endpoint |
    | the learner's competency statuses load, and the request for their subsection scores fails                                |

Scenario Outline: The Course Progress card stays hidden when the competency criteria panel can't be shown
  Given a course with competency criteria
  And <failure>
  When the learner opens the course's Progress tab
  Then nothing from the Course Progress card appears, including anything another ticket renders inside it
  And no error message is shown to the learner
  And the certificate status panel and the related links appear as usual

  Examples:
    | failure                                                                  |
    | the request for the course's competency criteria fails                   |
    | the course's criteria load, and the request for the course outline fails |

Scenario: A course using one taxonomy shows no taxonomy subheading in Focus Areas
  Given a course whose competency criteria all use tags from "Workplace Skills"
  When the learner opens the course's Progress tab
  Then the Focus Area rows appear directly under the "Focus Areas" heading
  And "Workplace Skills" doesn't appear anywhere in the Course Progress card

Scenario Outline: Rows are grouped under a subheading per taxonomy when the course uses more than one
  Given a course with competency criteria on tags from <taxonomies>
  When the learner opens the course's Progress tab
  Then under the "Focus Areas" heading, a subheading appears for each of those taxonomies, named as in the competency criteria panel's taxonomy headings and in the same order
  And each card's row appears under its own taxonomy's subheading, in the same order as that taxonomy's cards

  Examples:
    | taxonomies                                                         |
    | "Workplace Skills" and "Accounting Standards"                      |
    | "Workplace Skills", "Accounting Standards", and "Digital Literacy" |

Scenario: Tags with the same name in two taxonomies get separate rows with their own statuses
  Given "Workplace Skills" and "Accounting Standards" each have a top-level tag named "Communication", and the course has criteria on both tags
  And the learner's competency status is Demonstrated for the "Communication" tag in "Workplace Skills", and none recorded for the one in "Accounting Standards"
  When the learner opens the course's Progress tab
  Then a "Communication" row showing "Demonstrated" appears under the "Workplace Skills" subheading
  And a "Communication" row showing "Available" appears under the "Accounting Standards" subheading

Scenario: Every card gets a plain-text row, and a long name is cut short with its full name available via tooltip
  Given a course whose competency criteria panel shows 15 cards, some headed by names too long to fit on one line beside their status pill in the right column
  When the learner opens the course's Progress tab
  Then the Course Progress card shows 15 Focus Area rows, with no "show more" control and no scrolling area of its own
  And no row's name is a link
  And every row is one line tall, with its status pill whole and at the right edge of the row
  And a name that doesn't fit ends in an ellipsis instead of wrapping onto another line or running under the pill
  And hovering over, or moving keyboard focus to, a cut-short name shows its full name in a tooltip
  And a name that fits shows no tooltip

Scenario Outline: The Course Progress card is first in the right column at every screen width
  Given a course with competency criteria
  When the learner opens the course's Progress tab at <width>
  Then a card headed "Course Progress", with a "Focus Areas" heading above its rows, appears <place>
  And the certificate status panel and the related links still appear, and behave as they do on a site without the plugin
  And the page doesn't scroll horizontally

  Examples:
    | width                                                               | place                                                                                                                     |
    | a width where the main column and the right column sit side by side | at the top of the right column, above everything else in that column, including the certificate status panel when it is there |
    | a width where the right column stacks below the main column         | below all of the main column's content, and above everything else in the right column                                   |

Scenario Outline: Course staff viewing a learner see the same rows and statuses that learner sees
  Given the course has competency criteria on "Communication" and "Inference", so its cards are headed "Communication" and "Critical Thinking"
  And a learner in content group A has a competency status of Demonstrated for "Communication" and for "Inference"
  And "Group B Project", a subsection under "Communication", is restricted to content group B, so it has no score of the learner's to hide and masks nothing, and the learner's own Progress tab shows the "Communication" row as "Demonstrated"
  And "Unit 3 Quiz", a subsection under "Inference", is set to show assessment results only once it is past due, and its due date hasn't passed, so the learner's own Progress tab shows the "Critical Thinking" row as "Available"
  And the staff member has no competency statuses of their own
  When a member of course staff <view>
  Then the Focus Area rows read "Communication" and "Critical Thinking", as on the learner's own Progress tab
  And the "Communication" row shows "Demonstrated" and the "Critical Thinking" row shows "Available", as on the learner's own Progress tab

  Examples:
    | view                                                                          |
    | opens that learner's progress page, for example from the instructor dashboard |
    | views the course's Progress tab masquerading as that learner                  |

Scenario: Fixed text is translated, and competency names appear as stored
  Given the learner's language is one for which the plugin's translations are installed
  When the learner opens the course's Progress tab
  Then the "Course Progress" and "Focus Areas" headings appear in the learner's language
  And each row's status label appears in the learner's language, the same as on the card headings
  And each competency name and taxonomy subheading appears exactly as it is stored in its taxonomy, untranslated

Scenario: A screen reader user can move through the card by headings and hears each row with its status
  Given a course whose cards span two taxonomies
  When a screen reader user moves through the Course Progress card, including by jumping between headings
  Then they hear "Course Progress" as a level 2 heading, the level the stock "Course completion" and "Grades" card titles use
  And they hear "Focus Areas" as a level 3 heading, and each taxonomy subheading as a level 4 heading
  And they hear each taxonomy's rows as a list, announced with its number of items
  And they hear each row's full competency name, even when it is cut short on screen, followed by its status, each status once, with no separate announcement from the status icon or the tooltip
  And no Focus Area row is announced as a heading
```

<details>
<summary>Technical Details</summary>

This is a suggested approach, not the source of truth. The User Story, Description, and Acceptance Criteria define what must be true when the work is done.

**Summary**

The sidebar widget calls the same two hooks the main competency panel calls, `useCompetencyCards` from #734 and `useCompetencyStatuses` from #739, through the plugin's single query client, so the two widgets share every request and the sidebar shows the same masked statuses as the card headings. It renders a "Course Progress" card with one "Focus Areas" row per card in the main panel, showing that card's heading name and its status pill on one line, grouped under a heading per taxonomy when the course uses more than one. A name too long for its row ends in a CSS ellipsis and gets a tooltip. The widget renders nothing whenever the main panel renders nothing, and a tutor-mfe pull request moves tutor-mfe's pinned package version to the release that includes this ticket.

**Approach**

1. **Widget.** Replace the body of #829's placeholder `CompetencyProgressSummary` in `src/CompetencyProgressSummary.jsx`. Keep the component's name, its named export from `src/index.jsx`, and its widget id `competency_progress_summary`, because operators import the component and target the id in their own `pluginSlots` configuration. #829's `getPluginSlots` already registers the widget in `org.openedx.frontend.learning.progress_tab_certificate_status_side_panel.v1` at priority 20 with `keepDefault` true, so the slot configuration stays as it is. That slot renders the stock certificate status only at large widths but renders plugin widgets at every width, so the widget needs no width check of its own.
2. **Data.** The widget reads `{ courseId, targetUserId }` from `useProgressRouteParams` and calls `useCompetencyCards(courseId)` and `useCompetencyStatuses(courseId, targetUserId)`, exactly as `CompetencyProgressPanel` does. The two widgets sit in different slots with no common ancestor the plugin controls, so the module-level client from `src/data/queryClient.js` is the only state they share; identical query keys on that one client make react-query send each request once for both widgets. `useCompetencyStatuses` also brings #740's masking, including its staff-route rule, with no new code.
3. **When the card renders.** Return null unless `useCompetencyCards` reports `isReady`, the same flag #734's `CompetencyProgressPanel` checks, so the sidebar never renders when the panel does not. Returning null while loading, in a course without criteria, and after a criteria or outline failure is what keeps #755's notice, and its #754 request, from mounting in those cases.
4. **Card.** `CourseProgressCard` in `src/CourseProgressCard.jsx` takes plain props: #734's taxonomy sections, and the tag status map, which the widget passes as `statuses.tags` once `isPending` is false and as null otherwise. It renders a Paragon `Card` with "Course Progress" as an `h2` and "Focus Areas" as an `h3`, both from `src/messages.js`, as real heading elements, because Paragon's `Card.Header` renders its `title` and `subtitle` props as `div`s. Keep the Focus Areas heading and its rows in one block, so #755 can add `RecommendedNextAction` after that block, inside the card, without restructuring it. Do not export `CourseProgressCard` from `src/index.jsx`.
5. **Rows.** Render one list item per card, in the order of #734's sections and of the cards within them, showing the card heading tag's `value` and keyed by its `id`. The row label is the card heading exactly as #734 computed it; this ticket adds no label logic. With more than one taxonomy section, give each section an `h4` with the taxonomy name, followed by that section's own list. With one section, render one list and no `h4`. Safari's VoiceOver drops list semantics from a list styled with `list-unstyled`, so check that the rows still announce as a list there.
6. **Status and long names.** Each row is a one-line flex row holding the name and #739's `StatusOval`.
   - The pill is `StatusOval` with the heading tag's status from the map and no `percentGraded`, so the colors, icons, and labels match the card headings exactly. A row shows no pill when the map is null, which covers both pending and failed statuses, or when the tag is missing from the map, which is how #740 represents an unknown status. The pill gets `flex-shrink-0`, so it stays whole at the right edge.
   - The name renders through #734's `TruncatedName`, as the row's `flex-grow-1` item, so a name too long for the row ends in an ellipsis and, only then, gets a tab stop and a tooltip with the full name. CSS truncation keeps the full name in the DOM, so a screen reader reads it whole, and `TruncatedName`'s tooltip is set up not to announce the name a second time. Tests put a name in the truncated state the same way #734's `TruncatedName` tests do, by stubbing `ResizeObserver`, `scrollWidth`, and `clientWidth`.
7. **Test cases beyond the AC:**
   - Render `CompetencyProgressPanel` and `CompetencyProgressSummary` together in one tree, on the learner route and again on the staff route. Once the pills appear, assert that #733's criteria, the course outline, #738's statuses, and the Progress API were each requested exactly once. This catches the two widgets building different keys for the two requests that depend on the learner, #738's statuses and the Progress API, for example the sidebar falling back to the signed-in user's id on the learner route, where `useProgressRouteParams` gives no `targetUserId`. A mismatch like that would otherwise silently double those requests.
   - A course with criteria on both "Problem Solving" and its grandchild "Root Cause Analysis" shows exactly one row, reading "Problem Solving", the same single card #734's merge rule gives the main panel. #902 rejects criteria on both an ancestor and its descendant on Studio re-import, but a Django admin edit can still produce them.
   - When #738's statuses and the Progress API's scores arrive after the criteria and the outline, the card appears at the same time as the main panel's cards, with every row's name and no pill. Once both arrive, every row shows its pill, and no row shows a status that later changes.
   - A status the page doesn't recognize, returned by the platform for "Communication": the "Communication" row shows its name and no pill, and every other row shows its pill as usual. QA can't produce an unrecognized status without mocking the response, so this is a render test rather than an Acceptance Criteria scenario.
8. **tutor-mfe pin.** Once a package release includes this ticket, open a pull request to `overhangio/tutor-mfe` that moves the pinned package version #828 adds to that release. Verify it on a Learning MFE image rebuilt from that branch, by opening the Progress tab of a course with criteria. Until a tutor-mfe release includes that pull request, Tutor sites show #829's placeholder where this card goes.

Out of scope:

- The Recommended Next Action notice (#755).
- Release documentation (#744).
- Letting a course author choose which level of the hierarchy Focus Areas shows, a candidate follow-up that has no issue yet.

**Files to create and modify**

Paths are relative to the root of the plugin repository from #810.

| File | Change |
| --- | --- |
| `src/CompetencyProgressSummary.jsx` | modified: the real widget replaces #829's placeholder |
| `src/CourseProgressCard.jsx` | new |
| `src/messages.js` | modified |
| `tutormfe/plugin.py` in `overhangio/tutor-mfe` | modified: wherever #828 declares the package's pinned version, most likely this file, otherwise `tutormfe/templates/mfe/build/mfe/Dockerfile` |

**Additional context**

- Figma for the case with two taxonomies, with rows grouped under a heading per taxonomy: https://www.figma.com/design/VqDdtf3NOsUihle6SNS6Kw/-Course-Level----Student-Progress?node-id=1562-27227
- In frontend-app-learning, `src/course-home/progress-tab/ProgressTab.jsx` lays out the right column, and `src/plugin-slots/ProgressTabCertificateStatusSidePanelSlot/` shows the width-gated stock content.
- Showing #829's placeholder on Tutor sites for one tutor-mfe release is an accepted tradeoff. Sites that install the package without tutor-mfe get this card as soon as they upgrade the package.
- Known limitations, which #744 documents:
  - A row whose heading tag has no criteria of its own takes its status from #643's roll-up, so it reads "Available" until #643 ships.
  - A single subsection with a hidden score anywhere under a card's heading makes that row read "Available", because #740 spreads masking to every ancestor tag.
  - Statuses span all of the learner's courses, so a row can read "Partially Attempted" after the learner has finished everything in this course.
  - A site that writes its own `pluginSlots` instead of calling `getPluginSlots` must register the widget by hand.

</details>
