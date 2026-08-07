#!/usr/bin/env python3
"""Developer CLI for orchestration plans under ``.claude/orchestration``.

This is tooling for developers driving Claude Code sub-agent orchestration.
It is NOT part of the openedx-core library and must never import from it.

Python 3.12 standard library only: no pydantic, no jsonschema, no third-party
imports of any kind. Plan documents are hand-validated against the field-by-
field spec in ``schema.json`` (documentation only, not a runtime dependency).

Subcommands:
    list                                     table of every plan in plans/
    validate [plan_id | --all]               hand-rolled schema + graph validation
    show <plan_id> [--plan-file <path>]      title/mandate/mermaid/cost report
    start <plan_id> [--plan-file <path>]     create a run ledger
         --task "..."
    complete <run_id> <node_id>              mark a node complete in a run
         [--approved-by-user]
    skip <run_id> <node_id> --reason "..."   mark a node waived in a run
    check <run_id>                           the gate: are required nodes done?
    receipt <run_id>                         mermaid diagram of what actually happened

Run as ``python3 .claude/orchestration/orchestrate.py <subcommand>`` from the
repo root, or by absolute path from anywhere -- all paths are resolved
relative to this script's own location, never the current working directory.

Ledgers (run state) live outside this repo entirely: see ``default_state_dir``.
``.claude/`` is shared config symlinked into many repos, so run files must not
collide across projects or pollute a tools repo's own git history.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Paths -- resolved relative to this script's own location, not the cwd, and
# not the caller's argv[0], so this works whether invoked as a relative path
# from the repo root or by absolute path from anywhere (including through a
# symlink -- .claude/ in this repo is itself one).
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_PLANS_DIR = SCRIPT_DIR / "plans"
DEFAULT_CLAUDE_DIR = SCRIPT_DIR.parent

SLUG_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

# Agent kinds that are SDK/engine builtins, always available regardless of
# whether a file exists for them under .claude/agents/. Only agent kinds
# backed by a repo-authored definition file (business-analyst,
# software-architect) need that file to actually exist.
BUILTIN_AGENT_KINDS: set[str] = {"orchestrator", "Explore", "general-purpose", "Plan", "claude"}


def _slugify(text: str) -> str:
    """Human-readable prefix plus a hash of the full input, so distinct paths
    that collapse to the same readable slug (``foo_bar``, ``foo-bar``,
    ``foo.bar``, ``foo bar``, or a case difference) still key to different
    state directories -- the exact collision this slug exists to prevent."""
    out: list[str] = []
    prev_dash = False
    for ch in text:
        if ch.isalnum():
            out.append(ch.lower())
            prev_dash = False
        elif not prev_dash:
            out.append("-")
            prev_dash = True
    readable = "".join(out).strip("-") or "root"
    digest = hashlib.sha256(text.encode()).hexdigest()[:8]
    return f"{readable[:60]}-{digest}"


def default_state_dir() -> Path:
    """``~/.local/state/claude-orchestration/<project slug>``, honoring ``XDG_STATE_HOME``.

    Computed fresh on every call (not cached at import time) so tests can
    point it elsewhere by setting the environment before calling.
    """
    xdg = os.environ.get("XDG_STATE_HOME")
    base = Path(xdg) if xdg else Path.home() / ".local" / "state"
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or str(Path.cwd())
    slug = _slugify(str(Path(project_dir).resolve()))
    return base / "claude-orchestration" / slug


# ---------------------------------------------------------------------------
# Enums -- mirror schema.json's $defs exactly.
# ---------------------------------------------------------------------------
class Model(str, Enum):
    HAIKU = "haiku"
    SONNET = "sonnet"
    OPUS = "opus"


class Effort(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    XHIGH = "xhigh"


class Size(str, Enum):
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


class Role(str, Enum):
    RESEARCH = "research"
    PLAN = "plan"
    IMPLEMENT = "implement"
    EVALUATE = "evaluate"
    SYNTHESIZE = "synthesize"


class Shape(str, Enum):
    READ_HEAVY = "read-heavy"
    BALANCED = "balanced"
    THINK_HEAVY = "think-heavy"


class AgentType(str, Enum):
    ORCHESTRATOR = "orchestrator"
    EXPLORE = "Explore"
    GENERAL_PURPOSE = "general-purpose"
    BUSINESS_ANALYST = "business-analyst"
    SOFTWARE_ARCHITECT = "software-architect"
    PLAN = "Plan"
    CLAUDE = "claude"


class OnExhausted(str, Enum):
    SURFACE_TO_USER = "surface_to_user"
    PROCEED = "proceed"


# ---------------------------------------------------------------------------
# Data model -- mirrors schema.json's object shapes. Kept as plain dataclasses
# so a future swap to pydantic only has to replace parse_plan() below; nothing
# else in this file should need to change shape.
# ---------------------------------------------------------------------------
@dataclass
class Feedback:
    to: str
    when: str
    max_iterations: int
    on_exhausted: OnExhausted = OnExhausted.SURFACE_TO_USER


@dataclass
class Requires:
    agents: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)


@dataclass
class Node:
    id: str
    name: str
    description: str
    agent: AgentType
    model: Model
    effort: Effort
    size: Size
    role: Role
    required: bool
    shape: Shape = Shape.BALANCED
    requires_user_approval: bool = False
    skills: list[str] = field(default_factory=list)
    inputs: list[str] = field(default_factory=list)
    produces: Optional[str] = None
    gates: Optional[str] = None
    feedback: Optional[Feedback] = None


@dataclass
class Orchestrator:
    model: Model
    effort: Effort
    mandate: str


@dataclass
class Plan:
    id: str
    title: str
    description: str
    when_to_use: str
    baseline_size: float
    orchestrator: Orchestrator
    nodes: list[Node] = field(default_factory=list)
    requires: Optional[Requires] = None


# ---------------------------------------------------------------------------
# Cost model constants -- heuristics for *relative* comparison only. These are
# not real dollar or token figures; they exist so different plan shapes can be
# compared against each other and against an all-Opus baseline. This block is
# the intended tuning surface: adjust weights here, not scattered elsewhere.
#
# IMPORTANT: nothing here, or in the functions below, may branch on `role`.
# An earlier version excluded 'evaluate' nodes from the baseline, which meant
# relabeling a node flipped a plan's verdict without changing any dispatch.
# `role` is diagram colouring and an explanatory breakdown only; the
# denominator must be label-invariant.
# ---------------------------------------------------------------------------
MODEL_WEIGHT: dict[str, float] = {"haiku": 1.0, "sonnet": 3.0, "opus": 5.0}
EFFORT_MULTIPLIER: dict[str, float] = {"low": 0.6, "medium": 1.0, "high": 1.5, "xhigh": 2.2}
SIZE_UNITS: dict[str, float] = {"small": 10.0, "medium": 30.0, "large": 80.0}
SHAPE_SPLIT: dict[str, tuple[float, float]] = {
    "read-heavy": (0.8, 0.2),
    "balanced": (0.5, 0.5),
    "think-heavy": (0.2, 0.8),
}
OUTPUT_WEIGHT: float = 5.0  # output tokens cost 5x input at every model
PREFIX_UNITS: dict[str, float] = {
    "orchestrator": 0.0,
    "Explore": 8.0,
    "general-purpose": 10.0,
    "business-analyst": 15.0,
    "software-architect": 15.0,
    "Plan": 10.0,
    "claude": 10.0,
}
RETURN_UNITS: dict[str, float] = {"small": 3.0, "medium": 6.0, "large": 10.0}
LOOP_ITER_FRACTION: float = 0.35
LOOP_PROBABILITY: list[float] = [0.5, 0.2, 0.1]  # per successive iteration
# Compared against *sizes*, not costs. Comparing costs lets a node's `shape` and
# `effort` leak in, so a plan with one think-heavy node reads as "finely decomposed"
# when it is really just deliberating harder in the same number of steps.
DECOMPOSITION_FLAG_THRESHOLD: float = 1.3
TOO_CLOSE_TO_CALL_PCT: float = 15.0


# =============================================================================
# Parsing / validation
#
# Everything below builds a Plan (best-effort, with safe fallback values for
# malformed fields) plus a list of human-readable error strings. Parsing never
# raises and never stops at the first problem, so `validate` can report every
# error in one pass, per the project rule that validation is exhaustive.
# =============================================================================


def _enum_or_none(enum_cls: type[Enum], value: object) -> object | None:
    """Return the matching enum member for ``value``, or None if invalid."""
    if not isinstance(value, str):
        return None
    try:
        return enum_cls(value)
    except ValueError:
        return None


_CONTROL_CHAR_IN_VALUE_PATTERN = re.compile(r"[\x00-\x1f\x7f]")


def _contains_control_chars(text: str) -> bool:
    """True if `text` contains a control character (including newline/tab).

    Rejected at validation time in free-text fields that later get embedded
    in a single mermaid statement (name, description, feedback.when), so the
    problem is caught at the source rather than papered over at render time.
    """
    return bool(_CONTROL_CHAR_IN_VALUE_PATTERN.search(text))


def _check_unknown_and_missing(raw: dict, allowed: set[str], required: set[str], where: str) -> list[str]:
    errors: list[str] = []
    unknown = set(raw) - allowed
    missing = required - set(raw)
    for f in sorted(missing):
        errors.append(f"{where}: missing required field '{f}'")
    for f in sorted(unknown):
        errors.append(f"{where}: unknown field '{f}'")
    return errors


def parse_requires(raw: object) -> tuple[Optional[Requires], list[str]]:
    errors: list[str] = []
    where = "requires"
    if not isinstance(raw, dict):
        return None, [f"{where} must be an object"]

    allowed = {"agents", "skills"}
    errors.extend(_check_unknown_and_missing(raw, allowed, set(), where))

    agents_raw = raw.get("agents", [])
    agents: list[str] = []
    if not isinstance(agents_raw, list) or not all(isinstance(a, str) for a in agents_raw):
        errors.append(f"{where}.agents must be an array of strings")
    else:
        agents = agents_raw

    skills_raw = raw.get("skills", [])
    skills: list[str] = []
    if not isinstance(skills_raw, list) or not all(isinstance(s, str) for s in skills_raw):
        errors.append(f"{where}.skills must be an array of strings")
    else:
        skills = skills_raw

    return Requires(agents=agents, skills=skills), errors


def parse_feedback(raw: object, node_label: str) -> tuple[Optional[Feedback], list[str]]:
    """Parse a node's ``feedback`` object. ``raw`` is the value already known non-None."""
    errors: list[str] = []
    where = f"node '{node_label}': feedback"
    if not isinstance(raw, dict):
        return None, [f"{where} must be an object"]

    allowed = {"to", "when", "max_iterations", "on_exhausted"}
    required = {"to", "when", "max_iterations"}
    errors.extend(_check_unknown_and_missing(raw, allowed, required, where))

    to = raw.get("to")
    if "to" in raw and (not isinstance(to, str) or len(to) < 1):
        errors.append(f"{where}.to must be a non-empty string")
    if not isinstance(to, str):
        to = ""

    when = raw.get("when")
    if "when" in raw and (not isinstance(when, str) or len(when) < 1):
        errors.append(f"{where}.when must be a non-empty string")
    elif isinstance(when, str) and _contains_control_chars(when):
        errors.append(f"{where}.when must not contain control characters")
    if not isinstance(when, str):
        when = ""

    max_iterations = raw.get("max_iterations")
    valid_max_iterations = (
        isinstance(max_iterations, int) and not isinstance(max_iterations, bool) and 1 <= max_iterations <= 3
    )
    if "max_iterations" in raw and not valid_max_iterations:
        errors.append(f"{where}.max_iterations must be an integer in 1..3, got {max_iterations!r}")
    if not valid_max_iterations:
        max_iterations = 1

    on_exhausted: Optional[OnExhausted] = None
    if "on_exhausted" in raw:
        on_exhausted = _enum_or_none(OnExhausted, raw.get("on_exhausted"))
        if on_exhausted is None:
            errors.append(
                f"{where}.on_exhausted must be one of {sorted(o.value for o in OnExhausted)}, "
                f"got {raw.get('on_exhausted')!r}"
            )
    if on_exhausted is None:
        on_exhausted = OnExhausted.SURFACE_TO_USER

    return Feedback(to=to, when=when, max_iterations=max_iterations, on_exhausted=on_exhausted), errors


