from dataclasses import dataclass

from agentshield.exceptions import BudgetExceededError


@dataclass(frozen=True)
class BudgetStatus:
    """Current state of an AgentShield budget."""

    limit: float | None
    spent: float

    @property
    def remaining(self) -> float | None:
        """Return remaining budget, if a limit exists."""
        if self.limit is None:
            return None

        return max(self.limit - self.spent, 0.0)

    @property
    def exhausted(self) -> bool:
        """Return whether the configured budget is exhausted."""
        if self.limit is None:
            return False

        return self.spent >= self.limit


class BudgetPolicy:
    """Enforces a maximum accumulated spend."""

    def __init__(self, limit: float | None) -> None:
        if limit is not None and limit < 0:
            raise ValueError("budget limit cannot be negative")

        self._limit = limit

    @property
    def limit(self) -> float | None:
        return self._limit

    def check(self, spent: float) -> BudgetStatus:
        """Check whether the current spend has exhausted the budget."""

        if spent < 0:
            raise ValueError("spent cannot be negative")

        status = BudgetStatus(
            limit=self._limit,
            spent=spent,
        )

        if status.exhausted:
            raise BudgetExceededError(
                f"Budget limit reached: ${spent:.6f}"
            )

        return status