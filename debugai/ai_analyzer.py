from debugai import PROVIDERS


def get_provider(name: str = None):
    """
    Return a provider instance.

    If `name` is given (e.g. "openai", "anthropic", "nvidia"), return that
    provider if its key is set — or raise a clear error if not.

    If `name` is None, auto-detect by walking PROVIDERS in priority order
    (OpenAI → Anthropic → NVIDIA) and returning the first available one.
    """
    if name:
        name = name.lower()
        for provider in PROVIDERS:
            if provider.name().lower() == name:
                if not provider.is_available():
                    raise EnvironmentError(
                        f"Provider '{provider.name()}' requested but "
                        f"{provider.name().upper()}_API_KEY is not set."
                    )
                return provider
        available = [p.name().lower() for p in PROVIDERS]
        raise ValueError(
            f"Unknown provider '{name}'. Available: {', '.join(available)}"
        )

    for provider in PROVIDERS:
        if provider.is_available():
            return provider

    # Nothing available — tell the user exactly what to do
    raise EnvironmentError(
        "No AI provider configured.\n"
        "Set one of the following environment variables:\n"
        "  export OPENAI_API_KEY=...      (recommended)\n"
        "  export ANTHROPIC_API_KEY=...\n"
        "  export NVIDIA_API_KEY=..."
    )


def _providers_to_try(name: str = None) -> list:
    """
    Resolve the ordered list of providers to attempt.

    - Explicit `name`: exactly that one provider — honoured as-is, with NO
      failover (the user made a deliberate choice).
    - Auto (name is None): every available provider in priority order, so a
      provider whose API call fails falls over to the next one.

    Raises EnvironmentError / ValueError for the same configuration problems
    as get_provider (unknown provider, requested provider missing its key,
    or no provider configured at all).
    """
    if name:
        return [get_provider(name)]

    available = [p for p in PROVIDERS if p.is_available()]
    if not available:
        get_provider(None)  # delegate for the canonical "no provider" error
    return available


def analyze_with_ai(log: str, provider_name: str = None, source_context: str = None) -> dict:
    """
    Run AI analysis on a stack trace.

    Args:
        log:            The raw stack trace string.
        provider_name:  Optional override ("openai", "anthropic", "nvidia").
                        If None, auto-detects from env vars and fails over
                        across all available providers on error.
        source_context: Optional local source snippet around the failure,
                        included in the prompt to sharpen the diagnosis.

    Returns:
        dict with keys: root_cause, fix, prevention, confidence
    """
    try:
        providers = _providers_to_try(provider_name)

    except (EnvironmentError, ValueError) as e:
        # Configuration problem (missing API key, or an unknown/typo'd
        # --provider). Surface the actionable message directly instead of
        # labelling it an "AI analysis failed" runtime error.
        return {
            "root_cause": str(e),
            "fix": "",
            "prevention": "",
            "confidence": "low"
        }

    # Try each provider in order; on failure fall over to the next.
    last_error = None
    for provider in providers:
        try:
            prompt = provider.build_prompt(log, source_context)
            raw = provider.analyze(prompt)
            return provider.parse_response(raw)
        except Exception as e:  # noqa: BLE001 — record and try the next provider
            last_error = e
            continue

    return {
        "root_cause": "AI analysis failed.",
        "fix": str(last_error) if last_error else "",
        "prevention": "Check your API key and network connection.",
        "confidence": "low"
    }