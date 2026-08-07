#!/usr/bin/env python3
"""Tests for orchestrate.py. Stdlib unittest only, no third-party test deps.

Run with:
    python3 .claude/orchestration/test_orchestrate.py -v
"""

from __future__ import annotations

import contextlib
import copy
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
import orchestrate as orch  # noqa: E402

PLANS_DIR = orch.DEFAULT_PLANS_DIR
CLAUDE_DIR = orch.DEFAULT_CLAUDE_DIR
ALL_PLAN_IDS = ["authoring", "implementation", "research-question", "review-only"]


def run_cli(argv: list[str]) -> tuple[int, str, str]:
    """Run orchestrate.main(argv), capturing stdout/stderr."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        rc = orch.main(argv)
    return rc, out.getvalue(), err.getvalue()


def make_node(**overrides: object) -> dict:
    base: dict = {
        "id": "node-a",
        "name": "Node A",
        "description": "does a thing",
        "agent": "general-purpose",
        "model": "sonnet",
        "effort": "medium",
        "size": "small",
        "shape": "balanced",
        "role": "research",
        "required": True,
        "skills": [],
        "inputs": [],
        "produces": "something",
        "gates": None,
        "feedback": None,
    }
    base.update(overrides)
    return base


def make_plan(plan_id: str = "fixture-plan", nodes: Optional[list] = None, **overrides: object) -> dict:
    if nodes is None:
        nodes = [
            make_node(id="research-node", role="research", required=True, gates=None),
            make_node(
                id="eval-node", name="Evaluator", role="evaluate", required=True,
                inputs=["research-node"], gates="user_response",
            ),
        ]
    plan = {
        "id": plan_id,
        "title": "Fixture plan",
        "description": "a fixture",
        "when_to_use": "in tests",
        "baseline_size": 50,
        "orchestrator": {"model": "opus", "effort": "xhigh", "mandate": "own it"},
        "nodes": nodes,
    }
    plan.update(overrides)
    return plan


def write_plan(dir_path: Path, plan_id: str, plan_dict: dict) -> Path:
    path = dir_path / f"{plan_id}.json"
    path.write_text(json.dumps(plan_dict))
    return path


class TempDirTestCase(unittest.TestCase):
    """Base class giving each test its own throwaway directory tree."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="orchestrate-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)


# =============================================================================
# Shipped plans
# =============================================================================


class ShippedPlansTests(unittest.TestCase):
    def test_all_shipped_plans_validate_cleanly(self) -> None:
        for plan_id in ALL_PLAN_IDS:
            with self.subTest(plan=plan_id):
                plan, errors = orch.load_plan_file(PLANS_DIR / f"{plan_id}.json")
                self.assertEqual(errors, [])
                self.assertIsNotNone(plan)

    def test_shipped_plans_have_no_requires_warnings(self) -> None:
        # The agents/skills named in `requires` should all resolve against
        # this repo's actual .claude/agents and .claude/skills.
        for plan_id in ALL_PLAN_IDS:
            with self.subTest(plan=plan_id):
                plan, _errors = orch.load_plan_file(PLANS_DIR / f"{plan_id}.json")
                warnings = orch.check_requires_availability(plan, CLAUDE_DIR)
                self.assertEqual(warnings, [])

    def test_shipped_plan_cost_report_has_verdict(self) -> None:
        for plan_id in ALL_PLAN_IDS:
            with self.subTest(plan=plan_id):
                plan, errors = orch.load_plan_file(PLANS_DIR / f"{plan_id}.json")
                self.assertEqual(errors, [])
                report = orch.render_cost_report(plan)
                self.assertTrue("COST PASS" in report or "COST FAIL" in report)

    def test_authoring_plan_fails_with_decomposition_flag(self) -> None:
        # Per the architecture review: authoring is expected to genuinely
        # fail cost-wise, and that is correct, not a bug to tune away.
        plan, errors = orch.load_plan_file(PLANS_DIR / "authoring.json")
        self.assertEqual(errors, [])
        report = orch.compute_cost_report(plan)
        self.assertGreaterEqual(report.total, report.baseline_declared)
        self.assertGreater(report.decomposed_size, report.declared_size * orch.DECOMPOSITION_FLAG_THRESHOLD)
        rendered = orch.render_cost_report(plan)
        self.assertIn("COST FAIL", rendered)
        self.assertIn("DECOMPOSITION FLAG", rendered)

    def test_decomposition_flag_compares_sizes_not_costs(self) -> None:
        """Regression: the flag fired on every `implementation` run.

        `implementation` decomposes only mildly (required sizes 150 vs a
        declared 118, ratio 1.27, under the 1.3 threshold) but carries a
        think-heavy `plan` node. Comparing *costs* let that shape inflate the
        ratio to 1.36 and trip the flag, so the one plan meant to be the
        common case cried wolf every time. Sizes are shape-independent.
        """
        plan, errors = orch.load_plan_file(PLANS_DIR / "implementation.json")
        self.assertEqual(errors, [])
        report = orch.compute_cost_report(plan)
        self.assertLessEqual(report.decomposed_size, report.declared_size * orch.DECOMPOSITION_FLAG_THRESHOLD)
        self.assertNotIn("DECOMPOSITION FLAG", orch.render_cost_report(plan))

        # The cost ratio that used to drive the flag is still above threshold,
        # so this test fails if anyone reverts to comparing costs.
        self.assertGreater(
            report.baseline_derived, report.baseline_declared * orch.DECOMPOSITION_FLAG_THRESHOLD
        )

    def test_decomposition_flag_is_shape_invariant(self) -> None:
        """Flipping every node's shape must not change whether the flag fires."""
        plan, errors = orch.load_plan_file(PLANS_DIR / "authoring.json")
        self.assertEqual(errors, [])
        before = orch.compute_cost_report(plan).decomposed_size
        for node in plan.nodes:
            node.shape = orch.Shape.READ_HEAVY
        self.assertEqual(orch.compute_cost_report(plan).decomposed_size, before)

    def test_implementation_research_review_plans_pass(self) -> None:
        for plan_id in ("implementation", "research-question", "review-only"):
            with self.subTest(plan=plan_id):
                plan, errors = orch.load_plan_file(PLANS_DIR / f"{plan_id}.json")
                self.assertEqual(errors, [])
                report = orch.compute_cost_report(plan)
                self.assertLess(report.total, report.baseline_declared)


