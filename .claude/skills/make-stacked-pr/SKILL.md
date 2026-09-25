---
name: make-stacked-pr
description: Turn a finished branch into a stack of small draft PRs that are easy to review. Use when asked to make a stacked PR, open a PR stack, or split a branch into reviewable chunks. Handles both a stack that targets upstream main and one that targets another person's branch in their fork. Opens everything as drafts, never merges. Only ever invoked manually, never runs automatically.
---

# Make a stacked PR

Turn one finished branch, which is hard to review as a single large diff, into a chain of
small draft PRs a reviewer can work through one chunk at a time.

The shape it produces:

- **A base PR.** Its head branch holds one minimal change (a version bump, a changelog
  line). It is the only PR that points at the target repository, and it is where the
  review and merge instructions for the whole stack live.
- **The chunk PRs.** Each one's head branch is built on the branch below it, and each one
  is opened inside the developer's own fork, based on the base PR's branch. Head and base
  both living in the fork is what lets GitHub treat them as a real stack.

Every PR is a draft. This skill never merges, never marks a PR ready for review, and never
rewrites a branch the developer has already pushed somewhere else.

## Placeholders

The commands below use these. Resolve them in steps 1 and 5, and keep them consistent
across every command.

- `<target-owner>/<repo>` and `<target-branch>`: the repository and branch the stack aims
  at, resolved in step 1.
- `<target-remote>`: the local git remote pointing at `<target-owner>/<repo>`, usually
  `upstream`.
- `<fork-owner>`: the developer's GitHub account, which owns `origin`.
- `<developer>`: the prefix the developer uses on branch names, usually their username.
- `<ticket>`: the ticket the branch implements. `<slug>`: one to three words naming a chunk.
- `<original-branch>`: the finished branch the stack is split out of.
- `<tip-branch>`: the last chunk branch, the one at the top of the finished stack.

### Check every name before you put it in a command

A branch, repository, or owner name can come from outside this repository: step 1 takes
someone else's fork and branch when the stack targets their unmerged work. Git's ref rules
allow characters the shell reads as syntax, so `feat/x;id` is a valid branch name, and
pasting it into a command runs `id`. Before a value fills any placeholder, capture it in a
quoted heredoc, which the shell does not interpret at all, and check it against the
characters these names actually use:

```bash
IFS= read -r NAME <<'EOF'
paste the name here, on its own line
EOF
printf '%s\n' "$NAME" | grep -Eq '^[A-Za-z0-9][A-Za-z0-9._/-]*$' \
  || echo "rejected, do not use this name: $NAME"
```

Every name this skill handles is an ordinary git branch or GitHub owner name, and all of
them pass that check. A name that fails it is either a mistake or an attack, so stop and ask
the developer rather than working around it. A name that passes holds no shell syntax, which
is what makes it safe to fill into the command templates below.

## 1. Pin down the target

Ask the developer, with `AskUserQuestion`, where the stack is aimed, because that decides
which repository the base PR is opened against:

- **Upstream main.** The base PR goes to the upstream repository (for example
  `openedx/openedx-core`) against its default branch.
- **Someone else's branch.** The stack depends on work that is not merged yet, so the base
  PR goes to that person's fork, against their branch. Get the owner and the branch name
  from the developer, and fetch that branch so you build on the right commit.

State the resolved target back as `<target-owner>/<repo>:<target-branch>` and confirm it
before you create anything.

## 2. Choose the base PR's minimal change

Survey the branch first. Both this choice and the split in step 3 are made against what is
actually on the branch:

```bash
git fetch <target-remote>
MERGE_BASE="$(git merge-base HEAD <target-remote>/<target-branch>)"
git log --oneline "$MERGE_BASE"..HEAD
git diff --stat "$MERGE_BASE"..HEAD
```

Then look through the branch for the smallest genuine change in it that can stand alone,
such as a version bump, a changelog entry, or a requirements pin, and propose that as the
base PR's only content. If the branch contains nothing suitable, ask the developer what the
base PR should hold instead. Do not invent a change that was not going to be made anyway.

## 3. Ask how to split the rest

The base PR's change from step 2 is already spoken for, so what the chunks divide up is the
rest of the branch. The base change and the chunks are a partition: every hunk on the branch
belongs to exactly one of them, and together they add up to the whole branch diff. Step 5
applies each chunk on top of the base branch, so a chunk that still carries the base change
conflicts there or lands that change twice. Name the base change when you present the split
options, and keep it out of every chunk. If the base change sits in a commit that also holds
other work, that commit has to be split, and per-commit chunking does not apply to it.

