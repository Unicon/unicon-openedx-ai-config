# [FE] Sunburst Tooltips

GitHub: https://github.com/openedx/openedx-core/issues/751 (#751, OPEN)
Cached: 2026-09-21

## User Story
As a learner, when I hover over or tap a segment of the sunburst, I want to see more information about what that segment represents in order to understand where I stand on it and what it takes to demonstrate it.

## Description
This ticket implements the tooltips and hover highlight for the sunburst built in #747. Hovering with a pointer or tapping a segment shows its tooltip beside that segment. Tapping another segment switches, and tapping outside or pressing Escape dismisses it. There are 2 cases of tooltips:

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

While a segment is hovered or tapped, its status icon is drawn inside the segment when the segment is wide enough to hold it. Also while a segment is hovered or tapped, there is a faded overlay for all the other segments in that sunburst except for this one, its ancestors, and its descendants, and when the page shows two sunbursts, the whole other sunburst fades too.

This ticket has five parts:
- The hover and tap state, including a brief pause before the first tooltip and a grace period so the pointer can reach the tooltip.
- The highlight, which fades the rest of the hovered sunburst and the whole other sunburst.
- The status icon drawn in the hovered segment, with a size rule for thin segments.
- The tooltip's positioning, which opens away from the sunburst's center and stays on screen on a phone.
- The tooltip's two content variants, including the assignment count, the requirement line, and the row of status icons.

## Context
- Corresponds to UXD Spike #750
- Blocked by #747

## UX Design

@illiphilli, please add the UX design screenshot(s) and the Figma link for this ticket. The three tooltip frames still need: the in-segment status icon (the 18px card icon with a 2px white ring and a light shadow) on the hovered segment; a Demonstrated assignment frame showing the percent in the oval; a phone frame; and the Option G Available icon in place of the hollow circle in the competency frame's icon row.

