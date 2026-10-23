---
name: prepare-pr-review
description: Use when asked to prepare a pull request for a human line-by-line review in Plannotator, or when the user runs /prepare-pr-review with a PR URL. Reads an existing code review markdown file (asking for its path when none is given), maps the PR's manual testing steps to the code they run, and opens a guided walkthrough in Plannotator. Never posts to GitHub.
---

# Prepare a PR for line-by-line review

Command: `/prepare-pr-review <PR URL> [review file]`. The skill turns an existing code review file and the PR's manual testing steps into a saved Plannotator guide, opens the PR in Plannotator, and ends the turn. Jesper reads every line and posts their own comments. The PR on GitHub never changes.

Paths: `<skill_dir>` is the base directory printed when this skill loads ("Base directory for this skill: ..."). When no such line is shown, it is the folder that contains this SKILL.md. Use it in every script and reference path, because the session may run in any directory. `<artifacts>` is `/Users/jesperhodge/openedx/pr-reviews/<repo>-<n>/`, created with `mkdir -p`.

## Steps

**1. Pin the PR.** Parse the URL into `<owner>`, `<repo>`, and `<n>`, then run:

```bash
python3 <skill_dir>/scripts/fetch_pr.py <url> --out <artifacts>/pr.json
gh issue view <issue> --repo <issue owner/repo> --json number,title,body,updatedAt > <artifacts>/issue-<issue>.json
```

`fetch_pr.py` lists every changed file, including past the 100 files that `gh pr view` returns. Run `gh issue view` once per linked issue, taken from `closingIssuesReferences` and from issue references in the PR body. Use `url` from `pr.json` as the canonical PR URL below.

The review file path comes from the command. When none is given, ask Jesper for it and wait. This is the only question the skill asks. Check that the file exists and names this PR (its number, URL, or head SHA), and ask again if not. The skill never runs a code review.

The testing section is the text under the PR body's testing heading, which is any heading that mentions testing instructions, test steps, test plan, or "how to test". It runs up to the next heading of the same or higher level, and the heading line itself is excluded. Find it and choose one outcome. Say in one message what was found, then continue without waiting, except in the first outcome.

- **No usable section.** There is no testing section, or it holds no actionable step (only "run the tests", "see the ticket", "N/A"). Stop before any other work. Tell Jesper, and include a short draft comment asking the author to add manual testing instructions. State that the skill does not post it.
- **Vague steps.** A step leaves out where to go, what to do, or what should happen. Continue. The mapper sharpens these steps.
- **Usable steps.** Continue with the steps as written.

**2. Start the mapper, before reading the rest of the review file.** The clone is `/Users/jesperhodge/openedx/<repo>`. When it is missing, run `gh repo clone <owner>/<repo> <artifacts>/clone` and use that folder. Before dispatching, read only the review file's acceptance-criteria table, which is quick. Then read `<skill_dir>/references/mapper-brief.md` and replace every placeholder by plain string replacement, never `str.format`, because the brief's JSON example has literal braces.

| Placeholder | Value |
| --- | --- |
| `{pr_url}`, `{pr_number}`, `{head_sha}` | `url`, `number`, `headRefOid` from `pr.json` |
| `{base_repo_url}` | `https://github.com/<owner>/<repo>.git` of the PR's base repository |
| `{repo_clone}` | the clone path above |
| `{artifacts}`, `{skill_dir}` | the two folders defined at the top |
| `{testing_steps}` | the author's testing section, verbatim |
| `{criteria_text}` | the review file's criteria table. When it has none, the acceptance criteria from the linked issues, then the behavior the PR body describes, then "No acceptance criteria stated." |

Dispatch it with the Agent tool: `subagent_type: general-purpose`, `model: sonnet`, `run_in_background: true`, and the filled brief as the prompt. Do not add placement rules of your own. The brief decides which chapter holds each file, including test files. Go on to the rest of step 3 without waiting for it.

**3. Read the review file.** Copy it to `<artifacts>/review.md`, then write two files from it. Include only what the review file contains. Do not add, merge, or reword findings, and do not add findings of your own. The only text you write yourself is a missing finding title, below.

`<artifacts>/criteria.json`, from the review's acceptance-criteria table:

```json
{"criteria": [{"id": "AC1", "text": "quoted criterion", "implemented_at": ["src/x.tsx:12-30"], "tested_by": ["x.test.tsx::name"], "verdict": "Covered"}]}
```

`<artifacts>/findings.json`, from its findings and verdict line:

```json
{"verdict": "Ready to merge: with fixes. One sentence.", "findings": [{"severity": "Gap", "title": "Short title", "anchor": "src/x.tsx:304-308", "why": "One full sentence ending in a period."}]}
```

