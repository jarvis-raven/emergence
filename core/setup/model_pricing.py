"""Model pricing lookup for cost estimation.

Provides estimated cost-per-trigger defaults based on model pricing.
Updated periodically as model pricing changes.
"""

# Cost per 1M tokens (input + output averaged)
# Source: OpenRouter pricing page (as of 2026-02-11)
MODEL_PRICING = {
    # Anthropic models
    "anthropic/claude-opus-4": 15.00,
    "anthropic/claude-sonnet-4": 3.00,
    "anthropic/claude-haiku-4": 0.80,
    # OpenAI models
    "openai/gpt-4-turbo": 10.00,
    "openai/gpt-4": 30.00,
    "openai/gpt-3.5-turbo": 0.50,
    "openai/o1": 15.00,
    "openai/o1-mini": 3.00,
    # Google models
    "google/gemini-pro-1.5": 1.25,
    "google/gemini-flash-1.5": 0.15,
    # Moonshot (Kimi)
    "moonshotai/kimi-k2.5": 0.30,
    # Meta
    "meta-llama/llama-3.1-70b": 0.35,
    "meta-llama/llama-3.1-405b": 2.70,
    # Mistral
    "mistralai/mistral-large": 2.00,
    "mistralai/mistral-medium": 0.75,
    "mistralai/mistral-small": 0.20,
    # Deepseek
    "deepseek/deepseek-chat": 0.14,
    "deepseek/deepseek-coder": 0.14,
}

# Provider prefixes for pattern matching
PROVIDER_PREFIXES = {
    "anthropic/": ["opus", "sonnet", "haiku"],
    "openai/": ["gpt", "o1"],
    "google/": ["gemini"],
    "moonshotai/": ["kimi"],
    "meta-llama/": ["llama"],
    "mistralai/": ["mistral"],
    "deepseek/": ["deepseek"],
}


def estimate_cost_per_trigger(model: str, tokens_per_session: int = 10000) -> float:
    """Estimate cost per drive trigger session based on model.

    Args:
        model: Model identifier (e.g., "anthropic/claude-sonnet-4-20250514")
        tokens_per_session: Estimated tokens per drive session (default: 10k)

    Returns:
        Estimated cost in USD per trigger

    Examples:
        >>> estimate_cost_per_trigger("moonshotai/kimi-k2.5")
        0.003  # $0.30 per 1M tokens * 10k tokens

        >>> estimate_cost_per_trigger("anthropic/claude-opus-4")
        0.15  # $15 per 1M tokens * 10k tokens
    """
    # Normalize model name (remove version suffixes)
    normalized = model.lower()
    for suffix in ["-20250514", "-latest", "-preview", "-0125", "-0613"]:
        normalized = normalized.replace(suffix, "")

    # Try exact match first
    if normalized in MODEL_PRICING:
        cost_per_1m = MODEL_PRICING[normalized]
        return (cost_per_1m / 1_000_000) * tokens_per_session

    # Try partial match (e.g., "opus" in model name)
    for provider_prefix, keywords in PROVIDER_PREFIXES.items():
        if normalized.startswith(provider_prefix):
            for keyword in keywords:
                if keyword in normalized:
                    # Find a model with this keyword
                    for model_key, cost in MODEL_PRICING.items():
                        if model_key.startswith(provider_prefix) and keyword in model_key:
                            cost_per_1m = cost
                            return (cost_per_1m / 1_000_000) * tokens_per_session

    # Default fallback: $1.00 per trigger (conservative middle ground)
    return 1.00


def get_suggested_budget(model: str) -> dict:
    """Get suggested budget limits based on model cost.

    Args:
        model: Model identifier

    Returns:
        Dict with suggested daily_limit and cost_per_trigger

    Examples:
        >>> get_suggested_budget("moonshotai/kimi-k2.5")
        {'daily_limit': 10.0, 'cost_per_trigger': 0.003}

        >>> get_suggested_budget("anthropic/claude-opus-4")
        {'daily_limit': 50.0, 'cost_per_trigger': 0.15}
    """
    cost_per_trigger = estimate_cost_per_trigger(model)

    # Suggest daily limit based on cost tier
    if cost_per_trigger < 0.01:  # Very cheap (< $0.01/trigger)
        daily_limit = 10.0
    elif cost_per_trigger < 0.10:  # Cheap (< $0.10/trigger)
        daily_limit = 25.0
    elif cost_per_trigger < 0.50:  # Medium (< $0.50/trigger)
        daily_limit = 50.0
    else:  # Expensive (>= $0.50/trigger)
        daily_limit = 100.0

    return {
        "daily_limit": daily_limit,
        "cost_per_trigger": round(cost_per_trigger, 3),
    }


if __name__ == "__main__":
    # Test pricing for common models
    test_models = [
        "anthropic/claude-opus-4-20250514",
        "anthropic/claude-sonnet-4-20250514",
        "moonshotai/kimi-k2.5",
        "openai/gpt-4-turbo",
        "google/gemini-flash-1.5",
    ]

    print("Model Cost Estimates (per 10k token session):\n")
    for model in test_models:
        budget = get_suggested_budget(model)
        print(
            f"{model:45} → ${budget['cost_per_trigger']:.3f}/trigger (daily limit: ${budget['daily_limit']})"
        )
