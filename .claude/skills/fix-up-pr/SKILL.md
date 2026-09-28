---
name: fix-up-pr
description: Final pass over a pull request before it is merged, after a code review has come in. Use when asked to fix up a PR, address review comments, or do a last check on a PR or a stack of PRs. Works for a single PR or a stack, and for a ticket that is a child of a parent ticket. Covers acceptance-criteria coverage, test quality, review comments, and the blast radius and security of the change.
---

# Fix up a PR

A pull request has been reviewed and now has to be brought to a merge-ready state. This
skill does four things: it confirms the change actually satisfies the acceptance criteria
it claims, it checks that the tests would fail if the code broke, it works through the
review comments with the developer deciding each one, and it looks at what the change can
break outside its own diff.

The developer decides which review comments get acted on. Do not silently implement a
reviewer's suggestion the developer has not agreed to, and do not commit or push unless
asked.

This skill runs in the top-level session. Per the Delegation rule in `CLAUDE.md`, that
session is the only one that dispatches sub-agents; a dispatched sub-agent never
dispatches a further one.

## 1. Establish what is being fixed up

Before anything else, pin down these four things and state them back to the developer:

- **The pull requests in scope.** One PR, or a stack of several. If the developer named a
  range or a branch, resolve it with `gh pr list` and `gh pr view`.
- **The ticket the work implements.** Usually in the PR description ("closes #N") or in
  the branch name. Confirm it rather than inferring it.
- **Whether that ticket has a parent.** A ticket is often one slice of a larger one, and
  the parent holds the acceptance criteria that the child narrows. Follow the parent links
  upward until you reach the ticket that actually states acceptance criteria. There may be
  no parent at all, in which case the ticket's own criteria are the whole picture.
- **Whether any additional context is important.** Sometimes ADRs in some
  `docs/decisions` folders are relevant, or documentation elsewhere.

The PRs and the issues often live in different repositories: PRs on a fork (`origin`,
here `jesperhodge/openedx-core`), issues on the upstream repository (`upstream`, here
`openedx/openedx-core`). Pass `--repo <owner>/<name>` to every `gh` call so you are
reading the right one.

If any of the four is ambiguous, ask with `AskUserQuestion` instead of guessing. A wrong
ticket means you check the change against the wrong criteria, and every step after that is
wasted.

### When it is a stack

A stack is a chain of PRs where each PR's base is the PR below it, so the diffs are
cumulative. Two consequences shape the rest of this skill:

- **Review in stack order, bottom first.** A later PR can move, fix, or delete code an
  earlier PR introduced, so a finding against the bottom PR may already be resolved higher
  up. Check the tip of the stack before reporting such a finding.
- **Judge acceptance criteria against the whole stack, but review comments per PR.** An
  acceptance criterion may be implemented in one PR and tested in another, and that is
  fine. Only call coverage missing when it is missing from every PR in the stack. A review
  comment, in contrast, belongs to the PR it was left on and is answered there.

For a single PR both points collapse: that PR is the whole change, and there is one set of
comments.

### Sequential or parallel, for a stack

Once you know it is a stack, ask the developer with `AskUserQuestion` how to work through
it, and offer these two options:

- **Sequential.** You handle the PRs yourself, bottom of the stack first. One context holds
  the whole stack, so you can see directly that a later PR already resolved an earlier
  one's problem, and that an acceptance criterion implemented low in the stack is tested
  higher up. Slower, and the whole stack's diffs and comment threads land in your context.
- **Parallel.** One `general-purpose` sub-agent on Sonnet per PR, each in its own git
  worktree (pass `isolation: "worktree"` on the Agent call), all dispatched in a single
  message so they run at once. Faster, and each PR's bulk reading stays out of your
  context. The cost is that no sub-agent can see the rest of the stack, so the
  cross-PR judgments are yours to make afterward.

Recommend sequential for two or three PRs, where the coordination costs more than the
parallelism saves, and parallel for a longer stack.

