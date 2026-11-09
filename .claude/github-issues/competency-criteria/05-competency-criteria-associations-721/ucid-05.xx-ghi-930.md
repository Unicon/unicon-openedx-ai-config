# [FE] Resizable divider between the associations and content panels on the Competency Management page

GitHub: https://github.com/openedx/openedx-core/issues/930 (#930, DRAFT)
Cached: 2026-11-06

**Blocked by:** https://github.com/openedx/openedx-core/issues/670 (creates the two panels this divider sits between) and https://github.com/openedx/openedx-core/issues/672 (fills the associations panel).

## User Story

As a course author, I want to move the bar between the associations panel and the content panel up or down, in order to give more room to whichever panel I am working in so that I can see more information in one panel or the other without scrolling.

## Description

The Competency Management page stacks two panels on its right side: the associations panel, labeled "Competency Criteria Associations," above the content panel, labeled "Courses & Content." We need to add the horizontal bar between them (named ResizeBar in the Figma design) so an author can drag it, or use the keyboard, to make one panel taller and the other shorter by the same amount. The two panels together always fill the height of the larger panel area on the right, each panel scrolls on its own when its content is taller than its space, and neither panel can be resized below a minimum height, so neither disappears. The panels start at an even 50/50 split, and the chosen split is remembered across page visits.

## Context

- https://github.com/openedx/openedx-core/issues/670 creates the page, the associations panel, and the content panel that this bar separates.
- Figma: the design component is named ResizeBar.
- The bar works on every screen size the page is designed for, not only desktop.

## UX Design

@illiphilli, please add the UX design screenshot(s) and the Figma link for this ticket.

- Figma: https://www.figma.com/design/VhAdaucNQS49x0Afp9xPZw/Competency-Application?node-id=3231-57561&t=CfkfvjdmVvKlEpAH-1
- Screenshots: TBD

## Acceptance Criteria

```
Scenario: The panels start at an even split
  Given I open the Competency Management page and have never resized the panels
  When the page finishes loading
  Then the associations panel and the content panel are the same height
  And together the two panels and the bar between them fill the height the panel area has

Scenario: Drag the bar up to give the content panel more room
  Given the panels are at their starting split
  When I press on the bar, drag it upward, and release
  Then the associations panel becomes shorter and the content panel becomes taller by the same amount
  And the bar stays under the pointer while I drag

Scenario: Drag the bar down to give the associations panel more room
  Given the panels are at their starting split
  When I press on the bar, drag it downward, and release
  Then the associations panel becomes taller and the content panel becomes shorter by the same amount

Scenario: Resize the panels with the keyboard
  Given the bar has keyboard focus
  When I press the up arrow key
  Then the associations panel becomes shorter and the content panel becomes taller
  When I press the down arrow key
  Then the associations panel becomes taller and the content panel becomes shorter

Scenario: The bar can be reached and understood without a mouse
  Given I move through the page with the Tab key
  When focus reaches the bar
  Then the bar shows a visible focus indicator
  And a screen reader announces it as a resizable divider between the two panels, along with its current position

Scenario: Neither panel can be dragged shut
  Given the associations panel is already at its minimum height
  When I drag the bar further up, or press the up arrow key
  Then the associations panel stays at its minimum height and the content panel stays at its own height
  And the same holds for the content panel and the down direction

Scenario: A panel scrolls inside its own space
  Given a panel holds more content than fits at its current height
  When I look at that panel
  Then its content scrolls inside the panel
  And moving the bar does not change the combined height of the two panels

Scenario: The bar works on touch screens and at every supported screen size
  Given I am using a touch screen, or any screen size the page is designed for
  When I drag the bar with my finger, or use the keyboard
  Then the panels resize the same way as with a mouse
  And no part of the bar is hidden or unreachable

Scenario: The chosen split is remembered
  Given I have moved the bar away from the starting split
  When I leave the page and open it again, or reload it, in the same browser
  Then the panels open at the split I chose

Scenario: One remembered split applies to every competency
  Given I have moved the bar away from the starting split while viewing one competency
  When I select a different competency
  Then the panels keep the same split

Scenario: The remembered split cannot be read
  Given the browser blocks storage, or the remembered value is damaged or out of range
  When I open the page
  Then the page loads without an error and the panels start at the even split
  And I can still resize the panels for the rest of the visit
```

<details>
<summary>Technical Details</summary>

This is a suggested approach, not the source of truth. The User Story, Description, and Acceptance Criteria define what must be true when the work is done.

**Approach**

1. Add a vertical split component beside `ResizableBox` in `src/generic/resizable/`. It renders a top slot, the bar, and a bottom slot in a flex column that fills its parent. `ResizableBox` only resizes a width with mouse events, so it cannot be reused as is. Reuse its pattern of clamping the preferred value on render.
2. State is the top panel's share of the available height, a fraction in the range 0 to 1. Clamp it on every render so each panel keeps at least a minimum height (a constant of about 120px, the implementer's choice), measured against the container's current height.
3. Drag with Pointer Events (`onPointerDown`, then `setPointerCapture`, `pointermove`, `pointerup`) so mouse and touch share one code path and the drag continues when the pointer leaves the bar. Set `touch-action: none` on the bar so a touch drag does not scroll the page. Commit the value to storage on release, not on every move.
4. Make the bar a focusable element with `role="separator"`, `aria-orientation="horizontal"`, `aria-valuenow`, `aria-valuemin`, `aria-valuemax`, and an `aria-label`, following the WAI-ARIA window splitter pattern. Up and down arrows change the split by a fixed step. Add the visible focus style. Strings go in `messages.ts` through `defineMessages`.
5. Persist with `useStickyState` from `src/hooks.ts`, under one key not tied to a competency. That hook calls `localStorage.getItem` and `JSON.parse` without a guard, so a blocked store or a corrupt value throws on first render. Wrap the read and write in a guard, or add a safe variant, and validate that the stored value is a finite number between 0 and 1.
6. Keep the panel area's height as it is today, set by `--competency-panel-height` in `CompetencyAssociationsPanel.scss`. The split fills that height. Give each slot `min-height: 0` and `overflow: auto` so each panel scrolls internally. Cover the mobile layout too, where the page stacks its columns in a `Row`; confirm what height the split gets there.
7. Style with Paragon tokens, and take the bar's look from the Figma component named ResizeBar. If the design needs a value no token supplies, flag it before implementation.

Test cases the implementation must cover:
- Pointer drag and arrow keys change the split in the right direction by the same amount for both panels.
- The split clamps at each panel's minimum height, through both the drag and the keyboard paths.
- The split is read from storage on mount and written on release.
- Missing, unparsable, non-numeric, and out-of-range stored values fall back to 0.5.
- A throwing `localStorage` does not break rendering.
- The separator exposes the ARIA role, orientation, and value attributes.

**Files to create and modify**

| File | Change |
| --- | --- |
| src/generic/resizable/ResizableSplit.tsx | new: vertical split with the bar, drag, keyboard, and clamping |
| src/generic/resizable/ResizableSplit.test.tsx | new: tests for the cases above |
| src/generic/resizable/index.scss | modified: bar and focus styles |
| src/hooks.ts | modified: guard `useStickyState` against unavailable or invalid storage |
| src/taxonomy/competency-management/ (page and panel components from the panels tickets) | modified: place the two panels inside the split |

**Additional context**

- `src/generic/resizable/Resizable.tsx`: the existing horizontal `ResizableBox`, the precedent for clamping and the drag handle.
- `src/taxonomy/competency-management/associations/CompetencyAssociationsPanel.scss`: defines `--competency-panel-height`, the fixed height the split fills.

</details>
