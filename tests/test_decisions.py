import pytest

from agentshield.circuit import CircuitOpenError, CircuitState
from agentshield.config import ShieldConfig
from agentshield.decisions import ProtectionDecision
from agentshield.exceptions import BudgetExceededError
from agentshield.protection import ProtectionController
from agentshield.telemetry import InMemoryEventSink
from agentshield.usage import LLMUsage


def test_allowed_decision_contains_policy_and_operation_index():
    controller = ProtectionController(
        ShieldConfig(max_duration_seconds=None)
    )

    decision = controller.check_before_operation(now=1.0)

    assert decision.allowed is True
    assert decision.blocked is False
    assert decision.policy == "circuit"
    assert decision.reason == "operation_allowed"
    assert decision.operation_index == 1


def test_budget_decision_contains_current_value_and_limit():
    controller = ProtectionController(
        ShieldConfig(budget_limit=1.0, max_duration_seconds=None)
    )
    controller.record_usage(
        LLMUsage(
            model="test-model",
            input_tokens=1,
            output_tokens=1,
            cost=1.5,
        )
    )

    with pytest.raises(BudgetExceededError):
        controller.check_before_operation(now=1.0)

    decision = controller.last_decision
    assert decision is not None
    assert decision.allowed is False
    assert decision.policy == "budget"
    assert decision.reason == "budget_exceeded"
    assert decision.current_value == 1.5
    assert decision.configured_limit == 1.0


def test_circuit_open_decision_is_recorded():
    controller = ProtectionController(
        ShieldConfig(max_duration_seconds=None)
    )
    controller.circuit.open(now=0.0)

    with pytest.raises(CircuitOpenError):
        controller.check_before_operation(now=1.0)

    decision = controller.last_decision
    assert decision is not None
    assert decision.allowed is False
    assert decision.policy == "circuit"
    assert decision.reason == "circuit_already_open"
    assert controller.circuit.state is CircuitState.OPEN


def test_decision_telemetry_uses_structured_values():
    sink = InMemoryEventSink()
    controller = ProtectionController(
        ShieldConfig(max_duration_seconds=None),
        event_sink=sink,
        session_id="session-1",
    )

    controller.check_before_operation(now=1.0)

    event = sink.events[-1]
    assert event.event_type == "protection_decision"
    assert event.session_id == "session-1"
    assert event.policy == "circuit"
    assert event.protection_reason == "operation_allowed"
    assert event.metadata["current_value"] is None


def test_protection_decision_is_immutable():
    decision = ProtectionDecision(
        allowed=True,
        policy="test",
        reason="allowed",
        metadata={"source": "test"},
    )

    with pytest.raises(AttributeError):
        decision.allowed = False

    with pytest.raises(TypeError):
        decision.metadata["changed"] = True