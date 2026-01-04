"""AI 服务单元测试."""

from __future__ import annotations

import io
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from PIL import Image
from pydantic import SecretStr

from src.models.api_config import APIConfig
from src.services.ai_service import (
    AIService,
    get_ai_service,
    reset_ai_service,
)
from src.services.ai_providers import AIProviderType
from src.utils.exceptions import (
    AIServiceError,
    APIKeyNotFoundError,
)


# ===================
# Fixtures
# ===================
@pytest.fixture
def api_config() -> APIConfig:
    """返回测试用 API 配置."""
    return APIConfig(
        api_key=SecretStr("*****************"),
        timeout=30,
        max_retries=2,
    )


@pytest.fixture
def ai_service(api_config: APIConfig) -> AIService:
    """返回测试用 AI 服务实例."""
    return AIService(api_config, provider_type=AIProviderType.DASHSCOPE)


@pytest.fixture
def sample_image_bytes() -> bytes:
    """生成测试用图片字节数据."""
    img = Image.new("RGBA", (100, 100), (255, 0, 0, 255))
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture
def sample_background_bytes() -> bytes:
    """生成测试用背景图片."""
    img = Image.new("RGB", (200, 200), (0, 128, 255))
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture
def mock_provider_response() -> bytes:
    """模拟提供者返回的图片数据."""
    img = Image.new("RGBA", (100, 100), (0, 255, 0, 255))
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


# ===================
# 初始化测试
# ===================
class TestAIServiceInit:
    """测试 AIService 初始化."""

    def test_init_with_config(self, api_config: APIConfig) -> None:
        """测试使用配置初始化."""
        service = AIService(api_config)
        assert service.config == api_config
        assert service._provider is None

    def test_init_without_config(self) -> None:
        """测试不使用配置初始化."""
        service = AIService()
        assert service.config is not None

    def test_config_setter_resets_provider(self, ai_service: AIService) -> None:
        """测试设置配置会重置提供者."""
        # 模拟已创建提供者
        ai_service._provider = MagicMock()

        # 设置新配置
        new_config = APIConfig(api_key=SecretStr("new-key"))
        ai_service.config = new_config

        assert ai_service._provider is None
        assert ai_service.config == new_config


# ===================
# 提供者测试
# ===================
class TestAIServiceProvider:
    """测试 AIService 提供者."""

    def test_provider_raises_without_api_key(self) -> None:
        """测试没有 API 密钥时抛出异常."""
        service = AIService(APIConfig())  # 没有 api_key

        with pytest.raises(APIKeyNotFoundError):
            _ = service.provider

    def test_provider_creates_dashscope_provider(self, api_config: APIConfig) -> None:
        """测试创建 DashScope 提供者."""
        service = AIService(api_config, provider_type=AIProviderType.DASHSCOPE)
        provider = service.provider
        assert provider.provider_type == AIProviderType.DASHSCOPE

    def test_provider_creates_openai_provider(self, api_config: APIConfig) -> None:
        """测试创建 OpenAI 提供者."""
        service = AIService(api_config, provider_type=AIProviderType.OPENAI)
        provider = service.provider
        assert provider.provider_type == AIProviderType.OPENAI

    def test_set_provider_type(self, ai_service: AIService) -> None:
        """测试切换提供者类型."""
        ai_service._provider = MagicMock()
        ai_service.set_provider_type(AIProviderType.OPENAI)
        assert ai_service._provider is None


# ===================
# 背景去除测试
# ===================
class TestRemoveBackground:
    """测试背景去除功能."""

    @pytest.mark.asyncio
    async def test_remove_background_success(
        self,
        ai_service: AIService,
        sample_image_bytes: bytes,
        mock_provider_response: bytes,
    ) -> None:
        """测试成功去除背景."""
        mock_provider = AsyncMock()
        mock_provider.remove_background = AsyncMock(return_value=mock_provider_response)

        ai_service._provider = mock_provider
        result = await ai_service.remove_background(sample_image_bytes)

        assert isinstance(result, bytes)
        assert len(result) > 0
        mock_provider.remove_background.assert_called_once()

    @pytest.mark.asyncio
    async def test_remove_background_custom_prompt(
        self,
        ai_service: AIService,
        sample_image_bytes: bytes,
        mock_provider_response: bytes,
    ) -> None:
        """测试使用自定义提示词去除背景."""
        mock_provider = AsyncMock()
        mock_provider.remove_background = AsyncMock(return_value=mock_provider_response)

        custom_prompt = "Make the background white"

        ai_service._provider = mock_provider
        await ai_service.remove_background(sample_image_bytes, prompt=custom_prompt)

        mock_provider.remove_background.assert_called_once_with(
            sample_image_bytes, custom_prompt
        )


