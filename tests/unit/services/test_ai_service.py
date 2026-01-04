"""AI 服务单元测试."""

from __future__ import annotations

import io
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from PIL import Image
from pydantic import SecretStr

from src.models.api_config import APIConfig, ImageGenerationParams
from src.services.ai_service import (
    AIService,
    get_ai_service,
    reset_ai_service,
)
from src.utils.exceptions import (
    AIServiceError,
    APIKeyNotFoundError,
    APIRequestError,
    APITimeoutError,
)


# ===================
# Fixtures
# ===================
@pytest.fixture
def api_config() -> APIConfig:
    """返回测试用 API 配置."""
    return APIConfig(
        base_url="https://api.test.com/v1",
        api_key=SecretStr("sk-test-key-12345"),
        timeout=30,
        max_retries=2,
    )


@pytest.fixture
def ai_service(api_config: APIConfig) -> AIService:
    """返回测试用 AI 服务实例."""
    return AIService(api_config)


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
def mock_openai_response() -> MagicMock:
    """模拟 OpenAI API 响应."""
    # 创建模拟图片作为 base64 响应
    img = Image.new("RGBA", (100, 100), (0, 255, 0, 255))
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")

    import base64
    b64_data = base64.b64encode(buffer.getvalue()).decode()

    response = MagicMock()
    response.data = [MagicMock(b64_json=b64_data)]
    return response


# ===================
# 初始化测试
# ===================
class TestAIServiceInit:
    """测试 AIService 初始化."""

    def test_init_with_config(self, api_config: APIConfig) -> None:
        """测试使用配置初始化."""
        service = AIService(api_config)
        assert service.config == api_config
        assert service._client is None

    def test_init_without_config(self) -> None:
        """测试不使用配置初始化."""
        service = AIService()
        assert service.config is not None
        assert service.config.base_url == "https://api.openai.com/v1"

    def test_config_setter_resets_client(self, ai_service: AIService) -> None:
        """测试设置配置会重置客户端."""
        # 模拟已创建客户端
        ai_service._client = MagicMock()

        # 设置新配置
        new_config = APIConfig(api_key=SecretStr("new-key"))
        ai_service.config = new_config

        assert ai_service._client is None
        assert ai_service.config == new_config


# ===================
# 客户端测试
# ===================
class TestAIServiceClient:
    """测试 AIService 客户端."""

    def test_client_raises_without_api_key(self) -> None:
        """测试没有 API 密钥时抛出异常."""
        service = AIService(APIConfig())  # 没有 api_key

        with pytest.raises(APIKeyNotFoundError):
            _ = service.client

    def test_client_creates_async_client(self, ai_service: AIService) -> None:
        """测试客户端创建."""
        with patch("src.services.ai_service.AsyncOpenAI") as mock_client:
            _ = ai_service.client

            mock_client.assert_called_once()
            call_kwargs = mock_client.call_args[1]
            assert call_kwargs["api_key"] == "sk-test-key-12345"
            assert call_kwargs["base_url"] == "https://api.test.com/v1"
            assert call_kwargs["timeout"] == 30
            assert call_kwargs["max_retries"] == 0


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
        mock_openai_response: MagicMock,
    ) -> None:
        """测试成功去除背景."""
        mock_client = AsyncMock()
        mock_client.images.edit = AsyncMock(return_value=mock_openai_response)

        with patch.object(ai_service, "_client", mock_client):
            result = await ai_service.remove_background(sample_image_bytes)

            assert isinstance(result, bytes)
            assert len(result) > 0

            # 验证 API 调用
            mock_client.images.edit.assert_called_once()
            call_kwargs = mock_client.images.edit.call_args[1]
            assert "Remove the background" in call_kwargs["prompt"]

    @pytest.mark.asyncio
    async def test_remove_background_custom_prompt(
        self,
        ai_service: AIService,
        sample_image_bytes: bytes,
        mock_openai_response: MagicMock,
    ) -> None:
        """测试使用自定义提示词去除背景."""
        mock_client = AsyncMock()
        mock_client.images.edit = AsyncMock(return_value=mock_openai_response)

        custom_prompt = "Make the background white"

        with patch.object(ai_service, "_client", mock_client):
            await ai_service.remove_background(sample_image_bytes, prompt=custom_prompt)

            call_kwargs = mock_client.images.edit.call_args[1]
            assert call_kwargs["prompt"] == custom_prompt


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
        mock_openai_response: MagicMock,
    ) -> None:
        """测试成功合成商品."""
        mock_client = AsyncMock()
        mock_client.images.edit = AsyncMock(return_value=mock_openai_response)

        with patch.object(ai_service, "_client", mock_client):
            result = await ai_service.composite_product(
                background=sample_background_bytes,
                product=sample_image_bytes,
            )

            assert isinstance(result, bytes)
            assert len(result) > 0

    @pytest.mark.asyncio
    async def test_composite_product_with_position(
        self,
        ai_service: AIService,
        sample_background_bytes: bytes,
        sample_image_bytes: bytes,
        mock_openai_response: MagicMock,
    ) -> None:
        """测试使用位置提示合成商品."""
        mock_client = AsyncMock()
        mock_client.images.edit = AsyncMock(return_value=mock_openai_response)

        with patch.object(ai_service, "_client", mock_client):
            await ai_service.composite_product(
                background=sample_background_bytes,
                product=sample_image_bytes,
                position_hint="center",
            )

            call_kwargs = mock_client.images.edit.call_args[1]
            assert "center" in call_kwargs["prompt"]


