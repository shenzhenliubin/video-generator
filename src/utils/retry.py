"""
Retry Logic

Exponential backoff retry decorator for external API calls.
"""

import asyncio
from functools import wraps
from typing import Any, Callable

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)


def with_retry(
    max_attempts: int = 3,
    base_wait: float = 1.0,
    max_wait: float = 10.0,
) -> Callable:
    """
    Decorator for retrying functions with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts
        base_wait: Initial wait time in seconds
        max_wait: Maximum wait time in seconds

    Returns:
        Decorated function with retry logic
    """

    def decorator(func: Callable) -> Callable:
        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=1, min=base_wait, max=max_wait),
            retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        )
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            return await func(*args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            return func(*args, **kwargs)

        # Return appropriate wrapper based on whether function is async
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator
