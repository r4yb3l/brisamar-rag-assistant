class LLMUnavailableError(RuntimeError):
    """The provider kept failing after retries (timeouts, rate limits, 5xx)."""


def is_transient_llm_error(error: BaseException) -> bool:
    try:
        import litellm
    except ImportError:
        return False
    transient = (
        litellm.Timeout,
        litellm.RateLimitError,
        litellm.APIConnectionError,
        litellm.InternalServerError,
        litellm.ServiceUnavailableError,
    )
    return isinstance(error, transient)
