"""应用设置模型."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.utils.constants import (
    APP_DATA_DIR,
    DATABASE_PATH,
    DEFAULT_API_BASE,
    DEFAULT_OUTPUT_HEIGHT,
    DEFAULT_OUTPUT_QUALITY,
    DEFAULT_OUTPUT_WIDTH,
    MAX_QUEUE_SIZE,
)


class Settings(BaseSettings):
    """应用设置.

    支持从环境变量和 .env 文件加载配置。

    Attributes:
        openai_api_base: OpenAI API 基础 URL
        log_level: 日志级别
        max_queue_size: 最大队列大小
        default_output_width: 默认输出宽度
        default_output_height: 默认输出高度
        default_output_quality: 默认输出质量
        database_path: 数据库文件路径
        debug: 调试模式
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # API 配置
    openai_api_base: str = Field(
        default=DEFAULT_API_BASE,
        description="OpenAI API 基础 URL",
    )

    # 应用配置
    log_level: str = Field(
        default="INFO",
        description="日志级别",
    )

    max_queue_size: int = Field(
        default=MAX_QUEUE_SIZE,
        ge=1,
        le=50,
        description="最大队列大小",
    )

    concurrent_limit: int = Field(
        default=3,
        ge=1,
        le=10,
        description="并发处理数量",
    )

    # 输出配置
    default_output_width: int = Field(
        default=DEFAULT_OUTPUT_WIDTH,
        ge=100,
        le=4096,
        description="默认输出宽度",
    )

    default_output_height: int = Field(
        default=DEFAULT_OUTPUT_HEIGHT,
        ge=100,
        le=4096,
        description="默认输出高度",
    )

    default_output_quality: int = Field(
        default=DEFAULT_OUTPUT_QUALITY,
        ge=1,
        le=100,
        description="默认输出质量",
    )

    # 数据库配置
    database_path: Optional[Path] = Field(
        default=None,
        description="数据库文件路径",
    )

    # 开发配置
    debug: bool = Field(
        default=False,
        description="调试模式",
    )

    dev_tools: bool = Field(
        default=False,
        description="启用开发工具",
    )

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """验证日志级别."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper_v = v.upper()
        if upper_v not in valid_levels:
            raise ValueError(f"无效的日志级别: {v}，有效值: {valid_levels}")
        return upper_v

    @property
    def db_path(self) -> Path:
        """获取数据库路径."""
        return self.database_path or DATABASE_PATH

    @property
    def output_size(self) -> tuple[int, int]:
        """获取默认输出尺寸."""
        return (self.default_output_width, self.default_output_height)
