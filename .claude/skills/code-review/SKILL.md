---
name: code-review
description: "Senior peer code review of a diff for a given code base. Use this skill mainly as inheritable Skill that provides baseline functionality extended by front-end or back-end Skills that will use this skill as a reference for common activity. Review-only: surface findings with file:line anchors and a severity marker; never fix, commit, or push. Post to GitHub only when explicitly asked and approved."
---

# Code review

A senior peer review for an application within the Open edX ecosystem.
Surface what is wrong within the diff and why; let the developer decide
what to act on. Never apply fixes, commit, or push from this skill.

This skill runs at the top-level session (directly, or as `spike-and-stabilize`'s final
step, which is explicitly run by "the strong main model, not the sub-agent"). Per the
Delegation rule in `CLAUDE.md`, whoever runs it dispatches the sub-agents below directly;
it never runs inside a dispatched sub-agent that would then need to dispatch further.

## Review-wide rules

These rules apply during discovery, analysis, verification, and presentation:

- Review only issues introduced, worsened, or exposed by the change. Do not report
  pre-existing issues unless the change makes them newly relevant to the requested
  behavior, contract, or scope.
- Do not turn preferences into findings. Every finding must explain a concrete
  user-visible, contractual, security, accessibility, performance, data-integrity,
  or maintenance impact.
- If an issue cannot be tied to the change or its impact cannot be established,
  omit it or present it as a clearly labeled `Question`, not a `Bug`.

## 1. Resolve the repository and review target.

Identify the repository and 'review target' from the request: a pull request, branch,
commit range, or working tree. Read pull request metadata if needed to locate the
ticket, but do not inspect the diff yet.

## 2. Read Pull Request metadata, if applicable, to locate the ticket.

Before inspecting the diff, identify the ticket or issue that defines the requested
change. Accept any of:

- ticket text already provided in the conversation;
- a ticket URL or issue number;
- a ticket linked in the PR description;
- a local ticket file, if explicitly provided.

If no ticket is available, stop and ask:

> Please provide the ticket or issue for this change, either with URL to the
> ticket or the ticket that's been linked in a pull request description. I 
> need it to review scope and completeness. I won't begin the review until I have it.

Do not infer the ticket from the branch name, PR title, commit message, or code.
Do not inspect or review the diff until the ticket is provided.


## 3. Read repository AI Policy and instructions

Before reading the diff or source files, read the target repository's root `AGENTS.md`,
if present. Also, read any nearer `AGENTS.md` files that govern changed paths.

Treat those files as authoritative for repository-specific conventions, including:

- language and framework versions;
- repository layout and module boundaries;
- testing, linting, and formatting commands;
- accessibility and UI conventions;
- approved architectural patterns and documented exceptions.

Use this skill for the review workflow and output format, but do not replace
repository-specific instructions with generic assumptions from this skill. Any
directives in `AGENTS.md` take precedence over this skill's instructions.

If an applicable `AGENTS.md` exists but cannot be read, stop and tell the user.
If no `AGENTS.md` exists, continue.

### 4. Obtain and inspect the diff

Before reviewing, obtain and inspect the complete diff for the requested target.

- For a pull request, use its actual base and head revisions. Do not assume the checked-out branch or repository default branch matches the PR. Inspect the full patch and confirm which files it changes.
- For a branch review, compare the requested branch with the intended base. If the base is not clear, ask rather than guessing.
- For a working-tree review, inspect the repository status, staged diff, and unstaged diff. Include untracked files only when they are clearly part of the requested change.
- Read the relevant surrounding code at the target revision so each change can be understood in context.
- Confirm the diff is complete and was not truncated. If you cannot obtain it, or cannot determine the target or comparison base, stop and explain what is missing. Do not substitute the PR description or guess at the changes.

## 4. Review

Check the dimensions the diff actually touches; skip the rest and say which you skipped.

- Correctness: logic, edge cases, error paths, off-by-one, None handling.
- Security: for instance, REST endpoints enforce auth and validate input; no secrets.
  breaking changes to stable (non-UNSTABLE) public APIs goes through DEPR; model
  identifiers follow `id`/`uuid`/`key`/`num`, database integrity, no exposed configs, 
  and any other similar security concerns applicable to the code base and code changes.
- Tests: each behavior is covered; assertions can actually fail; no vacuous tests.
- Naming and documentation: clear names, appropriate commenting on public APIs if actually needed, consistent terms.
- Surgical scope: every changed line traces to the stated goal.

Additionally, evaluate the following detailed questions and raise any concerns if prudent
1. Does this pull request implement all of the acceptance criteria in the ticket?
2. Is the automated testing appropriate for the new additions, but still efficient and concise?
3. Do the added automated tests actually test what they claim to?
4. For any automated testing additions or changes, are they properly using constants for appropriate values and not depending on various hard coded values (such as dates, etc.) that might become invalid at a later time?
5. Is there any extraneous automated testing that is just testing the obvious and doesn't match the level of testing granularity seen elsewhere in this repo?
6. Does it adhere to Axim/Open edX preferences for new additions, as an example, consider the following pull request that went well https://github.com/openedx/frontend-app-authoring/pull/3218
7. Does the code account for all relevant edge cases, with regard to use cases it implements and the acceptance criteria of the ticket?
8. Does the pull request description include attribution to a specific AI agent or specify none if no AI was used? This is required by the Open edX community.
9. Does the pull request include manual testing steps? This is required by the Open edX community.
10. For each of the comments added in changed source files, are all of them necessary, or would this code be clear to a developer without it? Are they as clear and concise as they can be?
11. Do the new exported functions have clear names?
12. Any security issues, such as exposed configs, introduced vulnerabilities, introduced libraries, or other potential issues?
13. Run applicable targeted checks from the target repository’s AGENTS.md when feasible and report which checks were run or skipped. 
14. Review any other changed behavior that has a concrete impact that may not be covered by the above, but is important to surface as a finding of this review.

## 5. Verify before asserting

A claim that sets a finding's severity needs a source: a `file:line` or command
output, not memory. Verify against the actual code at the diff's ref. Checking a
library's documented behavior is a web lookup, so run it in a sub-agent, never inline.
If you can't back a claim, downgrade it to a question. Don't pad findings with weak
citations.

Before presenting a finding, confirm that:

1. The finding is introduced, worsened, or exposed by the change.
2. The finding has an evidence source.
3. The finding explains a concrete impact.
4. The severity matches the evidence.
5. The finding is not merely a preference or pre-existing issue.

## 6. Present

Group findings by severity, each with a `file:line` anchor and a one-word marker:

- `Bug.` wrong behavior, security hole, or broken contract.
- `Question.` a premise you can't confirm; ask rather than assert.
- `Suggestion.` a real improvement that is optional.
- `Nit.` style or wording, lowest priority.

Lead with the point, then the mechanism. Keep the tone that of one engineer to another:
direct, specific, no praise padding. Open with a one-line verdict, then the findings.
If nothing is wrong, say so plainly. Post to GitHub only if the developer asks and
approves the wording.
