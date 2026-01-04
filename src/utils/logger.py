"""日志工具模块."""

import logging
import sys
from pathlib import Path
from typing import Optional

from src.utils.constants import LOG_DIR

# 日志格式
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# 全局日志级别缓存
_log_level: int = logging.INFO
_initialized: bool = False


def setup_logger(
    name: str,
    level: Optional[int] = None,
    log_to_file: bool = True,
) -> logging.Logger:
    """设置并返回日志记录器.

    Args:
        name: 日志记录器名称，通常使用 __name__
        level: 日志级别，默认使用全局配置
        log_to_file: 是否输出到文件

    Returns:
        配置好的日志记录器
    """
    global _initialized

    logger = logging.getLogger(name)

    # 如果已经配置过，直接返回
    if logger.handlers:
        return logger

    # 设置日志级别
    log_level = level if level is not None else _log_level
    logger.setLevel(log_level)

    # 创建格式化器
    formatter = logging.Formatter(LOG_FORMAT, DATE_FORMAT)

    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 文件处理器（可选）
    if log_to_file and not _initialized:
        try:
            LOG_DIR.mkdir(parents=True, exist_ok=True)
            log_file = LOG_DIR / "app.log"

            file_handler = logging.FileHandler(
                log_file, encoding="utf-8", mode="a"
            )
            file_handler.setLevel(log_level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            logger.warning(f"无法创建日志文件: {e}")

    # 防止日志传播到根日志记录器
    logger.propagate = False

    _initialized = True
    return logger


def set_log_level(level: int | str) -> None:
    """设置全局日志级别.

    Args:
        level: 日志级别，可以是整数或字符串 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    global _log_level

    if isinstance(level, str):
        level = getattr(logging, level.upper(), logging.INFO)

    _log_level = level

    # 更新所有已存在的日志记录器
    for name in logging.Logger.manager.loggerDict:
        logger = logging.getLogger(name)
        logger.setLevel(level)
        for handler in logger.handlers:
            handler.setLevel(level)


def get_log_level() -> int:
    """获取当前全局日志级别."""
    return _log_level
