---
name: frontend-code-review
description: "Extends the 'code-review-openedx' skill. Senior UX/Frontend peer review of a diff for this Frontend application. Use when asked to review a PR, a branch, or a diff, or for a second opinion on changes. Review-only: surface findings with file:line anchors and a severity marker; never fix, commit, or push. Post to GitHub only when explicitly asked and approved."
---

# Frontend Code Review (Extension of 'code-review-openedx')

A senior peer review for the general frontend application within the Open edX ecosystem. 
Surface what is wrong and why; let the developer decide what to act on. Never apply fixes,
commit, or push from this skill.

This skill runs in the top-level session. Per the Delegation rule in `CLAUDE.md`, whoever
runs it dispatches the sub-agents the parent skill names; it never runs inside a dispatched
sub-agent that would then need to dispatch further.

## Step 0: component tree map (runs before everything else)

When the review target is a pull request, run the `pr-component-tree` skill on it first, before
reading the parent skill and before the parent's phase A. It does not count against phase A's
tool-call budget. When the target is a branch or the working tree, skip this step and tell the
developer why.

1. Run `pr-component-tree` for the PR. It produces a Markdown file with the component tree as an
   inline SVG, and a plain-text outline of the same tree and notes.
2. Give the developer the result right away, in its own message and before the review starts:
   the absolute path of the Markdown file and the short summary the skill prescribes. The
   developer can read it while the review runs, so do not wait for the review to finish.
3. Make the outline context for the review. In the parent's A4 shared brief, add one line: "Read
   `<absolute path of the outline>` after this brief: the PR's component tree, one line per
   component, with a note on each changed component and changed module." That line counts toward
   the brief's 150 lines; the outline does not. Every B agent reads the outline after the brief.
4. Treat the outline as orientation: which components changed, how they nest on each page, which
   changed modules feed them, and what each change does. A sub-agent derived it from the diff, so
   it is not evidence. Every finding still cites lines read at the head SHA, and a note in the
   outline that the code contradicts is itself worth a finding.

## Parent skill

This skill manually builds on the sibling `code-review-openedx` skill; Codex does not load
that skill automatically. Before starting the review, read
[`../code-review-openedx/SKILL.md`](../code-review-openedx/SKILL.md) in full.

Follow the parent skill's review workflow, review-wide rules, evidence requirements,
and finding format. The frontend-specific checks below belong to the parent's phase B dispatch
wave (remits B3 to B5) and its phase C verification; they do not replace its general review
requirements.

If the parent skill file is missing or unreadable, stop and tell the user before
reviewing the change.

## In the parent's phase B remits and phase C verification, add the following frontend-specific questions:

In addition to the parent's checks in [code-review-openedx](../code-review-openedx/SKILL.md) (give the component, accessibility,
and styling questions to remit B5, any test question to remit B4, and the rest to phase C), evaluate the following detailed questions about this Frontend code review and raise any further concerns if prudent 
1. Is the Paragon design system being used as extensively as possible for the given components added in this change? Paragon components, bootstrap classes from Paragon and design tokens, with CSS used sparingly?
2. Does the implementation meet WCAG AA accessibility standards, if applicable?
3. Does it adhere to general best practices for this repo's version of React? 
4. Is it using TypeScript, TanStackQuery instead of Redux, other things? 
5. Is it avoiding inline styles?