- Figma: TBD
  - [Competency tooltip](https://www.figma.com/design/VqDdtf3NOsUihle6SNS6Kw/-Course-Level----Student-Progress?node-id=1244-26891)
  - [Sub-competency tooltip](https://www.figma.com/design/VqDdtf3NOsUihle6SNS6Kw/-Course-Level----Student-Progress?node-id=1253-5600)
  - [Assignment tooltip](https://www.figma.com/design/VqDdtf3NOsUihle6SNS6Kw/-Course-Level----Student-Progress?node-id=1253-6531)
- Screenshots: TBD

## Acceptance Criteria

These scenarios use #734's terms (card heading, placeholder row), #739's terms (named row, oval), and #747's terms (segment, competency ring, subsection ring, "drawn as"), and these:

- A tag row is a row inside a card for a tag other than the card heading, shown with the target icon before its name. A tag row for a tag with criteria in this course has its groups and subsections under it; a tag row for a tag with no criteria of its own in this course has nothing beneath it.
- The tooltip is the card that appears beside a segment the learner hovers over or taps. A competency tooltip is the one for a card heading's or tag row's segment. An assignment tooltip is the one for a subsection segment.
- A hidden subsection's segment is the segment #747 draws for a subsection the card counts in a placeholder row.
- A segment's subtree is every segment beneath it, out to the subsection ring.
- While a segment is hovered or tapped, a segment is lit when it keeps its full color and faded when it is drawn paler.
- Unless a scenario says otherwise, the course's criteria use one taxonomy, the learner's statuses load, no status is masked, and the learner uses a mouse. The "Critical Thinking" card has tag rows "Analysis" and "Inference", "Quiz 3" appears under both, and the sunburst also has a "Communication" segment.

```gherkin
Scenario: The tooltip appears beside the hovered segment's center and stays there
  When the learner rests the pointer on the "Analysis" segment
  Then the tooltip for "Analysis" appears beside the "Analysis" segment's status icon, 20px from the icon
  And when the learner moves the pointer to another point inside the "Analysis" segment, the tooltip stays where it is instead of following the pointer
  And the tooltip appears in that same place whichever edge of the "Analysis" segment the pointer entered from

Scenario: The first tooltip waits for a short pause, and moving between segments switches at once
  Given no tooltip is showing
  When the learner moves the pointer onto the "Analysis" segment and keeps it there
  Then the tooltip for "Analysis", the highlight, and the status icon appear together after a brief pause, not the instant the pointer arrives
  And when the learner then moves the pointer onto the "Inference" segment, the tooltip for "Inference" replaces it with no pause

Scenario: Passing the pointer quickly across the sunburst shows nothing
  Given no tooltip is showing
  When the learner moves the pointer across the sunburst and off it again without resting on any segment
  Then no tooltip appears and no segment fades

Scenario Outline: The hovered segment, the segments above it, and its whole subtree stay lit
  When the learner hovers over <hovered>
  Then <lit> are lit, in exactly the colors the legend shows
  And every other segment in that sunburst fades, including <faded>

  Examples:
    | hovered                                 | lit                                                                                     | faded                                                                                         |
    | the "Critical Thinking" segment         | "Critical Thinking", "Analysis", "Inference", and every subsection segment beneath them | "Communication" and its subsection segments                                                   |
    | the "Analysis" segment                  | "Analysis", "Critical Thinking", and every subsection segment beneath "Analysis"        | "Inference", the "Quiz 3" segment beneath "Inference", and "Communication"                    |
    | the "Quiz 3" segment beneath "Analysis" | that "Quiz 3" segment, "Analysis", and "Critical Thinking"                              | the "Quiz 3" segment beneath "Inference" and the other subsection segments beneath "Analysis" |

Scenario: Hovering a segment in one sunburst fades the whole other sunburst, but never the legend
  Given a course with criteria on tags from "Workplace Skills" and "Accounting Standards", so two sunbursts appear
  When the learner hovers over a segment in the "Accounting Standards" sunburst
  Then the segments outside the hovered branch fade in the "Accounting Standards" sunburst
  And every segment in the "Workplace Skills" sunburst fades
  And every legend entry keeps its full color
  And only one tooltip shows on the page
  And when the learner then hovers over a segment in the "Workplace Skills" sunburst, its tooltip replaces the first one, and every segment in the "Accounting Standards" sunburst fades instead

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

Scenario Outline: The status icon appears only on a segment at least 22px long through its middle
  Given <segment> is <length> long, measured along the arc halfway between its inner and outer edges
  When the learner hovers over that segment
  Then <icon>
  And the segment is lit, and its tooltip appears beside the center of the segment and shows its status

  Examples:
    | segment                                                           | length            | icon                                                                             |
    | a subsection segment beneath "Analysis", which has 40 subsections | shorter than 22px | no status icon appears in or over the segment                                    |
    | the "Quiz 3" segment beneath "Analysis"                           | 22px or longer    | its status icon appears at its center, at the same size as on any other segment |

Scenario: Moving the pointer to a neighboring segment switches the tooltip and highlight
  Given the tooltip for "Analysis" is showing, and it doesn't cover the "Inference" segment
  When the learner moves the pointer directly onto the neighboring "Inference" segment, across the gap between them
  Then the tooltip for "Inference" replaces the one for "Analysis", without every segment returning to full color in between
  And the lit and faded segments, and the icon, change to follow "Inference"

Scenario Outline: The learner can move the pointer from a segment onto its tooltip without it closing or switching
  Given the tooltip for <segment> is showing
  When the learner moves the pointer from the center of that segment straight onto the tooltip, however slowly
  Then the tooltip and the highlight stay as they are the whole way, even where other segments lie between the segment and the tooltip
  And they stay as they are while the pointer is anywhere over the tooltip
  And when the pointer then leaves the tooltip for somewhere other than a segment, the tooltip closes and every segment returns to full color

  Examples:
    | segment                                                           |
    | the "Critical Thinking" segment, in the innermost ring            |
    | the "Quiz 3" segment beneath "Analysis", in the subsection ring   |
    | a subsection segment beneath "Analysis", which has 40 subsections |

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
    | no tooltip is showing                 | the "Analysis" segment                    | the tooltip for "Analysis" appears at once, with the same highlight and icon as when hovering |
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
    | "Problem Definition" | a tag row for a tag with no criteria of its own | Demonstrated | Demonstrated |

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
    | "Problem Definition" | a tag row with no criteria of its own, with "Root Cause Analysis" nested beneath it |

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
  And the segment shows the Available icon at its center

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
  And a tooltip read by assistive technology gives its text in order: the name, the status label, and for a competency tooltip the assignment count and the requirement line, with no icon and no icon row announced

Scenario Outline: The tooltip opens on the side of the segment away from the sunburst's center, unless it doesn't fit there
  Given the learner's language reads <direction>
  When the learner hovers over <segment>
  Then the tooltip appears <side> of the center of that segment, fully within the screen

  Examples:
    | direction     | segment                                                                              | side         |
    | left to right | a segment right of the sunburst's center                                             | to the right |
    | left to right | a segment left of the sunburst's center                                              | to the left  |
    | left to right | a segment right of the sunburst's center, with no room for the tooltip to its right | to the left  |
    | left to right | the only card heading's segment, which spans the whole circle                        | to the right |
    | right to left | a segment right of the sunburst's center                                             | to the right |
    | right to left | a segment left of the sunburst's center                                              | to the left  |
    | right to left | a segment left of the sunburst's center, with no room for the tooltip to its left   | to the right |
    | right to left | the only card heading's segment, which spans the whole circle                        | to the left  |

Scenario: The tooltip fits a phone screen
  Given the learner is on a phone-sized touch screen
  When the learner taps a segment near the edge of the screen
  Then the tooltip appears at once, floating over the page, and nothing on the page moves to make room for it
  And the whole tooltip is within the screen
  And the tooltip is 265px wide, or the screen's width minus 32px when that is narrower
  And long tag and subsection names wrap inside the tooltip instead of being cut off
  And the page doesn't scroll horizontally
```

<details>
<summary>Technical Details</summary>

This is a suggested approach, not the source of truth. The User Story, Description, and Acceptance Criteria define what must be true when the work is done.

**Summary**

One hover state for the page, held in `CompetencySunbursts` and set by event delegation on each chart's `<svg>`, drives three things: the highlight, which also fades the whole other chart; the status icon drawn at the active segment's centroid; and a controlled Paragon `Overlay` that shows the card 20px from that icon, on the side away from the chart's center. The first card waits for a 250ms pause, and later ones switch at once. A transparent strip on the card's near side and a short grace delay let the pointer move from the segment onto the card without the card switching or closing. A pure function over #747's node tree builds each segment's card content, and one `SunburstTooltip` component renders that content as a competency variant or an assignment variant.

**Approach**

1. **Hover state.** `useSunburstHover()` in `src/useSunburstHover.js` holds the page's one active segment, as a chart key and a segment id, along with whether a hover or a tap opened it, and at most one pending timer. `CompetencySunburstsContent` calls it once and passes the active segment and the handlers to each `Sunburst` with that chart's key, so both charts share one highlight and one card. A chart that doesn't hold the active segment fades every one of its segments (step 2), and the legend never fades.
   - `onPointerOver` on each chart's `<svg>`, from a mouse or pen, reads `event.target.closest('[data-segment-id]')`. Each 2px gap is drawn by the stroke of an adjacent path, so the browser counts the gap as part of that segment, and crossing a gap moves straight from one segment to the next.
   - While no card is showing, entering a segment starts a 250ms pause, the designer's delay before the first card. Entering another segment during the pause moves the pending target to that segment without restarting the 250ms, and leaving the segments cancels the pause. When the pause ends, the segment under the pointer becomes active, and its highlight, icon, and card appear together.
   - While a card is showing, entering a different segment, in either chart, makes that segment active at once. Moving within the active segment changes nothing, because the card is anchored to the segment (step 4), not to the pointer.
   - The card never closes while the pointer is over a segment or over the card. When the pointer leaves a segment or the card for anywhere else (the center hole, the center caption, the legend, or the page), start a 150ms grace delay. Entering any segment or the card cancels the delay. If it runs out, the card closes, and the next card waits for the pause again. The delay only has to cover the moment between leaving the segment and reaching the card, which step 4's strip makes nearly instant.
   - For a touch pointer, ignore pointer over and out, because a tap fires them in one burst. Taps use neither the pause nor the grace delay.
     - `onPointerUp` from a touch pointer activates the tapped segment at once.
     - A tap on the segment that is already active keeps the card open.
     - A `pointerdown` listener on `document` closes the card when the tap lands on neither a `[data-segment-id]` path nor the card. That covers the center hole, the center caption, the legend, and the rest of the page. Leave `Overlay`'s `rootClose` off, because it would treat a tap on another segment as a tap outside.
   - While a card is open, a `keydown` listener on `document` closes it on Escape and cancels any pending timer. The card stays closed until the pointer enters a different segment or leaves the chart.
   - Treat a missing `pointerType`, as in jsdom's events, as a mouse.
2. **Highlight.** `litIds(nodesById, activeId)` in `src/data/sunburstTooltip.js` returns the active node, its `ancestorIds`, and its whole subtree. Every other path in the chart gets `data-dimmed` and a `fill-opacity` of 0.2, the designer's 20% fade, and so does every path in a chart that doesn't hold the active segment. Use `fill-opacity` rather than `opacity`, so lit segments keep the legend's colors and the gap strokes stay unchanged. Memoize the paths on the lit set, so they re-render only when the active segment changes.
3. **In-segment icon.** While a chart holds the active segment, `Sunburst` renders one 22px `aria-hidden` box with `pointer-events: none`, absolutely positioned in the chart wrapper and centered on the active node's centroid. The box holds the in-segment icon and is also the card's anchor in step 4. Key it by the active id.
   - The box holds the 18px status icon that the cards show, from #739's shared status map, for the segment's drawn status, so a hidden or unknown-status segment shows the Available icon. The icon has a 2px white ring and a light shadow, and it sits above any faded segment it overlaps.
   - Draw the icon only when the segment is at least 22px long at the centroid's radius: the node's angle in radians times the centroid's distance from the chart's center. #747 puts the centroid halfway across the band the segment covers across its whole angle, so a tag with no rows, which reaches out to the subsection ring, is measured halfway across that wider band.
   - On a shorter segment the box stays but is empty, so the card sits in the same place whether or not the icon fits. The highlight and the card still show the segment's status.
4. **Card.** `SunburstHoverCard` in `src/SunburstHoverCard.jsx` renders one Paragon `Overlay` per chart:
   - `show` while that chart holds the active segment;
   - as `target`, step 3's box, passed as the element itself from a callback ref. Because the box is keyed by the active id, each segment gets a new element, which Popper and `Overlay` both pick up. Neither of them notices an anchor that moves, and `Overlay` doesn't re-read a ref object.
   - `placement` on the side of the box away from the chart's center: `right` when the centroid is right of the center, and `left` when it is left of it. A centroid within 1px of the vertical center line, such as the full-circle segment of a taxonomy's only card, uses the reading direction: `right`, or `left` in right-to-left locales. The centroid is already mirrored in right-to-left locales, so the rule needs no other right-to-left handling. Opening away from the center keeps the card off as much of the chart as possible, because the part of the chart under the card can't be hovered while the card shows.
   - `popperConfig` with a 20px offset from the box, the designer's gap; when the card doesn't fit on that side, Popper's flip modifier falls back to the opposite side, then above, then below; and `preventOverflow` on both axes with 16px of padding, so on a phone the card shifts to stay on screen even if it then covers the segment;
   - `transition={false}`, because step 1's timers own the timing.

   Three details need care:
   - Render a function child that puts a Paragon `Card` inside a wrapper `div` that takes the `ref` and `style` `Overlay` passes. `Popover` would always render an arrow. The card is 265px wide and never wider than `calc(100vw - 32px)`.
   - When a hover opened the card, give the wrapper a transparent `::before` strip on the side that faces the box, chosen from the final `placement` that `Overlay` passes to the function child, and reaching 31px back to the centroid: the 20px gap plus half the box. The browser counts the strip as part of the wrapper, so a pointer moving from the segment's center toward the card is over the card as soon as it leaves the segment, and the faded segments under the strip never take over. The strip is what lets an inner-ring segment's card meet WCAG 1.4.13. Leave the strip off a card that a tap opened, where it would swallow taps on the segments beneath it. Put the strip on the wrapper rather than on the `Card`, whose styles may clip overflow.
   - Confirm early, in a browser, that Popper positions correctly against the box. Under Paragon 23 (react-bootstrap 1.6), the function child does receive the placement after any such fallback, `popperConfig` passes straight through Paragon's `Overlay`, and nothing swaps `left` and `right` in a right-to-left layout, so those three need no check; re-verify them if the plugin pins a different Paragon major.

   `Overlay`'s portal keeps the card outside the `role="img"` subtree.
5. **Name and status.** `buildSunburstTooltip(node, nodesById)` in `src/data/sunburstTooltip.js` returns one of three shapes, which `SunburstTooltip` in `src/SunburstTooltip.jsx` renders:
   - competency, for a tag node: the tag name from `source`, and `StatusOval` without a percent;
   - subsection, for a named row: the assignment icon, the subsection name (which wraps), and `StatusOval` with `percentGraded`, as the card row shows;
   - hidden, for a criterion whose subsection is hidden from the learner: the assignment icon and the sentence "A subsection that isn't visible to you", with no oval.

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
8. **Tests beyond the AC.** These cover cases the Acceptance Criteria leave out or that QA can't set up by hand.
   - Pure tests for `buildSunburstTooltip`:
     - a card heading with criteria of its own and a row beneath it, for example "Problem Solving" whose own criteria are one group with one rule, with a "Problem Definition" row beneath it: the requirement line reads "MULTIPLE REQUIREMENTS" because the node has a tag child. This layout can exist only where a taxonomy re-import moved tags after criteria were created. #902 rejects that on re-import, and only a Django admin edit can still produce it, so QA can't stage it;
     - a status the page doesn't recognize, returned by the platform for "Analysis" (a tag row) or for "Quiz 1" (a subsection): the tooltip shows the name with no oval, and the segment shows the Available icon. QA can't produce an unrecognized status without mocking the response.
   - Pure test for the side rule: a centroid right of, left of, and on the center line, in both reading directions.
   - Render tests, with fake timers for the first-show pause and the pointer-out grace:
     - moving from an inner-ring segment onto its card, the grace delay, the 250ms pause and its retargeting to another segment, and the other chart's full fade;
     - Escape closes the card, and the card reopens only when the pointer enters a different segment or leaves the chart and comes back;
     - a tap, a tap on another segment, a tap on the same segment, and a tap outside, with a touch `pointerType`.
   - In a browser, not jsdom: Popper's positioning against the icon box, the strip, and the fallback sides, since jsdom has no layout.
9. **tutor-mfe pin.** Once a package release includes this ticket, open a pull request to `overhangio/tutor-mfe` that moves the pinned package version #828 adds to that release, and verify it on a Learning MFE image rebuilt from that branch. Until a tutor-mfe release includes that pull request, Tutor sites show the sunbursts without hover or tap behavior.

Out of scope:
- keyboard navigation of the segments;
- competency statements and the "Needs revision" and "Awaiting evaluation" icons (#750);
- a fifth legend entry for hidden subsections.

**Files to create and modify**

Paths are relative to the root of the plugin repository from #810.

| File | Change |
| --- | --- |
| `src/useSunburstHover.js` | new |
| `src/SunburstHoverCard.jsx` | new |
| `src/SunburstTooltip.jsx` | new |
| `src/data/sunburstTooltip.js` | new: `litIds`, `buildSunburstTooltip` |
| `src/Sunburst.jsx` | modified: delegated pointer handlers, `data-dimmed`, the icon box, the hover card |
| `src/CompetencySunbursts.jsx` | modified: calls `useSunburstHover` once and passes the active segment and handlers to each `Sunburst` |
| `src/ruleText.js` | modified: extract `recognizeRule` |
| `src/messages.js` | modified |
| `tutormfe/plugin.py` in `overhangio/tutor-mfe` | modified: wherever #828 declares the package's pinned version, most likely this file, otherwise `tutormfe/templates/mfe/build/mfe/Dockerfile` |

**Additional context**

- Design decisions: the designer's [2026-10-23 answers on #750](https://github.com/openedx/openedx-core/issues/750#issuecomment-6354761729) set the anchoring, card width, fade, in-segment icon, and thin-segment rule used above. Its light-label proposal from the Paragon Working Group was not adopted; the full card stays beside the segment, de-jittered by anchoring it to the segment and by the first-show pause.
- The three Figma frames linked under UX Design predate #768's Option G, so the hollow circle in the competency frame's icon row is the Available icon. The [Sunburst Explorer](https://d3v8e8hqzoulm1.cloudfront.net/axim/sunburst-explorer/) prototype, under "Summary with hover", shows the in-segment icon.
- Paragon's `Overlay` only adds default props to react-bootstrap's `Overlay` (`rootClose` false, `transition` Fade). `OverlayTrigger` can't keep a portaled card open while it is hovered, because its mouseout check looks only inside the trigger.
- A jsx-a11y rule may flag the pointer handlers on the `<svg>` for having no keyboard handlers. Don't suppress it without approval. The segments stay unfocusable because every fact in the card is also text in the cards below.
- #752 should document:
  - the competency oval shows the learner's status across all courses (#740), while the count and icons are this course's, so "Demonstrated" can sit above Not Demonstrated icons;
  - a tooltip never says why a status reads Available;
  - hidden subsections are counted;
  - the icon row is left out above 12.

</details>
