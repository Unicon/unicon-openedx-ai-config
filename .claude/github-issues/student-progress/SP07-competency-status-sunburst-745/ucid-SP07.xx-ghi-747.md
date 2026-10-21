# [FE] Static Competency Status Sunburst

GitHub: https://github.com/openedx/openedx-core/issues/747 (#747, OPEN)
Cached: 2026-09-21

## User Story
As a learner, I want a way to visually see how the subsection assignments and subcompetencies in my course stack to parent competencies that I can demonstrate in order to understand what is needed from me in the course and how my work in this course inter-relates.

## Description
Above the competency status cards in the primary pane of the Progress page, we want to add a sunburst and its legend.

Sunburst:
- The center of the sunburst should say "COMPETENCIES DEMONSTRATED".
- The rings of the sunburst should correspond to how the competency status cards are laid out in #734 so that the innermost rings correspond to the tags for the title of each card, and the subsequent levels of rings correspond to the subcompetencies displayed within those cards at their corresponding level in the hierarchy.
- The outermost ring of the sunburst is for the subsection assignments, and it is thinner than the comepetency tag hierarchy levels.

Legend:
- Demonstrated has a green checkmark and segments of the sunburst for demonstrated competencies and subsections should be the same green color as the icon.
- Available has a dotted circle with a light blue/gray color and the segments of the suburst for available competencies and subsections should be the same color as the icon.
- Partially attempted has a blue half circle icon and the segments of the sunburst for "Partially Attempted" competencies should be the same color as the icon.
- Not Demonstrated is red with a minus sign and the segments of the sunburst for "Not Demonstrated" subsections should be the same colora s the icon.

## Context
- Implements the UXD Spike #769
- The tooltip is out of scope for this ticket because it will be built in #751

## Notes for drafting

- Status sources: competency segments (card headings, rows, and path rows) read #740's per-tag masked statuses; subsection segments read #739's per-criterion masked statuses. Both come through #739's shared hook, which applies the masking rule, so the chart can never reveal what the cards hide. Hidden placeholder subsections have no status by design in #739.
- Status colors and icons are Option G from #768 (Phil, 2026-10-08, approved on the Axim/Unicon sync): Available slate with a dashed ring `#CBD5E1`, Demonstrated `#3FA36F`, Partially Attempted `#0A67A3`, Not Demonstrated `#741420`. Three of these are not in Paragon yet. #739 and #740 still describe Available as an empty circle in blue/white and need updating to Option G. The sunburst is the third renderer of these colors after #739's ovals and #740's pills, so one shared status map should feed all of them plus the legend; the AC does not restate colors.
- Competencies are never Not Demonstrated: ADR 0002 excludes that status at competency level and #740 shows only Available, Partially Attempted, and Demonstrated on headings and rows. Red applies to subsection segments only. A subsection segment can be Partially Attempted (inferred from #739's Technical Details; its Description lists only three subsection states).
- Phil's #769 questions, as answered for MVP on 2026-10-21: (1) summary only, no explorer; (2) the inner ring starts at the card headings; (3) no ring cap; (4) equal share of the parent's angle; (5) no display limit; (6) one sunburst per taxonomy. #769 is still open; these answers should go back to it and mock 2 needs redrawing (see below).

### Decisions from the pre-handoff check (2026-10-21)

