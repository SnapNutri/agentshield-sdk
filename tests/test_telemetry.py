import pytest

from agentshield import (
    BudgetExceededError,
    InMemoryEventSink,
    ShieldConfig,
    shield,
)
from agentshield.events import AgentShieldEvent
from agentshield.session import AgentSession
from agentshield.usage import LLMUsage


def test_telemetry_is_disabled_without_a_sink():
    session = AgentSession(ShieldConfig(max_duration_seconds=None))

    session.start()
    session.record_step()
    session.finish()

    assert session.event_sink is None


def test_in_memory_sink_records_ordered_metadata_events():
    sink = InMemoryEventSink()
    session = AgentSession(
        ShieldConfig(max_duration_seconds=None),
        event_sink=sink,
    )

    session.start()
    session.record_step()
    session.protection.record_tool("search")
    session.protection.record_response("private response")
    session.protection.record_llm_call(
        model="gpt-4o-mini",
        input_tokens=100,
        output_tokens=50,
        latency_ms=25,
    )
    session.finish()

    assert [event.event_type for event in sink.events] == [
        "session_started",
        "step_recorded",
        "tool_used",
        "response_recorded",
        "llm_call_recorded",
        "session_finished",
    ]
    assert all(event.session_id == session.session_id for event in sink.events)
    assert sink.events[2].metadata == {"tool_name": "search"}
    assert sink.events[3].metadata == {"response_type": "str"}
    assert "private response" not in repr(sink.events[3])
    assert sink.events[4].cost is not None
    assert sink.events[4].input_tokens == 100

    with pytest.raises(TypeError):
        sink.events[0].metadata["changed"] = True


def test_protection_event_is_emitted_before_budget_exception():
    sink = InMemoryEventSink()
    session = AgentSession(
        ShieldConfig(budget_limit=1.0, max_duration_seconds=None),
        event_sink=sink,
    )
    session.start()

    session.protection.record_usage(
        LLMUsage(
            model="test-model",
            input_tokens=1,
            output_tokens=1,
            cost=2.0,
        )
    )

    with pytest.raises(BudgetExceededError):
        session.protection.check_before_operation(now=1.0)

    assert sink.events[-1].event_type == "protection_triggered"
    assert sink.events[-1].policy == "budget"
    assert sink.events[-1].decision == "block"


def test_sink_failures_do_not_affect_execution():
    class BrokenSink:
        def emit(self, event):
            raise RuntimeError("telemetry unavailable")

    session = AgentSession(
        ShieldConfig(max_duration_seconds=None),
        event_sink=BrokenSink(),
    )

    session.start()
    assert session.record_step() == 1
    session.finish()


def test_in_memory_sink_is_bounded():
    sink = InMemoryEventSink(max_events=2)

    for index in range(3):
        sink.emit(
            AgentShieldEvent(
                session_id="session",
                event_type=f"event-{index}",
            )
        )

    assert [event.event_type for event in sink.events] == [
        "event-1",
        "event-2",
    ]


def test_event_sinks_isolate_nested_sessions():
    sink = InMemoryEventSink()
    captured = []

    @shield(max_duration_seconds=None, event_sink=sink)
    def inner():
        from agentshield.context import current_session

        captured.append(current_session().session_id)

    @shield(max_duration_seconds=None, event_sink=sink)
    def outer():
        from agentshield.context import current_session

        outer_id = current_session().session_id
        inner()
        captured.append(current_session().session_id)
        return outer_id

    outer_id = outer()

    assert captured[0] != outer_id
    assert captured[1] == outer_id
    assert len({event.session_id for event in sink.events}) == 2