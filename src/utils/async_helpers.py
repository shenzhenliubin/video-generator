"""
Async Helper Functions

Utilities for working with async code.
"""

import asyncio
from typing import Any, Coroutine, TypeVar

T = TypeVar("T")


async def gather_with_concurrency(
    coroutines: list[Coroutine[Any, Any, T]],
    max_concurrency: int = 10,
) -> list[T]:
    """
    Run coroutines with a concurrency limit.

    Args:
        coroutines: List of coroutines to run
        max_concurrency: Maximum concurrent tasks

    Returns:
        List of results in order
    """
    semaphore = asyncio.Semaphore(max_concurrency)

    async def run_with_semaphore(coro: Coroutine[Any, Any, T]) -> T:
        async with semaphore:
            return await coro

    return await asyncio.gather(
        *(run_with_semaphore(coro) for coro in coroutines)
    )