- Rings follow #734's card layout exactly. Ring 1 is the card headings; each further ring is one nesting depth of rows inside the card, including the ancestor case's path rows; the outermost thin ring is the subsections. Breadcrumb ancestors are not drawn. Under this rule a taxonomy with criteria only at level 6 gives two competency rings, "Level 5" and "Level 6", and more than two competency rings arises only when one course has criteria on a tag and on a descendant of it, which #666 blocks except through a taxonomy re-import. Mock 2 is drawn from the top of the taxonomy and needs redrawing by @illiphilli.
- #734 is to be changed so that a tag that would head one card and also appear in another card's breadcrumb merges the two into one card headed by the shallower tag, with the deeper card's heading becoming a path row (for example one "Problem Solving" card holding a "Strategy Selection" row and a "Problem Definition" path row with "Root Cause Analysis" nested under it). This keeps the sunburst, the cards, and #743's Focus Areas in parity and draws Problem Definition inside Problem Solving. #734's scenario "One tag can head one card and appear in another card's breadcrumb" is rewritten accordingly. This case is reachable in normal authoring (cousin tags), unlike the ancestor case.
- Static means no hover, focus, click, tooltip, drill-in, or animation. Segments are not in the tab order and the chart is one image to assistive technology. Tooltips and the faded overlay belong to Epic SP8 (#749, built in #751).
- Loading and failure: the chart renders nothing until #739's statuses have loaded, and stays hidden if they fail; the cards still render per #734's own rule. This departs from #743's "structure without statuses" decision on purpose, because the chart's only content is status color. Consequence for the AC: the chart appears after the slowest request, so the cards shift down when it lands.
- Taxonomies: one sunburst per taxonomy, all of them rendered above all the cards (not inside each taxonomy section). A course using three or more taxonomies renders no sunbursts at all, as a temporary rule until Phil answers what the layout should be. Each sunburst's legend sits with it.
- Mixed depth: a competency with no rows beneath it extends its segment outward through the unused ring positions to the subsection ring, so every subsection segment sits in the one shared outer ring. With hand-rolled SVG this is one conditional on the segment's outer radius; a chart library would need two marks or a custom layout for it.
- Hidden subsections: one neutral segment per hidden criterion, in a style distinct from Available, with a fifth legend entry. Phil designs the style and the legend entry; the architect prefers this over leaving them out because transparency to learners is a CBE tenet.
- Sizing: each child gets an equal share of its parent's angle at every level. A competency with many subsections therefore gets thin outer segments.
- Drawing: Technical Details recommend hand-rolled SVG with no new runtime dependency (each segment is one path of two arcs and two lines, Paragon color tokens applied by CSS class), with the data step kept library-independent so a later drill-in could swap only the drawing component. Record one Open Question labeled (implementer): hand-rolled SVG versus TanStack Charts 1.1, tagging Adolfo for an opinion before implementation. Facts gathered 2026-10-21: TanStack Charts is MIT, 1.1.0 shipped 2026-10-09 with a stable-API claim, supports React 18 and 19, its sunburst has `rootId`, `visibleDepth`, `ringPadding`, and `strokeWidth`, keyboard navigation and an image role with required `ariaLabel` are built in, it depends on a dozen d3 packages, bundle size unconfirmed, and the repo is under three months old. Phil's reasons for it (drill-in, keyboard navigation, custom tooltip) all serve later tickets; SVG covers MVP and SP8's tooltip and overlay with Paragon `OverlayTrigger` and an opacity change.
- Mounting: inside #734's `CompetencyProgressPanel`, above the taxonomy sections, so it inherits the panel's ready check and #839's placement handling with no new slot registration. Wrap the chart in its own error boundary, as #755 does for its notice, so a chart crash cannot hide the cards.
- Data: a pure function over `useCompetencyCards`' output (per taxonomy section) and `useCompetencyStatuses`' two maps, in one new data file. No new request or hook. One segment per criterion, so a subsection under two competencies appears once under each with that criterion's own status. Group and rule-box structure is not drawn; a tag's subsections are flattened in the order the card shows them.
- Order: clockwise from 12 o'clock in the cards' reading order (cards in #733's order, rows in card order, subsections by group, rule line, then outline position, hidden ones last), mirrored in right-to-left languages.
- Labels and center: no labels on segments. The center shows the fixed caption "COMPETENCIES DEMONSTRATED" in every state unless the Figma shows a count; Claude did not check the Figma.
- Legend: always lists all four statuses (five with the hidden-subsection entry) in the Description's order, as real text with icons hidden from screen readers.
- Accessibility: the SVG has `role="img"` and a short text alternative saying what the chart is and that the cards below list every competency and status. Segments are not focusable. WCAG 1.4.1 is met by the cards carrying the same information as text. Risk noted by both experts: the light Available fill next to white gaps may fall short of 3:1 (WCAG 1.4.11); defensible while the cards carry the information, but Phil should check it.
- Small screens: the SVG scales to the main column's width between a minimum and maximum diameter, the legend wraps, nothing scrolls sideways. Phil sets the sizes. Gaps between segments use the card background token, not literal white.
- Staff viewing a learner: one scenario mirroring #740's staff masking rule.
- Tests: pure-function tests on the node tree and angles, plus render tests asserting each ring's segment count and a `data-status` attribute per segment; no snapshots of path strings. Fixtures: #734's example course, the ancestor case, a tag whose subsections are all hidden, a subsection under two competencies, a two-taxonomy course, a three-taxonomy course.
- #748 docs should cover: what the rings follow, the status colors, masking making tags read Available, statuses spanning courses, the missing labels and tooltips until SP8, the three-or-more-taxonomies rule, and headings reading Available until #643 ships.
- Unverified by Claude: the Figma sunburst frames (center count, ring-width ratios, legend placement, start angle), Phil's Sunburst Explorer prototype, and whether #733 can return criteria on something that is not a subsection (the course's final grade); #734 is silent on that and the outer ring would need a rule for it.