If the developer picks parallel:

- Do step 2 yourself first, before dispatching anything. Every sub-agent has to work from
  the same set of applicable acceptance criteria, and that set is a judgment call about
  the ticket, not something to make four times independently.
- Brief each sub-agent completely: its PR number, the repository to pass to `gh`, the
  branch to check out in its worktree, the applicable acceptance criteria from step 2, and
  the fact that it is one PR in a stack rather than the whole change. Per the Delegation
  rule in `CLAUDE.md`, it cannot dispatch a sub-agent of its own, so tell it to report back
  what it needs instead of trying.
- Have each sub-agent run steps 3 through 5 and step 7 for its own PR, plus step 6's first
  pass, the one that checks each comment against the current code and drops the ones
  already handled. That pass belongs in the sub-agent because it is reading that PR's code
  anyway. The sub-agent reports its findings and the comments that survived, including any
  it judges to be a decision for the developer. It does not ask the developer anything
  itself.
- Apply the fixes bottom-up from your own session after the reports are in, not inside the
  sub-agents. Changing a lower PR forces a rebase of every PR above it in the stack, and
  that is a sequential operation however the investigation was parallelized.
- Reconcile the reports before presenting them. A sub-agent reporting an uncovered
  acceptance criterion or an unfixed bug may be looking at something a PR above it already
  handles, and it had no way to know.

## 2. Work out which acceptance criteria apply

Read the acceptance criteria from the ticket that states them. If the work is a child
ticket, read the parent's criteria and then use the child ticket to select the subset the
PRs are actually on the hook for. Do not hold the change to criteria the child ticket does
not claim, and say which ones you excluded so the developer can correct you.

Acceptance criteria are the source of truth. However, sometimes they can go stale when the PR lands, as ticket and PR discussions move forward. So, check the comments in tickets and the PR, and if you find conflicts, you should flag it to the developer and clarify. Do not assume that the acceptance criteria have changed - instead, if you see any conflict, always ask.

Produce an explicit table before going further: each criterion, whether it is in scope for
these PRs, and where in the diff and in the tests it is satisfied. That table is what the
rest of the check is measured against.

Reading a stack's worth of issue bodies and comment threads is bulk reading, so for a
stack, dispatch a Sonnet `general-purpose` sub-agent to gather and condense them, and work
from its digest. For a single PR, run the `gh` calls inline.

## 3. Gather each PR's description and comments

For each PR in scope:

```
gh pr view <n> --repo <owner>/<name> --comments
gh pr diff <n> --repo <owner>/<name>
gh api repos/<owner>/<name>/pulls/<n>/comments
```

The last call matters: inline review comments on specific lines do not appear in
`gh pr view --comments`, and those lines are usually where the substantive review lives.
Also pull the review summaries (`gh api repos/<owner>/<name>/pulls/<n>/reviews`) when a
reviewer left their main point in the review body rather than on a line.

Also fetch which review threads GitHub already marks resolved. That state is not in the
REST comments endpoint, so it takes a GraphQL query:

```
gh api graphql -f query='
  query($owner:String!, $name:String!, $number:Int!) {
    repository(owner:$owner, name:$name) {
      pullRequest(number:$number) {
        reviewThreads(first:100) {
          nodes { isResolved isOutdated path line comments(first:20) { nodes { author { login } body } } }
        }
      }
    }
  }' -F owner=<owner> -F name=<name> -F number=<n>
```

Carry the `isResolved` and `isOutdated` flags into step 6. They are signals about each
comment, not verdicts on it.

## 4. Run the testing instructions

Run whatever the PR description asks a reviewer to run, as far as it can be run here.
Report what passed, what failed along with its output, and what you skipped along with why
(a devstack that is not running, a manual browser step, data you do not have). Do not
report a skipped step as a pass.

Follow the verification rules in `CLAUDE.md`: run the relevant linters directly rather
than `make validate`, and run pytest without coverage, scoped to the tests related to the
changed code. In a frontend repository, use that repository's own tools instead.

