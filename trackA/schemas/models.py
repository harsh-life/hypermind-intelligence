"""Model registry schema. Source: docs/08_MODEL_REGISTRY.md, "Candidate
Model Manifest Schema".

Only the candidate-model manifest *shape* is implemented here. NOT
implemented (Model Registry logic, explicitly excluded from this
context): the "Currently Selected Implementations" table, any role ->
model lookup/binding, and the benchmarking process itself
(docs/16_EVALUATION_BENCHMARKING.md). The Judge model identity is
UNDECIDED per docs/08 — nothing here invents a resolution for that; a
ModelManifest simply may or may not exist yet for a given role.
"""
from __future__ import annotations

from typing import Any, Dict, Literal, Optional

from pydantic import model_validator

from trackA.schemas.base import HypermindModel


class ModelRuntimeRequirements(HypermindModel):
    """ModelManifest.runtime_requirements, docs/08."""

    min_ram_gb: float
    min_vram_gb: float
    quantization: str


class ModelQualityMetrics(HypermindModel):
    """ModelManifest.quality_metrics, docs/08.

    [ABSOLUTE RULE, docs/08]: "do not invent benchmark results... A
    quality_metrics field with a null value means 'not yet measured' —
    it is never filled with an estimate, a vendor claim, or an
    assumption." All three rate fields therefore default to None, never
    a fabricated number.
    """

    structured_output_validity_rate: Optional[float] = None
    useful_hypothesis_rate: Optional[float] = None
    false_positive_rate: Optional[float] = None
    reference: str = (
        "EVALUATION_BENCHMARKING.md — null until actually measured, never estimated"
    )

    @model_validator(mode="after")
    def _rates_in_range(self) -> "ModelQualityMetrics":
        for name in (
            "structured_output_validity_rate",
            "useful_hypothesis_rate",
            "false_positive_rate",
        ):
            value = getattr(self, name)
            if value is not None and not (0.0 <= value <= 1.0):
                raise ValueError(f"ModelQualityMetrics.{name} must be within [0, 1]")
        return self


class ModelManifest(HypermindModel):
    """docs/08_MODEL_REGISTRY.md "Candidate Model Manifest Schema".

    Referred to as `ModelManifest` by docs/02_COMPONENT_SPECS.md §4
    (which itself contains a stale citation pointing to docs/03 instead
    of docs/08 for this type — docs/14_CONSISTENCY_AUDIT.md FINDING-1
    already flags that citation as a plain, undecided-nothing-needed
    correction; noted here for completeness, not re-litigated).

    "Do not add a candidate to this registry merely because it exists" —
    that gatekeeping and any role-to-candidate binding is Model Registry
    logic and out of scope for this context; this type only represents
    one candidate's own self-contained manifest.
    """

    candidate_id: str
    model_identity: str
    source_provider: str
    version: str
    intended_worker_role: str
    execution_location: Literal["local", "remote"]
    runtime_requirements: ModelRuntimeRequirements
    input_format: str
    output_schema_compatibility: Literal["gbnf", "json_mode", "none", "requires_wrapper"]
    benchmark_status: Literal[
        "NOT_YET_BENCHMARKED", "PENDING", "BENCHMARKED", "REJECTED"
    ]
    quality_metrics: ModelQualityMetrics
    latency_ms_p50: Optional[float] = None
    cost_per_call_usd: float = 0.0
    known_limitations: str
    security_suitability_notes: str
    approval_status: Literal["candidate", "approved", "deprecated", "rejected"]
    replacement_policy: str
