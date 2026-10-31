# [FE] Sunburst Tooltips

GitHub: https://github.com/openedx/openedx-core/issues/751 (#751, OPEN)
Cached: 2026-09-21

## User Story
As a learner, when I hover over or tap a segment of the sunburst, I want to see more information about what that segment represents in order to understand where I stand on it and what it takes to demonstrate it.

## Description
This ticket implements the tooltips and hover highlight for the sunburst built in #747. Hovering with a pointer or tapping a segment shows its tooltip; tapping another segment switches, and tapping outside or pressing Escape dismisses it. There are 2 cases of tooltips:

Tooltip for Competency Tag segment:
- Display the competency tag name.
- Display the competency status using the same oval that #740 shows on a card heading.
- Display the icon and count of subsection assignments beneath this segment in the sunburst, in the format "<icon> # ASSIGNMENTS".
- If this segment has no competency segments beneath it and its tag's criteria in this course are one group with one rule, display that rule in the format "COMPLETE ANY/ALL AT XX% OR BETTER" (or "OR LOWER" / "EXACTLY", matching #734's rule lines). Otherwise display "MULTIPLE REQUIREMENTS".
- If the count is 12 or fewer, display an icon for the status of each of those subsection assignments at the bottom of the tooltip, in the same order as their segments. If the count is more than 12, don't display any icons for them.

Tooltip for Subsection Assignment segment:
- Display the subsection assignment icon and the name of the subsection, which should wrap.
- Display the competency criterion status just like how it looks in its card row below.
- For a subsection hidden from the learner, display "A subsection that isn't visible to you" and no status.

While a segment is hovered or tapped, its status icon is drawn inside the segment. Also while a segment is hovered or tapped, there is a faded overlay for all the other segments in that sunburst except for this one, its ancestors, and its descendants.

## Context
- Corresponds to UXD Spike #750
- Blocked by #747

## UX Design

@illiphilli, please add the UX design screenshot(s) and the Figma link for this ticket.

