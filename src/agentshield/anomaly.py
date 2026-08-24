from __future__ import annotations

import re
from collections import deque
from difflib import SequenceMatcher


class AnomalyDetector:
    """Detect exact repetition of a configured step cycle."""

    def __init__(
        self,
        max_loops: int = 3,
        cycle_length: int = 2,
        max_tool_repetitions: int | None = None,
        max_stagnation_steps: int | None = None,
        stagnation_similarity: float = 0.70,
    ) -> None:
        if max_loops is not None and max_loops <= 0:
            raise ValueError("max_loops must be positive")

        if cycle_length <= 0:
            raise ValueError("cycle_length must be positive")

        if (
            max_tool_repetitions is not None
            and max_tool_repetitions <= 0
        ):
            raise ValueError("max_tool_repetitions must be positive")

        if max_stagnation_steps is not None and max_stagnation_steps <= 0:
            raise ValueError("max_stagnation_steps must be positive")

        if not 0.0 <= stagnation_similarity <= 1.0:
            raise ValueError(
                "stagnation_similarity must be between 0.0 and 1.0"
            )

        self.max_loops = max_loops
        self.cycle_length = cycle_length
        self.max_tool_repetitions = max_tool_repetitions
        self.max_stagnation_steps = max_stagnation_steps
        self.stagnation_similarity = stagnation_similarity
        self._steps: deque[str] = deque(
            maxlen=cycle_length * (max_loops or 1)
        )
        self._responses: deque[str] = deque(
            maxlen=max_stagnation_steps or 1
        )
        self._current_tool: str | None = None
        self._tool_repetitions = 0

    def record(self, step: object) -> None:
        """Record a step signature for cycle detection."""

        self._steps.append(str(step))

    def is_loop_detected(self) -> bool:
        """Return whether the configured cycle has repeated enough times."""

        if self.max_loops is None:
            return False

        cycle_size = self.cycle_length
        repeated_size = cycle_size * self.max_loops

        if len(self._steps) < repeated_size:
            return False

        repeated_steps = list(self._steps)[-repeated_size:]
        cycle = repeated_steps[:cycle_size]

        return repeated_steps == cycle * self.max_loops

    def record_tool(self, tool_name: str) -> bool:
        """Record a tool call and return whether its repetition limit was reached."""

        if tool_name == self._current_tool:
            self._tool_repetitions += 1
        else:
            self._current_tool = tool_name
            self._tool_repetitions = 1

        return (
            self.max_tool_repetitions is not None
            and self._tool_repetitions >= self.max_tool_repetitions
        )

    def record_response(self, response: object) -> bool:
        """Record a response and return whether the recent window is stagnant."""

        if self.max_stagnation_steps is None:
            return False

        normalized = re.sub(r"[^a-z0-9]+", " ", str(response).lower())
        normalized = " ".join(normalized.split())
        self._responses.append(normalized)

        if len(self._responses) < self.max_stagnation_steps:
            return False

        recent = list(self._responses)[-self.max_stagnation_steps:]
        reference = recent[0]
        similar_count = sum(
            SequenceMatcher(None, reference, response).ratio()
            >= self.stagnation_similarity
            for response in recent
        )
        proportion = similar_count / len(recent)

        return proportion >= self.stagnation_similarity

    def is_stagnation_detected(self) -> bool:
        """Return whether the current response window is stagnant."""

        if self.max_stagnation_steps is None:
            return False

        if len(self._responses) < self.max_stagnation_steps:
            return False

        recent = list(self._responses)[-self.max_stagnation_steps:]
        reference = recent[0]
        similar_count = sum(
            SequenceMatcher(None, reference, response).ratio()
            >= self.stagnation_similarity
            for response in recent
        )

        return (
            similar_count / len(recent)
            >= self.stagnation_similarity
        )