# =============================================================================
# Field / structural validation rules (one rule per test, in-memory / tmp_path)
# =============================================================================


class ValidationRuleTests(TempDirTestCase):
    def _errors_for(self, plan_dict: dict, plan_id: str = "fixture-plan") -> list[str]:
        path = write_plan(self.tmp, plan_id, plan_dict)
        _plan, errors = orch.load_plan_file(path)
        return errors

    def test_sonnet_above_high_effort_rejected(self) -> None:
        plan_dict = make_plan(nodes=[
            make_node(id="research-node", role="research", model="sonnet", effort="xhigh", required=True),
            make_node(
                id="eval-node", name="Evaluator", role="evaluate", required=True,
                inputs=["research-node"], gates="user_response",
            ),
        ])
        errors = self._errors_for(plan_dict)
        self.assertTrue(any("sonnet must not exceed effort" in e for e in errors), errors)

    def test_cycle_in_inputs_detected(self) -> None:
        nodes = [
            make_node(id="a", role="research", required=True, inputs=["b"]),
            make_node(id="b", name="B", role="evaluate", required=True, inputs=["a"], gates="user_response"),
        ]
        errors = self._errors_for(make_plan(nodes=nodes))
        self.assertTrue(any("cycle detected in inputs" in e for e in errors), errors)

    def test_dangling_inputs_reference_detected(self) -> None:
        nodes = [
            make_node(id="a", role="research", required=True, inputs=["missing-node"]),
            make_node(
                id="eval-node", name="Evaluator", role="evaluate", required=True,
                inputs=["a"], gates="user_response",
            ),
        ]
        errors = self._errors_for(make_plan(nodes=nodes))
        self.assertTrue(any("inputs references unknown node 'missing-node'" in e for e in errors), errors)

    def test_dangling_feedback_to_reference_detected(self) -> None:
        nodes = [
            make_node(id="research-node", role="research", required=True),
            make_node(
                id="eval-node", name="Evaluator", role="evaluate", required=True,
                inputs=["research-node"], gates="user_response",
                feedback={"to": "missing-node", "when": "bad", "max_iterations": 1},
            ),
        ]
        errors = self._errors_for(make_plan(nodes=nodes))
        self.assertTrue(any("feedback.to references unknown node 'missing-node'" in e for e in errors), errors)

    def test_duplicate_node_ids_detected(self) -> None:
        nodes = [
            make_node(id="dup", role="research", required=True),
            make_node(id="dup", name="Evaluator", role="evaluate", required=True, gates="user_response"),
        ]
        errors = self._errors_for(make_plan(nodes=nodes))
        self.assertTrue(any("duplicate node id 'dup'" in e for e in errors), errors)

    def test_missing_evaluator_gate_detected(self) -> None:
        nodes = [
            make_node(id="research-node", role="research", required=True, gates=None),
            make_node(
                id="synth-node", name="Synth", role="synthesize", required=True,
                inputs=["research-node"], gates=None,
            ),
        ]
        errors = self._errors_for(make_plan(nodes=nodes))
        self.assertTrue(any("no evaluator gating the user response" in e for e in errors), errors)

    def test_unknown_field_detected(self) -> None:
        plan_dict = make_plan()
        plan_dict["unexpected_field"] = "surprise"
        errors = self._errors_for(plan_dict)
        self.assertTrue(any("unknown field 'unexpected_field'" in e for e in errors), errors)

    def test_bad_enum_value_detected(self) -> None:
        nodes = [
            make_node(id="research-node", role="research", required=True, model="claude-3"),
            make_node(
                id="eval-node", name="Evaluator", role="evaluate", required=True,
                inputs=["research-node"], gates="user_response",
            ),
        ]
        errors = self._errors_for(make_plan(nodes=nodes))
        self.assertTrue(any("model must be one of" in e for e in errors), errors)

    def test_id_filename_mismatch_detected(self) -> None:
        plan_dict = make_plan(plan_id="wrong-id")
        errors = self._errors_for(plan_dict, plan_id="fixture-plan")
        self.assertTrue(any("does not match filename stem" in e for e in errors), errors)

    def test_missing_required_field_detected(self) -> None:
        plan_dict = make_plan()
        del plan_dict["title"]
        errors = self._errors_for(plan_dict)
        self.assertTrue(any("missing required field 'title'" in e for e in errors), errors)

    def test_bad_node_id_slug_detected(self) -> None:
        nodes = [
            make_node(id="Bad_ID!", role="research", required=True),
            make_node(id="eval-node", name="Evaluator", role="evaluate", required=True, gates="user_response"),
        ]
        errors = self._errors_for(make_plan(nodes=nodes))
        self.assertTrue(any("must match slug pattern" in e for e in errors), errors)

    def test_bad_gates_value_detected(self) -> None:
        nodes = [
            make_node(id="research-node", role="research", required=True, gates="something_else"),
            make_node(
                id="eval-node", name="Evaluator", role="evaluate", required=True,
                inputs=["research-node"], gates="user_response",
            ),
        ]
        errors = self._errors_for(make_plan(nodes=nodes))
        self.assertTrue(any("gates must be 'user_response' or null" in e for e in errors), errors)

    def test_bad_max_iterations_detected(self) -> None:
        nodes = [
            make_node(id="research-node", role="research", required=True),
            make_node(
                id="eval-node", name="Evaluator", role="evaluate", required=True,
                inputs=["research-node"], gates="user_response",
                feedback={"to": "research-node", "when": "bad", "max_iterations": 5},
            ),
        ]
        errors = self._errors_for(make_plan(nodes=nodes))
        self.assertTrue(any("max_iterations must be an integer in 1..3" in e for e in errors), errors)

    # -- new-schema rules --

    def test_missing_baseline_size_detected(self) -> None:
        plan_dict = make_plan()
        del plan_dict["baseline_size"]
        errors = self._errors_for(plan_dict)
        self.assertTrue(any("missing required field 'baseline_size'" in e for e in errors), errors)

    def test_non_positive_baseline_size_detected(self) -> None:
        plan_dict = make_plan(baseline_size=0)
        errors = self._errors_for(plan_dict)
        self.assertTrue(any("baseline_size must be a number > 0" in e for e in errors), errors)

    def test_bad_agent_enum_value_detected(self) -> None:
        nodes = [
            make_node(id="research-node", role="research", required=True, agent="totally-made-up-agent"),
            make_node(
                id="eval-node", name="Evaluator", role="evaluate", required=True,
                inputs=["research-node"], gates="user_response",
            ),
        ]
        errors = self._errors_for(make_plan(nodes=nodes))
        self.assertTrue(any("agent must be one of" in e for e in errors), errors)

    def test_shape_defaults_to_balanced_when_absent(self) -> None:
        node_dict = make_node(id="research-node", role="research", required=True)
        del node_dict["shape"]
        plan_dict = make_plan(nodes=[
            node_dict,
            make_node(id="eval-node", name="Evaluator", role="evaluate", required=True,
                      inputs=["research-node"], gates="user_response"),
        ])
        path = write_plan(self.tmp, "fixture-plan", plan_dict)
        plan, errors = orch.load_plan_file(path)
        self.assertEqual(errors, [])
        research = next(n for n in plan.nodes if n.id == "research-node")
        self.assertEqual(research.shape, orch.Shape.BALANCED)

    def test_requires_user_approval_defaults_to_false(self) -> None:
        node_dict = make_node(id="research-node", role="research", required=True)
        self.assertNotIn("requires_user_approval", node_dict)
        plan_dict = make_plan(nodes=[
            node_dict,
            make_node(id="eval-node", name="Evaluator", role="evaluate", required=True,
                      inputs=["research-node"], gates="user_response"),
        ])
        path = write_plan(self.tmp, "fixture-plan", plan_dict)
        plan, errors = orch.load_plan_file(path)
        self.assertEqual(errors, [])
        research = next(n for n in plan.nodes if n.id == "research-node")
        self.assertFalse(research.requires_user_approval)

    def test_on_exhausted_defaults_to_surface_to_user(self) -> None:
        nodes = [
            make_node(id="research-node", role="research", required=True),
            make_node(
                id="eval-node", name="Evaluator", role="evaluate", required=True,
                inputs=["research-node"], gates="user_response",
                feedback={"to": "research-node", "when": "bad", "max_iterations": 1},
            ),
        ]
        path = write_plan(self.tmp, "fixture-plan", make_plan(nodes=nodes))
        plan, errors = orch.load_plan_file(path)
        self.assertEqual(errors, [])
        eval_node = next(n for n in plan.nodes if n.id == "eval-node")
        self.assertEqual(eval_node.feedback.on_exhausted, orch.OnExhausted.SURFACE_TO_USER)

    def test_requires_warns_but_does_not_fail_on_missing_agent_or_skill(self) -> None:
        plan_dict = make_plan(requires={"agents": ["nonexistent-agent"], "skills": ["nonexistent-skill"]})
        path = write_plan(self.tmp, "fixture-plan", plan_dict)
        plan, errors = orch.load_plan_file(path)
        self.assertEqual(errors, [])  # never fails validation
        warnings = orch.check_requires_availability(plan, CLAUDE_DIR)
        self.assertTrue(any("nonexistent-agent" in w for w in warnings), warnings)
        self.assertTrue(any("nonexistent-skill" in w for w in warnings), warnings)

    def test_requires_builtin_agents_never_warn(self) -> None:
        plan_dict = make_plan(requires={"agents": ["Explore", "general-purpose", "orchestrator"], "skills": []})
        path = write_plan(self.tmp, "fixture-plan", plan_dict)
        plan, errors = orch.load_plan_file(path)
        self.assertEqual(errors, [])
        warnings = orch.check_requires_availability(plan, CLAUDE_DIR)
        self.assertEqual(warnings, [])


