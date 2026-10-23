# [FE] Static Competency Status Sunburst

GitHub: https://github.com/openedx/openedx-core/issues/747 (#747, OPEN)
Cached: 2026-09-21

## User Story
As a learner, I want to see at a glance how the subsection assignments and sub-competencies in my course roll up to the competencies on my Progress page, and the status of each, in order to understand how my work in this course inter-relates and where I stand.

## Description
Above the competency status cards in the main column of the Progress page, add one sunburst per taxonomy that the course's competency criteria use, with a single legend. A course whose criteria use three or more taxonomies shows no sunbursts for now.

Sunburst:
- The center of the sunburst says "COMPETENCIES DEMONSTRATED".
- The rings correspond to how #734 lays out that taxonomy's cards. The innermost ring has one segment per card heading, and each further ring is one nesting depth of the rows inside the cards. Breadcrumb ancestors above a card heading are not drawn.
- The outermost ring is for the subsection assignments, and it is thinner than the competency rings. A competency with no rows beneath it extends its segment outward to meet the subsection ring, so every subsection segment sits in that one outer ring.
- Within each ring, children share their parent's angle equally. Segments run clockwise from 12 o'clock in the order the cards display them.

Legend:
- Each segment is filled with its status's color.
- Demonstrated has a green checkmark. Competency and subsection segments can be Demonstrated.
- Available has a slate circle with a dashed ring. Competency and subsection segments can be Available.
- Partially Attempted has a blue half-filled circle. Competency and subsection segments can be Partially Attempted.
- Not Demonstrated has a dark red circle with a minus sign. Only subsection segments can be Not Demonstrated, because a competency is never Not Demonstrated.
- The legend always lists all four statuses.

## Context
- Corresponds with the UXD Spike #769
- The tooltip is out of scope for this ticket because it will be built in #751.
- Blocked by #734, #739, #740

## UX Design

@illiphilli, please add the UX design screenshot(s) and the Figma link for this ticket.

