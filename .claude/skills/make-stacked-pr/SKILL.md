---
name: make-stacked-pr
description: Turn a finished branch into a stack of small draft PRs that are easy to review. Use when asked to make a stacked PR, open a PR stack, or split a branch into reviewable chunks. Handles both a stack that targets upstream main and one that targets another person's branch in their fork. Opens everything as drafts, never merges.
---

# Make a stacked PR

One branch holding a large change is hard to review. This skill turns that branch into a
chain of small draft PRs, each a meaningful chunk, so a reviewer can work through them one
at a time.

The shape it produces:

- **A base PR.** Its head branch holds one minimal change (a version bump, a changelog
  line). It is the only PR that points at the target repository, and it is where the
  review and merge instructions for the whole stack live.
- **The chunk PRs.** Each one's head branch is built on the branch below it, and each one
  is opened inside the developer's own fork, based on the base PR's branch. Because head
  and base both live in the fork, GitHub treats them as a real stack.

Every PR is a draft. This skill never merges, never marks a PR ready for review, and never
rewrites a branch the developer has already pushed somewhere else.

## 1. Pin down the target

Ask the developer, with `AskUserQuestion`, where the stack is aimed, because it decides
which repository the base PR is opened against:

- **Upstream main.** The base PR goes to the upstream repository (`upstream`, for example
  `openedx/openedx-core`) against its default branch.
- **Someone else's branch.** The stack depends on work that is not merged yet, so the base
  PR goes to that person's fork, against their branch. Get the owner and the branch name
  from the developer, and fetch that branch so you can build on the right commit.

State back the resolved target as `<owner>/<repo>:<branch>` and confirm it before you
create anything. Getting this wrong means the whole stack has the wrong contents.

## 2. Ask how to split the branch

Do not decide the split yourself. Show the developer what there is to split:

```bash
git fetch <target-remote>
git log --oneline "$(git merge-base HEAD <target-ref>)"..HEAD
git diff --stat "$(git merge-base HEAD <target-ref>)"..HEAD
```

Then ask them how to chunk it, with `AskUserQuestion`, offering concrete options drawn
from that output rather than generic ones: one PR per commit, a named grouping of the
existing commits, or a re-slice by file area that ignores the current commit boundaries.

Two things to tell them while they decide:

- A chunk should stand on its own. If a chunk leaves the repository failing its tests
  until a later chunk lands, say so and name the chunk. The developer still makes the
  call, but they should make it knowing that.
- Re-slicing costs work. Cutting at existing commit boundaries is a `git switch -c` per
  chunk. Anything else means cherry-picking or splitting commits.

## 3. Choose the base PR's minimal change

Look through the branch for the smallest genuine change in it that can stand alone, such
as a version bump, a changelog entry, or a requirements pin, and propose that as the base
PR's only content. If the branch contains nothing suitable, ask the developer what the
base PR should hold instead. Do not invent a change that was not going to be made anyway.

## 4. Get one approval for the whole plan

Before touching git, show the developer the complete plan: the target, the base branch and
its minimal change, every chunk branch with its base and its contents, and the ASCII map
from step 7. Get one approval for all of it. After that approval, run the rest without
stopping again.

## 5. Build the branches

Name the branches so the stack order is readable, for example
`<developer>/<ticket>-stack-base`, then `<developer>/<ticket>-01-<slug>`,
`<developer>/<ticket>-02-<slug>`, and so on.

Cut the base branch from the target ref, put the minimal change on it, then cut each chunk
branch from the branch below it:

```bash
git switch -c <ticket>-stack-base <target-remote>/<target-branch>
# apply the minimal change, commit
git switch -c <ticket>-01-<slug> <ticket>-stack-base
# apply chunk 1, commit
git switch -c <ticket>-02-<slug> <ticket>-01-<slug>
```

Push every branch to the developer's fork (`origin`) with `git push -u origin <branch>`.
The tip branch ends up holding the minimal change plus every chunk, which is the original
branch's content, so nothing is lost when the stack merges down.

## 6. Open the draft PRs

The base PR is the only cross-repository one:

```bash
gh pr create --repo <target-owner>/<repo> --base <target-branch> \
  --head <fork-owner>:<ticket>-stack-base --draft --title "..." --body "..."
```

Each chunk PR is opened inside the fork, based on the branch below it:

```bash
gh pr create --repo <fork-owner>/<repo> --base <ticket>-stack-base \
  --head <ticket>-01-<slug> --draft --title "..." --body "..."
```

After creating each one, confirm it landed where you meant it to:

```bash
gh pr view <number> --repo <fork-owner>/<repo> --json baseRepository,baseRefName,headRefName
```

`gh` defaults a fork's base repository to the upstream parent, so a chunk PR that was
meant to stay inside the fork can end up opened against upstream instead. A PR's base
repository cannot be edited after the fact, so if one landed wrong, close it and create it
again with `--repo` set explicitly.

Give each chunk PR a body that says what the chunk does and which PR it sits on top of.
Do not wire the stack together with tooling or the API beyond setting each PR's base
branch, which is all the steps above do. Tell the developer to create the stack itself in
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

```
openedx/openedx-core : main                  <- target
└── jesperhodge/openedx-core : 642-stack-base    PR #101 (draft)
    └── 642-01-models                            PR #102 (draft)
        └── 642-02-admin                         PR #103 (draft)
            └── 642-03-tests                     PR #104 (draft)
```

Then one table row per PR, with the branch, the PR number and link, the base branch, and a
few words on what the chunk contains. Close by reminding the developer of the two things
left for them: create the stack in GitHub's stacking UI, and mark the PRs ready for review
when they want the review to start.
