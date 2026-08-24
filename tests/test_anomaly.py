import pytest

from agentshield.anomaly import AnomalyDetector


def test_non_repeating_sequence_is_not_a_loop():
    detector = AnomalyDetector()

    for step in ("A", "B", "C", "D"):
        detector.record(step)

    assert detector.is_loop_detected() is False


def test_two_step_repeating_loop_is_detected():
    detector = AnomalyDetector(max_loops=3, cycle_length=2)

    for step in ("A", "B", "A", "B", "A", "B"):
        detector.record(step)

    assert detector.is_loop_detected() is True


def test_three_step_repeating_loop_is_detected():
    detector = AnomalyDetector(max_loops=3, cycle_length=3)

    for step in ("A", "B", "C", "A", "B", "C", "A", "B", "C"):
        detector.record(step)

    assert detector.is_loop_detected() is True


def test_different_sequence_is_not_a_loop():
    detector = AnomalyDetector(max_loops=3, cycle_length=2)

    for step in ("A", "B", "A", "C", "A", "B"):
        detector.record(step)

    assert detector.is_loop_detected() is False


def test_detector_rejects_invalid_configuration():
    with pytest.raises(ValueError):
        AnomalyDetector(max_loops=0)

    with pytest.raises(ValueError):
        AnomalyDetector(cycle_length=0)

    with pytest.raises(ValueError):
        AnomalyDetector(max_tool_repetitions=0)


def test_different_tools_are_safe():
    detector = AnomalyDetector(max_tool_repetitions=3)

    assert [detector.record_tool(tool) for tool in ("search", "read", "write")] == [
        False,
        False,
        False,
    ]


def test_tool_repetition_below_threshold_is_safe():
    detector = AnomalyDetector(max_tool_repetitions=6)

    for _ in range(3):
        assert detector.record_tool("search") is False


def test_tool_repetition_reaches_threshold():
    detector = AnomalyDetector(max_tool_repetitions=6)

    for _ in range(5):
        assert detector.record_tool("search") is False

    assert detector.record_tool("search") is True
    assert detector.record_tool("search") is True


def test_different_tool_resets_repetition_count():
    detector = AnomalyDetector(max_tool_repetitions=3)

    assert detector.record_tool("search") is False
    assert detector.record_tool("search") is False
    assert detector.record_tool("read") is False
    assert detector.record_tool("search") is False


def test_stagnation_is_disabled_by_default():
    detector = AnomalyDetector(max_stagnation_steps=None)

    for _ in range(5):
        assert detector.record_response("Same response") is False


def test_stagnation_requires_a_full_window():
    detector = AnomalyDetector(max_stagnation_steps=5)

    for _ in range(4):
        assert detector.record_response("Same response") is False


def test_different_responses_are_not_stagnant():
    detector = AnomalyDetector(
        max_stagnation_steps=5,
        stagnation_similarity=0.70,
    )

    for response in ("A", "B", "C", "D", "E"):
        detector.record_response(response)

    assert detector.is_stagnation_detected() is False


def test_highly_similar_responses_are_stagnant():
    detector = AnomalyDetector(
        max_stagnation_steps=5,
        stagnation_similarity=0.70,
    )

    responses = (
        "I need more information!",
        "I NEED MORE INFORMATION.",
        "I need more information to continue.",
        "I need additional information.",
        "I need more information!",
    )

    results = [detector.record_response(response) for response in responses]

    assert results[-1] is True
    assert detector.is_stagnation_detected() is True


def test_mixed_responses_are_not_stagnant():
    detector = AnomalyDetector(
        max_stagnation_steps=5,
        stagnation_similarity=0.70,
    )

    responses = (
        "I need more information.",
        "I need more information.",
        "A useful result was found.",
        "The task is complete.",
        "A different answer is available.",
    )

    for response in responses:
        detector.record_response(response)

    assert detector.is_stagnation_detected() is False


def test_stagnation_configuration_is_validated():
    with pytest.raises(ValueError):
        AnomalyDetector(max_stagnation_steps=0)

    with pytest.raises(ValueError):
        AnomalyDetector(max_stagnation_steps=-1)

    with pytest.raises(ValueError):
        AnomalyDetector(stagnation_similarity=-0.1)

    with pytest.raises(ValueError):
        AnomalyDetector(stagnation_similarity=1.1)


def test_detector_history_is_bounded():
    detector = AnomalyDetector(
        max_loops=2,
        cycle_length=2,
        max_stagnation_steps=3,
    )

    for index in range(20):
        detector.record(f"step-{index}")
        detector.record_response(f"response-{index}")

    assert detector._steps.maxlen == 4
    assert detector._responses.maxlen == 3
    assert len(detector._steps) == 4
    assert len(detector._responses) == 3