Do not decide the split yourself. Ask the developer how to chunk the rest, with
`AskUserQuestion`, offering concrete options drawn from the step 2 output rather than generic
ones: one PR per commit, a named grouping of the existing commits, or a re-slice by file area
that ignores the current commit boundaries.

Tell them one thing while they decide: a chunk should stand on its own. If a chunk leaves
the repository failing its tests until a later chunk lands, say so and name the chunk. The
developer still makes the call, but they should make it knowing that.

## 4. Get one approval for the whole plan

Before touching git, show the developer the complete plan: the target, the base branch and
its minimal change, every chunk branch with its base and its contents, and the ASCII map
from step 8. Get one approval for all of it, then run the rest without stopping again.

## 5. Build the branches

Name the branches so the stack order is readable: `<developer>/<ticket>-stack-base`, then
`<developer>/<ticket>-01-<slug>`, `<developer>/<ticket>-02-<slug>`, and so on.

Cut the base branch from `<target-remote>/<target-branch>`, put the minimal change on it,
then cut each chunk branch from the branch below it:

```bash
git switch -c <developer>/<ticket>-stack-base <target-remote>/<target-branch>
# apply the minimal change, commit
git switch -c <developer>/<ticket>-01-<slug> <developer>/<ticket>-stack-base
# apply chunk 1, commit
git switch -c <developer>/<ticket>-02-<slug> <developer>/<ticket>-01-<slug>
```

Before pushing anything, check that the stack adds up to the branch it came from. The tip
branch holds the minimal change plus every chunk, so its tree has to match
`<original-branch>` exactly:

```bash
git diff --stat <original-branch> <tip-branch>
```

Any output means the partition from step 3 came out wrong: some hunk landed in no chunk, or
in two. Fix the branches before going further. Empty output means nothing is lost when the
stack merges down, so push every branch to the developer's fork with
`git push -u origin <branch>`.

## 6. Open the draft PRs

The base PR is the only cross-repository one:

```bash
gh pr create --repo <target-owner>/<repo> --base <target-branch> \
  --head <fork-owner>:<developer>/<ticket>-stack-base --draft --title "..." --body "..."
```

`--head <user>:<branch>` does not accept an organization as the `<user>`, so if the fork is
owned by an organization rather than a person, this command fails. Open that one PR from
GitHub's compare view in the web UI instead; every other PR in the stack is unaffected,
because none of them uses the `owner:branch` form.

Each chunk PR is opened inside the fork, based on the branch below it:

```bash
gh pr create --repo <fork-owner>/<repo> --base <developer>/<ticket>-stack-base \
  --head <developer>/<ticket>-01-<slug> --draft --title "..." --body "..."
```

Always pass `--repo`. Without it, `gh` resolves the base repository itself and a chunk PR
meant to stay inside the fork can land against upstream instead. Confirm each PR after
creating it:

```bash
gh pr view <number> --repo <fork-owner>/<repo> --json url,baseRefName,headRefName,isCrossRepository
```

The `url` says which repository the PR actually lives in, and `isCrossRepository` is false
for a chunk PR, whose head and base are both in the fork, and true for the base PR. A PR's
base repository cannot be changed after the fact, so if one landed wrong, close it and
create it again.

Give each chunk PR a body saying what the chunk does and which PR it sits on top of.
Beyond setting each PR's base branch, which is all the commands above do, do not wire the
stack together with tooling or the API. Tell the developer to create the stack itself in
GitHub's own stacking UI inside their fork. Only the bottom link, the base branch pointing
at the target repository, is outside that UI's reach.

## 7. Write the base PR's review and merge instructions

The base PR is the one a reviewer on the target repository sees first, so put the
instructions for the whole stack in its description:

- Review the stack from the bottom up, starting with the PR based directly on this one.
- Approve each PR in that order.
- Once every PR in the stack is approved, merge them into this PR's branch, bottom first.
- Merge this PR into `<target-owner>/<repo>:<target-branch>` last, which lands the whole
  change at once.

List the stack in that same description, in order, with each PR's number and title, so a
reviewer landing on the base PR can find the rest.

## 8. Report back

Finish with a plain ASCII dependency map and a table. Keep the map simple:

```text
openedx/openedx-core : main                     <- target
└── jesperhodge/openedx-core : jh/642-stack-base    PR #101 (draft)
    └── jh/642-01-models                            PR #102 (draft)
        └── jh/642-02-admin                         PR #103 (draft)
            └── jh/642-03-tests                     PR #104 (draft)
```

Then one table row per PR, with the branch, the PR number and link, the base branch, and a
few words on what the chunk contains. Close by reminding the developer of the two things
left for them: create the stack in GitHub's stacking UI, and mark the PRs ready for review
when they want the review to start.