# =============================================================================
# Cost model
# =============================================================================


class CostModelTests(unittest.TestCase):
    def _fixture_plan(self) -> orch.Plan:
        orchestrator = orch.Orchestrator(model=orch.Model.OPUS, effort=orch.Effort.HIGH, mandate="own it")
        research_node = orch.Node(
            id="research-node", name="R", description="d", agent=orch.AgentType.GENERAL_PURPOSE,
            model=orch.Model.HAIKU, effort=orch.Effort.LOW, size=orch.Size.SMALL, shape=orch.Shape.BALANCED,
            role=orch.Role.RESEARCH, required=True, inputs=[],
        )
        eval_node = orch.Node(
            id="eval-node", name="E", description="d", agent=orch.AgentType.GENERAL_PURPOSE,
            model=orch.Model.SONNET, effort=orch.Effort.HIGH, size=orch.Size.SMALL, shape=orch.Shape.BALANCED,
            role=orch.Role.EVALUATE, required=True, inputs=["research-node"], gates="user_response",
            feedback=orch.Feedback(to="research-node", when="bad", max_iterations=2),
        )
        optional_node = orch.Node(
            id="optional-node", name="O", description="d", agent=orch.AgentType.ORCHESTRATOR,
            model=orch.Model.OPUS, effort=orch.Effort.MEDIUM, size=orch.Size.MEDIUM, shape=orch.Shape.BALANCED,
            role=orch.Role.IMPLEMENT, required=False, inputs=["research-node"],
        )
        return orch.Plan(
            id="fixture", title="Fixture", description="d", when_to_use="tests",
            baseline_size=10.0, orchestrator=orchestrator,
            nodes=[research_node, eval_node, optional_node],
        )

    def test_cost_arithmetic_hand_computed(self) -> None:
        # Hand-computed by the exact formulas in orchestrate.py's cost model
        # block. orchestrator = opus/high => model_w=5.0, effort_m=1.5.
        #
        # research-node: shape=balanced (0.5/0.5), size=small(10), model=haiku(1.0), effort=low(0.6)
        #   node_cost  = 1.0 * (10*0.5 + 5.0*10*0.5*0.6) = 1.0*(5 + 15) = 20.0
        #   handoff    = PREFIX_UNITS[general-purpose](10.0)*1.0 + RETURN_UNITS[small](3.0)*5.0 = 10+15 = 25.0
        #   cost(R)    = 45.0
        #
        # eval-node: shape=balanced, size=small(10), model=sonnet(3.0), effort=high(1.5)
        #   node_cost  = 3.0 * (10*0.5 + 5.0*10*0.5*1.5) = 3.0*(5 + 37.5) = 127.5
        #   handoff    = PREFIX_UNITS[general-purpose](10.0)*3.0 + RETURN_UNITS[small](3.0)*5.0 = 30+15 = 45.0
        #   cost(E)    = 172.5
        #
        # optional-node: agent=orchestrator => handoff = 0
        #   shape=balanced, size=medium(30), model=opus(5.0), effort=medium(1.0)
        #   node_cost  = 5.0 * (30*0.5 + 5.0*30*0.5*1.0) = 5.0*(15 + 75) = 450.0
        #   cost(O)    = 450.0
        plan = self._fixture_plan()
        self.assertAlmostEqual(orch.node_cost(plan.nodes[0]), 20.0)
        self.assertAlmostEqual(orch.handoff_cost(plan.nodes[0], plan.orchestrator), 25.0)
        self.assertAlmostEqual(orch.node_cost(plan.nodes[1]), 127.5)
        self.assertAlmostEqual(orch.handoff_cost(plan.nodes[1], plan.orchestrator), 45.0)
        self.assertAlmostEqual(orch.node_cost(plan.nodes[2]), 450.0)
        self.assertAlmostEqual(orch.handoff_cost(plan.nodes[2], plan.orchestrator), 0.0)

        report = orch.compute_cost_report(plan)

        # baseline_declared: _work(baseline_size=10, balanced, opus=5.0, high=1.5)
        #   = 5.0*(10*0.5 + 5.0*10*0.5*1.5) = 5.0*(5+37.5) = 212.5
        self.assertAlmostEqual(report.baseline_declared, 212.5)

        # baseline_derived: sum over REQUIRED nodes of _work(SIZE_UNITS[size], node.shape, opus, high)
        #   research-node (small, balanced): 5.0*(10*0.5+5*10*0.5*1.5) = 212.5
        #   eval-node     (small, balanced): same shape/size            = 212.5
        #   (optional-node excluded: not required)
        self.assertAlmostEqual(report.baseline_derived, 425.0)

        # total: cost(R) + cost(E) = 45.0 + 172.5 = 217.5
        self.assertAlmostEqual(report.total, 217.5)

        # optional_add: cost(O) = 450.0
        self.assertAlmostEqual(report.optional_add, 450.0)

        # feedback edge: eval-node -> research-node, max_iterations=2
        #   iter_cost = 0.35*(node_cost(R)+node_cost(E)) + handoff(R)+handoff(E)
        #             = 0.35*(20.0+127.5) + 25.0+45.0 = 0.35*147.5 + 70.0 = 51.625+70.0 = 121.625
        #   expected  = 0.5*iter_cost + 0.2*iter_cost = 0.7*121.625 = 85.1375
        #   ceiling   = 2*121.625 = 243.25
        self.assertAlmostEqual(report.feedback_expected, 85.1375)
        self.assertAlmostEqual(report.feedback_ceiling, 243.25)

    def test_handoff_cost_zero_for_orchestrator_agent(self) -> None:
        plan = self._fixture_plan()
        orchestrator_agent_node = plan.nodes[2]
        self.assertEqual(orchestrator_agent_node.agent, orch.AgentType.ORCHESTRATOR)
        self.assertEqual(orch.handoff_cost(orchestrator_agent_node, plan.orchestrator), 0.0)

    def test_handoff_cost_scales_with_sub_agents_own_model_weight(self) -> None:
        orchestrator = orch.Orchestrator(model=orch.Model.OPUS, effort=orch.Effort.HIGH, mandate="m")
        haiku_explore = orch.Node(
            id="a", name="A", description="d", agent=orch.AgentType.EXPLORE, model=orch.Model.HAIKU,
            effort=orch.Effort.LOW, size=orch.Size.SMALL, shape=orch.Shape.BALANCED,
            role=orch.Role.RESEARCH, required=True,
        )
        opus_architect = orch.Node(
            id="b", name="B", description="d", agent=orch.AgentType.SOFTWARE_ARCHITECT, model=orch.Model.OPUS,
            effort=orch.Effort.XHIGH, size=orch.Size.SMALL, shape=orch.Shape.BALANCED,
            role=orch.Role.PLAN, required=True,
        )
        haiku_handoff = orch.handoff_cost(haiku_explore, orchestrator)
        opus_handoff = orch.handoff_cost(opus_architect, orchestrator)
        self.assertGreater(haiku_handoff, 0.0)
        self.assertGreater(opus_handoff, 0.0)
        self.assertLess(haiku_handoff, opus_handoff)

    def test_work_splits_by_shape_think_heavy_costs_more_than_read_heavy(self) -> None:
        read_heavy = orch._work(30.0, orch.Shape.READ_HEAVY, orch.MODEL_WEIGHT["sonnet"], orch.EFFORT_MULTIPLIER["high"])
        think_heavy = orch._work(30.0, orch.Shape.THINK_HEAVY, orch.MODEL_WEIGHT["sonnet"], orch.EFFORT_MULTIPLIER["high"])
        balanced = orch._work(30.0, orch.Shape.BALANCED, orch.MODEL_WEIGHT["sonnet"], orch.EFFORT_MULTIPLIER["high"])
        self.assertLess(read_heavy, balanced)
        self.assertLess(balanced, think_heavy)

    def test_baseline_declared_independent_of_node_list(self) -> None:
        plan = self._fixture_plan()
        before = orch.baseline_declared_cost(plan)

        mutated = copy.deepcopy(plan)
        mutated.nodes[0].size = orch.Size.LARGE  # blow up a node's size

        after_node_change = orch.baseline_declared_cost(mutated)
        self.assertAlmostEqual(before, after_node_change)

        derived_before = orch.baseline_derived_cost(plan)
        derived_after = orch.baseline_derived_cost(mutated)
        self.assertNotAlmostEqual(derived_before, derived_after)

    def test_label_invariance_role_flip_does_not_change_cost_or_verdict(self) -> None:
        """Regression test for the bug that motivated this rewrite: an
        earlier cost model excluded 'evaluate' nodes from the baseline, so
        relabeling a node's role flipped the verdict without changing any
        dispatch. role must now be cosmetic (diagram colour + breakdown) only."""
        plan = self._fixture_plan()
        report_before = orch.compute_cost_report(plan)

        flipped = copy.deepcopy(plan)
        flipped.nodes[1].role = orch.Role.SYNTHESIZE  # was EVALUATE
        report_after = orch.compute_cost_report(flipped)

        self.assertAlmostEqual(report_before.baseline_derived, report_after.baseline_derived)
        self.assertAlmostEqual(report_before.total, report_after.total)
        self.assertAlmostEqual(report_before.baseline_declared, report_after.baseline_declared)
        verdict_before = report_before.total < report_before.baseline_declared
        verdict_after = report_after.total < report_after.baseline_declared
        self.assertEqual(verdict_before, verdict_after)

    def test_decomposition_flag_fires_above_threshold(self) -> None:
        orchestrator = orch.Orchestrator(model=orch.Model.OPUS, effort=orch.Effort.XHIGH, mandate="m")
        # A tiny declared baseline next to a large required node list should
        # trip the decomposition flag (derived > declared * 1.3).
        big_node = orch.Node(
            id="a", name="A", description="d", agent=orch.AgentType.ORCHESTRATOR, model=orch.Model.OPUS,
            effort=orch.Effort.XHIGH, size=orch.Size.LARGE, shape=orch.Shape.THINK_HEAVY,
            role=orch.Role.PLAN, required=True,
        )
        plan = orch.Plan(
            id="p", title="P", description="d", when_to_use="t",
            baseline_size=1.0, orchestrator=orchestrator, nodes=[big_node],
        )
        rendered = orch.render_cost_report(plan)
        self.assertIn("DECOMPOSITION FLAG", rendered)

    def test_decomposition_flag_absent_below_threshold(self) -> None:
        orchestrator = orch.Orchestrator(model=orch.Model.OPUS, effort=orch.Effort.XHIGH, mandate="m")
        small_node = orch.Node(
            id="a", name="A", description="d", agent=orch.AgentType.ORCHESTRATOR, model=orch.Model.OPUS,
            effort=orch.Effort.XHIGH, size=orch.Size.SMALL, shape=orch.Shape.BALANCED,
            role=orch.Role.PLAN, required=True,
        )
        plan = orch.Plan(
            id="p", title="P", description="d", when_to_use="t",
            baseline_size=1000.0, orchestrator=orchestrator, nodes=[small_node],
        )
        rendered = orch.render_cost_report(plan)
        self.assertNotIn("DECOMPOSITION FLAG", rendered)


