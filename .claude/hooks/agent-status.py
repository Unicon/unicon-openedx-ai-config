#!/usr/bin/env python3
"""Show what every live Claude Code session is doing, computed fresh on each read.

Nothing here is written by a hook anymore. `claude agents --json --all` already knows
which sessions are alive, and every session's own transcript already carries an
AI-generated task title (`ai-title`, overridden by `custom-title` if the session was
renamed) that Claude Code keeps rewriting as the conversation moves on. Reading the
last of each, plus the last `last-prompt` record and the tail end of tool activity, is
enough to answer "what is this session doing" without a hook firing on every prompt
and every turn, and without a state file that can drift from what actually happened.

`list` (the default) renders three buckets, most urgent first: NEEDS YOU (blocked on a
human decision), WORKING (modified in roughly the last minute and a half), and IDLE
(finished and quiet). It writes the same text to agent-status.md and prints it to
stdout, because /todo reads the file and a human reads the terminal. `--json` emits
the same data in structured form for a caller that wants to parse it. `dismiss
<session-id-or-name>` records a session's transcript mtime so its row stays hidden
until that mtime changes, meaning the session was picked back up.

Session identity is always the session id, never the name Claude Code derives for a
session: those names collide (two live sessions can both be named
unicon-openedx-ai-config-6a), so a name alone cannot tell two sessions apart. When a
displayed name is ambiguous, the pid is printed alongside it.

The transcript's line-by-line schema is not versioned, and Claude Code's own docs say
it can change between releases, so every field access below is defensive: a record we
cannot make sense of is skipped, not raised. A session we cannot read is still a row,
with whatever we do know about it.
"""

import glob
import json
import os
import subprocess
import sys
import time

HOOKS_DIR = os.path.dirname(os.path.abspath(__file__))
CLAUDE_DIR = os.path.dirname(HOOKS_DIR)
OUTPUT_PATH = os.path.join(CLAUDE_DIR, "agent-status.md")
STATE_PATH = os.path.join(CLAUDE_DIR, "agent-status-state.json")

CLAUDE_BIN = "claude"

# 400KB tail was enough to find every live session's latest title when this was
# prototyped against the real machine; transcripts run to 3.87MB, median 286KB.
TAIL_BYTES = 409600
WORKING_SECONDS = 90       # quiet less than this and a session counts as actively working
QUIET_SECONDS = 60         # an unanswered tool call quiet longer than this needs a permission decision
ABANDONED_SECONDS = 8 * 60 * 60  # idle longer than this and a session is an abandoned tab, not a task
TITLE_CHARS = 60
ASK_CHARS = 140            # the rendered "asks:" line is read on every /todo invocation
IDLE_MAX_ROWS = 6          # further idle rows roll into the hidden count instead of printing

# Claude Code writes this exact text as a "user" record when the developer stops a
# turn. It is not a prompt, so it must never surface as one, and its presence is the
# only reliable signal that the turn ended by interruption rather than completion.
INTERRUPT_PREFIX = "[Request interrupted by user"


# ---------------------------------------------------------------------------
# Session inventory
# ---------------------------------------------------------------------------

