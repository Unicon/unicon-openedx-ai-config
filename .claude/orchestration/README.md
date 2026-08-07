# Orchestration

Plans that decide how Claude uses sub-agents for a task, rendered as a mermaid diagram
for approval, and enforced while the task runs.

Driven by the `orchestrate` skill. This directory is the data and the tooling; the skill
is the workflow.

## Why

Three problems, one mechanism:

- **Cost.** The top-level agent is Opus at `xhigh`, the most expensive thing in the
  system. Left alone it does everything itself. A plan pushes recon to Haiku and
  implementation to Sonnet and keeps only planning and judgment on Opus.
- **Reliability.** An evaluator that runs "when it seems worth it" does not run. Every
  plan must declare at least one evaluator gating the developer's answer, and validation
  rejects plans that do not.
- **Visibility.** The orchestration is a file you can read, diff, and change, and a
  diagram generated from that file rather than described in prose.

## Usage

```
python3 .claude/orchestration/orchestrate.py list
python3 .claude/orchestration/orchestrate.py show implementation
python3 .claude/orchestration/orchestrate.py validate --all

python3 .claude/orchestration/orchestrate.py start implementation --task "add X"
python3 .claude/orchestration/orchestrate.py complete <run_id> recon --note "..."
python3 .claude/orchestration/orchestrate.py check <run_id>
```

`check` is the gate. It exits non-zero while any required node is outstanding, and the
skill must run it before the developer receives an answer.

Pure Python 3.12 standard library. No third-party dependencies, no dependency on
openedx-core or its virtualenv. This directory lives in the
`unicon-openedx-ai-config` repository and is symlinked into each project.

## The data model

A plan is a JSON file in `plans/`. `schema.json` documents every field; the validator in
`orchestrate.py` enforces it by hand, since `jsonschema` is not available.

A plan is a **minimum**, not an exhaustive script. Nodes marked `required` must run. The
orchestrator is free to add any other sub-agent, tool, or skill call it judges useful,
and is expected to.

Each node declares the sub-agent's role name, a one or two sentence description of how it
behaves, the agent type to dispatch, the model and effort to dispatch it on, the skills it
may use, and what it hands back.

Four relationships, nothing more:

| Field | Meaning | Diagram |
| --- | --- | --- |
| `inputs` | Hard dependency. Must be acyclic. | solid arrow |
| `gates` | `"user_response"`: must complete before the developer gets an answer. | thick arrow to the answer |
| `requires_user_approval` | Mid-graph barrier: cannot complete until the developer approves. | marked node |
| `feedback` | Loop back to an earlier node on a condition, bounded by `max_iterations`. | dotted arrow |

`requires_user_approval` is not decoration. Plan approval used to live in a node's prose
description, which made the most consequential gate in the system invisible to the
checker and impossible to enforce. As a completion precondition it reuses the existing
DAG: downstream nodes list the node in `inputs`, so they cannot start until approval
lands.

`agent: "orchestrator"` means the top-level agent does that node itself, inline, at no
handover cost. Inline it when the orchestrator already holds the inputs and the work is
synthesis or judgment. Delegate to an agent on the *same* model when independence or
context isolation is the point: a second Opus reviewing the orchestrator's reasoning cold
is worth far more than the orchestrator checking itself.

### Ceilings

Opus at effort `xhigh` is the most expensive configuration allowed. Sonnet never exceeds
effort `high`. Validation enforces both.

## The cost model

Headline figures are percentages. Raw numbers are unitless relative points for comparing
plans, never tokens and never dollars.

Model weights come from list pricing, where input and output ratios are identical, so one
scalar per model is exact: Opus 5, Sonnet 3, Haiku 1. Output tokens cost 5x input at every
model, and effort raises thinking tokens, which are output. So cost splits by `shape`: a
file sweep and a design pass of the same `size` differ severalfold, and effort multiplies
only the thinking half. Everything else is a heuristic, living in one marked constants
block at the top of `orchestrate.py`, which is the intended tuning surface.

The verdict compares the plan's total against `baseline_size`: the author's honest
estimate of what one all-Opus session would spend on a comparable deliverable. That
number is declared per plan and is deliberately **not** derived from the plan's own nodes.

