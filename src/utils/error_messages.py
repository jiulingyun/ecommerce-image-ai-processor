"""用户友好的错误消息管理模块.

提供错误信息的中文描述、解决建议和错误分类功能。

Features:
    - 错误消息中文化
    - 错误解决建议
    - 错误严重级别分类
    - 统一的错误格式化
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from src.utils.exceptions import (
    AIServiceError,
    APIKeyNotFoundError,
    APIRequestError,
    APITimeoutError,
    AppException,
    ConfigError,
    DatabaseConnectionError,
    DatabaseError,
    ImageCorruptedError,
    ImageNotFoundError,
    ImageProcessError,
    ImageTooLargeError,
    InvalidConfigValueError,
    QueueError,
    QueueFullError,
    TaskNotFoundError,
    UnsupportedImageFormatError,
)


class ErrorSeverity(str, Enum):
    """错误严重级别."""

    INFO = "info"  # 提示信息
    WARNING = "warning"  # 警告
    ERROR = "error"  # 错误
    CRITICAL = "critical"  # 严重错误


@dataclass
class UserFriendlyError:
    """用户友好的错误信息.

    Attributes:
        title: 错误标题
        message: 错误描述
        suggestion: 解决建议
        severity: 错误严重级别
        error_code: 错误代码
        details: 详细技术信息（可选，用于调试）
    """

    title: str
    message: str
    suggestion: str
    severity: ErrorSeverity
    error_code: str
    details: Optional[str] = None

    def to_dict(self) -> dict:
        """转换为字典."""
        return {
            "title": self.title,
            "message": self.message,
            "suggestion": self.suggestion,
            "severity": self.severity.value,
            "error_code": self.error_code,
            "details": self.details,
        }


# 错误消息映射表
ERROR_MESSAGES = {
    # AI 服务错误
    "API_KEY_NOT_FOUND": UserFriendlyError(
        title="API 密钥未配置",
        message="未找到 AI 服务的 API 密钥，无法进行图片处理。",
        suggestion="请在「设置」→「API 配置」中配置您的 API 密钥。",
        severity=ErrorSeverity.ERROR,
        error_code="API_KEY_NOT_FOUND",
    ),
    "API_REQUEST_ERROR": UserFriendlyError(
        title="API 请求失败",
        message="与 AI 服务通信时发生错误。",
        suggestion="请检查网络连接，稍后重试。如果问题持续，请检查 API 配置是否正确。",
        severity=ErrorSeverity.ERROR,
        error_code="API_REQUEST_ERROR",
    ),
    "API_TIMEOUT": UserFriendlyError(
        title="请求超时",
        message="AI 服务响应超时，处理可能需要更长时间。",
        suggestion="请稍后重试，或尝试处理较小的图片。",
        severity=ErrorSeverity.WARNING,
        error_code="API_TIMEOUT",
    ),
    "API_RATE_LIMIT": UserFriendlyError(
        title="请求频率限制",
        message="API 请求过于频繁，已被服务商限制。",
        suggestion="请等待几分钟后重试，或减少并发处理数量。",
        severity=ErrorSeverity.WARNING,
        error_code="API_RATE_LIMIT",
    ),
    "API_QUOTA_EXCEEDED": UserFriendlyError(
        title="配额已用尽",
        message="您的 API 使用配额已用尽。",
        suggestion="请检查您的 API 账户配额，或升级您的套餐计划。",
        severity=ErrorSeverity.ERROR,
        error_code="API_QUOTA_EXCEEDED",
    ),
    # 图片处理错误
    "IMAGE_NOT_FOUND": UserFriendlyError(
        title="找不到图片",
        message="指定的图片文件不存在或已被移动。",
        suggestion="请检查文件路径是否正确，或重新选择图片。",
        severity=ErrorSeverity.ERROR,
        error_code="IMAGE_NOT_FOUND",
    ),
    "UNSUPPORTED_FORMAT": UserFriendlyError(
        title="不支持的图片格式",
        message="该图片格式不受支持。",
        suggestion="请使用 JPG、PNG 或 WebP 格式的图片。",
        severity=ErrorSeverity.ERROR,
        error_code="UNSUPPORTED_FORMAT",
    ),
    "IMAGE_TOO_LARGE": UserFriendlyError(
        title="图片文件过大",
        message="图片文件大小超过了处理限制。",
        suggestion="请使用较小的图片，或先压缩图片后再上传。",
        severity=ErrorSeverity.WARNING,
        error_code="IMAGE_TOO_LARGE",
    ),
    "IMAGE_CORRUPTED": UserFriendlyError(
        title="图片文件损坏",
        message="无法读取图片文件，文件可能已损坏。",
        suggestion="请尝试使用其他软件打开该图片，或使用其他图片。",
        severity=ErrorSeverity.ERROR,
        error_code="IMAGE_CORRUPTED",
    ),
    "IMAGE_PROCESS_FAILED": UserFriendlyError(
        title="图片处理失败",
        message="处理图片时发生错误。",
        suggestion="请检查图片是否正常，或尝试使用其他图片。",
        severity=ErrorSeverity.ERROR,
        error_code="IMAGE_PROCESS_FAILED",
    ),
    # 队列错误
    "QUEUE_FULL": UserFriendlyError(
        title="处理队列已满",
        message="当前处理队列已达到最大容量。",
        suggestion="请等待当前任务完成后再添加新任务。",
        severity=ErrorSeverity.WARNING,
        error_code="QUEUE_FULL",
    ),
    "TASK_NOT_FOUND": UserFriendlyError(
        title="任务未找到",
        message="找不到指定的处理任务。",
        suggestion="任务可能已被删除，请刷新任务列表。",
        severity=ErrorSeverity.WARNING,
        error_code="TASK_NOT_FOUND",
    ),
    # 配置错误
    "CONFIG_ERROR": UserFriendlyError(
        title="配置错误",
        message="应用配置存在问题。",
        suggestion="请检查配置文件，或重置为默认配置。",
        severity=ErrorSeverity.ERROR,
        error_code="CONFIG_ERROR",
    ),
    "INVALID_CONFIG": UserFriendlyError(
        title="配置值无效",
        message="某些配置值不符合要求。",
        suggestion="请检查并修正配置值，确保在有效范围内。",
        severity=ErrorSeverity.WARNING,
        error_code="INVALID_CONFIG",
    ),
    # 数据库错误
    "DATABASE_ERROR": UserFriendlyError(
        title="数据存储错误",
        message="访问本地数据时发生错误。",
        suggestion="请重启应用，如果问题持续，请清除应用数据。",
        severity=ErrorSeverity.ERROR,
        error_code="DATABASE_ERROR",
    ),
    "DATABASE_CONNECTION_ERROR": UserFriendlyError(
        title="数据库连接失败",
        message="无法连接到本地数据库。",
        suggestion="请检查磁盘空间和权限，或重启应用。",
        severity=ErrorSeverity.CRITICAL,
        error_code="DATABASE_CONNECTION_ERROR",
    ),
    # 通用错误
    "UNKNOWN_ERROR": UserFriendlyError(
        title="未知错误",
        message="发生了意外错误。",
        suggestion="请重试操作，如果问题持续，请联系技术支持。",
        severity=ErrorSeverity.ERROR,
        error_code="UNKNOWN_ERROR",
    ),
    "NETWORK_ERROR": UserFriendlyError(
        title="网络连接错误",
        message="无法连接到网络。",
        suggestion="请检查您的网络连接，确保可以访问互联网。",
        severity=ErrorSeverity.ERROR,
        error_code="NETWORK_ERROR",
    ),
    "PERMISSION_DENIED": UserFriendlyError(
        title="权限不足",
        message="没有足够的权限执行此操作。",
        suggestion="请检查文件或文件夹的访问权限。",
        severity=ErrorSeverity.ERROR,
        error_code="PERMISSION_DENIED",
    ),
    "DISK_FULL": UserFriendlyError(
        title="磁盘空间不足",
        message="磁盘空间已满，无法保存文件。",
        suggestion="请清理磁盘空间后重试。",
        severity=ErrorSeverity.CRITICAL,
        error_code="DISK_FULL",
    ),
}


def get_user_friendly_error(
    exception: Exception,
    include_details: bool = False,
) -> UserFriendlyError:
    """将异常转换为用户友好的错误信息.

    Args:
        exception: 异常对象
        include_details: 是否包含详细技术信息

    Returns:
        UserFriendlyError 对象
    """
    details = str(exception) if include_details else None

    # 根据异常类型匹配错误消息
    if isinstance(exception, APIKeyNotFoundError):
        error = ERROR_MESSAGES["API_KEY_NOT_FOUND"]
    elif isinstance(exception, APITimeoutError):
        error = ERROR_MESSAGES["API_TIMEOUT"]
    elif isinstance(exception, APIRequestError):
        # 检查是否是特定的 HTTP 错误
        if hasattr(exception, "status_code"):
            if exception.status_code == 429:
                error = ERROR_MESSAGES["API_RATE_LIMIT"]
            elif exception.status_code == 402:
                error = ERROR_MESSAGES["API_QUOTA_EXCEEDED"]
            else:
                error = ERROR_MESSAGES["API_REQUEST_ERROR"]
        else:
            error = ERROR_MESSAGES["API_REQUEST_ERROR"]
    elif isinstance(exception, ImageNotFoundError):
        error = ERROR_MESSAGES["IMAGE_NOT_FOUND"]
    elif isinstance(exception, UnsupportedImageFormatError):
        error = ERROR_MESSAGES["UNSUPPORTED_FORMAT"]
    elif isinstance(exception, ImageTooLargeError):
        error = ERROR_MESSAGES["IMAGE_TOO_LARGE"]
    elif isinstance(exception, ImageCorruptedError):
        error = ERROR_MESSAGES["IMAGE_CORRUPTED"]
    elif isinstance(exception, ImageProcessError):
        error = ERROR_MESSAGES["IMAGE_PROCESS_FAILED"]
    elif isinstance(exception, QueueFullError):
        error = ERROR_MESSAGES["QUEUE_FULL"]
    elif isinstance(exception, TaskNotFoundError):
        error = ERROR_MESSAGES["TASK_NOT_FOUND"]
    elif isinstance(exception, InvalidConfigValueError):
        error = ERROR_MESSAGES["INVALID_CONFIG"]
    elif isinstance(exception, ConfigError):
        error = ERROR_MESSAGES["CONFIG_ERROR"]
    elif isinstance(exception, DatabaseConnectionError):
        error = ERROR_MESSAGES["DATABASE_CONNECTION_ERROR"]
    elif isinstance(exception, DatabaseError):
        error = ERROR_MESSAGES["DATABASE_ERROR"]
    elif isinstance(exception, AIServiceError):
        error = ERROR_MESSAGES["API_REQUEST_ERROR"]
    elif isinstance(exception, OSError):
        # 处理常见的系统错误
        if "No space left" in str(exception):
            error = ERROR_MESSAGES["DISK_FULL"]
        elif "Permission denied" in str(exception):
            error = ERROR_MESSAGES["PERMISSION_DENIED"]
        else:
            error = ERROR_MESSAGES["UNKNOWN_ERROR"]
    elif isinstance(exception, ConnectionError):
        error = ERROR_MESSAGES["NETWORK_ERROR"]
    else:
        error = ERROR_MESSAGES["UNKNOWN_ERROR"]

    # 创建新的错误对象，包含详细信息
    return UserFriendlyError(
        title=error.title,
        message=error.message,
        suggestion=error.suggestion,
        severity=error.severity,
        error_code=error.error_code,
        details=details,
    )


def format_error_message(error: UserFriendlyError) -> str:
    """格式化错误消息为显示文本.

    Args:
        error: UserFriendlyError 对象

    Returns:
        格式化的错误消息字符串
    """
    lines = [
        f"❌ {error.title}",
        "",
        error.message,
        "",
        f"💡 建议: {error.suggestion}",
    ]

    if error.details:
        lines.extend(["", f"详细信息: {error.details}"])

    return "\n".join(lines)


def get_severity_icon(severity: ErrorSeverity) -> str:
    """获取错误级别对应的图标.

    Args:
        severity: 错误严重级别

    Returns:
        图标字符串
    """
    icons = {
        ErrorSeverity.INFO: "ℹ️",
        ErrorSeverity.WARNING: "⚠️",
        ErrorSeverity.ERROR: "❌",
        ErrorSeverity.CRITICAL: "🚫",
    }
    return icons.get(severity, "❓")


def get_severity_color(severity: ErrorSeverity) -> str:
    """获取错误级别对应的颜色.

    Args:
        severity: 错误严重级别

    Returns:
        颜色值（十六进制）
    """
    colors = {
        ErrorSeverity.INFO: "#1890ff",  # 蓝色
        ErrorSeverity.WARNING: "#faad14",  # 黄色
        ErrorSeverity.ERROR: "#ff4d4f",  # 红色
        ErrorSeverity.CRITICAL: "#cf1322",  # 深红色
    }
    return colors.get(severity, "#666666")
