"""Optional, modular Promptfoo-style supplementary checks. Context-4 task
brief §15.

Zero coupling: nothing in `trackA.evaluation.harness`/`judge_package`/
`judge`/`results`/`cases` imports this module, and this module imports
nothing from them. Promptfoo remains "part of the evaluation toolkit" for
repeatable prompt/model regression checks and structured-output checks,
never the primary candidate-competition mechanism (task brief §3: "the
unit of comparison is the actual task/trajectory ... Promptfoo is
supplementary, not the primary evaluation mechanism").

No real `promptfoo` CLI/binary is invoked anywhere in this module — the
task brief explicitly requires the test suite never need external
tooling/API access to pass (§22), and shelling out to an assumed-
installed binary would violate that. `PromptfooAdapter` is the pluggable
seam a real integration would implement later (running the actual
`promptfoo` CLI/config against a candidate and parsing its result);
`MockPromptfooAdapter` exists only to prove that seam is usable, exactly
like `trackA.models.runtime.MockAdapter` does for the inference-adapter
layer.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, ClassVar, Dict

from trackA.schemas.base import HypermindModel


class PromptfooCheckResult(HypermindModel):
    """One structured-output/regression check result. Not part of the
    docs/03 canonical schema set and not exported from
    `trackA.schemas` — deliberately kept local to this optional,
    supplementary module (see module docstring)."""

    check_id: str
    candidate_id: str
    passed: bool
    detail: Dict[str, Any] = {}


class PromptfooAdapter(ABC):
    """The pluggable seam for a real Promptfoo integration. Never called
    by any core evaluation module (see module docstring)."""

    check_suite: ClassVar[str]

    @abstractmethod
    def run_check(self, *, check_id: str, candidate_id: str, prompt: str) -> PromptfooCheckResult:
        raise NotImplementedError


class MockPromptfooAdapter(PromptfooAdapter):
    """Trivial stand-in proving the `PromptfooAdapter` contract is usable
    without any real `promptfoo` binary or network access — never
    intended for anything beyond tests/local development wiring."""

    check_suite = "mock"

    def run_check(self, *, check_id: str, candidate_id: str, prompt: str) -> PromptfooCheckResult:
        return PromptfooCheckResult(
            check_id=check_id, candidate_id=candidate_id, passed=True, detail={"prompt": prompt}
        )
