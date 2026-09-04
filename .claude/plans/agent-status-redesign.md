# Agent status: redesign plan

## The outcome we are aiming for

One fantastic overview of what every Claude session is doing, integrated with `/todo`, that
hides sessions the developer no longer cares about, and that costs approximately nothing in
tokens or latency.

## What is wrong today

`\.claude/hooks/agent-status.py` runs on `UserPromptSubmit` and `Stop`, writing one file per
session under `.claude/agent-status/`, each holding `name|task|status`. Six things are broken,
all verified against the live machine:

| Problem | Evidence |
| --- | --- |
| The task label is the first 60 characters of the *opening* prompt, so it is truncated and stale. | `openedx-core-2a` reads `<task-notification> <task-id>a906a14f88355abed</task-id> <to`. |
| Claude Code injects `<ide_opened_file>`, `<task-notification>` and `<system-reminder>` blocks into the same user record as the real prompt, so the captured "task" is usually injected boilerplate. | 6 of 14 status files begin with `<ide_opened_file>The user opened the file /Users/jesperhodge`. |
| Output is a directory of 14 files, one per session. | `ls .claude/agent-status/` |
| Status is guessed by testing whether the last 3 characters of the final message contain `?`. | `command_end()` in the current script. |
| Nothing ages out, so 23-hour-old abandoned tabs sit alongside live work. | Of 23 live sessions, 12 have been untouched for more than 18 hours and 4 have no transcript at all. |
| The `/todo` skill treats the session name as a unique handle, but derived names collide. | Two live sessions are named `unicon-openedx-ai-config-6a` and two more `unicon-openedx-ai-config-f2`. |

## The key discovery

**Claude Code already writes an AI-generated, continuously-refreshed task summary for every
session, and we were ignoring it.** Each transcript contains repeated records of the form
`{"type":"ai-title","aiTitle":"…","sessionId":"…"}`, plus `{"type":"custom-title","customTitle":…}`
when the developer has renamed the chat, and `{"type":"last-prompt","lastPrompt":"…"}` holding
the latest genuine human instruction with none of the injected boilerplate.

These records solve the whole "summarize the task" problem for free. Reading the *last*
`ai-title` in a transcript rather than the first also solves staleness, because Claude Code
rewrites the title as the conversation moves on. Measured examples:

| Session | Old label (first 60 chars of opening prompt) | `ai-title` |
| --- | --- | --- |
| `unicon-openedx-ai-config-43` | `/todo important for today: review https://github.com/openedx` | PR #39054 and review #676 |
| `openedx-core-2a` | `<task-notification> <task-id>a906a14f88355abed</task-id> <to` | Issue 642 implementation |
| `unicon-openedx-ai-config-ec` | `<ide_opened_file>The user opened the file /Users/jesperhodge` | Review 641 implementation agent work |

Nothing about this costs tokens. It is a file read.

## Third-party tools: surveyed, and rejected with reasons

The developer asked whether an existing tool does this properly. It was worth asking, and the
answer is no.

| Tool | Why it does not fit |
| --- | --- |
| `claude agents --json --all` (first-party CLI) | **Partially adopted, see below.** It reliably enumerates live sessions, but for interactive sessions it returns only `pid, cwd, kind, name, sessionId, startedAt`. Verified: no `state`, no `waitingFor`, no summary. Those richer fields exist only for background sessions dispatched from agent view. |
| `claude-sessions-monitor` | Closest community match, but 6 stars, and it reimplements exactly the transcript parsing below while adding an install and an external dependency for the one thing we need. |
| `claude-code-dashboard`, `claude-code-monitor` | Browser dashboards. Not a `cat`-able feed for a skill, and a second UI to keep alive. |
| `ccmanager`, `claude-squad`, `vibe-kanban` | Session *launchers* and orchestrators. They only track sessions started through them, which would mean changing how every session is launched. |
| Happy Coder | Solves "notify me when blocked", not "give me an overview". |
| `ccusage`/`cchistory` | Retrospective token-spend reporting. Wrong problem. |
| Claude Code OpenTelemetry export | No metric or event reports per-session current activity. Built for aggregate cost dashboards. |
| `claude-notifier` (already installed globally) | Its `_lib/session-label.js` already reads `ai-title`, which is how this discovery was made. But it is a desktop-notification tool, and its per-session state files are unreliable for our purposes: `claude-notifier-task-start/` still held a file for a session idle 17 minutes. We should not build on another tool's internals. |

We adopt `claude agents --json --all` for the session inventory, because it is a documented,
first-party, scriptable surface that already filters to live sessions. This removes the current
script's hand-rolled `~/.claude/sessions/*.json` scanning and `os.kill(pid, 0)` liveness checks.
It returned 23 live sessions from 47 registry files, and costs 205ms.

## Three plans considered

### Plan A: keep the hook-driven design and enrich it