def parse_orchestrator(raw: object) -> tuple[Orchestrator, list[str]]:
    errors: list[str] = []
    where = "orchestrator"
    if not isinstance(raw, dict):
        return Orchestrator(model=Model.OPUS, effort=Effort.XHIGH, mandate=""), [f"{where} must be an object"]

    allowed = {"model", "effort", "mandate"}
    required = {"model", "effort", "mandate"}
    errors.extend(_check_unknown_and_missing(raw, allowed, required, where))

    model = _enum_or_none(Model, raw.get("model")) if "model" in raw else None
    if "model" in raw and model is None:
        errors.append(f"{where}.model must be one of {sorted(m.value for m in Model)}, got {raw.get('model')!r}")

    effort = _enum_or_none(Effort, raw.get("effort")) if "effort" in raw else None
    if "effort" in raw and effort is None:
        errors.append(f"{where}.effort must be one of {sorted(e.value for e in Effort)}, got {raw.get('effort')!r}")

    mandate = raw.get("mandate")
    if "mandate" in raw and (not isinstance(mandate, str) or len(mandate) < 1):
        errors.append(f"{where}.mandate must be a non-empty string")
    if not isinstance(mandate, str):
        mandate = ""

    if model == Model.SONNET and effort == Effort.XHIGH:
        errors.append(f"{where}: sonnet must not exceed effort 'high' (got 'xhigh')")

    return Orchestrator(model=model or Model.OPUS, effort=effort or Effort.XHIGH, mandate=mandate), errors


