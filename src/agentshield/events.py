from __future__ import annotations

from dataclasses import dataclass, field
from time import time
from types import MappingProxyType
from typing import Mapping


@dataclass(frozen=True)
class AgentShieldEvent:
    """Immutable, metadata-only record of an AgentShield runtime event."""

    session_id: str
    event_type: str
    timestamp: float = field(default_factory=time)
    operation_index: int | None = None
    policy: str | None = None
    decision: str | None = None
    cost: float | None = None
    duration: float | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    protection_reason: str | None = None
    metadata: Mapping[str, object] = field(
        default_factory=lambda: MappingProxyType({})
    )

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "metadata",
            MappingProxyType(dict(self.metadata)),
        )
