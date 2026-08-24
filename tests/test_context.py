import pytest

from agentshield.config import ShieldConfig
from agentshield.context import (
    current_session,
    reset_current_session,
    set_current_session,
)
from agentshield.session import AgentSession


def test_current_session_returns_active_session():
    session = AgentSession(
        ShieldConfig(
            budget_limit=5.0,
        )
    )

    token = set_current_session(session)

    try:
        assert current_session() is session

    finally:
        reset_current_session(token)


def test_current_session_requires_active_session():
    with pytest.raises(
        RuntimeError,
        match="No active AgentShield session",
    ):
        current_session()


def test_reset_restores_previous_context():
    session_one = AgentSession(
        ShieldConfig(
            budget_limit=5.0,
        )
    )

    session_two = AgentSession(
        ShieldConfig(
            budget_limit=10.0,
        )
    )

    token_one = set_current_session(session_one)

    try:
        assert current_session() is session_one

        token_two = set_current_session(session_two)

        try:
            assert current_session() is session_two

        finally:
            reset_current_session(token_two)

        assert current_session() is session_one

    finally:
        reset_current_session(token_one)


def test_nested_shield_restores_outer_context():
    from agentshield.sdk import shield

    captured = []

    @shield(max_duration_seconds=None)
    def inner():
        captured.append(current_session())

    @shield(max_duration_seconds=None)
    def outer():
        outer_session = current_session()
        inner()
        captured.append(current_session())
        return outer_session

    outer_session = outer()

    assert captured == [captured[0], outer_session]
    assert captured[0] is not outer_session
    with pytest.raises(RuntimeError, match="No active AgentShield session"):
        current_session()