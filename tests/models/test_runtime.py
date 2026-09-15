from __future__ import annotations

import pytest
from pydantic import ValidationError

from trackA.models.runtime import (
    InferenceRequest,
    InferenceResult,
    MockAdapter,
    ModelBinding,
    RuntimeRegistry,
)
from trackA.registries.errors import (
    DuplicateIdError,
    MissingReferenceError,
    UnknownIdError,
    UnsupportedBackendError,
)
from trackA.registries.models import ModelRegistry


def test_mock_adapter_satisfies_inference_adapter_contract():
    adapter = MockAdapter()
    result = adapter.infer(
        InferenceRequest(role="extractor", prompt="hello"),
        binding=ModelBinding(candidate_id="c1", backend="mock"),
    )
    assert isinstance(result, InferenceResult)
    assert result.success is True
    assert "hello" in result.output_text


def test_inference_result_requires_error_message_on_failure():
    with pytest.raises(ValidationError):
        InferenceResult(success=False)


def test_inference_result_allows_failure_with_error():
    result = InferenceResult(success=False, error="model refusal")
    assert result.error == "model refusal"


def test_register_adapter_and_bind_and_invoke():
    runtime = RuntimeRegistry()
    runtime.register_adapter(MockAdapter())
    runtime.bind(ModelBinding(candidate_id="qwen2.5-1.5b-extractor", backend="mock"))

    result = runtime.invoke(
        "qwen2.5-1.5b-extractor", InferenceRequest(role="extractor", prompt="parse this")
    )
    assert result.success is True
    assert "qwen2.5-1.5b-extractor" in result.output_text


def test_duplicate_adapter_registration_rejected():
    runtime = RuntimeRegistry()
    runtime.register_adapter(MockAdapter())
    with pytest.raises(DuplicateIdError):
        runtime.register_adapter(MockAdapter())


def test_bind_unsupported_backend_rejected():
    runtime = RuntimeRegistry()
    with pytest.raises(UnsupportedBackendError):
        runtime.bind(ModelBinding(candidate_id="c1", backend="ollama"))


def test_get_adapter_unsupported_backend_rejected():
    runtime = RuntimeRegistry()
    with pytest.raises(UnsupportedBackendError):
        runtime.get_adapter("litellm")


def test_duplicate_binding_rejected():
    runtime = RuntimeRegistry()
    runtime.register_adapter(MockAdapter())
    runtime.bind(ModelBinding(candidate_id="c1", backend="mock"))
    with pytest.raises(DuplicateIdError):
        runtime.bind(ModelBinding(candidate_id="c1", backend="mock"))


def test_invoke_without_binding_raises_unknown_id():
    runtime = RuntimeRegistry()
    runtime.register_adapter(MockAdapter())
    with pytest.raises(UnknownIdError):
        runtime.invoke("never-bound", InferenceRequest(role="extractor", prompt="x"))


def test_bind_validates_candidate_exists_in_model_registry_when_provided(model_data):
    models = ModelRegistry()
    models.register_from_dict(model_data())

    runtime = RuntimeRegistry(model_registry=models)
    runtime.register_adapter(MockAdapter())

    # bound candidate is registered -> succeeds
    runtime.bind(ModelBinding(candidate_id="qwen2.5-1.5b-extractor", backend="mock"))

    # bound candidate is NOT registered -> missing-reference failure
    with pytest.raises(MissingReferenceError):
        runtime.bind(ModelBinding(candidate_id="never-registered", backend="mock"))


def test_bind_skips_model_registry_check_when_not_provided():
    runtime = RuntimeRegistry()  # no model_registry supplied
    runtime.register_adapter(MockAdapter())
    # No MissingReferenceError even though "anything" was never registered
    # anywhere -- this constructor param is opt-in, not mandatory coupling.
    runtime.bind(ModelBinding(candidate_id="anything", backend="mock"))
    assert len(runtime.bindings()) == 1


def test_backend_is_an_open_string_not_a_closed_enum():
    """Context-2 task brief §5: Ollama must not be the only representable
    backend, and new backends must not require a schema change."""
    binding = ModelBinding(candidate_id="c1", backend="a-future-backend-nobody-has-named-yet")
    assert binding.backend == "a-future-backend-nobody-has-named-yet"


def test_model_binding_serialization_round_trip():
    binding = ModelBinding(candidate_id="c1", backend="litellm", connection={"model": "gemini/gemini-1.5-flash"})
    dumped = binding.model_dump(mode="json")
    reloaded = ModelBinding.model_validate(dumped)
    assert reloaded == binding
