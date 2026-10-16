---
name: backend-code-review
description: "Extends the 'code-review' skill. Senior backend peer review of a diff for this application. Use when asked to review a PR, a branch, or a diff, or for a second opinion on changes. Also run as the final step of spike-and-stabilize. Review-only: surface findings with file:line anchors and a severity marker; never fix, commit, or push. Post to GitHub only when explicitly asked and approved."
---

# Backend Code Review (Extension of 'code-review')

A senior peer review for the general backend application within the Open edX ecosystem.
Surface what is wrong and why; let the developer decide what to act on. Never apply fixes,
commit, or push from this skill.

This skill runs at the top-level session (directly, or as `spike-and-stabilize`'s final
step, which is explicitly run by "the strong main model, not the sub-agent"). Per the
Delegation rule in `CLAUDE.md`, whoever runs it dispatches the sub-agents the parent skill
names; it never runs inside a dispatched sub-agent that would then need to dispatch further.

## Parent skill

This skill manually builds on the sibling `code-review` skill; Codex and Claude do not load
that skill automatically. Before starting the review, read
[`../code-review/SKILL.md`](../code-review/SKILL.md) in full.

Follow the parent skill's review workflow, review-wide rules, evidence requirements,
and finding format. The backend-specific checks below supplement the parent's
`Review` section; they do not replace its general review requirements.

If the parent skill file is missing or unreadable, stop and tell the user before
reviewing the change.

## During the inherited 'Review' step, add the following backend-specific questions:

In addition to the standard 'Review' steps outlined in [code-review](../code-review/SKILL.md), evaluate the following
detailed questions about this Backend code review and raise any further concerns if prudent

1. Does it adhere to general best practices for this repo's version of Django/Python?
2. Any security issues or vulnerabilities introduced in this pull request?
3. Do all added functions have appropriate, descriptive but concise names?
4. Do all added functions have appropriate, descriptive but concise docstrings? Could they be reworded so that they are
   less verbose if they seem too long?
5. If there are any database changes, do they follow the Open edX database design guidelines?
6. If there are any database changes, are all added database migrations properly documented?
7. If there are any database queries, are they thoroughly, efficiently, and concisely unit tested?
8. If there are any database queries added or changed, are they properly optimized and performant?
9. If there are any database queries added or changed, are they properly secured?
10. If a model field is added, which generic surfaces pick it up without any code naming it: an admin registration
    without an explicit `fields` list, a serializer or form using `__all__`, import/export, `model_to_dict`? Enumerate
    them and check each against what the ticket says may read or write the field.

Additional Notes:

1. A schema-only migration needs no test of its own. The criterion it serves counts as covered in the parent skill's
   acceptance-criteria table when a behavior test sets and reads the new column or constraint, alongside the
   repository's standard migration check when it has one. A new column that no test touches is a `Gap`, even when
   the migration applies cleanly.
