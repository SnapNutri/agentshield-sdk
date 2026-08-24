import pytest

from agentshield.config import ShieldConfig


def test_default_config_values():
    config = ShieldConfig()
    assert config.budget_limit == 5.0
    assert config.max_steps == 20
    assert config.max_latency_seconds == 60.0
    assert config.max_duration_seconds == 60.0
    assert config.circuit_cooldown_seconds == 30.0
    assert config.circuit_half_open_max_calls == 3


def test_custom_config_values():
    config = ShieldConfig(
        budget_limit=10.0,
        circuit_cooldown_seconds=15.0,
        circuit_half_open_max_calls=5,
    )
    assert config.budget_limit == 10.0
    assert config.circuit_cooldown_seconds == 15.0
    assert config.circuit_half_open_max_calls == 5


def test_circuit_configuration_defaults():
    config = ShieldConfig()
    assert config.circuit_cooldown_seconds == 30.0
    assert config.circuit_half_open_max_calls == 3


def test_invalid_circuit_cooldown_is_rejected():
    with pytest.raises(ValueError, match="circuit_cooldown_seconds"):
        ShieldConfig(
            circuit_cooldown_seconds=-1.0,
        )


def test_invalid_half_open_call_limit_is_rejected():
    with pytest.raises(
        ValueError,
        match="circuit_half_open_max_calls",
    ):
        ShieldConfig(
            circuit_half_open_max_calls=0,
        )


def test_duration_configuration_is_validated():
    assert ShieldConfig(max_duration_seconds=None).max_duration_seconds is None

    with pytest.raises(ValueError):
        ShieldConfig(max_duration_seconds=-1.0)

    with pytest.raises(ValueError):
        ShieldConfig(max_duration_seconds=float("nan"))

    with pytest.raises(ValueError):
        ShieldConfig(max_duration_seconds=float("inf"))


def test_legacy_latency_configuration_maps_to_duration():
    config = ShieldConfig(max_latency_seconds=12.0)

    assert config.max_duration_seconds == 12.0
    assert config.max_latency_seconds == 12.0