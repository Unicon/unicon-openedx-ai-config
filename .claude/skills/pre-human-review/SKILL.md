---
name: pre-human-review
description: Use when a pull request is implemented and is about to go to a human reviewer, or when asked to get a PR ready for review, run an AI review before human review, or do the pre-review pass. Takes optional arguments --model (default opus) and --effort (default xhigh) for the review session. Works for backend and frontend PRs.
---

# Pre-human review

Every new PR gets an independent AI review before a human sees it. A fresh Claude session runs the repo's review skill on the PR, the developer decides what to do about each finding, the agreed findings are fixed, and the PR carries both the untouched review and a report of what was done about it.

## Arguments

| Argument | Default | Meaning |
| --- | --- | --- |
| `--model <model>` | `opus` | Model of the review session. Any value `claude --model` accepts: an alias such as `opus` or `sonnet`, or a full model id such as `claude-fable-5-1`. |
| `--effort <level>` | `xhigh` | Effort of the review session: `low`, `medium`, `high`, `xhigh` or `max`. |

When the developer names a model or effort in words ("review it with Sonnet at high"), use those values as the arguments: the model's alias or full id (Fable is `claude-fable-5-1`), and the effort level as named.

## Why the review runs as a separate top-level session

`backend-code-review` and `frontend-code-review` dispatch their own sub-agents, so they must run in a top-level session. By the Delegation rule in `CLAUDE.md`, a sub-agent cannot reliably dispatch another, so the review never runs through the Agent tool. It runs as a separate, headless Claude Code process started from the shell. That process also has a clean context: it has not seen the implementation conversation, so its review is not anchored on the implementer's reasoning.

## Steps

### 1. Settle the change first

The code, tests and PR description are final, and the `clean-up-text` pass that `CLAUDE.md` requires has run. The review must see the text that will ship.

The review fetches the ticket and the PR with `gh`, and `code-review-openedx` stops the review as blocked when it cannot. So the PR must be open on GitHub (a draft is fine), and `gh` must be installed and authenticated. If either is missing, tell the developer and stop. Never hand the review a local copy of the ticket or the PR description instead: the review skill rejects such a copy and ends blocked, so a local copy only wastes the session.

Collect the review's inputs:

- the repository path, the branch, its base commit, and the commits under review (for a stacked branch, only its own commits);
- the ticket, as a GitHub issue reference (`org/repo#N`);
- the PR, as a GitHub PR reference;
- the review skill: `backend-code-review` for a Python/Django change, `frontend-code-review` for a JS/TS frontend change.

The review skills write every file they produce, including the final review, to a `pr-reviews/` folder in the session's working directory. The review session runs from the workspace root, the folder that holds the repositories, so its result is `<workspace root>/pr-reviews/<ticket number>-review-result.md` unless the developer names another name.

### 2. Start the review session

Find the `claude` binary. Use `claude` when `command -v claude` finds it. Otherwise Claude Code runs as the VS Code extension, and its binary is in the newest extension folder:

```bash
CLAUDE_BIN=$(command -v claude || echo "$(ls -d ~/.vscode/extensions/anthropic.claude-code-*-linux-x64 | sort -V | tail -1)/resources/native-binary/claude")
```

On macOS the folder name ends in `-darwin-arm64` or `-darwin-x64` instead of `-linux-x64`. If neither finds a binary, stop and ask the developer where Claude Code is installed.

Run it from the workspace root, the folder that holds the Open edX repositories, so the review can read neighboring repos for companion changes. Run it in the background, and redirect its output to a log file:

```bash
"$CLAUDE_BIN" -p --model "<model>" --effort "<effort>" --permission-mode auto \
  "/backend-code-review Review PR <org/repo#PR>, branch <branch> in <repo path>, against base <base sha>, commits <shas>. The ticket is <org/repo#N>. Do not modify the repository, commit, or push. Name the final review pr-reviews/<N>-review-result.md." \
  > <scratch dir>/<N>-review.log 2>&1
```

Start the prompt with the review skill chosen in step 1 (`/backend-code-review` or `/frontend-code-review`). State every input in the prompt itself, because the review session knows nothing of this conversation. Name the PR, the ticket, and the commits that belong to this PR. A headless Claude Code session cannot start a ChatGPT agent, so the review skips its adversarial step and says so in the result. Wait for the harness to report that the background process finished, without polling it; a deep review can take tens of minutes. Then check that the output file exists and ends with the review's verdict. If it does not, read the end of the log and report the failure to the developer.

### 3. Triage every finding with the developer

Read the review file and check each finding against the code. Then show the developer one table: the finding, what it says in one sentence, and your recommendation (fix, do not fix with a reason, or a question for someone else). Stop and wait for the developer's reply: the developer decides each finding.

- A blanket answer ("fix all of them", "fix 1 to 5, drop 6") decides every finding it names.

- A finding the developer disagrees with is never implemented.
- A finding that is a question for a product owner or a maintainer is raised with them, and the PR description says so.
- A finding that would need a suppression directive (`# noqa`, `# pylint: disable`, `# type: ignore`, `// eslint-disable`) needs the developer's explicit approval of that directive, as `CLAUDE.md` requires. A blanket answer does not cover it.
- When the review has no findings, there is nothing to triage: go to step 5.

### 4. Fix the agreed findings

Delegate the fixes to an implementation sub-agent, on the model `CLAUDE.md`'s Delegation table names for writing code, with the review file's anchors and the developer's decisions in the prompt. Put each fix where the repo's commit conventions want it. Re-run the linters and the tests the change touches, and check the result yourself before going on. Commit and push only when the developer asks, as `CLAUDE.md` requires. The fixes get no second review session unless the developer asks for one.

### 5. Write the fix report

Write `<workspace root>/pr-reviews/<N>-fix-report.md`, next to the review, a Markdown file with three tables:

- **Fixed:** the finding, the fix, and where it was made. Each cell is one sentence; a fix with several parts may take more.
- **Not fixed:** the finding and the reason it was not fixed.
- **Raised separately:** the finding and where it went (a product owner, a maintainer, a follow-up ticket).

End it with the verification that ran after the fixes and its results.

### 6. Attach both files and hand over

The PR carries the review file exactly as the review session wrote it, and the fix report.

With the developer's approval, post both on the PR with `gh`, for example as one comment with each file in a collapsed `<details>` block. A GitHub comment holds at most 65,536 characters, so a longer review goes in a comment of its own, and one that still does not fit is attached as a file. If the developer would rather post them, give the full path of both files.

Then tell the developer the PR is ready for human review.

## Common mistakes

| Mistake | What to do instead |
| --- | --- |
| Running the review through the Agent tool. | Start a separate headless `claude -p` process from the shell, as step 2 shows. |
| Skipping the separate session because `claude` is not on PATH. | Use the VS Code extension's binary, as step 2 shows. |
| Deciding on your own which findings to fix or dispute. | Recommend, and let the developer decide each finding, as step 3 says. |
| Editing the review file, or summarizing it instead of attaching it. | Attach it unchanged, and put your view of it in the fix report. |
| Leaving the inputs implicit ("review my branch"). | Name the PR, branch, base, commits and ticket in the prompt. |
| Giving the review a local copy of the ticket or the PR description when `gh` is missing. | Stop and tell the developer: the review needs `gh` and an open PR, as step 1 says. |
