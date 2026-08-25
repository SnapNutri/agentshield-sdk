import pytest

from agentshield import current_shield, shield
from agentshield.circuit import CircuitState
from agentshield.context import current_session
from agentshield.exceptions import (
    BudgetExceededError,
    DurationLimitExceededError,
    LoopDetectedError,
    StagnationDetectedError,
    ToolRepetitionError,
)
from agentshield.session import SessionStatus


def test_shield_runs_function():
    @shield(budget_limit=5.0)
    def add(a, b):
        return a + b

    result = add(2, 3)

    assert result == 5


def test_shield_preserves_arguments():
    @shield(budget_limit=5.0)
    def greet(name, greeting="Hello"):
        return f"{greeting}, {name}"

    result = greet(
        "Alice",
        greeting="Welcome",
    )

    assert result == "Welcome, Alice"


def test_shield_preserves_function_metadata():
    @shield(budget_limit=5.0)
    def documented_function():
        """This is an important function."""

        return 42

    assert documented_function.__name__ == "documented_function"
    assert documented_function.__doc__ == "This is an important function."


def test_shield_does_not_swallow_function_errors():
    @shield(budget_limit=5.0)
    def broken_function():
        raise ValueError("something went wrong")

    with pytest.raises(
        ValueError,
        match="something went wrong",
    ):
        broken_function()


def test_shield_completes_session():
    captured_session = None

    @shield(budget_limit=5.0)
    def successful_agent():
        nonlocal captured_session
        captured_session = current_session()
        return "done"

    result = successful_agent()

    assert result == "done"
    assert captured_session is not None
    assert captured_session.status is SessionStatus.COMPLETED


def test_shield_marks_failed_session():
    captured_session = None

    @shield(budget_limit=5.0)
    def failing_agent():
        nonlocal captured_session
        captured_session = current_session()
        raise RuntimeError("agent failed")

    with pytest.raises(RuntimeError, match="agent failed"):
        failing_agent()

    assert captured_session is not None
    assert captured_session.status is SessionStatus.FAILED


def test_shield_exposes_current_session_inside_agent():
    captured_session = None

    @shield(budget_limit=5.0)
    def my_agent():
        nonlocal captured_session
        captured_session = current_session()
        return "done"

    result = my_agent()

    assert result == "done"
    assert captured_session is not None
    assert captured_session.status is SessionStatus.COMPLETED


def test_shield_clears_context_after_execution():
    @shield(budget_limit=5.0)
    def my_agent():
        return "done"

    my_agent()

    with pytest.raises(
        RuntimeError,
        match="No active AgentShield session",
    ):
        current_session()


def test_shield_clears_context_after_exception():
    @shield(budget_limit=5.0)
    def broken_agent():
        assert current_session() is not None
        raise RuntimeError("boom")

    with pytest.raises(
        RuntimeError,
        match="boom",
    ):
        broken_agent()

    with pytest.raises(
        RuntimeError,
        match="No active AgentShield session",
    ):
        current_session()


def test_public_agentshield_api_exposes_current_shield():
    assert callable(shield)
    assert callable(current_shield)


def test_agent_can_use_current_shield():
    @shield(
        budget_limit=5.0,
        max_steps=3,
    )
    def agent():
        control = current_shield()

        control.check_before_step()
        control.record_step()

        return "success"

    assert agent() == "success"


def test_agent_can_record_llm_call():
    @shield(
        budget_limit=5.0,
        max_steps=10,
    )
    def agent():
        control = current_shield()

        control.check_before_step()

        cost = control.record_llm_call(
            model="gpt-4o-mini",
            input_tokens=1000,
            output_tokens=500,
            latency_ms=500,
        )

        control.record_step()

        return cost

    cost = agent()

    assert cost >= 0


def test_agent_stops_when_budget_is_exhausted():
    steps_completed = 0

    @shield(
        budget_limit=1.0,
        max_steps=10,
    )
    def agent():
        nonlocal steps_completed

        control = current_shield()

        control.check_before_step()

        control.record_llm_call(
            model="gpt-4o-mini",
            input_tokens=2_000_000,
            output_tokens=2_000_000,
            latency_ms=100,
        )

        control.record_step()
        steps_completed += 1

        control.check_before_step()

        steps_completed += 1

        return "should-not-reach"

    with pytest.raises(BudgetExceededError):
        agent()

    assert steps_completed == 1


def test_agent_stops_when_loop_is_detected():
    captured_session = None

    @shield(
        max_loops=3,
        cycle_length=2,
    )
    def looping_agent():
        nonlocal captured_session
        captured_session = current_session()
        control = current_shield()

        for step in ("search", "read") * 3:
            control.record_step(step)

        return "should-not-finish"

    with pytest.raises(LoopDetectedError, match="Infinite loop detected"):
        looping_agent()

    assert captured_session is not None
    assert captured_session.protection.circuit.state is CircuitState.OPEN


def test_agent_stops_when_tool_is_repeated():
    captured_session = None

    @shield(max_tool_repetitions=3)
    def repetitive_agent():
        nonlocal captured_session
        captured_session = current_session()
        control = current_shield()

        control.record_tool("search")
        control.record_tool("search")
        control.record_tool("search")

        return "should-not-finish"

    with pytest.raises(ToolRepetitionError, match="Tool repeated"):
        repetitive_agent()

    assert captured_session is not None
    assert captured_session.protection.circuit.state is CircuitState.OPEN


def test_agent_stops_when_stagnation_is_detected():
    captured_session = None

    @shield(
        max_stagnation_steps=5,
        stagnation_similarity=0.70,
    )
    def stagnant_agent():
        nonlocal captured_session
        captured_session = current_session()
        control = current_shield()

        for _ in range(5):
            control.record_response("I need more information to continue.")

        return "should-not-finish"

    with pytest.raises(StagnationDetectedError, match="stagnation"):
        stagnant_agent()

    assert captured_session is not None
    assert captured_session.protection.circuit.state is CircuitState.OPEN


def test_agent_stops_when_duration_is_exceeded():
    captured_session = None

    @shield(max_duration_seconds=5.0)
    def slow_agent():
        nonlocal captured_session
        captured_session = current_session()
        captured_session.protection._started_at -= 6.0
        current_shield().check_before_step()

    with pytest.raises(DurationLimitExceededError):
        slow_agent()

    assert captured_session is not None
    assert captured_session.status is SessionStatus.BLOCKED
    assert captured_session.protection.circuit.state is CircuitState.OPEN