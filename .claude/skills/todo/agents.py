#!/usr/bin/env python3
"""List the developer's live Claude Code sessions, what each one is about, and whether it
is busy.

Reads only metadata plus one label per session: the session registry in
~/.claude/sessions/*.json, the modification time of each session's transcript, one `ps`
pass, and the first human prompt of each conversation truncated to 60 characters. The
opening prompt is the closest thing to a chat name that is stored on disk; the title the
editor shows in its own UI is not persisted anywhere. Nothing else from a conversation is
ever read, so no other session's contents reach anyone's context.

One line per live session:

    <cwd> | <branch> | <session name> | <state> | idle <n>s | pid <n> | <label>

States:
    busy        The session wrote to its transcript in the last 2 minutes, or it is
                running a child process right now (a command or an MCP server).
    needs-you   Its turn ended and it is waiting for you. `idle` says how long.
    never-used  The session is open but has never been given a prompt.
    dismissed   The developer already told the sheet this one is finished, and it has done
                nothing since. See "Finished sessions" below.

Anything idle for more than 8 hours also gets the `stale` marker: an abandoned editor tab
rather than work in progress.

Finished sessions
-----------------
A session stays alive in the editor after its work is done, so it looks like it is waiting
for the developer forever. When they say a session is finished, the skill appends a line to
.claude/my-todo-log.md in this exact shape:

    - 2026-08-27 11:20 — Competency taxonomy accessor tests (session wt-640-cbe-foundation-16 done)

This script reads those lines and reports such a session as `dismissed` for as long as it
stays quiet. If the session writes to its transcript again after that timestamp, the
developer picked the work back up, so its real state is reported instead.
"""
import datetime
import glob
import json
import os
import re
import subprocess
import time

HOME = os.path.expanduser("~/.claude")
LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "my-todo-log.md")
BUSY_SECONDS = 120
STALE_SECONDS = 8 * 3600
LABEL_CHARS = 60
LABEL_SCAN_LINES = 300

DONE_LINE = re.compile(r"^- (\d{4}-\d{2}-\d{2} \d{2}:\d{2}) .*\(session (\S+) done\)\s*$")
WRAPPED_TAG = re.compile(
    r"<(ide_selection|ide_opened_file|ide_diagnostics|system-reminder"
    r"|local-command-[a-z]+|command-[a-z]+)>.*?</\1>",
    re.S,
)
BARE_TAG = re.compile(r"<[^>]{1,60}>")
SKILL_PREAMBLE = "Base directory for this skill:"


def child_counts():
    """Map parent pid to number of live children, from a single ps pass."""
    counts = {}
    try:
        out = subprocess.run(["ps", "-Ao", "ppid="], capture_output=True, text=True).stdout
    except OSError:
        return counts
    for field in out.split():
        try:
            ppid = int(field)
        except ValueError:
            continue
        counts[ppid] = counts.get(ppid, 0) + 1
    return counts


def dismissals():
    """Map session name to the epoch time the developer declared it finished."""
    found = {}
    try:
        with open(LOG) as handle:
            lines = handle.readlines()
    except OSError:
        return found
    for line in lines:
        match = DONE_LINE.match(line.rstrip("\n"))
        if not match:
            continue
        try:
            when = datetime.datetime.strptime(match.group(1), "%Y-%m-%d %H:%M").timestamp()
        except ValueError:
            continue
        name = match.group(2)
        found[name] = max(when, found.get(name, 0))
    return found


def branch(cwd, cache):
    if cwd not in cache:
        try:
            out = subprocess.run(
                ["git", "-C", cwd, "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True, text=True, timeout=5,
            )
            cache[cwd] = out.stdout.strip() if out.returncode == 0 else "-"
        except (OSError, subprocess.TimeoutExpired):
            cache[cwd] = "-"
    return cache[cwd]


def label(transcript):
    """The conversation's first human prompt, cleaned up and truncated."""
    try:
        handle = open(transcript)
    except OSError:
        return "-"
    with handle:
        for index, line in enumerate(handle):
            if index > LABEL_SCAN_LINES:
                break
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            if entry.get("type") != "user" or entry.get("isMeta"):
                continue
            content = entry.get("message", {}).get("content")
            if isinstance(content, list):
                content = " ".join(
                    part.get("text", "") for part in content if isinstance(part, dict)
                )
            if not isinstance(content, str):
                continue
            text = BARE_TAG.sub(" ", WRAPPED_TAG.sub(" ", content))
            text = re.sub(r"\s+", " ", text).strip()
            if len(text) < 8 or text.startswith(SKILL_PREAMBLE):
                continue
            return text[:LABEL_CHARS]
    return "-"


def live_sessions():
    for path in glob.glob(os.path.join(HOME, "sessions", "*.json")):
        try:
            with open(path) as handle:
                data = json.load(handle)
        except (OSError, ValueError):
            continue
        pid, sid, cwd = data.get("pid"), data.get("sessionId"), data.get("cwd")
        if not (pid and sid and cwd) or data.get("kind") != "interactive":
            continue
        try:
            os.kill(pid, 0)
        except OSError:
            continue  # Registry entry outlived the process.
        yield pid, sid, cwd, data.get("name") or "-"


def main():
    now = time.time()
    kids = child_counts()
    done = dismissals()
    cache = {}
    rows = []
    for pid, sid, cwd, name in live_sessions():
        transcript = os.path.join(HOME, "projects", cwd.replace("/", "-"), sid + ".jsonl")
        try:
            touched = os.path.getmtime(transcript)
        except OSError:
            touched = None
        idle = None if touched is None else now - touched
        if idle is None:
            state = "never-used"
        elif name in done and touched <= done[name]:
            state = "dismissed"
        elif idle < BUSY_SECONDS or kids.get(pid, 0) > 0:
            state = "busy"
        else:
            state = "needs-you"
        stale = " stale" if idle is not None and idle > STALE_SECONDS else ""
        age = "-" if idle is None else "%ds" % int(idle)
        text = "-" if touched is None else label(transcript)
        rows.append((cwd, name, "%s | %s | %s | %s | idle %s | pid %d%s | %s"
                     % (cwd, branch(cwd, cache), name, state, age, pid, stale, text)))
    if not rows:
        print("no live Claude sessions found")
        return
    for _, _, line in sorted(rows):
        print(line)


if __name__ == "__main__":
    main()
