from __future__ import annotations

import time

from agentshield.context import current_session
from agentshield.exceptions import AgentShieldError, StepLimitExceededError
from agentshield.session import SessionStatus


class ShieldControl:
    """Public control interface for the active AgentShield session."""

    def check_before_step(self) -> None:
        """Check whether another agent step may begin."""

        session = current_session()

        try:
            session.protection.check_before_operation(
                now=time.monotonic(),
            )
        except AgentShieldError:
            session.finish(SessionStatus.BLOCKED)
            raise

        max_steps = session.config.max_steps

        if (
            max_steps is not None
            and session.step_count >= max_steps
        ):
            session.protection.record_step_limit_decision(
                session.step_count,
                max_steps,
            )
            session.finish(SessionStatus.BLOCKED)

            raise StepLimitExceededError(
                f"Maximum step limit reached: "
                f"{session.step_count} / {max_steps}"
            )

    def record_step(self, step: object | None = None) -> int:
        """Record a completed agent step."""

        session = current_session()

        return session.record_step(step)

    def record_tool(self, tool_name: str) -> None:
        """Record a tool call for repetition detection."""

        session = current_session()

        try:
            session.protection.record_tool(tool_name)
        except AgentShieldError:
            session.finish(SessionStatus.BLOCKED)
            raise

    def record_response(self, response: object) -> None:
        """Record an agent response for stagnation detection."""

        session = current_session()

        try:
            session.protection.record_response(response)
        except AgentShieldError:
            session.finish(SessionStatus.BLOCKED)
            raise

    def record_llm_call(
        self,
        *,
        model: str,
        input_tokens: int,
        output_tokens: int,
        latency_ms: float,
    ) -> float:
        """Record one LLM call and return its cost."""

        session = current_session()

        return session.protection.record_llm_call(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
        )


def current_shield() -> ShieldControl:
    """Return the control interface for the active session."""

    current_session()
    return ShieldControl()