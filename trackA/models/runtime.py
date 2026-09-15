"""Runtime / inference adapter interface. Context-2 task brief §3.G.

This is the layer between "which model candidate fulfils this role"
(Model Registry, `trackA.registries.models`) and "how do I actually call
that candidate" (a real Ollama HTTP call, a LiteLLM proxy call, a Docker
`exec`, a cloud API request — none of which are implemented here).

Four pieces:

    InferenceRequest / InferenceResult
        Backend-agnostic request/response shapes, matching docs/02
        §5's `infer(role, prompt, generation_policy) -> InferenceResult`
        interface ("InferenceResult — raw model output, not yet
        validated against any schema; schema validation is the calling
        component's job").

    ModelBinding
        Joins one Model Registry candidate (`candidate_id`) to a backend
        identifier and backend-specific connection config. NOT a
        duplicate of `ModelManifest` (docs/08_MODEL_REGISTRY.md,
        Context-1-locked): `ModelManifest.execution_location` is the
        candidate's own static, authored classification
        (`"local" | "remote"`); `ModelBinding` is the separate, later-
        supplied runtime wiring for that candidate — how it's actually
        reached today, which can change without touching the candidate's
        manifest (deployment config, not architecture). This is new
        content this context is explicitly asked to build (task brief
        §3.G), not a parallel representation of an existing concept.

    InferenceAdapter (ABC)
        The pluggable backend contract. `backend` is a deliberately open
        string identifier, not a closed enum — the same extensibility
        rationale already applied elsewhere in this package to
        `ToolManifest.category` and `SkillManifest.vulnerability_class`
        (docs/03 §2.4's note; OD-12). Known, currently-anticipated values
        are listed in `KNOWN_BACKENDS` for documentation only; nothing
        rejects an adapter registered under an unlisted name, so a future
        backend never requires a code change here.

    RuntimeRegistry
        Dispatches an InferenceRequest for a given `candidate_id` to the
        InferenceAdapter registered for that candidate's bound backend.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, ClassVar, Dict, List, Optional

from pydantic import model_validator

from trackA.registries.errors import DuplicateIdError, MissingReferenceError, UnknownIdError, UnsupportedBackendError
from trackA.schemas.base import HypermindModel

# Documentation only — see the module docstring. Not enforced anywhere.
KNOWN_BACKENDS = frozenset({"ollama", "litellm", "http_api", "docker_exec", "mock"})


class InferenceRequest(HypermindModel):
    """docs/02 §5's InferenceRequest(role, prompt, generation_policy)."""

    role: str
    prompt: str
    generation_policy: Dict[str, Any] = {}


class InferenceResult(HypermindModel):
    """docs/02 §5: raw model output, not yet schema-validated — that
    validation is the calling component's job (e.g. the Extractor
    validates its own output against ExtractorJSON), not this layer's."""

    success: bool
    output_text: Optional[str] = None
    raw: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    latency_ms: Optional[float] = None

    @model_validator(mode="after")
    def _error_present_on_failure(self) -> "InferenceResult":
        if not self.success and not self.error:
            raise ValueError("InferenceResult.error is required when success is False")
        return self


class ModelBinding(HypermindModel):
    """Runtime wiring for one Model Registry candidate. See module
    docstring for why this is distinct from `ModelManifest`."""

    candidate_id: str
    backend: str
    connection: Dict[str, Any] = {}


class InferenceAdapter(ABC):
    """The pluggable backend contract. A concrete adapter (a real Ollama
    client, a real LiteLLM client, ...) is later-context work — see the
    package docstring; only the interface and `MockAdapter` (a contract-
    proving stand-in) exist here."""

    backend: ClassVar[str]

    @abstractmethod
    def infer(self, request: InferenceRequest, *, binding: ModelBinding) -> InferenceResult:
        """Run one inference call. Implementations must never raise for a
        model-side failure (timeout, refusal, malformed output) — they
        return an `InferenceResult(success=False, error=...)` instead, so
        callers have one uniform failure shape regardless of backend. An
        implementation *may* still raise for a genuine adapter-usage
        error (e.g. a malformed `binding.connection`)."""
        raise NotImplementedError


class MockAdapter(InferenceAdapter):
    """A trivial in-memory adapter that echoes the request. Exists only
    to prove `RuntimeRegistry`'s dispatch contract is usable end-to-end
    without any real backend — never intended for anything beyond tests
    and local development wiring."""

    backend = "mock"

    def infer(self, request: InferenceRequest, *, binding: ModelBinding) -> InferenceResult:
        return InferenceResult(
            success=True,
            output_text=f"mock[{binding.candidate_id}]: {request.prompt}",
            raw={"request": request.model_dump(mode="json"), "binding": binding.model_dump(mode="json")},
        )


class RuntimeRegistry:
    """Binds Model Registry candidates to backends and dispatches
    inference calls to the matching InferenceAdapter.

    `model_registry` is optional: when supplied, `bind()` verifies the
    bound `candidate_id` is actually a registered Model Registry entry
    (a "missing reference" check, Context-2 task brief §6/§7) without
    hard-coupling this class to the Model Registry for callers that don't
    need that check.
    """

    def __init__(self, *, model_registry=None) -> None:
        self._model_registry = model_registry
        self._adapters: Dict[str, InferenceAdapter] = {}
        self._bindings: Dict[str, ModelBinding] = {}

    def register_adapter(self, adapter: InferenceAdapter) -> None:
        if adapter.backend in self._adapters:
            raise DuplicateIdError(f"an adapter is already registered for backend {adapter.backend!r}")
        self._adapters[adapter.backend] = adapter

    def get_adapter(self, backend: str) -> InferenceAdapter:
        try:
            return self._adapters[backend]
        except KeyError:
            raise UnsupportedBackendError(
                f"no InferenceAdapter is registered for backend {backend!r}"
            ) from None

    def bind(self, binding: ModelBinding) -> None:
        if binding.candidate_id in self._bindings:
            raise DuplicateIdError(f"candidate_id already bound: {binding.candidate_id!r}")
        if binding.backend not in self._adapters:
            raise UnsupportedBackendError(
                f"cannot bind candidate {binding.candidate_id!r} to unregistered "
                f"backend {binding.backend!r}"
            )
        if self._model_registry is not None and binding.candidate_id not in self._model_registry:
            raise MissingReferenceError(
                f"ModelBinding.candidate_id {binding.candidate_id!r} is not a "
                f"registered Model Registry candidate"
            )
        self._bindings[binding.candidate_id] = binding

    def invoke(self, candidate_id: str, request: InferenceRequest) -> InferenceResult:
        try:
            binding = self._bindings[candidate_id]
        except KeyError:
            raise UnknownIdError(f"no runtime binding for candidate_id: {candidate_id!r}") from None
        adapter = self.get_adapter(binding.backend)
        return adapter.infer(request, binding=binding)

    def bindings(self) -> List[ModelBinding]:
        return list(self._bindings.values())
