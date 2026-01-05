"""AI抠图服务包装器.

包装现有AI服务的抠图功能，提供统一接口。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from src.services.background_removal.base import (
    BackgroundRemoverType,
    BaseBackgroundRemover,
)
from src.utils.logger import setup_logger

if TYPE_CHECKING:
    from src.services.ai_service import AIService

logger = setup_logger(__name__)


class AIRemover(BaseBackgroundRemover):
    """AI抠图服务包装器.

    包装现有的 AIService 抠图功能，提供统一的 BaseBackgroundRemover 接口。

    Attributes:
        ai_service: AI服务实例

    Example:
        >>> from src.services.ai_service import get_ai_service
        >>> remover = AIRemover(ai_service=get_ai_service())
        >>> result = await remover.remove_background(image_bytes)
    """

    remover_type = BackgroundRemoverType.AI

    def __init__(
        self,
        ai_service: Optional["AIService"] = None,
    ) -> None:
        """初始化AI抠图服务.

        Args:
            ai_service: AI服务实例，如果为None则使用全局单例
        """
        self._ai_service = ai_service

    @property
    def ai_service(self) -> "AIService":
        """获取AI服务实例."""
        if self._ai_service is None:
            from src.services.ai_service import get_ai_service
            self._ai_service = get_ai_service()
        return self._ai_service

    async def remove_background(
        self,
        image: bytes,
        **kwargs,
    ) -> bytes:
        """去除图片背景.

        调用AI服务进行抠图。

        Args:
            image: 输入图片字节数据
            **kwargs: 额外参数，支持 prompt

        Returns:
            处理后的透明背景PNG图片字节数据
        """
        prompt = kwargs.get("prompt")
        logger.info("开始调用AI服务抠图")

        result = await self.ai_service.remove_background(image, prompt=prompt)

        logger.info(f"AI抠图完成，输出大小: {len(result)} bytes")
        return result

    async def health_check(self) -> bool:
        """检查服务是否可用.

        Returns:
            服务是否可用
        """
        return await self.ai_service.health_check()

    async def close(self) -> None:
        """关闭服务.

        注意：这里不关闭ai_service，因为它可能是全局单例。
        """
        pass
