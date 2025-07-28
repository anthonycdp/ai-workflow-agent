"""
Retry middleware with exponential backoff.

This middleware provides automatic retry capabilities for failed
tool executions with configurable backoff strategies.
"""

import asyncio
import random
from functools import wraps
from typing import Any, Callable, Optional, TypeVar, cast

T = TypeVar("T")


class RetryMiddleware:
    """
    Middleware for automatic retry with exponential backoff.

    This middleware wraps tool executions and automatically retries
    on failure with configurable delay and backoff.

    Features:
    - Configurable maximum retries
    - Exponential backoff with jitter
    - Custom retry conditions
    - Retry statistics tracking

    Attributes:
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries (seconds)
        backoff: Multiplier for delay after each retry
        max_delay: Maximum delay cap (seconds)
        jitter: Whether to add random jitter to delays
    """

    def __init__(
        self,
        max_retries: int = 3,
        delay: float = 1.0,
        backoff: float = 2.0,
        max_delay: float = 60.0,
        jitter: bool = True,
        retryable_exceptions: Optional[list[type[Exception]]] = None,
    ):
        """
        Initialize the retry middleware.

        Args:
            max_retries: Maximum retry attempts
            delay: Initial delay in seconds
            backoff: Backoff multiplier
            max_delay: Maximum delay in seconds
            jitter: Add random jitter to delays
            retryable_exceptions: List of exception types to retry on
        """
        self.max_retries = max_retries
        self.delay = delay
        self.backoff = backoff
        self.max_delay = max_delay
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions or [
            ConnectionError,
            TimeoutError,
            OSError,
        ]

        # Statistics
        self._total_retries = 0
        self._successful_retries = 0
        self._failed_after_retries = 0

    def calculate_delay(self, attempt: int) -> float:
        """
        Calculate the delay for a given retry attempt.

        Uses exponential backoff with optional jitter.

        Args:
            attempt: The retry attempt number (0-indexed)

        Returns:
            Delay in seconds
        """
        # Exponential backoff
        delay = self.delay * (self.backoff**attempt)

        # Cap at max delay
        delay = min(delay, self.max_delay)

        # Add jitter (±25%)
        if self.jitter:
            jitter_range = delay * 0.25
            delay += random.uniform(-jitter_range, jitter_range)

        return max(0.1, delay)  # Minimum 100ms

    def should_retry(self, exception: Exception) -> bool:
        """
        Determine if an exception should trigger a retry.

        Args:
            exception: The exception that occurred

        Returns:
            True if should retry
        """
        return isinstance(exception, tuple(self.retryable_exceptions))

    async def execute(
        self,
        func: Callable[..., T],
        *args,
        **kwargs,
    ) -> T:
        """
        Execute a function with retry logic.

        Args:
            func: Async function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function

        Returns:
            Result of the function

        Raises:
            Exception: If all retries fail
        """
        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                # Handle both sync and async functions
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                    if asyncio.iscoroutine(result):
                        result = await result

                # Track successful retry if we had previous attempts
                if attempt > 0:
                    self._successful_retries += 1

                return cast(T, result)

            except Exception as e:
                last_exception = e

                # Check if we should retry
                if not self.should_retry(e):
                    raise

                # Check if we have retries left
                if attempt >= self.max_retries:
                    self._failed_after_retries += 1
                    raise

                # Calculate and wait for delay
                delay = self.calculate_delay(attempt)
                self._total_retries += 1

                await asyncio.sleep(delay)

        # This should never be reached, but satisfy type checker
        if last_exception:
            raise last_exception
        raise RuntimeError("Unexpected state in retry middleware")

    def get_statistics(self) -> dict[str, int]:
        """Get retry statistics."""
        return {
            "total_retries": self._total_retries,
            "successful_retries": self._successful_retries,
            "failed_after_retries": self._failed_after_retries,
        }

    def reset_statistics(self) -> None:
        """Reset retry statistics."""
        self._total_retries = 0
        self._successful_retries = 0
        self._failed_after_retries = 0


def with_retry(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    max_delay: float = 60.0,
    jitter: bool = True,
):
    """
    Decorator for adding retry logic to functions.

    Args:
        max_retries: Maximum retry attempts
        delay: Initial delay in seconds
        backoff: Backoff multiplier
        max_delay: Maximum delay in seconds
        jitter: Add random jitter to delays

    Returns:
        Decorated function with retry logic
    """
    middleware = RetryMiddleware(
        max_retries=max_retries,
        delay=delay,
        backoff=backoff,
        max_delay=max_delay,
        jitter=jitter,
    )

    def decorator(func: Callable[..., T]) -> Callable[..., Any]:
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> T:
            return await middleware.execute(func, *args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> T:
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(middleware.execute(func, *args, **kwargs))

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator
