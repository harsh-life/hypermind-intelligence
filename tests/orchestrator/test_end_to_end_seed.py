"""End-to-end integration over the REAL shipped seed manifests.

Every other orchestrator test builds its registries from synthetic
`tests/registries/conftest` dict-factories. This module deliberately loads
the actual `trackA/registries/data/` seed files through the real
`from_directory` loaders and wires them through the real Orchestrator,
Scope Gate, Tool Executor, RoleResolver and RuntimeRegistry — so a break
in the shipped configuration, or in any A->B seam between these
subsystems, is caught here rather than only in isolation.

Two things this file proves that no other test did:

1. The shipped seed data actually runs through the whole control flow
   without an unhandled exception — including the architecturally-correct
   state where a role has candidates but none approved yet (docs/13 OD-27:
   a model earns `approved` only via benchmarking; Judge identity is
   UNDECIDED in docs/08). That state must surface as a clean failure
   outcome, never a crash. (Regression for the NoApprovedCandidateError
   escaping `run_judge`/`run_specialist_action`/`run_worker_action`.)

2. The complete golden path — MODEL PROPOSES -> SCOPE DECIDES -> TOOL
   EXECUTES -> RAW_OBSERVATION -> MODEL_INTERPRETATION -> CANDIDATE_FINDING
   -> (human validation boundary, never crossed automatically) — runs to a
   CANDIDATE_FINDING when, and only when, an approved model exists for the
   role, and never produces a VALIDATED_FINDING on its own.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

import pytest

from tests.orchestrator.conftest import (
    ScriptedAdapter,
    structured_success,
)
from tests.registries.conftest import model_manifest_data
from trackA.execution.backends import MockToolBackend
from trackA.execution.tools import ToolExecutor
from trackA.models.runtime import InferenceResult, MockAdapter, ModelBinding, RuntimeRegistry
from trackA.orchestrator.run import Orchestrator
from trackA.policy.scope_gate import ScopeGate
from trackA.registries.models import ModelRegistry
from trackA.registries.resolution import RoleResolver
from trackA.registries.skills import SkillRegistry
from trackA.registries.tools import ToolRegistry
from trackA.registries.workers import WorkerRegistry
from trackA.schemas.common import PipelineStage, Provenance, TrustClassification
from trackA.schemas.orchestrator import OrchestratorAction
from trackA.schemas.scope import RunScope, ScopeAuthorization, ScopeDecision, ScopeRequest

SEED = Path(__file__).resolve().parents[2] / "trackA" / "registries" / "data"
RUN_ID = "77777777-7777-4777-8777-777777777777"


def _scope_authorization(run_id: str = RUN_ID) -> ScopeAuthorization:
    request = ScopeRequest(
        provenance=Provenance(run_id=run_id, stage=PipelineStage.SCOPE_GATE, source_component="test"),
        target_identifier="example.com",
        authorization_reference="https://bugcrowd.com/example-program/scope",
        requested_by="harsh",
    )
    decision = ScopeDecision(
        provenance=Provenance(run_id=run_id, stage=PipelineStage.SCOPE_GATE, source_component="test"),
        request_record_id=request.provenance.record_id,
        decision="allow",
        reason="in scope",
        policy_version="v1",
    )
    return ScopeAuthorization(request=request, decision=decision)


def _run_scope(run_id: str = RUN_ID) -> RunScope:
    return RunScope(
        run_id=run_id,
        authorization_reference="https://bugcrowd.com/example-program/scope",
        allowed_domains=["example.com"],
        allowed_subdomains=["*.example.com"],
        established_by="harsh",
    )


def _build_orchestrator(
    *,
    extra_approved: Optional[List[dict]] = None,
    scripted: Optional[Dict[str, List[InferenceResult]]] = None,
):
    """Wire an Orchestrator from the real seed registries.

    `extra_approved` — additional ModelManifest dicts to register (e.g. a
    post-benchmark approved judge/specialist candidate, simulating the
    human approval docs/13 OD-27 requires before a role can run live).
    `scripted` — per-candidate_id scripted InferenceResults; any candidate
    not listed is bound to the plain MockAdapter.
    """
    tool_registry = ToolRegistry.from_directory(SEED / "tools")
    worker_registry = WorkerRegistry.from_directory(SEED / "workers")
    skill_registry = SkillRegistry.from_directory(SEED / "skills")
    model_registry = ModelRegistry.from_directory(SEED / "models")
    for extra in extra_approved or []:
        model_registry.register_from_dict(extra)

    runtime = RuntimeRegistry(model_registry=model_registry)
    runtime.register_adapter(MockAdapter())
    scripted = scripted or {}
    for candidate in model_registry.all():
        if candidate.candidate_id in scripted:
            adapter = ScriptedAdapter(scripted[candidate.candidate_id])
            adapter.backend = f"scripted-{candidate.candidate_id}"
            runtime.register_adapter(adapter)
            runtime.bind(ModelBinding(candidate_id=candidate.candidate_id, backend=adapter.backend))
        else:
            runtime.bind(ModelBinding(candidate_id=candidate.candidate_id, backend="mock"))

    orchestrator = Orchestrator(
        tool_registry=tool_registry,
        worker_registry=worker_registry,
        skill_registry=skill_registry,
        model_registry=model_registry,
        role_resolver=RoleResolver(model_registry),
        runtime_registry=runtime,
        scope_gate=ScopeGate(),
        tool_executor=ToolExecutor(
            tool_registry=tool_registry,
            backend=MockToolBackend(canned_outputs={"subfinder": "api.example.com\nsub2.example.com"}),
        ),
    )
    return orchestrator


def _action(action_type: str, target: str, parameters: dict) -> OrchestratorAction:
    return OrchestratorAction(
        provenance=Provenance(
            run_id=RUN_ID,
            stage=PipelineStage.ORCHESTRATOR,
            source_component="planner (test)",
            model_id="planner-model",
            model_version="v1",
        ),
        proposed_action_type=action_type,
        target_registry_id=target,
        proposed_parameters=parameters,
        session_action_count=1,
    )


class TestSeedDataRunsCoherently:
    def test_tool_then_worker_golden_path_with_seed_data(self):
        """subfinder (active seed tool) executes and yields a
        RAW_OBSERVATION; the endpoint_mapper worker (whose role HAS an
        approved seed candidate) then produces a MODEL_INTERPRETATION —
        the first two rungs of the evidence ladder, entirely on seed data.
        """
        orch = _build_orchestrator()
        ctx = orch.start_run(run_id=RUN_ID, scope=_scope_authorization(), run_scope=_run_scope())

        tool = ctx.execute_tool_action(_action("tool_execution", "subfinder", {"domain": "example.com"}))
        assert tool.was_authorized
        assert tool.invocation is not None
        assert tool.invocation.raw_output is not None
        assert tool.invocation.raw_output.trust_classification == TrustClassification.RAW_OBSERVATION

        worker = ctx.run_worker_action(
            _action("worker_invocation", "endpoint_mapper_v1", {}),
            payload={"entities": [{"type": "endpoint", "value": "/api/v1/users/{id}"}]},
            source_extractor_record_id=tool.invocation.raw_output.provenance.record_id,
        )
        assert worker.was_authorized
        assert worker.output is not None
        assert worker.output.trust_classification == TrustClassification.MODEL_INTERPRETATION
        assert worker.output.provenance.run_id == RUN_ID

    def test_judge_without_approved_candidate_fails_cleanly_not_crash(self):
        """Regression: the seed `judge` role has only a `candidate` model
        (never approved — Judge identity is UNDECIDED, docs/08). run_judge
        must return a clean unreachable_dependency failure, not raise
        NoApprovedCandidateError."""
        orch = _build_orchestrator()
        ctx = orch.start_run(run_id=RUN_ID, scope=_scope_authorization(), run_scope=_run_scope())
        outcome = ctx.run_judge(worker_output_record_ids=["w1"], accumulated_evidence={})
        assert outcome.decision is None
        assert outcome.failure is not None
        assert outcome.failure.failure_type == "unreachable_dependency"

    def test_specialist_without_approved_candidate_fails_cleanly_and_yields_no_finding(self):
        """Regression: both seed `specialist` candidates are unapproved.
        run_specialist_action must fail cleanly AND, crucially, produce no
        CANDIDATE_FINDING when there is no approved model to produce it."""
        orch = _build_orchestrator()
        ctx = orch.start_run(run_id=RUN_ID, scope=_scope_authorization(), run_scope=_run_scope())
        outcome = ctx.run_specialist_action(
            _action("specialist_investigation", "idor_v1", {}),
            evidence_context={"endpoints": ["/api/v1/users/{id}"]},
            judge_routing_record_id="j1",
        )
        assert outcome.was_authorized  # skill registry lookup + resolve attempt happened
        assert outcome.output is None  # no candidate finding fabricated
        assert outcome.failure is not None
        assert outcome.failure.failure_type == "unreachable_dependency"


class TestFullGoldenPathToCandidateFinding:
    """The complete flow, exercised when a human HAS approved a model for
    the judge and specialist roles (post-benchmark, docs/13 OD-27). Seed
    registries throughout; only the model-approval state is advanced, which
    is exactly the one thing OD-27 says a human does after benchmarking.
    """

    def _judge_payload(self):
        return {
            "decision": "route_to_skill",
            "target_skill_id": "idor_v1",
            "reasoning": "object-reference pattern is consistent with IDOR prerequisites",
            "confidence": 0.72,
        }

    def _specialist_payload(self):
        return {
            "vulnerability_claim": "GET /api/v1/users/{id} returns other users' data without an ownership check",
            "replication_command": "curl -H 'Authorization: Bearer <A>' https://api.example.com/api/v1/users/1043",
            "supporting_evidence": {"request": "...", "response_snippet": "...", "comparison_context": "..."},
            "specialist_confidence": 0.66,
        }

    def _approved_models(self):
        return [
            model_manifest_data(
                candidate_id="approved-judge",
                model_identity="Qwen2.5-14B",
                intended_worker_role="judge",
                approval_status="approved",
                output_schema_compatibility="json_mode",
            ),
            model_manifest_data(
                candidate_id="approved-specialist",
                model_identity="Qwen2.5-14B",
                intended_worker_role="specialist",
                approval_status="approved",
                output_schema_compatibility="json_mode",
            ),
        ]

    def test_pipeline_reaches_candidate_finding_and_stops_there(self):
        orch = _build_orchestrator(
            extra_approved=self._approved_models(),
            scripted={
                "approved-judge": [structured_success(self._judge_payload())],
                "approved-specialist": [structured_success(self._specialist_payload())],
            },
        )
        ctx = orch.start_run(run_id=RUN_ID, scope=_scope_authorization(), run_scope=_run_scope())

        # 1-9: tool -> RAW_OBSERVATION
        tool = ctx.execute_tool_action(_action("tool_execution", "subfinder", {"domain": "example.com"}))
        assert tool.was_authorized and tool.invocation.raw_output is not None

        # 10-11 (worker): MODEL_INTERPRETATION
        worker = ctx.run_worker_action(
            _action("worker_invocation", "endpoint_mapper_v1", {}),
            payload={"entities": [{"type": "endpoint", "value": "/api/v1/users/{id}"}]},
            source_extractor_record_id=tool.invocation.raw_output.provenance.record_id,
        )
        assert worker.output is not None

        # Judge routes to the IDOR skill.
        judge = ctx.run_judge(
            worker_output_record_ids=[worker.output.provenance.record_id],
            accumulated_evidence={"endpoints": ["/api/v1/users/{id}"]},
        )
        assert judge.decision is not None
        assert judge.decision.decision == "route_to_skill"
        assert judge.decision.target_skill_id == "idor_v1"

        # Specialist produces a CANDIDATE_FINDING — and stops there.
        specialist = ctx.run_specialist_action(
            _action("specialist_investigation", "idor_v1", {}),
            evidence_context={"endpoints": ["/api/v1/users/{id}"]},
            judge_routing_record_id=judge.decision.provenance.record_id,
        )
        assert specialist.output is not None
        assert specialist.output.trust_classification == TrustClassification.CANDIDATE_FINDING
        assert specialist.output.replication_command  # non-empty, schema-enforced

        # 12-14: provenance links the whole trajectory to one run; the
        # finalized artifact contains NO validated finding — the human
        # validation boundary is never crossed automatically.
        artifact = ctx.finalize()
        assert artifact.run_id == RUN_ID
        dumped = artifact.model_dump_json()
        assert "VALIDATED_FINDING" not in dumped
        for record_id_carrier in (
            tool.invocation.raw_output,
            worker.output,
            judge.decision,
            specialist.output,
        ):
            assert record_id_carrier.provenance.run_id == RUN_ID

    def test_no_orchestrator_path_emits_a_validated_finding(self):
        """Structural: TrustClassification.VALIDATED_FINDING must never
        appear anywhere in a finalized run artifact — the Orchestrator has
        no code path that promotes a candidate to validated (that is the
        human validation boundary, docs/13 OD-06)."""
        orch = _build_orchestrator(
            extra_approved=self._approved_models(),
            scripted={
                "approved-judge": [structured_success(self._judge_payload())],
                "approved-specialist": [structured_success(self._specialist_payload())],
            },
        )
        ctx = orch.start_run(run_id=RUN_ID, scope=_scope_authorization(), run_scope=_run_scope())
        ctx.execute_tool_action(_action("tool_execution", "subfinder", {"domain": "example.com"}))
        ctx.run_specialist_action(
            _action("specialist_investigation", "idor_v1", {}),
            evidence_context={},
            judge_routing_record_id="j1",
        )
        artifact = ctx.finalize()
        assert "VALIDATED_FINDING" not in artifact.model_dump_json()
