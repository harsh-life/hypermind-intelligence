"""Tool execution layer. Context 5 (runtime/tools/orchestration).

Owns turning an *already-authorized* tool invocation into a captured
result (docs/02_COMPONENT_SPECS.md §12, Docker Tool Execution Engine).
This package never decides *whether* a request is authorized — that is
the Scope Gate's job (trackA.policy.scope_gate, Context 3, reused
unmodified) and the Orchestrator's job to invoke it first
(trackA.orchestrator). See trackA/execution/tools.py's module docstring
for the isolation-boundary design.
"""
from __future__ import annotations

from trackA.execution.backends import MockToolBackend, ToolBackend, ToolBackendResult
from trackA.execution.tools import ToolExecutor, ToolInvocationRecord

__all__ = [
    "ToolBackend",
    "ToolBackendResult",
    "MockToolBackend",
    "ToolExecutor",
    "ToolInvocationRecord",
]
