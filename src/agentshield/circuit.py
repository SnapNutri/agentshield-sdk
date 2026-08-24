from enum import Enum
from threading import RLock


class CircuitState(str, Enum):
    """Possible states of the AgentShield circuit breaker."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitOpenError(RuntimeError):
    """Raised when the circuit blocks an operation."""


class CircuitBreaker:
    """A three-state runtime circuit breaker."""

    def __init__(
        self,
        *,
        cooldown_seconds: float = 30.0,
        half_open_max_calls: int = 3,
    ) -> None:
        if cooldown_seconds < 0:
            raise ValueError("cooldown_seconds cannot be negative")

        if half_open_max_calls <= 0:
            raise ValueError("half_open_max_calls must be positive")

        self._cooldown_seconds = cooldown_seconds
        self._half_open_max_calls = half_open_max_calls

        self._state = CircuitState.CLOSED
        self._opened_at: float | None = None
        self._half_open_calls = 0
        self._lock = RLock()

    @property
    def state(self) -> CircuitState:
        """Return the current circuit state."""
        with self._lock:
            return self._state

    def open(self, now: float) -> None:
        """Open the circuit and block operations."""

        with self._lock:
            self._state = CircuitState.OPEN
            self._opened_at = now
            self._half_open_calls = 0

    def check(self, now: float) -> None:
        """Check whether an operation is currently allowed."""

        with self._lock:
            if self._state is CircuitState.CLOSED:
                return

            if self._state is CircuitState.OPEN:
                if self._opened_at is None:
                    raise RuntimeError(
                        "OPEN circuit is missing opened_at timestamp"
                    )

                elapsed = now - self._opened_at

                if elapsed < self._cooldown_seconds:
                    raise CircuitOpenError(
                        "Circuit is open; operation blocked"
                    )

                self._state = CircuitState.HALF_OPEN
                self._half_open_calls = 0

            if self._state is CircuitState.HALF_OPEN:
                if self._half_open_calls >= self._half_open_max_calls:
                    raise CircuitOpenError(
                        "Circuit is half-open and test capacity is exhausted"
                    )

                self._half_open_calls += 1

    def record_success(self) -> None:
        """Record a successful operation."""

        with self._lock:
            if self._state is CircuitState.HALF_OPEN:
                self._state = CircuitState.CLOSED
                self._opened_at = None
                self._half_open_calls = 0

    def record_failure(self, now: float) -> None:
        """Record a failure and open the circuit."""

        self.open(now)