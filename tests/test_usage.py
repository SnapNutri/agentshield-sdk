import pytest

from agentshield.usage import LLMUsage, UsageTracker


def test_tracker_starts_empty():
    tracker = UsageTracker()

    assert tracker.records == ()
    assert tracker.total_cost == 0.0
    assert tracker.total_input_tokens == 0
    assert tracker.total_output_tokens == 0


def test_tracker_accumulates_usage():
    tracker = UsageTracker()

    tracker.record(
        LLMUsage(
            model="test-model",
            input_tokens=1_000,
            output_tokens=500,
            cost=0.006,
        )
    )

    tracker.record(
        LLMUsage(
            model="test-model",
            input_tokens=2_000,
            output_tokens=1_000,
            cost=0.012,
        )
    )

    assert tracker.total_cost == pytest.approx(0.018)
    assert tracker.total_input_tokens == 3_000
    assert tracker.total_output_tokens == 1_500
    assert len(tracker.records) == 2