"""AI 服务模块.

提供统一的 AI 图片处理服务接口，支持多种 AI 服务商。

Features:
    - 背景去除
    - 商品合成
    - 多图融合编辑
    - 可扩展的提供者架构
"""

from __future__ import annotations

from typing import Optional

from src.models.api_config import APIConfig
from src.services.ai_providers import (
    BaseAIImageProvider,
    AIProviderType,
    create_ai_provider,
)
from src.utils.exceptions import (
    APIKeyNotFoundError,
)
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class AIService:
    """AI 图片处理服务.

    提供统一的 AI 图片处理接口，内部使用可切换的提供者实现。

    Attributes:
        config: API 配置
        provider: AI 提供者实例

    Example:
        >>> config = APIConfig(api_key="sk-xxx")
        >>> service = AIService(config, provider_type="dashscope")
        >>> result = await service.remove_background(image_bytes)
    """

    def __init__(
        self,
        config: Optional[APIConfig] = None,
        provider_type: AIProviderType | str = AIProviderType.DASHSCOPE,
    ) -> None:
        """初始化 AI 服务.

        Args:
            config: API 配置，如果为 None 则使用默认配置
            provider_type: AI 提供者类型，默认使用 DashScope
        """
        self._config = config or APIConfig()
        self._provider_type = provider_type
        self._provider: Optional[BaseAIImageProvider] = None

    @property
    def config(self) -> APIConfig:
        """获取 API 配置."""
        return self._config

    @config.setter
    def config(self, value: APIConfig) -> None:
        """设置 API 配置并重置提供者."""
        self._config = value
        self._provider = None

    @property
    def provider(self) -> BaseAIImageProvider:
        """获取或创建 AI 提供者实例.

        Returns:
            AI 提供者实例

        Raises:
            APIKeyNotFoundError: 当 API 密钥未配置时
        """
        if self._provider is None:
            if not self._config.has_api_key:
                raise APIKeyNotFoundError()

            self._provider = create_ai_provider(
                provider_type=self._provider_type,
                api_key=self._config.get_api_key_value(),
                model=self._config.model.model,
                base_url=self._config.base_url if "dashscope" not in self._config.base_url else None,
                timeout=self._config.timeout,
            )

        return self._provider

    def set_provider_type(self, provider_type: AIProviderType | str) -> None:
        """切换 AI 提供者类型.

        Args:
            provider_type: 新的提供者类型
        """
        self._provider_type = provider_type
        self._provider = None
        logger.info(f"AI 提供者已切换为: {provider_type}")

    async def remove_background(
        self,
        image: bytes,
        prompt: Optional[str] = None,
    ) -> bytes:
        """去除图片背景.

        使用 AI 将图片背景去除，返回透明 PNG。

        Args:
            image: 输入图片的字节数据
            prompt: 可选的提示词，用于指导背景去除

        Returns:
            处理后的透明 PNG 图片字节数据

        Raises:
            AIServiceError: 当 AI 处理失败时
            APIKeyNotFoundError: 当 API 密钥未配置时
            APIRequestError: 当 API 请求失败时
            APITimeoutError: 当请求超时时
        """
        return await self.provider.remove_background(image, prompt)

    async def composite_product(
        self,
        background: bytes,
        product: bytes,
        prompt: Optional[str] = None,
        position_hint: Optional[str] = None,
    ) -> bytes:
        """将商品合成到背景图中.

        使用 AI 多图融合功能将商品自然地合成到背景/场景图片中。

        Args:
            background: 背景图片的字节数据
            product: 商品图片的字节数据（建议为透明背景）
            prompt: 可选的合成提示词
            position_hint: 位置提示（如 "center", "left", "right"）

        Returns:
            合成后的图片字节数据

        Raises:
            AIServiceError: 当 AI 处理失败时
            APIKeyNotFoundError: 当 API 密钥未配置时
            APIRequestError: 当 API 请求失败时
            APITimeoutError: 当请求超时时
        """
        # 构建合成提示词
        position_desc = position_hint or "合适"
        default_prompt = (
            f"将图2中的商标/图案合成到图1中的商品上。"
            f"合成要求：符合图1的风格、光线、角度，"
            f"商标大小适中，位置在{position_desc}位置，看上去自然合理。"
        )

        return await self.provider.composite_images(
            images=[background, product],
            prompt=prompt or default_prompt,
        )

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
        return await self.provider.edit_image(image, prompt)

    async def health_check(self) -> bool:
        """检查 AI 服务是否可用.

        Returns:
            服务是否可用
        """
        try:
            if not self._config.has_api_key:
                logger.warning("API 密钥未配置")
                return False

            return await self.provider.health_check()

        except Exception as e:
            logger.warning(f"AI 服务健康检查失败: {e}")
            return False

    async def close(self) -> None:
        """关闭服务，释放资源."""
        if self._provider:
            await self._provider.close()
            self._provider = None
            logger.debug("AI 服务已关闭")

    async def __aenter__(self) -> "AIService":
        """异步上下文管理器入口."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """异步上下文管理器出口."""
        await self.close()


# 单例实例
_ai_service_instance: Optional[AIService] = None


def get_ai_service(
    config: Optional[APIConfig] = None,
    provider_type: AIProviderType | str = AIProviderType.DASHSCOPE,
) -> AIService:
    """获取 AI 服务单例.

    Args:
        config: API 配置，首次调用时必须提供
        provider_type: AI 提供者类型

    Returns:
        AIService 实例
    """
    global _ai_service_instance

    if _ai_service_instance is None:
        _ai_service_instance = AIService(config, provider_type)
    elif config is not None:
        _ai_service_instance.config = config

    return _ai_service_instance


async def reset_ai_service() -> None:
    """重置 AI 服务单例."""
    global _ai_service_instance

    if _ai_service_instance:
        await _ai_service_instance.close()
        _ai_service_instance = None
