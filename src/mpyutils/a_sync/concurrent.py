import asyncio
from typing import Awaitable, Literal, cast, overload

from mpyutils.typing import AsyncFn, T


@overload
async def gather(
    *coros: Awaitable[T], max_concurrent: int, return_exceptions: Literal[False] = False
) -> list[T]: ...


@overload
async def gather(
    *coros: Awaitable[T], max_concurrent: int, return_exceptions: Literal[True]
) -> list[T | BaseException]: ...


async def gather(
    *coros: Awaitable[T], max_concurrent: int, return_exceptions: bool = False
) -> list[T] | list[T | BaseException]:
    """Limited concurrency version of asyncio.gather."""
    semaphore = asyncio.Semaphore(max_concurrent)

    async def sem_coro(coro: Awaitable[T]):
        async with semaphore:  # Limits concurrency
            return await coro

    tasks = [sem_coro(coro) for coro in coros]
    return await asyncio.gather(*tasks, return_exceptions=return_exceptions)


def with_semaphore(max_concurrent: int):
    """A decorator to limit the concurrency of an async function.
    """
    def _inner_decorator(func: AsyncFn) -> AsyncFn:
        semaphore = asyncio.Semaphore(max_concurrent)

        async def wrapper(*args, **kwargs):
            async with semaphore:
                return await func(*args, **kwargs)

        return cast(AsyncFn, wrapper)

    return _inner_decorator
