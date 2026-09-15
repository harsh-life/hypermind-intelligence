from __future__ import annotations

import pytest
from pydantic import ValidationError

from trackA.schemas.common import PipelineStage
from trackA.schemas.workers import WorkerInput, WorkerManifest, WorkerOutput
from tests.conftest import make_manifest_provenance, make_provenance


def _manifest(**overrides):
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
        provenance=make_manifest_provenance(),
    )
    data.update(overrides)
    return WorkerManifest(**data)


def test_worker_manifest_valid_uses_role_binding_not_model_field():
    manifest = _manifest()
    assert manifest.worker_role_binding == "endpoint_mapper"
    assert not hasattr(manifest, "model")


def test_worker_manifest_rejects_bad_timeout():
    with pytest.raises(ValidationError):
        _manifest(timeout_seconds=-1)


def test_worker_manifest_rejects_negative_retry_limit():
    with pytest.raises(ValidationError):
        _manifest(retry_limit=-1)


def test_worker_input_valid(run_id):
    wi = WorkerInput(
        provenance=make_provenance(run_id, PipelineStage.WORKER),
        worker_id="endpoint_mapper_v1",
        payload={"entities": []},
        source_extractor_record_id="d1",
    )
    assert wi.worker_id == "endpoint_mapper_v1"


def test_worker_output_requires_model_provenance(run_id):
    with pytest.raises(ValidationError):
        WorkerOutput(
            provenance=make_provenance(run_id, PipelineStage.WORKER),
            worker_id="endpoint_mapper_v1",
            payload={"mapped_endpoints": []},
            retry_count=0,
        )


def test_worker_output_negative_retry_rejected(run_id):
    with pytest.raises(ValidationError):
        WorkerOutput(
            provenance=make_provenance(
                run_id, PipelineStage.WORKER, model_id="worker-model-a", model_version="v1"
            ),
            worker_id="endpoint_mapper_v1",
            payload={},
            retry_count=-1,
        )
