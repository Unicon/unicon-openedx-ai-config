#!/usr/bin/env python3
"""Record what each Claude Code session is doing, as one line per session.

Claude Code runs this from a hook, never the model, so it adds no tokens to a
request and no thinking to a turn. `start` runs when you submit a prompt, `end`
runs when the agent stops, and `list` prints the table for you to read.

Each session owns one file under .claude/agent-status/, named for its session id
and holding `name|task|status`. One file per session is what makes concurrent
sessions safe: a single shared log would need every session to read it and write
it back, and two sessions doing that at the same moment lose a line.

The task is the first 60 characters of the opening prompt, written once and left
alone afterwards. The status is `working` while a turn runs. When the turn ends,
the agent's last message decides: a message ending in a question means the agent
is waiting for you, anything else means it finished what you asked for.

`list` shows only sessions whose process is still alive, because a session killed
mid-turn keeps its last written status and would otherwise read `working` forever.
"""

import glob
import json
import os
import sys
import time

HOOKS_DIR = os.path.dirname(os.path.abspath(__file__))
STATUS_DIR = os.path.join(os.path.dirname(HOOKS_DIR), "agent-status")

TASK_CHARS = 60
# How much of the transcript's end to parse. A turn's final message is the last
# thing written to it, so there is no reason to read the whole conversation.
TAIL_BYTES = 262144
UNKNOWN_TASK = "(task not recorded)"
# Marks a session whose process has exited. Its status is the last one it wrote,
# so `working · closed` is a turn that was interrupted and may need resuming.
CLOSED = " · closed"


def read_event():
    """The hook payload Claude Code writes to this process's stdin."""
    try:
        return json.load(sys.stdin)
    except Exception:
        return {}


def registry():
    """Every interactive session Claude Code has registered, keyed by session id.

    This is the only place a session's name and process id exist, and it is plain
    metadata: no conversation is opened to read it.
    """
    sessions = {}
    for path in glob.glob(os.path.expanduser("~/.claude/sessions/*.json")):
        try:
            with open(path) as handle:
                entry = json.load(handle)
        except Exception:
            continue
        if entry.get("kind") != "interactive":
            continue
        if entry.get("sessionId"):
            sessions[entry["sessionId"]] = entry
    return sessions


def is_running(entry):
    """Whether the session's process is still alive."""
    pid = entry.get("pid")
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


def session_name(session_id, cwd):
    """The name Claude Code gave the session, such as openedx-core-39.

    The name begins with the directory the session runs in, which is what lets a
    reader tell which repository a row belongs to. Fall back to that directory
    when the registry has no entry for the session yet.
    """
    entry = registry().get(session_id) or {}
    return entry.get("name") or os.path.basename(cwd.rstrip("/")) or session_id[:8]


def entry_path(session_id):
    return os.path.join(STATUS_DIR, session_id)


def load(session_id):
    """The session's existing name and task, or None if it has no entry yet."""
    try:
        with open(entry_path(session_id)) as handle:
            parts = handle.read().rstrip("\n").split("|")
    except OSError:
        return None
    return parts if len(parts) == 3 else None


def save(session_id, name, task, status):
    os.makedirs(STATUS_DIR, exist_ok=True)
    with open(entry_path(session_id), "w") as handle:
        handle.write("%s|%s|%s\n" % (name, task, status))


def one_line(text, limit):
    """Collapse text to a single line that cannot break the pipe-separated format."""
    text = " ".join(text.split()).replace("|", "/")
    return text[:limit]


def last_agent_message(transcript_path):
    """The final text the agent wrote in its own transcript."""
    try:
        size = os.path.getsize(transcript_path)
        with open(transcript_path, errors="replace") as handle:
            if size > TAIL_BYTES:
                handle.seek(size - TAIL_BYTES)
                handle.readline()  # drop the partial line the seek landed inside
            lines = handle.readlines()
    except OSError:
        return ""
    message = ""
    for line in lines:
        try:
            record = json.loads(line)
        except ValueError:
            continue
        if record.get("type") != "assistant":
            continue
        blocks = record.get("message", {}).get("content") or []
        text = "".join(
            block.get("text", "")
            for block in blocks
            if isinstance(block, dict) and block.get("type") == "text"
        )
        if text.strip():
            message = text
    return message


def existing_or_new(event):
    session_id = event.get("session_id", "")
    prompt = one_line(event.get("prompt", ""), TASK_CHARS)
    known = load(session_id)
    if known:
        name, task = known[0], known[1]
        # A Stop hook firing before the session's first prompt leaves the
        # placeholder behind, so let the next real prompt replace it.
        if task == UNKNOWN_TASK and prompt:
            task = prompt
        return session_id, name, task
    name = session_name(session_id, event.get("cwd", ""))
    return session_id, name, prompt or UNKNOWN_TASK


def command_start(event):
    session_id, name, task = existing_or_new(event)
    if session_id:
        save(session_id, name, task, "working")


def command_end(event):
    session_id, name, task = existing_or_new(event)
    if not session_id:
        return
    # Only the agent knows whether it stopped to ask something or because it was
    # done, and it says so in how its message ends.
    ending = last_agent_message(event.get("transcript_path", "")).rstrip()[-3:]
    save(session_id, name, task, "waiting for answer" if "?" in ending else "Completed")


def command_list():
    """Print one line per running session, newest change first.

    A session whose process has exited keeps the last status it wrote, and is
    marked closed rather than dropped: `working · closed` is a turn that was cut
    off partway and may be worth resuming. A session that is open but has never
    run the hook has nothing on disk at all, and is counted at the end so it is
    not mistaken for having no work.
    """
    live = registry()
    reported, rows = set(), []
    for path in glob.glob(os.path.join(STATUS_DIR, "*")):
        session_id = os.path.basename(path)
        try:
            with open(path) as handle:
                parts = handle.read().rstrip("\n").split("|")
        except OSError:
            continue
        if len(parts) != 3:
            continue
        name, task, status = parts
        entry = live.get(session_id)
        if entry and is_running(entry):
            reported.add(session_id)
        else:
            status += CLOSED
        changed = time.strftime("%Y-%m-%d %H:%M", time.localtime(os.path.getmtime(path)))
        rows.append((changed, name, task, status))
    silent = sum(
        1
        for session_id, entry in live.items()
        if session_id not in reported and is_running(entry)
    )

    if rows:
        rows.sort(reverse=True)
        name_width = max(len(row[1]) for row in rows)
        status_width = max(len(row[3]) for row in rows)
        for changed, name, task, status in rows:
            print("%-*s | %-*s | %-*s | %s"
                  % (name_width, name, TASK_CHARS, task, status_width, status, changed))
    else:
        print("No session has reported a status yet.")
    if silent:
        print("(%d open session%s never reported: empty tabs, or started before the hook)"
              % (silent, "" if silent == 1 else "s"))


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "list"
    if mode == "list":
        command_list()
    elif mode == "start":
        command_start(read_event())
    elif mode == "end":
        command_end(read_event())