# =============================================================================
# Mermaid rendering
# =============================================================================


class MermaidTests(unittest.TestCase):
    def _fixture_plan(self) -> orch.Plan:
        orchestrator = orch.Orchestrator(model=orch.Model.OPUS, effort=orch.Effort.XHIGH, mandate="m")
        n1 = orch.Node(
            id="n1", name="N1", description="d", agent=orch.AgentType.EXPLORE, model=orch.Model.HAIKU,
            effort=orch.Effort.LOW, size=orch.Size.SMALL, shape=orch.Shape.READ_HEAVY,
            role=orch.Role.RESEARCH, required=True,
        )
        n2 = orch.Node(
            id="n2", name='N2 "quoted"', description="d", agent=orch.AgentType.GENERAL_PURPOSE,
            model=orch.Model.SONNET, effort=orch.Effort.HIGH, size=orch.Size.SMALL, shape=orch.Shape.BALANCED,
            role=orch.Role.EVALUATE, required=True, inputs=["n1"], gates="user_response",
            feedback=orch.Feedback(to="n1", when='loop "back"', max_iterations=2),
        )
        return orch.Plan(
            id="fixture", title="Fixture", description="d", when_to_use="tests",
            baseline_size=10.0, orchestrator=orchestrator, nodes=[n1, n2],
        )

    def test_mermaid_id_sanitizes_dashes(self) -> None:
        self.assertEqual(orch._mermaid_id("my-node-id"), "n_my_node_id")

    def test_mermaid_contains_expected_edge_kinds(self) -> None:
        mermaid = orch.generate_mermaid(self._fixture_plan())
        self.assertIn("TASK --> n_n1", mermaid)
        self.assertIn("n_n1 --> n_n2", mermaid)
        self.assertIn("n_n2 ==> ANSWER", mermaid)
        self.assertIn("n_n2 -.->|", mermaid)

    def test_mermaid_has_no_unescaped_quotes_inside_labels(self) -> None:
        mermaid = orch.generate_mermaid(self._fixture_plan())
        self.assertIn("quoted", mermaid)
        self.assertNotIn('"quoted"', mermaid)
        self.assertIn("back", mermaid)
        self.assertNotIn('"back"', mermaid)

    def test_mermaid_ids_have_no_dashes_for_all_shipped_plans(self) -> None:
        for plan_id in ALL_PLAN_IDS:
            plan, _errors = orch.load_plan_file(PLANS_DIR / f"{plan_id}.json")
            for n in plan.nodes:
                self.assertNotIn("-", orch._mermaid_id(n.id))

    def test_receipt_mermaid_marks_complete_pending_and_waived_distinctly(self) -> None:
        plan = self._fixture_plan()
        ledger = {
            "completed": {"n1": {"at": "t", "note": ""}},
            "waived": {"n2": {"at": "t", "reason": "risk accepted"}},
        }
        mermaid = orch.generate_receipt_mermaid(plan, ledger)
        self.assertIn("[complete]", mermaid)
        self.assertIn("[WAIVED]", mermaid)
        self.assertIn("statusWaivedRequired", mermaid)  # n2 is required=True
        self.assertIn("statusComplete", mermaid)

        ledger_pending = {"completed": {}, "waived": {}}
        mermaid_pending = orch.generate_receipt_mermaid(plan, ledger_pending)
        self.assertIn("[pending]", mermaid_pending)
        self.assertIn("statusPending", mermaid_pending)


