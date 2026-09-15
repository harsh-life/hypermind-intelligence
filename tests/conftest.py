"""Shared fixtures/factories for the schema-layer test suite."""
from __future__ import annotations

import pytest

from trackA.schemas.common import ManifestProvenance, PipelineStage, Provenance


@pytest.fixture
def run_id() -> str:
    return "11111111-1111-4111-8111-111111111111"


def make_provenance(run_id: str, stage: PipelineStage, **overrides) -> Provenance:
    data = {
        "run_id": run_id,
        "stage": stage,
        "source_component": overrides.pop("source_component", "Test Component"),
    }
    data.update(overrides)
    return Provenance(**data)


def make_manifest_provenance(**overrides) -> ManifestProvenance:
    data = {
        "created_by": "harsh",
        "source_basis": "test fixture",
        "version": "1.0.0",
    }
    data.update(overrides)
    return ManifestProvenance(**data)


@pytest.fixture
def provenance_factory(run_id):
    def _factory(stage: PipelineStage, **overrides) -> Provenance:
        return make_provenance(run_id, stage, **overrides)

    return _factory


@pytest.fixture
def manifest_provenance_factory():
    return make_manifest_provenance
