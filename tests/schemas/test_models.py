from __future__ import annotations

import pytest
from pydantic import ValidationError

from trackA.schemas.models import ModelManifest, ModelQualityMetrics, ModelRuntimeRequirements


def _manifest(**overrides):
    data = dict(
        candidate_id="cand-001",
        model_identity="Foundation-Sec-8B",
        source_provider="Hugging Face / Cisco Foundation AI",
        version="2025-04",
        intended_worker_role="specialist_idor",
        execution_location="local",
        runtime_requirements=ModelRuntimeRequirements(min_ram_gb=16, min_vram_gb=8, quantization="Q4_K_M"),
        input_format="chat template",
        output_schema_compatibility="json_mode",
        benchmark_status="NOT_YET_BENCHMARKED",
        quality_metrics=ModelQualityMetrics(),
        known_limitations="Competitive on CTIBENCH per vendor claim, not independently verified.",
        security_suitability_notes="No special trust-boundary concerns noted yet.",
        approval_status="candidate",
        replacement_policy="re-benchmark if a newer candidate is proposed for this role",
    )
    data.update(overrides)
    return ModelManifest(**data)


def test_model_manifest_valid_with_null_quality_metrics():
    manifest = _manifest()
    assert manifest.quality_metrics.structured_output_validity_rate is None
    assert manifest.benchmark_status == "NOT_YET_BENCHMARKED"


def test_model_manifest_cost_defaults_to_zero():
    manifest = _manifest()
    assert manifest.cost_per_call_usd == 0.0


def test_model_manifest_rejects_bad_execution_location():
    with pytest.raises(ValidationError):
        _manifest(execution_location="hybrid")


def test_quality_metrics_rate_out_of_range_rejected():
    with pytest.raises(ValidationError):
        ModelQualityMetrics(false_positive_rate=1.5)


def test_quality_metrics_measured_rate_accepted():
    metrics = ModelQualityMetrics(false_positive_rate=0.12)
    assert metrics.false_positive_rate == 0.12
