import pytest

from agentshield.circuit import (
    CircuitBreaker,
    CircuitOpenError,
    CircuitState,
)


def test_circuit_starts_closed():
    circuit = CircuitBreaker()

    assert circuit.state is CircuitState.CLOSED


def test_closed_circuit_allows_operations():
    circuit = CircuitBreaker()

    circuit.check(now=0.0)

    assert circuit.state is CircuitState.CLOSED


def test_open_circuit_blocks_during_cooldown():
    circuit = CircuitBreaker(cooldown_seconds=30.0)

    circuit.open(now=100.0)

    with pytest.raises(CircuitOpenError):
        circuit.check(now=110.0)

    assert circuit.state is CircuitState.OPEN


def test_open_circuit_enters_half_open_after_cooldown():
    circuit = CircuitBreaker(
        cooldown_seconds=30.0,
        half_open_max_calls=3,
    )

    circuit.open(now=100.0)

    circuit.check(now=130.0)

    assert circuit.state is CircuitState.HALF_OPEN


def test_half_open_success_closes_circuit():
    circuit = CircuitBreaker(
        cooldown_seconds=30.0,
        half_open_max_calls=3,
    )

    circuit.open(now=100.0)
    circuit.check(now=130.0)
    circuit.record_success()

    assert circuit.state is CircuitState.CLOSED


def test_half_open_capacity_is_limited():
    circuit = CircuitBreaker(
        cooldown_seconds=30.0,
        half_open_max_calls=2,
    )

    circuit.open(now=100.0)

    circuit.check(now=130.0)
    circuit.check(now=130.0)

    with pytest.raises(CircuitOpenError):
        circuit.check(now=130.0)


def test_failure_opens_circuit():
    circuit = CircuitBreaker()

    circuit.record_failure(now=50.0)

    assert circuit.state is CircuitState.OPEN


def test_invalid_configuration_is_rejected():
    with pytest.raises(ValueError):
        CircuitBreaker(cooldown_seconds=-1.0)

    with pytest.raises(ValueError):
        CircuitBreaker(half_open_max_calls=0)