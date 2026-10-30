---
name: backend-code-review
description: "Extends the 'code-review-openedx' skill. Senior backend peer review of a diff for this application. Use when asked to review a PR, a branch, or a diff, or for a second opinion on changes. Review-only: surface findings with file:line anchors and a severity marker; never fix, commit, or push. Post to GitHub only when explicitly asked and approved."
---

# Backend Code Review (Extension of 'code-review-openedx')

A senior peer review for the general backend application within the Open edX ecosystem.
Surface what is wrong and why; let the developer decide what to act on. Never apply fixes,
commit, or push from this skill.

This skill runs in the top-level session. Per the Delegation rule in `CLAUDE.md`, whoever
runs it dispatches the sub-agents the parent skill names; it never runs inside a dispatched
sub-agent that would then need to dispatch further.

## Parent skill

This skill manually builds on the sibling `code-review-openedx` skill; Codex and Claude do not load
that skill automatically. Before starting the review, read
[`../code-review-openedx/SKILL.md`](../code-review-openedx/SKILL.md) in full; it tells the session
to read `review-rules.md` first.

Follow the parent skill's review workflow, review-wide rules, evidence requirements,
and finding format. The backend-specific questions in `review-additions.md` are review questions
in the sense of the parent's step A5: B agents answer them in the wave (remits B2 to B5), and
phase C verifies the findings they produce like any other candidate. They add to the parent's general review
requirements and replace none of them.

If the parent skill file is missing or unreadable, stop and tell the user before
reviewing the change.

## Backend review questions

The backend review questions and the consolidation note live in `review-additions.md` in this
skill's directory, numbered Q1 to Q12. Each B dispatch names that file and its `## B<n>` section
when it has one for that remit, the consolidation dispatch names the whole file, and the developer's questions are numbered from Q13.

## Delivering the review

When the review is done, your response in chat is only a link to the cleaned-up file that the
parent's phase D produces, nothing more. When the user asked questions that are an integral part
of the review, the answers are part of the review in that file.
