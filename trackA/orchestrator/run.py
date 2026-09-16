"""The Orchestrator and its per-run execution context. Context-5 task
brief §3/§5/§7/§8/§10/§16/§17/§18/§21.

Implements docs/02_COMPONENT_SPECS.md §11's Orchestrator/Planner, scoped
to what the task brief actually asks for: a bounded, deterministic
check-chain over an already-existing `OrchestratorAction` (the "model
proposes" record, docs/03 §2.3, unmodified) — never the planning LLM
itself, which is out of scope (the model's *proposal* is a caller-
supplied input to this module, exactly like every other document in this
package treats `OrchestratorAction` as something a caller already has).

The check chain, in the order docs/02 §11 specifies (schema -> scope ->
registry -> stage -> worker/skill -> resource -> EXECUTE), narrowed to
what actually applies per `proposed_action_type`:

    tool_execution:            schema, scope (Scope Gate), tool registry
                                (existence + active + stage), resource
    worker_invocation:         schema, worker registry (existence),
                                resource
    specialist_investigation:  schema, skill registry (existence, via the
                                caller="specialist_executor" the Skill
                                Registry itself requires — never anything
                                else, see module docstring below), resource

`worker_invocation`/`specialist_investigation` do not pass through the
Scope Gate: Workers and Specialists operate on already-extracted
structured data, not the network (docs/07_DOCKER_SPEC_README.md §7:
"Workers: --network=none — operate on structured JSON only"), so there is
no network-capable operation for the Scope Gate to evaluate. This is a
narrowing of applicability, not a second authorization mechanism replacing
it (task brief §5) — the Scope Gate remains the *only* gate for any
network-capable request, and nothing here ever lets a `tool_execution`
action skip it.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union

from trackA.execution.tools import RegistryRejectedInvocation, ToolExecutor
from trackA.models.runtime import InferenceRequest, InferenceResult, RuntimeRegistry
from trackA.orchestrator.errors import RunTerminatedError
from trackA.orchestrator.inference import classify_result
from trackA.orchestrator.outcomes import (
    JudgeActionOutcome,
    SpecialistActionOutcome,
    ToolActionOutcome,
    WorkerActionOutcome,
)
from trackA.orchestrator.run_artifact import RunArtifact
from trackA.policy.scope_gate import ScopeGate, ScopeGateDecision
from trackA.registries.errors import RegistryError
from trackA.registries.models import ModelRegistry
from trackA.registries.resolution import RoleResolver
from trackA.registries.skills import SPECIALIST_EXECUTOR, SkillRegistry
from trackA.registries.tools import ToolRegistry
from trackA.registries.workers import WorkerRegistry
from trackA.schemas.audit import AuditEvent, FailureEvent
from trackA.schemas.common import PipelineStage, Provenance
from trackA.schemas.execution import AuthorizedAction, OrchestratorRejection
from trackA.schemas.gates import CheckResult
from trackA.schemas.judge import JudgeInput, JudgeRoutingDecision
from trackA.schemas.orchestrator import OrchestratorAction
from trackA.schemas.scope import Run, RunScope, ScopeAuthorization
from trackA.schemas.skills import SpecialistInput, SpecialistPoCOutput
from trackA.schemas.tools import ToolExecutionRequest
from trackA.schemas.workers import WorkerInput, WorkerOutput

_JUDGE_ROLE = "judge"


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _extract_payload(result: InferenceResult) -> Optional[Dict[str, Any]]:
    """The one, documented default strategy for turning a model's raw
    response into a structured payload — "schema validation is the
    calling component's job" (trackA.models.runtime's own docstring).

    Mirrors `trackA.evaluation.harness`'s `final_output` convention
    (result.raw used directly when it's a dict) as the primary path, with
    a `json.loads(output_text)` fallback for adapters that only populate
    `output_text`. Returns `None` — never a best-guess partial object —
    when neither yields a JSON object, so the caller can treat that
    uniformly as "malformed output, do not propagate"
    (docs/02_COMPONENT_SPECS.md §13's Extractor rule, applied at this
    layer to every model-backed stage alike).
    """
    if isinstance(result.raw, dict):
        return result.raw
    if result.output_text:
        try:
            parsed = json.loads(result.output_text)
        except (TypeError, ValueError):
            return None
        return parsed if isinstance(parsed, dict) else None
    return None


class Orchestrator:
    """Shared, run-independent machinery: registries, the Scope Gate, the
    Tool Executor, the runtime dispatch table. Constructed once; every
    run gets its own `RunContext` (`start_run`) holding only that run's
    mutable, session-scoped state (docs/02 §11 State: "session-scoped
    state only for the duration of a single target's run ... discarded at
    run end, not persisted as memory").
    """

    def __init__(
        self,
        *,
        tool_registry: ToolRegistry,
        worker_registry: WorkerRegistry,
        skill_registry: SkillRegistry,
        model_registry: ModelRegistry,
        role_resolver: RoleResolver,
        runtime_registry: RuntimeRegistry,
        scope_gate: ScopeGate,
        tool_executor: ToolExecutor,
        max_actions_per_run: int = 1000,
        max_specialist_retries: int = 2,
        max_judge_retries: int = 2,
    ) -> None:
        # All operational bounds below default to a configurable number,
        # never a value docs/13_OPEN_DECISIONS.md's OD-02 has actually
        # locked (OD-02 [LOCKED]: "Do not ratify the proposed per-
        # component default numbers yet ... values are established and
        # tuned from real execution results, not predefined arbitrarily")
        # — every one is a constructor parameter precisely so a caller
        # can override it once real numbers exist, never a hardcoded
        # production constant (task brief §17/§21). `WorkerManifest.
        # retry_limit`, by contrast, IS a canonical, per-manifest-authored
        # value (docs/03 §2.10, [LOCKED]) and is used as-is wherever a
        # worker is actually invoked, never overridden by any number here.
        if max_actions_per_run < 1:
            raise ValueError("Orchestrator.max_actions_per_run must be >= 1")
        self.tool_registry = tool_registry
        self.worker_registry = worker_registry
        self.skill_registry = skill_registry
        self.model_registry = model_registry
        self.role_resolver = role_resolver
        self.runtime_registry = runtime_registry
        self.scope_gate = scope_gate
        self.tool_executor = tool_executor
        self.max_actions_per_run = max_actions_per_run
        self.max_specialist_retries = max_specialist_retries
        self.max_judge_retries = max_judge_retries

    def start_run(
        self, *, run_id: str, scope: ScopeAuthorization, run_scope: Optional[RunScope] = None
    ) -> "RunContext":
        run = Run(run_id=run_id, scope=scope, run_scope=run_scope)
        return RunContext(orchestrator=self, run=run)


class RunContext:
    """One run's live, mutable, session-scoped state — never shared
    across runs, never persisted as memory, discarded (after an optional
    final write via `finalize()`) at run end (docs/02 §11 State).
    """

    def __init__(self, *, orchestrator: Orchestrator, run: Run) -> None:
        self._orch = orchestrator
        self.run = run
        self._actions_proposed = 0
        self._terminated = False

        self.audit_events: List[AuditEvent] = []
        self.failure_events: List[FailureEvent] = []
        self.tool_actions: List[ToolActionOutcome] = []
        self.worker_actions: List[WorkerActionOutcome] = []
        self.specialist_actions: List[SpecialistActionOutcome] = []
        self.judge_actions: List[JudgeActionOutcome] = []

    # -- bookkeeping ---------------------------------------------------

    def _require_not_terminated(self) -> None:
        if self._terminated:
            raise RunTerminatedError(
                f"run {self.run.run_id!r} has already been finalized — no "
                f"further actions may be proposed or executed against it"
            )

    def _emit_audit(self, event_type: str, *, detail: Dict[str, Any], related_record_ids: List[str]) -> None:
        self.audit_events.append(
            AuditEvent(
                provenance=Provenance(
                    run_id=self.run.run_id,
                    stage=PipelineStage.ORCHESTRATOR,
                    source_component="Orchestrator",
                ),
                event_type=event_type,
                detail=detail,
                related_record_ids=related_record_ids,
            )
        )

    def _record_failure(
        self,
        *,
        stage: PipelineStage,
        failure_type: str,
        detail: str,
        retry_count: int,
    ) -> FailureEvent:
        event = FailureEvent(
            provenance=Provenance(
                run_id=self.run.run_id, stage=stage, source_component="Orchestrator"
            ),
            failure_type=failure_type,
            detail=detail,
            retry_count_at_failure=retry_count,
        )
        self.failure_events.append(event)
        return event

    # -- the check chain (docs/02 §11) ----------------------------------

    def _authorize(
        self, action: OrchestratorAction
    ) -> Tuple[Union[AuthorizedAction, OrchestratorRejection], Optional[ScopeGateDecision]]:
        self._require_not_terminated()
        self._actions_proposed += 1

        checks: List[CheckResult] = [CheckResult(check_name="schema_validation", passed=True)]

        def reject(reason: str, reason_code: str) -> Tuple[OrchestratorRejection, Optional[ScopeGateDecision]]:
            rejection = OrchestratorRejection(
                provenance=Provenance(
                    run_id=self.run.run_id,
                    stage=PipelineStage.ORCHESTRATOR,
                    source_component="Orchestrator",
                ),
                source_action_id=action.provenance.record_id,
                checks_performed=list(checks),
                reason=reason,
                reason_code=reason_code,
            )
            self._emit_audit(
                "rejected",
                detail={"reason": reason, "reason_code": reason_code},
                related_record_ids=[action.provenance.record_id],
            )
            return rejection, scope_decision

        scope_decision: Optional[ScopeGateDecision] = None

        # A model can never smuggle an action addressed to a different
        # run into this RunContext (task brief §22's "target expansion
        # attempt" / "duplicate/invalid runtime state" cases start here).
        if action.provenance.run_id != self.run.run_id:
            checks.append(CheckResult(check_name="run_correlation", passed=False))
            return reject(
                f"action.provenance.run_id {action.provenance.run_id!r} does not "
                f"match this run ({self.run.run_id!r})",
                "run_id_mismatch",
            )
        checks.append(CheckResult(check_name="run_correlation", passed=True))

        if action.proposed_action_type == "tool_execution":
            scope_decision = self._orch.scope_gate.authorize_action(action, self.run.run_scope)
            checks.append(CheckResult(check_name="scope_gate", passed=scope_decision.is_allowed))
            if not scope_decision.is_allowed:
                return reject(
                    scope_decision.reason,
                    scope_decision.reason_code.value if scope_decision.reason_code else "scope_denied",
                )
            try:
                self._orch.tool_registry.lookup(action.target_registry_id)
                self._orch.tool_registry.validate_invocation(
                    action.target_registry_id, stage="tool_execution"
                )
                checks.append(CheckResult(check_name="tool_registry", passed=True))
            except RegistryError as exc:
                checks.append(CheckResult(check_name="tool_registry", passed=False))
                return reject(str(exc), "tool_registry_rejection")

        elif action.proposed_action_type == "worker_invocation":
            try:
                self._orch.worker_registry.lookup(action.target_registry_id)
                checks.append(CheckResult(check_name="worker_registry", passed=True))
            except RegistryError as exc:
                checks.append(CheckResult(check_name="worker_registry", passed=False))
                return reject(str(exc), "worker_registry_rejection")

        elif action.proposed_action_type == "specialist_investigation":
            # [LOCKED, docs/02 §3] the ONLY legitimate caller identity for
            # the Skill Registry. Never accepted as a parameter anywhere
            # in this module — see the module/class docstrings.
            try:
                self._orch.skill_registry.lookup(
                    action.target_registry_id, caller=SPECIALIST_EXECUTOR
                )
                checks.append(CheckResult(check_name="skill_registry", passed=True))
            except RegistryError as exc:
                checks.append(CheckResult(check_name="skill_registry", passed=False))
                return reject(str(exc), "skill_registry_rejection")

        # Resource validation (docs/02 §11 step 6): the one bound this
        # context actually enforces for MVP is the configurable per-run
        # action budget (see Orchestrator.__init__'s docstring on why
        # this and every other number here is a constructor parameter,
        # not a canonical constant) — the concrete "bounded orchestration"
        # / loop-prevention mechanism docs/02 §11's State row names but
        # leaves unspecified.
        if self._actions_proposed > self._orch.max_actions_per_run:
            checks.append(CheckResult(check_name="resource_check", passed=False))
            return reject(
                f"run {self.run.run_id!r} has exceeded its configured action "
                f"budget ({self._orch.max_actions_per_run})",
                "action_budget_exhausted",
            )
        checks.append(CheckResult(check_name="resource_check", passed=True))

        authorized = AuthorizedAction(
            provenance=Provenance(
                run_id=self.run.run_id, stage=PipelineStage.ORCHESTRATOR, source_component="Orchestrator"
            ),
            source_action_id=action.provenance.record_id,
            action_type=action.proposed_action_type,
            target_registry_id=action.target_registry_id,
            authorized_parameters=dict(action.proposed_parameters),
            checks_performed=checks,
        )
        self._emit_audit(
            "authorized",
            detail={"action_type": action.proposed_action_type, "target_registry_id": action.target_registry_id},
            related_record_ids=[action.provenance.record_id],
        )
        return authorized, scope_decision

    # -- role invocation (shared by worker/judge/specialist) ------------

    def _invoke_candidate(
        self, candidate_id: str, request: InferenceRequest, *, max_retries: int
    ) -> Tuple[InferenceResult, str, int]:
        retries_used = 0
        result = self._orch.runtime_registry.invoke(candidate_id, request)
        status = classify_result(result)
        # Bounded retry applies only to technical failures. A refusal
        # ends the loop immediately — the very first attempt that comes
        # back "refusal" is the last call this run ever makes for this
        # request (task brief §17 [LOCKED elsewhere in this package,
        # docs/08_MODEL_REGISTRY.md's Failure Policy]: "do NOT retry to
        # defeat the refusal").
        while status == "technical_failure" and retries_used < max_retries:
            retries_used += 1
            result = self._orch.runtime_registry.invoke(candidate_id, request)
            status = classify_result(result)
        return result, status, retries_used

    # -- tool_execution ---------------------------------------------------

    def execute_tool_action(self, action: OrchestratorAction) -> ToolActionOutcome:
        """MODEL REQUEST -> NORMALIZE -> SCOPE GATE -> TOOL REGISTRY ->
        (only if every prior step allowed it) TOOL EXECUTOR. A denial at
        any step means the executor is never called — this is the one
        property every adversarial "scope bypass" / "unauthorized tool"
        test in this context's suite exists to prove.
        """
        authorization, scope_decision = self._authorize(action)
        if isinstance(authorization, OrchestratorRejection):
            outcome = ToolActionOutcome(action=action, rejected=authorization, scope_decision=scope_decision)
            self.tool_actions.append(outcome)
            return outcome

        request = ToolExecutionRequest(
            provenance=Provenance(
                run_id=self.run.run_id, stage=PipelineStage.ORCHESTRATOR, source_component="Orchestrator"
            ),
            tool_id=action.target_registry_id,
            parameters=dict(action.proposed_parameters),
            authorized_by_action_id=authorization.provenance.record_id,
        )
        try:
            invocation = self._orch.tool_executor.execute(request)
        except RegistryRejectedInvocation as exc:
            # Belt-and-suspenders: `_authorize` already checked the Tool
            # Registry, so this should be unreachable in practice, but the
            # Tool Executor enforces its own registry check unconditionally
            # (trackA/execution/tools.py's own module docstring) precisely
            # so it is never the sole line of defense — if it ever *does*
            # fire here, that is a genuine bug worth surfacing as a
            # failure event, not swallowing.
            failure = self._record_failure(
                stage=PipelineStage.TOOL_EXECUTION,
                failure_type="unreachable_dependency",
                detail=f"Tool Executor rejected an already-authorized request: {exc}",
                retry_count=0,
            )
            outcome = ToolActionOutcome(
                action=action, authorized=authorization, scope_decision=scope_decision, failure=failure
            )
            self.tool_actions.append(outcome)
            return outcome

        outcome = ToolActionOutcome(
            action=action, authorized=authorization, scope_decision=scope_decision, invocation=invocation
        )
        self.tool_actions.append(outcome)
        self._emit_audit(
            "gate_passed" if invocation.result.exit_status == "success" else "gate_failed",
            detail={"tool_id": invocation.tool_id, "exit_status": invocation.result.exit_status},
            related_record_ids=[invocation.result.provenance.record_id],
        )
        return outcome

    # -- worker_invocation ------------------------------------------------

    def run_worker_action(
        self, action: OrchestratorAction, *, payload: Dict[str, Any], source_extractor_record_id: str
    ) -> WorkerActionOutcome:
        """Resolves `action.target_registry_id` (a `worker_id`) through
        the Worker Registry, follows its `worker_role_binding` pointer
        through `RoleResolver` to the Model Registry's approved candidate
        for that role, and invokes it via `RuntimeRegistry` — the exact
        `worker_role_binding -> Model Registry / RoleResolver -> runtime
        adapter` chain the task brief §7 specifies, with no model
        identity or backend ever hardcoded in this module.
        """
        authorization, _ = self._authorize(action)
        if isinstance(authorization, OrchestratorRejection):
            outcome = WorkerActionOutcome(action=action, rejected=authorization)
            self.worker_actions.append(outcome)
            return outcome

        worker_manifest = self._orch.worker_registry.lookup(action.target_registry_id)
        candidate = self._orch.role_resolver.resolve_for_worker(worker_manifest)

        # Constructed for provenance/audit completeness (docs/03 §2.11:
        # "Produced by: Worker Execution Framework") even though only its
        # `payload` actually feeds the model call below — the Extractor
        # stage itself is out of Context 5's scope (a future context's
        # job; see this context's completion report), so
        # `source_extractor_record_id` here is whatever upstream record
        # id the caller supplies (typically a RawToolOutput record id
        # when no real ExtractorJSON exists yet), not fabricated.
        WorkerInput(
            provenance=Provenance(run_id=self.run.run_id, stage=PipelineStage.WORKER, source_component="Worker Execution Framework"),
            worker_id=action.target_registry_id,
            payload=payload,
            source_extractor_record_id=source_extractor_record_id,
        )

        request = InferenceRequest(
            role=worker_manifest.worker_role_binding,
            prompt=json.dumps(
                {"system_prompt": worker_manifest.system_prompt, "payload": payload}, sort_keys=True
            ),
            generation_policy={},
        )
        result, status, retries_used = self._invoke_candidate(
            candidate.candidate_id, request, max_retries=worker_manifest.retry_limit
        )

        if status == "refusal":
            failure = self._record_failure(
                stage=PipelineStage.WORKER,
                failure_type="model_refusal",
                detail=result.error or "worker model refused the request",
                retry_count=retries_used,
            )
            outcome = WorkerActionOutcome(action=action, authorized=authorization, failure=failure, retries_used=retries_used)
            self.worker_actions.append(outcome)
            return outcome
        if status == "technical_failure":
            failure = self._record_failure(
                stage=PipelineStage.WORKER,
                failure_type="unreachable_dependency",
                detail=result.error or "worker model call failed after exhausting retries",
                retry_count=retries_used,
            )
            outcome = WorkerActionOutcome(action=action, authorized=authorization, failure=failure, retries_used=retries_used)
            self.worker_actions.append(outcome)
            return outcome

        payload_dict = _extract_payload(result)
        if payload_dict is None:
            failure = self._record_failure(
                stage=PipelineStage.WORKER,
                failure_type="schema_invalid",
                detail="worker output was not a parseable structured payload",
                retry_count=retries_used,
            )
            outcome = WorkerActionOutcome(action=action, authorized=authorization, failure=failure, retries_used=retries_used)
            self.worker_actions.append(outcome)
            return outcome

        output = WorkerOutput(
            provenance=Provenance(
                run_id=self.run.run_id,
                stage=PipelineStage.WORKER,
                source_component="Worker Execution Framework",
                model_id=candidate.candidate_id,
                model_version=candidate.version,
            ),
            worker_id=action.target_registry_id,
            payload=payload_dict,
            retry_count=retries_used,
        )
        outcome = WorkerActionOutcome(action=action, authorized=authorization, output=output, retries_used=retries_used)
        self.worker_actions.append(outcome)
        self._emit_audit(
            "gate_passed",
            detail={"worker_id": action.target_registry_id},
            related_record_ids=[output.provenance.record_id],
        )
        return outcome

    # -- Judge ------------------------------------------------------------

    def run_judge(
        self, *, worker_output_record_ids: List[str], accumulated_evidence: Dict[str, Any]
    ) -> JudgeActionOutcome:
        """[LOCKED, docs/02 §3/§15] The Judge never reaches the Skill
        Registry. This method's own signature is the structural proof:
        it accepts no `skill_id`, no `caller` override, and this module
        contains no code path from here into
        `trackA.registries.skills.SkillRegistry` at all — "enforced by
        omission," restated at the Orchestrator layer exactly as
        docs/02 §3 already enforces it at the registry layer.
        """
        self._require_not_terminated()
        judge_input = JudgeInput(
            provenance=Provenance(run_id=self.run.run_id, stage=PipelineStage.JUDGE, source_component="Orchestrator"),
            worker_output_record_ids=list(worker_output_record_ids),
            accumulated_evidence=accumulated_evidence,
            # contains_skill_content has no other legal value — Literal[False]
            # (trackA/schemas/judge.py) — restated explicitly here anyway so
            # this call site reads as an assertion, not an accident of the
            # schema default.
            contains_skill_content=False,
        )
        candidate = self._orch.role_resolver.resolve(_JUDGE_ROLE)
        request = InferenceRequest(
            role=_JUDGE_ROLE,
            prompt=json.dumps(
                {
                    "worker_output_record_ids": judge_input.worker_output_record_ids,
                    "accumulated_evidence": judge_input.accumulated_evidence,
                },
                sort_keys=True,
            ),
            generation_policy={},
        )
        result, status, retries_used = self._invoke_candidate(
            candidate.candidate_id, request, max_retries=self._orch.max_judge_retries
        )

        if status == "refusal":
            failure = self._record_failure(
                stage=PipelineStage.JUDGE,
                failure_type="model_refusal",
                detail=result.error or "judge model refused the request",
                retry_count=retries_used,
            )
            outcome = JudgeActionOutcome(judge_input=judge_input, failure=failure, retries_used=retries_used)
            self.judge_actions.append(outcome)
            return outcome
        if status == "technical_failure":
            failure = self._record_failure(
                stage=PipelineStage.JUDGE,
                failure_type="unreachable_dependency",
                detail=result.error or "judge model call failed after exhausting retries",
                retry_count=retries_used,
            )
            outcome = JudgeActionOutcome(judge_input=judge_input, failure=failure, retries_used=retries_used)
            self.judge_actions.append(outcome)
            return outcome

        payload_dict = _extract_payload(result)
        decision: Optional[JudgeRoutingDecision] = None
        if payload_dict is not None:
            try:
                decision = JudgeRoutingDecision(
                    provenance=Provenance(
                        run_id=self.run.run_id,
                        stage=PipelineStage.JUDGE,
                        source_component="Neutral Judge",
                        model_id=candidate.candidate_id,
                        model_version=candidate.version,
                    ),
                    **payload_dict,
                )
            except (TypeError, ValueError):
                decision = None

        if decision is None:
            failure = self._record_failure(
                stage=PipelineStage.JUDGE,
                failure_type="schema_invalid",
                detail="judge output was not a parseable JudgeRoutingDecision",
                retry_count=retries_used,
            )
            outcome = JudgeActionOutcome(judge_input=judge_input, failure=failure, retries_used=retries_used)
            self.judge_actions.append(outcome)
            return outcome

        outcome = JudgeActionOutcome(judge_input=judge_input, decision=decision, retries_used=retries_used)
        self.judge_actions.append(outcome)
        self._emit_audit(
            "gate_passed",
            detail={"decision": decision.decision},
            related_record_ids=[decision.provenance.record_id],
        )
        return outcome

    # -- specialist_investigation ------------------------------------------

    def run_specialist_action(
        self, action: OrchestratorAction, *, evidence_context: Dict[str, Any], judge_routing_record_id: str
    ) -> SpecialistActionOutcome:
        """Resolves `action.target_registry_id` (a `skill_id`) through the
        Skill Registry using the ONLY caller identity the registry ever
        accepts for a read (`SPECIALIST_EXECUTOR` — see `_authorize`
        above), follows the resolved `SkillManifest.specialist_role_binding`
        through `RoleResolver`, and invokes it. Stops at `CANDIDATE_FINDING`
        (`SpecialistPoCOutput`) — never further (task brief §19).
        """
        authorization, _ = self._authorize(action)
        if isinstance(authorization, OrchestratorRejection):
            outcome = SpecialistActionOutcome(action=action, rejected=authorization)
            self.specialist_actions.append(outcome)
            return outcome

        skill_manifest = self._orch.skill_registry.lookup(action.target_registry_id, caller=SPECIALIST_EXECUTOR)
        candidate = self._orch.role_resolver.resolve_for_skill(skill_manifest)

        SpecialistInput(
            provenance=Provenance(run_id=self.run.run_id, stage=PipelineStage.SPECIALIST, source_component="Specialist Executor"),
            skill_id=action.target_registry_id,
            evidence_context=evidence_context,
            judge_routing_record_id=judge_routing_record_id,
        )

        request = InferenceRequest(
            role=skill_manifest.specialist_role_binding,
            prompt=json.dumps(
                {"system_prompt": skill_manifest.system_prompt, "evidence_context": evidence_context}, sort_keys=True
            ),
            generation_policy={},
        )
        result, status, retries_used = self._invoke_candidate(
            candidate.candidate_id, request, max_retries=self._orch.max_specialist_retries
        )

        if status == "refusal":
            failure = self._record_failure(
                stage=PipelineStage.SPECIALIST,
                failure_type="model_refusal",
                detail=result.error or "specialist model refused the request",
                retry_count=retries_used,
            )
            outcome = SpecialistActionOutcome(action=action, authorized=authorization, failure=failure, retries_used=retries_used)
            self.specialist_actions.append(outcome)
            return outcome
        if status == "technical_failure":
            failure = self._record_failure(
                stage=PipelineStage.SPECIALIST,
                failure_type="unreachable_dependency",
                detail=result.error or "specialist model call failed after exhausting retries",
                retry_count=retries_used,
            )
            outcome = SpecialistActionOutcome(action=action, authorized=authorization, failure=failure, retries_used=retries_used)
            self.specialist_actions.append(outcome)
            return outcome

        payload_dict = _extract_payload(result)
        output: Optional[SpecialistPoCOutput] = None
        if payload_dict is not None:
            try:
                output = SpecialistPoCOutput(
                    provenance=Provenance(
                        run_id=self.run.run_id,
                        stage=PipelineStage.SPECIALIST,
                        source_component="Specialist Executor",
                        model_id=candidate.candidate_id,
                        model_version=candidate.version,
                    ),
                    skill_id=action.target_registry_id,
                    **payload_dict,
                )
            except (TypeError, ValueError):
                output = None

        if output is None:
            # Covers both "not JSON at all" and "JSON but missing/empty
            # replication_command" — SpecialistPoCOutput's own validator
            # (trackA/schemas/skills.py, [LOCKED]) already refuses to
            # construct without a non-empty replication_command, so that
            # specific, security-relevant omission surfaces here as the
            # exact same schema_invalid failure as any other malformed
            # output, never as a partially-valid candidate.
            failure = self._record_failure(
                stage=PipelineStage.SPECIALIST,
                failure_type="schema_invalid",
                detail="specialist output was not a parseable SpecialistPoCOutput "
                "(or was missing its required non-empty replication_command)",
                retry_count=retries_used,
            )
            outcome = SpecialistActionOutcome(action=action, authorized=authorization, failure=failure, retries_used=retries_used)
            self.specialist_actions.append(outcome)
            return outcome

        outcome = SpecialistActionOutcome(action=action, authorized=authorization, output=output, retries_used=retries_used)
        self.specialist_actions.append(outcome)
        self._emit_audit(
            "gate_passed",
            detail={"skill_id": action.target_registry_id},
            related_record_ids=[output.provenance.record_id],
        )
        return outcome

    # -- termination --------------------------------------------------

    def finalize(self) -> RunArtifact:
        """Marks this run terminated (no further action may be proposed
        or executed against it — `_require_not_terminated` above) and
        returns the run's structured artifact (task brief §3: "producing
        structured run artifacts"). Does NOT write to disk itself —
        writing is an explicit, separate caller decision via
        `trackA.orchestrator.storage.write_run_artifact`, keeping
        `RunContext` usable in tests with no filesystem dependency at
        all.
        """
        self._require_not_terminated()
        self._terminated = True
        return RunArtifact(
            run_id=self.run.run_id,
            started_at=self.run.started_at,
            finalized_at=_now_iso(),
            scope_established=bool(self.run.run_scope and self.run.run_scope.is_established),
            actions_proposed=self._actions_proposed,
            tool_actions=list(self.tool_actions),
            worker_actions=list(self.worker_actions),
            specialist_actions=list(self.specialist_actions),
            judge_actions=list(self.judge_actions),
            audit_events=list(self.audit_events),
            failure_events=list(self.failure_events),
        )

    @property
    def is_terminated(self) -> bool:
        return self._terminated
