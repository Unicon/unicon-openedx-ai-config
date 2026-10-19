---
name: frontend-code-review
description: "Extends the 'code-review-openedx' skill. Senior UX/Frontend peer review of a diff for this Frontend application. Use when asked to review a PR, a branch, or a diff, or for a second opinion on changes. Also run as the final step of spike-and-stabilize. Review-only: surface findings with file:line anchors and a severity marker; never fix, commit, or push. Post to GitHub only when explicitly asked and approved."
---

# Frontend Code Review (Extension of 'code-review-openedx')

A senior peer review for the general frontend application within the Open edX ecosystem. 
Surface what is wrong and why; let the developer decide what to act on. Never apply fixes,
commit, or push from this skill.

This skill runs at the top-level session (directly, or as `spike-and-stabilize`'s final
step, which is explicitly run by "the strong main model, not the sub-agent"). Per the
Delegation rule in `CLAUDE.md`, whoever runs it dispatches the sub-agents the parent skill
names; it never runs inside a dispatched sub-agent that would then need to dispatch further.

## Parent skill

This skill manually builds on the sibling `code-review-openedx` skill; Codex does not load
that skill automatically. Before starting the review, read
[`../code-review-openedx/SKILL.md`](../code-review-openedx/SKILL.md) in full.

Follow the parent skill's review workflow, review-wide rules, evidence requirements,
and finding format. The frontend-specific checks below supplement the parent's
`Review` section; they do not replace its general review requirements.

If the parent skill file is missing or unreadable, stop and tell the user before
reviewing the change.

## During the inherited 'Review' step, add the following frontend-specific questions:

In addition to the standard 'Review' steps outlined in [code-review-openedx](../code-review-openedx/SKILL.md), evaluate the following detailed questions about this Frontend code review and raise any further concerns if prudent 
1. Is the Paragon design system being used as extensively as possible for the given components added in this change? Paragon components, bootstrap classes from Paragon and design tokens, with CSS used sparingly?
2. Does the implementation meet WCAG AA accessibility standards, if applicable?
3. Does it adhere to general best practices for this repo's version of React? 
4. Is it using TypeScript, TanStackQuery instead of Redux, other things? 
5. Is it avoiding inline styles?
