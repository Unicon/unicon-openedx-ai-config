#!/usr/bin/env bash
# SessionStart hook: inject this setup's copy of the using-superpowers skill.
#
# The superpowers skills live in .claude/skills/ as a maintained copy of the
# upstream plugin (see .claude/superpowers-fork.md). The upstream plugin's
# own SessionStart hook injects its `superpowers:using-superpowers`; this hook
# injects the local copy, which tells Claude to prefer the local skills when
# both are present. It mirrors the upstream hook's output format for Claude
# Code and depends on nothing outside bash, because SessionStart hooks can run
# with an empty PATH.
set -euo pipefail

case "$0" in
  */*) SCRIPT_DIR="$(cd "${0%/*}" && pwd)" ;;
  *) SCRIPT_DIR="$(pwd)" ;;
esac
CLAUDE_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

skill_md="${CLAUDE_DIR}/skills/using-superpowers/SKILL.md"
if [ -r "$skill_md" ]; then
  content="$(<"$skill_md")"
else
  content="Error reading the local using-superpowers skill at ${skill_md}"
fi

escape_for_json() {
  local s="$1"
  s="${s//\\/\\\\}"
  s="${s//\"/\\\"}"
  s="${s//$'\n'/\\n}"
  s="${s//$'\r'/\\r}"
  s="${s//$'\t'/\\t}"
  printf '%s' "$s"
}

escaped=$(escape_for_json "$content")
context="<EXTREMELY_IMPORTANT>\nThis workspace ships its own copy of the superpowers skills in .claude/skills/. They take precedence over any installed superpowers plugin: invoke the bare skill name (for example 'brainstorming'), never the 'superpowers:' prefixed one.\n\n**Below is the full content of the local 'using-superpowers' skill - your introduction to using skills. For all other skills, use the 'Skill' tool:**\n\n${escaped}\n</EXTREMELY_IMPORTANT>"

printf '{\n  "hookSpecificOutput": {\n    "hookEventName": "SessionStart",\n    "additionalContext": "%s"\n  }\n}\n' "$context"
exit 0
