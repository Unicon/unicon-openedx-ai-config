#!/bin/bash
# List the developer's live Claude Code sessions, or name one of them.
#
# With no arguments, prints one line per live interactive session: the session's name, the
# directory it runs in, its state, how long it has been idle, and, for a session that could
# earn a row on the to-do sheet, the path to its transcript.
#
#   busy        It wrote to its transcript in the last 2 minutes, or it has a child process
#               running right now (a command or an MCP server).
#   needs-you   Its turn ended and it is waiting for the developer.
#   stale       Idle for more than 8 hours: an abandoned editor tab, not work in progress.
#   never-used  Open, but never given a prompt.
#
# Everything it reads is metadata: the session registry in ~/.claude/sessions/, the
# modification time of each session's transcript, and one `ps` pass. It opens no
# conversation, and it lists no sub-agents, because the registry records only interactive
# sessions. A `stale` or `never-used` session gets no transcript path, because the sheet
# never shows one.
#
# With `--label <transcript path>`, prints that conversation's first human prompt, cut to 60
# characters, and nothing else. The opening prompt is the closest thing to a chat name that
# exists on disk, because the title the editor shows in its own interface is not persisted
# anywhere. This is the only conversation content anything here ever reads, so it is a
# separate mode rather than a column: run it only for a session that is getting a row.

if [ "$1" = "--label" ]; then
  [ -n "$2" ] || { echo "usage: sessions.sh --label <transcript path>" >&2; exit 2; }
  head -c 20000 "$2" | grep -oE '"(content|text)":"[^<"][^"]{19,}' \
    | head -1 | sed 's/^"[a-z]*":"//; s/\\n/ /g' | cut -c1-60
  exit 0
fi

now=$(date +%s); pp=$(ps -Ao ppid=)
for f in ~/.claude/sessions/*.json; do
  j=$(cat "$f"); case $j in *'"kind":"interactive"'*) ;; *) continue;; esac
  pid=${j#*'"pid":'};        pid=${pid%%,*}
  sid=${j#*'"sessionId":"'}; sid=${sid%%\"*}
  cwd=${j#*'"cwd":"'};       cwd=${cwd%%\"*}
  nm=${j#*'"name":"'};       nm=${nm%%\"*}
  kill -0 "$pid" 2>/dev/null || continue
  t="$HOME/.claude/projects/$(printf %s "$cwd" | tr / -)/$sid.jsonl"
  [ -f "$t" ] || { printf '%s | %s | never-used\n' "$nm" "${cwd##*/}"; continue; }
  idle=$(( (now - $(stat -f %m "$t")) / 60 ))
  if [ "$idle" -lt 2 ] || printf '%s\n' "$pp" | grep -qw "$pid"; then st=busy
  elif [ "$idle" -gt 480 ]; then st=stale
  else st=needs-you; fi
  case $st in stale) printf '%s | %s | stale | idle %dm\n' "$nm" "${cwd##*/}" "$idle";;
  *) printf '%s | %s | %s | idle %dm | %s\n' "$nm" "${cwd##*/}" "$st" "$idle" "$t";; esac
done
