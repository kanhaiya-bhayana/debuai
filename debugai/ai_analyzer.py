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


def analyze_with_ai(log: str, provider_name: str = None) -> dict:
    """
    Run AI analysis on a stack trace.

    Args:
        log:           The raw stack trace string.
        provider_name: Optional override ("openai", "anthropic", "nvidia").
                       If None, auto-detects from env vars.

    Returns:
        dict with keys: root_cause, fix, prevention, confidence
    """
    try:
        provider = get_provider(provider_name)
        prompt = provider.build_prompt(log)
        raw = provider.analyze(prompt)
        return provider.parse_response(raw)

    except EnvironmentError as e:
        return {
            "root_cause": str(e),
            "fix": "",
            "prevention": "",
            "confidence": "low"
        }

    except Exception as e:
        return {
            "root_cause": "AI analysis failed.",
            "fix": str(e),
            "prevention": "Check your API key and network connection.",
            "confidence": "low"
        }