- Number criteria AC1 to ACn across all linked issues. Strip the table's surrounding quotes from the criterion text and keep any inner quotes. `tested_by` copies what the review says: `path::test name` when it names a test, otherwise the review's description as given. "none" or an empty cell becomes `[]`. `verdict` is copied from the review's Verdict cell. An anchor has its backticks stripped and is `path:line` or `path:start-end`. An empty, "none", or "-" Implemented-at cell becomes `[]`, never `["none"]`, because the composer rejects anything that is not an anchor. A row whose In scope cell starts with "no" stays out of `criteria.json`. List it in the summary message under "Criteria the review set aside", with the review's reason. Widen a single-line anchor to the enclosing function or block, read at the head SHA.
- `severity` is one of `Bug`, `Gap`, `Question`, `Suggestion`, `Nit`. A finding with no severity word, including one on a file the PR did not change, becomes `Question`.
- `why` keeps the review's own sentence and punctuation. Add a period only when the sentence has no closing punctuation at all, so a question keeps its "?".
- A finding with no title in the review gets a `title` of at most 8 words, taken from the finding's heading or first clause. It may only restate the review's point, and it is the only text the skill writes in its own words. A finding title and a code-ref role carry no trailing period.
- No criteria table: build the criteria from the linked issues, find each one's anchors by reading the diff at the head SHA, and use the verdict "Not in the review".
- A finding with no file location stays out of `findings.json`. List it in the summary message under "Findings without a location".
- No verdict line: use "The review file states no verdict."

**4. Check the mapper's output.** Wait for the mapper's completion notice, then run:

```bash
python3 <skill_dir>/scripts/guide_inputs.py --check <artifacts>
```

Exit 0 prints `Placement OK`. On exit 1, send the error text to the mapper with SendMessage, and check again after it fixes `chapters.json`. If it returns "Needs research" items, answer them with SendMessage.

**5. Compose the guide.**

```bash
python3 <skill_dir>/scripts/compose_guide.py --artifacts <artifacts>
```

On exit 1, show the error, stop, and offer the fallback below. The output lists `Guide:`, `Label:`, and `Change map:`. A `Warning:` line means the installed Plannotator version differs from the tested one. Show the warning to Jesper and offer the fallback.

**6. Launch.** Call the `plannotator` tool with `{"action": "review", "target": "<canonical PR URL>"}`. Open the PR by URL so Plannotator's PR mode can post comments to GitHub. Without the tool, run `plannotator review <url>` with `run_in_background: true` and `timeout: 7200000`, and tell Jesper that Ask AI in the browser lacks the workspace config, so questions work best in this chat.

End the turn with a summary message. It holds:

- the guide label to pick under Guide > previous guides (`PR #<n> prepared <YYYY-MM-DD HH:MM>`);
- the change map path;
- the component tree file path, when the review file names one. When it names none, leave this line out and say so in the message;
- the acceptance-criteria gap list, read from the `overview` of the first section ("Before you start") in the JSON file at the printed `Guide:` path;
- any "Findings without a location";
- any "Criteria the review set aside";
- the verdict line.

**7. Ask AI questions.** While the review is open, questions arrive as messages in this session. Answer from `review.md`, the issue files, and the code at the head SHA, citing `file:line`. If Ask AI or "check coverage" gets no answer while the review is open, tell Jesper to start a second Claude Code session in the same folder and ask there.

**8. "check coverage".**

```bash
python3 <skill_dir>/scripts/coverage_check.py --artifacts <artifacts>
```

Relay its output. Exit 2 means Plannotator has no progress for this PR yet.

## Fallback

Run this only after Jesper says yes to the offer in step 5, whether composing failed or a version warning came up. When you make the offer, tell Jesper that the script writes the user-level file `~/.plannotator/guide-instructions.md`, which stays in effect for every later Plannotator guide in any repo until it is deleted, and that an existing file is copied to a `.bak-<timestamp>` backup first.

```bash
python3 <skill_dir>/scripts/fallback_instructions.py --artifacts <artifacts>
```

The script prints `Backup: <path>` when it replaced an existing file. Then tell Jesper to click Guide in Plannotator and generate the guide. In this route the findings live only in the review file. After the guide is generated, offer to delete `~/.plannotator/guide-instructions.md`, or, when a backup was made, to restore it over that file.

## Rules

- Never post to GitHub. Never use Plannotator's external-annotations API, because it posts as Jesper's own comments.
- Never change the PR, its commits, or its branches.
- Never export a standalone guide or open a diff by patch file. Only a saved guide from `compose_guide.py`, opened through the PR URL, shows up in the live review.
- Only the top-level session dispatches sub-agents, and the only dispatch is the mapper.
