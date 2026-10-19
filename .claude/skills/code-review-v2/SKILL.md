---
name: code-review-v2
description: Use when asked for a thorough, adversarial code review of a pull request, branch, or diff in an Open edX repository (openedx-core, edx-platform, frontend-app-authoring), or for a second opinion on a change before merge. Review-only; never fixes, commits, pushes, or posts to GitHub unless explicitly asked and approved.
---

# Code review v2: parallel adversarial review with impact scoring

## Overview

Six independent reviewers each attack the change from one angle, and the top-level session
then filters their reports for signal, scores every surviving finding 1-100 for impact on the
merge decision, and reports the result. The reviewers are deliberately strong models told to
be adversarial; the orchestrator is deliberately skeptical of them. Neither half works alone:
strong reviewers produce confident noise, and an orchestrator reviewing alone misses angles.

This skill runs in the top-level session. Per the Delegation rule in `CLAUDE.md`, only that
session dispatches the reviewers; a reviewer never dispatches further. A reviewer that needs
something it cannot fetch returns a "Needs research" item, and the orchestrator fulfills it
inline (a `gh api` call, a grep, a web fetch) or with a cheap `Explore` dispatch.

**Model choice and cost.** This skill dispatches `software-architect` reviewers on Fable
(security, correctness) and Opus (the other four). That is an explicit, standing user override
of the model table in `CLAUDE.md`, which would route review to Sonnet. The tradeoff was
accepted when the skill was created and is worth restating to the developer when the skill is
invoked on a small change: in its first run, on a 99-line schema-only PR, each reviewer used
100k to 200k tokens and 12 to 18 minutes of wall clock, and five of six surfaced the same
headline finding. Reserve the skill for reviews where a missed defect is expensive. Pass
`model` explicitly on every dispatch.

## When to use

- A PR, branch, or diff needs a real review before merge, and a missed defect would be
  costly: schema changes, public API changes, anything touching learner data or security.
- The developer asks for a second opinion on a change that already has an approval.
- The developer asks for this skill by name.

Do not use it for a one-line fix, a rename, or a docs typo; a direct inline read is enough.

## 1. Pin the target and gather context (orchestrator, inline)

Do this yourself with a handful of commands; it is lookups, not judgment.

1. Resolve the PR on the upstream repository, not the fork: `gh pr view <n> --repo
   <owner>/<repo> --json title,body,headRefName,baseRefName,files,commits,reviews,comments`.
   Record the head SHA, the base SHA, and the merge-base. Fetch prior reviews and inline
   review threads so the new review does not repeat them.
2. Resolve the ticket from "Closes #n" in the PR body. Fetch it and record its `updatedAt`.
   Fetch every ticket the PR body or the ticket names as a sibling, consumer, or design
   source (`gh issue view <n> --repo ... --json title,state,body`), and the comments of any
   design discussion issue (`gh api repos/<owner>/<repo>/issues/<n>/comments --paginate`).
3. Produce the diff against the merge-base: `git diff <merge-base>..<head>`.
4. List what landed on main after the PR branched, in the apps the PR touches and in any app
   that depends on them: `git log --oneline <merge-base>..upstream/main -- <paths>`. The
   checked-out tree does not contain those commits, so a reviewer reading HEAD will reason
   from a stale picture (a precedent the ticket says to mirror, a foreign key that changed,
   a new consumer). Name the relevant commits in the brief with their SHAs.
5. Locate the governing documents: ADRs in `docs/*/decisions/` of this repo and of sibling
   repos (`../edx-platform`, `../openedx-proposals`), the repo's `CLAUDE.md`, and any
   precedent the ticket says to mirror.
6. Confirm the cheap baseline facts inline so reviewers build on them instead of re-deriving:
   run the touched tests without coverage, run `makemigrations --check --dry-run` for the
   touched app, read the CI status with `gh pr checks`. Note any local environment gap you
   hit (a missing test dependency, for example) so reviewers are not surprised by it.
7. Save everything to the scratchpad under `context/`: `pr_<n>.diff`, `pr_<n>_body.md`,
   `pr_<n>_prior_reviews.md`, `issue_<n>.md` per ticket, and the comment dumps. Then write
   `context/BRIEF.md` from the template in [scopes.md](scopes.md): standing rules, the PR
   facts, the context file list, the confirmed facts, and the strict output format.

