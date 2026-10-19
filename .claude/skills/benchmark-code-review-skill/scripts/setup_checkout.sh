#!/usr/bin/env bash
# Build an isolated clone with no remotes, frozen at review time, plus one worktree per variant.
#
# Usage:
#   bash setup_checkout.sh <local-repo-path> <upstream-git-url> <head-sha> <main-sha> <out-dir> <variant> [<variant>...]
# Environment:
#   CLAUDE_DIR=/path/to/.claude   copy CLAUDE.md and architecture-overview.md into each worktree's .claude/
#   BASE_SHA=<sha>                the commit the PR branched from; default is <head-sha>^ (right for a one-commit PR)
#   ABSENT_SHAS="<sha> <sha>"     commits that must not exist afterwards (the merge commit, later review heads)
#   CUTOFF=<iso timestamp>        the review cutoff from case.json; default is main's commit date
#
# Result: <out-dir>/repo with branches main, pr-head, pr-base, and <out-dir>/wt-<variant> detached at <head-sha>.
# No remote is configured and unreachable objects are pruned, so an agent cannot reach the merged fix or current main.
# Worktrees share the clone's refs and object store; when agents may create branches that the other variant must not
# see, run this script once per variant with its own <out-dir>.
set -euo pipefail
SRC=$1; URL=$2; HEAD_SHA=$3; MAIN_SHA=$4; OUT=$5; shift 5
mkdir -p "$OUT"
git clone --no-checkout --quiet "$SRC" "$OUT/repo"
cd "$OUT/repo"
git remote remove origin
git fetch --quiet "$URL" "$HEAD_SHA" "$MAIN_SHA"
git branch -f main "$MAIN_SHA"
git branch -f pr-head "$HEAD_SHA"
git branch -f pr-base "${BASE_SHA:-${HEAD_SHA}^}"
git symbolic-ref HEAD refs/heads/main
for b in $(git for-each-ref --format='%(refname:short)' refs/heads/); do
  case "$b" in main|pr-head|pr-base) ;; *) git branch -D "$b" >/dev/null ;; esac
done
git tag -l | xargs git tag -d >/dev/null 2>&1 || true
# A local clone copies every object, including commits made after the cutoff. Drop what no ref reaches.
git reflog expire --expire=now --all
git gc --prune=now --quiet
for v in "$@"; do
  git worktree add --detach --quiet "$OUT/wt-$v" "$HEAD_SHA"
  if [ -n "${CLAUDE_DIR:-}" ]; then
    mkdir -p "$OUT/wt-$v/.claude"
    cp "$CLAUDE_DIR/CLAUDE.md" "$OUT/wt-$v/.claude/" 2>/dev/null || true
    cp "$CLAUDE_DIR/architecture-overview.md" "$OUT/wt-$v/.claude/" 2>/dev/null || true
  fi
done
echo "branches:"; git branch -v
echo "worktrees:"; git worktree list
echo "remotes: $(git remote | wc -l | tr -d ' ') (must be 0); tags: $(git tag -l | wc -l | tr -d ' ') (must be 0)"
echo "merge-base(pr-head, main) = $(git merge-base pr-head main)"
CUTOFF=${CUTOFF:-$(git log -1 --format=%cI main)}
echo "commits since $CUTOFF reachable from a ref other than main: $(git rev-list --all --since="$CUTOFF" --not main | wc -l | tr -d ' ') (must be 0)"
for s in ${ABSENT_SHAS:-}; do
  if git cat-file -e "$s" 2>/dev/null; then echo "LEAK: $s is still present"; else echo "absent as required: $s"; fi
done
