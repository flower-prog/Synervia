"""Model cost table and tokens-to-credits conversion."""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ModelCost:
    input_per_1m_usd: float
    output_per_1m_usd: float
    cached_input_per_1m_usd: float = 0.0


MODEL_COSTS: dict[str, ModelCost] = {
    # OpenAI
    "gpt-4o": ModelCost(2.50, 10.00, 1.25),
    "gpt-4o-mini": ModelCost(0.15, 0.60, 0.075),
    "o1": ModelCost(15.00, 60.00),
    "o1-mini": ModelCost(3.00, 12.00),
    "o3": ModelCost(10.00, 40.00),
    "o4-mini": ModelCost(1.10, 4.40),
    # Anthropic
    "claude-3-5-sonnet-20241022": ModelCost(3.00, 15.00, 1.50),
    "claude-3-5-haiku-20241022": ModelCost(0.80, 4.00, 0.40),
    "claude-opus-4-20250514": ModelCost(15.00, 75.00, 7.50),
    "claude-sonnet-4-5": ModelCost(3.00, 15.00, 1.50),
    "claude-haiku-4-5-20251001": ModelCost(0.80, 4.00, 0.40),
    # Google
    "gemini-1.5-pro": ModelCost(1.25, 5.00),
    "gemini-1.5-flash": ModelCost(0.075, 0.30),
    "gemini-2.0-flash": ModelCost(0.10, 0.40),
    "gemini-2.5-pro": ModelCost(1.25, 10.00),
}

DEFAULT_MARKUP_MULTIPLIER: float = 2.0

_FALLBACK_COST = ModelCost(input_per_1m_usd=5.0, output_per_1m_usd=15.0)


def usage_to_credits(
    *,
    model: str,
    input_tokens: int,
    output_tokens: int,
    cached_tokens: int = 0,
    credits_per_usd: int = 1000,
    markup: float = DEFAULT_MARKUP_MULTIPLIER,
) -> int:
    """Return the number of credits to charge for a given usage."""
    cost = MODEL_COSTS.get(model)
    if not cost:
        logger.warning("unknown_model_cost", extra={"model": model})
        cost = _FALLBACK_COST

    raw_usd = (
        input_tokens * cost.input_per_1m_usd / 1_000_000
        + output_tokens * cost.output_per_1m_usd / 1_000_000
        + cached_tokens * cost.cached_input_per_1m_usd / 1_000_000
    )
    charged_usd = raw_usd * markup
    credits = int(charged_usd * credits_per_usd)
    return max(credits, 1)  # always charge at least 1 credit per call
