"""日志工具模块.

提供应用日志记录功能，支持控制台输出和文件记录。

Features:
    - 控制台彩色输出
    - 文件日志轮转
    - 结构化日志格式
    - 全局日志级别管理
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from typing import Optional

from src.utils.constants import LOG_DIR

# 日志格式
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# 日志文件配置
LOG_FILE_MAX_BYTES = 10 * 1024 * 1024  # 10MB
LOG_FILE_BACKUP_COUNT = 5

# 全局日志级别缓存
_log_level: int = logging.INFO
_root_configured: bool = False


class ColoredFormatter(logging.Formatter):
    """彩色日志格式化器."""

    COLORS = {
        logging.DEBUG: "\033[36m",     # 青色
        logging.INFO: "\033[32m",      # 绿色
        logging.WARNING: "\033[33m",   # 黄色
        logging.ERROR: "\033[31m",     # 红色
        logging.CRITICAL: "\033[35m",  # 紫色
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录."""
        color = self.COLORS.get(record.levelno, "")
        record.levelname = f"{color}{record.levelname}{self.RESET}"
        return super().format(record)


def _configure_root_logger() -> None:
    """配置根日志记录器."""
    global _root_configured
    if _root_configured:
        return

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger()
    root.setLevel(_log_level)
    root.handlers.clear()

    # 控制台（彩色）
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(_log_level)
    console.setFormatter(ColoredFormatter(LOG_FORMAT, DATE_FORMAT))
    root.addHandler(console)

    # 主日志文件（轮转）
    file_handler = RotatingFileHandler(
        LOG_DIR / "app.log",
        maxBytes=LOG_FILE_MAX_BYTES,
        backupCount=LOG_FILE_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setLevel(_log_level)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
    root.addHandler(file_handler)

    # 错误日志（单独记录）
    error_handler = RotatingFileHandler(
        LOG_DIR / "error.log",
        maxBytes=LOG_FILE_MAX_BYTES,
        backupCount=LOG_FILE_BACKUP_COUNT,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
    root.addHandler(error_handler)

    _root_configured = True


def setup_logger(name: str, level: Optional[int] = None) -> logging.Logger:
    """设置并返回日志记录器.

    Args:
        name: 日志记录器名称，通常使用 __name__
        level: 日志级别，默认使用全局配置

    Returns:
        配置好的日志记录器
    """
    _configure_root_logger()
    logger = logging.getLogger(name)
    logger.setLevel(level if level is not None else _log_level)
    return logger


def set_log_level(level: int | str) -> None:
    """设置全局日志级别."""
    global _log_level
    if isinstance(level, str):
        level = getattr(logging, level.upper(), logging.INFO)
    _log_level = level

    root = logging.getLogger()
    root.setLevel(level)
    for handler in root.handlers:
        if handler.level != logging.ERROR:
            handler.setLevel(level)


def get_log_level() -> int:
    """获取当前全局日志级别."""
    return _log_level


def get_log_level_name() -> str:
    """获取当前日志级别名称."""
    return logging.getLevelName(_log_level)