def parse_node(raw: object, index: int) -> tuple[Optional[Node], list[str]]:
    errors: list[str] = []
    if not isinstance(raw, dict):
        return None, [f"nodes[{index}] must be an object"]

    node_id = raw.get("id")
    label = node_id if isinstance(node_id, str) else f"<nodes[{index}]>"
    where = f"node '{label}'"

    allowed = {
        "id", "name", "description", "agent", "model", "effort", "size", "role", "required",
        "shape", "requires_user_approval", "skills", "inputs", "produces", "gates", "feedback",
    }
    required = {"id", "name", "description", "agent", "model", "effort", "size", "role", "required"}
    errors.extend(_check_unknown_and_missing(raw, allowed, required, where))

    if "id" in raw and (not isinstance(node_id, str) or not SLUG_PATTERN.match(node_id)):
        errors.append(f"{where}: id must match slug pattern ^[a-z0-9]+(-[a-z0-9]+)*$, got {node_id!r}")
    if not isinstance(node_id, str):
        node_id = f"__invalid_node_{index}"

    name = raw.get("name")
    if "name" in raw and (not isinstance(name, str) or len(name) < 1):
        errors.append(f"{where}: name must be a non-empty string")
    elif isinstance(name, str) and _contains_control_chars(name):
        errors.append(f"{where}: name must not contain control characters")
    if not isinstance(name, str):
        name = ""

    description = raw.get("description")
    if "description" in raw and (not isinstance(description, str) or len(description) < 1):
        errors.append(f"{where}: description must be a non-empty string")
    elif isinstance(description, str) and _contains_control_chars(description):
        errors.append(f"{where}: description must not contain control characters")
    if not isinstance(description, str):
        description = ""

    agent_raw = raw.get("agent")
    agent = _enum_or_none(AgentType, agent_raw) if "agent" in raw else None
    if "agent" in raw and agent is None:
        errors.append(f"{where}: agent must be one of {sorted(a.value for a in AgentType)}, got {agent_raw!r}")
    if agent is None:
        agent = AgentType.GENERAL_PURPOSE

    model = _enum_or_none(Model, raw.get("model")) if "model" in raw else None
    if "model" in raw and model is None:
        errors.append(f"{where}: model must be one of {sorted(m.value for m in Model)}, got {raw.get('model')!r}")

    effort = _enum_or_none(Effort, raw.get("effort")) if "effort" in raw else None
    if "effort" in raw and effort is None:
        errors.append(f"{where}: effort must be one of {sorted(e.value for e in Effort)}, got {raw.get('effort')!r}")

    size = _enum_or_none(Size, raw.get("size")) if "size" in raw else None
    if "size" in raw and size is None:
        errors.append(f"{where}: size must be one of {sorted(s.value for s in Size)}, got {raw.get('size')!r}")

    role = _enum_or_none(Role, raw.get("role")) if "role" in raw else None
    if "role" in raw and role is None:
        errors.append(f"{where}: role must be one of {sorted(r.value for r in Role)}, got {raw.get('role')!r}")

    shape: Optional[Shape] = None
    if "shape" in raw:
        shape = _enum_or_none(Shape, raw.get("shape"))
        if shape is None:
            errors.append(f"{where}: shape must be one of {sorted(s.value for s in Shape)}, got {raw.get('shape')!r}")
    if shape is None:
        shape = Shape.BALANCED

    required_flag = raw.get("required")
    if "required" in raw and not isinstance(required_flag, bool):
        errors.append(f"{where}: required must be a boolean")
    if not isinstance(required_flag, bool):
        required_flag = False

    requires_user_approval_raw = raw.get("requires_user_approval", False)
    if "requires_user_approval" in raw and not isinstance(requires_user_approval_raw, bool):
        errors.append(f"{where}: requires_user_approval must be a boolean")
    requires_user_approval = requires_user_approval_raw if isinstance(requires_user_approval_raw, bool) else False

    if model == Model.SONNET and effort == Effort.XHIGH:
        errors.append(f"{where}: sonnet must not exceed effort 'high' (got 'xhigh')")

    skills_raw = raw.get("skills", [])
    skills: list[str] = []
    if not isinstance(skills_raw, list) or not all(isinstance(s, str) for s in skills_raw):
        errors.append(f"{where}: skills must be an array of strings")
    else:
        skills = skills_raw

    inputs_raw = raw.get("inputs", [])
    inputs: list[str] = []
    if not isinstance(inputs_raw, list) or not all(isinstance(s, str) for s in inputs_raw):
        errors.append(f"{where}: inputs must be an array of strings")
    else:
        inputs = inputs_raw

    produces_raw = raw.get("produces")
    produces: Optional[str] = None
    if produces_raw is not None:
        if not isinstance(produces_raw, str):
            errors.append(f"{where}: produces must be a string")
        else:
            produces = produces_raw

    gates_raw = raw.get("gates")
    gates: Optional[str] = None
    if gates_raw is not None:
        if gates_raw != "user_response":
            errors.append(f"{where}: gates must be 'user_response' or null, got {gates_raw!r}")
        else:
            gates = gates_raw

    feedback: Optional[Feedback] = None
    feedback_raw = raw.get("feedback")
    if feedback_raw is not None:
        feedback, fb_errors = parse_feedback(feedback_raw, label)
        errors.extend(fb_errors)

    node = Node(
        id=node_id,
        name=name,
        description=description,
        agent=agent,
        model=model or Model.OPUS,
        effort=effort or Effort.LOW,
        size=size or Size.SMALL,
        role=role or Role.RESEARCH,
        required=required_flag,
        shape=shape,
        requires_user_approval=requires_user_approval,
        skills=skills,
        inputs=inputs,
        produces=produces,
        gates=gates,
        feedback=feedback,
    )
    return node, errors


def parse_plan(raw: object, source_path: Path) -> tuple[Optional[Plan], list[str]]:
    """Parse and field-validate a raw JSON plan document.

    Always returns a best-effort ``Plan`` (using safe fallback values for any
    malformed field) alongside every error found, so callers can run further
    structural checks (DAG, cross-references) even on a broken plan and report
    everything in one pass. Returns ``(None, [errors])`` only when ``raw``
    isn't even a JSON object.
    """
    errors: list[str] = []
    if not isinstance(raw, dict):
        return None, ["plan must be a JSON object"]

    allowed = {"id", "title", "description", "when_to_use", "baseline_size", "requires", "orchestrator", "nodes"}
    required = {"id", "title", "description", "when_to_use", "baseline_size", "orchestrator", "nodes"}
    errors.extend(_check_unknown_and_missing(raw, allowed, required, "plan"))

    plan_id = raw.get("id")
    if "id" in raw and (not isinstance(plan_id, str) or not SLUG_PATTERN.match(plan_id)):
        errors.append(f"plan: id must match slug pattern ^[a-z0-9]+(-[a-z0-9]+)*$, got {plan_id!r}")
    expected_stem = source_path.stem
    if isinstance(plan_id, str) and plan_id != expected_stem:
        errors.append(f"plan: id '{plan_id}' does not match filename stem '{expected_stem}' ({source_path.name})")
    if not isinstance(plan_id, str):
        plan_id = expected_stem

    title = raw.get("title")
    if "title" in raw and (not isinstance(title, str) or not (1 <= len(title) <= 60)):
        errors.append(f"plan: title must be a string of length 1..60, got {title!r}")
    if not isinstance(title, str):
        title = ""

    description = raw.get("description")
    if "description" in raw and (not isinstance(description, str) or len(description) < 1):
        errors.append("plan: description must be a non-empty string")
    if not isinstance(description, str):
        description = ""

    when_to_use = raw.get("when_to_use")
    if "when_to_use" in raw and (not isinstance(when_to_use, str) or len(when_to_use) < 1):
        errors.append("plan: when_to_use must be a non-empty string")
    if not isinstance(when_to_use, str):
        when_to_use = ""

    baseline_size_raw = raw.get("baseline_size")
    valid_baseline = (
        isinstance(baseline_size_raw, (int, float))
        and not isinstance(baseline_size_raw, bool)
        and baseline_size_raw > 0
    )
    if "baseline_size" in raw and not valid_baseline:
        errors.append(f"plan: baseline_size must be a number > 0, got {baseline_size_raw!r}")
    baseline_size = float(baseline_size_raw) if valid_baseline else 1.0

    requires: Optional[Requires] = None
    if "requires" in raw:
        requires, req_errors = parse_requires(raw.get("requires"))
        errors.extend(req_errors)

    orchestrator, orch_errors = (
        parse_orchestrator(raw.get("orchestrator"))
        if "orchestrator" in raw
        else (Orchestrator(model=Model.OPUS, effort=Effort.XHIGH, mandate=""), [])
    )
    errors.extend(orch_errors)

    nodes_raw = raw.get("nodes")
    nodes: list[Node] = []
    if "nodes" in raw:
        if not isinstance(nodes_raw, list) or len(nodes_raw) < 1:
            errors.append("plan: nodes must be a non-empty array")
        else:
            for i, n in enumerate(nodes_raw):
                node, node_errors = parse_node(n, i)
                errors.extend(node_errors)
                if node is not None:
                    nodes.append(node)

    plan = Plan(
        id=plan_id,
        title=title,
        description=description,
        when_to_use=when_to_use,
        baseline_size=baseline_size,
        orchestrator=orchestrator,
        nodes=nodes,
        requires=requires,
    )
    return plan, errors


