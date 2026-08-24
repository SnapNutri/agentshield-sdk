import pytest


def test_agentshield_package_imports():
    import agentshield

    assert agentshield is not None


def test_public_api_exports_expected_objects():
    from agentshield import (
        AgentSession,
        AgentShieldError,
        AgentShieldEvent,
        BudgetExceededError,
        DurationLimitExceededError,
        EventSink,
        InMemoryEventSink,
        LoopDetectedError,
        ModelPricing,
        ProtectionDecision,
        SessionStatus,
        ShieldConfig,
        StagnationDetectedError,
        StepLimitExceededError,
        ToolRepetitionError,
        calculate_token_cost,
        current_shield,
        shield,
    )

    assert all(
        value is not None
        for value in (
            AgentSession,
            AgentShieldError,
            AgentShieldEvent,
            BudgetExceededError,
            DurationLimitExceededError,
            EventSink,
            InMemoryEventSink,
            LoopDetectedError,
            ModelPricing,
            ProtectionDecision,
            SessionStatus,
            ShieldConfig,
            StagnationDetectedError,
            StepLimitExceededError,
            ToolRepetitionError,
            calculate_token_cost,
            current_shield,
            shield,
        )
    )


def test_invalid_public_configuration_has_clear_errors():
    from agentshield import ShieldConfig

    with pytest.raises(ValueError, match="max_steps"):
        ShieldConfig(max_steps=0)

    with pytest.raises(ValueError, match="stagnation_similarity"):
        ShieldConfig(stagnation_similarity=2.0)