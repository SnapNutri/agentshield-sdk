import pytest

from agentshield.budget import (
    BudgetExceededError,
    BudgetPolicy,
)
from agentshield.exceptions import BudgetExceededError as CanonicalBudgetExceededError


def test_budget_exception_is_canonical():
    assert BudgetExceededError is CanonicalBudgetExceededError


def test_budget_allows_spending_below_limit():
    policy = BudgetPolicy(limit=5.0)

    status = policy.check(spent=2.0)

    assert status.limit == 5.0
    assert status.spent == 2.0
    assert status.remaining == pytest.approx(3.0)
    assert status.exhausted is False


def test_budget_blocks_when_limit_is_reached():
    policy = BudgetPolicy(limit=5.0)

    with pytest.raises(BudgetExceededError):
        policy.check(spent=5.0)


def test_budget_blocks_when_limit_is_exceeded():
    policy = BudgetPolicy(limit=5.0)

    with pytest.raises(BudgetExceededError):
        policy.check(spent=5.5)


def test_unlimited_budget_never_exhausts():
    policy = BudgetPolicy(limit=None)

    status = policy.check(spent=1_000_000.0)

    assert status.limit is None
    assert status.remaining is None
    assert status.exhausted is False


def test_negative_budget_limit_is_rejected():
    with pytest.raises(ValueError):
        BudgetPolicy(limit=-1.0)


def test_negative_spend_is_rejected():
    policy = BudgetPolicy(limit=5.0)

    with pytest.raises(ValueError):
        policy.check(spent=-1.0)