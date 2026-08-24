from __future__ import annotations

from collections import deque
from threading import Lock
from typing import Protocol

from agentshield.events import AgentShieldEvent


class EventSink(Protocol):
    """Minimal destination interface for AgentShield events."""

    def emit(self, event: AgentShieldEvent) -> None:
        """Accept one event."""


class InMemoryEventSink:
    """Bounded event sink intended for tests and local inspection."""

    def __init__(self, max_events: int = 1_000) -> None:
        if max_events <= 0:
            raise ValueError("max_events must be positive")

        self._events: deque[AgentShieldEvent] = deque(maxlen=max_events)
        self._lock = Lock()

    @property
    def events(self) -> tuple[AgentShieldEvent, ...]:
        """Return retained events in emission order."""

        with self._lock:
            return tuple(self._events)

    def emit(self, event: AgentShieldEvent) -> None:
        """Store one event, evicting the oldest event at capacity."""

        with self._lock:
            self._events.append(event)


def emit_safely(
    sink: EventSink | None,
    event: AgentShieldEvent,
) -> None:
    """Emit telemetry without allowing sink failures to affect the SDK."""

    if sink is None:
        return

    try:
        sink.emit(event)
    except Exception:
        return