def find_cycles(nodes: list[Node]) -> list[list[str]]:
    """Detect cycles in the ``inputs`` dependency graph.

    Edges run input -> node (the input must complete before the node), which
    is the direction the DAG must respect. Returns each distinct cycle found
    as the ordered list of node ids forming it (first id repeated at the end).
    """
    id_set = {n.id for n in nodes}
    graph: dict[str, list[str]] = {n.id: [] for n in nodes}
    for n in nodes:
        for inp in n.inputs:
            if inp in id_set:
                graph[inp].append(n.id)

    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = {nid: WHITE for nid in graph}
    cycles: list[list[str]] = []
    reported: set[frozenset] = set()
    path: list[str] = []

    def dfs(u: str) -> None:
        color[u] = GRAY
        path.append(u)
        for v in graph[u]:
            if color[v] == GRAY:
                idx = path.index(v)
                cycle = path[idx:] + [v]
                key = frozenset(cycle)
                if key not in reported:
                    reported.add(key)
                    cycles.append(cycle)
            elif color[v] == WHITE:
                dfs(v)
        path.pop()
        color[u] = BLACK

    for nid in list(graph):
        if color[nid] == WHITE:
            dfs(nid)

    return cycles


def validate_semantics(plan: Plan) -> list[str]:
    """Structural checks that need the full node list: uniqueness, references,
    the inputs DAG, and the evaluator-gate guarantee."""
    errors: list[str] = []

    ids = [n.id for n in plan.nodes]
    seen: set[str] = set()
    dupes: set[str] = set()
    for i in ids:
        if i in seen:
            dupes.add(i)
        seen.add(i)
    for d in sorted(dupes):
        errors.append(f"duplicate node id '{d}'")

    id_set = set(ids)

    for n in plan.nodes:
        for inp in n.inputs:
            if inp not in id_set:
                errors.append(f"node '{n.id}': inputs references unknown node '{inp}'")

    for cycle in find_cycles(plan.nodes):
        errors.append(f"cycle detected in inputs: {' -> '.join(cycle)}")

    for n in plan.nodes:
        if n.feedback is not None and n.feedback.to not in id_set:
            errors.append(f"node '{n.id}': feedback.to references unknown node '{n.feedback.to}'")

    for n in plan.nodes:
        if n.gates == "user_response" and not n.required:
            errors.append(
                f"node '{n.id}': gates == 'user_response' but required is false; an optional gate is not a gate"
            )

    # An orchestrator node IS the session, so it cannot run on some other model.
    # Left unchecked, relabeling one to a cheaper model prices it at that rate and
    # understates the plan while the work is unchanged, the same failure mode as
    # branching the cost model on a node's role.
    for n in plan.nodes:
        if n.agent != AgentType.ORCHESTRATOR:
            continue
        if n.model != plan.orchestrator.model or n.effort != plan.orchestrator.effort:
            errors.append(
                f"node '{n.id}': agent is 'orchestrator' but declares "
                f"{n.model.value}/{n.effort.value} while the orchestrator runs "
                f"{plan.orchestrator.model.value}/{plan.orchestrator.effort.value}; an orchestrator "
                f"node is the session itself and cannot run on a different model"
            )

    has_required_gate_evaluator = any(
        n.gates == "user_response" and n.role == Role.EVALUATE and n.required for n in plan.nodes
    )
    if not has_required_gate_evaluator:
        errors.append(
            "no required node has gates == 'user_response' AND role == 'evaluate': this plan has no evaluator "
            "gating the user response, which is the structural guarantee this tool exists to provide"
        )

    return errors


def check_requires_availability(plan: Plan, claude_dir: Path) -> list[str]:
    """Soft check for `requires`: warn, never fail, when a named agent or
    skill isn't present in the active .claude/, so a plan carried into
    another repo degrades legibly instead of breaking mid-run."""
    warnings: list[str] = []
    if plan.requires is None:
        return warnings

    agents_dir = claude_dir / "agents"
    skills_dir = claude_dir / "skills"

    for agent_name in plan.requires.agents:
        if agent_name in BUILTIN_AGENT_KINDS:
            continue
        if not (agents_dir / f"{agent_name}.md").exists():
            warnings.append(f"requires.agents: '{agent_name}' not found under {agents_dir}")

    for skill_name in plan.requires.skills:
        if not (skills_dir / skill_name).is_dir() and not (skills_dir / f"{skill_name}.md").exists():
            warnings.append(f"requires.skills: '{skill_name}' not found under {skills_dir}")

    return warnings


def load_plan_file(path: Path) -> tuple[Optional[Plan], list[str]]:
    """Read, parse, and fully validate (field + structural) a plan file."""
    try:
        text = path.read_text()
    except OSError as e:
        return None, [f"{path.name}: could not read file: {e}"]
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as e:
        return None, [f"{path.name}: invalid JSON: {e}"]
    plan, errors = parse_plan(raw, path)
    if plan is not None:
        errors.extend(validate_semantics(plan))
    return plan, [f"{path.name}: {e}" for e in errors]


# =============================================================================
# Mermaid rendering -- generated purely from parsed Plan data.
# =============================================================================


def _mermaid_id(node_id: str) -> str:
    return "n_" + node_id.replace("-", "_")


_WHITESPACE_RUN_PATTERN = re.compile(r"\s+")
_STRAY_CONTROL_CHAR_PATTERN = re.compile(r"[\x00-\x08\x0e-\x1f\x7f]")


def _mermaid_escape(text: str) -> str:
    """Make ``text`` safe to embed as a single mermaid statement.

    A field only has to pass ``len >= 1`` validation to reach here, so a
    newline (or any other control character) in e.g. a node ``name`` would
    otherwise split the generated flowchart statement across lines and
    produce invalid mermaid syntax. Whitespace runs (including \\n, \\r, \\t)
    collapse to a single space; other control characters are dropped outright.
    """
    text = _WHITESPACE_RUN_PATTERN.sub(" ", text)
    text = _STRAY_CONTROL_CHAR_PATTERN.sub("", text)
    text = text.replace('"', "'")
    return text.strip()


_ROLE_CLASSDEFS = [
    "    classDef research fill:#7fb3d9,stroke:#2c5a7a,color:#12202b;",
    "    classDef plan fill:#b3a2d9,stroke:#5a4a7a,color:#1c1626;",
    "    classDef implement fill:#8fc9a0,stroke:#3a6b47,color:#12271a;",
    "    classDef evaluate fill:#e8b06a,stroke:#8a5a1f,color:#2b1c08;",
    "    classDef synthesize fill:#7fd1c9,stroke:#2c6e66,color:#0f2624;",
    "    classDef orchestrator fill:#a9adb6,stroke:#3d4048,color:#1a1b1e,stroke-width:3px;",
    "    classDef optional stroke-dasharray: 5 5;",
]


def _node_base_classes(n: Node) -> list[str]:
    classes = [n.role.value]
    if n.agent == AgentType.ORCHESTRATOR:
        classes.append("orchestrator")
    if not n.required:
        classes.append("optional")
    return classes


