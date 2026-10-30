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

## Step 0: component tree map (runs in phase A)

When the review target is a pull request, dispatch one `general-purpose` Sonnet agent (`effort: high`,
model passed explicitly, budget 40 tool calls) in the same message as the parent's brief
agent. It does not count against phase A's budget. Its prompt follows the parent's dispatch
template, except that the Read line is "Read `<absolute path of the sibling `pr-component-tree`
directory of the `code-review-openedx` skill directory>/SKILL.md` and run its steps 1 to 7 yourself". The agent is both that skill's top-level session and its sub-agent,
so it dispatches nothing.
Tell it to write the Markdown file and the outline into the working directory, and to make its final
message the absolute path of the Markdown file and the short summary that `pr-component-tree` step 8
describes, and nothing else. Give the brief
agent the outline path `<dir>/component-tree-pr-<N>-context.txt`, the file `pr-component-tree`
writes. When the target is a branch or the working tree, skip this step and tell the developer why.

When the agent returns, relay its summary to the developer right away, in its own message, with
the absolute path of the Markdown file. The developer can read it while the review runs.

## Parent skill

This skill manually builds on the sibling `code-review-openedx` skill; Codex does not load
that skill automatically. Before starting the review, read
[`../code-review-openedx/SKILL.md`](../code-review-openedx/SKILL.md) in full; it tells the session
to read `review-rules.md` first.

Follow the parent skill's review workflow, review-wide rules, evidence requirements,
and finding format. The frontend-specific questions in `review-additions.md` are review questions
in the sense of the parent's step A5: B agents answer them in the wave (remits B3 and B5), and
phase C verifies the findings they produce like any other candidate. They add to the parent's general review
requirements and replace none of them.

If the parent skill file is missing or unreadable, stop and tell the user before
reviewing the change.

## Frontend review questions

The frontend review questions and the note on the component tree outline live in
`review-additions.md` in this skill's directory. The questions are numbered Q1 to Q5, and the
developer's questions are numbered from Q6. Each B dispatch names the `## All` section, and also
its own `## B<n>` section when the file has one for that remit (B3 and B5).

## Delivering the review

When the review is done, your response in chat is only a link to the cleaned-up file that the
parent's phase D produces, nothing more. When the user asked questions that are an integral part
of the review, the answers are part of the review in that file. The component tree message from
step 0 is sent earlier, while the review runs.
