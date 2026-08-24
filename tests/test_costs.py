import pytest

from agentshield.costs import ModelPricing, calculate_token_cost


def test_calculates_token_cost():
    pricing = ModelPricing(
        input_per_1k=0.002,
        output_per_1k=0.008,
    )

    cost = calculate_token_cost(
        pricing=pricing,
        input_tokens=1_000,
        output_tokens=500,
    )

    assert cost == pytest.approx(0.006)


def test_rejects_negative_input_tokens():
    pricing = ModelPricing(
        input_per_1k=0.002,
        output_per_1k=0.008,
    )

    with pytest.raises(ValueError):
        calculate_token_cost(
            pricing=pricing,
            input_tokens=-1,
            output_tokens=100,
        )


def test_rejects_negative_output_tokens():
    pricing = ModelPricing(
        input_per_1k=0.002,
        output_per_1k=0.008,
    )

    with pytest.raises(ValueError):
        calculate_token_cost(
            pricing=pricing,
            input_tokens=100,
            output_tokens=-1,
        )


def test_unknown_model_does_not_silently_bypass_cost_tracking():
    with pytest.raises(ValueError, match="Unknown model pricing"):
        calculate_token_cost(
            model="unknown-model",
            input_tokens=100,
            output_tokens=100,
        )


def test_model_pricing_rejects_invalid_values():
    with pytest.raises(ValueError):
        ModelPricing(input_per_1k=-1.0, output_per_1k=0.0)