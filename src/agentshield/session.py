from __future__ import annotations

import time
import uuid
from enum import Enum
from typing import TYPE_CHECKING

from agentshield.config import ShieldConfig
from agentshield.events import AgentShieldEvent
from agentshield.exceptions import AgentShieldError, StepLimitExceededError
from agentshield.protection import ProtectionController
from agentshield.telemetry import EventSink, emit_safely

if TYPE_CHECKING:
    from agentshield.report import SessionReport


class SessionStatus(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"

    PENDING = CREATED
    ACTIVE = RUNNING
    FINISHED = COMPLETED


class AgentSession:
    """Manages one protected agent execution."""

    def __init__(
        self,
        config: ShieldConfig | None = None,
        event_sink: EventSink | None = None,
    ) -> None:
        self.session_id = str(uuid.uuid4())

        self.config = (
            config
            if config is not None
            else ShieldConfig()
        )

        self.protection = ProtectionController(
            self.config,
            event_sink=event_sink,
            session_id=self.session_id,
        )
        self.event_sink = event_sink

        self.status = SessionStatus.CREATED
        self.step_count = 0

        self.started_at: float | None = None
        self.finished_at: float | None = None

    def start(self) -> None:
        """Start the session."""

        if self.status is not SessionStatus.CREATED:
            raise RuntimeError("Session has already started")

        self.status = SessionStatus.RUNNING
        self.started_at = time.monotonic()
        self.protection.start(now=self.started_at)
        self.finished_at = None
        emit_safely(
            self.event_sink,
            AgentShieldEvent(
                session_id=self.session_id,
                event_type="session_started",
            ),
        )

    def finish(
        self,
        status: SessionStatus = SessionStatus.FINISHED,
    ) -> None:
        """Finish the session with the supplied final status."""

        if self.status is SessionStatus.CREATED:
            raise RuntimeError("Session has not started")

        self.status = status

        if self.finished_at is None:
            self.finished_at = time.monotonic()

        emit_safely(
            self.event_sink,
            AgentShieldEvent(
                session_id=self.session_id,
                event_type="session_finished",
                duration=self.duration_seconds,
                decision=self.status.value,
                protection_reason=self.protection.protection_reason,
            ),
        )

    def record_step(self, step: object | None = None) -> int:
        """Record one completed agent step."""

        if self.status is not SessionStatus.RUNNING:
            raise RuntimeError("Session is not running")

        if (
            self.config.max_steps is not None
            and self.step_count >= self.config.max_steps
        ):
            self.status = SessionStatus.BLOCKED
            self.protection.record_step_limit_decision(
                self.step_count,
                self.config.max_steps,
            )

            raise StepLimitExceededError(
                "Maximum step limit exceeded"
            )

        try:
            self.protection.record_step(step)
        except AgentShieldError:
            self.status = SessionStatus.BLOCKED
            raise
        self.step_count += 1

        return self.step_count

    @property
    def duration_seconds(self) -> float:
        """Return the session duration in seconds."""

        if self.started_at is None:
            return 0.0

        end = (
            self.finished_at
            if self.finished_at is not None
            else time.monotonic()
        )

        return end - self.started_at

    def report(self) -> "SessionReport":
        """Create a report representing this session."""

        from agentshield.report import SessionReport

        return SessionReport(
            session_id=self.session_id,
            status=self.status,
            total_cost=self.protection.usage.total_cost,
            budget_limit=self.config.budget_limit,
            step_count=self.step_count,
            max_steps=self.config.max_steps,
            duration_seconds=self.duration_seconds,
            circuit_state=self.protection.circuit.state,
            max_duration_seconds=self.config.max_duration_seconds,
            protection_reason=self.protection.protection_reason,
        )