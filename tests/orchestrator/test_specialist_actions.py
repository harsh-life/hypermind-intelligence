"""Specialist-investigation actions: Skill Registry resolution (through
the sole `SPECIALIST_EXECUTOR` caller identity), `specialist_role_binding
-> RoleResolver`, and the `replication_command`-required stop-at-
candidate-finding boundary (task brief §8/§19)."""
from __future__ import annotations

from tests.orchestrator.conftest import runtime_registry_with_scripted, structured_success
from trackA.schemas.common import TrustClassification


_VALID_POC_PAYLOAD = {
    "vulnerability_claim": "GET /api/v1/users/{id} returns another user's data",
    "replication_command": "curl -H 'Authorization: Bearer <token>' https://target/api/v1/users/2",
    "supporting_evidence": {"request": "...", "response_snippet": "..."},
    "specialist_confidence": 0.7,
}


class TestSpecialistResolutionAndInvocation:
    def test_authorized_specialist_action_resolves_role_and_produces_candidate_finding(
        self, orchestrator_factory, run_id, scope_authorization, run_scope_factory, action_factory, model_registry
    ):
        registry, adapter = runtime_registry_with_scripted(
            model_registry, candidate_id="cand-specialist", results=[structured_success(_VALID_POC_PAYLOAD)]
        )
        orch = orchestrator_factory(runtime_registry=registry)
        ctx = orch.start_run(run_id=run_id, scope=scope_authorization, run_scope=run_scope_factory())
        outcome = ctx.run_specialist_action(
            action_factory(action_type="specialist_investigation", target="idor_v1", parameters={}),
            evidence_context={"mapped_endpoints": []},
            judge_routing_record_id="j1",
        )
        assert outcome.was_authorized
        assert outcome.output is not None
        assert outcome.output.trust_classification == TrustClassification.CANDIDATE_FINDING
        assert outcome.output.replication_command == _VALID_POC_PAYLOAD["replication_command"]
        assert outcome.output.provenance.model_id == "cand-specialist"

    def test_unregistered_skill_denied(self, run_context, action_factory):
        outcome = run_context.run_specialist_action(
            action_factory(action_type="specialist_investigation", target="ssrf_v1", parameters={}),
            evidence_context={},
            judge_routing_record_id="j1",
        )
        assert not outcome.was_authorized
        assert outcome.rejected.reason_code == "skill_registry_rejection"

    def test_specialist_invocation_does_not_pass_through_scope_gate(self, run_context, action_factory, mock_tool_backend):
        run_context.run_specialist_action(
            action_factory(action_type="specialist_investigation", target="idor_v1", parameters={}),
            evidence_context={},
            judge_routing_record_id="j1",
        )
        assert mock_tool_backend.calls == []


class TestReplicationCommandRequirement:
    def test_missing_replication_command_never_produces_a_candidate_finding(
        self, orchestrator_factory, run_id, scope_authorization, run_scope_factory, action_factory, model_registry
    ):
        payload = dict(_VALID_POC_PAYLOAD)
        payload["replication_command"] = ""
        registry, adapter = runtime_registry_with_scripted(
            model_registry, candidate_id="cand-specialist", results=[structured_success(payload)]
        )
        orch = orchestrator_factory(runtime_registry=registry)
        ctx = orch.start_run(run_id=run_id, scope=scope_authorization, run_scope=run_scope_factory())
        outcome = ctx.run_specialist_action(
            action_factory(action_type="specialist_investigation", target="idor_v1", parameters={}),
            evidence_context={},
            judge_routing_record_id="j1",
        )
        assert outcome.output is None
        assert outcome.failure.failure_type == "schema_invalid"

    def test_never_promotes_past_candidate_finding(
        self, orchestrator_factory, run_id, scope_authorization, run_scope_factory, action_factory, model_registry
    ):
        registry, adapter = runtime_registry_with_scripted(
            model_registry, candidate_id="cand-specialist", results=[structured_success(_VALID_POC_PAYLOAD)]
        )
        orch = orchestrator_factory(runtime_registry=registry)
        ctx = orch.start_run(run_id=run_id, scope=scope_authorization, run_scope=run_scope_factory())
        outcome = ctx.run_specialist_action(
            action_factory(action_type="specialist_investigation", target="idor_v1", parameters={}),
            evidence_context={},
            judge_routing_record_id="j1",
        )
        # trust_classification is structurally pinned by the schema
        # itself (SpecialistPoCOutput, trackA/schemas/skills.py) —
        # nothing here can even construct a VALIDATED_FINDING-classified
        # record. This test documents that guarantee at the call site
        # this context actually built.
        assert outcome.output.trust_classification == TrustClassification.CANDIDATE_FINDING
        assert not hasattr(outcome.output, "reviewer_action")
