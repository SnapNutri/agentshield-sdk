from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from types import MappingProxyType


@dataclass(frozen=True)
class ModelPricing:
    """Pricing for one model, expressed as USD per 1,000 tokens."""

    input_per_1k: float
    output_per_1k: float

    def __post_init__(self) -> None:
        if (
            self.input_per_1k < 0
            or self.output_per_1k < 0
            or not isfinite(self.input_per_1k)
            or not isfinite(self.output_per_1k)
        ):
            raise ValueError("Model pricing must be finite and non-negative")


MODEL_PRICING = MappingProxyType({
    "gpt-4o-mini": ModelPricing(
        input_per_1k=0.00015,
        output_per_1k=0.00060,
    ),
    "gpt-4o": ModelPricing(
        input_per_1k=0.0025,
        output_per_1k=0.0100,
    ),
    "gpt-3.5-turbo": ModelPricing(
        input_per_1k=0.0005,
        output_per_1k=0.0015,
    ),
    "claude-3-5-sonnet": ModelPricing(
        input_per_1k=0.0030,
        output_per_1k=0.0150,
    ),
    "claude-3-haiku": ModelPricing(
        input_per_1k=0.00025,
        output_per_1k=0.00125,
    ),
})


def calculate_token_cost(
    model: str | ModelPricing | None = None,
    input_tokens: int = 0,
    output_tokens: int = 0,
    *,
    pricing: ModelPricing | None = None,
) -> float:
    """
    Calculate the USD cost of an LLM call.

    Either `model` or `pricing` may be supplied.

    Examples:

        calculate_token_cost(
            model="gpt-4o-mini",
            input_tokens=1000,
            output_tokens=500,
        )

        calculate_token_cost(
            pricing=ModelPricing(
                input_per_1k=0.002,
                output_per_1k=0.008,
            ),
            input_tokens=1000,
            output_tokens=500,
        )
    """

    if input_tokens < 0:
        raise ValueError("Token counts cannot be negative")

    if output_tokens < 0:
        raise ValueError("Token counts cannot be negative")

    if pricing is not None:
        selected_pricing = pricing

    elif isinstance(model, ModelPricing):
        selected_pricing = model

    elif isinstance(model, str):
        selected_pricing = MODEL_PRICING.get(model.lower())

        if selected_pricing is None:
            raise ValueError(f"Unknown model pricing: {model}")

    elif model is None:
        raise ValueError(
            "Either model or pricing must be provided"
        )

    else:
        raise TypeError(
            "model must be a string or ModelPricing"
        )

    return (
        (input_tokens / 1000.0)
        * selected_pricing.input_per_1k
        + (output_tokens / 1000.0)
        * selected_pricing.output_per_1k
    )


# Backward-compatible alias.
calculate_cost = calculate_token_cost