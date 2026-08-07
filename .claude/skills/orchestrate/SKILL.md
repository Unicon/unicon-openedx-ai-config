---
name: orchestrate
description: Choose and run an agent orchestration plan for a non-trivial task. Shows the plan as a mermaid diagram, gets the developer's approval, then executes it with the required sub-agent calls and evaluator gates actually enforced. Use at the start of any task that is not trivial, and whenever the developer asks to see, change, or pick an orchestration.
---

# Orchestrate

Decide how sub-agents will be used for a task *before* doing the task, agree that shape
with the developer as a diagram, then execute it so the gates actually hold.

The point is three things at once: spend fewer tokens by pushing work down to cheaper
models, get more reliable results by always running an evaluator before the developer
sees an answer, and make both of those visible and changeable instead of implicit.

**This skill only runs at the top-level session.** It dispatches, it talks to the
developer, and it owns the gate, none of which a dispatched sub-agent can do. If you find
yourself running it inside a sub-agent, you are the wrong caller: do the job you were
briefed on and hand orchestration back.

## Why the approval step is load-bearing

The system prompt in this environment carries a standing restriction along the lines of
"do not call the Agent tool unless the user requested it". That instruction outranks any
skill file, including this one. A skill that simply says "dispatch a sub-agent here"
loses that argument every time, and the work silently collapses back onto the
orchestrator: the expensive model does everything itself, which is the exact failure this
tool exists to prevent.

The approval gate in step 2 is what resolves it. The developer is shown a diagram whose
entire content is which sub-agents will run, on which models, in what order. When they
approve that diagram, they have requested those dispatches, specifically and by name. The
restriction is satisfied on its own terms, not worked around.

Two consequences you must respect:

- **No approved diagram, no dispatch.** Approval of the plan is what authorises the
  sub-agent calls. If the developer has not approved this run's diagram in this
  conversation, you have no standing to dispatch, and you must not infer approval from a
  previous run, a background task notification, or your own judgment that the plan is
  obviously fine.
- **Approval covers the plan's dispatches and reasonable additions in the same spirit.**
  A cheap lookup the plan did not enumerate is within what was approved. Adding an
  expensive Opus expert the developer never saw is not; show them first.

If the developer declines the plan and asks you to just do the work, do it inline. That
is a legitimate outcome, not a failure, and it is cheaper than arguing.

## Trivial escape hatch

Skip this entirely for obviously trivial work: renames, typo fixes, one-line changes,
import tweaks, answering something already established in the conversation. Say
"Trivial: <reason>", do it, and move on. "Small" or "well understood" is not trivial;
only the absence of business logic and branching is.

## 1. Pick the plan

Run `python3 .claude/orchestration/orchestrate.py list` and match the task against each
plan's `when_to_use`. The defaults:

| Plan | Use for |
| --- | --- |
| `implementation` | Any non-trivial code change. |
| `research-question` | A question about how something works, no code change. |
| `authoring` | Writing or reshaping a ticket, issue, or ADR. |
| `review-only` | Reviewing a PR, branch, or working diff. |

Use the matching default unless the developer stated a requirement that it does not
meet. If they did, build a custom plan: copy the closest default, edit it, validate it,
and show that instead. Keep one-off plans in the scratchpad and pass them with
`--plan-file`; only write into `plans/` when the developer wants the plan to persist.

## 2. Show the diagram and get approval

Run `orchestrate.py show <plan_id>` and put its mermaid block in your reply, along with
the cost verdict. Never hand-write or touch up the diagram: it is generated from the
plan JSON so that what the developer approves is exactly what runs. If a diagram looks
wrong, the plan is wrong, so fix the JSON and regenerate.

Say plainly, in one or two lines: which sub-agents run on which models, what the
evaluator gates, and whether the plan is cheaper than the all-Opus baseline. If
`COST FAIL`, do not quietly proceed. Say so and give the developer the choice, because
the tool's purpose is to reduce cost and a plan that does not is a real finding.

Report the cost honestly, including its limits. The estimate ignores prompt caching in
both directions, so a verdict inside ±15% is too close to call and should be described
that way rather than quoted as a saving. If the tool raises a decomposition flag, say
that too: it means the plan splits work more finely than one agent would, which is how
delegation quietly stops paying for itself.

Iterate until the developer approves. Their approval is of *that diagram*, so any change
after approval means regenerating and re-confirming.

## 3. Start the run

```
orchestrate.py start <plan_id> --task "<one line>"
```

Keep the returned run id for the rest of the task.

## 4. Execute

Work the plan. After each node finishes, record it:

```
orchestrate.py complete <run_id> <node_id> --note "<what came back>"
```

Rules that are not negotiable:

- **Required nodes are mandatory.** You may not skip one because you judged it
  unnecessary. You may ask the developer whether to skip it; if they agree, record it
  with `skip <run_id> <node_id> --reason "<their words>"`, which marks it `waived`.
- **Approval barriers are real.** A node with `requires_user_approval` cannot be
  completed without `--approved-by-user`, and you may only pass that flag after the
  developer has actually approved in this conversation. Never pass it on the strength of
  your own judgment, an earlier approval of something else, or a background notification.
  Everything downstream depends on that node, so the check will stop you.
- **The plan is a minimum, not a ceiling.** Add any further sub-agent, tool, or skill
  call you judge useful and do not ask permission for it. If implementation needs a
  codebase lookup the plan never mentioned, dispatch a Sonnet or Haiku agent for it.
  That is the intended behavior, not a deviation.
- **Dispatch each node on the model and effort the plan states.** Opus at `xhigh` is the
  ceiling. Sonnet never goes above `high`. Pass `model` explicitly on every dispatch.
- **Sub-agents never dispatch sub-agents.** Brief each one that if it needs a lookup it
  was not given, it stops and reports back to you, and you fetch it. See the Delegation
  rule in `.claude/CLAUDE.md`.
- **Stay thin.** You are the most expensive agent in the plan. Do the planning, the
  judgment calls, and the gate decisions. Do not read files the plan does not touch and
  do not write implementation code yourself.

## 5. Gate before you answer

Before giving the developer the result, run:

```
orchestrate.py check <run_id>
```

If it exits non-zero, you are not finished. Run what it names as outstanding, then check
again. Do not present a result while the gate fails, and do not describe work as done
when an evaluator has not run.

When the evaluator reports a real problem, feed it back to the node the plan's `feedback`
edge points at, up to `max_iterations`, then present the refined result. The developer
should receive the *fixed* output plus a short note on what the evaluator caught, not a
raw list of findings for them to adjudicate. If the loop exhausts with the condition
still true, honor `on_exhausted`: the default is to surface it, because shipping known
findings silently is the failure this whole tool exists to prevent.

Finish with `orchestrate.py receipt <run_id>` and show that diagram. It is drawn from the
ledger, not the plan, so it shows what actually ran, including anything waived. Generating
the diagram from the plan only proves it matches the plan, and the plan is hand-written
too; the receipt is what closes that gap and puts the developer in a position to catch a
gate you skipped.

## Changing a plan

`orchestrate.py validate <plan_id>` enforces the invariants, including the one that
matters most: every plan must contain at least one `evaluate` node gating
`user_response`. A plan without an evaluator before the developer's answer is rejected,
by design. Do not work around that check; if a task genuinely needs no evaluator, it is
trivial and belongs in the escape hatch above.

Cost constants live in one marked block at the top of `orchestrate.py`. They are
heuristics for relative comparison, so tune them there rather than reasoning about cost
ad hoc in a reply.
