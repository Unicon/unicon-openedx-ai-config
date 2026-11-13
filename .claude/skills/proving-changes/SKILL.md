---
name: proving-changes
description: Use when a code change is about to be called done, complete, or ready for review, when a plan task needs its verification steps, and when a pull request is about to be opened
---

# Proving Changes

## Overview

**Core principle:** Proof is evidence you observed yourself in this session. A change without proof is a change you do not have full confidence in, and you say so.

This skill defines what counts as proof, where proof is recorded, and the check that decides whether a change is done. The other workflow skills (writing-plans, executing-plans, subagent-driven-development, finishing-a-development-branch) call into it at fixed points; it also applies on its own to any change made without a plan.

## What Counts as Proof

Proof is evidence you observed yourself in this session: command output, a reproduction, a screenshot. Use the most direct proof the change allows. From most to least direct:

1. **Reproduction.** Reproduce the original failure, apply the fix, then watch the same reproduction pass.
2. **The repo's CI checks.** Run the checks the repo's CI runs (typecheck, lint, tests), scoped the way the repo's instructions (CLAUDE.md, AGENTS.md) say to run them locally.
3. **One focused test.** When the behavior has no test and the repo has a test setup, add one focused test that fails without the fix and passes with it.
4. **Run the app and look.** For UI and runtime behavior, run the app and observe the change. Green mocked tests do not prove that the user experience works. Take a screenshot when it helps a reader, and attach it to the PR when you have a way to upload it.

Not proof: reading the diff, reasoning about what the code does, a run from an earlier session, a subagent's report whose output you did not read, or a mocked test standing in for runtime behavior.

A doc change is proven by building or rendering it. A comment or docstring change is covered by the proof of the code it describes; name that proof.

**When you cannot find a way to prove a change, you do not have full confidence. Ask the user.** This is one of the few reasons a running plan stops.

## The Proof Record

One record per branch. `bash scripts/proof-dir` (in this skill's directory) prints the record's directory, `<repo-root>/.superpowers/proofs/<branch>/`, git-ignored and keyed by branch, so it outlives the plan workspace that executing-plans and subagent-driven-development delete when a plan finishes. The record is `PROOF.md` in that directory, with screenshots beside it. Start it from [proof-record-template.md](proof-record-template.md).

The record has four parts:

- **Acceptance criteria.** One row per criterion from the ticket or spec, with the proof ids that demonstrate it and the result.
- **Proofs.** One entry per proof: an id, what it proves, its kind (reproduction, CI check, focused test, run the app), the command or steps, the observed output trimmed to the lines that carry the result, PASS or FAIL, and the changed files or hunks it covers. PASS means the run showed what the entry claims, so a reproduction that fails before the fix, as expected, is a PASS.
- **Diff coverage.** Every file in `git diff --stat BASE..HEAD`, with the proof ids that exercise it. BASE is the commit the branch forked from (`git merge-base <target branch> HEAD`), or a task's starting commit when the record covers one task. Files with several unrelated hunks get one row per hunk. An `Uncovered` list closes the section and is empty when the work is done.
- **Open.** Changes you could not find a way to prove, and why. This list goes to the user.

Write each proof entry in the same message as the command that produced it. Output scrolls out of context; a record written at the end is reconstruction, not evidence. A subagent that implements a task writes its proof entries to the same record.

## The Done Check

A change is done when the proof record covers every change in the diff and every proof result is PASS, and every acceptance criterion maps to at least one passing proof. Run the check whenever you are about to say a change is done, complete, or ready for review, and once more after the last commit on the branch, including review fixes:

1. List the diff: `git diff --stat BASE..HEAD`, then the hunks for any file whose coverage is unclear.
2. For each file or hunk, point at a proof entry that exercises it. Fill the Diff coverage section; what you cannot point at goes under `Uncovered`.
3. Re-run every proof whose covered files changed after it ran. A proof proves the tree it ran on, and nothing newer.
4. If `Uncovered` is non-empty or any proof is FAIL, that is one cycle: fix the code or add the missing proof, re-run, and start again at step 1.

**Three cycles maximum.** After the third cycle with gaps remaining, stop. Move the gaps to `Open` with the reason each one resists proof, and ask the user. Three cycles without full coverage means the change or the proof plan is wrong, and a fourth cycle would hide that.

## Where It Sits in the Workflow

| Point in the workflow | What this skill requires there |
|---|---|
| writing-plans | Each task carries a `**Proof:**` block naming the proof for that task's change, and the plan header lists the acceptance criteria the proofs must demonstrate. |
| executing-plans, subagent-driven-development | A task's proof entries are in the record before its completion line. After the final review's fixes, the done check runs before finishing-a-development-branch. |
| test-driven-development on its own | Record proofs as you go. The RED and GREEN runs are proof entries. Run the done check before finishing. |
| finishing-a-development-branch | The record is final: taken after the last commit. Before the PR opens, the descriptive text in the record (not commands, not output) goes through the clean-up-text skill. The record is attached to the PR under a `## Proof` heading, with screenshots uploaded where a way exists. |

## Common Rationalizations

| Excuse | Reality |
|--------|---------|
| "Tests pass, so it works" | Tests prove what they assert. Map the diff; a hunk no test reaches is unproven. |
| "The subagent reported green" | Its report is a claim. Read the output it saved, or run the command. |
| "The component test covers the UI change" | A mocked test does not prove the user experience. Run the app and look. |
| "I proved it before the review fix" | A proof proves the tree it ran on. Re-run the proofs that cover the touched files. |
| "One more cycle will get it" | Three cycles without full coverage means something is wrong with the change or the proof plan. Ask the user. |
| "This hunk is too trivial to prove" | Name the proof that exercises it. A trivial hunk is cheap to cover. |
| "I'll write the record at the end" | Output scrolls out of context. Record each proof where you saw it. |
| "The PR description is long enough already" | The reviewer reads the proof to trust the change. It belongs on the PR. |

## Red Flags

- "should", "probably", or "seems to" about a change's behavior
- A changed file that no proof entry names
- A proof older than the last commit that touched its files
- A screenshot you described but did not take
- A PR opened without a `## Proof` section

**All of these mean: run the done check before claiming anything.**
