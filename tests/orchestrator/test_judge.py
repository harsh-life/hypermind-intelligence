"""The Judge path: never gated by an `OrchestratorAction`, never able to
reach the Skill Registry (docs/02 §3/§15, [LOCKED]). Task brief §8/§22."""
from __future__ import annotations

import inspect

from tests.orchestrator.conftest import refusal_result, runtime_registry_with_scripted, structured_success
from trackA.orchestrator.run import RunContext
from trackA.registries.skills import SPECIALIST_EXECUTOR
from trackA.registries.errors import AccessDeniedError


class TestJudgeStructuralBoundary:
    def test_run_judge_signature_accepts_no_skill_id_or_caller_override(self):
        sig = inspect.signature(RunContext.run_judge)
        param_names = set(sig.parameters) - {"self"}
        assert "skill_id" not in param_names
        assert "caller" not in param_names
        assert param_names == {"worker_output_record_ids", "accumulated_evidence"}

    def test_judge_input_always_asserts_no_skill_content(self, run_context):
        outcome = run_context.run_judge(worker_output_record_ids=["w1"], accumulated_evidence={"endpoints": []})
        assert outcome.judge_input.contains_skill_content is False

    def test_skill_registry_still_rejects_a_caller_literally_named_judge(self, skill_registry):
        # Directly exercising the registry-layer guarantee this
        # orchestrator-layer boundary is built on top of (Context 2,
        # unmodified) — the Orchestrator's own run_judge simply never
        # reaches this call at all (see the signature test above), and
        # this confirms that even if some future code tried, the registry
        # itself would still refuse it.
        try:
            skill_registry.lookup("idor_v1", caller="judge")
            assert False, "expected AccessDeniedError"
        except AccessDeniedError:
            pass

    def test_specialist_path_uses_only_the_documented_caller_identity(self, run_context, action_factory):
        # Indirect proof that the Specialist path's Skill Registry access
        # always goes through SPECIALIST_EXECUTOR: a specialist_investigation
        # action for a *registered* skill_id succeeds (would raise
        # AccessDeniedError at the registry layer if any other caller
        # string were ever used).
        outcome = run_context.run_specialist_action(
            action_factory(action_type="specialist_investigation", target="idor_v1", parameters={}),
            evidence_context={"mapped_endpoints": []},
            judge_routing_record_id="j1",
        )
        assert outcome.was_authorized or outcome.rejected.reason_code != "skill_registry_rejection"


class TestJudgeInvocation:
    def test_judge_resolves_role_and_produces_routing_decision(self, orchestrator_factory, run_id, scope_authorization, run_scope_factory, model_registry):
        payload = {
            "decision": "route_to_skill",
            "target_skill_id": "idor_v1",
            "reasoning": "endpoint pattern consistent with IDOR investigation",
            "confidence": 0.7,
        }
        registry, adapter = runtime_registry_with_scripted(
            model_registry, candidate_id="cand-judge", results=[structured_success(payload)]
        )
        orch = orchestrator_factory(runtime_registry=registry)
        ctx = orch.start_run(run_id=run_id, scope=scope_authorization, run_scope=run_scope_factory())
        outcome = ctx.run_judge(worker_output_record_ids=["w1"], accumulated_evidence={"endpoints": ["/x"]})
        assert outcome.decision is not None
        assert outcome.decision.decision == "route_to_skill"
        assert outcome.decision.target_skill_id == "idor_v1"
        assert outcome.decision.provenance.model_id == "cand-judge"

    def test_judge_refusal_produces_failure_not_a_fabricated_decision(self, orchestrator_factory, run_id, scope_authorization, run_scope_factory, model_registry):
        registry, adapter = runtime_registry_with_scripted(
            model_registry, candidate_id="cand-judge", results=[refusal_result()]
        )
        orch = orchestrator_factory(runtime_registry=registry)
        ctx = orch.start_run(run_id=run_id, scope=scope_authorization, run_scope=run_scope_factory())
        outcome = ctx.run_judge(worker_output_record_ids=["w1"], accumulated_evidence={})
        assert outcome.decision is None
        assert outcome.failure.failure_type == "model_refusal"
        assert adapter.call_count == 1

    def test_judge_malformed_output_never_defaults_to_a_routing_decision(self, orchestrator_factory, run_id, scope_authorization, run_scope_factory, model_registry):
        # Missing required fields (reasoning/confidence) -> construction
        # fails -> must surface as schema_invalid, never as e.g. a
        # silently-defaulted "drop" decision.
        registry, adapter = runtime_registry_with_scripted(
            model_registry, candidate_id="cand-judge", results=[structured_success({"decision": "drop"})]
        )
        orch = orchestrator_factory(runtime_registry=registry)
        ctx = orch.start_run(run_id=run_id, scope=scope_authorization, run_scope=run_scope_factory())
        outcome = ctx.run_judge(worker_output_record_ids=["w1"], accumulated_evidence={})
        assert outcome.decision is None
        assert outcome.failure.failure_type == "schema_invalid"
