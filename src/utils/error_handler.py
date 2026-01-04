"""错误处理工具模块.

提供统一的错误处理机制和用户友好的错误消息。
"""

from __future__ import annotations

import traceback
from typing import Any, Callable, Optional, Type, TypeVar

from src.utils.exceptions import (
    AIServiceError,
    APIKeyNotFoundError,
    APIRequestError,
    APITimeoutError,
    AppException,
    ConfigError,
    DatabaseError,
    ImageProcessError,
    QueueError,
)
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

T = TypeVar("T")


# 错误消息映射
ERROR_MESSAGES = {
    APIKeyNotFoundError: "请先在设置中配置 API 密钥",
    APITimeoutError: "网络请求超时，请检查网络连接后重试",
    APIRequestError: "API 请求失败，请稍后重试",
    AIServiceError: "AI 服务异常，请稍后重试",
    ImageProcessError: "图片处理失败，请检查图片文件",
    ConfigError: "配置错误，请检查配置文件",
    QueueError: "任务队列异常",
    DatabaseError: "数据库操作失败",
}


def get_user_friendly_message(exception: Exception) -> str:
    """获取用户友好的错误消息.

    Args:
        exception: 异常对象

    Returns:
        用户友好的错误消息
    """
    # 检查是否是已知的应用异常
    for exc_type, message in ERROR_MESSAGES.items():
        if isinstance(exception, exc_type):
            return message

    # 如果是 AppException，使用其消息
    if isinstance(exception, AppException):
        return exception.message

    # 未知异常
    return "操作失败，请稍后重试"


def get_error_details(exception: Exception) -> dict[str, Any]:
    """获取错误详细信息.

    Args:
        exception: 异常对象

    Returns:
        包含错误详情的字典
    """
    details = {
        "type": type(exception).__name__,
        "message": str(exception),
        "user_message": get_user_friendly_message(exception),
    }

    # 添加应用异常的额外信息
    if isinstance(exception, AppException):
        details["code"] = exception.code

    # 添加 API 请求错误的状态码
    if isinstance(exception, APIRequestError) and exception.status_code:
        details["status_code"] = exception.status_code

    return details


def handle_exception(
    exception: Exception,
    context: str = "",
    reraise: bool = True,
    log_traceback: bool = True,
) -> None:
    """统一异常处理.

    Args:
        exception: 异常对象
        context: 上下文描述
        reraise: 是否重新抛出异常
        log_traceback: 是否记录堆栈跟踪
    """
    # 构建日志消息
    msg = f"异常发生"
    if context:
        msg = f"{context}: {msg}"

    # 记录日志
    if log_traceback:
        logger.exception(f"{msg}: {exception}")
    else:
        logger.error(f"{msg}: {exception}")

    # 重新抛出
    if reraise:
        raise exception


def safe_execute(
    func: Callable[..., T],
    *args: Any,
    default: Optional[T] = None,
    on_error: Optional[Callable[[Exception], None]] = None,
    **kwargs: Any,
) -> Optional[T]:
    """安全执行函数，捕获异常.

    Args:
        func: 要执行的函数
        *args: 位置参数
        default: 发生异常时的默认返回值
        on_error: 错误回调函数
        **kwargs: 关键字参数

    Returns:
        函数返回值或默认值
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logger.warning(f"函数 {func.__name__} 执行失败: {e}")
        if on_error:
            on_error(e)
        return default


async def safe_execute_async(
    func: Callable[..., T],
    *args: Any,
    default: Optional[T] = None,
    on_error: Optional[Callable[[Exception], None]] = None,
    **kwargs: Any,
) -> Optional[T]:
    """安全执行异步函数，捕获异常.

    Args:
        func: 要执行的异步函数
        *args: 位置参数
        default: 发生异常时的默认返回值
        on_error: 错误回调函数
        **kwargs: 关键字参数

    Returns:
        函数返回值或默认值
    """
    try:
        return await func(*args, **kwargs)
    except Exception as e:
        logger.warning(f"异步函数 {func.__name__} 执行失败: {e}")
        if on_error:
            on_error(e)
        return default


class ErrorCollector:
    """错误收集器.

    用于批量操作时收集所有错误。

    Example:
        >>> collector = ErrorCollector()
        >>> for item in items:
        ...     try:
        ...         process(item)
        ...     except Exception as e:
        ...         collector.add(e, context=f"处理 {item}")
        >>> if collector.has_errors:
        ...     print(collector.summary)
    """

    def __init__(self) -> None:
        self._errors: list[tuple[Exception, str]] = []

    def add(self, exception: Exception, context: str = "") -> None:
        """添加错误.

        Args:
            exception: 异常对象
            context: 上下文描述
        """
        self._errors.append((exception, context))
        logger.warning(f"收集到错误 [{context}]: {exception}")

    @property
    def has_errors(self) -> bool:
        """是否有错误."""
        return len(self._errors) > 0

    @property
    def error_count(self) -> int:
        """错误数量."""
        return len(self._errors)

    @property
    def errors(self) -> list[tuple[Exception, str]]:
        """所有错误."""
        return self._errors.copy()

    @property
    def summary(self) -> str:
        """错误摘要."""
        if not self._errors:
            return "无错误"

        lines = [f"共 {len(self._errors)} 个错误:"]
        for i, (exc, ctx) in enumerate(self._errors, 1):
            ctx_str = f" ({ctx})" if ctx else ""
            lines.append(f"  {i}. {type(exc).__name__}{ctx_str}: {exc}")

        return "\n".join(lines)

    def clear(self) -> None:
        """清除所有错误."""
        self._errors.clear()

    def raise_if_errors(self, message: str = "批量操作中发生错误") -> None:
        """如果有错误则抛出异常.

        Args:
            message: 异常消息
        """
        if self._errors:
            raise AppException(f"{message}\n{self.summary}")
