from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Any

_UNSET = object()


@dataclass(frozen=True)
class ShieldConfig:
    budget_limit: float | None = 5.0
    max_steps: int | None = 20
    max_duration_seconds: float | None = 60.0
    circuit_cooldown_seconds: float = 30.0
    circuit_half_open_max_calls: int = 3
    max_loops: int | None = None
    cycle_length: int = 2
    max_tool_repetitions: int | None = None
    max_stagnation_steps: int | None = None
    stagnation_similarity: float = 0.70

    def __init__(
        self,
        budget_limit: float | None = 5.0,
        max_steps: int | None = 20,
        max_duration_seconds: float | None = 60.0,
        circuit_cooldown_seconds: float = 30.0,
        circuit_half_open_max_calls: int = 3,
        max_loops: int | None = None,
        cycle_length: int = 2,
        max_tool_repetitions: int | None = None,
        max_stagnation_steps: int | None = None,
        stagnation_similarity: float = 0.70,
        *,
        max_latency_seconds: float | None | Any = _UNSET,
    ) -> None:
        if max_latency_seconds is not _UNSET:
            if max_duration_seconds != 60.0:
                raise TypeError(
                    "Provide either max_duration_seconds or "
                    "max_latency_seconds, not both"
                )
            max_duration_seconds = max_latency_seconds

        object.__setattr__(self, "budget_limit", budget_limit)
        object.__setattr__(self, "max_steps", max_steps)
        object.__setattr__(self, "max_duration_seconds", max_duration_seconds)
        object.__setattr__(self, "circuit_cooldown_seconds", circuit_cooldown_seconds)
        object.__setattr__(
            self,
            "circuit_half_open_max_calls",
            circuit_half_open_max_calls,
        )
        object.__setattr__(self, "max_loops", max_loops)
        object.__setattr__(self, "cycle_length", cycle_length)
        object.__setattr__(self, "max_tool_repetitions", max_tool_repetitions)
        object.__setattr__(self, "max_stagnation_steps", max_stagnation_steps)
        object.__setattr__(self, "stagnation_similarity", stagnation_similarity)
        self.__post_init__()

    @property
    def max_latency_seconds(self) -> float | None:
        """Backward-compatible alias for max_duration_seconds."""

        return self.max_duration_seconds

    def __post_init__(self) -> None:
        self._validate_optional_number("budget_limit", self.budget_limit, 0.0)
        self._validate_optional_integer("max_steps", self.max_steps)
        self._validate_optional_number(
            "max_duration_seconds", self.max_duration_seconds, 0.0
        )
        self._validate_number(
            "circuit_cooldown_seconds", self.circuit_cooldown_seconds, 0.0
        )
        self._validate_integer(
            "circuit_half_open_max_calls", self.circuit_half_open_max_calls, 1
        )
        self._validate_optional_integer("max_loops", self.max_loops)
        self._validate_integer("cycle_length", self.cycle_length, 1)
        self._validate_optional_integer(
            "max_tool_repetitions", self.max_tool_repetitions
        )
        self._validate_optional_integer(
            "max_stagnation_steps", self.max_stagnation_steps
        )
        self._validate_number(
            "stagnation_similarity", self.stagnation_similarity, 0.0, 1.0
        )

    @staticmethod
    def _validate_number(
        name: str,
        value: object,
        minimum: float,
        maximum: float | None = None,
    ) -> None:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{name} must be numeric")
        if not isfinite(value) or value < minimum:
            raise ValueError(f"{name} must be finite and non-negative")
        if maximum is not None and value > maximum:
            raise ValueError(f"{name} must be between {minimum} and {maximum}")

    @classmethod
    def _validate_optional_number(
        cls, name: str, value: object, minimum: float
    ) -> None:
        if value is not None:
            cls._validate_number(name, value, minimum)

    @staticmethod
    def _validate_integer(name: str, value: object, minimum: int) -> None:
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{name} must be an integer")
        if value < minimum:
            raise ValueError(f"{name} must be at least {minimum}")

    @classmethod
    def _validate_optional_integer(cls, name: str, value: object) -> None:
        if value is not None:
            cls._validate_integer(name, value, 1)
