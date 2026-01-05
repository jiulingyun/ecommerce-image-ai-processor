"""抠图服务抽象基类.

定义统一的抠图接口，支持多种实现方式（外部API、AI模型等）。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional

from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class BackgroundRemoverType(str, Enum):
    """抠图服务类型."""

    EXTERNAL_API = "external_api"  # 外部API服务
    AI = "ai"  # AI模型抠图


class BaseBackgroundRemover(ABC):
    """抠图服务抽象基类.

    定义统一的抠图接口，所有抠图实现需继承此类。

    Example:
        >>> remover = ExternalAPIRemover(api_url="http://localhost:5000/api/remove-background")
        >>> result = await remover.remove_background(image_bytes)
    """

    remover_type: BackgroundRemoverType

    @abstractmethod
    async def remove_background(
        self,
        image: bytes,
        **kwargs,
    ) -> bytes:
        """去除图片背景.

        Args:
            image: 输入图片字节数据
            **kwargs: 额外参数

        Returns:
            处理后的透明背景PNG图片字节数据
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

    async def __aenter__(self) -> "BaseBackgroundRemover":
        """异步上下文管理器入口."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """异步上下文管理器出口."""
        await self.close()