A confirmed fact in the brief is a command and its output ("`grep -rn 'class .*(ObjectTag)'
src/` returns only the test proxy"), never a universal negative ("nothing subclasses these
models"). In the first run a shell glob error silently truncated one grep and the brief
asserted a negative that a reviewer later disproved; a stated command lets a reviewer re-run
it, a bare conclusion makes them trust it.

## 2. Dispatch six reviewers in one message (orchestrator)

One `software-architect` dispatch per scope, all in the same message so they run in parallel,
each told to read `BRIEF.md` first. The six scopes and the concrete probes each must cover
are in [scopes.md](scopes.md):

| # | Scope | Model |
| --- | --- | --- |
| 1 | Security: OWASP Top 10, Django/DRF practice, integrity of any protective data | fable |
| 2 | Correctness: every acceptance criterion, every PR claim, relevant ADRs here and in sibling repos | fable |
| 3 | Architectural conventions and soundness: how similar code is written here and in edx-platform, ADRs, OEPs, library stability | opus |
| 4 | Testing and edge cases: AC coverage, mutation checks, edge-case enumeration, tests fail for the stated reason | opus |
| 5 | Open questions: what the PR, ticket, or design left unanswered, with the concrete consequence of each answer | opus |
| 6 | Miscellaneous: style, docs, migration hygiene, linters on touched files, commit and PR hygiene, writing rules | opus |

Each prompt names the probes for its scope, tells the reviewer which claims in the PR body to
verify rather than trust, and asks for CONFIRMED versus INFERRED on every finding. Every
finding carries the reviewer's own impact estimate; the orchestrator re-scores it later.

While they run, do independent work. Do not read their output files; wait for completion.

## 3. Filter for signal (orchestrator)

When all six reports are in, work through them in this order:

1. **Deduplicate across scopes.** The same defect often surfaces in several reports with
   different framing. Merge into one finding and keep the strongest evidence; note how many
   reviewers converged on it, which is itself a signal.
2. **Verify every load-bearing claim yourself** before scoring it. Read the cited line, run
   the cited command, check the quoted acceptance criterion against the ticket text. A
   reviewer's CONFIRMED label is a claim, not a proof. Drop any finding whose evidence does
   not hold. Check each new claim against what earlier reports and the brief established;
   when they conflict, resolve it by looking, not by majority.
3. **Separate merge impact from program impact.** Reviewers told to score "impact on the
   merge decision" will score a downstream design risk at 10 even when it is the most
   important thing in their report. Collect every item whose action is "record on ticket X"
   into one finding, "open questions to record downstream", and score the value of recording
   them now, while the context is fresh and the schema or contract is still cheap to change.
4. **Check each finding against the ticket's scope.** A finding that asks for work the ticket
   explicitly defers to another ticket is an open question to record, not a change request.
5. **Score impact 1-100** with the rubric below. Score the consequence, not the reviewer's
   severity label and not how much text the reviewer wrote.
6. **Pick the drop threshold** and say what it is. The default is 25. Lower it when the PR is
   small and clean and the few findings deserve a hearing; raise it when the PR is large and
   the list needs to fit in one reviewer sitting.

### Impact rubric

| Score | Meaning | Treat as |
| --- | --- | --- |
| 80-100 | Data loss, security hole, broken acceptance criterion, or a downstream consumer breaks. Merging as-is causes harm. | Change request, blocking |
| 50-79 | A real correctness, coverage, or convention gap with a concrete consequence, or a PR claim that is false and that a reviewer would rely on. | Change request, should fix before merge |
| 25-49 | A genuine improvement or an open question with a stated consequence, where the author could reasonably decline. | Comment, author's call |
| 1-24 | Preference, nit, or a problem the ticket defers elsewhere with no cost to deferring. | Drop, or list in one line |

## 4. Report (orchestrator)

Lead with the verdict in one sentence: approve, approve with comments, or request changes,
and the threshold used. Then:

- **Kept findings**, highest impact first, one short table row each: impact, scope, anchor,
  what is wrong, what to do. Below the table, give each kept finding the two to four sentences
  a reader needs to act without opening the reports.
- **Dropped findings**, one line each with the score and the reason they are noise, so the
  developer can disagree.
- **Checked and acceptable**, a short list of what the reviewers examined and found fine, so
  "not checked" is distinguishable from "checked, OK".
- **Gaps**: what could not be verified, any "Needs research" item left open, and any error in
  the brief that a reviewer caught.

Do not post to GitHub. If the developer asks for a GitHub review, draft the text, show it,
and post only the approved wording.

## Common mistakes

- **Trusting the reviewers' severities.** They inflate nits and under-score program risks.
  Re-score everything from consequence.
- **Scoring volume.** Six reports produce thirty findings; most are the same four defects.
- **Reviewing the roadmap instead of the diff.** A finding about what a downstream ticket
  should do belongs under open questions unless this PR fixes the schema or contract in a way
  that makes the downstream work impossible or expensive.
- **A stale HEAD.** The PR branch predates commits on main that change the picture. Step 1.4
  exists because a reviewer reading HEAD alone missed a PROTECT foreign key that had landed
  on main and changed a "silent data loss" finding into a "loud failure" one.
- **Letting a reviewer dispatch.** It cannot. Fulfill its "Needs research" item yourself.
- **Reading the agents' output files.** They are full transcripts and will flood the context.
  Wait for the completion notification and read the returned report.
