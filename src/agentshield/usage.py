from dataclasses import dataclass
from math import isfinite
from threading import Lock


@dataclass(frozen=True)
class LLMUsage:
    """Usage information for one LLM call."""

    model: str
    input_tokens: int
    output_tokens: int
    cost: float

    def __post_init__(self) -> None:
        for name, value in (
            ("input_tokens", self.input_tokens),
            ("output_tokens", self.output_tokens),
        ):
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{name} must be an integer")
            if value < 0:
                raise ValueError(f"{name} cannot be negative")

        if isinstance(self.cost, bool) or not isinstance(self.cost, (int, float)):
            raise TypeError("cost must be numeric")
        if not isfinite(self.cost) or self.cost < 0:
            raise ValueError("cost must be finite and non-negative")


class UsageTracker:
    """Tracks LLM usage and accumulated cost for one session."""

    def __init__(self) -> None:
        self._records: list[LLMUsage] = []
        self._lock = Lock()

    @property
    def records(self) -> tuple[LLMUsage, ...]:
        """Return all recorded LLM calls."""
        with self._lock:
            return tuple(self._records)

    @property
    def total_cost(self) -> float:
        """Return the accumulated cost of all recorded calls."""
        with self._lock:
            return sum(record.cost for record in self._records)

    @property
    def total_input_tokens(self) -> int:
        """Return the total number of input tokens."""
        with self._lock:
            return sum(record.input_tokens for record in self._records)

    @property
    def total_output_tokens(self) -> int:
        """Return the total number of output tokens."""
        with self._lock:
            return sum(record.output_tokens for record in self._records)

    def record(self, usage: LLMUsage) -> None:
        """Record one completed LLM call."""
        with self._lock:
            self._records.append(usage)
