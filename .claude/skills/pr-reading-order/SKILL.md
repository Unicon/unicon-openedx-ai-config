---
name: pr-reading-order
description: Use when asked for a reading order, a review map, or the main threads of execution of a pull request, so a human reviewer knows which file and function to read first and where to go next; when a reviewer says a PR is too long to understand quickly; or when asked to show which acceptance criteria each part of a PR implements, with blast radius per piece. Works for any repository with a linked ticket whose acceptance criteria are Gherkin scenarios.
---

# PR reading order

Turns a PR into one SVG that tells a human reviewer what to read, in what order. The SVG has
1 to 5 threads of execution, each a column of boxes from top to bottom joined by arrows. Each
box names one file or function to read, says in one sentence what it does, and is colored from
green to red by blast radius (0 to 100). Beside each box sits the verbatim Gherkin of every
acceptance criterion (AC) that box implements, plus any behavior the box adds that no AC asked
for. Below the threads come the ACs that no thread covers, with where each is implemented or
that it is missing, and then everything else in the diff, to skim last.

The goal is that the reviewer reads the threads (source boxes, then the thread's test box) and
understands the PR, then skims the rest. Threads are the major flows, not a complete inventory.

The analysis is yours; the drawing is deterministic. You write a JSON spec, and
`scripts/render_reading_order.py` renders it, copying AC text from the ticket itself and
refusing a spec that leaves an AC or a changed file out. Never hand-write SVG.

## Steps

**1. Pin the PR (top-level session).** `gh pr view <pr> --json title,headRefOid,files,body`.
Save the changed paths, one per line, to `files.txt`. Find the linked ticket or tickets (PR
body, or the review file when one is given) and save each body with
`gh issue view <n> --repo <owner/repo> --json body -q .body > ticket<n>.md`. When a review file
is given, compare its head SHA with `headRefOid`; if they differ, its line numbers are stale,
so say so in the subtitle and use the live head's line numbers.

**2. Read the diff (sub-agent).** Per the Delegation rule in `CLAUDE.md`, dispatch one
`general-purpose` Sonnet sub-agent, model passed explicitly, with the brief in
`references/diff-reader-brief.md` filled in. It returns the changed pieces with head-SHA line
ranges, candidate threads with their tests, leftovers, and blast-radius scores.

**3. Write the spec (top-level session).** Before relying on the sub-agent's line numbers for
the core pieces, read those files at the head SHA
(`gh api "repos/<head owner>/<repo>/contents/<path>?ref=<sha>" -H "Accept: application/vnd.github.raw"`);
hunk headers alone give only approximate lines. Then:
- **Choose 1 to 5 threads.** A thread is one end-to-end flow of data or control through changed
  code. Put first the thread whose output the others read (usually the data or fetch path).
- **Order the steps** in each thread the way the data flows, producer before consumer, then end
  the thread with one or two `test` steps naming the tests that exercise it, with line numbers;
  one test step may list tests from several files.
- **`does` is exactly one sentence** about what the piece does now, taken from the code.
- **`blast`** (0 to 100) is how much breaks, and how widely, if the piece is wrong. Shared hooks,
  cache keys, context providers and API clients score high; leaf components, strings, styles
  and tests score low. Add a short `blastWhy` on source steps; it is optional elsewhere.
- **`acs`** lists the scenario titles exactly as the ticket writes them, each at the one step
  whose own lines implement it. An AC goes on a step only when a reviewer reading that step's
  lines would see the behavior the AC describes. An AC implemented by a style rule, by unchanged
  code, by the backend, or by a piece too small to be a step goes to `elsewhere` instead; most
  PRs have some. When several steps implement an AC together, put it on the step whose lines
  decide the outcome its "Then" lines check. A source step with no AC is fine. Prefix with the ticket number (`"682:Title"`) only when two tickets share a
  title.
- **`notInAcs`** lists behavior the step adds that no AC asked for, one sentence each.
- **`elsewhere`** holds every AC that no thread step carries, with `where` it is implemented and
  a `note` on how far it is tested. Set `"missing": true` only for an AC that nothing implements;
  for a partly implemented AC, say what is missing in the `note`.
- **`leftovers`** holds every changed file that no step or `elsewhere` entry names, one sentence
  each, including test files that only update mocks or fixtures. One `where` may name several
  files.
- **`where`** is a path relative to the base directory the subtitle names, plus line numbers.
  The changed-files check matches on the bare file name (`api.ts` in `data/api.ts:60-69`).

**4. Render and verify (top-level session).** `scripts/` is relative to this skill's directory;
pass absolute paths for the script and every file when running from elsewhere.

```bash
python3 scripts/render_reading_order.py SPEC.json --acs 683=ticket683.md --changed-files files.txt --svg reading-order-pr<N>.svg
```

Pass one `--acs TICKET=PATH` per ticket; `TICKET` is the ticket number, used as the label beside
each AC and as the prefix that tells two tickets' same-named ACs apart. The script exits with a message naming any AC that appears
nowhere, any unknown AC title (with the closest match), any changed file no `where` names, and
any `does` (on a step or a leftover) longer than one sentence. Fix the spec and re-render until
it passes. On success it prints the SVG path, then one line stating how many ACs sit in threads and elsewhere and
how many changed files it checked; confirm those counts match the ticket and the PR. Then look at
the result: when Google Chrome is installed, screenshot it headless
(`--headless=new --screenshot=out.png --window-size=1640,<height>`) and read the image, and fix
any overlap by changing the spec.

Write the SVG next to the review file when one is given, otherwise to the session scratchpad
directory, never inside the repository under review. Open it for the user (`open <file>.svg` on
macOS opens it in the browser).

**5. Deliver.** Give the absolute path of the SVG and, in at most five lines, the threads in
reading order and any AC marked missing.

## Spec format

```json
{
  "title": "Reading order for PR #6: <PR title>",
  "subtitle": "owner/repo PR #6, head <short sha>. Paths are under src/feature/.",
  "threads": [{
    "title": "Thread 1: the course list reports its keys, and the fetch is scoped to them",
    "summary": "One or two sentences on the flow, from its trigger to what it produces.",
    "steps": [
      {"name": "useThing", "where": "data/apiHooks.ts:34-59", "kind": "source",
       "does": "One sentence.", "blast": 80, "blastWhy": "shared by every mutation",
       "acs": ["Exact scenario title"], "notInAcs": ["One sentence."]},
      {"name": "Hook tests", "where": "data/apiHooks.test.tsx:51, 75", "kind": "test",
       "does": "One sentence.", "blast": 10}
    ]
  }],
  "elsewhere": [{"ac": "Exact scenario title", "where": "file:lines", "note": "Implemented, untested.", "missing": false}],
  "leftovers": [{"where": "messages.ts:78-157", "does": "One sentence.", "blast": 8}],
  "footnotes": ["Optional lines at the bottom."]
}
```

`kind` is `source` or `test`; test boxes get a dashed border. `blast` is an integer 0 to 100 and
is optional on `elsewhere` entries. `testdata/pr6-spec.json` is a regression fixture for the
renderer; do not read it when building a spec.

## Common mistakes

| Mistake | Fix |
| --- | --- |
| Paraphrasing an AC in the spec | Give the exact scenario title; the renderer copies the text. |
| One thread per file | A thread is a flow across files; files are its steps. |
| Ten threads to cover everything | Keep 1 to 5; the rest goes to `elsewhere` and `leftovers`. |
| Tests in a separate thread | End each thread with the tests for that thread. |
| Every AC forced onto some step | Put an AC on a step only when that step's lines implement it; the rest go to `elsewhere`. |
| Line numbers from an older review or head | Use line numbers at the live head SHA. |
| Scoring blast radius by lines changed | Score it by consumers and by data or cache impact. |
| Editing the SVG by hand | Change the spec and re-render. |
