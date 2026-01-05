"""抠图服务模块.

提供统一的抠图服务接口，支持多种实现方式。

Example:
    >>> from src.services.background_removal import get_background_remover
    >>> remover = get_background_remover("external_api", api_url="http://localhost:5000/api/remove-background")
    >>> result = await remover.remove_background(image_bytes)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from src.services.background_removal.base import (
    BackgroundRemoverType,
    BaseBackgroundRemover,
)
from src.services.background_removal.ai_remover import AIRemover
from src.services.background_removal.external_api_remover import ExternalAPIRemover

if TYPE_CHECKING:
    from src.services.ai_service import AIService

__all__ = [
    "BackgroundRemoverType",
    "BaseBackgroundRemover",
    "AIRemover",
    "ExternalAPIRemover",
    "get_background_remover",
]


# 单例实例缓存
_remover_instances: dict[str, BaseBackgroundRemover] = {}


def get_background_remover(
    remover_type: BackgroundRemoverType | str = BackgroundRemoverType.EXTERNAL_API,
    *,
    # 外部API参数
    api_url: Optional[str] = None,
    api_key: Optional[str] = None,
    timeout: int = 120,
    proxy: Optional[str] = None,
    # AI服务参数
    ai_service: Optional["AIService"] = None,
    # 其他
    use_cache: bool = True,
) -> BaseBackgroundRemover:
    """获取抠图服务实例.

    工厂函数，根据类型返回对应的抠图服务实例。

    Args:
        remover_type: 抠图服务类型
        api_url: 外部API地址（external_api类型必需）
        api_key: 外部API密钥
        timeout: 请求超时时间（秒）
        proxy: 代理设置
        ai_service: AI服务实例（ai类型可选）
        use_cache: 是否使用缓存的实例

    Returns:
        抠图服务实例

    Raises:
        ValueError: 参数无效

    Example:
        >>> # 使用外部API
        >>> remover = get_background_remover(
        ...     "external_api",
        ...     api_url="http://localhost:5000/api/remove-background",
        ...     api_key="your-api-key"
        ... )
        >>>
        >>> # 使用AI服务
        >>> remover = get_background_remover("ai")
    """
    # 转换字符串类型
    if isinstance(remover_type, str):
        try:
            remover_type = BackgroundRemoverType(remover_type)
        except ValueError:
            raise ValueError(f"不支持的抠图服务类型: {remover_type}")

    # 生成缓存键
    cache_key = f"{remover_type.value}:{api_url or ''}:{api_key or ''}"

    # 检查缓存
    if use_cache and cache_key in _remover_instances:
        return _remover_instances[cache_key]

    # 创建实例
    if remover_type == BackgroundRemoverType.EXTERNAL_API:
        if not api_url:
            raise ValueError("使用外部API抠图服务时必须指定 api_url")
        instance = ExternalAPIRemover(
            api_url=api_url,
            api_key=api_key or "",
            timeout=timeout,
            proxy=proxy,
        )
    elif remover_type == BackgroundRemoverType.AI:
        instance = AIRemover(ai_service=ai_service)
    else:
        raise ValueError(f"不支持的抠图服务类型: {remover_type}")

    # 缓存实例
    if use_cache:
        _remover_instances[cache_key] = instance

    return instance


def reset_background_remover_cache() -> None:
    """重置抠图服务缓存."""
    global _remover_instances
    _remover_instances = {}