# =============================================================================
# Ledger: run lifecycle, approval barrier, waiving, receipt
# =============================================================================


class LedgerTests(TempDirTestCase):
    def test_ledger_roundtrip_start_complete_check(self) -> None:
        runs_dir = self.tmp / "runs"
        rc, out, _err = run_cli(["--plans-dir", str(PLANS_DIR), "--runs-dir", str(runs_dir),
                                  "start", "review-only", "--task", "review this diff"])
        self.assertEqual(rc, 0)
        run_id = out.strip()

        rc, out, _err = run_cli(["--plans-dir", str(PLANS_DIR), "--runs-dir", str(runs_dir), "check", run_id])
        self.assertEqual(rc, 1)
        self.assertIn("GATE FAIL:", out.splitlines()[-1])

        for node_id in ["scope", "review", "verify-findings"]:
            rc, _out, _err = run_cli(["--plans-dir", str(PLANS_DIR), "--runs-dir", str(runs_dir),
                                       "complete", run_id, node_id])
            self.assertEqual(rc, 0, node_id)

        rc, out, _err = run_cli(["--plans-dir", str(PLANS_DIR), "--runs-dir", str(runs_dir), "check", run_id])
        self.assertEqual(rc, 0)
        self.assertEqual(out.splitlines()[-1], "GATE PASS")
        self.assertIn("All gate nodes are completed.", out)
        self.assertNotIn("Consent-recorded exceptions", out)

    def test_start_creates_ledger_with_expected_shape(self) -> None:
        runs_dir = self.tmp / "runs"
        rc, out, _err = run_cli(["--plans-dir", str(PLANS_DIR), "--runs-dir", str(runs_dir),
                                  "start", "review-only", "--task", "review PR #123"])
        self.assertEqual(rc, 0)
        run_id = out.strip()
        ledger_path = runs_dir / f"{run_id}.json"
        self.assertTrue(ledger_path.exists())
        ledger = json.loads(ledger_path.read_text())
        self.assertEqual(ledger["plan_id"], "review-only")
        self.assertEqual(ledger["task"], "review PR #123")
        self.assertEqual(ledger["completed"], {})
        self.assertEqual(ledger["waived"], {})
        self.assertIn("started_at", ledger)
        self.assertEqual(ledger["run_id"], run_id)
        self.assertTrue(run_id.endswith("-review-only"))

    def test_complete_refuses_node_with_unmet_dependency(self) -> None:
        runs_dir = self.tmp / "runs"
        rc, out, _err = run_cli(["--plans-dir", str(PLANS_DIR), "--runs-dir", str(runs_dir),
                                  "start", "review-only", "--task", "t"])
        run_id = out.strip()

        rc, _out, err = run_cli(["--plans-dir", str(PLANS_DIR), "--runs-dir", str(runs_dir),
                                  "complete", run_id, "review"])
        self.assertEqual(rc, 1)
        self.assertIn("unmet dependencies", err)
        self.assertIn("scope", err)

    def test_waived_required_node_lets_check_pass_but_is_reported_separately(self) -> None:
        runs_dir = self.tmp / "runs"
        rc, out, _err = run_cli(["--plans-dir", str(PLANS_DIR), "--runs-dir", str(runs_dir),
                                  "start", "review-only", "--task", "t"])
        run_id = out.strip()

        rc, out, _err = run_cli(["--plans-dir", str(PLANS_DIR), "--runs-dir", str(runs_dir),
                                  "skip", run_id, "scope", "--reason", "user approved skipping scope"])
        self.assertEqual(rc, 0)
        self.assertIn("WARNING", out)
        self.assertIn("explicit user consent", out)

        for node_id in ["review", "verify-findings"]:
            rc, _out, _err = run_cli(["--plans-dir", str(PLANS_DIR), "--runs-dir", str(runs_dir),
                                       "complete", run_id, node_id])
            self.assertEqual(rc, 0, node_id)

        rc, out, _err = run_cli(["--plans-dir", str(PLANS_DIR), "--runs-dir", str(runs_dir), "check", run_id])
        self.assertEqual(rc, 0)
        self.assertEqual(out.splitlines()[-1], "GATE PASS")

    def test_check_reports_waived_gate_node_distinctly_from_completed(self) -> None:
        runs_dir = self.tmp / "runs"
        rc, out, _err = run_cli(["--plans-dir", str(PLANS_DIR), "--runs-dir", str(runs_dir),
                                  "start", "review-only", "--task", "t"])
        run_id = out.strip()

        run_cli(["--plans-dir", str(PLANS_DIR), "--runs-dir", str(runs_dir), "complete", run_id, "scope"])
        run_cli(["--plans-dir", str(PLANS_DIR), "--runs-dir", str(runs_dir), "complete", run_id, "review"])

        rc, _out, _err = run_cli(["--plans-dir", str(PLANS_DIR), "--runs-dir", str(runs_dir),
                                   "skip", run_id, "verify-findings", "--reason", "user accepted risk"])
        self.assertEqual(rc, 0)

        rc, out, _err = run_cli(["--plans-dir", str(PLANS_DIR), "--runs-dir", str(runs_dir), "check", run_id])
        self.assertEqual(rc, 0)
        self.assertIn("Consent-recorded exceptions", out)
        self.assertIn("verify-findings", out)
        self.assertEqual(out.splitlines()[-1], "GATE PASS")

    def test_complete_refuses_and_then_accepts_requires_user_approval_node(self) -> None:
        runs_dir = self.tmp / "runs"
        rc, out, _err = run_cli(["--plans-dir", str(PLANS_DIR), "--runs-dir", str(runs_dir),
                                  "start", "implementation", "--task", "t"])
        run_id = out.strip()
        run_cli(["--plans-dir", str(PLANS_DIR), "--runs-dir", str(runs_dir), "complete", run_id, "recon"])

        rc, _out, err = run_cli(["--plans-dir", str(PLANS_DIR), "--runs-dir", str(runs_dir),
                                  "complete", run_id, "plan"])
        self.assertEqual(rc, 1)
        self.assertIn("requires_user_approval", err)

        rc, _out, _err = run_cli(["--plans-dir", str(PLANS_DIR), "--runs-dir", str(runs_dir),
                                   "complete", run_id, "plan", "--approved-by-user"])
        self.assertEqual(rc, 0)

        ledger = json.loads((runs_dir / f"{run_id}.json").read_text())
        self.assertTrue(ledger["completed"]["plan"]["approved_by_user"])

    def test_receipt_marks_waived_and_complete_nodes_distinctly(self) -> None:
        runs_dir = self.tmp / "runs"
        rc, out, _err = run_cli(["--plans-dir", str(PLANS_DIR), "--runs-dir", str(runs_dir),
                                  "start", "review-only", "--task", "t"])
        run_id = out.strip()
        run_cli(["--plans-dir", str(PLANS_DIR), "--runs-dir", str(runs_dir), "complete", run_id, "scope"])
        run_cli(["--plans-dir", str(PLANS_DIR), "--runs-dir", str(runs_dir),
                 "skip", run_id, "review", "--reason", "time-boxed, shipping without it"])

        rc, out, _err = run_cli(["--plans-dir", str(PLANS_DIR), "--runs-dir", str(runs_dir), "receipt", run_id])
        self.assertEqual(rc, 0)
        self.assertIn("```mermaid", out)
        self.assertIn("[complete]", out)
        self.assertIn("[WAIVED]", out)
        self.assertIn("[pending]", out)  # verify-findings never touched

    def test_plan_file_flag_allows_one_off_plan_outside_plans_dir(self) -> None:
        runs_dir = self.tmp / "runs"
        external_dir = self.tmp / "external"
        external_dir.mkdir()
        plan_dict = make_plan(plan_id="one-off")
        plan_path = write_plan(external_dir, "one-off", plan_dict)

        rc, out, err = run_cli(["--runs-dir", str(runs_dir), "show", "--plan-file", str(plan_path), "--cost-only"])
        self.assertEqual(rc, 0, err)
        self.assertIn("COST", out)

        rc, out, _err = run_cli(["--runs-dir", str(runs_dir), "start", "--plan-file", str(plan_path),
                                  "--task", "one-off task"])
        self.assertEqual(rc, 0)
        run_id = out.strip()
        self.assertTrue(run_id.endswith("-one-off"))

        # complete must still be able to find the plan again via the ledger's
        # recorded plan_path, even though it isn't under any --plans-dir.
        rc, _out, err = run_cli(["--runs-dir", str(runs_dir), "complete", run_id, "research-node"])
        self.assertEqual(rc, 0, err)

    def test_ledger_paths_resolve_under_temp_xdg_state_home_never_in_repo(self) -> None:
        fake_state_home = self.tmp / "xdg-state"
        old_xdg = os.environ.get("XDG_STATE_HOME")
        old_project = os.environ.get("CLAUDE_PROJECT_DIR")
        os.environ["XDG_STATE_HOME"] = str(fake_state_home)
        os.environ["CLAUDE_PROJECT_DIR"] = "/some/fake/project/dir"
        try:
            state_dir = orch.default_state_dir()
            self.assertTrue(str(state_dir).startswith(str(fake_state_home)))
            repo_root = orch.SCRIPT_DIR.parent.parent  # .claude/orchestration -> .claude -> repo root
            self.assertFalse(str(state_dir).startswith(str(repo_root)))

            rc, out, _err = run_cli(["start", "review-only", "--task", "t"])
            self.assertEqual(rc, 0)
            run_id = out.strip()
            ledger_file = state_dir / "runs" / f"{run_id}.json"
            self.assertTrue(ledger_file.exists())
        finally:
            if old_xdg is None:
                os.environ.pop("XDG_STATE_HOME", None)
            else:
                os.environ["XDG_STATE_HOME"] = old_xdg
            if old_project is None:
                os.environ.pop("CLAUDE_PROJECT_DIR", None)
            else:
                os.environ["CLAUDE_PROJECT_DIR"] = old_project
            shutil.rmtree(fake_state_home, ignore_errors=True)


