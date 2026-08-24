import pytest

from agentshield.circuit import (
    CircuitState,
)
from agentshield.config import ShieldConfig
from agentshield.exceptions import (
    BudgetExceededError,
    DurationLimitExceededError,
)
from agentshield.protection import ProtectionController
from agentshield.usage import LLMUsage


def make_controller() -> ProtectionController:
    """Create a test protection controller."""

    return ProtectionController(
        ShieldConfig(
            budget_limit=5.0,
        )
    )


def test_protection_allows_operation_with_budget_remaining():
    controller = make_controller()

    controller.check_before_operation(now=0.0)

    assert controller.circuit.state is CircuitState.CLOSED


def test_budget_does_not_block_when_under_limit():
    controller = make_controller()

    controller.record_usage(
        LLMUsage(
            model="test-model",
            input_tokens=1_000,
            output_tokens=1_000,
            cost=4.99,
        ),
        now=10.0,
    )

    controller.check_before_operation(now=11.0)

    assert controller.circuit.state is CircuitState.CLOSED


def test_protection_opens_circuit_when_budget_is_exhausted():
    controller = make_controller()

    controller.record_usage(
        LLMUsage(
            model="test-model",
            input_tokens=1_000,
            output_tokens=1_000,
            cost=5.0,
        ),
        now=10.0,
    )

    assert controller.circuit.state is CircuitState.OPEN


def test_budget_exhaustion_raises_budget_error():
    controller = make_controller()

    controller.record_usage(
        LLMUsage(
            model="test-model",
            input_tokens=1_000,
            output_tokens=1_000,
            cost=5.0,
        ),
        now=10.0,
    )

    with pytest.raises(BudgetExceededError, match="Budget limit reached"):
        controller.check_before_operation(now=11.0)


def test_exact_budget_limit_blocks_agent():
    controller = make_controller()

    controller.record_usage(
        LLMUsage(
            model="test-model",
            input_tokens=1_000,
            output_tokens=1_000,
            cost=5.0,
        ),
        now=10.0,
    )

    with pytest.raises(BudgetExceededError):
        controller.check_before_operation(now=11.0)

    assert controller.circuit.state is CircuitState.OPEN


def test_unrelated_errors_do_not_open_circuit():
    controller = make_controller()

    class BrokenUsage:
        @property
        def total_cost(self):
            raise RuntimeError("unrelated failure")

    controller.usage = BrokenUsage()

    with pytest.raises(RuntimeError, match="unrelated failure"):
        controller.check_before_operation(now=0.0)

    assert controller.circuit.state is CircuitState.CLOSED


def test_duration_protection_disabled():
    controller = ProtectionController(
        ShieldConfig(max_duration_seconds=None)
    )
    controller.start(now=0.0)

    controller.check_before_operation(now=1_000.0)

    assert controller.circuit.state is CircuitState.CLOSED


def test_duration_below_limit_allows_operation():
    controller = ProtectionController(
        ShieldConfig(max_duration_seconds=5.0)
    )
    controller.start(now=10.0)

    controller.check_before_operation(now=14.99)

    assert controller.circuit.state is CircuitState.CLOSED


@pytest.mark.parametrize("now", [15.0, 16.0])
def test_duration_at_or_above_limit_blocks_operation(now):
    controller = ProtectionController(
        ShieldConfig(max_duration_seconds=5.0)
    )
    controller.start(now=10.0)

    with pytest.raises(DurationLimitExceededError, match="Duration limit reached"):
        controller.check_before_operation(now=now)

    assert controller.circuit.state is CircuitState.OPEN