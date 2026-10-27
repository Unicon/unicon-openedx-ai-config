#!/usr/bin/env bash
# Run a built-in (forked) Claude Code skill against a frozen worktree, as a separate Claude Code process.
#
# Usage:
#   bash run_builtin_skill.sh <worktree> <brief.md> <out-dir> [model] [claude-binary]
#
# Why a separate process: a skill such as the stock `code-review` is not a file and runs as a forked execution behind
# the Skill tool. The fork resolves its git target against the process's primary working directory and does not see
# the calling conversation, so invoked from a dispatched agent it reviews the developer checkout, whatever the brief
# says (verified on PR 847, 2026-10-19: two attempts both reviewed the wrong branch). Starting a fresh `claude -p`
# session whose cwd is the worktree makes the worktree the only checkout the fork can see.
#
# The brief is the prompt. Read-only tools are allowed; Edit/Write/WebFetch/WebSearch are denied. The brief's directory
# is added as an allowed directory so the agent can read the frozen context files beside it. Output:
#   <out-dir>/transcript.jsonl   stream-json transcript (extract the report and audit it with extract_handback.py)
#   <out-dir>/stderr.txt         stderr plus the exit code
#   <out-dir>/claude_version.txt, start_time.txt, end_time.txt
# Pass the binary that this session runs (the VS Code extension bundles its own under resources/native-binary/) so the
# skill version under test is the one the user actually has; record it in the results.
set -euo pipefail
WT=$1; BRIEF=$2; OUT=$3; MODEL=${4:-claude-fable-5-1}; BIN=${5:-claude}
mkdir -p "$OUT"
cd "$WT"
date -u +%Y-%m-%dT%H:%M:%SZ > "$OUT/start_time.txt"
"$BIN" --version > "$OUT/claude_version.txt"
set +e
"$BIN" -p "$(cat "$BRIEF")" --model "$MODEL" --output-format stream-json --verbose \
  --allowedTools "Bash,Read,Grep,Glob,Agent,Skill,TodoWrite,ReportFindings" \
  --disallowedTools "Edit,Write,MultiEdit,NotebookEdit,WebFetch,WebSearch" \
  --add-dir "$(cd "$(dirname "$BRIEF")" && pwd)" > "$OUT/transcript.jsonl" 2> "$OUT/stderr.txt"
echo "exit=$?" >> "$OUT/stderr.txt"
set -e
date -u +%Y-%m-%dT%H:%M:%SZ > "$OUT/end_time.txt"
cat "$OUT/stderr.txt"
