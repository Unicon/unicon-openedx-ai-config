---
name: skill-improver
description: Reviews recent developer corrections and promotes them into durable, principled edits of skills and CLAUDE.md. Use when the developer wants to improve how Claude works from recent feedback, asks to "improve our skills", "review recent corrections", "what have I corrected you on", "turn feedback into skill updates", "reflect on recent sessions", or runs a skill-improver pass. Covers gathering corrections from transcripts and memory, extracting the principle behind each correction, applying an evidence bar, routing each principle to the right home, conflict and duplication checks, and a per-principle approval gate.
---

# Skill Improver

Corrections the developer gives mid-session are the highest-signal input for
improving how Claude works in this repo. This skill turns those corrections into
durable, principled edits of the files that shape behavior: skills, CLAUDE.md
and its instruction files.

The hard part is not writing edits. It is getting at the principle behind a
correction instead of encoding the literal fix, and gating the write so the
instruction files neither bloat nor contradict themselves. The workflow exists
to enforce both.

## When this applies

Run on demand only, when the developer asks for an improvement pass. This skill
has no automatic trigger and no stop-hook. Typical openings: "improve our skills
from recent sessions", "what have I corrected you on lately", "turn that
feedback into skill updates", "reflect on the last few sessions".

## What it does not do

- It does not run automatically. The developer starts every pass.
- It does not write or curate memory files. It reads them, and recommends
  pruning entries that a promoted rule now covers, but the existing auto-memory
  mechanism owns memory.
- It does not self-merge. Edits land on a branch and open a pull request the
  developer reviews.
- It does not encode one-off soft preferences. Those stay in memory until they
  recur or escalate.

## Model and orchestration

- The main session keeps the strong model. Extracting the principle, judging the
  evidence bar, routing, conflict checks, and the approval gate are all judgment
  work. Do them yourself.
- Push the context-heavy reading into sub-agents so raw transcripts never enter
  the main context. Reading a transcript or an instruction doc is
  reading-and-reasoning: dispatch a **Sonnet** sub-agent, medium effort for a
  single short transcript, high effort when it must weigh several sessions or a
  long doc. Pass `model` explicitly on every dispatch.
- Never read a raw `*.jsonl` transcript into the main context. It is mostly tool
  output and is enormous. A sub-agent returns the handful of corrections, not the
  file.

## 1. Identify the base conversation

The developer names the conversation whose corrections you will mine. Get to one
certain match before reading anything.

- **Locate the transcript directory.** Claude Code stores one JSONL file per
  session under `${CLAUDE_CONFIG_DIR:-$HOME/.claude}/projects/<slug>/`, where
  `<slug>` is the project's working directory with every non-alphanumeric
  character replaced by `-` (so `/Users/dev/openedx-core` becomes
  `-Users-dev-openedx-core`). Derive it, never hardcode it:
  ```bash
  BASE="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/projects"
  SLUG="$(pwd | sed 's/[^A-Za-z0-9]/-/g')"
  PROJDIR="$BASE/$SLUG"
  ```
  If `$PROJDIR` is missing, or its transcripts' `cwd` field does not match the
  current directory, fall back to matching ground truth: the right directory is
  the one under `$BASE` whose `*.jsonl` files carry `"cwd":"<current repo path>"`.
- **Only top-level files are conversations.** `<uuid>/subagents/agent-*.jsonl`
  and `<uuid>/tool-results/*.txt` are sub-agent and tool-output sidecars, skip
  them.
- **Ask for the name.** If the developer did not already give it, ask for the
  beginning of the conversation's title. Recency is the prior: the most recent
  sessions, and the last one above all, are the likeliest target.
- **List candidates most-recent-first.** The current title is the **last**
  `type:"ai-title"` record in a file; titles get rewritten through a session, so
  an earlier one is stale. `jq` is not installed here, so parse with `python3`:
  ```bash
  cd "$PROJDIR"
  for f in $(ls -t *.jsonl); do
    python3 -c "
  import json
  t=[json.loads(l)['aiTitle'] for l in open('$f') if l.strip() and json.loads(l).get('type')=='ai-title']
  print('$f', '->', t[-1] if t else '(untitled)')"
  done
  ```
  Output is one short title per session, so it can run in the main session.
- **The newest file is usually this session.** The top entry by recency is the
  run you are in now; it contains this skill-improver invocation. Treat the most
  recent *other* conversation as the default target, not this one.
- **Match, then confirm.** Case-insensitive prefix match on the current title;
  fall back to the `lastPrompt` field (`type:"last-prompt"`, the developer's most
  recent free-text prompt) when the title is generic. One clean match: state it
  back and confirm. Several or none: show the recent list with titles and times
  and clarify. Do not start reading until exactly one conversation is agreed.

## 2. Gather corrections

