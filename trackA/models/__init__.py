"""Model Serving Layer (docs/02_COMPONENT_SPECS.md component 5).

Separate top-level package from `trackA.registries`, matching the
repository layout docs/15_ENGINEERING_HANDOFF.md §4 recommends:
`registries/` for Tool/Worker/Skill/Model registries (components 1-4),
`models/` for the "Ollama serving integration" component (component 5) —
generalised here to "the inference-adapter/runtime integration," since
this context's explicit job is to make Ollama one representable backend
among several, not the only one (Context-2 task brief §5: "Ollama is NOT
the only supported backend").

Context-2 scope (task brief §3.G): an interface/abstraction only. No real
network call to Ollama, LiteLLM, or any cloud API is implemented here —
see `runtime.MockAdapter` for the one concrete adapter this context
provides, which exists solely to prove the contract is usable, not as a
production implementation.
"""
from __future__ import annotations

from trackA.models.runtime import (
    InferenceAdapter,
    InferenceRequest,
    InferenceResult,
    MockAdapter,
    ModelBinding,
    RuntimeRegistry,
)

__all__ = [
    "InferenceAdapter",
    "InferenceRequest",
    "InferenceResult",
    "ModelBinding",
    "RuntimeRegistry",
    "MockAdapter",
]