Keep `UserPromptSubmit` and `Stop`, add `PermissionRequest`, `PreToolUse:AskUserQuestion`,
`Notification` filtered to `idle_prompt`, and `SessionEnd`. Write status transitions into one
JSON state file guarded by `flock`. Take the task label from `ai-title`.

Rejected. Six hook registrations spawn a subprocess on every prompt and every turn end. The
accumulated state file drifts from reality whenever a hook is missed, which is exactly how
today's `(task not recorded)` rows appear. Worst of all, hooks only take effect for sessions
started *after* the settings change, so all 23 currently-open sessions would stay broken until
each one is restarted.

### Plan B: derive everything at read time, and delete the hooks (recommended)

`agent-status.py` becomes a pure reader. On each run it asks `claude agents --json --all` for the
live inventory, then makes one tail pass over each live session's transcript to extract the
title, the latest real prompt, the recent tool activity, and the pending tool state. Status is
computed from ground truth every time. The only persisted state is which sessions the developer
has dismissed.

I prototyped this end to end against all 23 live sessions. It produced a correct, meaningful
title for every session that has one, and ran in **0.31 seconds total** (0.21s of that is the
`claude agents` call; the transcript scanning for all 23 sessions took 0.04s).

Why this is the right shape:

- It cannot drift, because nothing is remembered. What you read is computed from the transcript.
- It works immediately for all 23 open sessions, with no restarts and no `(task not recorded)`.
- Removing the two hooks is a small performance *gain*: no Python subprocess on every prompt
  submit and every turn end.
- With no concurrent writers there is no locking problem, so "a single output file" becomes
  trivially correct rather than something we have to defend with `flock`.
- It is substantially less code than what exists today.

The one thing derivation cannot know is developer intent: whether they have already looked at a
finished session. That single fact is what the state file holds.

### Plan C: Plan B plus hooks for precise blocked-state signals

Plan B, plus `PermissionRequest` and `PreToolUse:AskUserQuestion` hooks so that "blocked on you"
is recorded as fact rather than inferred.

Rejected as unnecessary, because the prototype showed the inference is already sound. A
`tool_use` block with no matching `tool_result` means that tool call has not completed; if the
transcript has also been quiet for a while, the session is sitting at a prompt waiting for the
developer. The prototype correctly reported `pending=['Bash']` for the session that was mid-call.
Keep this in reserve: if the derived blocked-state proves unreliable in practice, adding these
two hooks later is an additive change that does not disturb the rest of the design.

**Chosen: Plan B.**

## The design

### Signals, and where each comes from

| What we need | Source | Verified |
| --- | --- | --- |
| Which sessions are alive | `claude agents --json --all`, filtered to `kind == "interactive"` | Yes, 23 sessions, 205ms |
| Repo and worktree | `cwd` from the same call | Yes |
| Task summary | last `ai-title`, overridden by last `custom-title` | Yes, present in all 20 ai-config transcripts |
| Latest real instruction | last `last-prompt` record | Yes, e.g. "Check PR #39054 as done. Add review #676 to the daily goals." |
| Currently blocked | `tool_use` with no matching `tool_result` | Yes |
| Working vs idle | transcript file mtime | Yes |
| What it has been doing | `tool_use` names counted since the last real user turn | Yes |
| Running subagents | `<project>/<sessionId>/subagents/*.meta.json` → `agentType`, `description`, `model` | Yes |
| Already-seen sessions | our own dismissal file | New |

Note that subagent turns live in separate files under `subagents/`, not inline in the main
transcript, so the main transcript needs no `isSidechain` filtering.

### Status values

Derived per session, in priority order:

| Status | Rule |
| --- | --- |
| `needs answer` | An unanswered `AskUserQuestion` tool call. |
| `needs permission` | Some other unanswered `tool_use`, and the transcript has been quiet for more than 60s. |
| `working` | Transcript modified within the last 90s, or an unanswered `tool_use` more recent than that. |
| `finished` | Alive, quiet, and the last thing written was assistant text. |
| `interrupted` | The process is gone but the last turn never completed. |
| `closed` | The process is gone and the last turn did complete. |
| `never used` | Alive with no transcript: an empty editor tab. |

### Relevance, which is the point of the exercise

Three buckets, printed in this order, most urgent first: **needs you**, **working**, **idle**.

Hide, rather than print:
- Sessions dismissed by the developer whose transcript has not changed since dismissal.
- Sessions idle for more than 24 hours, which are abandoned tabs.
- Sessions with no transcript.

Each hidden group is reported as a single count line, never as rows, so nothing disappears
silently. On the current machine state this turns 23 rows into roughly 6 relevant ones.

### Output

`list` writes one rendered file, `.claude/agent-status.md`, and prints the same text to stdout,
which is what `/todo` already consumes. `--json` emits the structured form for a caller that
wants to parse rather than read. This satisfies "make the output a single file" without adding
per-session shards back in a different shape.