- Dispatch a **Sonnet** sub-agent to read the agreed transcript and return the
  developer's corrections, nothing else. Give it the file path and these
  extraction rules, because `type:"user"` records are mostly not human text:
  - Keep a record only if `type == "user"`, `isMeta` is absent or false, and
    `message.content` is a **list** containing a `{"type":"text"}` block. That is
    genuine developer prose.
  - Drop `tool_result` blocks (tool output threaded back as a user turn),
    string-valued `message.content` (slash commands and command stdout), `isMeta`
    caveat wrappers, and `queue-operation` records (they carry no `message`).
  - A correction is a turn where the developer pushed back, redirected, tightened
    scope, rejected an approach, or stated a preference or standard. A plain task
    instruction is not a correction. Return each with its verbatim quote, the
    `timestamp`, and one line of what you were doing when it landed.
- Reference extractor for the sub-agent:
  ```bash
  python3 - "<file>.jsonl" <<'PY'
  import json, sys
  for l in open(sys.argv[1]):
      l = l.strip()
      if not l: continue
      o = json.loads(l)
      if o.get('type') != 'user' or o.get('isMeta'): continue
      c = o.get('message', {}).get('content')
      if not isinstance(c, list): continue
      for b in c:
          if isinstance(b, dict) and b.get('type') == 'text':
              print(o['timestamp'], '::', b['text'][:400])
  PY
  ```
- Read the project memory too, so each correction is judged against what is
  already recorded. Memory lives in `$PROJDIR/memory/` (same directory as the
  transcripts); start at `MEMORY.md`. This project may have no memory dir yet, in
  which case there is
  nothing to cross-reference. A bare `MEMORY.md` index you can read directly;
  push to a sub-agent only if the entries themselves need reading in bulk.

## 3. Extract the principle

- For each correction, write the general rule it implies, not the literal fix.
  The correction is evidence; the principle is what you promote. This is the
  judgment that justifies keeping the main session on the strong model.
- Ask: what would I have needed to believe to avoid this correction? That belief,
  stated as a standing instruction, is the principle.
- Example: "don't read the whole file into context, dispatch a sub-agent" is not
  the rule "never read this file"; it is "push context-heavy reading into a
  sub-agent and reason over its summary."
- Discard corrections with no generalizable principle behind them: a one-time
  factual fix, a typo, a detail true only of one file.

## 4. Apply the evidence bar

Promote a principle only when it clears the bar. Below it, it stays a soft
preference for memory.

- **Recurrence or force.** It appeared more than once, or the developer stated it
  as a standard ("always", "never", "from now on"), or corrected the same thing
  again after you had already done it once.
- **Generalizes.** It holds beyond the one file or task in front of you.
- **Not already covered.** No existing instruction already says it (confirm in
  step 6).
- A single, softly-worded, one-off preference does not clear the bar. Note it and
  leave it for the auto-memory mechanism; do not promote it.

## 5. Route to the right home

Send each promoted principle to exactly one home.

- **CLAUDE.md or a doc it references** for a cross-cutting standard that should
  hold across tasks. Put it in the scoped doc when it is scoped (a frontend rule
  in `frontend-app-authoring-architecture-overview.md`), in `CLAUDE.md` when it is
  general.
- **A skill** for a principle that is really a procedure for one kind of task.
  Edit the relevant `.claude/skills/<name>/SKILL.md`. If it needs a skill that
  does not exist, flag it and stop: a new skill is its own piece of work, not a
  line edit.
- **Memory (read-only here)** for a soft or still-thin preference. The auto-memory
  mechanism owns it; this skill does not write it. Recommend the entry to the
  developer, and recommend pruning any memory entry a newly promoted rule now
  supersedes.
- A principle that reads like a hard rule has no separate rules file to live in;
  it belongs in `CLAUDE.md` (the first bullet), not a new mechanism.

## 6. Conflict and duplication checks

Before writing, read the target and check the principle against what is already
there.

- **Duplicate:** a line already says it. Sharpen that line if needed; do not add
  a second.
- **Conflict:** a line says the opposite. Surface both versions to the developer
  and let them decide. Never silently override an existing instruction.
- **Bloat:** prefer editing or tightening an existing instruction over appending
  a new one. Instruction files earn their keep by staying short.

## 7. Approve and apply

- Gate per principle, not per pass. For each one show the principle, the evidence
  (quoted corrections), the chosen home, and the exact diff. Get a go or no-go on
  that one before moving to the next. Do not batch-approve.
- Apply only the approved edits, on a new branch, in house writing style: US
  spelling, no em dashes, current state not history. Commit with a conventional
  message (`docs:` for instruction files) and open a pull request for the
  developer to review.
- Do not self-merge, and do not push to `main`.
- Report what you did not promote and why, so the developer can override the bar
  when they disagree.

Every promoted line must trace to a quoted correction. If you cannot cite the
evidence, it does not belong in an instruction file.
