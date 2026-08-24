from dataclasses import dataclass

from agentshield.circuit import CircuitState
from agentshield.session import SessionStatus


@dataclass(frozen=True)
class SessionReport:
    """Immutable summary of one AgentShield session."""

    session_id: str
    status: SessionStatus

    total_cost: float
    budget_limit: float | None

    step_count: int
    max_steps: int | None

    duration_seconds: float | None

    circuit_state: CircuitState
    max_duration_seconds: float | None = None
    protection_reason: str | None = None