"""重试机制模块.

提供函数重试装饰器，支持同步和异步函数。

Features:
    - 可配置重试次数和延迟
    - 指数退避
    - 异常类型过滤
    - 重试回调
"""

from __future__ import annotations

import asyncio
import functools
import time
from typing import Any, Callable, Optional, Tuple, Type, TypeVar, Union

from src.utils.logger import setup_logger

logger = setup_logger(__name__)

# 类型变量
F = TypeVar("F", bound=Callable[..., Any])


class RetryConfig:
    """重试配置.

    Attributes:
        max_retries: 最大重试次数
        delay: 初始延迟（秒）
        backoff: 退避乘数
        max_delay: 最大延迟（秒）
        exceptions: 需要重试的异常类型
    """

    def __init__(
        self,
        max_retries: int = 3,
        delay: float = 1.0,
        backoff: float = 2.0,
        max_delay: float = 30.0,
        exceptions: Tuple[Type[Exception], ...] = (Exception,),
    ) -> None:
        self.max_retries = max_retries
        self.delay = delay
        self.backoff = backoff
        self.max_delay = max_delay
        self.exceptions = exceptions


# 默认配置
DEFAULT_RETRY_CONFIG = RetryConfig()


def retry(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    max_delay: float = 30.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[int, Exception], None]] = None,
) -> Callable[[F], F]:
    """重试装饰器.

    支持同步函数的重试。

    Args:
        max_retries: 最大重试次数
        delay: 初始延迟（秒）
        backoff: 退避乘数
        max_delay: 最大延迟（秒）
        exceptions: 需要重试的异常类型
        on_retry: 重试回调函数

    Returns:
        装饰器函数

    Example:
        >>> @retry(max_retries=3, delay=1.0)
        ... def fetch_data():
        ...     # 可能失败的操作
        ...     pass
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception: Optional[Exception] = None
            current_delay = delay

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt < max_retries:
                        logger.warning(
                            f"函数 {func.__name__} 执行失败 (尝试 {attempt + 1}/{max_retries + 1}): {e}"
                        )

                        # 调用重试回调
                        if on_retry:
                            on_retry(attempt + 1, e)

                        # 等待后重试
                        time.sleep(current_delay)
                        current_delay = min(current_delay * backoff, max_delay)
                    else:
                        logger.error(
                            f"函数 {func.__name__} 重试 {max_retries} 次后仍然失败: {e}"
                        )

            # 抛出最后的异常
            if last_exception:
                raise last_exception

        return wrapper  # type: ignore

    return decorator


def async_retry(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    max_delay: float = 30.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[int, Exception], None]] = None,
) -> Callable[[F], F]:
    """异步重试装饰器.

    支持异步函数的重试。

    Args:
        max_retries: 最大重试次数
        delay: 初始延迟（秒）
        backoff: 退避乘数
        max_delay: 最大延迟（秒）
        exceptions: 需要重试的异常类型
        on_retry: 重试回调函数

    Returns:
        装饰器函数

    Example:
        >>> @async_retry(max_retries=3, delay=1.0)
        ... async def fetch_data():
        ...     # 可能失败的异步操作
        ...     pass
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception: Optional[Exception] = None
            current_delay = delay

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt < max_retries:
                        logger.warning(
                            f"异步函数 {func.__name__} 执行失败 (尝试 {attempt + 1}/{max_retries + 1}): {e}"
                        )

                        # 调用重试回调
                        if on_retry:
                            on_retry(attempt + 1, e)

                        # 异步等待后重试
                        await asyncio.sleep(current_delay)
                        current_delay = min(current_delay * backoff, max_delay)
                    else:
                        logger.error(
                            f"异步函数 {func.__name__} 重试 {max_retries} 次后仍然失败: {e}"
                        )

            # 抛出最后的异常
            if last_exception:
                raise last_exception

        return wrapper  # type: ignore

    return decorator


class RetryContext:
    """重试上下文管理器.

    用于需要更精细控制的重试场景。

    Example:
        >>> async with RetryContext(max_retries=3) as ctx:
        ...     while ctx.should_retry:
        ...         try:
        ...             result = await some_operation()
        ...             break
        ...         except Exception as e:
        ...             ctx.record_failure(e)
    """

    def __init__(
        self,
        max_retries: int = 3,
        delay: float = 1.0,
        backoff: float = 2.0,
        max_delay: float = 30.0,
    ) -> None:
        self.max_retries = max_retries
        self.delay = delay
        self.backoff = backoff
        self.max_delay = max_delay
        self._attempt = 0
        self._last_exception: Optional[Exception] = None
        self._current_delay = delay

    @property
    def attempt(self) -> int:
        """当前尝试次数."""
        return self._attempt

    @property
    def should_retry(self) -> bool:
        """是否应该继续重试."""
        return self._attempt <= self.max_retries

    @property
    def last_exception(self) -> Optional[Exception]:
        """最后一次异常."""
        return self._last_exception

    def record_failure(self, exception: Exception) -> None:
        """记录失败.

        Args:
            exception: 异常对象
        """
        self._last_exception = exception
        self._attempt += 1

        if self._attempt <= self.max_retries:
            logger.warning(
                f"操作失败 (尝试 {self._attempt}/{self.max_retries + 1}): {exception}"
            )

    async def wait(self) -> None:
        """等待下次重试."""
        await asyncio.sleep(self._current_delay)
        self._current_delay = min(self._current_delay * self.backoff, self.max_delay)

    def wait_sync(self) -> None:
        """同步等待下次重试."""
        time.sleep(self._current_delay)
        self._current_delay = min(self._current_delay * self.backoff, self.max_delay)

    async def __aenter__(self) -> "RetryContext":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> bool:
        return False

    def __enter__(self) -> "RetryContext":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        return False
