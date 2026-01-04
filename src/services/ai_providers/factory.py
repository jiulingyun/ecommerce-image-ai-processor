"""AI 提供者工厂.

提供创建 AI 提供者实例的工厂函数。
"""

from __future__ import annotations

from typing import Optional

from src.services.ai_providers.base import BaseAIImageProvider, AIProviderType
from src.services.ai_providers.dashscope_provider import DashScopeProvider
from src.services.ai_providers.openai_provider import OpenAIProvider
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

# 提供者类型到类的映射
_PROVIDER_CLASSES: dict[AIProviderType, type[BaseAIImageProvider]] = {
    AIProviderType.DASHSCOPE: DashScopeProvider,
    AIProviderType.OPENAI: OpenAIProvider,
}


def get_available_providers() -> list[AIProviderType]:
    """获取可用的提供者类型列表.

    Returns:
        可用的提供者类型列表
    """
    return list(_PROVIDER_CLASSES.keys())


def create_ai_provider(
    provider_type: AIProviderType | str,
    api_key: str,
    model: Optional[str] = None,
    **kwargs,
) -> BaseAIImageProvider:
    """创建 AI 提供者实例.

    Args:
        provider_type: 提供者类型
        api_key: API 密钥
        model: 模型名称
        **kwargs: 其他配置参数

    Returns:
        AI 提供者实例

    Raises:
        ValueError: 当提供者类型不支持时
    """
    # 转换字符串为枚举
    if isinstance(provider_type, str):
        try:
            provider_type = AIProviderType(provider_type.lower())
        except ValueError:
            raise ValueError(f"不支持的 AI 提供者类型: {provider_type}")

    provider_class = _PROVIDER_CLASSES.get(provider_type)
    if provider_class is None:
        raise ValueError(f"不支持的 AI 提供者类型: {provider_type}")

    logger.info(f"创建 AI 提供者: {provider_type.value}")
    return provider_class(api_key=api_key, model=model, **kwargs)


def register_provider(
    provider_type: AIProviderType,
    provider_class: type[BaseAIImageProvider],
) -> None:
    """注册自定义 AI 提供者.

    允许扩展自定义的 AI 提供者实现。

    Args:
        provider_type: 提供者类型标识
        provider_class: 提供者类

    Raises:
        ValueError: 当类型已存在时
    """
    if provider_type in _PROVIDER_CLASSES:
        raise ValueError(f"提供者类型已存在: {provider_type}")

    _PROVIDER_CLASSES[provider_type] = provider_class
    logger.info(f"注册自定义 AI 提供者: {provider_type.value}")
