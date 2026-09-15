"""Skill schemas. Source: docs/03_DATA_SCHEMAS_README.md §2.15-2.17,
reconciled against docs/04_WORKER_SKILL_CONTRACTS.md and
docs/01_ARCHITECTURE.md §4.

CandidateFinding (the task's requested name) = SpecialistPoCOutput below
— see trackA/schemas/__init__.py for the alias.
"""
from __future__ import annotations

from typing import Any, Dict, List, Literal

from pydantic import model_validator

from trackA.schemas.base import HypermindModel
from trackA.schemas.common import ManifestProvenance, Provenance, TrustClassification


class SkillManifest(HypermindModel):
    """docs/03 §2.15, [LOCKED field list], RECONCILED.

    Two deliberate deviations from docs/03's literal text, both flagged:

    - `specialist_role_binding` is ADDED. docs/03 §2.15's SkillManifest
      (and every instance actually written in docs/05_SKILL_MANIFESTS_
      README.md — idor_v1/ssrf_v1/auth_bypass_v1/privilege_escalation_v1)
      has NO field pointing at a Model Registry role at all. But
      docs/04_WORKER_SKILL_CONTRACTS.md explicitly designs
      `specialist_role_binding` for exactly this purpose, with the same
      "pointer, not a model identifier" rationale used for
      WorkerManifest, and docs/01_ARCHITECTURE.md §4 [LOCKED] requires
      this separation architecturally for "a worker or skill contract."
      This is a gap in docs/03/docs/05 that docs/14_CONSISTENCY_AUDIT.md
      did not catch. Since the calling task requires preserving
      "model-role vs model-identity separation" and names docs/04 as
      authoritative, this field is added here. Flagged in the
      schema-layer report as an unresolved documentation gap, not a
      silent invention — the field, its name, and its rationale are all
      taken directly from docs/04.
    - `provenance: ManifestProvenance` replaces docs/03's `provenance:
      Provenance` (the pipeline-run-oriented common type). This is
      exactly OD-15's original scope (docs/13_OPEN_DECISIONS.md) before
      FINDING-2 widened it to all three manifest types — a `Provenance`
      requires a `run_id`, which does not naturally exist for a manifest
      authored once by a human outside any pipeline run. See
      trackA/schemas/common.py's ManifestProvenance docstring.
    """

    skill_id: str
    vulnerability_class: str
    methodology: str
    specialist_role_binding: str
    system_prompt: str
    few_shot_examples: List[Dict[str, Any]]
    references: List[str]
    expected_inputs: Dict[str, Any]
    expected_outputs: Dict[str, Any]
    permissions: List[str]
    version: str
    provenance: ManifestProvenance
    validation_status: Literal["draft", "active", "deprecated"]


class SpecialistInput(HypermindModel):
    """docs/03 §2.16. Produced by: Specialist Executor."""

    provenance: Provenance
    skill_id: str
    evidence_context: Dict[str, Any]
    judge_routing_record_id: str


class SpecialistPoCOutput(HypermindModel):
    """docs/03 §2.17. Produced by: Specialist Executor.

    [LOCKED] `replication_command` must be non-empty — the Evidence Gate
    hard-requires this; a record without it must fail downstream, not be
    treated as acceptable. Enforced here with `min_length=1` so an empty
    string cannot even be constructed.

    Per docs/02_COMPONENT_SPECS.md §16 [REQ]: the `replication_command`
    is itself a *proposed* reproduction step for a human, never something
    this schema layer (or anything else in this context) executes.
    """

    provenance: Provenance
    trust_classification: Literal[TrustClassification.CANDIDATE_FINDING] = (
        TrustClassification.CANDIDATE_FINDING
    )
    skill_id: str
    vulnerability_claim: str
    replication_command: str
    supporting_evidence: Dict[str, Any]
    specialist_confidence: float

    @model_validator(mode="after")
    def _validate(self) -> "SpecialistPoCOutput":
        if not self.replication_command:
            raise ValueError(
                "SpecialistPoCOutput.replication_command must be non-empty "
                "(docs/03 §2.17, [LOCKED])"
            )
        if not (0.0 <= self.specialist_confidence <= 1.0):
            raise ValueError(
                "SpecialistPoCOutput.specialist_confidence must be within [0, 1]"
            )
        if not self.provenance.model_id:
            raise ValueError(
                "SpecialistPoCOutput.provenance.model_id is required (docs/03 §2.17)"
            )
        return self