That last point is the load-bearing one. An earlier version derived the baseline from the
node list and excluded `evaluate` nodes from it. Editing one node's `role` from `evaluate`
to `synthesize` then moved the baseline ninefold and flipped the verdict from FAIL to
PASS, with the total cost identical at 693 both times and not a single dispatch changed.
A denominator an author can edit at will is not a test. So the cost model must never
branch on `role`, and the baseline must never be the plan wearing different prices.

Both baselines are reported. When the derived one exceeds the declared one by more than
30%, the tool raises a decomposition flag: the plan is splitting work more finely than a
single agent would, which is exactly how delegation quietly loses money.

Two honest caveats the tool prints and you should believe:

- It ignores prompt caching in both directions. Orchestrator-inline work is the most
  cache-favoured work in the system, worth roughly 10 to 15% off the baseline; delegation
  keeps the orchestrator's window small, which pays on every later turn. **Verdicts inside
  ±15% are too close to call.**
- Effort multipliers are defensible as an ordering and indefensible as exact ratios. They
  need calibration against real usage before anyone quotes them as fact.

`authoring` currently reports COST FAIL. That is correct, not a bug to tune away: two
Opus experts cost more than one Opus pass. It is a deliberate purchase of independent
requirements and design perspectives, and the tool's job is to say so out loud so the
choice is yours.

## Adding a plan

Copy the closest plan in `plans/`, edit it, and run `validate <id>`. The `id` must match
the filename stem. Validation reports every error at once, not just the first.

One-off plans for a single task belong in the scratchpad and are passed with
`--plan-file`. Only add a file to `plans/` when it is worth keeping.

Declare `requires` so a plan carried into another repository fails loudly at validation
rather than mid-run. Validation warns rather than errors, so the plan degrades legibly.

## Run ledgers

Ledgers live under `~/.local/state/claude-orchestration/<project>/`, keyed by consuming
repo and honouring `XDG_STATE_HOME`. They are deliberately outside this directory: this
config is symlinked into many repositories, so ledgers written here would collide across
projects and fill the tools repo with untracked files.

Node status is `pending`, `complete`, or `waived`. Waiving a required node needs a
reason, which records the developer's consent as a first-class state instead of leaving
"bypass the checker" as the only available path.

`orchestrate.py receipt <run_id>` redraws the diagram from the ledger, so you see what
actually ran rather than what was promised. That matters because generating the diagram
from the plan only guarantees it matches the *plan*, which is hand-written too.

## Honest limits, and the way out

As shipped, the ledger is a self-check: the orchestrator is both the enforcer and the
enforced. It turns a silent omission into an affirmative act and leaves an auditable
trail, which is most of the value. It is not a control, and nothing here claims
otherwise. Three single-step bypasses exist: never run `check`, run it and ignore a
non-zero exit, or write a completion record for a node that never ran.

The third bypass is closeable today, and it is the one worth closing first, because it
turns the ledger from a claim into evidence. A `SubagentStop` hook fires once per
sub-agent, from the harness rather than the model, carrying `agent_id`, `agent_type`, and
the sub-agent's final message. A ledger written from that hook records dispatches that
actually happened. Register the writer on `PostToolUse` with matcher `Agent`, which cannot
block anything no matter how it exits, and keep any `SubagentStop` handler always exiting
0. `$CLAUDE_PROJECT_DIR` is exported into the hook process and resolves per invocation, so
one hook shared through this symlinked config sees the correct repo each time.

Per-sub-agent token usage is a harder case worth knowing about before relying on it. The
usage fields exist, but only on `PostToolUse` for sub-agents run in the *foreground*, and
sub-agents now run in the background by default. Getting real token accounting means
forcing foreground and giving up concurrency, or parsing each sub-agent's transcript,
which is not a documented guarantee. Until one of those is done, treat the cost model's
constants as uncalibrated estimates rather than measurements.

A `Stop` hook shelling `check` is the remaining piece for the first two bypasses. It is
deliberately not installed: it would apply to every repository this config is symlinked
into. If added, it must fail open on every error, and note that Claude Code force-ends a
turn after 8 consecutive blocks, so a buggy hook degrades rather than wedging a session
permanently.
