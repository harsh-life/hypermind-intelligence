from __future__ import annotations

import ast
import inspect

from trackA.evaluation import promptfoo as promptfoo_module
from trackA.evaluation.promptfoo import MockPromptfooAdapter, PromptfooAdapter, PromptfooCheckResult


def test_mock_promptfoo_adapter_satisfies_contract():
    adapter = MockPromptfooAdapter()
    result = adapter.run_check(check_id="structured-output-1", candidate_id="cand-a", prompt="hello")
    assert isinstance(result, PromptfooCheckResult)
    assert result.passed is True
    assert result.candidate_id == "cand-a"


def test_promptfoo_module_has_zero_coupling_from_core_evaluation_modules():
    """Task brief §15: 'keep it modular rather than making the rest of
    the architecture depend on Promptfoo.'"""
    for module_name in ("harness", "judge", "judge_package", "results", "cases"):
        module = __import__(f"trackA.evaluation.{module_name}", fromlist=[module_name])
        source = inspect.getsource(module)
        tree = ast.parse(source)
        imported = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                imported.append(node.module)
            elif isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
        assert not any("promptfoo" in name.lower() for name in imported), (module_name, imported)


def test_promptfoo_module_does_not_import_core_evaluation_modules():
    """The dependency is one-directional: nothing in promptfoo.py reaches
    back into the harness/judge/results machinery either."""
    source = inspect.getsource(promptfoo_module)
    tree = ast.parse(source)
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
        elif isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
    forbidden = ("harness", "judge", "judge_package", "results", "cases")
    assert not any(any(f in name for f in forbidden) for name in imported if "trackA.evaluation" in name)


def test_promptfoo_check_result_not_exported_from_trackA_schemas():
    """Deliberately kept local to this optional module, not part of the
    docs/03 canonical schema set (trackA/schemas/__init__.py)."""
    import trackA.schemas as schemas

    assert "PromptfooCheckResult" not in schemas.__all__


def test_custom_promptfoo_adapter_is_pluggable():
    class CountingAdapter(PromptfooAdapter):
        check_suite = "counting"

        def __init__(self):
            self.calls = 0

        def run_check(self, *, check_id, candidate_id, prompt):
            self.calls += 1
            return PromptfooCheckResult(check_id=check_id, candidate_id=candidate_id, passed=True)

    adapter = CountingAdapter()
    adapter.run_check(check_id="c1", candidate_id="cand-a", prompt="x")
    assert adapter.calls == 1
