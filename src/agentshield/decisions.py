from __future__ import annotations

from dataclasses import dataclass, field
from time import time
from types import MappingProxyType
from typing import Mapping


@dataclass(frozen=True)
class ProtectionDecision:
    """Immutable result of one protection evaluation."""

    allowed: bool
    policy: str
    reason: str
    timestamp: float = field(default_factory=time)
    session_id: str | None = None
    operation_index: int | None = None
    current_value: float | int | None = None
    configured_limit: float | int | None = None
    metadata: Mapping[str, object] = field(
        default_factory=lambda: MappingProxyType({})
    )

    @property
    def blocked(self) -> bool:
        """Return whether this decision blocks execution."""

        return not self.allowed

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "metadata",
            MappingProxyType(dict(self.metadata)),
        )
