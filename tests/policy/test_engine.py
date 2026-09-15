from __future__ import annotations

import pytest
from pydantic import ValidationError

from trackA.policy.engine import PolicyDecision, PolicyEngine


class TestPolicyDecision:
    def test_allow_with_reason_code_rejected(self):
        with pytest.raises(ValidationError):
            PolicyDecision(policy_id="x", decision="allow", reason="ok", reason_code="nope")

    def test_deny_without_reason_code_rejected(self):
        with pytest.raises(ValidationError):
            PolicyDecision(policy_id="x", decision="deny", reason="no")

    def test_valid_allow(self):
        d = PolicyDecision(policy_id="x", decision="allow", reason="ok")
        assert d.reason_code is None

    def test_valid_deny(self):
        d = PolicyDecision(policy_id="x", decision="deny", reason="no", reason_code="r")
        assert d.reason_code == "r"


class TestPolicyEngine:
    def test_unregistered_policy_denies(self):
        engine = PolicyEngine()
        decision = engine.evaluate("nonexistent", {})
        assert decision.decision == "deny"
        assert decision.reason_code == "unknown_policy"

    def test_registered_policy_allow_passthrough(self):
        engine = PolicyEngine()
        engine.register_policy("p", lambda doc: PolicyDecision(policy_id="p", decision="allow", reason="ok"))
        decision = engine.evaluate("p", {})
        assert decision.decision == "allow"

    def test_policy_exception_fails_closed(self):
        engine = PolicyEngine()

        def boom(doc):
            raise RuntimeError("kaboom")

        engine.register_policy("p", boom)
        decision = engine.evaluate("p", {})
        assert decision.decision == "deny"
        assert decision.reason_code == "policy_evaluation_error"

    def test_policy_returning_wrong_policy_id_fails_closed(self):
        engine = PolicyEngine()
        engine.register_policy(
            "p", lambda doc: PolicyDecision(policy_id="other", decision="allow", reason="ok")
        )
        decision = engine.evaluate("p", {})
        assert decision.decision == "deny"
        assert decision.reason_code == "policy_id_mismatch"

    def test_deterministic_same_input_same_output(self):
        engine = PolicyEngine()
        calls = {"n": 0}

        def counting_policy(doc):
            calls["n"] += 1
            allowed = doc.get("x") == 1
            return PolicyDecision(
                policy_id="p",
                decision="allow" if allowed else "deny",
                reason="ok" if allowed else "no",
                reason_code=None if allowed else "r",
            )

        engine.register_policy("p", counting_policy)
        d1 = engine.evaluate("p", {"x": 1})
        d2 = engine.evaluate("p", {"x": 1})
        assert d1.decision == d2.decision == "allow"
        assert calls["n"] == 2