- Figma: TBD
  - [Six Deep](https://www.figma.com/design/VqDdtf3NOsUihle6SNS6Kw/-Course-Level----Student-Progress?node-id=1089-4395)
  - [Two taxonomies](https://www.figma.com/design/VqDdtf3NOsUihle6SNS6Kw/-Course-Level----Student-Progress?node-id=1562-27227)
  - [Sizes and legend](https://www.figma.com/design/VqDdtf3NOsUihle6SNS6Kw/-Course-Level----Student-Progress?node-id=1564-13187)
  - [Six-level merge](https://www.figma.com/design/VqDdtf3NOsUihle6SNS6Kw/-Course-Level----Student-Progress?node-id=1568-13715)
- Screenshots: TBD

## Acceptance Criteria

These scenarios use #734's terms (card, card heading, tag row, path row, breadcrumb, named row, placeholder row) and #739's and #740's statuses, plus these definitions:

- The competency rings are the sunburst's inner bands. The innermost holds one segment per card heading, and each further ring holds the tag rows and path rows at the next nesting depth inside the cards. The subsection ring is the outermost band and holds one segment for each subsection the cards count, including each subsection counted in a placeholder row.
- A segment's angle is the share of the circle it spans.
- A segment is drawn as a status when it is filled with that status's color from the legend.
- Unless a scenario says otherwise, the course's criteria use one taxonomy, the learner's statuses and scores have loaded, and no status is masked.

```gherkin
Scenario: One sunburst and one legend appear above the cards
  Given a course whose competency criteria all use tags from "Workplace Skills"
  When the learner opens the course's Progress tab
  Then one sunburst and one legend appear at the top of the competency criteria panel, above the "Workplace Skills" heading and its cards
  And no taxonomy name appears above the sunburst
  And no segment carries a text label

Scenario Outline: The center caption is the same whatever the learner's progress
  Given a course with competency criteria
  And <progress>
  When the learner opens the course's Progress tab
  Then the center of the sunburst reads "COMPETENCIES DEMONSTRATED", with no count or percentage

  Examples:
    | progress                                                   |
    | the learner hasn't submitted anything in the course        |
    | the learner has demonstrated every competency in the chart |

Scenario: A course using two taxonomies shows one named sunburst per taxonomy and one shared legend
  Given a course with competency criteria on tags from "Workplace Skills" and from "Accounting Standards", and each taxonomy has a top-level tag named "Communication" with criteria in this course
  When the learner opens the course's Progress tab
  Then two sunbursts appear above all of the cards, one per taxonomy, in the same order as the taxonomy headings below them
  And each sunburst has its own taxonomy's name, "Accounting Standards" or "Workplace Skills", above it
  And each sunburst draws only its own taxonomy's cards, so each "Communication" tag has a segment only in its own taxonomy's sunburst
  And exactly one legend appears for the two sunbursts
  And no sunburst or legend appears inside either taxonomy's section of cards

Scenario: A course using three or more taxonomies shows no sunburst
  Given a course with competency criteria on tags from three taxonomies
  When the learner opens the course's Progress tab
  Then no sunburst and no legend appear, and no message or empty space takes their place
  And each taxonomy's heading and cards appear as usual

Scenario: The rings follow the cards, starting from the card headings
  Given the taxonomy and course criteria from #734's Description example, which give a "Communication" card with no tag rows, a "Critical Thinking" card with "Analysis" and "Inference" rows, and a "Problem Definition" card with a "Root Cause Analysis" row under a "Problem Solving" breadcrumb
  When the learner opens the course's Progress tab
  Then the innermost ring has three segments, one per card heading: "Communication", "Critical Thinking", and "Problem Definition"
  And the second ring has "Analysis" and "Inference" beneath "Critical Thinking", and "Root Cause Analysis" beneath "Problem Definition"
  And no segment is drawn for "Problem Solving" or for any other breadcrumb entry
  And the subsection ring has one segment for each subsection the three cards count, beneath the tag the card lists it under
  And the subsection ring is narrower than each competency ring

Scenario: A competency with no tag rows beneath it reaches out to the subsection ring
  Given the course from #734's Description example
  When the learner opens the course's Progress tab
  Then the "Communication" segment extends from the innermost ring across the second ring's position to the subsection ring
  And Communication's subsection segments sit in the same outermost ring as every other subsection segment

Scenario: A card below the top of a deep taxonomy draws only the card's own levels
  Given a taxonomy six levels deep, with one tag at each level, named "Level 1" at the top through "Level 6" at the bottom
  And the course has competency criteria on "Level 6" only, so its card is headed "Level 5" with "Level 1" through "Level 4" as a breadcrumb
  When the learner opens the course's Progress tab
  Then the sunburst has two competency rings: "Level 5", spanning the whole circle, and "Level 6" beneath it
  And no segment is drawn for "Level 1", "Level 2", "Level 3", or "Level 4"

Scenario: A merged card draws its path rows as rings (Ref 2)
  Given "Problem Definition" and "Strategy Selection" are children of "Problem Solving", a top-level tag, and "Root Cause Analysis" is a child of "Problem Definition"
  And the course has competency criteria on "Strategy Selection" and "Root Cause Analysis" only, so #734 shows one "Problem Solving" card with a "Strategy Selection" row and a "Problem Definition" path row with "Root Cause Analysis" nested under it
  When the learner opens the course's Progress tab
  Then the sunburst has three competency rings: "Problem Solving"; then "Strategy Selection" and "Problem Definition"; then "Root Cause Analysis", beneath "Problem Definition"
  And the "Strategy Selection" segment extends from the second ring to the subsection ring

Scenario: Six competency rings are all drawn, with no cap
  Given "Problem Solving" is a top-level tag whose children include "Strategy Selection" and "Problem Definition"
  And below "Problem Definition" is one tag per level, "Level 3", "Level 4", and "Level 5", and "Level 5" has two children, "Level 6 A" and "Level 6 B"
  And the course has competency criteria on "Strategy Selection", "Level 6 A", and "Level 6 B" only, so #734 shows one "Problem Solving" card with "Problem Definition", "Level 3", "Level 4", and "Level 5" as nested path rows
  When the learner opens the course's Progress tab
  Then the sunburst has six competency rings and the subsection ring
  And "Level 6 A" and "Level 6 B" are segments in the sixth competency ring, beneath "Level 5"
  And no ring is left out and no level is combined with another

Scenario: A card heading with criteria of its own shares its angle between its own subsections and its rows (Ref 1)
  Given "Root Cause Analysis" is a child of "Problem Definition", which is a child of "Problem Solving", a top-level tag
  And "Problem Solving" and "Root Cause Analysis" both have criteria in this course and "Problem Definition" has none, so #734 shows one "Problem Solving" card whose own groups list two subsections first, followed by a "Problem Definition" path row with "Root Cause Analysis" nested under it
  When the learner opens the course's Progress tab
  Then the sunburst has three competency rings: "Problem Solving", then "Problem Definition", then "Root Cause Analysis"
  And Problem Solving's two own subsection segments and the "Problem Definition" segment each span a third of Problem Solving's angle
  And over its two own subsections, the "Problem Solving" segment extends outward across the second and third rings' positions to the subsection ring
  And Problem Solving's own subsection segments sit in the subsection ring, clockwise before the subsection segments beneath "Problem Definition"

Scenario: Children share their parent's angle equally in every ring
  Given a "Critical Thinking" card with tag rows "Analysis", which has three subsections, and "Inference", which has one
  And a "Communication" card with no tag rows and two subsections
  When the learner opens the course's Progress tab
  Then "Critical Thinking" and "Communication" each span half of the circle
  And "Analysis" and "Inference" each span half of Critical Thinking's angle
  And each of Analysis's three subsection segments spans a third of Analysis's angle, and Inference's one subsection segment spans all of Inference's angle
  And each of Communication's two subsection segments spans half of Communication's angle

Scenario: Every subsection gets its own segment, however many there are
  Given a tag with 40 subsections in this course
  When the learner opens the course's Progress tab
  Then 40 subsection segments appear beneath that tag's segment, each spanning an equal share of its angle
  And no subsections are combined into a shared segment

Scenario: Segments run clockwise from 12 o'clock in the order the cards show them
  Given a "Communication" card followed by a "Critical Thinking" card, which lists "Analysis" and then "Inference"
  And under Analysis's rule line the card lists "Quiz 1", "Quiz 2", and then a placeholder row for one hidden subsection
  When the learner opens the course's Progress tab
  Then the "Communication" segment starts at 12 o'clock, and "Critical Thinking" follows it clockwise
  And within Critical Thinking's angle, "Analysis" comes before "Inference", clockwise
  And within Analysis's angle, the segments for "Quiz 1", "Quiz 2", and the hidden subsection follow clockwise in that order

Scenario: Segments run counterclockwise in a right-to-left language
  Given the "Communication" card followed by the "Critical Thinking" card from the previous scenario
  And the learner's language reads right to left, such as Arabic
  When the learner opens the course's Progress tab
  Then the "Communication" segment starts at 12 o'clock, and every segment follows counterclockwise, in the same order as the cards

Scenario Outline: Each competency segment is drawn in the status the cards show for it
  Given <tag> appears in the cards as <kind>
  And the learner's competency status for <tag> is <status>
  When the learner opens the course's Progress tab
  Then the <tag> segment is drawn as <label>, matching the status the cards show for <tag>

  Examples:
    | tag                  | kind           | status              | label               |
    | "Critical Thinking"  | a card heading | none recorded       | Available           |
    | "Analysis"           | a tag row      | Partially Attempted | Partially Attempted |
    | "Problem Definition" | a path row     | Demonstrated        | Demonstrated        |

Scenario Outline: Each subsection segment is drawn in the status its row's oval shows
  Given "Quiz 1" appears by name under "Analysis", under a rule line reading "AT 80% OR BETTER"
  And <result>
  When the learner opens the course's Progress tab
  Then the "Quiz 1" segment is drawn as <label>, matching Quiz 1's oval in the card

  Examples:
    | result                                                                                              | label               |
    | the learner hasn't submitted Quiz 1                                                                 | Available           |
    | the learner's recorded status on Quiz 1 is Partially Attempted                                      | Partially Attempted |
    | the learner scored 12 of 20 points on Quiz 1, so their recorded status is Not Demonstrated          | Not Demonstrated    |
    | the learner scored 19 of 20 points on Quiz 1, so their recorded status is Demonstrated              | Demonstrated        |
    | Quiz 1's results are set never to be shown, and the learner's recorded status on it is Demonstrated | Available           |

Scenario Outline: A segment whose status the page doesn't recognize is drawn as Available
  Given the platform returns a status for <item> that the page doesn't recognize, so the cards show no status for it
  When the learner opens the course's Progress tab
  Then <segment> is drawn as Available
  And the legend still lists exactly four statuses

  Examples:
    | item                                                  | segment                |
    | "Analysis", a tag row in the "Critical Thinking" card | the "Analysis" segment |
    | "Quiz 1", a subsection under "Analysis"               | the "Quiz 1" segment   |

Scenario: A competency is drawn in its own status even when every subsection under it is Not Demonstrated
  Given the learner's recorded status is Not Demonstrated on each subsection under "Analysis"
  And their competency status for "Analysis" is Partially Attempted
  When the learner opens the course's Progress tab
  Then each subsection segment beneath "Analysis" is drawn as Not Demonstrated
  And the "Analysis" segment is drawn as Partially Attempted

Scenario: A competency the cards mask is drawn as Available
  Given "Problem Definition" and "Strategy Selection" are children of "Problem Solving", "Root Cause Analysis" is a child of "Problem Definition", and the course has criteria on "Strategy Selection" and "Root Cause Analysis" only
  And the learner's competency status is Demonstrated for all four tags
  And "Final Exam", a subsection under "Root Cause Analysis" that the learner has not submitted, is set to show assessment results only once it is past due, and its due date hasn't passed
  When the learner opens the course's Progress tab
  Then the "Final Exam", "Root Cause Analysis", "Problem Definition", and "Problem Solving" segments are drawn as Available, as the cards show them
  And the "Strategy Selection" segment is drawn as Demonstrated
  And no masked segment is drawn as Demonstrated at any point while the page loads

Scenario: Each subsection hidden from the learner gets its own segment, drawn like an Available one
  Given a rule line under "Analysis" lists "Quiz 1", which the learner can see, and a placeholder row reading "3 more subsections that aren't visible to you"
  And the learner scored 19 of 20 points on one of the hidden subsections before the author hid it from the course outline, so their recorded status on it is Demonstrated
  When the learner opens the course's Progress tab
  Then four subsection segments appear beneath "Analysis": Quiz 1's, followed clockwise by one for each hidden subsection
  And each hidden subsection's segment looks the same as an Available subsection segment
  And the legend still lists exactly four statuses

Scenario: A subsection under two competencies appears under each, with each one's own status
  Given "Quiz 3" appears by name under "Analysis", under a rule line reading "AT 80% OR BETTER", and under "Inference", under a rule line reading "AT 90% OR BETTER"
  And the learner scored 17 of 20 points on Quiz 3, so their recorded status is Demonstrated for the "Analysis" criterion and Not Demonstrated for the "Inference" criterion
  When the learner opens the course's Progress tab
  Then a "Quiz 3" segment beneath "Analysis" is drawn as Demonstrated
  And a second "Quiz 3" segment beneath "Inference" is drawn as Not Demonstrated

Scenario: The legend always lists all four statuses
  Given a course in which no segment is drawn as Partially Attempted or Not Demonstrated
  When the learner opens the course's Progress tab
  Then the legend lists "Demonstrated", "Available", "Partially Attempted", and "Not Demonstrated", in that order, each with its status icon
  And every segment's color is the color of one of those four entries
  And the legend's text meets WCAG 2.1 AA contrast against its background

Scenario: The gaps between segments match the background behind the sunburst
  Given a site whose theme gives the Progress tab a background other than white
  When the learner opens the course's Progress tab
  Then the gaps between segments show the same color as the area behind the sunburst, not white

Scenario Outline: The sunburst doesn't respond to the pointer or to touch
  Given a course with competency criteria
  When <action>
  Then no tooltip, highlight, fade, or icon appears, and the sunburst and the rest of the page stay as they were

  Examples:
    | action                                       |
    | the learner moves the pointer over a segment |
    | the learner clicks a segment                 |
    | the learner taps a segment on a touch screen |

Scenario: Keyboard focus passes over the sunburst
  Given a course with competency criteria
  When a keyboard user presses Tab to move through the Progress tab
  Then focus never stops on a sunburst or on any of its segments

Scenario: The sunburst appears only once the learner's statuses have loaded
  Given a course with competency criteria
  And the learner's competency statuses and subsection scores finish loading after the cards appear
  When the learner opens the course's Progress tab
  Then the cards appear first, with no sunburst, legend, loading indicator, or reserved space above them
  And once the statuses and scores load, the sunburst and legend appear above the cards all at once, without animating, with every segment in its final status
  And the cards move down to make room for them
  And no segment changes after the sunburst first appears

Scenario Outline: The sunburst stays hidden when the learner's statuses can't be loaded
  Given a course with competency criteria
  And the request for <data> fails
  When the learner opens the course's Progress tab
  Then no sunburst and no legend appear, and no error message appears in their place
  And the taxonomy headings and cards appear as #739 and #740 describe for that failure

  Examples:
    | data                              |
    | the learner's competency statuses |
    | the learner's subsection scores   |

Scenario: A failure while drawing the sunburst doesn't hide the cards
  Given the learner's statuses load, but drawing the sunburst fails, for example because the data has a shape the chart doesn't expect
  When the learner opens the course's Progress tab
  Then no sunburst and no legend appear
  And the taxonomy headings and cards appear as usual
  And the failure is reported to the site's logging service

Scenario Outline: Course staff viewing a learner see the sunburst that matches that page's cards
  Given a learner in content group A, whose competency status is Demonstrated for "Communication" and for "Inference", a tag row in the "Critical Thinking" card
  And "Group B Project", a subsection under "Communication", is restricted to content group B
  And "Unit 3 Quiz", a subsection under "Inference", is set to show assessment results only once it is past due, and its due date hasn't passed
  And the staff member has no competency statuses of their own
  When a member of course staff <view>
  Then the "Communication" segment is drawn as Demonstrated
  And the "Inference", "Critical Thinking", "Unit 3 Quiz", and "Group B Project" segments are drawn as Available
  And every segment whose card heading, tag row, or subsection row shows a status on that page is drawn in that status

  Examples:
    | view                                                                          |
    | opens that learner's progress page, for example from the instructor dashboard |
    | views the Progress tab masquerading as that learner                           |

Scenario: The sunburst scales with the main column and fits a small screen
  Given a course with competency criteria
  When the learner narrows the browser window from desktop width to a phone-sized viewport
  Then each sunburst shrinks with the main column, staying round and within the column
  And the legend's entries wrap onto more lines instead of being cut off
  And the page doesn't scroll horizontally at any width

Scenario: A screen reader user hears each sunburst as one image, and the cards carry its information
  Given a course with competency criteria
  When a screen reader user moves through the top of the competency criteria panel
  Then they hear each sunburst once, as an image whose text alternative says it summarizes their competency statuses and that the cards below list every competency and its status
  And when there are two sunbursts, each one's text alternative also names its taxonomy
  And they hear no individual segment
  And they hear the legend's four status names as text, each once, with no separate announcement for the legend's icons
  And every competency and subsection the sunburst draws appears in the cards as text, with the same status wherever the card shows one
```

<details>
<summary>Technical Details</summary>

This is a suggested approach, not the source of truth. The User Story, Description, and Acceptance Criteria define what must be true when the work is done.

**Summary**

A pure function turns each taxonomy section from #734's `useCompetencyCards`, plus the two masked status maps from #739's `useCompetencyStatuses`, into a list of sunburst nodes with angles, rings, and statuses. A hand-written SVG component draws one path per node, with no new runtime dependency. `CompetencyProgressPanel` renders one or two charts and one shared legend above the taxonomy sections, inside their own error boundary. Every segment carries the ids, ancestry, source references, and centroid that #751's tooltips and highlight build on.

**Approach**

1. **Node tree.** `buildSunburstTree(section, statuses)` in `src/data/buildSunburstTree.js` takes one taxonomy section and the `statuses` from `useCompetencyStatuses`. It returns the section's nodes in reading order, with angles in radians and rings as indexes. It works only in angles and ring indexes, never pixels or SVG, so a later drill-in or chart library can reuse it.
   - Each card heading is a tag node in ring 0. Each row, path rows included, is a tag node one ring deeper than the row or heading it sits under.
   - Each criterion is one subsection node in the outer ring. A subsection under two tags, or in two groups under one tag, therefore gets one node per criterion.
   - A tag node's children are its own subsections first, then its child rows, in card order. Its own subsections go group by group and rule box by rule box: the named subsections in outline order, then that rule box's hidden criteria. Each child gets an equal share of its parent's angle, and the card headings share the full circle equally.
   - Each tag node records the angle span its own subsections cover. The drawing step extends the tag's segment out to the subsection ring over that span. A tag with no rows therefore extends across its whole angle, and a heading with both its own subsections and rows (#734 Ref 1) extends only over its own subsections.
   - A tag node's status is `statuses.tags.get(tagId)`, and a subsection node's is `statuses.criteria.get(criterionId).status` (#739's criteria entries are objects with `status`, `percentGraded`, and `masked`). A missing entry, which covers every hidden criterion and any unknown status, is drawn as Available.
   - For #751, every node carries four things:
     - an `id` namespaced by kind (`tag-12`, `criterion-12`), hidden criteria included, because tag ids and criterion ids are separate id spaces;
     - `ancestorIds`;
     - `source`, a reference to the #734 card or row for a tag node, or to the named row or hidden criterion for a subsection node;
     - `entry`, the raw #739 map entry for the node (or null when there is none), so #751 can tell an unknown or missing status from a real Available one and can read a subsection's `percentGraded`.
2. **Hidden criterion ids.** `buildCompetencyCards` gives each rule box a count of its hidden criteria. Have it also carry those criteria's ids, in `id` order, beside the count. Each hidden segment then has an id, and the cards keep rendering the count as they do.
3. **Geometry.** `src/sunburstGeometry.js` takes the nodes, the ring count, and a diameter in pixels, and returns each node's path string and centroid.
   - The ring count is the deepest tag ring plus one. The radii are a center hole, a competency band split equally among the rings, and a thinner subsection ring. Take the ratios from the Sizes and legend frame. A Ref 2 merge can produce six competency rings; they are drawn thin, with no cap.
   - A plain segment is two arcs and two lines. A Ref 1 heading is one path of three arcs and three lines, so no seam is drawn inside one segment.
   - A segment that spans the full circle, such as the only card in a taxonomy or a tag with one subsection, must be drawn as two half arcs, because an SVG arc whose start and end points coincide draws nothing. Set the large-arc flag when a span exceeds half the circle.
   - The centroid is the segment's angular midpoint, at the mid-radius of the band the segment covers across its whole angle.
   - In a right-to-left locale (`isRtl(getLocale())` from `@edx/frontend-platform/i18n`), mirror x. The segments then run counterclockwise, while the node tree keeps reading order.
4. **Chart.** `Sunburst` in `src/Sunburst.jsx` renders one `<svg role="img">` per section, sized in pixels, inside a `position: relative` wrapper that also holds the center caption, so #751 can position its anchor and in-segment icon against the wrapper. It builds a `nodesById` index from step 1's list for its own lookups and for #751.
   - The `aria-label` comes from `src/messages.js` and includes the taxonomy name only when there are two charts.
   - Each segment is a `<path>` with `data-segment-id`, `data-status`, and `data-ring`.
   - The fill comes from #739's shared status map as an inline style, so a later Paragon token drops in.
   - Each path is stroked 2px in `var(--pgn-color-body-bg)`, the page background behind the panel, which #734 places directly in the main column rather than in a Card. The strokes draw the gaps, so #751's `fill-opacity` fade leaves the gaps unchanged.
   - The center caption is an `aria-hidden` HTML element over the hole, so it wraps in long translations and can take Paragon's `text-uppercase`. Hide it when the diameter is under 320px.
5. **Layout and legend.** `CompetencySunbursts` in `src/CompetencySunbursts.jsx` measures its own width with a `ResizeObserver`. It renders nothing for three or more sections.
   - One section: the diameter follows the column, from 240 to 420px.
   - Two sections: the charts sit side by side at (width minus 40px) / 2, up to 420px each, when that gives each chart at least 280px. Otherwise they stack, up to 320px each. Each chart has its taxonomy name above it as plain text, not a heading, so heading navigation still lands only on #734's taxonomy headings.
   - A chart is never wider than the column, so nothing scrolls sideways.
   - `SunburstLegend` in `src/SunburstLegend.jsx` is one list placed after all the charts, which puts it centered under side-by-side charts and under the last of stacked ones. It has four entries in the Description's order: icons from the status map marked `aria-hidden`, labels as text, wrapping with Bootstrap's flex utilities.
6. **Mounting and states.** `CompetencyProgressPanel` renders `CompetencySunbursts` above the taxonomy sections and passes it the sections and `statuses` it already has, so there is no new request, hook, or slot.
   - `CompetencySunbursts` is only the `ErrorBoundary` from `@edx/frontend-platform/react`, with an empty fragment as `fallbackComponent`, as #755 does, around an inner `CompetencySunburstsContent` in the same file.
   - The inner component does all the work in step 5 and builds the trees: measuring the width, laying out the charts, and rendering the legend. Keeping all of it inside the boundary is what makes a throw anywhere in the chart hide only the chart and never the cards.
   - It renders nothing while `isPending` is true or `statuses` is null.
7. **Tests beyond the AC.**
   - Pure tests for `buildSunburstTree`:
     - equal shares at each level;
     - extension spans for a tag without rows and for a Ref 1 heading;
     - the order of own subsections, rule boxes, outline positions, and hidden criteria;
     - a Ref 2 merge with six rings;
     - a subsection under two tags as two nodes, each with its own status;
     - hidden and unknown statuses drawn as Available;
     - ids on hidden nodes.
   - Geometry tests: a full-circle segment, a span over half the circle, a centroid, and mirroring.
   - Render tests count each ring's segments by `data-ring` and check each segment's `data-status`. Don't snapshot path strings.
   - jsdom has no `ResizeObserver`, so mock it.

Out of scope:

- hover, tap, tooltips, the highlight, and the in-segment status icon (#751);
- a layout for three or more taxonomies;
- a distinct style or legend entry for hidden subsections;
- a minimum ring width for deep merges.

**Files to create and modify**

Paths are relative to the root of the plugin repository from #810.

| File | Change |
| --- | --- |
| `src/data/buildSunburstTree.js` | new |
| `src/data/buildCompetencyCards.js` | modified: hidden criterion ids on each rule box |
| `src/sunburstGeometry.js` | new |
| `src/Sunburst.jsx` | new |
| `src/SunburstLegend.jsx` | new |
| `src/CompetencySunbursts.jsx` | new |
| `src/CompetencyProgressPanel.jsx` | modified: renders `CompetencySunbursts` above the taxonomy sections |
| `src/messages.js` | modified: center caption, text alternatives, legend labels |

**Additional context**

- Design references: the four Figma frames linked under UX Design, plus [a row with no criteria of its own](https://www.figma.com/design/VqDdtf3NOsUihle6SNS6Kw/-Course-Level----Student-Progress?node-id=1559-12397). The [Sunburst Explorer](https://d3v8e8hqzoulm1.cloudfront.net/axim/sunburst-explorer/) prototype opens on this ticket's static mode.
- The colors and icons are #768's Option G. The Available fill (`#CBD5E1`) is 1.48:1 against the white gaps and page, below WCAG 1.4.11's 3:1 for graphics. For comparison, Demonstrated is 3.14:1, Partially Attempted 6.03:1, Not Demonstrated 11.27:1, and the Available icon's dashed ring 6.69:1. This is accepted for MVP because the cards below give every status as text.
- #748 should document:
  - what the rings follow;
  - the status colors and the Available contrast;
  - masking that makes tags read Available;
  - statuses that span courses;
  - the missing segment labels and tooltips until #751;
  - the rule for three or more taxonomies;
  - card headings that read Available until #643 ships.
- More than two competency rings come from #734's card merges (Ref 2), which #666 allows. #733's response order sets the card order that the segments follow.

</details>

## Open Questions

- (architect, final review) How should the chart handle six competency rings? #734's merge rule (Ref 2) can nest path rows five deep under a card heading, which #666 allows, so a follow-up that closes the re-import loophole would still not make two rings the maximum. At the 240px minimum diameter each ring is about 9px wide. Approach step 3 accepts thin rings with no cap, which the designer also leans toward. Alternatives: let the minimum diameter grow with the ring count (for example at least 24px per ring), or cap the rings and roll deeper levels into their row's segment.
- (architect, final review) Should the center caption be hidden on charts narrower than 320px? The designer's Sizes and legend frame hides it there, and Approach step 4 follows that frame, but the Description says the center "says COMPETENCIES DEMONSTRATED" and the Acceptance Criteria say it reads that in every state. If the hiding stands, the Description's center bullet needs a qualifier and the caption scenario needs a small-chart exception. The alternative is to show the caption at every size in smaller type.
- (architect, final review) Where should the hidden criterion ids per rule box be added? #734's transform gives each rule box only a count of hidden criteria, and this ticket needs an id on every hidden segment (and #751 a reference to each hidden criterion). Approach step 2 adds the ids in this ticket. If #734 has not been built yet, adding them there is cheaper, and step 2 and its files-table row drop out of this ticket.
- (architect, final review) With two taxonomies, is the name above each chart plain text or a heading? Approach step 5 uses plain text so heading navigation still lands only on #734's taxonomy headings. A heading would duplicate those in the heading outline.
