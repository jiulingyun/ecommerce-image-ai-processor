"""API 配置模型."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, SecretStr, field_validator

from src.utils.constants import (
    API_MAX_RETRIES,
    API_RETRY_DELAY,
    API_TIMEOUT,
    DEFAULT_API_BASE,
)


class AIModelConfig(BaseModel):
    """AI 模型配置.

    配置 GPT-Image-1.5 模型的参数。

    Attributes:
        model: 模型名称
        max_tokens: 最大 token 数
        temperature: 温度参数
    """

    model: str = Field(
        default="gpt-image-1.5",
        description="AI 模型名称",
    )
    max_tokens: int = Field(
        default=4096,
        ge=1,
        le=8192,
        description="最大 token 数",
    )
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="温度参数",
    )


class APIConfig(BaseModel):
    """OpenAI API 配置.

    配置 API 连接参数。

    Attributes:
        base_url: API 基础 URL
        api_key: API 密钥（敏感信息）
        timeout: 请求超时时间
        max_retries: 最大重试次数
        retry_delay: 重试延迟
        model_config: 模型配置
    """

    base_url: str = Field(
        default=DEFAULT_API_BASE,
        description="API 基础 URL",
    )
    api_key: Optional[SecretStr] = Field(
        default=None,
        description="API 密钥",
    )
    timeout: int = Field(
        default=API_TIMEOUT,
        ge=10,
        le=300,
        description="请求超时时间 (秒)",
    )
    max_retries: int = Field(
        default=API_MAX_RETRIES,
        ge=0,
        le=10,
        description="最大重试次数",
    )
    retry_delay: float = Field(
        default=API_RETRY_DELAY,
        ge=0.1,
        le=10.0,
        description="重试延迟 (秒)",
    )
    model: AIModelConfig = Field(
        default_factory=AIModelConfig,
        description="模型配置",
    )

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, v: str) -> str:
        """验证 API URL."""
        v = v.strip().rstrip("/")
        if not v.startswith(("http://", "https://")):
            raise ValueError("API URL 必须以 http:// 或 https:// 开头")
        return v

    @property
    def has_api_key(self) -> bool:
        """检查是否配置了 API 密钥."""
        return self.api_key is not None and len(self.api_key.get_secret_value()) > 0

    def get_api_key_value(self) -> Optional[str]:
        """获取 API 密钥明文值.

        注意: 仅在需要时调用，不要记录日志。

        Returns:
            API 密钥字符串或 None
        """
        if self.api_key:
            return self.api_key.get_secret_value()
        return None

    def to_safe_dict(self) -> dict:
        """转换为安全字典（隐藏敏感信息）.

        Returns:
            不包含敏感信息的字典
        """
        return {
            "base_url": self.base_url,
            "has_api_key": self.has_api_key,
            "timeout": self.timeout,
            "max_retries": self.max_retries,
            "retry_delay": self.retry_delay,
            "model": self.model.model_dump(),
        }


class ImageGenerationParams(BaseModel):
    """图片生成参数.

    用于 AI 图片处理 API 调用的参数。

    Attributes:
        prompt: 提示词
        size: 图片尺寸
        quality: 图片质量
        n: 生成数量
    """

    prompt: str = Field(
        default="",
        max_length=4000,
        description="提示词",
    )
    size: str = Field(
        default="1024x1024",
        description="图片尺寸",
    )
    quality: str = Field(
        default="standard",
        description="图片质量 (standard/hd)",
    )
    n: int = Field(
        default=1,
        ge=1,
        le=4,
        description="生成数量",
    )

    @field_validator("size")
    @classmethod
    def validate_size(cls, v: str) -> str:
        """验证图片尺寸."""
        valid_sizes = {"256x256", "512x512", "1024x1024", "1024x1792", "1792x1024"}
        if v not in valid_sizes:
            raise ValueError(f"无效的图片尺寸: {v}，有效值: {valid_sizes}")
        return v

    @field_validator("quality")
    @classmethod
    def validate_quality(cls, v: str) -> str:
        """验证图片质量."""
        valid_qualities = {"standard", "hd"}
        if v not in valid_qualities:
            raise ValueError(f"无效的图片质量: {v}，有效值: {valid_qualities}")
        return v
