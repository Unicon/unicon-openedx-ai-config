---
name: paragon-a11y-check
description: "EXPERIMENTAL. Use when checking Paragon-based React UI in an Open edX frontend for WCAG 2.1 AA issues: after implementing a design, during frontend-code-review, or on request for a set of files or a diff. Checks Paragon component reuse, accessible names from react-intl messages, roles, color-independent status, keyboard and focus behavior against WAI-ARIA APG patterns, and role-based tests — and separately records which results were inspected in code and which were observed in the running app, with an optional axe run as a diagnostic. Review-only: reports findings with file:line anchors and WCAG criteria, never fixes code, never reports an unobserved check as passing, and is not a conformance audit."
---

# Paragon accessibility check (EXPERIMENTAL)

Read `.claude/design-system/policy.md` §4 first — it defines which of this skill's checks
are required for a `complete` `figma-to-paragon` run (the observed checks) and which are
diagnostics only.

## What this is and is not

- Review-only. It never edits code.
- It is not a WCAG conformance audit — it's a targeted check against the failure modes this
  workflow actually produces (missing names, color-only status, broken keyboard access,
  Paragon components used incorrectly), verified against the target repo's own tooling gaps
  (see §8).
- "Inspected" (read in code) and "observed" (confirmed in the running app) are reported
  separately, and never conflated. An inspected-only pass on something that also needs
  observation is not a pass on that item.

## 1. Inputs

Target files or diff (resolve per `code-review`'s repo/diff-resolution steps if unsure), plus
the design's `A11y` annotations from the handoff block, if this follows `figma-to-paragon`.

## 2. Reuse

- Flag a hand-built widget where Paragon already covers it (a custom dropdown instead of
  `Dropdown`/`Menu`, a custom dialog instead of `ModalDialog`, a hand-rolled tab UI instead
  of `Tabs`, checkbox/switch markup instead of `Form`'s controls).
- Interactive content inside a `Popover` or `Tooltip` — both render with `role="tooltip"`
  semantics that exclude it; that content needs `ModalPopup` instead.

## 3. Names

- Every user-facing string, including an accessible name, comes from a `messages.ts`/`.js`
  entry with a `description` (the target repo's own i18n convention — see its `AGENTS.md`).
- Apply the repo's own role-before-`aria-label` rule if it has one (check `CLAUDE.md`): some
  implicit roles (e.g. a plain `<div>`/`<span>`'s `generic` role) prohibit `aria-label` and
  screen readers may not announce it reliably — use a visually-hidden `sr-only` sibling
  instead.
- `IconButton` requires `alt`; a standalone meaningful `Icon` needs `screenReaderText`.

## 4. Status and color

- Every status/state has a text or icon signal, never color alone.
- A chart or other graphic gets an `aria-hidden` visual plus an `.sr-only` structured
  fallback (`<dl>`, `<ul>`, or `<table>`) carrying the same information as text.
- Any custom color pair (not a straight Paragon token pairing already vetted for contrast)
  gets its contrast checked against the resolved values from the installed CSS (WCAG 1.4.3
  normal text / 1.4.11 non-text) — compute it, don't eyeball it.

## 5. Keyboard and focus

- DOM order matches visual/tab order; focus is visible at every step.
- A custom widget follows its WAI-ARIA APG pattern. Example: a tree (e.g. the taxonomy tree)
  needs tree/treeitem roles, `aria-expanded`, roving `tabindex`, and arrow-key navigation —
  Paragon's `useArrowKeyNavigation` hook can help with the last part.
- Focus returns somewhere sensible after a modal/dialog closes (not lost to `<body>`).

## 6. Structure

Heading levels match the design's `heading` annotation (independent of visual size — Paragon
decouples `.hN` classes from `<hN>` elements for exactly this reason). Landmarks present.
`Form.Group`/`Form.Label` used for form field labeling; `Form.Control.Feedback` for errors,
associated with its field. Live regions for async status updates. Reflow at 320px width and
text at 200% don't break the layout or clip content.

## 7. Tests

Every new or annotated interactive element has a `getByRole` query with an accessible name
(React Testing Library query priority — most target repos already require this), and its
states are asserted (`aria-expanded`, `aria-selected`, `disabled`, etc.), not just its
presence.

## 8. Optional diagnostic: axe

Gate: confirm before running. Inject `axe-core` into the target repo's Playwright driving
recipe if it has one (`frontend-app-authoring`'s `run-frontend-app-authoring` skill has a
working Playwright setup you can extend) — report-only, never add `axe-core` to
`package.json`. Automated tools catch a fraction of real issues; a clean axe run is evidence
for the report, never grounds to skip §§2-7 or to mark anything "passed."

**Known gaps in the tooling itself** (state these in the report, don't paper over them):
`frontend-app-authoring`'s `.oxlintrc.json` has the `jsx-a11y` plugin commented out (with a
"TODO: enable" note), and there's no `jest-axe` in its dependencies — nothing automated in
that repo's own CI catches what this skill checks by hand.

## 9. Required "observed" checks (running app, per `policy.md` §4)

If the app can run (e.g. via `run-frontend-app-authoring` for `frontend-app-authoring`):
keyboard-operate every new control, confirm visible focus and order, confirm focus return
after any dialog closes, confirm reflow at 320px and text at 200%, and confirm rendered
contrast for any custom color pair. If the app can't be run, mark every one of these
`not verified` explicitly — this makes the overall `figma-to-paragon` run `incomplete`
(`policy.md` §4), which is correct: don't report them as passed by omission.

## 10. Report

- Findings in the `code-review` skill's format (`Bug.`/`Question.`/`Suggestion.`/`Nit.`, each
  with a `file:line` anchor) plus the relevant WCAG success criterion.
- A table: each design `A11y` annotation (or, with no design, each interactive
  element/status/heading found) → inspected result → observed result → evidence.
- A list of anything skipped or left `unverified`, and why.

## When blocked

- The app can't run: do the inspected-only checks (§§2-7), report every observed item as
  `not verified`, and say the overall run can't be `complete` until it's confirmed.
- A component's real ARIA role is unclear from its README: read its source
  (`node_modules/@openedx/paragon/src/<Component>/index.jsx`) or query it by role in a quick
  test rather than guessing.
