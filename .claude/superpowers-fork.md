# The superpowers skills in this setup

`.claude/skills/` holds a copy of every skill from the upstream [superpowers](https://github.com/obra/superpowers) plugin, under the same directory names, so the team can change them. Claude Code cannot shadow a plugin skill with a project skill, because plugin skills are namespaced as `superpowers:<name>`. The local copies therefore use the bare names, and three things make Claude pick them when the plugin is also installed: the local `using-superpowers` skill says so, `CLAUDE.md` says so, and the SessionStart hook in `.claude/settings.json` injects the local `using-superpowers` at the start of every session, the same way the plugin's own hook injects its version.

## Upstream version

| | |
|---|---|
| Source | `superpowers@claude-plugins-official`, plugin version 7.0.0 |
| Upstream commit | `bb92a77741419a4ab5f06e711a283343f1ada0c3` |
| Copied on | 2026-11-05 |

The import was two mechanical steps: copy `skills/*` from the plugin cache into `.claude/skills/`, then strip the `superpowers:` prefix from every cross-reference so a copied skill that names another skill names the local copy:

```
sed -i '' -E 's/superpowers:([a-z-]+)/\1/g' <every file under the copied skills>
```

## What the team changed

- `proving-changes/` is a new skill. It defines what counts as proof of a change, where proof is recorded (`.superpowers/proofs/<branch>/PROOF.md`, printed by `bash scripts/proof-dir`), and the done check: the record covers every hunk in the diff with passing proof, closed in at most three cycles, then the user is asked.
- `using-superpowers/SKILL.md`: a "Local Copies Win" section.
- `writing-plans/SKILL.md`: an Acceptance Criteria section in the plan header, a Proof block per task, and a proof-coverage item in the self-review.
- `executing-plans/SKILL.md` and `subagent-driven-development/SKILL.md`: a fifth stop (a change that cannot be proven), the proof record started at setup, proof in the completion contract or reviewer inputs, and the done check before `finishing-a-development-branch`.
- `subagent-driven-development/implementer-prompt.md`: a "Prove the Change" section and proof in the report contract. `task-reviewer-prompt.md`: a Proof Coverage part and verdict.
- `requesting-code-review/code-reviewer.md`: the proof record as a reviewer input and a Proof check.
- `verification-before-completion/SKILL.md`: a row in the failures table and a section pointing at `proving-changes`.
- `finishing-a-development-branch/SKILL.md`: the done check in Step 1, and the cleaned-up proof record attached to the PR under `## Proof` in the PR option.
- `test-driven-development/SKILL.md`: one checklist item.

## Updating to a newer upstream

1. Install or update the plugin, and find its cache directory under `~/.claude/plugins/cache/claude-plugins-official/superpowers/<version>/skills`.
2. Produce the upstream delta: `diff -ru <old version>/skills <new version>/skills > upstream.patch`, using the old version recorded in the table above.
3. Apply the delta to `.claude/skills/` with `patch -p<n>`, resolve conflicts against the team changes listed above, and re-run the prefix strip on any new or changed file.
4. Update the table above, and this list if a team change moved or was absorbed upstream.
