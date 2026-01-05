"""AI 服务集成测试.

测试 AIService 与 AI Providers 的集成。
注意：这些测试使用 mock 避免实际 API 调用。
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.models.api_config import APIConfig
from src.models.process_config import ProcessConfig, AIPromptConfig
from src.services.ai_service import AIService
from src.services.ai_providers import AIProviderType
from src.utils.exceptions import APIKeyNotFoundError


class TestAIServiceProviderIntegration:
    """AIService 与 Provider 集成测试."""

    def test_service_creates_provider_on_demand(self):
        """测试服务按需创建提供者."""
        config = APIConfig(api_key="test-api-key")
        service = AIService(config=config)

        # 验证初始时没有提供者
        assert service._provider is None

        # 访问 provider 属性时创建
        provider = service.provider
        assert provider is not None
        assert service._provider is provider

    def test_service_without_api_key_raises_error(self):
        """测试无 API 密钥时抛出错误."""
        config = APIConfig()
        service = AIService(config=config)

        with pytest.raises(APIKeyNotFoundError):
            _ = service.provider

    def test_switch_provider_type(self):
        """测试切换提供者类型."""
        config = APIConfig(api_key="test-api-key")
        service = AIService(config=config, provider_type=AIProviderType.DASHSCOPE)

        # 获取初始提供者
        provider1 = service.provider

        # 切换提供者类型
        service.set_provider_type(AIProviderType.OPENAI)

        # 验证旧提供者被清除
        assert service._provider is None

        # 获取新提供者
        provider2 = service.provider
        assert provider2 is not provider1

    def test_config_change_resets_provider(self):
        """测试配置变更重置提供者."""
        config1 = APIConfig(api_key="test-key-1")
        service = AIService(config=config1)

        # 创建提供者
        _ = service.provider

        # 更改配置
        config2 = APIConfig(api_key="test-key-2")
        service.config = config2

        # 验证提供者被重置
        assert service._provider is None


class TestAIServiceAsyncOperations:
    """AIService 异步操作测试."""

    @pytest.mark.asyncio
    async def test_remove_background_integration(self):
        """测试背景去除集成流程."""
        config = APIConfig(api_key="test-api-key")
        service = AIService(config=config)

        # Mock provider
        mock_provider = AsyncMock()
        mock_provider.remove_background.return_value = b"result_image_data"

        with patch.object(service, "_provider", mock_provider):
            result = await service.remove_background(
                image=b"test_image_data",
                prompt="remove background"
            )

        assert result == b"result_image_data"
        mock_provider.remove_background.assert_called_once_with(
            b"test_image_data", "remove background"
        )

    @pytest.mark.asyncio
    async def test_composite_product_integration(self):
        """测试商品合成集成流程."""
        config = APIConfig(api_key="test-api-key")
        service = AIService(config=config)

        mock_provider = AsyncMock()
        mock_provider.composite_images.return_value = b"composite_result"

        with patch.object(service, "_provider", mock_provider):
            result = await service.composite_product(
                background=b"bg_data",
                product=b"prod_data",
                prompt="composite product"
            )

        assert result == b"composite_result"
        mock_provider.composite_images.assert_called_once()

    @pytest.mark.asyncio
    async def test_composite_with_config(self):
        """测试使用配置进行商品合成."""
        config = APIConfig(api_key="test-api-key")
        service = AIService(config=config)

        # 创建带提示词的处理配置
        process_config = ProcessConfig()
        process_config.prompt = AIPromptConfig(
            base_prompt="将商品自然合成到背景中",
            style_hint="保持原有风格",
            position_hint="center",  # 使用有效的枚举值
        )

        mock_provider = AsyncMock()
        mock_provider.composite_images.return_value = b"result"

        with patch.object(service, "_provider", mock_provider):
            result = await service.composite_product(
                background=b"bg",
                product=b"prod",
                config=process_config
            )

        # 验证使用了配置中的提示词
        assert mock_provider.composite_images.called

    @pytest.mark.asyncio
    async def test_edit_image_integration(self):
        """测试图片编辑集成流程."""
        config = APIConfig(api_key="test-api-key")
        service = AIService(config=config)

        mock_provider = AsyncMock()
        mock_provider.edit_image.return_value = b"edited_image"

        with patch.object(service, "_provider", mock_provider):
            result = await service.edit_image(
                image=b"original",
                prompt="enhance colors"
            )

        assert result == b"edited_image"


class TestAIServiceProviderFactory:
    """测试 AIService 与 Provider Factory 集成."""

    def test_dashscope_provider_creation(self):
        """测试创建 DashScope 提供者."""
        config = APIConfig(api_key="test-key")
        service = AIService(config=config, provider_type=AIProviderType.DASHSCOPE)

        provider = service.provider
        assert provider is not None

    def test_openai_provider_creation(self):
        """测试创建 OpenAI 提供者."""
        config = APIConfig(api_key="test-key", base_url="https://api.example.com")
        service = AIService(config=config, provider_type=AIProviderType.OPENAI)

        provider = service.provider
        assert provider is not None

    def test_provider_type_string(self):
        """测试使用字符串指定提供者类型."""
        config = APIConfig(api_key="test-key")
        service = AIService(config=config, provider_type="dashscope")

        provider = service.provider
        assert provider is not None


class TestAIServiceErrorHandling:
    """AIService 错误处理测试."""

    @pytest.mark.asyncio
    async def test_handles_provider_error(self):
        """测试处理提供者错误."""
        from src.utils.exceptions import AIServiceError

        config = APIConfig(api_key="test-key")
        service = AIService(config=config)

        mock_provider = AsyncMock()
        mock_provider.remove_background.side_effect = AIServiceError("API error")

        with patch.object(service, "_provider", mock_provider):
            with pytest.raises(AIServiceError):
                await service.remove_background(b"test")

    def test_invalid_provider_type(self):
        """测试无效的提供者类型."""
        config = APIConfig(api_key="test-key")

        with pytest.raises(ValueError):
            service = AIService(config=config, provider_type="invalid_type")
            _ = service.provider
