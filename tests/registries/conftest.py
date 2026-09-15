"""Shared dict-factory fixtures for the registries test suite.

Plain dicts (not pre-built Pydantic objects) are returned deliberately —
most registry behavior under test is exercised through
`register_from_dict`, which is the path real manifest-file loading also
goes through (`trackA.registries._io.read_manifest_file` yields a dict),
so these factories exercise the same code path as production loading.
"""
from __future__ import annotations

from pathlib import Path

import pytest

SEED_DATA_DIR = Path(__file__).resolve().parents[2] / "trackA" / "registries" / "data"


def manifest_provenance_data(**overrides) -> dict:
    data = {"created_by": "harsh", "source_basis": "test fixture", "version": "1.0.0"}
    data.update(overrides)
    return data


def tool_manifest_data(**overrides) -> dict:
    data = dict(
        tool_id="subfinder",
        name="Subfinder",
        version="v2.6.3",
        purpose="Passive subdomain enumeration",
        category="recon",
        input_schema={"type": "object", "properties": {"domain": {"type": "string"}}, "required": ["domain"]},
        expected_output="A list of subdomains believed to belong to the target domain.",
        container_image="sha256:abc123",
        network_requirements={"egress": "DNS + HTTPS to passive-source APIs only"},
        filesystem_requirements={"read_only_root": True},
        resource_limits={"cpu": "1", "memory_mb": 512},
        timeout_seconds=120,
        allowed_stages=["tool_execution"],
        risk_classification="low",
        failure_handling="on timeout, treat partial output as untrusted",
        audit_requirements="log domain input and exit code",
        provenance=manifest_provenance_data(),
    )
    data.update(overrides)
    return data


def worker_manifest_data(**overrides) -> dict:
    data = dict(
        worker_id="endpoint_mapper_v1",
        purpose="Map every reachable endpoint and identify object references.",
        input_schema={"type": "object"},
        output_schema={"type": "object"},
        worker_role_binding="endpoint_mapper",
        system_prompt="You map API endpoints. You do not evaluate vulnerability likelihood.",
        allowed_tools=[],
        timeout_seconds=60,
        retry_limit=2,
        resource_limits={"max_tokens": 2048},
        success_criteria="produces a structured endpoint map",
        failure_criteria="output is not valid JSON",
        must_not=["evaluate vulnerability likelihood", "propose exploit steps"],
        provenance_requirements="log input entity count and output endpoint count",
        provenance=manifest_provenance_data(),
    )
    data.update(overrides)
    return data


def skill_manifest_data(**overrides) -> dict:
    data = dict(
        skill_id="idor_v1",
        vulnerability_class="IDOR",
        methodology="Test object reference manipulation across authenticated endpoints.",
        system_prompt="You are the IDOR Specialist.",
        few_shot_examples=[],
        references=["OWASP API Security Top 10 - API1:2023"],
        expected_inputs={"type": "object"},
        expected_outputs={"type": "object", "required": ["replication_command"]},
        permissions=["read_endpoint_map"],
        version="1.0.0",
        provenance=manifest_provenance_data(),
        validation_status="draft",
    )
    data.update(overrides)
    return data


def model_manifest_data(**overrides) -> dict:
    data = dict(
        candidate_id="qwen2.5-1.5b-extractor",
        model_identity="Qwen2.5-1.5B-Instruct",
        source_provider="Hugging Face / Alibaba",
        version="q4_k_m",
        intended_worker_role="extractor",
        execution_location="local",
        runtime_requirements={"min_ram_gb": 4, "min_vram_gb": 0, "quantization": "Q4_K_M"},
        input_format="GBNF-constrained chat prompt",
        output_schema_compatibility="gbnf",
        benchmark_status="NOT_YET_BENCHMARKED",
        quality_metrics={},
        known_limitations="Not yet benchmarked.",
        security_suitability_notes="Runs local-only.",
        approval_status="candidate",
        replacement_policy="Re-benchmark per docs/16 before replacement.",
    )
    data.update(overrides)
    return data


@pytest.fixture
def tool_data():
    return tool_manifest_data


@pytest.fixture
def worker_data():
    return worker_manifest_data


@pytest.fixture
def skill_data():
    return skill_manifest_data


@pytest.fixture
def model_data():
    return model_manifest_data
