"""Orchestrator schemas. Source: docs/03_DATA_SCHEMAS_README.md §2.3."""
from __future__ import annotations

from typing import Any, Dict, Literal

from pydantic import model_validator

from trackA.schemas.base import HypermindModel
from trackA.schemas.common import PipelineStage, Provenance


class OrchestratorAction(HypermindModel):
    """docs/03 §2.3. Produced by: Orchestrator's planning LLM.

    "MODEL PROPOSES" — this is the model-proposed record; everything past
    it (schema/scope/registry/policy/resource checks) is deterministic
    Orchestrator logic and out of scope for this context.
    """

    provenance: Provenance
    proposed_action_type: Literal[
        "tool_execution", "worker_invocation", "specialist_investigation"
    ]
    target_registry_id: str
    proposed_parameters: Dict[str, Any]
    session_action_count: int

    @model_validator(mode="after")
    def _validate(self) -> "OrchestratorAction":
        if self.provenance.stage != PipelineStage.ORCHESTRATOR:
            raise ValueError("OrchestratorAction.provenance.stage must be 'orchestrator'")
        if not self.provenance.model_id:
            raise ValueError(
                "OrchestratorAction.provenance.model_id is required "
                "(docs/03 §2.3: this is a model-proposed record)"
            )
        if self.session_action_count < 1:
            raise ValueError("OrchestratorAction.session_action_count must be >= 1")
        return self