# ===================
# 商品合成测试
# ===================
class TestCompositeProduct:
    """测试商品合成功能."""

    @pytest.mark.asyncio
    async def test_composite_product_success(
        self,
        ai_service: AIService,
        sample_background_bytes: bytes,
        sample_image_bytes: bytes,
        mock_provider_response: bytes,
    ) -> None:
        """测试成功合成商品."""
        mock_provider = AsyncMock()
        mock_provider.composite_images = AsyncMock(return_value=mock_provider_response)

        ai_service._provider = mock_provider
        result = await ai_service.composite_product(
            background=sample_background_bytes,
            product=sample_image_bytes,
        )

        assert isinstance(result, bytes)
        assert len(result) > 0
        mock_provider.composite_images.assert_called_once()

    @pytest.mark.asyncio
    async def test_composite_product_with_position(
        self,
        ai_service: AIService,
        sample_background_bytes: bytes,
        sample_image_bytes: bytes,
        mock_provider_response: bytes,
    ) -> None:
        """测试使用位置提示合成商品."""
        mock_provider = AsyncMock()
        mock_provider.composite_images = AsyncMock(return_value=mock_provider_response)

        ai_service._provider = mock_provider
        await ai_service.composite_product(
            background=sample_background_bytes,
            product=sample_image_bytes,
            position_hint="center",
        )

        call_args = mock_provider.composite_images.call_args
        assert "center" in call_args[1]["prompt"]


# ===================
# 健康检查测试
# ===================
class TestHealthCheck:
    """测试健康检查功能."""

    @pytest.mark.asyncio
    async def test_health_check_success(self, ai_service: AIService) -> None:
        """测试健康检查成功."""
        mock_provider = AsyncMock()
        mock_provider.health_check = AsyncMock(return_value=True)

        ai_service._provider = mock_provider
        result = await ai_service.health_check()
        assert result is True

    @pytest.mark.asyncio
    async def test_health_check_no_api_key(self) -> None:
        """测试没有 API 密钥时健康检查失败."""
        service = AIService(APIConfig())
        result = await service.health_check()
        assert result is False

    @pytest.mark.asyncio
    async def test_health_check_provider_error(self, ai_service: AIService) -> None:
        """测试提供者错误时健康检查失败."""
        mock_provider = AsyncMock()
        mock_provider.health_check = AsyncMock(side_effect=Exception("Connection failed"))

        ai_service._provider = mock_provider
        result = await ai_service.health_check()
        assert result is False


# ===================
# 上下文管理器测试
# ===================
class TestContextManager:
    """测试上下文管理器."""

    @pytest.mark.asyncio
    async def test_async_context_manager(self, api_config: APIConfig) -> None:
        """测试异步上下文管理器."""
        async with AIService(api_config) as service:
            assert service is not None
            assert isinstance(service, AIService)


# ===================
# 单例测试
# ===================
class TestSingleton:
    """测试单例模式."""

    @pytest.mark.asyncio
    async def test_get_ai_service_singleton(self, api_config: APIConfig) -> None:
        """测试获取单例."""
        # 重置单例
        await reset_ai_service()

        service1 = get_ai_service(api_config)
        service2 = get_ai_service()

        assert service1 is service2

        # 清理
        await reset_ai_service()

    @pytest.mark.asyncio
    async def test_get_ai_service_update_config(self, api_config: APIConfig) -> None:
        """测试更新配置."""
        await reset_ai_service()

        service1 = get_ai_service(api_config)

        new_config = APIConfig(
            api_key=SecretStr("new-key"),
            base_url="https://new-api.com/v1",
        )
        service2 = get_ai_service(new_config)

        assert service1 is service2
        assert service2.config.base_url == "https://new-api.com/v1"

        await reset_ai_service()

    @pytest.mark.asyncio
    async def test_reset_ai_service(self, api_config: APIConfig) -> None:
        """测试重置单例."""
        service1 = get_ai_service(api_config)
        await reset_ai_service()
        service2 = get_ai_service(api_config)

        assert service1 is not service2
