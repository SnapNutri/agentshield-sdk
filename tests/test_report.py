import pytest

from agentshield.circuit import CircuitState
from agentshield.config import ShieldConfig
from agentshield.session import (
    AgentSession,
    SessionStatus,
    StepLimitExceededError,
)


def test_session_report_contains_execution_summary():
    session = AgentSession(
        ShieldConfig(
            budget_limit=5.0,
            max_steps=10,
        )
    )

    session.start()

    session.record_step()
    session.record_step()

    session.finish()

    report = session.report()

    assert report.session_id == session.session_id
    assert report.status is SessionStatus.COMPLETED

    assert report.total_cost == 0.0
    assert report.budget_limit == 5.0

    assert report.step_count == 2
    assert report.max_steps == 10
    assert report.max_duration_seconds == 60.0
    assert report.protection_reason is None

    assert report.duration_seconds is not None
    assert report.duration_seconds >= 0

    assert report.circuit_state is CircuitState.CLOSED


def test_session_report_shows_blocked_status():
    session = AgentSession(
        ShieldConfig(
            budget_limit=5.0,
            max_steps=1,
        )
    )

    session.start()

    session.record_step()

    try:
        session.record_step()
    except StepLimitExceededError:
        pass

    report = session.report()

    assert report.status is SessionStatus.BLOCKED
    assert report.step_count == 1
    assert report.max_steps == 1


def test_session_report_is_immutable():
    session = AgentSession(
        ShieldConfig(
            budget_limit=5.0,
        )
    )

    session.start()
    session.finish()

    report = session.report()

    with pytest.raises(AttributeError):
        report.total_cost = 100.0