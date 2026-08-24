from functools import wraps
import inspect
from typing import Any, Callable, TypeVar

from agentshield.config import ShieldConfig
from agentshield.telemetry import EventSink
from agentshield.context import (
    reset_current_session,
    set_current_session,
)
from agentshield.session import AgentSession, SessionStatus
from agentshield.exceptions import AgentShieldError


F = TypeVar("F", bound=Callable[..., Any])
_UNSET = object()


def shield(
    *,
    budget_limit: float | None = 5.0,
    max_steps: int | None = 20,
    max_latency_seconds: float | None = 60.0,
    max_duration_seconds: float | None | object = _UNSET,
    circuit_cooldown_seconds: float = 30.0,
    circuit_half_open_max_calls: int = 3,
    max_loops: int | None = None,
    cycle_length: int = 2,
    max_tool_repetitions: int | None = None,
    max_stagnation_steps: int | None = None,
    stagnation_similarity: float = 0.70,
    event_sink: EventSink | None = None,
) -> Callable[[F], F]:
    """Protect an agent function with AgentShield."""

    if max_duration_seconds is _UNSET:
        max_duration_seconds = max_latency_seconds
    elif max_latency_seconds != 60.0:
        raise TypeError(
            "Provide either max_duration_seconds or max_latency_seconds, not both"
        )

    config = ShieldConfig(
        budget_limit=budget_limit,
        max_steps=max_steps,
        max_duration_seconds=max_duration_seconds,
        circuit_cooldown_seconds=circuit_cooldown_seconds,
        circuit_half_open_max_calls=circuit_half_open_max_calls,
        max_loops=max_loops,
        cycle_length=cycle_length,
        max_tool_repetitions=max_tool_repetitions,
        max_stagnation_steps=max_stagnation_steps,
        stagnation_similarity=stagnation_similarity,
    )

    def decorator(function: F) -> F:
        if inspect.iscoroutinefunction(function):
            @wraps(function)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                session = AgentSession(config, event_sink=event_sink)
                session.start()
                token = set_current_session(session)

                try:
                    result = await function(*args, **kwargs)
                except AgentShieldError:
                    if session.status is SessionStatus.RUNNING:
                        session.finish(SessionStatus.BLOCKED)
                    raise
                except Exception:
                    if session.status is SessionStatus.RUNNING:
                        session.finish(SessionStatus.FAILED)
                    raise
                else:
                    session.finish(SessionStatus.COMPLETED)
                    return result
                finally:
                    reset_current_session(token)

            return async_wrapper  # type: ignore[return-value]

        @wraps(function)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            session = AgentSession(config, event_sink=event_sink)

            session.start()

            token = set_current_session(session)

            try:
                result = function(*args, **kwargs)

            except AgentShieldError:
                if session.status is SessionStatus.RUNNING:
                    session.finish(SessionStatus.BLOCKED)

                raise

            except Exception:
                if session.status is SessionStatus.RUNNING:
                    session.finish(SessionStatus.FAILED)

                raise

            else:
                session.finish(SessionStatus.COMPLETED)

                return result

            finally:
                reset_current_session(token)

        return wrapper  # type: ignore[return-value]

    return decorator