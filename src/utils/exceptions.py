"""自定义异常类."""

from __future__ import annotations


class AppException(Exception):
    """应用基础异常类.

    所有自定义异常都应继承此类。

    Attributes:
        message: 错误消息
        code: 错误代码
    """

    def __init__(self, message: str, code: str = "UNKNOWN") -> None:
        """初始化异常.

        Args:
            message: 错误消息
            code: 错误代码
        """
        self.message = message
        self.code = code
        super().__init__(self.message)

    def __str__(self) -> str:
        """返回异常字符串表示."""
        return f"[{self.code}] {self.message}"


# ===================
# 配置相关异常
# ===================
class ConfigError(AppException):
    """配置错误异常."""

    def __init__(self, message: str) -> None:
        super().__init__(message, "CONFIG_ERROR")


class InvalidConfigValueError(ConfigError):
    """配置值无效异常."""

    def __init__(self, key: str, value: str, reason: str = "") -> None:
        msg = f"配置项 '{key}' 的值 '{value}' 无效"
        if reason:
            msg += f": {reason}"
        super().__init__(msg)


# ===================
# AI 服务相关异常
# ===================
class AIServiceError(AppException):
    """AI 服务错误异常."""

    def __init__(self, message: str) -> None:
        super().__init__(message, "AI_SERVICE_ERROR")


class APIKeyNotFoundError(AIServiceError):
    """API 密钥未找到异常."""

    def __init__(self) -> None:
        super().__init__("API 密钥未配置，请在设置中配置 API 密钥")


class APIRequestError(AIServiceError):
    """API 请求错误异常."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        self.status_code = status_code
        msg = message
        if status_code:
            msg = f"API 请求失败 (HTTP {status_code}): {message}"
        super().__init__(msg)


class APITimeoutError(AIServiceError):
    """API 超时异常."""

    def __init__(self, timeout: int) -> None:
        super().__init__(f"API 请求超时 ({timeout}秒)")


# ===================
# 图片处理相关异常
# ===================
class ImageProcessError(AppException):
    """图片处理错误异常."""

    def __init__(self, message: str) -> None:
        super().__init__(message, "IMAGE_PROCESS_ERROR")


class ImageNotFoundError(ImageProcessError):
    """图片文件未找到异常."""

    def __init__(self, path: str) -> None:
        super().__init__(f"图片文件未找到: {path}")


class UnsupportedImageFormatError(ImageProcessError):
    """不支持的图片格式异常."""

    def __init__(self, format: str) -> None:
        super().__init__(f"不支持的图片格式: {format}")


class ImageTooLargeError(ImageProcessError):
    """图片文件过大异常."""

    def __init__(self, size: int, max_size: int) -> None:
        size_mb = size / (1024 * 1024)
        max_mb = max_size / (1024 * 1024)
        super().__init__(f"图片文件过大 ({size_mb:.1f}MB)，最大允许 {max_mb:.1f}MB")


class ImageCorruptedError(ImageProcessError):
    """图片文件损坏异常."""

    def __init__(self, path: str) -> None:
        super().__init__(f"图片文件损坏或无法读取: {path}")


# ===================
# 队列相关异常
# ===================
class QueueError(AppException):
    """队列错误异常."""

    def __init__(self, message: str) -> None:
        super().__init__(message, "QUEUE_ERROR")


class QueueFullError(QueueError):
    """队列已满异常."""

    def __init__(self, max_size: int) -> None:
        super().__init__(f"处理队列已满，最多支持 {max_size} 个任务")


class TaskNotFoundError(QueueError):
    """任务未找到异常."""

    def __init__(self, task_id: str) -> None:
        super().__init__(f"任务未找到: {task_id}")


# ===================
# 数据库相关异常
# ===================
class DatabaseError(AppException):
    """数据库错误异常."""

    def __init__(self, message: str) -> None:
        super().__init__(message, "DATABASE_ERROR")


class DatabaseConnectionError(DatabaseError):
    """数据库连接错误异常."""

    def __init__(self, path: str) -> None:
        super().__init__(f"无法连接到数据库: {path}")