def _node_label(n: Node) -> str:
    label = f"{n.name}<br/>{n.agent.value} · {n.model.value} · {n.effort.value}"
    if not n.required:
        label += "<br/>(optional)"
    return label


def generate_mermaid(plan: Plan) -> str:
    id_set = {n.id for n in plan.nodes}
    lines: list[str] = ["flowchart TD"]
    lines.append('    TASK(["Task"])')
    lines.append('    ANSWER(["Answer to user"])')

    for n in plan.nodes:
        label = _mermaid_escape(_node_label(n))
        lines.append(f'    {_mermaid_id(n.id)}["{label}"]')

    for n in plan.nodes:
        nid = _mermaid_id(n.id)
        if not n.inputs:
            lines.append(f"    TASK --> {nid}")
        for inp in n.inputs:
            if inp in id_set:
                lines.append(f"    {_mermaid_id(inp)} --> {nid}")

    for n in plan.nodes:
        if n.gates == "user_response":
            lines.append(f"    {_mermaid_id(n.id)} ==> ANSWER")

    for n in plan.nodes:
        if n.feedback is not None and n.feedback.to in id_set:
            label = _mermaid_escape(f"{n.feedback.when} · max {n.feedback.max_iterations}")
            lines.append(f'    {_mermaid_id(n.id)} -.->|"{label}"| {_mermaid_id(n.feedback.to)}')

    lines.append("")
    lines.extend(_ROLE_CLASSDEFS)

    for n in plan.nodes:
        nid = _mermaid_id(n.id)
        classes = _node_base_classes(n)
        lines.append(f"    class {nid} {','.join(classes)};")

    return "\n".join(lines)


def generate_receipt_mermaid(plan: Plan, ledger: dict) -> str:
    """Regenerate the diagram from the ledger: what actually happened, not
    what was planned. Completed nodes are styled distinctly, waived required
    nodes in red/bold, pending ones faded."""
    id_set = {n.id for n in plan.nodes}
    completed: dict = ledger.get("completed", {})
    waived: dict = ledger.get("waived", {})

    def status_of(n: Node) -> str:
        if n.id in completed:
            return "complete"
        if n.id in waived:
            return "waived"
        return "pending"

    lines: list[str] = ["flowchart TD"]
    lines.append('    TASK(["Task"])')
    lines.append('    ANSWER(["Answer to user"])')

    for n in plan.nodes:
        status = status_of(n)
        label = _node_label(n)
        label += {"complete": "<br/>[complete]", "waived": "<br/>[WAIVED]", "pending": "<br/>[pending]"}[status]
        lines.append(f'    {_mermaid_id(n.id)}["{_mermaid_escape(label)}"]')

    for n in plan.nodes:
        nid = _mermaid_id(n.id)
        if not n.inputs:
            lines.append(f"    TASK --> {nid}")
        for inp in n.inputs:
            if inp in id_set:
                lines.append(f"    {_mermaid_id(inp)} --> {nid}")

    for n in plan.nodes:
        if n.gates == "user_response":
            lines.append(f"    {_mermaid_id(n.id)} ==> ANSWER")

    for n in plan.nodes:
        if n.feedback is not None and n.feedback.to in id_set:
            label = _mermaid_escape(f"{n.feedback.when} · max {n.feedback.max_iterations}")
            lines.append(f'    {_mermaid_id(n.id)} -.->|"{label}"| {_mermaid_id(n.feedback.to)}')

    lines.append("")
    lines.extend(_ROLE_CLASSDEFS)
    lines.append("    classDef statusComplete stroke-width:4px;")
    lines.append("    classDef statusWaivedRequired fill:#c0392b,stroke:#5c1a10,color:#ffffff,stroke-width:4px;")
    lines.append("    classDef statusWaivedOptional fill:#e0a199,stroke:#5c1a10,color:#3a0d08,stroke-dasharray: 5 5;")
    lines.append("    classDef statusPending opacity:0.4;")

    for n in plan.nodes:
        nid = _mermaid_id(n.id)
        classes = _node_base_classes(n)
        status = status_of(n)
        if status == "complete":
            classes.append("statusComplete")
        elif status == "waived":
            classes.append("statusWaivedRequired" if n.required else "statusWaivedOptional")
        else:
            classes.append("statusPending")
        lines.append(f"    class {nid} {','.join(classes)};")

    return "\n".join(lines)


# =============================================================================
# Cost model
# =============================================================================


def _work(units: float, shape: Shape, model_w: float, effort_m: float) -> float:
    r, w = SHAPE_SPLIT[shape.value]
    return model_w * (units * r + OUTPUT_WEIGHT * units * w * effort_m)


def node_cost(n: Node) -> float:
    return _work(SIZE_UNITS[n.size.value], n.shape, MODEL_WEIGHT[n.model.value], EFFORT_MULTIPLIER[n.effort.value])


def handoff_cost(n: Node, orchestrator: Orchestrator) -> float:
    if n.agent == AgentType.ORCHESTRATOR:
        return 0.0
    return (
        PREFIX_UNITS[n.agent.value] * MODEL_WEIGHT[n.model.value]
        + RETURN_UNITS[n.size.value] * MODEL_WEIGHT[orchestrator.model.value]
    )


def baseline_declared_cost(plan: Plan) -> float:
    orch = plan.orchestrator
    return _work(plan.baseline_size, Shape.BALANCED, MODEL_WEIGHT[orch.model.value], EFFORT_MULTIPLIER[orch.effort.value])


def baseline_derived_cost(plan: Plan) -> float:
    orch = plan.orchestrator
    return sum(
        _work(SIZE_UNITS[n.size.value], n.shape, MODEL_WEIGHT[orch.model.value], EFFORT_MULTIPLIER[orch.effort.value])
        for n in plan.nodes
        if n.required
    )


@dataclass
class CostReport:
    rows: list[tuple[str, str, str, str, str, str, str, float, str]]
    role_breakdown: dict[str, float]
    baseline_declared: float
    baseline_derived: float
    total: float
    optional_add: float
    feedback_expected: float
    feedback_ceiling: float
    decomposed_size: float
    declared_size: float


def compute_cost_report(plan: Plan) -> CostReport:
    orch = plan.orchestrator

    def cost(n: Node) -> float:
        return node_cost(n) + handoff_cost(n, orch)

    required_nodes = [n for n in plan.nodes if n.required]
    optional_nodes = [n for n in plan.nodes if not n.required]

    baseline_declared = baseline_declared_cost(plan)
    baseline_derived = baseline_derived_cost(plan)
    total = sum(cost(n) for n in required_nodes)
    optional_add = sum(cost(n) for n in optional_nodes)

    node_by_id = {n.id: n for n in plan.nodes}
    feedback_expected = 0.0
    feedback_ceiling = 0.0
    for n in plan.nodes:
        if n.feedback is None:
            continue
        to_node = node_by_id.get(n.feedback.to)
        if to_node is None:
            continue
        iter_cost = LOOP_ITER_FRACTION * (node_cost(to_node) + node_cost(n)) + handoff_cost(to_node, orch) + handoff_cost(n, orch)
        max_it = n.feedback.max_iterations
        feedback_expected += sum(LOOP_PROBABILITY[i] * iter_cost for i in range(max_it))
        feedback_ceiling += max_it * iter_cost

    role_breakdown: dict[str, float] = {}
    for n in plan.nodes:
        role_breakdown[n.role.value] = role_breakdown.get(n.role.value, 0.0) + cost(n)

    rows = [
        (n.id, n.role.value, n.agent.value, n.model.value, n.effort.value, n.size.value, n.shape.value, cost(n),
         "required" if n.required else "optional")
        for n in plan.nodes
    ]

    return CostReport(
        rows=rows,
        role_breakdown=role_breakdown,
        baseline_declared=baseline_declared,
        baseline_derived=baseline_derived,
        total=total,
        optional_add=optional_add,
        feedback_expected=feedback_expected,
        feedback_ceiling=feedback_ceiling,
        decomposed_size=sum(SIZE_UNITS[n.size.value] for n in required_nodes),
        declared_size=plan.baseline_size,
    )


