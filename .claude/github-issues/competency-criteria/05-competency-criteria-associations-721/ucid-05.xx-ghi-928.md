# [FE] Show the full subsection name in a tooltip on a truncated criterion chip

GitHub: https://github.com/openedx/openedx-core/issues/928 (#928, OPEN)
Cached: 2026-11-04

## User Story
As a course author, I want to see the full subsection name when it's cut off in a criterion chip, so I can easily identify which subsection is associated with a competency criterion.

## Description
On the Competency Management page, subsection names appear as chips within a Competency Criteria Group. When a subsection name is too long to fit, the text is truncated with an ellipsis (...), making it difficult to identify the subsection.

A tooltip should display the full subsection name when the text is truncated. The tooltip should appear when hovering over the chip or navigating to it using the keyboard.

Only the subsection name should appear in the tooltip. The course name is not needed because the chip is already displayed within its associated course group.

The tooltip should use the existing Paragon component to maintain consistency with other tooltips on the Competency Management page.

## Context
- Follow-up from openedx/frontend-app-authoring#3321, item 5 of its routing comment. That issue closes as superseded once this ticket is posted.
- Sequenced after #710, which adds the ✕ to the same chip. #826 also edits the chip, in the PR stacked on #710's.
- #672 builds the chip and the Selected Content list it sits in.
- Design: Figma, CBE Stories section 5, row 2, frames [14](https://www.figma.com/design/VhAdaucNQS49x0Afp9xPZw/Competency-Application?node-id=3329-44821), [15](https://www.figma.com/design/VhAdaucNQS49x0Afp9xPZw/Competency-Application?node-id=3329-44893), [16](https://www.figma.com/design/VhAdaucNQS49x0Afp9xPZw/Competency-Application?node-id=3329-44965), and [17](https://www.figma.com/design/VhAdaucNQS49x0Afp9xPZw/Competency-Application?node-id=3329-45037).

## UX Design

@illiphilli, please add the UX design screenshot(s) and the Figma link for this ticket.

- Figma: TBD
- Screenshots: TBD

## Acceptance Criteria

```
Scenario Outline: Display the full subsection name in a tooltip
  Given a criterion chip in a Competency Criteria Group has a subsection name that is truncated with an ellipsis
  When <action>
  Then a tooltip appears below the chip
    And the tooltip displays the full subsection name without the course name

  Examples:
    | action                                                       |
    | the pointer hovers over the chip's name                      |
    | the pointer hovers over the chip's remove (✕) button         |
    | keyboard focus moves to the remove (✕) button                |
    | keyboard focus moves to a read-only chip without a ✕ button |


Scenario Outline: Close the tooltip using Esc
  Given a criterion chip's tooltip is open after <action>
  When Esc is pressed
  Then the tooltip closes
    And keyboard focus remains in its current position
    And the criterion association is not removed

  Examples:
    | action                                               |
    | hovering over the chip                               |
    | moving keyboard focus to the remove (✕) button       |
    | moving keyboard focus to a read-only chip            |


Scenario: Keep the tooltip open while hovering over it
  Given a criterion chip's tooltip is open
  When the pointer moves from the chip onto the tooltip
  Then the tooltip remains open


Scenario: Close the tooltip when the pointer moves away
  Given a criterion chip's tooltip is open
  When the pointer moves away from both the chip and tooltip
  Then the tooltip closes


Scenario: Close the tooltip when keyboard focus moves away
  Given a criterion chip's tooltip is open
  When keyboard focus moves to another element on the page
  Then the tooltip closes


Scenario: Do not display a tooltip when the full name is visible
  Given a criterion chip displays the full subsection name without truncation
  When the pointer hovers over the chip or keyboard focus moves to the chip or its remove (✕) button
  Then no tooltip appears


Scenario: Announce the full subsection name for screen readers
  Given a criterion chip has a truncated subsection name
  When a screen reader reaches the chip's remove (✕) button
  Then the screen reader announces that the button removes the association with the full subsection name


Scenario: Support keyboard navigation for read-only chips
  Given a course cannot be edited
    And the criterion chips do not have remove (✕) buttons
  When navigating through the Competency Criteria Group using the Tab key
  Then each chip receives keyboard focus once, even if its name is not truncated
    And the screen reader announces each chip's full subsection name


Scenario: Hide the tooltip while a criterion association is being removed
  Given a criterion chip's tooltip is open
  When removal of the criterion association begins
  Then the tooltip closes
    And the tooltip cannot reopen while removal is in progress


Scenario: Handle the tooltip after a removal attempt
  Given removal of a criterion association is in progress
  When the removal succeeds
  Then the chip and its tooltip are no longer displayed

  When the removal fails
  Then the chip is displayed again
    And the tooltip works normally when hovering over the chip or focusing its remove (✕) button


Scenario: Display a tooltip for unavailable content
  Given a criterion chip displays "Content unavailable" instead of a subsection name
  When the pointer hovers over the chip or keyboard focus moves to the chip or its remove (✕) button
  Then a tooltip appears only if "Content unavailable" is truncated
    And the tooltip displays only "Content unavailable"
    And no course name or internal content identifier is displayed
```

<details>
<summary>Technical Details</summary>

This is a suggested approach, not the source of truth. The User Story, Description, and Acceptance Criteria define what must be true when the work is done.

**Summary**

The chip reuses `useCompetencyTooltip`, the hook that opens the competency tree's and the course search's tooltips only when their text is truncated, and composes its own Paragon `Overlay` and `Tooltip` below the chip. The hook gets one change: keyboard focus on a child element, here the chip's ✕, counts as focus on the trigger. `CriterionChipProps` and the chip's callers stay as they are.

**Approach**

1. In `useCompetencyTooltip.ts`, make `openOnFocus` test `:focus-visible` on `event.target` instead of `event.currentTarget`. The chip's focus handler sits on the Chip root `div`, but keyboard focus lands on Paragon's internal ✕ `IconButton`, and the root itself never matches `:focus-visible`, so with the current check the tooltip would never open from the keyboard. The hook's two existing callers, `CompetencyTreeItem.tsx` and `CourseSearchBrowse.tsx`, take focus on the trigger element itself, so for them the target and the current target are the same element.
2. In `CriterionChip.tsx`, pass a ref to `Chip`, which forwards it to its root `div`, and call `useCompetencyTooltip`, imported from `@src/taxonomy/competency-management/competency-tooltip`. Its `isTruncated` callback checks `scrollWidth > clientWidth` on `chipRef.current?.querySelector('.pgn__chip__label')`: the label clips its own text, so the root never overflows and the label is the element to measure. `criteria-groups.scss` already targets the `.pgn__chip__label` class.
3. Pass `onMouseEnter={openOnHover}`, `onMouseLeave={close}`, `onFocus={openOnFocus}`, and `onBlur={close}` to `Chip`, which puts them on its root `div`. Hovering anywhere on the chip, ✕ included, opens the tooltip, and focus on the ✕ bubbles up to the root.
4. When there is no `onRemove`, the viewer is read-only and the chip has no ✕. In that case pass `tabIndex={0}` to `Chip`, so the chip itself becomes a tab stop and focusing it opens the same tooltip. `Chip` applies a passed `tabIndex` to its root, and adds none of its own because no `onClick` is passed.
5. Compose Paragon `Overlay` and `Tooltip` the way `CompetencyTooltip.tsx` sets them up:
   - `target` from the chip ref;
   - `rootClose`, with the hook's `close` as `onHide`, so Esc closes the tooltip whether hover or focus opened it;
   - an `id` from `useId()`;
   - no `aria-describedby`, because the ✕'s accessible name already carries the full name.

   Set `placement="bottom"` with `flip`. Leave `variant` unset: dark is Paragon's default, and `variant="dark"` is a type error.
6. Render the `Overlay` as a child of `Chip`. The tooltip is portaled, but as a React child it counts as part of the chip for mouse enter and leave, so the pointer can move onto the tooltip without the tooltip closing.
7. Set the `Overlay`'s `show` to `tooltipProps.show && !disabled`, so no tooltip shows while a delete is in flight.
8. The tooltip body is `displayName`, including the "Content unavailable" fallback, so the fallback follows the same truncation rule as any other label and `messages.ts` needs no new message.
9. Tests cover these cases:
   - an untruncated name opens nothing;
   - hovering the label, and hovering the ✕, each open the tooltip;
   - Tab to the ✕ opens it;
   - Tab to a read-only chip opens it;
   - moving the pointer onto the tooltip keeps it open;
   - Esc closes a tooltip opened by hover;
   - a disabled chip shows none.
10. Branch from the top of the open stack (AShatsila/frontend-app-authoring#7 through #11), or from `master` once that stack merges. AShatsila/frontend-app-authoring#8 (#826) also edits `CriterionChip.tsx`, so a base below it conflicts on that file.
11. Out of scope:
    - the ✕'s accessible name and its remove behavior (#710);
    - the usage-key tooltip on the "Content unavailable" chip, which #826 leaves to a follow-up;
    - touch-screen behavior.

**Files to create and modify**

| File | Change |
| --- | --- |
| src/taxonomy/competency-management/competency-tooltip/useCompetencyTooltip.ts | modified |
| src/taxonomy/competency-management/criteria-groups/CriterionChip.tsx | modified |
| src/taxonomy/competency-management/criteria-groups/CriterionChip.test.tsx | modified |

**Additional context**

- `src/taxonomy/competency-management/CompetencyTreeItem.tsx` is the prior art for how a caller wires the hook, and `src/taxonomy/competency-management/competency-tooltip/CompetencyTooltip.tsx` for the `Overlay` setup.
- The truncation stubs to copy are in `CompetencyTree.test.tsx`, which uses `jest.spyOn(Element.prototype, 'scrollWidth', 'get')`. The Esc keypress to copy is in `CompetencyTooltip.test.tsx`, which uses `fireEvent.keyUp(document, { key: 'Escape', keyCode: 27 })`.
- Paragon reuse check: Paragon's `Overlay` and `Tooltip` cover this tooltip, so it needs no custom markup or CSS. `OverlayTrigger` is deliberately left out; the comment in `useCompetencyTooltip.ts` explains that it cannot keep a portaled tooltip open while the pointer is on it.

</details>

## Open Questions

- (architect, final review) A chip the viewer cannot edit has no ✕, so this ticket makes the chip itself a tab stop that opens the same tooltip. Phil's frames 14 to 17 name only the ✕ as the keyboard trigger. Confirm with Phil that the read-only chip as a tab stop is the intended design, or choose hover-only for read-only chips.

## Notes for drafting

The title, User Story, Description, and Context above were drafted by Claude from the openedx/frontend-app-authoring#3321 thread at Tammie's request on 2026-11-04. They need a human rewrite before posting.

Requirement as Mary stated it on 2026-10-22: when a criterion chip's subsection name is cut off with an ellipsis, hovering or keyboard-focusing the chip shows a tooltip with the full subsection name. The tooltip does not need the course name, because the chip already sits inside the course-level group for its course, so the course name is visible on screen.

Design decisions as Phil stated them on 2026-10-30:
- Tooltip shows only when the chip's name is cut off, and holds the full subsection name only.
- Opens on hover and on keyboard focus of the chip's ✕. Esc closes it.
- The ✕'s accessible name carries the full name, so screen readers get it either way.
- Paragon `Tooltip` (dark), below the chip. Sequence after #710, which also edits the chip.

Decisions from the draft pass (Tammie, 2026-11-04):
- A chip without a ✕ (the viewer cannot edit the course) is itself a keyboard tab stop, always, and focusing it opens the same tooltip. Mary and Phil still need to confirm this, since Phil's frames name only the ✕.
- Hovering anywhere on the chip, ✕ included, opens the tooltip.
- No tooltip while a removal is in progress; it works again if the removal fails.
- Touch screens are out of scope, stated in Technical Details.
- The "Content unavailable" chip follows the same rule as any label.

Verified on 2026-11-04 (code on the #710 PR head and on master):
- The ✕'s accessible name already carries the full subsection name at the #710 PR head, so that part of Phil's design is reuse.
- Paragon's Tooltip has no dark variant to set; dark is the default. Placement must be set to bottom, since the default is right.
- The page's existing truncation tooltip hook already closes on Esc and stays open under the pointer. It tests focus visibility on the element carrying the handler, so it needs a one-line change for focus on the inner ✕ to count.
- The Browse Courses panel's pill shows the competency ID, and the subsection name beside it wraps, so there is no second chip to cover.

Related:
- #868 (closed) fixed overflow of long competency names and Competency ID badges on the same page; it did not touch the criterion chip.
- The same-named-subsections-from-different-courses case was ruled out by Mary: #672 nests every rule box under the course-level group for its course, so two chips in one box are always from the same course.
