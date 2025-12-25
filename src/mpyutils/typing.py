from typing import Any, Awaitable, Callable, TypeVar

T = TypeVar("T")
Fn = TypeVar("Fn", bound=Callable[..., Any])
AsyncFn = TypeVar("AsyncFn", bound=Callable[..., Awaitable[Any]])
