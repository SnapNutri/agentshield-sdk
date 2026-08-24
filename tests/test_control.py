import pytest

from agentshield.config import ShieldConfig
from agentshield.context import reset_current_session, set_current_session
from agentshield.control import ShieldControl, current_shield
from agentshield.session import (
    AgentSession,
    SessionStatus,
    StepLimitExceededError,
)


def make_session(
    max_steps: int | None = 3,
) -> AgentSession:
    return AgentSession(
        ShieldConfig(
            budget_limit=5.0,
            max_steps=max_steps,
        )
    )


def test_current_shield_returns_control_object():
    session = make_session()

    session.start()

    token = set_current_session(session)

    try:
        control = current_shield()

        assert isinstance(control, ShieldControl)

    finally:
        reset_current_session(token)


def test_check_before_step_allows_operation():
    session = make_session()

    session.start()

    token = set_current_session(session)

    try:
        control = current_shield()

        control.check_before_step()

    finally:
        reset_current_session(token)


def test_record_step_records_completed_step():
    session = make_session()

    session.start()

    token = set_current_session(session)

    try:
        control = current_shield()

        assert control.record_step() == 1
        assert session.step_count == 1

    finally:
        reset_current_session(token)


def test_check_before_step_blocks_when_limit_reached():
    session = make_session(max_steps=2)

    session.start()

    token = set_current_session(session)

    try:
        control = current_shield()

        control.record_step()
        control.record_step()

        with pytest.raises(
            StepLimitExceededError,
            match="Maximum step limit reached",
        ):
            control.check_before_step()

        assert session.status is SessionStatus.BLOCKED

    finally:
        reset_current_session(token)


def test_current_shield_requires_active_session():
    with pytest.raises(
        RuntimeError,
        match="No active AgentShield session",
    ):
        current_shield()


def test_record_llm_call_returns_cost():
    session = make_session()

    session.start()

    token = set_current_session(session)

    try:
        control = current_shield()

        cost = control.record_llm_call(
            model="gpt-4o-mini",
            input_tokens=1000,
            output_tokens=500,
            latency_ms=850,
        )

        assert cost >= 0
        assert session.protection.usage.total_cost == cost

    finally:
        reset_current_session(token)


def test_multiple_llm_calls_accumulate_cost():
    session = make_session()

    session.start()

    token = set_current_session(session)

    try:
        control = current_shield()

        first_cost = control.record_llm_call(
            model="gpt-4o-mini",
            input_tokens=1000,
            output_tokens=500,
            latency_ms=500,
        )

        second_cost = control.record_llm_call(
            model="gpt-4o-mini",
            input_tokens=2000,
            output_tokens=1000,
            latency_ms=700,
        )

        expected = first_cost + second_cost

        assert session.protection.usage.total_cost == expected

    finally:
        reset_current_session(token)