# =============================================================================
# CLI smoke tests (default paths)
# =============================================================================


class CliDefaultsTests(unittest.TestCase):
    def test_validate_all_real_plans_exits_zero(self) -> None:
        rc, _out, _err = run_cli(["validate", "--all"])
        self.assertEqual(rc, 0)

    def test_list_default_plans_dir(self) -> None:
        rc, out, _err = run_cli(["list"])
        self.assertEqual(rc, 0)
        for plan_id in ALL_PLAN_IDS:
            self.assertIn(plan_id, out)

    def test_show_mermaid_only(self) -> None:
        rc, out, _err = run_cli(["show", "implementation", "--mermaid-only"])
        self.assertEqual(rc, 0)
        self.assertIn("```mermaid", out)
        self.assertNotIn("Cost report", out)

    def test_show_cost_only(self) -> None:
        rc, out, _err = run_cli(["show", "implementation", "--cost-only"])
        self.assertEqual(rc, 0)
        self.assertIn("Cost report", out)
        self.assertNotIn("```mermaid", out)

    def test_show_out_writes_file(self) -> None:
        tmp = Path(tempfile.mkdtemp(prefix="orchestrate-test-"))
        try:
            out_path = tmp / "out.md"
            rc, _out, _err = run_cli(["show", "implementation", "--out", str(out_path)])
            self.assertEqual(rc, 0)
            content = out_path.read_text()
            self.assertIn("```mermaid", content)
            self.assertIn("Cost report", content)
            self.assertIn("Standard implementation", content)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
