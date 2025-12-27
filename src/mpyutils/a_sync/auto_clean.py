import functools
from typing import Protocol, cast, runtime_checkable

import aiohttp

from mpyutils.typing import AsyncFn


@runtime_checkable
class RequireAsyncClean(Protocol):
    async def close(self) -> None: ...


global_clean_list: list[RequireAsyncClean] = []
enter: bool = False


def auto_clean(func: AsyncFn) -> AsyncFn:
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        global enter
        # TODO: per task support?
        assert not enter
        enter = True
        res = await func(*args, **kwargs)
        for clean_obj in global_clean_list:
            try:
                await clean_obj.close()
            except Exception as e:
                # TODO: switch to logging
                print(f"Error cleaning up {clean_obj}: {e}")
        enter = False
        return res

    return cast(AsyncFn, wrapper)


class AutoCleanAiohttpMixin:
    """
    Mixin provides single auto clean aiohttp session

    Example:

    ```
    class Test(AutoCleanAiohttpMixin):
        pass

    class TestWithCustomSession(AutoCleanAiohttpMixin):
        def __init__(self, ...):
            session = aiohttp.ClientSession(...)
            self.init_session(session)

    test = Test()
    await test.session.get("https://example.com")

    # Session will be automatically cleaned up
    ```

    """

    _session: aiohttp.ClientSession | None = None

    def init_session(self, session: aiohttp.ClientSession):
        assert self._session is None, "Session already initialized"
        self._session = session
        global_clean_list.append(self._session)

    @property
    def session(self) -> aiohttp.ClientSession:
        try:
            assert self._session is not None
            return self._session
        except AssertionError:
            self._session = aiohttp.ClientSession()
            global_clean_list.append(self._session)
        return self._session
