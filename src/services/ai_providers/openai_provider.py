"""OpenAI AI 图片处理提供者.

使用 OpenAI API 实现图片编辑功能。
"""

from __future__ import annotations

import asyncio
import base64
import io
from typing import Optional

from openai import (
    AsyncOpenAI,
    APIConnectionError,
    APITimeoutError as OpenAITimeoutError,
    RateLimitError,
    APIStatusError,
)
from PIL import Image

from src.services.ai_providers.base import BaseAIImageProvider, AIProviderType
from src.utils.exceptions import (
    AIServiceError,
    APIRequestError,
    APITimeoutError,
)
from src.utils.logger import setup_logger
from src.utils.retry import async_retry

logger = setup_logger(__name__)

# 默认模型
DEFAULT_MODEL = "gpt-image-1"

# 默认 API 基础 URL
DEFAULT_BASE_URL = "https://api.openai.com/v1"


class OpenAIProvider(BaseAIImageProvider):
    """OpenAI 图片处理提供者.

    使用 DALL-E / GPT-Image 系列模型进行图片编辑。

    Features:
        - 单图编辑
        - 图片生成
        - 背景去除
    """

    provider_type = AIProviderType.OPENAI

    def __init__(
        self,
        api_key: str,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: int = 120,
        **kwargs,
    ) -> None:
        """初始化 OpenAI 提供者.

        Args:
            api_key: OpenAI API 密钥
            model: 模型名称，默认 gpt-image-1
            base_url: API 基础 URL
            timeout: 请求超时时间 (秒)
        """
        super().__init__(api_key, model, **kwargs)
        self._base_url = base_url or DEFAULT_BASE_URL
        self._timeout = timeout
        self._client: Optional[AsyncOpenAI] = None

    @property
    def default_model(self) -> str:
        """默认模型名称."""
        return DEFAULT_MODEL

    @property
    def client(self) -> AsyncOpenAI:
        """获取 OpenAI 异步客户端."""
        if self._client is None:
            self._client = AsyncOpenAI(
                api_key=self._api_key,
                base_url=self._base_url,
                timeout=self._timeout,
                max_retries=0,  # 使用自己的重试机制
            )
        return self._client

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

    async def composite_images(
        self,
        images: list[bytes],
        prompt: str,
    ) -> bytes:
        """合成多张图片.

        OpenAI 不直接支持多图输入，需要先将图片合并。

        Args:
            images: 图片字节数据列表
            prompt: 合成提示词

        Returns:
            合成后的图片字节数据
        """
        if len(images) < 2:
            raise AIServiceError("合成需要至少 2 张图片")

        # 合并图片
        merged = await self._merge_images(images)
        return await self._edit_image(
            image=merged,
            prompt=prompt,
            operation="composite_images",
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
        return await self._edit_image(
            image=image,
            prompt=prompt,
            operation="edit_image",
        )

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
        """使用 OpenAI API 编辑图片."""
        logger.info(f"开始 AI 图片处理: {operation}")

        try:
            image_file = io.BytesIO(image)
            image_file.name = "image.png"

            response = await self.client.images.edit(
                model=self._model,
                image=image_file,
                prompt=prompt,
                n=1,
                size="1024x1024",
                response_format="b64_json",
            )

            if response.data and len(response.data) > 0:
                b64_data = response.data[0].b64_json
                if b64_data:
                    result = base64.b64decode(b64_data)
                    logger.info(f"AI 图片处理完成: {operation}, 输出大小: {len(result)} bytes")
                    return result

            raise AIServiceError(f"AI 返回空结果: {operation}")

        except OpenAITimeoutError as e:
            logger.error(f"AI 请求超时: {operation}")
            raise APITimeoutError(self._timeout) from e

        except APIStatusError as e:
            logger.error(f"AI API 错误: {operation}, status={e.status_code}, message={e.message}")
            raise APIRequestError(e.message, e.status_code) from e

        except APIConnectionError as e:
            logger.error(f"AI 连接错误: {operation}, {e}")
            raise APIRequestError(f"无法连接到 AI 服务: {e}") from e

        except Exception as e:
            logger.exception(f"AI 处理未知错误: {operation}")
            raise AIServiceError(f"AI 处理失败: {e}") from e

    async def _merge_images(self, images: list[bytes]) -> bytes:
        """合并多张图片为一张.

        将图片并排放置。

        Args:
            images: 图片字节数据列表

        Returns:
            合并后的图片字节数据
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._merge_images_sync, images)

    def _merge_images_sync(self, images: list[bytes]) -> bytes:
        """同步合并图片."""
        pil_images = []
        for img_bytes in images:
            img = Image.open(io.BytesIO(img_bytes))
            if img.mode != "RGBA":
                img = img.convert("RGBA")
            pil_images.append(img)

        # 调整为相同高度
        target_height = min(img.height for img in pil_images)
        target_height = min(target_height, 512)

        resized = []
        for img in pil_images:
            ratio = target_height / img.height
            new_size = (int(img.width * ratio), target_height)
            resized.append(img.resize(new_size, Image.Resampling.LANCZOS))

        # 计算总宽度
        gap = 20
        total_width = sum(img.width for img in resized) + gap * (len(resized) - 1)

        # 创建画布
        merged = Image.new("RGBA", (total_width, target_height), (255, 255, 255, 255))

        # 粘贴图片
        x = 0
        for img in resized:
            merged.paste(img, (x, 0), img)
            x += img.width + gap

        # 输出
        output = io.BytesIO()
        merged.save(output, format="PNG")
        return output.getvalue()

    async def health_check(self) -> bool:
        """检查服务是否可用."""
        try:
            response = await self.client.models.list()
            logger.info("OpenAI 服务健康检查通过")
            return True
        except Exception as e:
            logger.warning(f"OpenAI 服务健康检查失败: {e}")
            return False

    async def close(self) -> None:
        """关闭客户端连接."""
        if self._client:
            await self._client.close()
            self._client = None
            logger.debug("OpenAI 客户端已关闭")