Sketch of the rendering:

```
NEEDS YOU
  openedx-core-2a       Issue 642 implementation                needs answer     2m
      asks: Which migration strategy should the leaf status use?
  ai-config-43          PR #39054 and review #676               finished        18m

WORKING
  ai-config-f2 (34935)  Agent-status hook and output improvement  working        4s
      ran 23 commands, 2 subagents: Research third-party trackers, Map session data

IDLE
  openedx-core-bb       GitHub issue 641 implementation         finished         17m

3 sessions hidden: 2 dismissed and unchanged, 1 abandoned for over 24h.
4 open tabs have never been used.
```

### Session identity

Key everything by `sessionId`, never by name, because derived names collide: two live sessions
are currently named `unicon-openedx-ai-config-6a` and two more `unicon-openedx-ai-config-f2`.
When a name is ambiguous, print the pid alongside it so the developer can tell the rows apart,
and use `sessionId` for `dismiss`.

### Dismissal

`agent-status.py dismiss <session-id-or-name>` records the session id and the transcript mtime at
the moment of dismissal. The row stays hidden until the transcript changes, at which point the
session has been picked back up and reappears on its own.

This replaces the fragile procedure the `/todo` skill performs today, which compares a timestamp
it wrote into `my-todo-log.md` against the last-change time printed by the status command. That
bookkeeping moves out of the skill's prose and into one line of code.

## Files to change

| File | Change |
| --- | --- |
| `.claude/hooks/agent-status.py` | Rewrite as a reader with `list`, `--json`, and `dismiss`. Delete `start`, `end`, and the registry and pid scanning. |
| `.claude/settings.json` | Remove the `UserPromptSubmit` and `Stop` hook registrations. |
| `.claude/settings.local.json` | Update the two allowlisted command strings. |
| `.gitignore` | Replace `.claude/agent-status/` with `.claude/agent-status*` to cover the new file and the state file. |
| `.claude/skills/todo/SKILL.md` | Rewrite the *Keeping IN FLIGHT true* section against the new statuses, and replace the log-timestamp dismissal procedure with `dismiss`. |
| `.claude/agent-status/` | Delete the stale directory. |

## Constraints for the implementer

- System Python is **3.9.6**. No `match`, no `X | Y` type unions, no `dict | dict`.
- Match the existing file's style: module docstring explaining *why*, `%`-style formatting,
  small named functions, comments that explain rather than narrate.
- Never crash on a missing or malformed transcript. A session we cannot read is still a row, with
  whatever we do know about it.
- Read only the tail of a transcript, not the whole file. Transcripts run to 3.87MB, median
  286KB. A 400KB tail was sufficient for every session tested; fall back to a head read if no
  title is found in the tail.
- Treat the transcript schema as unversioned and liable to change between Claude Code releases,
  because the docs say exactly that. Every field access is defensive, and an unrecognized shape
  degrades to a partial row rather than an exception.
- `claude agents --json` may fail or be absent. Fall back to reading `~/.claude/sessions/*.json`
  with a `kill -0` liveness check, which is what the current script does.
- Verify before reporting done: run `list` and `--json` against the real machine, confirm the
  live session count matches `claude agents --json --all`, confirm no row shows an
  `<ide_opened_file>` artifact, and time the run.

## As built: where the implementation diverged from this plan

Three things above were wrong or underspecified, and the implementation follows the corrected
form. They are recorded here so the plan does not contradict the code.

- **There is no `closed` status, and `interrupted` means something else.** The plan defined both
  in terms of a process that has exited. Verified: `claude agents --json --all` and the
  registry fallback both return only live processes, so a session whose process is gone never
  appears as a row at all. `interrupted` therefore reports a *live* session whose turn was
  stopped before it finished, which is detected from a final transcript record reading
  `[Request interrupted by user]`. This is the case that matters in practice, and a session the
  developer closes drops off the overview on its own.
- **`working` needed a stricter rule.** A first pass returned `working` whenever the last
  transcript record was a user turn with no pending tool call, which reported a session
  `working  2h` two hours after its turn was stopped. The only path to `working` is now a
  transcript modified within the last 90 seconds.
- **The relevance thresholds were too generous.** A 24-hour cutoff still printed twelve `IDLE`
  rows, six of them between 18 and 23 hours old, which is the noise the tool exists to remove.
  The cutoff is eight hours, and `IDLE` prints at most the six most recently active rows.

One bug found in review after the fix round is also worth recording, because it is the kind that
reports success while doing the wrong thing: `dismiss` accepted a session name, and on a name
shared by two live sessions it dismissed whichever it found first. It now refuses an ambiguous
name and prints each candidate's session id.

Remaining gap: the script has no automated tests. It was verified empirically against the live
machine, but the status-derivation, truncation and hiding rules are exactly the kind of logic
that would benefit from synthetic transcript fixtures.
