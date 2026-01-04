"""AI 服务模块.

封装 GPT-Image-1.5 API 调用，提供图片处理能力。

Features:
    - 背景去除
    - 商品合成
    - 异步处理
    - 自动重试
"""

from __future__ import annotations

import asyncio
import base64
import io
from typing import Optional

from openai import AsyncOpenAI, APIConnectionError, APITimeoutError as OpenAITimeoutError
from openai import RateLimitError, APIStatusError
from PIL import Image

from src.models.api_config import APIConfig, ImageGenerationParams
from src.utils.constants import API_TIMEOUT
from src.utils.exceptions import (
    AIServiceError,
    APIKeyNotFoundError,
    APIRequestError,
    APITimeoutError,
)
from src.utils.logger import setup_logger
from src.utils.retry import async_retry

logger = setup_logger(__name__)


class AIService:
    """GPT-Image-1.5 API 服务封装.

    提供 AI 图片处理能力，包括背景去除和商品合成。

    Attributes:
        config: API 配置
        client: OpenAI 异步客户端

    Example:
        >>> config = APIConfig(api_key="sk-xxx")
        >>> service = AIService(config)
        >>> result = await service.remove_background(image_bytes)
    """

    def __init__(self, config: Optional[APIConfig] = None) -> None:
        """初始化 AI 服务.

        Args:
            config: API 配置，如果为 None 则使用默认配置
        """
        self._config = config or APIConfig()
        self._client: Optional[AsyncOpenAI] = None

    @property
    def config(self) -> APIConfig:
        """获取 API 配置."""
        return self._config

    @config.setter
    def config(self, value: APIConfig) -> None:
        """设置 API 配置并重置客户端."""
        self._config = value
        self._client = None

    @property
    def client(self) -> AsyncOpenAI:
        """获取或创建 OpenAI 异步客户端.

        Returns:
            AsyncOpenAI 客户端实例

        Raises:
            APIKeyNotFoundError: 当 API 密钥未配置时
        """
        if self._client is None:
            if not self._config.has_api_key:
                raise APIKeyNotFoundError()

            self._client = AsyncOpenAI(
                api_key=self._config.get_api_key_value(),
                base_url=self._config.base_url,
                timeout=self._config.timeout,
                max_retries=0,  # 我们使用自己的重试机制
            )

        return self._client

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
        default_prompt = (
            "Remove the background from this image completely, "
            "keeping only the main subject. Make the background transparent. "
            "Preserve all details of the main subject with clean edges."
        )

        return await self._edit_image(
            image=image,
            prompt=prompt or default_prompt,
            operation="remove_background",
        )

    async def composite_product(
        self,
        background: bytes,
        product: bytes,
        prompt: Optional[str] = None,
        position_hint: Optional[str] = None,
    ) -> bytes:
        """将商品合成到背景图中.

        使用 AI 将商品自然地合成到背景/场景图片中。

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
        position_desc = position_hint or "appropriate position"
        default_prompt = (
            f"Seamlessly composite the product into this scene at {position_desc}. "
            "The product should blend naturally with the scene's lighting, "
            "shadows, and perspective. Maintain the product's original appearance "
            "while making it look like a natural part of the scene."
        )

        # 合并两张图片作为输入
        merged_image = await self._merge_images_for_composite(background, product)

        return await self._edit_image(
            image=merged_image,
            prompt=prompt or default_prompt,
            operation="composite_product",
        )

    async def generate_scene(
        self,
        prompt: str,
        params: Optional[ImageGenerationParams] = None,
    ) -> bytes:
        """生成场景图片.

        使用 AI 根据提示词生成场景图片。

        Args:
            prompt: 场景描述提示词
            params: 生成参数

        Returns:
            生成的图片字节数据

        Raises:
            AIServiceError: 当 AI 处理失败时
            APIKeyNotFoundError: 当 API 密钥未配置时
            APIRequestError: 当 API 请求失败时
            APITimeoutError: 当请求超时时
        """
        params = params or ImageGenerationParams(prompt=prompt)
        if not params.prompt:
            params = params.model_copy(update={"prompt": prompt})

        return await self._generate_image(params)

    @async_retry(
        max_retries=3,
        delay=1.0,
        backoff=2.0,
        exceptions=(APIConnectionError, RateLimitError),
    )
    async def _edit_image(
        self,
        image: bytes,
        prompt: str,
        operation: str,
    ) -> bytes:
        """内部方法：编辑图片.

        Args:
            image: 输入图片字节数据
            prompt: 编辑提示词
            operation: 操作名称（用于日志）

        Returns:
            处理后的图片字节数据
        """
        logger.info(f"开始 AI 图片处理: {operation}")

        try:
            # 将 bytes 转换为类文件对象
            image_file = io.BytesIO(image)
            image_file.name = "image.png"

            response = await self.client.images.edit(
                model=self._config.model.model,
                image=image_file,
                prompt=prompt,
                n=1,
                size="1024x1024",
                response_format="b64_json",
            )

            # 解码 base64 响应
            if response.data and len(response.data) > 0:
                b64_data = response.data[0].b64_json
                if b64_data:
                    result = base64.b64decode(b64_data)
                    logger.info(f"AI 图片处理完成: {operation}, 输出大小: {len(result)} bytes")
                    return result

            raise AIServiceError(f"AI 返回空结果: {operation}")

        except OpenAITimeoutError as e:
            logger.error(f"AI 请求超时: {operation}")
            raise APITimeoutError(self._config.timeout) from e

        except APIStatusError as e:
            logger.error(f"AI API 错误: {operation}, status={e.status_code}, message={e.message}")
            raise APIRequestError(e.message, e.status_code) from e

        except APIConnectionError as e:
            logger.error(f"AI 连接错误: {operation}, {e}")
            raise APIRequestError(f"无法连接到 AI 服务: {e}") from e

        except Exception as e:
            logger.exception(f"AI 处理未知错误: {operation}")
            raise AIServiceError(f"AI 处理失败: {e}") from e

    @async_retry(
        max_retries=3,
        delay=1.0,
        backoff=2.0,
        exceptions=(APIConnectionError, RateLimitError),
    )
    async def _generate_image(self, params: ImageGenerationParams) -> bytes:
        """内部方法：生成图片.

        Args:
            params: 生成参数

        Returns:
            生成的图片字节数据
        """
        logger.info(f"开始 AI 图片生成, prompt: {params.prompt[:50]}...")

        try:
            response = await self.client.images.generate(
                model=self._config.model.model,
                prompt=params.prompt,
                n=params.n,
                size=params.size,
                quality=params.quality,
                response_format="b64_json",
            )

            if response.data and len(response.data) > 0:
                b64_data = response.data[0].b64_json
                if b64_data:
                    result = base64.b64decode(b64_data)
                    logger.info(f"AI 图片生成完成, 输出大小: {len(result)} bytes")
                    return result

            raise AIServiceError("AI 返回空结果")

        except OpenAITimeoutError as e:
            logger.error("AI 请求超时")
            raise APITimeoutError(self._config.timeout) from e

        except APIStatusError as e:
            logger.error(f"AI API 错误: status={e.status_code}, message={e.message}")
            raise APIRequestError(e.message, e.status_code) from e

        except APIConnectionError as e:
            logger.error(f"AI 连接错误: {e}")
            raise APIRequestError(f"无法连接到 AI 服务: {e}") from e

        except Exception as e:
            logger.exception("AI 生成未知错误")
            raise AIServiceError(f"AI 生成失败: {e}") from e

    async def _merge_images_for_composite(
        self,
        background: bytes,
        product: bytes,
    ) -> bytes:
        """合并两张图片用于合成处理.

        将背景和商品图并排放置，便于 AI 理解合成需求。

        Args:
            background: 背景图片字节数据
            product: 商品图片字节数据

        Returns:
            合并后的图片字节数据
        """
        # 在线程池中执行图片操作，避免阻塞事件循环
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._merge_images_sync,
            background,
            product,
        )

    def _merge_images_sync(self, background: bytes, product: bytes) -> bytes:
        """同步方法：合并图片.

        Args:
            background: 背景图片字节数据
            product: 商品图片字节数据

        Returns:
            合并后的图片字节数据
        """
        # 打开图片
        bg_img = Image.open(io.BytesIO(background))
        prod_img = Image.open(io.BytesIO(product))

        # 确保都是 RGBA 模式
        if bg_img.mode != "RGBA":
            bg_img = bg_img.convert("RGBA")
        if prod_img.mode != "RGBA":
            prod_img = prod_img.convert("RGBA")

        # 调整尺寸为相同高度
        target_height = min(bg_img.height, prod_img.height, 512)

        bg_ratio = target_height / bg_img.height
        bg_new_size = (int(bg_img.width * bg_ratio), target_height)
        bg_img = bg_img.resize(bg_new_size, Image.Resampling.LANCZOS)

        prod_ratio = target_height / prod_img.height
        prod_new_size = (int(prod_img.width * prod_ratio), target_height)
        prod_img = prod_img.resize(prod_new_size, Image.Resampling.LANCZOS)

        # 创建并排画布
        total_width = bg_img.width + prod_img.width + 20  # 20px 间隔
        merged = Image.new("RGBA", (total_width, target_height), (255, 255, 255, 255))

        # 粘贴图片
        merged.paste(bg_img, (0, 0), bg_img)
        merged.paste(prod_img, (bg_img.width + 20, 0), prod_img)

        # 转换为 bytes
        output = io.BytesIO()
        merged.save(output, format="PNG")
        return output.getvalue()

    async def health_check(self) -> bool:
        """检查 AI 服务是否可用.

        Returns:
            服务是否可用
        """
        try:
            if not self._config.has_api_key:
                logger.warning("API 密钥未配置")
                return False

            # 尝试一个简单的 API 调用来验证连接
            response = await self.client.models.list()
            logger.info("AI 服务健康检查通过")
            return True

        except Exception as e:
            logger.warning(f"AI 服务健康检查失败: {e}")
            return False

    async def close(self) -> None:
        """关闭客户端连接."""
        if self._client:
            await self._client.close()
            self._client = None
            logger.debug("AI 服务客户端已关闭")

    async def __aenter__(self) -> "AIService":
        """异步上下文管理器入口."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """异步上下文管理器出口."""
        await self.close()


# 单例实例
_ai_service_instance: Optional[AIService] = None


def get_ai_service(config: Optional[APIConfig] = None) -> AIService:
    """获取 AI 服务单例.

    Args:
        config: API 配置，首次调用时必须提供

    Returns:
        AIService 实例
    """
    global _ai_service_instance

    if _ai_service_instance is None:
        _ai_service_instance = AIService(config)
    elif config is not None:
        _ai_service_instance.config = config

    return _ai_service_instance


async def reset_ai_service() -> None:
    """重置 AI 服务单例."""
    global _ai_service_instance

    if _ai_service_instance:
        await _ai_service_instance.close()
        _ai_service_instance = None
