import asyncio
from concurrent.futures import ThreadPoolExecutor

import pytest

from agentshield import InMemoryEventSink, current_shield, shield
from agentshield.config import ShieldConfig
from agentshield.context import current_session
from agentshield.session import AgentSession


def test_async_shield_preserves_context_until_await_completes():
    async def scenario():
        captured = None

        @shield(max_duration_seconds=None)
        async def agent():
            nonlocal captured
            captured = current_session()
            await asyncio.sleep(0)
            assert current_session() is captured
            current_shield().record_step()
            return "done"

        assert await agent() == "done"
        return captured

    captured = asyncio.run(scenario())
    assert captured is not None
    with pytest.raises(RuntimeError, match="No active AgentShield session"):
        current_session()


def test_concurrent_async_agents_have_independent_sessions_and_telemetry():
    async def scenario():
        sink = InMemoryEventSink()

        @shield(max_duration_seconds=None, event_sink=sink)
        async def agent(index):
            session_id = current_session().session_id
            await asyncio.sleep(0)
            current_shield().record_step(f"step-{index}")
            await asyncio.sleep(0)
            current_shield().record_tool(f"tool-{index}")
            return session_id

        session_ids = await asyncio.gather(*(agent(index) for index in range(5)))
        return session_ids, sink

    session_ids, sink = asyncio.run(scenario())
    assert len(set(session_ids)) == 5
    for session_id in session_ids:
        events = [event for event in sink.events if event.session_id == session_id]
        assert [event.event_type for event in events] == [
            "session_started",
            "step_recorded",
            "tool_used",
            "session_finished",
        ]


def test_nested_async_shields_restore_outer_context():
    async def scenario():
        captured = []

        @shield(max_duration_seconds=None)
        async def inner():
            captured.append(current_session())
            await asyncio.sleep(0)
            assert current_session() is captured[0]

        @shield(max_duration_seconds=None)
        async def outer():
            outer_session = current_session()
            await inner()
            captured.append(current_session())
            return outer_session

        return await outer(), captured

    outer_session, captured = asyncio.run(scenario())
    assert captured[0] is not outer_session
    assert captured[1] is outer_session
    with pytest.raises(RuntimeError, match="No active AgentShield session"):
        current_session()


def test_concurrent_threads_have_independent_sessions():
    def run_session(index):
        session = AgentSession(
            ShieldConfig(max_duration_seconds=None)
        )
        session.start()
        session.record_step(f"step-{index}")
        session.finish()
        return (
            session.session_id,
            session.step_count,
            session.protection.usage.total_cost,
        )

    with ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(run_session, range(5)))

    assert len({result[0] for result in results}) == 5
    assert all(result[1:] == (1, 0.0) for result in results)
