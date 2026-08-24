import pytest

from agentshield.config import ShieldConfig
from agentshield.exceptions import DurationLimitExceededError
from agentshield.session import (
    AgentSession,
    SessionStatus,
    StepLimitExceededError,
)


def make_session() -> AgentSession:
    """Create a test session."""

    return AgentSession(
        ShieldConfig(
            budget_limit=5.0,
        )
    )


def test_session_starts_in_created_state():
    session = make_session()

    assert session.status is SessionStatus.CREATED
    assert session.started_at is None
    assert session.finished_at is None
    assert session.step_count == 0


def test_session_start_changes_status_to_running():
    session = make_session()

    session.start()

    assert session.status is SessionStatus.RUNNING
    assert session.started_at is not None


def test_session_can_record_steps():
    session = make_session()

    session.start()

    assert session.record_step() == 1
    assert session.record_step() == 2
    assert session.record_step() == 3

    assert session.step_count == 3


def test_session_finish_changes_status():
    session = make_session()

    session.start()
    session.finish()

    assert session.status is SessionStatus.COMPLETED
    assert session.finished_at is not None


def test_session_can_finish_as_blocked():
    session = make_session()

    session.start()
    session.finish(SessionStatus.BLOCKED)

    assert session.status is SessionStatus.BLOCKED


def test_session_cannot_start_twice():
    session = make_session()

    session.start()

    with pytest.raises(RuntimeError):
        session.start()


def test_session_cannot_finish_before_start():
    session = make_session()

    with pytest.raises(RuntimeError):
        session.finish()


def test_session_cannot_record_step_before_start():
    session = make_session()

    with pytest.raises(RuntimeError):
        session.record_step()


def test_session_duration_is_available_while_running():
    session = make_session()

    session.start()

    duration = session.duration_seconds

    assert duration is not None
    assert duration >= 0


def test_session_duration_is_available_after_finish():
    session = make_session()

    session.start()
    session.finish()

    duration = session.duration_seconds

    assert duration is not None
    assert duration >= 0


def test_each_session_has_unique_id():
    session_one = make_session()
    session_two = make_session()

    assert session_one.session_id != session_two.session_id


def test_session_blocks_when_step_limit_is_exceeded():
    session = AgentSession(
        ShieldConfig(
            budget_limit=5.0,
            max_steps=3,
        )
    )

    session.start()

    assert session.record_step() == 1
    assert session.record_step() == 2
    assert session.record_step() == 3

    with pytest.raises(
        StepLimitExceededError,
        match="Maximum step limit exceeded",
    ):
        session.record_step()

    assert session.step_count == 3
    assert session.status is SessionStatus.BLOCKED


def test_session_allows_unlimited_steps_when_max_steps_is_none():
    session = AgentSession(
        ShieldConfig(
            budget_limit=5.0,
            max_steps=None,
        )
    )

    session.start()

    for _ in range(100):
        session.record_step()

    assert session.step_count == 100
    assert session.status is SessionStatus.RUNNING


def test_session_duration_limit_blocks_operation():
    session = AgentSession(
        ShieldConfig(max_duration_seconds=5.0)
    )
    session.protection.start(now=10.0)
    session.started_at = 10.0
    session.status = SessionStatus.RUNNING

    with pytest.raises(DurationLimitExceededError):
        session.protection.check_before_operation(now=15.0)

    assert session.protection.circuit.state.value == "open"