## 5. Check the tests

- Every applicable acceptance criterion has at least one test that exercises its path.
- Enumerate the edge cases of the changed behavior yourself. Then filter that list down to
  the ones with real impact, and say which ones you dropped and why. Volume is not the
  goal.
- Those major edge cases have tests.
- The tests genuinely pass and fail. For each load-bearing test, break the code path it
  covers, confirm the test fails, and confirm it fails for the reason its name states
  rather than on an import error or an unrelated assertion. Revert the break immediately
  afterward and verify the tree is clean. A test that passes against broken code is worse
  than no test.
- No test asserts behavior that contradicts the acceptance criteria. When one does, either
  the test is stale or the criterion is, and the supersession question from step 2 decides
  which.

Add the missing tests and fix the broken ones. New tests follow the conventions of the
test module they land in rather than introducing a new style.

## 6. Work through the review comments

Several of the comments have usually been dealt with already, so make that the first pass.
For every comment that asks for a change, look at the code as it stands now, at the tip of
the PR, before you consider doing the work. A comment can already be handled in three ways:
a later commit on the same PR addressed it, a later PR in the stack addressed it, or the
author fixed it without saying so in the thread.

Decide that against the code, not against the thread's state. A thread marked resolved on
GitHub does not prove the change landed, an unresolved thread does not prove it did not,
and `isOutdated` only means the diff moved under the comment, which often happens for
unrelated reasons. Use those flags to decide which comments to check first, then confirm
by reading the code the comment points at.

List each already-handled comment with the `file:line` or commit that handles it, and move
on without redoing the work. If you cannot tell whether a comment was addressed, treat it
as open and say that you were not sure.

Evaluate what is left on its merits: a reviewer can be wrong, and a comment that was right
when it was written can be obsolete now. Sort the remaining comments into three groups:

1. Clearly correct and mechanical. Fix these.
2. Clearly not applicable. Say why, and leave the code alone.
3. Genuinely a decision, meaning the reviewer's suggestion and the current code are two
   defensible options.

Batch every group-three question into one round with `AskUserQuestion` rather than
interrupting after each comment, per the batching rule in `CLAUDE.md`. For a stack that
means one round across all of its PRs, including the decisions the sub-agents handed back
in parallel mode, not one round per PR. Include your own recommendation for each question.
Then fix the accepted items one at a time, making the smallest correct change each time.

When an accepted item is genuinely complex, meaning it changes a public API, a data model,
a boundary between apps, or the migration story, stop and discuss it with the developer.
Recommend that they run that one item on a strong model with the `software-architect`
sub-agent rather than folding it into this pass.

## 7. Determine the blast radius and check security

Work out what the change can affect beyond its own diff, and say so explicitly:

- The public API surface, and whether any change to a stable (non-UNSTABLE) API needs to
  go through DEPR.
- Database migrations: backward compatibility, table locks, data loss, and ordering
  against migrations already merged.
- Callers of the changed code elsewhere in this repository, and in `openedx-platform` or
  community plugins that consume it. Delegate that search to an `Explore` sub-agent.
- Settings, feature flags, and anything else that changes behavior for an existing
  deployment.

Then list the security questions this change actually raises, and answer each one against
the code rather than from memory: authentication and permission checks on new or changed
REST endpoints, input validation, object-level access (whether one user can reach another
user's objects), injection through raw SQL or unescaped output, secrets in code or logs,
PII annotations on new models, and any new dependency.

If you find a security gap, put it at the top of your report under its own heading so that
it cannot be missed, state the concrete attack path, and fix it.

## 8. Report

One section per PR, plus a summary across the stack when there is one. Cover the
acceptance-criteria table from step 2, what you ran and what it did, tests added or fixed,
review comments grouped by what happened to each, the blast radius, and the security
findings.

State the gaps plainly: criteria you could not verify, tests you did not add, testing
instructions you could not run. A gap named is useful; a gap glossed over is not.