- Figma: TBD
  - [Competency tooltip](https://www.figma.com/design/VqDdtf3NOsUihle6SNS6Kw/-Course-Level----Student-Progress?node-id=1244-26891)
  - [Sub-competency tooltip](https://www.figma.com/design/VqDdtf3NOsUihle6SNS6Kw/-Course-Level----Student-Progress?node-id=1253-5600)
  - [Assignment tooltip](https://www.figma.com/design/VqDdtf3NOsUihle6SNS6Kw/-Course-Level----Student-Progress?node-id=1253-6531)
- Screenshots: TBD

## Acceptance Criteria

These scenarios use #734's, #739's, #740's, and #747's terms (card heading, tag row, path row, named row, placeholder row, oval, segment, competency ring, subsection ring, "drawn as"), and these:

- The tooltip is the card that appears beside a segment the learner hovers over or taps. A competency tooltip is the one for a card heading's, tag row's, or path row's segment. An assignment tooltip is the one for a subsection segment.
- A hidden subsection's segment is the segment #747 draws for a subsection the card counts in a placeholder row.
- A segment's subtree is every segment beneath it, out to the subsection ring.
- While a segment is hovered or tapped, a segment is lit when it keeps its full color and faded when it is drawn paler.
- Unless a scenario says otherwise, the course's criteria use one taxonomy, the learner's statuses load, no status is masked, and the learner uses a mouse. The "Critical Thinking" card has tag rows "Analysis" and "Inference", "Quiz 3" appears under both, and the sunburst also has a "Communication" segment.

```gherkin
Scenario: Hovering a segment shows its tooltip beside the point where the pointer entered
  When the learner moves the pointer onto the "Analysis" segment
  Then the tooltip for "Analysis" appears beside the point where the pointer entered the segment
  And when the learner moves the pointer to another point inside the "Analysis" segment, the tooltip stays where it first appeared instead of following the pointer

Scenario Outline: The hovered segment, the segments above it, and its whole subtree stay lit
  When the learner hovers over <hovered>
  Then <lit> are lit, in exactly the colors the legend shows
  And every other segment in that sunburst fades, including <faded>

  Examples:
    | hovered                                 | lit                                                                                     | faded                                                                                         |
    | the "Critical Thinking" segment         | "Critical Thinking", "Analysis", "Inference", and every subsection segment beneath them | "Communication" and its subsection segments                                                   |
    | the "Analysis" segment                  | "Analysis", "Critical Thinking", and every subsection segment beneath "Analysis"        | "Inference", the "Quiz 3" segment beneath "Inference", and "Communication"                    |
    | the "Quiz 3" segment beneath "Analysis" | that "Quiz 3" segment, "Analysis", and "Critical Thinking"                              | the "Quiz 3" segment beneath "Inference" and the other subsection segments beneath "Analysis" |

Scenario: Only the hovered sunburst fades
  Given a course with criteria on tags from "Workplace Skills" and "Accounting Standards", so two sunbursts appear
  When the learner hovers over a segment in the "Accounting Standards" sunburst
  Then the segments outside the hovered branch fade in the "Accounting Standards" sunburst only
  And every segment in the "Workplace Skills" sunburst and every legend entry keep their full color

Scenario Outline: The hovered segment shows its status icon at its center
  Given <segment> is drawn as <status>
  When the learner hovers over that segment
  Then the legend's <status> icon appears at the center of that segment
  And no other segment shows an icon
  And a screen reader doesn't announce the icon

  Examples:
    | segment                                          | status              |
    | the "Analysis" segment                           | Partially Attempted |
    | the "Critical Thinking" segment                  | Available           |
    | the "Quiz 3" segment beneath "Analysis"          | Demonstrated        |
    | the "Quiz 3" segment beneath "Inference"         | Not Demonstrated    |
    | a hidden subsection's segment beneath "Analysis" | Available           |

Scenario: The status icon keeps its size on a thin segment
  Given a tag with 40 subsections in this course, so each of its subsection segments is narrower than the status icon
  When the learner hovers over one of those subsection segments
  Then the segment's status icon appears at the same size as on any other segment, centered on the segment
  And where the icon is wider than the segment, it overlaps the faded segments beside it

Scenario: Moving the pointer to a neighboring segment switches the tooltip and highlight
  Given the tooltip for "Analysis" is showing
  When the learner moves the pointer directly onto the neighboring "Inference" segment, across the gap between them
  Then the tooltip for "Inference" replaces the one for "Analysis", without every segment returning to full color in between
  And the lit and faded segments, and the icon, change to follow "Inference"

Scenario: The learner can move the pointer onto the tooltip without it closing
  Given the tooltip for "Analysis" is showing
  When the learner moves the pointer from the "Analysis" segment onto the tooltip
  Then the tooltip and the highlight stay as they are while the pointer is over the tooltip
  And when the pointer then leaves the tooltip for somewhere other than a segment, the tooltip closes and every segment returns to full color

Scenario: Moving the pointer off the sunburst closes the tooltip
  Given the tooltip for "Analysis" is showing
  When the learner moves the pointer off the sunburst, not onto the tooltip
  Then the tooltip closes, every segment returns to full color, and no segment shows an icon

Scenario: Pressing Escape closes the tooltip
  Given the tooltip for "Analysis" is showing, with the pointer still over the "Analysis" segment
  When the learner presses Escape
  Then the tooltip closes and every segment returns to full color
  And the tooltip stays closed while the pointer stays within the "Analysis" segment

Scenario Outline: Tapping shows, switches, and closes the tooltip on a touch screen
  Given the learner is using a touch screen
  And <state>
  When the learner taps <target>
  Then <result>

  Examples:
    | state                                 | target                                    | result                                                                                 |
    | no tooltip is showing                 | the "Analysis" segment                    | the tooltip for "Analysis" appears, with the same highlight and icon as when hovering  |
    | the tooltip for "Analysis" is showing | the "Analysis" segment again              | the tooltip for "Analysis" stays open, with the same highlight and icon                |
    | the tooltip for "Analysis" is showing | the "Inference" segment                   | the tooltip for "Inference" replaces it, and the highlight and icon follow "Inference" |
    | the tooltip for "Analysis" is showing | the page outside the sunburst and tooltip | the tooltip closes and every segment returns to full color                             |
    | the tooltip for "Analysis" is showing | the center of the sunburst                | the tooltip closes and every segment returns to full color                             |
    | the tooltip for "Analysis" is showing | the tooltip itself                        | the tooltip stays open                                                                 |

Scenario Outline: Nothing appears over the parts of the chart that aren't segments
  Given no tooltip is showing
  When the learner moves the pointer over <place>
  Then no tooltip appears and no segment fades

  Examples:
    | place              |
    | the center caption |
    | the legend         |

Scenario: A competency tooltip shows the name, status, assignment count, requirement, and each assignment's status
  Given "Communication" is a card heading with tag rows "Written Communication" and "Oral Communication", and four subsection segments lie beneath the "Communication" segment
  And the learner's competency status for "Communication" is Partially Attempted
  When the learner hovers over the "Communication" segment
  Then the tooltip shows, from top to bottom: "Communication"; the "Partially Attempted" oval; the assignment icon with "4 ASSIGNMENTS"; "MULTIPLE REQUIREMENTS"; and a row of four status icons
  And the four icons show the statuses of the four subsection segments, in the same order as the segments

Scenario Outline: Every competency tooltip shows the status as a card heading's oval
  Given <tag> appears in the cards as <kind>, and the learner's competency status for it is <status>
  When the learner hovers over the <tag> segment
  Then the tooltip shows the "<label>" oval with its icon, the same oval a card heading shows, and not a tag row's pill

  Examples:
    | tag                  | kind           | status              | label               |
    | "Critical Thinking"  | a card heading | none recorded       | Available           |
    | "Analysis"           | a tag row      | Partially Attempted | Partially Attempted |
    | "Problem Definition" | a path row     | Demonstrated        | Demonstrated        |

Scenario Outline: A competency with no competency segments beneath it states its one rule
  Given "Written Communication" has no tag rows beneath it, and its criteria in this course are <criteria>
  When the learner hovers over the "Written Communication" segment
  Then the tooltip's requirement line reads "<line>"

  Examples:
    | criteria                                                                               | line                          |
    | one group that requires any one of them, each requiring 80% or better                  | COMPLETE ANY AT 80% OR BETTER |
    | one group that requires all of them, each requiring 80% or better                      | COMPLETE ALL AT 80% OR BETTER |
    | one group holding a single criterion that requires 80% or better                       | COMPLETE ANY AT 80% OR BETTER |
    | one group that requires all of them, each requiring 40% or lower                       | COMPLETE ALL AT 40% OR LOWER  |
    | one group that requires all of them, each requiring exactly 100%                       | COMPLETE ALL AT EXACTLY 100%  |
    | one group that requires all of them, two at 75% or better and one at 90% or better     | MULTIPLE REQUIREMENTS         |
    | two groups, each requiring 80% or better                                               | MULTIPLE REQUIREMENTS         |
    | one group with one rule the cards can't state, so the card's group line shows no score | MULTIPLE REQUIREMENTS         |

Scenario Outline: A competency with competency segments beneath it reads "MULTIPLE REQUIREMENTS"
  Given <tag> is <kind>
  When the learner hovers over the <tag> segment
  Then the tooltip's requirement line reads "MULTIPLE REQUIREMENTS"

  Examples:
    | tag                  | kind                                                                                                           |
    | "Critical Thinking"  | a card heading with tag rows beneath it                                                                        |
    | "Problem Definition" | a path row with "Root Cause Analysis" nested beneath it                                                        |
    | "Problem Solving"    | a card heading whose own criteria are one group with one rule, with a "Problem Definition" path row beneath it |

Scenario Outline: The assignment count includes every subsection beneath the segment, hidden ones too
  Given <total> subsection segments lie beneath the "Analysis" segment, <hidden> of them hidden subsections' segments
  When the learner hovers over the "Analysis" segment
  Then the tooltip shows the assignment icon with "<text>"

  Examples:
    | total | hidden | text           |
    | 1     | 0      | 1 ASSIGNMENT   |
    | 4     | 3      | 4 ASSIGNMENTS  |
    | 40    | 0      | 40 ASSIGNMENTS |

Scenario Outline: The row of status icons appears only for 12 or fewer assignments
  Given <total> subsection segments lie beneath the "Analysis" segment
  When the learner hovers over the "Analysis" segment
  Then <icons>
  And the tooltip still shows "<total> ASSIGNMENTS"

  Examples:
    | total | icons                                                                                            |
    | 12    | a row of 12 status icons appears at the bottom of the tooltip, in the same order as the segments |
    | 13    | no row of status icons appears                                                                   |

Scenario: A hidden subsection appears in the row as the Available icon
  Given beneath "Analysis" are "Quiz 1", drawn as Demonstrated, and then one hidden subsection's segment
  When the learner hovers over the "Analysis" segment
  Then the row of status icons shows the Demonstrated icon and then the Available icon

Scenario: A competency demonstrated in another course reads Demonstrated above this course's own results
  Given the learner's competency status for "Analysis" is Demonstrated, from another course
  And the learner's recorded status is Not Demonstrated on each of Analysis's two subsections in this course
  When the learner hovers over the "Analysis" segment
  Then the tooltip shows the "Demonstrated" oval
  And its row of status icons shows two Not Demonstrated icons

Scenario Outline: An assignment tooltip shows the subsection's name and the same oval as its card row
  Given "Draft a persuasive memo" appears by name under "Written Communication"
  And <result>
  When the learner hovers over the "Draft a persuasive memo" segment
  Then the tooltip shows the assignment icon and "Draft a persuasive memo"
  And the tooltip shows <oval>, the same as the subsection's row in the card
  And the tooltip shows no assignment count, no requirement line, and no row of status icons

  Examples:
    | result                                                                                         | oval                                       |
    | the learner hasn't submitted it                                                                | the "Available" oval, with no score        |
    | the learner's recorded status on it is Partially Attempted                                     | the "Partially Attempted" oval             |
    | the learner scored 12 of 20 points on it, so their recorded status is Not Demonstrated         | the "Not Demonstrated" oval, with no score |
    | the learner scored 19 of 20 points on it, so their recorded status is Demonstrated             | the "Demonstrated" oval reading "95%"      |
    | its results are set never to be shown, and the learner's recorded status on it is Demonstrated | the "Available" oval, with no score        |

Scenario: A hidden subsection's tooltip says it isn't visible and shows no status
  Given a placeholder row under "Analysis" reads "1 more subsection that isn't visible to you"
  And the learner's recorded status on that subsection is Demonstrated
  When the learner hovers over that hidden subsection's segment
  Then the tooltip shows the assignment icon and "A subsection that isn't visible to you"
  And the tooltip shows no subsection name, no oval, and no score
  And the segment shows the Available icon at its center, matching how it is drawn

Scenario Outline: A tooltip shows no oval for a status the page doesn't recognize
  Given the platform returns a status for <item> that the page doesn't recognize, so the cards show no status for it and #747 draws its segment as Available
  When the learner hovers over <segment>
  Then the tooltip shows the segment's name with no oval
  And the segment shows the Available icon at its center, matching how it is drawn

  Examples:
    | item                                                  | segment                |
    | "Analysis", a tag row in the "Critical Thinking" card | the "Analysis" segment |
    | "Quiz 1", a subsection under "Analysis"               | the "Quiz 1" segment   |

Scenario: Every tooltip shows what the cards show, masking included
  Given "Final Exam", a subsection under "Root Cause Analysis", is set to show assessment results only once it is past due, and its due date hasn't passed
  And the learner's recorded status is Demonstrated on "Final Exam", and their competency status is Demonstrated for "Root Cause Analysis", "Problem Definition", and "Problem Solving"
  When the learner hovers over the "Final Exam", "Root Cause Analysis", "Problem Definition", and "Problem Solving" segments in turn
  Then each tooltip shows the "Available" oval, the same status the cards show for that subsection or tag
  And no tooltip says why the status reads Available

Scenario Outline: Course staff viewing a learner see tooltips that match that page's cards
  Given a learner in content group A, whose competency status is Demonstrated for "Communication"
  And "Group B Project", a subsection under "Communication", is restricted to content group B
  And the staff member has no competency statuses of their own
  When a member of course staff <view> and hovers over the "Group B Project" segment
  Then <tooltip>
  And hovering over the "Communication" segment shows the "Demonstrated" oval, as that page's card heading does

  Examples:
    | view                                                                          | tooltip                                                                                        |
    | opens that learner's progress page, for example from the instructor dashboard | the tooltip shows "Group B Project" by name with the "Available" oval, as that page's row does |
    | views the Progress tab masquerading as that learner                           | the tooltip reads "A subsection that isn't visible to you", with no oval                       |

Scenario: The sunburst stays one image to assistive technology
  Given a course with competency criteria
  When a screen reader user moves through the top of the panel, or a keyboard user presses Tab through the page
  Then the screen reader announces each sunburst once, as the image #747 describes
  And focus never stops on a segment
  And when a tooltip's text is read aloud, none of its icons is announced

Scenario Outline: The tooltip opens on the side that fits
  Given the learner's language reads <direction>
  When the learner hovers over a segment <where>
  Then the tooltip appears <side> of the point where the pointer entered the segment, fully within the screen

  Examples:
    | direction     | where                             | side         |
    | left to right | with room to its right            | to the right |
    | left to right | near the right edge of the screen | to the left  |
    | right to left | with room to its left             | to the left  |

Scenario: The tooltip fits a phone screen
  Given the learner is on a phone-sized touch screen
  When the learner taps a segment near the edge of the screen
  Then the whole tooltip appears within the screen
  And long tag and subsection names wrap inside the tooltip instead of being cut off
  And the page doesn't scroll horizontally
```

<details>
<summary>Technical Details</summary>

This is a suggested approach, not the source of truth. The User Story, Description, and Acceptance Criteria define what must be true when the work is done.

**Summary**

Each chart has one hover state, set by event delegation on #747's `<svg>`. That state drives three things: the highlight, the status icon drawn inside the active segment, and one controlled Paragon `Overlay` that shows a card beside the point where the pointer entered the segment. A pure function over #747's node tree builds each segment's card content, and one `SunburstTooltip` component renders that content as a competency variant or an assignment variant. Only the card's presentation (step 4) would change under the light-label design raised in Open Questions.

**Approach**

1. **Hover state.** `useSunburstHover(nodesById)` in `src/useSunburstHover.js` holds the active segment's id, the point where the pointer entered it, and a hide timer. It takes the `nodesById` index that #747's `Sunburst` builds from its node list, which is in reading order: each tag's own subsections first, then its child rows, as #747 step 1 defines. Each `Sunburst` calls it once, so hovering one chart never fades the other chart or the legend.
   - `onPointerOver` on the `<svg>`, from a mouse or pen, reads `event.target.closest('[data-segment-id]')`. On a new segment it cancels any pending hide, sets the active id, and records the entry point relative to the chart's wrapper. Moving within the segment changes nothing, so the card never follows the cursor; WCAG 1.4.13 requires this so that the pointer can reach the card.
   - Each 2px gap is drawn by the stroke of an adjacent path, so the browser counts the gap as part of that segment and crossing it switches segments directly.
   - `onPointerOut` to the center, off the chart, or onto the card starts a short hide delay. The card's `onPointerEnter` cancels the delay, so the pointer can move onto the card, and its `onPointerLeave` starts it again.
   - For a touch pointer, ignore pointer over and out, because a tap fires them in one burst.
     - `onPointerUp` from a touch pointer activates the tapped segment.
     - A tap on the segment that is already active keeps the card open.
     - A tap on the `<svg>` that is not on a `[data-segment-id]` path (the center hole or a gap-free area) closes the card, and so does a tap on the HTML center caption. A `pointerdown` listener on `document` closes the card when a tap lands outside both the chart wrapper and the card. Leave `Overlay`'s `rootClose` off, because it would treat a tap on another segment as a tap outside.
   - While a card is open, a `keydown` listener on `document` closes it on Escape. The card stays closed until the pointer enters a different segment or leaves the chart.
   - Treat a missing `pointerType`, as in jsdom's events, as a mouse.
2. **Highlight.** `litIds(nodesById, activeId)` in `src/data/sunburstTooltip.js` returns the active node, its `ancestorIds`, and its whole subtree. Every other path in the chart gets `data-dimmed` and a lower `fill-opacity`. Use `fill-opacity` rather than `opacity`, so lit segments keep the legend's colors and the gap strokes stay unchanged. Memoize the paths on the lit set, so they re-render only when the active segment changes.
3. **In-segment icon.** An element positioned at the active node's centroid, inside the chart wrapper, shows the icon for the segment's drawn status from #739's shared status map, so a hidden or unknown-status segment shows the Available icon. The icon has a fixed size, is centered on the segment, sits above any faded neighbors it overlaps, and is `aria-hidden` with `pointer-events: none`.
4. **Card.** `SunburstHoverCard` in `src/SunburstHoverCard.jsx` renders one Paragon `Overlay` per chart:
   - `show` while a segment is active;
   - `placement` right, or left in right-to-left locales;
   - `flip`;
   - `transition={false}`, because the timers own the timing;
   - as `target`, a zero-size `aria-hidden` `<span>` absolutely positioned at the entry point.

   Three details need care:
   - Key the span by the active id, and pass `Overlay` the element itself from a callback ref. Popper doesn't notice an anchor that moves, and `Overlay` doesn't re-read a ref object, but both pick up a new element.
   - Render a function child that puts a Paragon `Card` in the `ref` and `style` that `Overlay` passes. `Popover` would always render an arrow.
   - Keep the offset small, so the pointer can reach the card without crossing another segment.

   `Overlay`'s portal keeps the card outside the `role="img"` subtree. Confirm early, in a browser, that Popper positions correctly against the zero-size span.
5. **Name and status.** `buildSunburstTooltip(node, nodesById)` in `src/data/sunburstTooltip.js` returns one of three shapes, which `SunburstTooltip` in `src/SunburstTooltip.jsx` renders:
   - competency, for a tag node: the tag name from `source`, and `StatusOval` without a percent;
   - subsection, for a named row: the assignment icon, the subsection name (which wraps), and `StatusOval` with `percentGraded`, as the card row shows;
   - hidden, for a hidden criterion: the assignment icon and the sentence "A subsection that isn't visible to you", with no oval.

   Whether to show an oval, and a subsection's `percentGraded`, come from the node's `entry` (the raw #739 map entry that #747 attaches to each node): no oval when it is null, even though the segment is drawn as Available.
6. **Count and icon row.** The competency shape adds two fields:
   - `count`: the number of subsection nodes in the node's subtree, hidden ones included;
   - `iconStatuses`: each of those nodes' drawn status, in tree order, or null when the count is over 12. Tree order, laid out in the card's text direction, matches the order of the segments in both directions.

   The count is an ICU plural message. The count's icon and the icon row are `aria-hidden`.
7. **Rule line.** The competency shape's `rule` is set only when all of these hold:
   - the node has no tag children;
   - its tag has exactly one bottom-tier group;
   - that group holds exactly one rule box;
   - that rule box's rule is recognized.

   The rule is then the group's "all" or "any" (AND reads "all"; OR or null reads "any"), plus the rule's `op` and value, with the percent formatted as #734 does. Every other case reads "Multiple requirements".
   - Recognize the rule with the function in `src/ruleText.js` that `formatRuleText` and #755's `combineThreshold` use. Neither #734 nor #755 names it as a separate function, so extract it as `recognizeRule(rule)` in `src/ruleText.js`.
   - Do not reuse `combineThreshold` for the rule line. It reduces several "or better" rules to the highest value, which would overstate an ALL group with mixed scores.
   - The messages are six whole sentences ("all" or "any", times "or better", "or lower", and "exactly"), plus "Multiple requirements". Write them in sentence case and uppercase them with `text-uppercase`.
8. **Tests beyond the AC.**
   - Pure tests:
     - the rule line for all and any, the three comparison forms, two rule boxes, two groups, a heading with rows, a path row, and an unknown rule;
     - the count with hidden criteria;
     - exactly 12 versus 13 icons;
     - the lit set.
   - Render tests, with fake timers:
     - hovering a `[data-segment-id]`, and the lit and dimmed attributes;
     - moving onto the card, and the hide delay;
     - Escape, and what reopens the card afterward;
     - a tap, a tap on another segment, a tap on the same segment, and a tap outside.

Out of scope:
- keyboard navigation of the segments;
- competency statements and the "Needs revision" and "Awaiting evaluation" icons (#750);
- a fifth legend entry for hidden subsections.

If the hover design becomes a light label with the details in a fixed spot (the first Open Question), steps 1 and 4 change. In step 1, the hide timer gains a 250ms first-show delay and the onto-card handling applies to the fixed card instead. In step 4:
- the overlay shows only step 5's name and status, still anchored at the entry point;
- a 250ms delay comes before the first show;
- #747's center caption shows the active segment's name and status;
- `SunburstTooltip` renders in a reserved space under the chart.

Steps 2, 3, and 5 to 7 stay as they are.

**Files to create and modify**

Paths are relative to the root of the plugin repository from #810.

| File | Change |
| --- | --- |
| `src/useSunburstHover.js` | new |
| `src/SunburstHoverCard.jsx` | new |
| `src/SunburstTooltip.jsx` | new |
| `src/data/sunburstTooltip.js` | new: `litIds`, `buildSunburstTooltip` |
| `src/Sunburst.jsx` | modified: delegated pointer handlers, `data-dimmed`, the in-segment icon, the hover card |
| `src/ruleText.js` | modified: extract `recognizeRule` |
| `src/messages.js` | modified |

**Additional context**

- The three Figma frames linked under UX Design predate #768's Option G, so the hollow circle in the competency frame's icon row is the Available icon. The [Sunburst Explorer](https://d3v8e8hqzoulm1.cloudfront.net/axim/sunburst-explorer/) prototype, under "Summary with hover", shows the in-segment icon.
- Paragon's `Overlay` only adds default props to react-bootstrap's `Overlay` (`rootClose` false, `transition` Fade). `OverlayTrigger` can't keep a portaled card open while it is hovered, because its mouseout check looks only inside the trigger.
- #747's scenario "The sunburst doesn't respond to the pointer or to touch" describes the chart before this ticket; this ticket replaces that test with the hover and tap scenarios above.
- A jsx-a11y rule may flag the pointer handlers on the `<svg>` for having no keyboard handlers. Don't suppress it without approval. The segments stay unfocusable because every fact in the card is also text in the cards below.
- #752 should document:
  - the competency oval shows the learner's status across all courses (#740), while the count and icons are this course's, so "Demonstrated" can sit above Not Demonstrated icons;
  - a tooltip never says why a status reads Available;
  - hidden subsections are counted;
  - the icon row is left out above 12.

</details>

## Open Questions

- (architect, final review) Which hover presentation does this ticket build? The draft follows the #750 frames: the full card beside the point where the pointer entered the segment. On 2026-10-22 the designer proposed, from Paragon Working Group feedback, a light label by the pointer showing only the name and status, with the full details in a fixed spot (the chart's center and a card under the chart), plus a 250ms pause before the first tooltip appears. The content scenarios in the Acceptance Criteria hold under either design; the placement and interaction scenarios, Technical Details step 4, the #750 frames, and the Description's two lists of tooltip contents change under the light label. The architect recommends the full card plus the 250ms first-show pause: the fixed spot either pushes the second chart and the legend under the pointer or covers them, and its center slot disappears on charts under 320px.
- (architect, final review) Should this ticket be split? It is about 4 developer-days. The seam: part 1 is Technical Details steps 1 to 5 (hover, tap and Escape state, highlight, in-segment icon, the card, and both content variants with name and status, about 2.5 days), which the hover-presentation question blocks; part 2 is steps 6 and 7 (the assignment count with its plural, the 12-icon row, the rule line and the shared recognizer in `src/ruleText.js`, about 1.5 days), which is the same under either presentation. The companion ticket would need its own human-written sections and issue number, and the Description's count, rule, and icon bullets would move to it.
- (architect, final review) Does hovering one sunburst fade the other? The notes say the other chart and the legend never fade, and the draft follows that. The designer's 2026-10-22 comment lists "with two taxonomies, hovering one sunburst fades the other" under fixes to the prototype, which reads as the opposite. Confirm with the designer. Fading the other chart would move the active id up into `CompetencySunbursts`, about an hour of work.
- (architect, final review) After Escape closes the card, what reopens it? The draft keeps it closed until the pointer enters a different segment or leaves the chart and comes back, and the Acceptance Criteria say the same. The alternative is to reopen only after the pointer leaves the chart.
- (implementer) Should the tooltip stay on hand-rolled SVG with Paragon `Overlay`, or move to TanStack Charts 1.1, whose tooltip, keyboard navigation, and drill-in were the designer's reasons for the library? Ask Adolfo before implementation. If TanStack is chosen, its `anchor: 'pointer'` must capture the position when the pointer enters a segment rather than track it, or the card can't be hovered (WCAG 1.4.13). Recommended: hand-rolled SVG with `Overlay`, matching #747.
