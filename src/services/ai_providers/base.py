"""AI 图片处理提供者抽象基类.

定义统一的 AI 图片处理接口，便于扩展不同服务商。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional

from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class AIProviderType(str, Enum):
    """AI 提供者类型."""

    DASHSCOPE = "dashscope"  # 阿里云百炼
    OPENAI = "openai"  # OpenAI


class BaseAIImageProvider(ABC):
    """AI 图片处理提供者抽象基类.

    定义统一的图片处理接口，所有 AI 服务商需实现此接口。

    Attributes:
        provider_type: 提供者类型标识
        api_key: API 密钥
        model: 使用的模型名称
    """

    provider_type: AIProviderType

    def __init__(
        self,
        api_key: str,
        model: Optional[str] = None,
        **kwargs,
    ) -> None:
        """初始化提供者.

        Args:
            api_key: API 密钥
            model: 模型名称，为 None 时使用默认模型
            **kwargs: 其他配置参数
        """
        self._api_key = api_key
        self._model = model or self.default_model
        self._extra_config = kwargs

    @property
    @abstractmethod
    def default_model(self) -> str:
        """默认模型名称."""
        pass

    @property
    def model(self) -> str:
        """当前使用的模型."""
        return self._model

    @abstractmethod
    async def remove_background(
        self,
        image: bytes,
        prompt: Optional[str] = None,
    ) -> bytes:
        """去除图片背景.

        Args:
            image: 输入图片字节数据
            prompt: 可选的提示词

        Returns:
            处理后的图片字节数据
        """
        pass

    @abstractmethod
    async def composite_images(
        self,
        images: list[bytes],
        prompt: str,
    ) -> bytes:
        """合成多张图片.

        Args:
            images: 图片字节数据列表
            prompt: 合成提示词

        Returns:
            合成后的图片字节数据
        """
        pass

    @abstractmethod
    async def edit_image(
        self,
        image: bytes,
        prompt: str,
    ) -> bytes:
        """编辑单张图片.

        Args:
            image: 输入图片字节数据
            prompt: 编辑提示词

        Returns:
            编辑后的图片字节数据
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """检查服务是否可用.

        Returns:
            服务是否可用
        """
        pass

    async def close(self) -> None:
        """关闭连接，释放资源.

        子类可重写此方法释放特定资源。
        """
        pass

    async def __aenter__(self) -> "BaseAIImageProvider":
        """异步上下文管理器入口."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """异步上下文管理器出口."""
        await self.close()
