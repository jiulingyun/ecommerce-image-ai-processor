"""阿里云百炼 DashScope AI 图片处理提供者.

使用 DashScope SDK 实现图片编辑功能。
"""

from __future__ import annotations

import asyncio
import base64
import mimetypes
from typing import Optional

import httpx

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
DEFAULT_MODEL = "qwen-image-edit-plus"

# API 基础 URL
DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/api/v1"


class DashScopeProvider(BaseAIImageProvider):
    """阿里云百炼 DashScope 图片处理提供者.

    使用 qwen-image-edit 系列模型进行图片编辑。

    Features:
        - 单图编辑
        - 多图融合 (最多 3 张)
        - 背景去除
        - 商品合成
    """

    provider_type = AIProviderType.DASHSCOPE

    def __init__(
        self,
        api_key: str,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: int = 120,
        **kwargs,
    ) -> None:
        """初始化 DashScope 提供者.

        Args:
            api_key: 百炼 API 密钥
            model: 模型名称，默认 qwen-image-edit-plus
            base_url: API 基础 URL，默认北京地域
            timeout: 请求超时时间 (秒)
        """
        super().__init__(api_key, model, **kwargs)
        self._base_url = base_url or DASHSCOPE_BASE_URL
        self._timeout = timeout
        self._http_client: Optional[httpx.AsyncClient] = None

        # 配置 dashscope SDK
        try:
            import dashscope
            dashscope.base_http_api_url = self._base_url
        except ImportError:
            logger.warning("dashscope SDK 未安装，将使用 HTTP 方式调用")

    @property
    def default_model(self) -> str:
        """默认模型名称."""
        return DEFAULT_MODEL

    @property
    def http_client(self) -> httpx.AsyncClient:
        """获取 HTTP 客户端."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=self._timeout)
        return self._http_client

    def _image_to_base64_data_url(self, image: bytes, format: str = "png") -> str:
        """将图片转换为 base64 data URL 格式."""
        b64 = base64.b64encode(image).decode("utf-8")
        return f"data:image/{format};base64,{b64}"

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
        default_prompt = "去除图片背景，保留主体，背景设为透明或纯白色，保持主体边缘清晰。"
        return await self._call_api(
            images=[image],
            prompt=prompt or default_prompt,
            operation="remove_background",
        )

    async def composite_images(
        self,
        images: list[bytes],
        prompt: str,
    ) -> bytes:
        """合成多张图片.

        使用多图融合功能，最多支持 3 张图片。

        Args:
            images: 图片字节数据列表 (1-3 张)
            prompt: 合成提示词，需使用 "图1"、"图2" 等指代

        Returns:
            合成后的图片字节数据
        """
        if len(images) > 3:
            raise AIServiceError("DashScope 最多支持 3 张图片融合")

        return await self._call_api(
            images=images,
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
        return await self._call_api(
            images=[image],
            prompt=prompt,
            operation="edit_image",
        )

    @async_retry(
        max_retries=3,
        delay=1.0,
        backoff=2.0,
        exceptions=(httpx.ConnectError, httpx.TimeoutException),
    )
    async def _call_api(
        self,
        images: list[bytes],
        prompt: str,
        operation: str,
    ) -> bytes:
        """调用 DashScope 图像编辑 API.

        优先使用 SDK，如不可用则使用 HTTP 方式。

        Args:
            images: 图片字节数据列表
            prompt: 编辑提示词
            operation: 操作名称

        Returns:
            处理后的图片字节数据
        """
        logger.info(f"开始 AI 图片处理: {operation}, 图片数: {len(images)}")

        # 尝试使用 SDK
        try:
            return await self._call_api_sdk(images, prompt, operation)
        except ImportError:
            logger.debug("SDK 不可用，使用 HTTP 方式")
            return await self._call_api_http(images, prompt, operation)

    async def _call_api_sdk(
        self,
        images: list[bytes],
        prompt: str,
        operation: str,
    ) -> bytes:
        """使用 DashScope SDK 调用 API."""
        from dashscope import MultiModalConversation

        # 构建 content
        content = []
        for img in images:
            data_url = self._image_to_base64_data_url(img)
            content.append({"image": data_url})
        content.append({"text": prompt})

        messages = [{"role": "user", "content": content}]

        # 在线程池中执行同步 SDK 调用
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: MultiModalConversation.call(
                api_key=self._api_key,
                model=self._model,
                messages=messages,
                stream=False,
                n=1,
                watermark=False,
                negative_prompt="低质量、模糊、变形",
                prompt_extend=True,
            ),
        )

        if response.status_code != 200:
            error_msg = getattr(response, "message", str(response))
            logger.error(f"AI API 错误: {operation}, code={response.status_code}, message={error_msg}")
            raise APIRequestError(error_msg, response.status_code)

        # 获取输出图片 URL
        try:
            image_url = response.output.choices[0].message.content[0]["image"]
        except (AttributeError, IndexError, KeyError) as e:
            raise AIServiceError(f"AI 返回格式异常: {operation}") from e

        # 下载图片
        result = await self._download_image(image_url)
        logger.info(f"AI 图片处理完成: {operation}, 输出大小: {len(result)} bytes")
        return result

    async def _call_api_http(
        self,
        images: list[bytes],
        prompt: str,
        operation: str,
    ) -> bytes:
        """使用 HTTP 方式调用 API."""
        try:
            # 构建 content 数组
            content = []
            for img in images:
                data_url = self._image_to_base64_data_url(img)
                content.append({"image": data_url})
            content.append({"text": prompt})

            # 构建请求体
            payload = {
                "model": self._model,
                "input": {
                    "messages": [
                        {
                            "role": "user",
                            "content": content,
                        }
                    ]
                },
                "parameters": {
                    "n": 1,
                    "negative_prompt": "低质量、模糊、变形",
                    "prompt_extend": True,
                    "watermark": False,
                },
            }

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key}",
            }

            url = f"{self._base_url}/services/aigc/multimodal-generation/generation"

            response = await self.http_client.post(url, json=payload, headers=headers)

            if response.status_code != 200:
                error_data = response.json() if response.text else {}
                error_msg = error_data.get("message", response.text)
                logger.error(f"AI API 错误: {operation}, status={response.status_code}, message={error_msg}")
                raise APIRequestError(error_msg, response.status_code)

            data = response.json()

            # 解析响应
            choices = data.get("output", {}).get("choices", [])
            if choices and len(choices) > 0:
                message = choices[0].get("message", {})
                content_list = message.get("content", [])
                for item in content_list:
                    if "image" in item:
                        image_url = item["image"]
                        result = await self._download_image(image_url)
                        logger.info(f"AI 图片处理完成: {operation}, 输出大小: {len(result)} bytes")
                        return result

            raise AIServiceError(f"AI 返回空结果: {operation}")

        except httpx.TimeoutException as e:
            logger.error(f"AI 请求超时: {operation}")
            raise APITimeoutError(self._timeout) from e

        except httpx.ConnectError as e:
            logger.error(f"AI 连接错误: {operation}, {e}")
            raise APIRequestError(f"无法连接到 AI 服务: {e}") from e

        except (APIRequestError, APITimeoutError):
            raise

        except Exception as e:
            logger.exception(f"AI 处理未知错误: {operation}")
            raise AIServiceError(f"AI 处理失败: {e}") from e

    async def _download_image(self, url: str) -> bytes:
        """下载图片."""
        response = await self.http_client.get(url)
        if response.status_code != 200:
            raise AIServiceError(f"下载图片失败: {response.status_code}")
        return response.content

    async def health_check(self) -> bool:
        """检查服务是否可用."""
        try:
            # 简单检查 API 连接
            headers = {"Authorization": f"Bearer {self._api_key}"}
            response = await self.http_client.get(
                f"{self._base_url}/models",
                headers=headers,
            )
            if response.status_code in (200, 404):  # 404 也说明服务可达
                logger.info("DashScope 服务健康检查通过")
                return True
            return False
        except Exception as e:
            logger.warning(f"DashScope 服务健康检查失败: {e}")
            return False

    async def close(self) -> None:
        """关闭 HTTP 客户端."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
            logger.debug("DashScope HTTP 客户端已关闭")