# ===================
# 场景生成测试
# ===================
class TestGenerateScene:
    """测试场景生成功能."""

    @pytest.mark.asyncio
    async def test_generate_scene_success(
        self,
        ai_service: AIService,
        mock_openai_response: MagicMock,
    ) -> None:
        """测试成功生成场景."""
        mock_client = AsyncMock()
        mock_client.images.generate = AsyncMock(return_value=mock_openai_response)

        with patch.object(ai_service, "_client", mock_client):
            result = await ai_service.generate_scene(
                prompt="A modern living room with white walls",
            )

            assert isinstance(result, bytes)
            assert len(result) > 0

            mock_client.images.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_scene_with_params(
        self,
        ai_service: AIService,
        mock_openai_response: MagicMock,
    ) -> None:
        """测试使用参数生成场景."""
        mock_client = AsyncMock()
        mock_client.images.generate = AsyncMock(return_value=mock_openai_response)

        params = ImageGenerationParams(
            prompt="A cozy cafe interior",
            size="1024x1024",
            quality="hd",
        )

        with patch.object(ai_service, "_client", mock_client):
            await ai_service.generate_scene(prompt="", params=params)

            call_kwargs = mock_client.images.generate.call_args[1]
            assert call_kwargs["size"] == "1024x1024"
            assert call_kwargs["quality"] == "hd"


# ===================
# 错误处理测试
# ===================
class TestErrorHandling:
    """测试错误处理."""

    @pytest.mark.asyncio
    async def test_api_timeout_error(
        self,
        ai_service: AIService,
        sample_image_bytes: bytes,
    ) -> None:
        """测试 API 超时错误."""
        from openai import APITimeoutError as OpenAITimeoutError

        mock_client = AsyncMock()
        mock_client.images.edit = AsyncMock(
            side_effect=OpenAITimeoutError(request=MagicMock())
        )

        with patch.object(ai_service, "_client", mock_client):
            with pytest.raises(APITimeoutError):
                await ai_service.remove_background(sample_image_bytes)

    @pytest.mark.asyncio
    async def test_api_status_error(
        self,
        ai_service: AIService,
        sample_image_bytes: bytes,
    ) -> None:
        """测试 API 状态错误."""
        from openai import APIStatusError

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.headers = {}

        mock_client = AsyncMock()
        mock_client.images.edit = AsyncMock(
            side_effect=APIStatusError(
                message="Bad request",
                response=mock_response,
                body={"error": {"message": "Bad request"}},
            )
        )

        with patch.object(ai_service, "_client", mock_client):
            with pytest.raises(APIRequestError) as exc_info:
                await ai_service.remove_background(sample_image_bytes)

            assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_empty_response_error(
        self,
        ai_service: AIService,
        sample_image_bytes: bytes,
    ) -> None:
        """测试空响应错误."""
        mock_response = MagicMock()
        mock_response.data = []  # 空数据

        mock_client = AsyncMock()
        mock_client.images.edit = AsyncMock(return_value=mock_response)

        with patch.object(ai_service, "_client", mock_client):
            with pytest.raises(AIServiceError) as exc_info:
                await ai_service.remove_background(sample_image_bytes)

            assert "空结果" in str(exc_info.value)


# ===================
# 图片合并测试
# ===================
class TestImageMerging:
    """测试图片合并功能."""

    def test_merge_images_sync(
        self,
        ai_service: AIService,
        sample_background_bytes: bytes,
        sample_image_bytes: bytes,
    ) -> None:
        """测试同步合并图片."""
        result = ai_service._merge_images_sync(
            sample_background_bytes,
            sample_image_bytes,
        )

        assert isinstance(result, bytes)

        # 验证合并后的图片
        img = Image.open(io.BytesIO(result))
        assert img.mode == "RGBA"
        # 合并后宽度应该大于单张图片
        assert img.width > 100


# ===================
# 健康检查测试
# ===================
class TestHealthCheck:
    """测试健康检查功能."""

    @pytest.mark.asyncio
    async def test_health_check_success(self, ai_service: AIService) -> None:
        """测试健康检查成功."""
        mock_client = AsyncMock()
        mock_client.models.list = AsyncMock(return_value=MagicMock())

        with patch.object(ai_service, "_client", mock_client):
            result = await ai_service.health_check()
            assert result is True

    @pytest.mark.asyncio
    async def test_health_check_no_api_key(self) -> None:
        """测试没有 API 密钥时健康检查失败."""
        service = AIService(APIConfig())
        result = await service.health_check()
        assert result is False

    @pytest.mark.asyncio
    async def test_health_check_api_error(self, ai_service: AIService) -> None:
        """测试 API 错误时健康检查失败."""
        mock_client = AsyncMock()
        mock_client.models.list = AsyncMock(side_effect=Exception("Connection failed"))

        with patch.object(ai_service, "_client", mock_client):
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
