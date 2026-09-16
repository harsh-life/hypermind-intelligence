"""Run lifecycle: initialization, resolution, provenance, independent run
artifacts, configurable action budget, and clean termination (task brief
§3/§18/§21/§25)."""
from __future__ import annotations

import pytest

from tests.orchestrator.conftest import make_scope_authorization
from trackA.orchestrator.errors import RunArtifactAlreadyExistsError, RunTerminatedError
from trackA.orchestrator.storage import read_run_artifact, write_run_artifact


class TestRunInitialization:
    def test_start_run_produces_a_fresh_unterminated_context(self, orchestrator, run_id, scope_authorization, run_scope_factory):
        ctx = orchestrator.start_run(run_id=run_id, scope=scope_authorization, run_scope=run_scope_factory())
        assert ctx.run.run_id == run_id
        assert ctx.is_terminated is False
        assert ctx.tool_actions == []
        assert ctx.audit_events == []

    def test_two_runs_from_the_same_orchestrator_do_not_share_state(self, orchestrator, run_scope_factory, action_factory):
        ctx_a = orchestrator.start_run(run_id="run-a", scope=make_scope_authorization("run-a"), run_scope=run_scope_factory(run_id="run-a"))
        ctx_b = orchestrator.start_run(run_id="run-b", scope=make_scope_authorization("run-b"), run_scope=run_scope_factory(run_id="run-b"))
        ctx_a.execute_tool_action(action_factory(provenance_overrides={"run_id": "run-a"}))
        assert len(ctx_a.tool_actions) == 1
        assert len(ctx_b.tool_actions) == 0


class TestProvenanceAndAuditTrail:
    def test_every_authorized_action_emits_an_audit_event(self, run_context, action_factory):
        run_context.execute_tool_action(action_factory())
        assert any(e.event_type == "authorized" for e in run_context.audit_events)

    def test_every_rejection_emits_an_audit_event(self, run_context, action_factory):
        run_context.execute_tool_action(action_factory(parameters={"domain": "not-authorized.org"}))
        assert any(e.event_type == "rejected" for e in run_context.audit_events)

    def test_audit_events_carry_this_runs_run_id(self, run_context, action_factory):
        run_context.execute_tool_action(action_factory())
        assert all(e.provenance.run_id == run_context.run.run_id for e in run_context.audit_events)


class TestActionBudget:
    def test_action_budget_is_configurable_and_enforced(self, orchestrator_factory, run_id, scope_authorization, run_scope_factory, action_factory, runtime_registry):
        orch = orchestrator_factory(runtime_registry=runtime_registry, max_actions_per_run=2)
        ctx = orch.start_run(run_id=run_id, scope=scope_authorization, run_scope=run_scope_factory())
        first = ctx.execute_tool_action(action_factory())
        second = ctx.execute_tool_action(action_factory(parameters={"domain": "not-authorized.org"}))
        third = ctx.execute_tool_action(action_factory())
        assert first.was_authorized
        assert not second.was_authorized  # denied on scope, well within budget
        assert not third.was_authorized
        assert third.rejected.reason_code == "action_budget_exhausted"

    def test_invalid_action_budget_rejected_at_construction(self, orchestrator_factory, runtime_registry):
        with pytest.raises(ValueError):
            orchestrator_factory(runtime_registry=runtime_registry, max_actions_per_run=0)


class TestCleanTermination:
    def test_finalize_produces_a_structured_artifact(self, run_context, action_factory):
        run_context.execute_tool_action(action_factory())
        artifact = run_context.finalize()
        assert artifact.run_id == run_context.run.run_id
        assert artifact.actions_proposed == 1
        assert len(artifact.tool_actions) == 1
        assert artifact.finalized_at

    def test_finalize_marks_the_run_terminated(self, run_context):
        run_context.finalize()
        assert run_context.is_terminated is True

    def test_no_further_actions_after_finalize(self, run_context, action_factory):
        run_context.finalize()
        with pytest.raises(RunTerminatedError):
            run_context.execute_tool_action(action_factory())

    def test_double_finalize_raises(self, run_context):
        run_context.finalize()
        with pytest.raises(RunTerminatedError):
            run_context.finalize()

    def test_worker_and_specialist_and_judge_also_blocked_after_finalize(self, run_context, action_factory):
        run_context.finalize()
        with pytest.raises(RunTerminatedError):
            run_context.run_worker_action(
                action_factory(action_type="worker_invocation", target="endpoint_mapper_v1", parameters={}),
                payload={},
                source_extractor_record_id="r1",
            )
        with pytest.raises(RunTerminatedError):
            run_context.run_judge(worker_output_record_ids=["w1"], accumulated_evidence={})
        with pytest.raises(RunTerminatedError):
            run_context.run_specialist_action(
                action_factory(action_type="specialist_investigation", target="idor_v1", parameters={}),
                evidence_context={},
                judge_routing_record_id="j1",
            )


class TestRunArtifactStorage:
    def test_write_then_read_round_trips(self, run_context, action_factory, tmp_path):
        run_context.execute_tool_action(action_factory())
        artifact = run_context.finalize()
        path = write_run_artifact(tmp_path, artifact)
        assert path.exists()
        reloaded = read_run_artifact(tmp_path, artifact.run_id)
        assert reloaded.run_id == artifact.run_id
        assert reloaded.actions_proposed == artifact.actions_proposed

    def test_write_never_overwrites_an_existing_artifact(self, run_context, action_factory, tmp_path):
        run_context.execute_tool_action(action_factory())
        artifact = run_context.finalize()
        write_run_artifact(tmp_path, artifact)
        with pytest.raises(RunArtifactAlreadyExistsError):
            write_run_artifact(tmp_path, artifact)

    def test_two_runs_write_independent_artifacts(self, orchestrator, run_scope_factory, action_factory, tmp_path):
        ctx_a = orchestrator.start_run(run_id="run-a", scope=make_scope_authorization("run-a"), run_scope=run_scope_factory(run_id="run-a"))
        ctx_b = orchestrator.start_run(run_id="run-b", scope=make_scope_authorization("run-b"), run_scope=run_scope_factory(run_id="run-b"))
        ctx_a.execute_tool_action(action_factory(provenance_overrides={"run_id": "run-a"}))
        artifact_a = ctx_a.finalize()
        artifact_b = ctx_b.finalize()
        write_run_artifact(tmp_path, artifact_a)
        write_run_artifact(tmp_path, artifact_b)
        reloaded_a = read_run_artifact(tmp_path, "run-a")
        reloaded_b = read_run_artifact(tmp_path, "run-b")
        assert reloaded_a.actions_proposed == 1
        assert reloaded_b.actions_proposed == 0