def format_table(headers: list[str], rows: list[list[str]]) -> str:
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))
    lines = ["  ".join(h.ljust(widths[i]) for i, h in enumerate(headers))]
    lines.append("  ".join("-" * widths[i] for i in range(len(headers))))
    for row in rows:
        lines.append("  ".join(cell.ljust(widths[i]) for i, cell in enumerate(row)))
    return "\n".join(lines)


def render_cost_report(plan: Plan) -> str:
    r = compute_cost_report(plan)
    headers = ["id", "role", "agent", "model", "effort", "size", "shape", "cost", "status"]
    rows = [
        [x[0], x[1], x[2], x[3], x[4], x[5], x[6], f"{x[7]:.1f}", x[8]]
        for x in r.rows
    ]
    table = format_table(headers, rows)
    role_lines = [f"  {role}: {cost:.1f}" for role, cost in sorted(r.role_breakdown.items())]

    lines: list[str] = []
    lines.append(
        "Cost report -- 'cost' is in relative points, not tokens or dollars, for comparison only."
    )
    lines.append("")
    lines.append(table)
    lines.append("")
    lines.append("Spend by role (colouring/breakdown only -- role never affects the totals below):")
    lines.extend(role_lines)
    lines.append("")
    summary_rows = [
        ["baseline_declared", f"author's honest all-Opus estimate, baseline_size={plan.baseline_size:.0f}",
         f"{r.baseline_declared:.1f}"],
        ["baseline_derived", "this node list done by the orchestrator alone, no delegation",
         f"{r.baseline_derived:.1f}"],
        ["total", "sum of required node cost + handoff, as delegated", f"{r.total:.1f}"],
        ["optional_add", "optional nodes, if the orchestrator runs them", f"{r.optional_add:.1f}"],
        ["feedback_expected", "probability-weighted rework across all feedback edges",
         f"{r.feedback_expected:.1f}"],
        ["feedback_ceiling", "worst case: every feedback edge exhausts max_iterations",
         f"{r.feedback_ceiling:.1f}"],
    ]
    lines.append(format_table(["metric", "meaning", "value"], summary_rows))
    lines.append("")

    if r.decomposed_size > r.declared_size * DECOMPOSITION_FLAG_THRESHOLD:
        lines.append(
            f"DECOMPOSITION FLAG: this plan splits the work more finely than a single agent would "
            f"(required node sizes total {r.decomposed_size:.0f} vs a declared baseline_size of "
            f"{r.declared_size:.0f})"
        )
        lines.append("")

    pct_declared = (r.total - r.baseline_declared) / r.baseline_declared * 100 if r.baseline_declared else 0.0
    pct_derived = (r.total - r.baseline_derived) / r.baseline_derived * 100 if r.baseline_derived else 0.0

    lines.append(f"total vs baseline_declared: {pct_declared:+.1f}%")
    if r.total < r.baseline_declared:
        lines.append(f"COST PASS — delegation is {-pct_declared:.1f}% cheaper than the declared all-Opus baseline")
    else:
        lines.append(
            f"COST FAIL — delegation is {pct_declared:.1f}% more expensive than the declared all-Opus baseline"
        )
        lines.append("this plan costs more than an all-Opus session; it must be justified by quality, not cost")

    lines.append(
        f"total vs baseline_derived (secondary: what one agent would spend on this SAME, more finely "
        f"decomposed, node list): {pct_derived:+.1f}%"
    )
    lines.append("")
    lines.append(
        "Caveat: this estimate ignores prompt caching in both directions -- orchestrator-inline work is "
        "cache-favoured (roughly 10-15% off the baseline), while delegation keeps the orchestrator's context "
        "window small, which pays off on later turns. Verdicts within ±15% of baseline are too close to call."
    )
    if abs(pct_declared) < TOO_CLOSE_TO_CALL_PCT:
        lines.append(
            f"NOTE: this plan's {pct_declared:+.1f}% margin is inside that ±15% band -- "
            "treat the verdict above as inconclusive."
        )

    return "\n".join(lines)


# =============================================================================
# `show` rendering
# =============================================================================


def render_header(plan: Plan) -> str:
    lines = [
        plan.title,
        "",
        plan.description,
        "",
        f"When to use: {plan.when_to_use}",
        "",
        f"Orchestrator: {plan.orchestrator.model.value} · {plan.orchestrator.effort.value}",
        f"Mandate: {plan.orchestrator.mandate}",
    ]
    return "\n".join(lines)


def render_mermaid_block(plan: Plan) -> str:
    return "```mermaid\n" + generate_mermaid(plan) + "\n```"


# =============================================================================
# Ledger (state dir, see default_state_dir())
# =============================================================================


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")


def load_ledger(run_id: str, runs_dir: Path) -> tuple[Optional[dict], Path, Optional[str]]:
    """Load a run ledger by id.

    Returns ``(ledger, path, error)``. ``ledger`` is None whenever ``error``
    is set; ``path`` is best-effort (for messages) even then. Defends against
    path traversal (a `run_id` containing `..` or an absolute-looking value,
    which pathlib's `/` operator would otherwise honor by discarding
    `runs_dir` entirely) and against corrupt/truncated ledger JSON, which
    must report a clean error rather than a raw traceback.
    """
    fallback_path = runs_dir / f"{run_id}.json"

    if ".." in run_id or not RUN_ID_PATTERN.match(run_id):
        return None, fallback_path, f"invalid run_id {run_id!r}: must match {RUN_ID_PATTERN.pattern} and not contain '..'"

    runs_dir_resolved = runs_dir.resolve()
    candidate = (runs_dir / f"{run_id}.json").resolve()
    try:
        candidate.relative_to(runs_dir_resolved)
    except ValueError:
        return None, fallback_path, f"invalid run_id {run_id!r}: resolves outside the runs directory"

    if not candidate.exists():
        return None, candidate, f"no such run '{run_id}' in {runs_dir}"

    try:
        ledger = json.loads(candidate.read_text())
    except json.JSONDecodeError as e:
        return None, candidate, f"run '{run_id}' has a corrupt ledger file ({candidate}): {e}"
    except OSError as e:
        return None, candidate, f"could not read run '{run_id}' ledger ({candidate}): {e}"

    if not isinstance(ledger, dict) or "completed" not in ledger or "waived" not in ledger:
        return None, candidate, f"run '{run_id}' ledger ({candidate}) is missing expected fields"

    return ledger, candidate, None


def save_ledger(ledger: dict, path: Path) -> None:
    path.write_text(json.dumps(ledger, indent=2) + "\n")


def load_plan_for_ledger(ledger: dict, plans_dir: Path) -> Optional[Plan]:
    """Load the plan a run's ledger refers to. Prefers the exact file path
    recorded at `start` time (so a one-off --plan-file plan keeps working),
    falling back to the usual plans_dir/<plan_id>.json lookup."""
    candidates: list[Path] = []
    plan_path_str = ledger.get("plan_path")
    if plan_path_str:
        candidates.append(Path(plan_path_str))
    candidates.append(plans_dir / f"{ledger['plan_id']}.json")

    for path in candidates:
        if path.exists():
            try:
                raw = json.loads(path.read_text())
            except json.JSONDecodeError:
                continue
            plan, _errors = parse_plan(raw, path)
            return plan
    return None


