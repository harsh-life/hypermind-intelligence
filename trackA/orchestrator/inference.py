"""Technical-failure vs. model-refusal classification for the Orchestrator's
own model invocations (Worker/Judge/Specialist). Context-5 task brief §9/§17.

Deliberately a small, self-contained duplicate of the *convention*
`trackA.evaluation.harness.classify_result` already established for the
same underlying `trackA.models.runtime.InferenceResult` type — NOT an
import of that module. Context-4 task brief §23 (this context's own
instructions) is explicit that live runtime execution must not depend on
the evaluation lab: "Evaluation is a consumer of runtime evidence, not the
authorization authority" — and the dependency direction that statement
implies (evaluation depends on runtime, never the reverse) rules out
`trackA.orchestrator` importing anything from `trackA.evaluation`, even a
small pure function. Duplicating this ~10-line, already-documented
convention here (rather than, say, relocating it into
`trackA.models.runtime`, which would mean editing Context 2's locked
runtime module for a Context-4-authored concern) is the smaller, safer
change — consistent with this codebase's existing precedent of small,
independently-justified duplication over cross-module coupling (e.g.
`trackA/registries/_io.py`'s manifest-file reading vs.
`trackA/evaluation/storage.py`'s separate artifact-file writing: both do
"read/write a JSON file" without being merged into one shared utility).

The convention itself, restated: an `InferenceAdapter` that can positively
identify a refusal (a real LLM backend usually can, from a stop_reason/
finish_reason-style signal) sets `InferenceResult.raw["refusal"] = True`.
Every other unsuccessful result is a technical failure, eligible for
bounded retry. Never inferred from free-text `error` content — guessing
"looks like a refusal" from message text is exactly the kind of
confidence-beyond-the-evidence this package's "evidence over confidence"
principle (docs/01_ARCHITECTURE.md §4) warns against, restated at this
layer.
"""
from __future__ import annotations

from typing import Literal

from trackA.models.runtime import InferenceResult

ResultStatus = Literal["success", "technical_failure", "refusal"]

REFUSAL_MARKER_KEY = "refusal"


def classify_result(result: InferenceResult) -> ResultStatus:
    if result.success:
        return "success"
    if isinstance(result.raw, dict) and result.raw.get(REFUSAL_MARKER_KEY) is True:
        return "refusal"
    return "technical_failure"
