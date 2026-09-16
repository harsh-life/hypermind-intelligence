"""The Tool Executor. Context-5 task brief §4/§13/§14.

Turns an *already-authorized* `ToolExecutionRequest` into a captured
`ToolExecutionResult` + `RawToolOutput` pair (docs/02_COMPONENT_SPECS.md
§12, Docker Tool Execution Engine), using the existing Tool Registry
(trackA.registries.tools.ToolRegistry, Context 2) and a pluggable
`ToolBackend` (trackA.execution.backends, this context).

This module deliberately knows nothing about the Scope Gate, RunScope, or
`OrchestratorAction` — request-level authorization is a distinct,
upstream concern (trackA.orchestrator, Context 5's own orchestration
layer built on top of Context 3's Scope Gate), never re-implemented or
duplicated here (task brief §5: "Do not implement a second authorization
mechanism"). What this module DOES still own, and enforces unconditionally
regardless of what called it, is the Tool Registry's own membership/
lifecycle gate (task brief §4: "Unknown/unregistered tools must fail
closed... Registry membership ≠ execution authorization" — the converse
is equally true and enforced here: NOT being registered/active always
blocks execution, even if some future caller forgot to check first).
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from trackA.execution.backends import ToolBackend
from trackA.registries.errors import InactiveEntryError, RegistryError, StageNotAllowedError, UnknownIdError
from trackA.registries.tools import ToolRegistry
from trackA.schemas.base import HypermindModel
from trackA.schemas.common import PipelineStage, Provenance
from trackA.schemas.tools import RawToolOutput, ToolExecutionRequest, ToolExecutionResult


class ToolInvocationRecord(HypermindModel):
    """The executor's own explicit record of one invocation attempt —
    tool identity/version, the input it ran with, execution metadata, the
    result, and the output (task brief §4's field list, minus
    "authorization context"/"scope decision": those belong to the caller
    that authorized the request in the first place, trackA.orchestrator,
    and are attached there rather than duplicated here — see that
    module's `ToolActionOutcome`, which composes this record together
    with the authorization/scope-decision context).
    """

    tool_id: str
    tool_version: str
    parameters: Dict[str, Any]
    result: ToolExecutionResult
    raw_output: Optional[RawToolOutput] = None


class RegistryRejectedInvocation(RegistryError):
    """Raised by `ToolExecutor.execute` when the Tool Registry itself
    blocks the invocation (unregistered tool_id, inactive
    `validation_status`, or a stage the tool does not allow) — wraps
    whichever specific `trackA.registries.errors` exception the registry
    raised, so a caller can catch one type for "the registry said no"
    while `__cause__` still preserves exactly why (mirrors
    `trackA.registries.errors.validate_manifest`'s own wrap-don't-swallow
    pattern).
    """


class ToolExecutor:
    """Resolves `request.tool_id` against the Tool Registry, dispatches
    to the configured `ToolBackend`, and wraps the result into the
    pipeline's own `ToolExecutionResult`/`RawToolOutput` schemas.

    One backend per executor, injected (task brief §12: "make the
    container dependency replaceable at the abstraction boundary") —
    deliberately not a `RuntimeRegistry`-style per-candidate dispatch
    table: every tool in docs/06_TOOL_REGISTRY_README.md runs through the
    same isolation mechanism (docs/07_DOCKER_SPEC_README.md's container
    policy applies uniformly), so there is exactly one execution
    environment to swap, not one per tool. A caller that genuinely needs
    per-tool backends can compose multiple `ToolExecutor` instances (one
    per backend) rather than this class growing a second dispatch
    mechanism to parallel `RuntimeRegistry`'s.
    """

    def __init__(self, *, tool_registry: ToolRegistry, backend: ToolBackend) -> None:
        self._tool_registry = tool_registry
        self._backend = backend

    def execute(
        self,
        request: ToolExecutionRequest,
        *,
        stage: str = "tool_execution",
    ) -> ToolInvocationRecord:
        """Raises `RegistryRejectedInvocation` for any Tool Registry
        rejection (unregistered / inactive / stage-not-allowed) —
        *before* the backend is ever invoked, so an unregistered tool_id
        can never reach a real execution environment regardless of what
        the caller already checked (task brief §4, fail-closed).

        A *backend-level* failure (timeout/crash/resource exhaustion) is
        never raised — it comes back as an ordinary
        `ToolInvocationRecord` whose `result.exit_status` reflects it and
        whose `raw_output` is `None`, exactly mirroring
        `InferenceAdapter.infer`'s "uniform failure shape, no exception
        for a domain-level failure" convention already established for
        the model-runtime layer (trackA.models.runtime).
        """
        try:
            manifest = self._tool_registry.lookup(request.tool_id)
            self._tool_registry.validate_invocation(request.tool_id, stage=stage)
        except (UnknownIdError, InactiveEntryError, StageNotAllowedError) as exc:
            raise RegistryRejectedInvocation(
                f"Tool Registry rejected invocation of {request.tool_id!r}: {exc}"
            ) from exc

        backend_result = self._backend.execute(
            tool_id=manifest.tool_id,
            container_image=manifest.container_image,
            parameters=request.parameters,
            timeout_seconds=manifest.timeout_seconds,
        )

        result_provenance = Provenance(
            run_id=request.provenance.run_id,
            stage=PipelineStage.TOOL_EXECUTION,
            source_component="Tool Executor",
            tool_id=manifest.tool_id,
            tool_version=manifest.version,
        )

        raw_output: Optional[RawToolOutput] = None
        raw_output_record_id: Optional[str] = None
        if backend_result.exit_status == "success":
            raw_output = RawToolOutput(
                provenance=Provenance(
                    run_id=request.provenance.run_id,
                    stage=PipelineStage.TOOL_EXECUTION,
                    source_component="Tool Executor",
                    tool_id=manifest.tool_id,
                    tool_version=manifest.version,
                ),
                content=backend_result.output,
                truncated=backend_result.truncated,
            )
            raw_output_record_id = raw_output.provenance.record_id

        result = ToolExecutionResult(
            provenance=result_provenance,
            request_record_id=request.provenance.record_id,
            exit_status=backend_result.exit_status,
            duration_ms=backend_result.duration_ms,
            raw_output_record_id=raw_output_record_id,
        )

        return ToolInvocationRecord(
            tool_id=manifest.tool_id,
            tool_version=manifest.version,
            parameters=dict(request.parameters),
            result=result,
            raw_output=raw_output,
        )
