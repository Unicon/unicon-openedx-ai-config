---
name: benchmark-code-review-skill
description: Use when asked to compare versions of a code-review skill, or two different review skills, against a real pull request whose human review comments serve as the answer key; for example "which skill version reviews better", "evaluate the code-review skill", "score the review skill against PR N", or "re-run the PR 847 benchmark". Also use before changing a code-review skill, to get a baseline the change can be measured against.
---

# Benchmark a code-review skill

One principle drives every step: each reviewing agent must see exactly what the human reviewer
saw, and nothing the human's review produced. GitHub state drifts after a review (the author
force-pushes fixes, the ticket gets amended to match the code, follow-up tickets appear, the fix
merges to main), and the review skills themselves fetch live PRs and read upstream main. Left
alone, an agent reviews the fixed code against the amended ticket and reads the answer key.

The scripts and templates in this directory encode the fixes. `cases/` holds saved benchmark
cases with their ground truth and past results; start from one when it fits.

## Procedure

1. **Freeze the case.** `python3 scripts/freeze_pr.py --repo owner/name --pr N --ticket T
   --issues <siblings> --out <scratch>/case`. It picks the cutoff (the earliest review with
   inline comments), the head SHA the comments anchor to (their `original_commit_id`, not the
   PR's current head), main as of the cutoff, and the last edit of the PR body, the ticket, and
   each sibling ticket before the cutoff. Read `case.json` and confirm the choices make sense;
   pass `--cutoff` to override. `ground_truth_source.md` is the answer key: keep it outside
   every directory an agent will read.
2. **Write the ground truth before any report exists.** From the answer key, take the first-round
   comments anchored to the frozen head; later rounds comment on code the fixes introduced and
   are excluded. Split multi-point comments into one item each, with file, mechanism, and the
   fix the reviewer asked for. Weight 3 for items the reviewer required before merge, 2 for
   substantive non-blocking requests, 1 for nits. Copy the credit tiers from
   `templates/scoring.md` into the file. Then check circularity: if a skill under test was
   written after this review and could have been informed by it, mark the affected items and
   say so in the results. Prefer a held-out PR when the skill change is large.
3. **Build isolated checkouts.** `CLAUDE_DIR=<config>/.claude bash scripts/setup_checkout.sh
   <local-repo> <upstream-url> <head-sha> <main-sha> <scratch>/eval <variant>...`. The result has
   no remotes, no tags, unreachable objects pruned (a local clone otherwise still holds the
   merged fix), `main` at the cutoff, `pr-head`, `pr-base`, and one worktree per variant, so
   break-and-restore edits cannot collide. `pr-base` defaults to the head's parent; for a PR
   with several commits pass `BASE_SHA`. Pass `CUTOFF` and `ABSENT_SHAS` (the merge commit and
   later review heads, all in `case.json`) so the script asserts nothing newer survived. For a
   stacked PR, `pr-base` is the stack's head and the PR's change is `git diff pr-base pr-head`;
   say so in the brief. Worktrees share refs, so if agents may create branches the other must
   not see, run the script once per variant. Smoke test one worktree: activate the project
   venv, export `PYTHONPATH=<worktree>/src`, confirm the package's `__file__` resolves under the
   worktree (the editable install points at the developer's checkout, on another branch), and
   run the touched tests.
4. **Serve each skill version as files.** `git -C <config> show <ref>:.claude/skills/<name>/SKILL.md`
   into `<scratch>/skills/<variant>/<name>/SKILL.md`, keeping sibling skills beside it so a
   parent reference like `../code-review-openedx/SKILL.md` resolves. The Skill tool loads only
   the current version, so the brief forbids it for review skills. Agent definitions under
   `.claude/agents/` come from the current session for every variant; if the config change
   touched them, say so in the results, or inline the old definition into a `general-purpose`
   dispatch.
5. **Verify nested dispatch.** Every review skill here dispatches sub-agents. Dispatch a cheap
   `general-purpose` agent whose only task is to dispatch an `Explore` agent and report the
   result. If it cannot, stop and tell the user; a run where one variant silently does its
   sub-agents' work inline measures nothing. The brief must state that the user overrides
   CLAUDE.md's delegation rule for this task, because the agents read that rule too.
6. **Write one brief per variant** from `templates/BRIEF.md`. The briefs differ only in the skill
   paths, worktree, and scratch directory. Each gets its own copy of the frozen context files.
   The brief forbids `gh`, WebFetch, and WebSearch against the repository's PRs and issues
   (the skills fetch them otherwise), states there is no deadline and that the agent must wait
   for its sub-agents, and requires a `## Process log` section so a degraded run is visible.
7. **Dispatch all variants in one message**, same `model` passed explicitly, in the background.
   Label variants neutrally (A, B) in briefs, directory names, and reports, and look up which is
   which only after scoring. If a rate limit kills them: every sub-agent died with its parent,
   so on resume tell each agent that pending results will not arrive and to re-dispatch; a
   child's report that arrives after its parent died is routed to you, so forward it verbatim
   to the parent.
8. **Collect reports** with `python3 scripts/extract_handback.py <transcript.output> <out.md>`.
   Never read a transcript into context. Audit each run with
   `python3 scripts/extract_handback.py <transcript.output> --audit <answer-key-dir> <config-repo>`:
   it prints tool-use counts, every Agent dispatch with its model, Skill calls, and any tool
   input that names a forbidden path. A hit means contamination; rerun that variant. If an
   agent delivers before its sub-agents report, record the delivery as interim and send it
   back to finish.
9. **Score** each report with `templates/scoring.md`: one row per ground-truth item, credit by
   content rather than by label, false positives counted only when the claim is wrong or rests
   on a premise the maintainer rejected, extras verified against the frozen code before they
   count as valid, communication graded last. Lock the tiers before the first report is read
   and apply them identically; when a later report makes you refine a tier, re-grade the
   earlier ones. Composite = 0.70 coverage + 0.15 precision + 0.15 communication.
10. **Report and save.** Scores table, items every variant missed, what separated them, valid
    findings outside the answer key, cost per variant from the process logs, and caveats
    (single run, interruptions, circularity). Write everything to the scratchpad first.
    Saving `ground_truth.md`, `case.json`, the frozen ticket and PR body, and `results.md`
    under `cases/<repo>-pr<N>/` is a change to the `.claude` setup: ask before doing it, and
    read `.claude/decisions/` first. Remind the user that decision 0002 asks for a line in
    `ai-output-evaluations/Output-evaluations.md`.

## Quick reference

| Drift or trap | What it does to the benchmark | Fix |
| --- | --- | --- |
| Force-pushed fixes | Current head is the fixed code | Head = inline comments' `original_commit_id` |
| Ticket amended after review | A deviation the reviewer flagged disappears | Freeze the ticket at the cutoff, not only the PR body |
| Sibling tickets edited or created after review | Decisions from the review leak in | Freeze siblings at the cutoff; exclude tickets created after it |
| Upstream main contains the merge | `git log` shows the fix | Clone with no remotes; `main` at the cutoff |
| Main set to the merge-base | Rebase and collision findings become unreachable | `main` = main as of the cutoff, as the reviewer had it |
| Skill fetches the PR with `gh` | Reads the comments | Forbid it; supply frozen files as the live source |
| Shared checkout | Break-and-restore edits collide | One worktree per variant; one clone per variant if agents create refs |
| Local clone keeps unreachable objects | The merged fix is still in the object store | Script prunes; assert with `ABSENT_SHAS` |
| `.claude/agents/` from the current session | Old variant runs with new agent definitions | Diff the config change; disclose or inline |
| Skill tool for the old version | Loads the new version | Serve versions as files; forbid the Skill tool |
| CLAUDE.md delegation rule | Agent refuses to dispatch | Verify nested dispatch; override in the brief |
| Editable install | Tests run the wrong branch | `PYTHONPATH` to the worktree, confirm `__file__` |
| Rate limit | Parents and children die together | Resume by SendMessage; forward orphaned reports |
| Agent delivers early | Missing skill steps look like skill failures | "No deadline" in the brief; send back to finish |

## Common mistakes

- Reviewing the ticket as it is today. On PR 847 the leaf-naming clause and a response field
  name were changed after the review; the frozen ticket is what makes those findings possible.
- Treating the second review round as ground truth. Those comments target code that did not
  exist at the frozen head.
- Reading sub-agent transcripts for the report. They are full JSONL logs; use the script.
- Scoring by label. A Nit that states the full request earns the same credit as a Gap that
  states it.
- Counting a maintainer-rejected premise as a Question. If the real reviewer said the premise
  is wrong, a finding built on it is a false positive.
- Claiming a ranking from one run. Differences of a few points flip on a rerun; say so.

## Saved cases

- `cases/openedx-core-pr847/`: openedx/openedx-core PR #847 at head `2ca89b767`, 21 ground-truth
  items, three variants scored on 2026-10-19 (`results.md`). Rebuild it with `freeze_pr.py`
  (the arguments are in `case.json`) or reuse `frozen/` directly.
