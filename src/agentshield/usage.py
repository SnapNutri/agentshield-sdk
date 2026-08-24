from dataclasses import dataclass
from threading import Lock


@dataclass(frozen=True)
class LLMUsage:
    """Usage information for one LLM call."""

    model: str
    input_tokens: int
    output_tokens: int
    cost: float


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