"""Shared fixtures for the trackA.evaluation test suite."""
from __future__ import annotations

from pathlib import Path

import pytest

from trackA.evaluation.cases import BenchmarkCaseStore, DatasetStore
from trackA.models.runtime import InferenceRequest, InferenceResult, InferenceAdapter, ModelBinding, RuntimeRegistry
from trackA.registries.models import ModelRegistry

SEED_DATA_DIR = Path(__file__).resolve().parents[2] / "trackA" / "evaluation" / "data"


def model_manifest_data(**overrides) -> dict:
    data = dict(
        candidate_id="cand-a",
        model_identity="Test-Model-A",
        source_provider="test",
        version="v1",
        intended_worker_role="specialist",
        execution_location="local",
        runtime_requirements={"min_ram_gb": 1, "min_vram_gb": 0, "quantization": "none"},
        input_format="chat",
        output_schema_compatibility="none",
        benchmark_status="NOT_YET_BENCHMARKED",
        quality_metrics={},
        known_limitations="none recorded",
        security_suitability_notes="test fixture",
        approval_status="candidate",
        replacement_policy="test fixture",
    )
    data.update(overrides)
    return data


class ScriptedAdapter(InferenceAdapter):
    """Returns a pre-scripted sequence of InferenceResults per candidate,
    one per call, so tests can deterministically exercise retry/refusal/
    success sequences without any real backend. The last scripted result
    repeats once its sequence is exhausted."""

    backend = "scripted"

    def __init__(self) -> None:
        self._scripts: dict[str, list[InferenceResult]] = {}
        self._call_counts: dict[str, int] = {}

    def script(self, candidate_id: str, results: list[InferenceResult]) -> None:
        self._scripts[candidate_id] = results
        self._call_counts[candidate_id] = 0

    def call_count(self, candidate_id: str) -> int:
        return self._call_counts.get(candidate_id, 0)

    def infer(self, request: InferenceRequest, *, binding: ModelBinding) -> InferenceResult:
        candidate_id = binding.candidate_id
        idx = self._call_counts.get(candidate_id, 0)
        self._call_counts[candidate_id] = idx + 1
        script = self._scripts[candidate_id]
        return script[min(idx, len(script) - 1)]


@pytest.fixture
def model_data():
    return model_manifest_data


@pytest.fixture
def case_store() -> BenchmarkCaseStore:
    return BenchmarkCaseStore.from_directory(SEED_DATA_DIR / "cases")


@pytest.fixture
def dataset_store() -> DatasetStore:
    store = DatasetStore()
    store.register_from_directory(SEED_DATA_DIR / "datasets")
    return store


@pytest.fixture
def two_candidate_registry(model_data) -> ModelRegistry:
    registry = ModelRegistry()
    registry.register_from_dict(model_data(candidate_id="cand-a"))
    registry.register_from_dict(model_data(candidate_id="cand-b"))
    return registry


@pytest.fixture
def scripted_runtime(two_candidate_registry) -> tuple[RuntimeRegistry, ScriptedAdapter]:
    adapter = ScriptedAdapter()
    runtime = RuntimeRegistry(model_registry=two_candidate_registry)
    runtime.register_adapter(adapter)
    runtime.bind(ModelBinding(candidate_id="cand-a", backend="scripted"))
    runtime.bind(ModelBinding(candidate_id="cand-b", backend="scripted"))
    return runtime, adapter