def resolve_plan_path(plan_id: Optional[str], plan_file: Optional[Path], plans_dir: Path) -> Optional[Path]:
    if plan_file is not None:
        return plan_file
    if plan_id is not None:
        return plans_dir / f"{plan_id}.json"
    return None


# =============================================================================
# Commands
# =============================================================================


def cmd_list(plans_dir: Path) -> int:
    rows: list[list[str]] = []
    for path in sorted(plans_dir.glob("*.json")):
        try:
            raw = json.loads(path.read_text())
        except json.JSONDecodeError as e:
            print(f"warning: skipping {path.name}: invalid JSON: {e}", file=sys.stderr)
            continue
        plan, _errors = parse_plan(raw, path)
        if plan is None:
            print(f"warning: skipping {path.name}: not a JSON object", file=sys.stderr)
            continue
        rows.append([plan.id, plan.title, plan.when_to_use])

    if not rows:
        print("no plans found")
        return 0

    print(format_table(["id", "title", "when_to_use"], rows))
    return 0


def cmd_validate(plan_id: Optional[str], validate_all: bool, plans_dir: Path, claude_dir: Path) -> int:
    if validate_all:
        paths = sorted(plans_dir.glob("*.json"))
        if not paths:
            print(f"no plans found in {plans_dir}")
            return 0
    else:
        if not plan_id:
            print("error: must specify a plan_id or --all", file=sys.stderr)
            return 1
        path = plans_dir / f"{plan_id}.json"
        if not path.exists():
            print(f"error: no such plan '{plan_id}' in {plans_dir}", file=sys.stderr)
            return 1
        paths = [path]

    all_errors: list[str] = []
    all_warnings: list[str] = []
    for path in paths:
        plan, errors = load_plan_file(path)
        warnings = check_requires_availability(plan, claude_dir) if plan is not None else []
        all_errors.extend(errors)
        all_warnings.extend(warnings)
        status = "OK" if not errors else f"{len(errors)} error(s)"
        if warnings:
            status += f", {len(warnings)} warning(s)"
        print(f"{path.stem}: {status}")

    if all_warnings:
        print()
        print("Warnings (non-fatal):")
        for w in all_warnings:
            print(f"  - {w}")

    if all_errors:
        print()
        print("Errors:")
        for e in all_errors:
            print(f"  - {e}")
        return 1
    return 0


