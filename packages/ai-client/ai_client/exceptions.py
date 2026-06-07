class AIClientError(Exception):
    """Base exception for AI client errors."""


class AIAuthError(AIClientError):
    """Raised on authentication failure (401)."""


class AIRateLimitError(AIClientError):
    """Raised when rate limit is exceeded (429)."""


class AIResponseError(AIClientError):
    """Raised on unexpected API response or other API errors."""