def live_sessions():
    """Every live interactive session, keyed by session id.

    `claude agents --json --all` is a documented, first-party surface that already
    limits itself to running processes. If it is missing, fails, or returns something
    we cannot parse, fall back to scanning the session registry files Claude Code
    writes itself and checking each pid by hand, which is what this script did before
    that CLI command existed.
    """
    try:
        result = subprocess.run(
            [CLAUDE_BIN, "agents", "--json", "--all"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr)
        sessions = json.loads(result.stdout)
        if not isinstance(sessions, list):
            raise ValueError("unexpected shape from `claude agents --json --all`")
    except Exception:
        return fallback_sessions()
    live = {}
    for entry in sessions:
        if not isinstance(entry, dict) or entry.get("kind") != "interactive":
            continue
        session_id = entry.get("sessionId")
        if session_id:
            live[session_id] = entry
    return live


def fallback_sessions():
    """The same inventory, built by hand when the `claude` CLI is unavailable."""
    live = {}
    for path in glob.glob(os.path.expanduser("~/.claude/sessions/*.json")):
        try:
            with open(path) as handle:
                entry = json.load(handle)
        except Exception:
            continue
        if not isinstance(entry, dict) or entry.get("kind") != "interactive":
            continue
        session_id = entry.get("sessionId")
        if session_id and process_alive(entry.get("pid")):
            live[session_id] = entry
    return live


def process_alive(pid):
    if not isinstance(pid, int):
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True  # alive, just not ours to signal
    except OSError:
        return False
    return True


def transcript_path(session_id, cwd):
    """Where a session's transcript lives, by slugging its cwd the way Claude Code does.

    /Users/x/y becomes -Users-x-y. If that guess is wrong, for instance because the
    session's cwd changed after the transcript file was created, fall back to a glob
    across every project directory for a file named after the session id.
    """
    if cwd:
        slug = "-" + cwd.strip("/").replace("/", "-")
        direct = os.path.expanduser("~/.claude/projects/%s/%s.jsonl" % (slug, session_id))
        if os.path.exists(direct):
            return direct
    matches = glob.glob(os.path.expanduser("~/.claude/projects/*/%s.jsonl" % session_id))
    return matches[0] if matches else None


# ---------------------------------------------------------------------------
# Transcript scanning
# ---------------------------------------------------------------------------

def empty_transcript_info():
    return {
        "ai_title": "",
        "custom_title": "",
        "last_prompt": "",
        "last_assistant_text": "",
        "pending_tools": {},     # tool_use id -> {"name": ..., "question": ... or None}
        "turn_tool_counts": {},  # tool name -> calls made since the last genuine user turn
        "last_record_type": "",  # "assistant" or "user", whichever type was written last
        "interrupted": False,    # the last user record was the interrupt marker, not a prompt
    }


def read_lines(path, size_limit, from_end):
    """The lines of a file, from its end or its start, within size_limit bytes.

    Reading only a slice of a multi-megabyte transcript is what keeps this script
    fast; TAIL_BYTES from the end holds the most recent activity, and a head read is
    only used as a fallback when the tail has no title in it.
    """
    try:
        size = os.path.getsize(path)
        with open(path, errors="replace") as handle:
            if from_end:
                if size > size_limit:
                    handle.seek(size - size_limit)
                    handle.readline()  # drop the partial line the seek landed inside
                return handle.readlines()
            data = handle.read(size_limit)
    except OSError:
        return []
    lines = data.splitlines()
    if size > size_limit and lines:
        lines.pop()  # the last line may be a partial one cut off by the read limit
    return lines


def is_interrupt_marker(text):
    """Whether text is the record Claude Code writes when a turn is stopped, not typed."""
    return isinstance(text, str) and text.strip().startswith(INTERRUPT_PREFIX)


def first_question(tool_input):
    """The text of an AskUserQuestion call's first question, or None."""
    if not isinstance(tool_input, dict):
        return None
    questions = tool_input.get("questions")
    if not isinstance(questions, list) or not questions:
        return None
    first = questions[0]
    text = first.get("question") if isinstance(first, dict) else None
    return text if isinstance(text, str) else None


def scan_records(lines):
    """One pass over transcript lines, extracting everything list/--json need.

    Every `.get` below tolerates a missing or differently-shaped field, because the
    transcript's schema is unversioned. A record that does not parse, or does not look
    like the shape we expect, is skipped rather than raising.
    """
    info = empty_transcript_info()
    for line in lines:
        try:
            record = json.loads(line)
        except ValueError:
            continue
        if not isinstance(record, dict):
            continue
        rtype = record.get("type")

        if rtype == "ai-title":
            title = record.get("aiTitle")
            if title:
                info["ai_title"] = title
        elif rtype == "custom-title":
            title = record.get("customTitle")
            if title:
                info["custom_title"] = title
        elif rtype == "last-prompt":
            prompt = record.get("lastPrompt")
            if prompt and not is_interrupt_marker(prompt):
                info["last_prompt"] = prompt
        elif rtype == "assistant":
            info["last_record_type"] = "assistant"
            info["interrupted"] = False
            blocks = (record.get("message") or {}).get("content")
            if not isinstance(blocks, list):
                blocks = []
            for block in blocks:
                if not isinstance(block, dict):
                    continue
                btype = block.get("type")
                if btype == "text":
                    text = block.get("text") or ""
                    if text.strip():
                        info["last_assistant_text"] = text
                elif btype == "tool_use":
                    name = block.get("name") or "tool"
                    info["turn_tool_counts"][name] = info["turn_tool_counts"].get(name, 0) + 1
                    tool_id = block.get("id")
                    if tool_id:
                        question = first_question(block.get("input")) if name == "AskUserQuestion" else None
                        info["pending_tools"][tool_id] = {"name": name, "question": question}
        elif rtype == "user":
            info["last_record_type"] = "user"
            content = (record.get("message") or {}).get("content")
            if isinstance(content, str):
                info["interrupted"] = is_interrupt_marker(content)
                if not info["interrupted"]:
                    info["turn_tool_counts"] = {}  # a plain-text turn is a genuine new prompt
                continue
            info["interrupted"] = False
            if not isinstance(content, list):
                continue
            # Claude Code writes a tool's result back as a "user" record. A record
            # that is only tool results is the system answering the agent, not the
            # developer starting something new, so it must not reset the tool tally.
            has_real_text = False
            for block in content:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "tool_result":
                    info["pending_tools"].pop(block.get("tool_use_id"), None)
                else:
                    has_real_text = True
            if has_real_text:
                info["turn_tool_counts"] = {}
    return info


def load_transcript(path):
    """A transcript's extracted signals, tail first, head as a title-only fallback."""
    info = scan_records(read_lines(path, TAIL_BYTES, from_end=True))
    if not info["ai_title"] and not info["custom_title"]:
        head = scan_records(read_lines(path, TAIL_BYTES, from_end=False))
        info["ai_title"] = info["ai_title"] or head["ai_title"]
        info["custom_title"] = info["custom_title"] or head["custom_title"]
    return info


def load_subagents(session_dir, now):
    """Subagents worth reporting: ones whose own transcript is still being written to.

    A subagent's turns live in <session_dir>/subagents/*.jsonl, siblings of
    *.meta.json files holding agentType/description/model. A subagent whose file has
    not grown recently is done or was abandoned, and listing it would advertise
    finished work as if it were still running. Callers only reach this function for a
    session whose own status is already "working", so a subagent shown here means both
    the parent session and the subagent transcript were touched in the last
    WORKING_SECONDS: two live signals, not one.
    """
    subagents = []
    for meta_path in glob.glob(os.path.join(session_dir, "subagents", "*.meta.json")):
        jsonl_path = meta_path[: -len(".meta.json")] + ".jsonl"
        try:
            age = now - os.path.getmtime(jsonl_path)
        except OSError:
            continue
        if age > WORKING_SECONDS:
            continue
        try:
            with open(meta_path) as handle:
                meta = json.load(handle)
        except Exception:
            continue
        if not isinstance(meta, dict):
            continue
        subagents.append({
            "description": meta.get("description") or meta.get("agentType") or "subagent",
            "agentType": meta.get("agentType") or "",
            "model": meta.get("model") or "",
        })
    return subagents


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------

def derive_status(has_transcript, age, pending_tools, turn_complete, interrupted):
    """A session's status, checked in priority order, most urgent first.

    Every session reaching this function is alive: both `claude agents --json --all`
    and its registry-scanning fallback only ever return running processes, so there is
    no "process has exited" case to detect here, unlike in the previous version of
    this script.

    "working" has exactly one path: the transcript was written to within
    WORKING_SECONDS. A session whose last record is the interrupt marker, or whose
    last turn is an unfinished user record older than that, is not working, it is
    stalled, and reporting it as working is worse than reporting nothing.
    """
    if not has_transcript:
        return "never used"
    if interrupted:
        return "interrupted"
    if any(tool["name"] == "AskUserQuestion" for tool in pending_tools.values()):
        return "needs answer"
    if pending_tools and age > QUIET_SECONDS:
        return "needs permission"
    if age <= WORKING_SECONDS:
        return "working"
    if turn_complete:
        return "finished"
    # Quiet for a while, nothing pending, and the last record is a user turn rather
    # than assistant text: the developer stopped the turn and never came back.
    return "interrupted"


# ---------------------------------------------------------------------------
# Dismissal state
# ---------------------------------------------------------------------------

def load_state():
    try:
        with open(STATE_PATH) as handle:
            state = json.load(handle)
    except (OSError, ValueError):
        return {}
    return state if isinstance(state, dict) else {}


def save_state(state):
    tmp_path = STATE_PATH + ".tmp"
    with open(tmp_path, "w") as handle:
        json.dump(state, handle)
    os.replace(tmp_path, STATE_PATH)


def command_dismiss(target):
    sessions = live_sessions()
    session_id = target if target in sessions else None
    if session_id is None:
        # Derived names are not unique, so a name can match several live sessions.
        # Dismissing an arbitrary one of them would hide the wrong work and report
        # success, so an ambiguous name is refused and the caller is given the ids.
        matches = [sid for sid, entry in sessions.items() if entry.get("name") == target]
        if len(matches) > 1:
            print("%r matches %d live sessions. Dismiss one by its session id:"
                  % (target, len(matches)), file=sys.stderr)
            for sid in matches:
                print("  %s  pid %s" % (sid, sessions[sid].get("pid")), file=sys.stderr)
            return 1
        session_id = matches[0] if matches else None
    if session_id is None:
        print("No live session matches %r." % target, file=sys.stderr)
        return 1
    entry = sessions[session_id]
    path = transcript_path(session_id, entry.get("cwd") or "")
    mtime = os.path.getmtime(path) if path and os.path.exists(path) else 0.0
    state = load_state()
    state.setdefault("dismissed", {})[session_id] = mtime
    save_state(state)
    print("Dismissed %s. It reappears once its transcript changes." % (entry.get("name") or session_id))
    return 0


# ---------------------------------------------------------------------------
# Building rows
# ---------------------------------------------------------------------------

def build_sessions():
    """One row per live session, each carrying its own hide_reason if it has one.

    Nothing is dropped here: a hidden row is still returned, so the caller can total
    hidden sessions into count lines instead of silently losing them.
    """
    now = time.time()
    sessions = live_sessions()
    state = load_state()
    dismissed = state.get("dismissed", {})
    dirty = False

    rows = []
    for session_id, entry in sessions.items():
        cwd = entry.get("cwd") or ""
        path = transcript_path(session_id, cwd)
        has_transcript = bool(path and os.path.exists(path))
        mtime = os.path.getmtime(path) if has_transcript else None
        age = (now - mtime) if mtime is not None else None
        info = load_transcript(path) if has_transcript else empty_transcript_info()

        pending = info["pending_tools"]
        turn_complete = has_transcript and info["last_record_type"] == "assistant" and not pending
        status = derive_status(has_transcript, age, pending, turn_complete, info["interrupted"])

        subagents = []
        if status == "working" and has_transcript:
            session_dir = os.path.join(os.path.dirname(path), session_id)
            subagents = load_subagents(session_dir, now)

        hide_reason = None
        if not has_transcript:
            hide_reason = "never_used"
        elif age is not None and age > ABANDONED_SECONDS:
            hide_reason = "abandoned"
        elif session_id in dismissed:
            if mtime is not None and abs(mtime - dismissed[session_id]) < 1e-6:
                hide_reason = "dismissed"
            else:
                # The transcript moved since dismissal: the session was picked back
                # up, so let it reappear and forget the stale dismissal.
                del dismissed[session_id]
                dirty = True

        title = info["custom_title"] or info["ai_title"] or info["last_prompt"] or "(untitled)"
        rows.append({
            "session_id": session_id,
            "pid": entry.get("pid"),
            "name": entry.get("name") or session_id[:8],
            "cwd": cwd,
            "title": " ".join(title.split()),
            "last_prompt": " ".join(info["last_prompt"].split()),
            "last_assistant_text": info["last_assistant_text"],
            "status": status,
            "age_seconds": age,
            "pending_tools": pending,
            "tool_counts": info["turn_tool_counts"],
            "subagents": subagents,
            "hide_reason": hide_reason,
        })

    if dirty:
        state["dismissed"] = dismissed
        save_state(state)
    return rows


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

BUCKETS = (
    ("NEEDS YOU", ("needs answer", "needs permission", "interrupted")),
    ("WORKING", ("working",)),
    ("IDLE", ("finished",)),
)


def format_age(seconds):
    seconds = int(seconds)
    if seconds < 60:
        return "%ds" % seconds
    minutes = seconds // 60
    if minutes < 60:
        return "%dm" % minutes
    return "%dh" % (minutes // 60)


def render_bucket(label, rows, name_width, title_width, status_width):
    if not rows:
        return ""
    lines = [label]
    for row in rows:
        lines.append("  %-*s  %-*s  %-*s  %s" % (
            name_width, row["display_name"],
            title_width, row["title"][:TITLE_CHARS],
            status_width, row["status"],
            format_age(row["age_seconds"]),
        ))
        for extra in row["extra_lines"]:
            lines.append("      %s" % extra)
    return "\n".join(lines)


def truncate_ask(text, limit):
    """text, whitespace-collapsed, cut to limit chars with a trailing ellipsis.

    The `list` output is read by /todo on every invocation, so a long question costs
    tokens directly and reads as a wall of text; the full question still reaches the
    --json caller untouched. The cut prefers a word boundary, but only one that falls
    in the last third of the budget, so a truncation never throws away most of the
    line just to land on a space.
    """
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    budget = limit - 1  # room for the trailing ellipsis
    cut = text[:budget]
    boundary = cut.rfind(" ")
    if boundary >= budget - budget // 3:
        cut = cut[:boundary]
    return cut.rstrip() + "…"


def extra_lines(row):
    """The indented detail line(s) under a row: what it is asking, or what it has run."""
    lines = []
    if row["status"] == "needs answer":
        for tool in row["pending_tools"].values():
            if tool["question"]:
                lines.append("asks: %s" % truncate_ask(tool["question"], ASK_CHARS))
                break
    elif row["status"] == "working":
        total = sum(row["tool_counts"].values())
        parts = []
        if total:
            parts.append("ran %d command%s" % (total, "" if total == 1 else "s"))
        if row["subagents"]:
            descriptions = ", ".join(sub["description"] for sub in row["subagents"])
            parts.append("%d subagent%s: %s" % (
                len(row["subagents"]), "" if len(row["subagents"]) == 1 else "s", descriptions))
        if parts:
            lines.append(", ".join(parts))
    return lines


def render_list(rows):
    visible = [row for row in rows if row["hide_reason"] is None]
    names = [row["name"] for row in visible]
    for row in visible:
        collides = names.count(row["name"]) > 1
        row["display_name"] = "%s (%s)" % (row["name"], row["pid"]) if collides else row["name"]
        row["extra_lines"] = extra_lines(row)

    bucket_rows_by_label = []
    idle_capped_n = 0
    for label, statuses in BUCKETS:
        bucket_rows = sorted(
            (row for row in visible if row["status"] in statuses),
            key=lambda row: row["age_seconds"],
        )
        if label == "IDLE" and len(bucket_rows) > IDLE_MAX_ROWS:
            idle_capped_n = len(bucket_rows) - IDLE_MAX_ROWS
            bucket_rows = bucket_rows[:IDLE_MAX_ROWS]
        bucket_rows_by_label.append((label, bucket_rows))

    # Widths are computed once across every row that will actually print, not per
    # bucket, so NEEDS YOU, WORKING and IDLE line up on the same grid.
    printed = [row for _, bucket_rows in bucket_rows_by_label for row in bucket_rows]
    name_width = max((len(row["display_name"]) for row in printed), default=0)
    title_width = min(max((len(row["title"][:TITLE_CHARS]) for row in printed), default=0), TITLE_CHARS)
    status_width = max((len(row["status"]) for row in printed), default=0)

    sections = []
    for label, bucket_rows in bucket_rows_by_label:
        text = render_bucket(label, bucket_rows, name_width, title_width, status_width)
        if text:
            sections.append(text)

    hidden = [row for row in rows if row["hide_reason"]]
    dismissed_n = sum(1 for row in hidden if row["hide_reason"] == "dismissed")
    abandoned_n = sum(1 for row in hidden if row["hide_reason"] == "abandoned")
    never_used_n = sum(1 for row in hidden if row["hide_reason"] == "never_used")

    footer = []
    if dismissed_n or abandoned_n or idle_capped_n:
        parts = []
        if abandoned_n:
            parts.append("%d abandoned for over %dh" % (abandoned_n, ABANDONED_SECONDS // 3600))
        if idle_capped_n:
            parts.append("%d idle beyond the %d shown" % (idle_capped_n, IDLE_MAX_ROWS))
        if dismissed_n:
            parts.append("%d dismissed and unchanged" % dismissed_n)
        total = dismissed_n + abandoned_n + idle_capped_n
        footer.append("%d session%s hidden: %s." % (total, "" if total == 1 else "s", ", ".join(parts)))
    if never_used_n == 1:
        footer.append("1 open tab has never been used.")
    elif never_used_n > 1:
        footer.append("%d open tabs have never been used." % never_used_n)

    if not sections and not footer:
        return "No live sessions."
    if footer:
        sections.append("\n".join(footer))
    return "\n\n".join(sections)


def json_row(row):
    return {
        "session_id": row["session_id"],
        "pid": row["pid"],
        "name": row["name"],
        "cwd": row["cwd"],
        "title": row["title"],
        "last_prompt": row["last_prompt"],
        "last_assistant_text": row["last_assistant_text"],
        "status": row["status"],
        "age_seconds": row["age_seconds"],
        "pending_tools": [
            {"id": tool_id, "name": tool["name"], "question": tool["question"]}
            for tool_id, tool in row["pending_tools"].items()
        ],
        "tool_counts": row["tool_counts"],
        "subagents": row["subagents"],
        "hidden": row["hide_reason"] is not None,
        "hide_reason": row["hide_reason"],
    }


def command_list(as_json):
    rows = build_sessions()
    if as_json:
        payload = {
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime()),
            "sessions": [json_row(row) for row in rows],
        }
        print(json.dumps(payload, indent=2))
        return 0
    text = render_list(rows)
    with open(OUTPUT_PATH, "w") as handle:
        handle.write(text + "\n")
    print(text)
    return 0


def main(argv):
    mode = argv[1] if len(argv) > 1 else "list"
    if mode == "list":
        return command_list(as_json=False)
    if mode == "--json":
        return command_list(as_json=True)
    if mode == "dismiss":
        if len(argv) < 3:
            print("usage: agent-status.py dismiss <session-id-or-name>", file=sys.stderr)
            return 1
        return command_dismiss(argv[2])
    print("usage: agent-status.py [list|--json|dismiss <session-id-or-name>]", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
