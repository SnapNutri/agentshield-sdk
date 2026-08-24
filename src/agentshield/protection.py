from __future__ import annotations

import time

from agentshield.anomaly import AnomalyDetector
from agentshield.circuit import CircuitBreaker
from agentshield.config import ShieldConfig
from agentshield.costs import calculate_token_cost
from agentshield.exceptions import (
    BudgetExceededError,
    DurationLimitExceededError,
    LoopDetectedError,
    StagnationDetectedError,
    ToolRepetitionError,
)
from agentshield.events import AgentShieldEvent
from agentshield.decisions import ProtectionDecision
from agentshield.telemetry import EventSink, emit_safely
from agentshield.usage import LLMUsage, UsageTracker


_UNSET = object()


class ProtectionController:
    """Coordinates budget enforcement, circuit breaking, and usage tracking."""

    def __init__(
        self,
        config_or_budget: ShieldConfig | float | None = None,
        circuit: CircuitBreaker | None = None,
        *,
        budget_limit: float | None | object = _UNSET,
        event_sink: EventSink | None = None,
        session_id: str = "",
    ) -> None:
        """Create a protection controller. Accepts either a ShieldConfig or a direct budget value."""
        if budget_limit is not _UNSET:
            if config_or_budget is not None:
                raise TypeError(
                    "Provide either config_or_budget or budget_limit, not both"
                )
            config_or_budget = budget_limit  # type: ignore[assignment]

        if isinstance(config_or_budget, ShieldConfig):
            self.config = config_or_budget
            self.budget_limit = config_or_budget.budget_limit
        else:
            self.config = ShieldConfig(budget_limit=config_or_budget)
            self.budget_limit = config_or_budget

        self.usage = UsageTracker()
        self.event_sink = event_sink
        self.session_id = session_id
        self._started_at: float | None = None
        self.protection_reason: str | None = None
        self.last_decision: ProtectionDecision | None = None
        self._operation_index = 0
        self.anomaly = (
            AnomalyDetector(
                max_loops=self.config.max_loops,
                cycle_length=self.config.cycle_length,
                max_tool_repetitions=self.config.max_tool_repetitions,
                max_stagnation_steps=self.config.max_stagnation_steps,
                stagnation_similarity=self.config.stagnation_similarity,
            )
            if (
                self.config.max_loops is not None
                or self.config.max_tool_repetitions is not None
                or self.config.max_stagnation_steps is not None
            )
            else None
        )
        self.circuit = (
            circuit
            if circuit is not None
            else CircuitBreaker(
                cooldown_seconds=self.config.circuit_cooldown_seconds,
                half_open_max_calls=self.config.circuit_half_open_max_calls,
            )
        )

    def _budget_exhausted(self) -> bool:
        """Return True when the configured budget has been exhausted."""

        if self.budget_limit is None:
            return False

        return self.usage.total_cost >= self.budget_limit

    def start(self, now: float | None = None) -> None:
        """Start tracking elapsed duration for this controller."""

        self._started_at = time.monotonic() if now is None else now

    def _emit(
        self,
        event_type: str,
        *,
        policy: str | None = None,
        decision: str | None = None,
        cost: float | None = None,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        metadata: dict[str, object] | None = None,
    ) -> None:
        """Emit a protection event when a session sink is configured."""

        emit_safely(
            self.event_sink,
            AgentShieldEvent(
                session_id=self.session_id,
                event_type=event_type,
                operation_index=None,
                policy=policy,
                decision=decision,
                cost=cost,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                metadata=metadata or {},
            ),
        )

    def _set_decision(
        self,
        *,
        allowed: bool,
        policy: str,
        reason: str,
        now: float,
        current_value: float | int | None = None,
        configured_limit: float | int | None = None,
        metadata: dict[str, object] | None = None,
    ) -> ProtectionDecision:
        decision = ProtectionDecision(
            allowed=allowed,
            policy=policy,
            reason=reason,
            session_id=self.session_id or None,
            operation_index=self._operation_index,
            current_value=current_value,
            configured_limit=configured_limit,
            metadata=metadata or {},
        )
        self.last_decision = decision
        emit_safely(
            self.event_sink,
            AgentShieldEvent(
                session_id=self.session_id,
                event_type="protection_decision",
                timestamp=decision.timestamp,
                operation_index=decision.operation_index,
                policy=decision.policy,
                decision="allow" if decision.allowed else "block",
                protection_reason=decision.reason,
                metadata={
                    **dict(decision.metadata),
                    "current_value": decision.current_value,
                    "configured_limit": decision.configured_limit,
                },
            ),
        )
        return decision

    def _trip_circuit(self, now: float | None = None) -> None:
        """Open/trip the circuit using whichever API it provides."""

        if hasattr(self.circuit, "trip"):
            self.circuit.trip(now=now)
            return

        if hasattr(self.circuit, "open"):
            self.circuit.open(
                now=time.monotonic() if now is None else now
            )

    def check_before_operation(
        self,
        now: float | None = None,
    ) -> ProtectionDecision:
        """Check session safety constraints before an operation step."""

        if now is None:
            now = time.monotonic()

        self._operation_index += 1

        if (
            self.config.max_duration_seconds is not None
            and self._started_at is not None
            and now - self._started_at >= self.config.max_duration_seconds
        ):
            self._set_decision(
                allowed=False,
                policy="duration",
                reason="duration_exceeded",
                now=now,
                current_value=now - self._started_at,
                configured_limit=self.config.max_duration_seconds,
            )
            self._trip_circuit(now=now)
            self.protection_reason = "duration"
            self._emit(
                "protection_triggered",
                policy="duration",
                decision="block",
            )

            raise DurationLimitExceededError(
                f"Duration limit reached: "
                f"{now - self._started_at:.6f} / "
                f"{self.config.max_duration_seconds:.6f} seconds"
            )

        if self._budget_exhausted():
            self._set_decision(
                allowed=False,
                policy="budget",
                reason="budget_exceeded",
                now=now,
                current_value=self.usage.total_cost,
                configured_limit=self.budget_limit,
            )
            self._trip_circuit(now=now)
            self.protection_reason = "budget"
            self._emit(
                "protection_triggered",
                policy="budget",
                decision="block",
            )

            raise BudgetExceededError(
                f"Budget limit reached: "
                f"{self.usage.total_cost:.6f} / "
                f"{self.budget_limit:.6f}"
            )

        try:
            if hasattr(self.circuit, "check"):
                self.circuit.check(now=now)
            elif hasattr(self.circuit, "check_state"):
                self.circuit.check_state(now=now)
        except Exception as error:
            self._set_decision(
                allowed=False,
                policy="circuit",
                reason="circuit_already_open",
                now=now,
                metadata={"error_type": type(error).__name__},
            )
            raise

        return self._set_decision(
            allowed=True,
            policy="circuit",
            reason="operation_allowed",
            now=now,
        )

    def record_usage(
        self,
        usage: LLMUsage | float,
        now: float | None = None,
    ) -> None:
        """Record usage and enforce the budget."""

        if hasattr(self.usage, "record"):
            self.usage.record(usage)

        elif hasattr(self.usage, "record_usage"):
            self.usage.record_usage(usage)

        elif hasattr(self.usage, "add"):
            self.usage.add(usage)

        if self._budget_exhausted():
            self._trip_circuit(now=now)
            self.protection_reason = "budget"
            self._emit(
                "budget_exhausted",
                policy="budget",
                decision="block",
                cost=self.usage.total_cost,
            )

    def record_step(self, step: object | None = None) -> None:
        """Record a step signature and stop execution when a loop is detected."""

        self._emit("step_recorded", decision="allow")

        if self.anomaly is None or step is None:
            return

        self.anomaly.record(step)

        if self.anomaly.is_loop_detected():
            self._set_decision(
                allowed=False,
                policy="loop",
                reason="loop_detected",
                now=time.monotonic(),
            )
            self._trip_circuit()
            self.protection_reason = "loop"
            self._emit(
                "protection_triggered",
                policy="loop",
                decision="block",
            )

            raise LoopDetectedError(
                f"Infinite loop detected: repeating cycle of "
                f"{self.anomaly.cycle_length} steps"
            )

    def record_tool(self, tool_name: str) -> None:
        """Record a tool call and stop execution on excessive repetition."""

        self._emit(
            "tool_used",
            decision="allow",
            metadata={"tool_name": tool_name},
        )

        if self.anomaly is None:
            return

        if self.anomaly.record_tool(tool_name):
            self._set_decision(
                allowed=False,
                policy="tool_repetition",
                reason="tool_repetition_detected",
                now=time.monotonic(),
                metadata={"tool_name": tool_name},
            )
            self._trip_circuit()
            self.protection_reason = "tool_repetition"
            self._emit(
                "protection_triggered",
                policy="tool_repetition",
                decision="block",
                metadata={"tool_name": tool_name},
            )

            raise ToolRepetitionError(
                f"Tool repeated too many times consecutively: {tool_name}"
            )

    def record_response(self, response: object) -> None:
        """Record a response and stop execution when stagnation is detected."""

        self._emit(
            "response_recorded",
            decision="allow",
            metadata={"response_type": type(response).__name__},
        )

        if self.anomaly is None:
            return

        if self.anomaly.record_response(response):
            self._set_decision(
                allowed=False,
                policy="stagnation",
                reason="stagnation_detected",
                now=time.monotonic(),
                metadata={"response_type": type(response).__name__},
            )
            self._trip_circuit()
            self.protection_reason = "stagnation"
            self._emit(
                "protection_triggered",
                policy="stagnation",
                decision="block",
                metadata={"response_type": type(response).__name__},
            )

            raise StagnationDetectedError(
                "Agent stagnation detected: recent responses are too similar"
            )

    def record_step_limit_decision(
        self,
        current_value: int,
        configured_limit: int,
    ) -> ProtectionDecision:
        """Record the decision made when the step limit blocks execution."""

        self.protection_reason = "step_limit"

        return self._set_decision(
            allowed=False,
            policy="step_limit",
            reason="step_limit_exceeded",
            now=time.monotonic(),
            current_value=current_value,
            configured_limit=configured_limit,
        )

    def record_llm_call(
        self,
        *,
        model: str,
        input_tokens: int,
        output_tokens: int,
        latency_ms: float,
        now: float | None = None,
    ) -> float:
        """
        Calculate and record one LLM call.

        Returns the calculated cost in USD.
        """

        cost = calculate_token_cost(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

        usage_obj = LLMUsage(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost,
        )

        self.record_usage(
            usage_obj,
            now=now,
        )

        self._emit(
            "llm_call_recorded",
            decision="allow",
            cost=cost,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            metadata={"model": model, "latency_ms": latency_ms},
        )

        return cost