def cmd_show(
    plan_id: Optional[str],
    plan_file: Optional[Path],
    plans_dir: Path,
    mermaid_only: bool,
    cost_only: bool,
    out: Optional[Path],
) -> int:
    if mermaid_only and cost_only:
        print("error: --mermaid-only and --cost-only are mutually exclusive", file=sys.stderr)
        return 1

    path = resolve_plan_path(plan_id, plan_file, plans_dir)
    if path is None:
        print("error: must specify a plan_id or --plan-file", file=sys.stderr)
        return 1
    if not path.exists():
        print(f"error: no such plan file '{path}'", file=sys.stderr)
        return 1

    plan, errors = load_plan_file(path)
    if plan is None:
        print(f"error: could not parse plan at '{path}':", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1
    if errors:
        print(f"warning: plan at '{path}' has validation errors:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)

    if mermaid_only:
        output = render_mermaid_block(plan)
    elif cost_only:
        output = render_cost_report(plan)
    else:
        output = "\n\n".join([render_header(plan), render_mermaid_block(plan), render_cost_report(plan)])

    if out is not None:
        out.write_text(output + "\n")
        print(f"wrote {out}")
    else:
        print(output)
    return 0


def cmd_start(
    plan_id: Optional[str], plan_file: Optional[Path], task: str, plans_dir: Path, runs_dir: Path
) -> int:
    path = resolve_plan_path(plan_id, plan_file, plans_dir)
    if path is None:
        print("error: must specify a plan_id or --plan-file", file=sys.stderr)
        return 1
    if not path.exists():
        print(f"error: no such plan file '{path}'", file=sys.stderr)
        return 1

    plan, errors = load_plan_file(path)
    if plan is None or errors:
        print(f"error: plan at '{path}' is invalid; fix it before starting a run:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    started_at = datetime.now(timezone.utc)
    run_id = f"{started_at.strftime('%Y%m%d-%H%M%S')}-{plan.id}"
    runs_dir.mkdir(parents=True, exist_ok=True)
    ledger_path = runs_dir / f"{run_id}.json"
    ledger = {
        "run_id": run_id,
        "plan_id": plan.id,
        "plan_path": str(path.resolve()),
        "task": task,
        "started_at": started_at.isoformat(),
        "completed": {},
        "waived": {},
    }
    save_ledger(ledger, ledger_path)
    print(run_id)
    return 0


def cmd_complete(
    run_id: str, node_id: str, note: Optional[str], approved_by_user: bool, plans_dir: Path, runs_dir: Path
) -> int:
    ledger, path, error = load_ledger(run_id, runs_dir)
    if error is not None:
        print(f"error: {error}", file=sys.stderr)
        return 1
    assert ledger is not None

    plan = load_plan_for_ledger(ledger, plans_dir)
    if plan is None:
        print(f"error: plan '{ledger['plan_id']}' referenced by run '{run_id}' could not be loaded", file=sys.stderr)
        return 1

    node = next((n for n in plan.nodes if n.id == node_id), None)
    if node is None:
        print(f"error: node '{node_id}' is not part of plan '{plan.id}'", file=sys.stderr)
        return 1

    unmet = [inp for inp in node.inputs if inp not in ledger["completed"] and inp not in ledger["waived"]]
    if unmet:
        print(f"error: node '{node_id}' has unmet dependencies: {', '.join(unmet)}", file=sys.stderr)
        return 1

    if node.requires_user_approval and not approved_by_user:
        print(
            f"error: node '{node_id}' requires_user_approval; rerun with --approved-by-user once the "
            "user has actually approved its output",
            file=sys.stderr,
        )
        return 1

    entry = {"at": _now_iso(), "note": note or ""}
    if node.requires_user_approval:
        entry["approved_by_user"] = True
    ledger["completed"][node_id] = entry
    save_ledger(ledger, path)
    print(f"completed '{node_id}' in run '{run_id}'")
    return 0


def cmd_skip(
    run_id: str, node_id: str, reason: str, approved_by_user: bool, plans_dir: Path, runs_dir: Path
) -> int:
    ledger, path, error = load_ledger(run_id, runs_dir)
    if error is not None:
        print(f"error: {error}", file=sys.stderr)
        return 1
    assert ledger is not None

    plan = load_plan_for_ledger(ledger, plans_dir)
    if plan is None:
        print(f"error: plan '{ledger['plan_id']}' referenced by run '{run_id}' could not be loaded", file=sys.stderr)
        return 1

    node = next((n for n in plan.nodes if n.id == node_id), None)
    if node is None:
        print(f"error: node '{node_id}' is not part of plan '{plan.id}'", file=sys.stderr)
        return 1

    # A waived node satisfies downstream `inputs` exactly like a completed
    # one (see cmd_complete's unmet-dependency check), so waiving an approval
    # barrier is still a side door unless it too requires explicit consent.
    if node.requires_user_approval and not approved_by_user:
        print(
            f"error: node '{node_id}' requires_user_approval; waiving it still requires --approved-by-user, "
            "so bypassing the barrier is an explicit user act, not a side effect of --reason",
            file=sys.stderr,
        )
        return 1

    if node.required:
        print(
            f"WARNING: '{node_id}' is a REQUIRED node. Waiving it requires explicit user consent. "
            f"Recording reason: {reason}"
        )

    entry = {"at": _now_iso(), "reason": reason}
    if node.requires_user_approval:
        entry["approved_by_user"] = True
    ledger["waived"][node_id] = entry
    save_ledger(ledger, path)
    print(f"waived '{node_id}' in run '{run_id}': {reason}")
    return 0


def cmd_check(run_id: str, plans_dir: Path, runs_dir: Path) -> int:
    ledger, _path, error = load_ledger(run_id, runs_dir)
    if error is not None:
        print(f"error: {error}", file=sys.stderr)
        return 1
    assert ledger is not None

    plan = load_plan_for_ledger(ledger, plans_dir)
    if plan is None:
        print(f"error: plan '{ledger['plan_id']}' referenced by run '{run_id}' could not be loaded", file=sys.stderr)
        return 1

    completed: dict = ledger["completed"]
    waived: dict = ledger["waived"]

    outstanding_required = [
        n.id for n in plan.nodes if n.required and n.id not in completed and n.id not in waived
    ]

    print(f"Run '{run_id}' -- plan '{plan.id}'")
    print()
    if outstanding_required:
        print(f"Outstanding required node(s) ({len(outstanding_required)}):")
        for nid in outstanding_required:
            print(f"  - {nid}")
    else:
        print("All required nodes are completed or explicitly waived.")
    print()

    gate_nodes = [n for n in plan.nodes if n.gates == "user_response"]
    incomplete_gates = [n for n in gate_nodes if n.id not in completed]
    waived_gates = [n for n in incomplete_gates if n.id in waived]
    truly_outstanding_gates = [n for n in incomplete_gates if n.id not in waived]

    print("User-response gate nodes:")
    if waived_gates:
        print("  Consent-recorded exceptions (waived, not completed):")
        for n in waived_gates:
            print(f"    - {n.id}: {waived[n.id]['reason']}")
    if truly_outstanding_gates:
        print("  Outstanding (neither completed nor waived):")
        for n in truly_outstanding_gates:
            print(f"    - {n.id}")
    if not incomplete_gates:
        print("  All gate nodes are completed.")
    print()

    # Defence in depth: a gate node that is neither completed nor waived
    # fails the check even if it somehow isn't marked `required` (e.g. an
    # older ledger from before that became a validation error). A waived
    # gate node is the consent path and does not fail the check on its own.
    outstanding_ids = set(outstanding_required) | {n.id for n in truly_outstanding_gates}
    if outstanding_ids:
        print(f"GATE FAIL: {len(outstanding_ids)} required node(s) outstanding")
        return 1
    print("GATE PASS")
    return 0


def cmd_receipt(run_id: str, plans_dir: Path, runs_dir: Path) -> int:
    ledger, _path, error = load_ledger(run_id, runs_dir)
    if error is not None:
        print(f"error: {error}", file=sys.stderr)
        return 1
    assert ledger is not None

    plan = load_plan_for_ledger(ledger, plans_dir)
    if plan is None:
        print(f"error: plan '{ledger['plan_id']}' referenced by run '{run_id}' could not be loaded", file=sys.stderr)
        return 1

    print(f"Receipt for run '{run_id}' -- plan '{plan.id}'")
    print(f"Task: {ledger.get('task', '')}")
    print()
    print("```mermaid")
    print(generate_receipt_mermaid(plan, ledger))
    print("```")
    return 0


# =============================================================================
# CLI wiring
# =============================================================================


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="orchestrate.py",
        description="Developer CLI for orchestration plans (see .claude/orchestration/schema.json).",
    )
    parser.add_argument(
        "--plans-dir", type=Path, default=None,
        help="Override the plans directory (default: plans/ next to this script). Mainly for tests.",
    )
    parser.add_argument(
        "--runs-dir", type=Path, default=None,
        help="Override the runs (ledger) directory (default: the OS state dir). Mainly for tests.",
    )
    parser.add_argument(
        "--claude-dir", type=Path, default=None,
        help="Override the active .claude/ directory used for the `requires` availability check. Mainly for tests.",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="List every plan in plans/.")

    p_validate = sub.add_parser("validate", help="Validate one plan or every plan.")
    p_validate.add_argument("plan_id", nargs="?", default=None, help="Plan id to validate.")
    p_validate.add_argument("--all", action="store_true", help="Validate every plan in plans/.")

    p_show = sub.add_parser("show", help="Show a plan's summary, mermaid diagram, and cost report.")
    p_show.add_argument("plan_id", nargs="?", default=None)
    p_show.add_argument("--plan-file", type=Path, default=None, help="Show a one-off plan living outside plans/.")
    p_show.add_argument("--mermaid-only", action="store_true")
    p_show.add_argument("--cost-only", action="store_true")
    p_show.add_argument("--out", type=Path, default=None, help="Write the output to a file instead of stdout.")

    p_start = sub.add_parser("start", help="Start a new run for a plan.")
    p_start.add_argument("plan_id", nargs="?", default=None)
    p_start.add_argument("--plan-file", type=Path, default=None, help="Start a run for a one-off plan outside plans/.")
    p_start.add_argument("--task", required=True)

    p_complete = sub.add_parser("complete", help="Mark a node complete in a run.")
    p_complete.add_argument("run_id")
    p_complete.add_argument("node_id")
    p_complete.add_argument("--note", default=None)
    p_complete.add_argument(
        "--approved-by-user", action="store_true",
        help="Required to complete a node with requires_user_approval: true.",
    )

    p_skip = sub.add_parser("skip", help="Mark a node waived in a run.")
    p_skip.add_argument("run_id")
    p_skip.add_argument("node_id")
    p_skip.add_argument("--reason", required=True)
    p_skip.add_argument(
        "--approved-by-user", action="store_true",
        help="Required to waive a node with requires_user_approval: true.",
    )

    p_check = sub.add_parser("check", help="Check whether a run satisfies its plan's gates.")
    p_check.add_argument("run_id")

    p_receipt = sub.add_parser("receipt", help="Regenerate the diagram from the ledger: what actually happened.")
    p_receipt.add_argument("run_id")

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    plans_dir: Path = args.plans_dir if args.plans_dir is not None else DEFAULT_PLANS_DIR
    runs_dir: Path = args.runs_dir if args.runs_dir is not None else default_state_dir() / "runs"
    claude_dir: Path = args.claude_dir if args.claude_dir is not None else DEFAULT_CLAUDE_DIR

    if args.command == "list":
        return cmd_list(plans_dir)
    if args.command == "validate":
        return cmd_validate(args.plan_id, args.all, plans_dir, claude_dir)
    if args.command == "show":
        return cmd_show(args.plan_id, args.plan_file, plans_dir, args.mermaid_only, args.cost_only, args.out)
    if args.command == "start":
        return cmd_start(args.plan_id, args.plan_file, args.task, plans_dir, runs_dir)
    if args.command == "complete":
        return cmd_complete(args.run_id, args.node_id, args.note, args.approved_by_user, plans_dir, runs_dir)
    if args.command == "skip":
        return cmd_skip(args.run_id, args.node_id, args.reason, args.approved_by_user, plans_dir, runs_dir)
    if args.command == "check":
        return cmd_check(args.run_id, plans_dir, runs_dir)
    if args.command == "receipt":
        return cmd_receipt(args.run_id, plans_dir, runs_dir)

    parser.error(f"unknown command {args.command!r}")
    return 2  # pragma: no cover -- parser.error() exits before this


if __name__ == "__main__":
    sys.exit(main())
