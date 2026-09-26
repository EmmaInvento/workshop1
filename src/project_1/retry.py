import random
import time
from collections.abc import Callable
from typing import TypeVar

from openai import (
    APIConnectionError,
    APITimeoutError,
    InternalServerError,
    RateLimitError,
)

RETRYABLE = (
    RateLimitError,
    APITimeoutError,
    InternalServerError,
    APIConnectionError,
)

MAX_RETRIES = 5 #prima chiamata + 5 retries

T = TypeVar("T") #every type can be returned but will be the same as fn


def call_with_retry(
    fn: Callable[[], T], #fn is a function that doesn't take args but give back a type T
    *,
    max_retries: int = MAX_RETRIES,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
) -> tuple[T, int]:
    """Call fn() with exponential backoff on transient API errors.

    Returns (result, retries_used) on success. Raises the last exception after
    exhausting retries.
    """
    delay = initial_delay #delay after an error

    for retries_used in range(max_retries + 1):
        try:
            return fn(), retries_used
        except RETRYABLE:
            if retries_used == max_retries:
                raise
            jitter = random.uniform(0, delay * 0.5)
            wait = min(delay + jitter, max_delay)
            time.sleep(wait)
            delay *= 2

    raise RuntimeError("retry loop exited without returning")