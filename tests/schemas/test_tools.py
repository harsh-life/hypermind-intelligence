from __future__ import annotations

import pytest
from pydantic import ValidationError

from trackA.schemas.common import PipelineStage, TrustClassification
from trackA.schemas.tools import RawToolOutput, ToolExecutionRequest, ToolExecutionResult, ToolManifest
from tests.conftest import make_manifest_provenance, make_provenance


def _tool_manifest(**overrides):
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
        provenance=make_manifest_provenance(),
    )
    data.update(overrides)
    return ToolManifest(**data)


def test_tool_manifest_valid():
    tm = _tool_manifest()
    assert tm.expected_output
    assert tm.category == "recon"


def test_tool_manifest_extensible_category_accepted():
    tm = _tool_manifest(category="vulnerability_scan")
    assert tm.category == "vulnerability_scan"


def test_tool_manifest_nuclei_style_high_risk_accepted():
    # Architecture-owner decision: the enum stays closed at low/medium/high;
    # a Nuclei-style entry is corrected to "high", not "medium-high".
    tm = _tool_manifest(
        tool_id="nuclei",
        name="Nuclei",
        category="vulnerability_scan",
        risk_classification="high",
    )
    assert tm.risk_classification == "high"


def test_tool_manifest_rejects_non_positive_timeout():
    with pytest.raises(ValidationError):
        _tool_manifest(timeout_seconds=0)


def test_tool_manifest_rejects_out_of_enum_risk_classification():
    with pytest.raises(ValidationError):
        _tool_manifest(risk_classification="medium-high")


def test_tool_execution_result_success_requires_raw_output(run_id):
    with pytest.raises(ValidationError):
        ToolExecutionResult(
            provenance=make_provenance(
                run_id, PipelineStage.TOOL_EXECUTION, tool_id="subfinder", tool_version="v2.6.3"
            ),
            request_record_id="r1",
            exit_status="success",
            duration_ms=4213,
        )


def test_tool_execution_result_success_with_raw_output(run_id):
    result = ToolExecutionResult(
        provenance=make_provenance(
            run_id, PipelineStage.TOOL_EXECUTION, tool_id="subfinder", tool_version="v2.6.3"
        ),
        request_record_id="r1",
        exit_status="success",
        duration_ms=4213,
        raw_output_record_id="c1",
    )
    assert result.exit_status == "success"


def test_tool_execution_result_requires_tool_id(run_id):
    with pytest.raises(ValidationError):
        ToolExecutionResult(
            provenance=make_provenance(run_id, PipelineStage.TOOL_EXECUTION),
            request_record_id="r1",
            exit_status="timeout",
            duration_ms=100,
        )


def test_raw_tool_output_defaults_to_raw_observation(run_id):
    obs = RawToolOutput(
        provenance=make_provenance(
            run_id, PipelineStage.TOOL_EXECUTION, tool_id="subfinder", tool_version="v2.6.3"
        ),
        content="sub1.example-bounty.com\n",
        truncated=False,
    )
    assert obs.trust_classification == TrustClassification.RAW_OBSERVATION


def test_raw_tool_output_rejects_other_trust_classification(run_id):
    with pytest.raises(ValidationError):
        RawToolOutput(
            provenance=make_provenance(
                run_id, PipelineStage.TOOL_EXECUTION, tool_id="subfinder", tool_version="v2.6.3"
            ),
            trust_classification="VALIDATED_FINDING",
            content="...",
            truncated=False,
        )


def test_tool_execution_request_valid(run_id):
    req = ToolExecutionRequest(
        provenance=make_provenance(run_id, PipelineStage.ORCHESTRATOR),
        tool_id="subfinder",
        parameters={"domain": "example-bounty.com"},
        authorized_by_action_id="a2",
    )
    assert req.tool_id == "subfinder"
