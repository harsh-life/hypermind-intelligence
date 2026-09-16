"""The pluggable tool-execution backend contract. Context-5 task brief
§11/§12.

Mirrors `trackA.models.runtime.InferenceAdapter`'s established pattern
deliberately (same package already sets this precedent for "the pluggable
backend contract" shape): an abstract `execute()` method, a `backend`
class-level identifier string, and a trivial concrete adapter
(`MockToolBackend`, analogous to `MockAdapter`) that proves the contract
end-to-end without any real external dependency.

What this module is explicitly NOT:

    - A Docker/container orchestration system. docs/07_DOCKER_SPEC_
      README.md describes real isolation requirements (read-only rootfs,
      tmpfs scratch, resource limits, dual timeouts, pinned digests) —
      none of that is implemented here. What *is* built is the
      replaceable abstraction boundary a future `DockerToolBackend`
      would implement (`ToolBackend.execute`): the executor
      (trackA.execution.tools.ToolExecutor) that calls it neither knows
      nor cares whether the concrete backend is a container, a
      subprocess, or (as today) an in-memory mock. Building the real
      Docker backend is explicitly out of this context's scope (task
      brief §12: "Do not build a full production container orchestration
      system"; §25: tests "must NOT depend on ... Docker Desktop
      availability").
    - A network-layer containment mechanism. Request-level Scope Gate
      authorization (trackA.policy.scope_gate, Context 3) and tool
      *execution* isolation are separate layers (task brief §11) — this
      module is purely the latter, and claims nothing about the former.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, ClassVar, Dict, Literal, Optional

from pydantic import model_validator

from trackA.schemas.base import HypermindModel

ExitStatus = Literal["success", "timeout", "crash", "resource_exhausted"]

# Documentation only, mirroring trackA.models.runtime.KNOWN_BACKENDS's
# precedent — nothing here rejects an unlisted backend name.
KNOWN_TOOL_BACKENDS = frozenset({"mock", "docker", "subprocess", "remote_api"})


class ToolBackendResult(HypermindModel):
    """What a `ToolBackend.execute()` call returns — backend-agnostic,
    not yet wrapped into the pipeline's own `ToolExecutionResult`/
    `RawToolOutput` schemas (that wrapping is
    `trackA.execution.tools.ToolExecutor`'s job, mirroring how
    `trackA.models.runtime.InferenceResult` is "raw model output, not yet
    validated" — the same "backend returns a plain result, the calling
    component does the schema work" convention already established for
    the model-runtime layer in this codebase).
    """

    exit_status: ExitStatus
    output: str = ""
    truncated: bool = False
    duration_ms: int = 0
    error: Optional[str] = None

    @model_validator(mode="after")
    def _validate(self) -> "ToolBackendResult":
        if self.duration_ms < 0:
            raise ValueError("ToolBackendResult.duration_ms must be >= 0")
        if self.exit_status != "success" and not self.error:
            raise ValueError(
                "ToolBackendResult.error is required when exit_status != 'success'"
            )
        return self


class ToolBackend(ABC):
    """The pluggable execution-environment contract. A concrete backend
    (a real container runtime, a real subprocess sandbox, a remote
    execution API) is future, separate work — see module docstring; only
    the interface and `MockToolBackend` exist here.
    """

    backend: ClassVar[str]

    @abstractmethod
    def execute(
        self,
        *,
        tool_id: str,
        container_image: str,
        parameters: Dict[str, Any],
        timeout_seconds: int,
    ) -> ToolBackendResult:
        """Run one tool invocation. Implementations must never raise for
        a tool-side failure (timeout, crash, resource exhaustion) — they
        return a `ToolBackendResult(exit_status=..., error=...)` instead,
        so callers have one uniform failure shape regardless of backend
        (mirrors `InferenceAdapter.infer`'s documented contract exactly).
        An implementation *may* still raise for a genuine adapter-usage
        error (e.g. a malformed backend-specific parameter)."""
        raise NotImplementedError


class MockToolBackend(ToolBackend):
    """A deterministic, in-memory backend for tests and local
    development wiring — never intended for anything beyond that (same
    role `MockAdapter` plays for the model-runtime layer).

    `canned_outputs` maps `tool_id -> output text` for tests that need a
    specific, deterministic tool output (e.g. to exercise Trust-Boundary-B
    handling of adversarial content embedded in tool output). Any
    `tool_id` not present in the map falls back to `default_output`.
    `failing_tools` maps `tool_id -> ToolBackendResult` for tests that
    need to exercise a specific failure mode (timeout/crash/
    resource_exhausted) deterministically, without any real environment
    ever actually timing out or crashing.
    """

    backend = "mock"

    def __init__(
        self,
        *,
        canned_outputs: Optional[Dict[str, str]] = None,
        failing_tools: Optional[Dict[str, ToolBackendResult]] = None,
        default_output: str = "mock tool output",
    ) -> None:
        self._canned_outputs = dict(canned_outputs or {})
        self._failing_tools = dict(failing_tools or {})
        self._default_output = default_output
        self.calls: list[Dict[str, Any]] = []

    def execute(
        self,
        *,
        tool_id: str,
        container_image: str,
        parameters: Dict[str, Any],
        timeout_seconds: int,
    ) -> ToolBackendResult:
        # Recorded unconditionally, including for tool_ids that go on to
        # "fail" below — tests assert against `.calls` to prove (or
        # disprove) that execution was ever attempted at all, which is
        # exactly the observable the Scope-Gate-bypass adversarial tests
        # need (trackA/orchestrator's tests): "the executor was never
        # invoked" must be checkable independent of the outcome.
        self.calls.append(
            {
                "tool_id": tool_id,
                "container_image": container_image,
                "parameters": dict(parameters),
                "timeout_seconds": timeout_seconds,
            }
        )
        if tool_id in self._failing_tools:
            return self._failing_tools[tool_id]
        return ToolBackendResult(
            exit_status="success",
            output=self._canned_outputs.get(tool_id, self._default_output),
            duration_ms=1,
        )
