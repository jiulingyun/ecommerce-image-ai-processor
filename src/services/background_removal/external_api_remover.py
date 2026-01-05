"""外部API抠图服务实现.

调用外部抠图API服务，处理返回的蒙版并生成透明背景PNG。
"""

from __future__ import annotations

import asyncio
import base64
import io
from typing import Optional

import httpx
from PIL import Image

from src.services.background_removal.base import (
    BackgroundRemoverType,
    BaseBackgroundRemover,
)
from src.utils.exceptions import AIServiceError, APIRequestError, APITimeoutError
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class ExternalAPIRemover(BaseBackgroundRemover):
    """外部API抠图服务.

    调用外部抠图API，处理返回的蒙版图片（白色=主体，黑色=透明），
    将蒙版应用到原图生成透明背景PNG。

    API 规范:
        - POST /api/remove-background
        - 请求头: X-API-Key 或参数 api_key
        - 输入类型: file(默认)/base64/url
        - 响应: JSON with result_url 或 base64

    Attributes:
        api_url: API 服务地址
        api_key: API 密钥
        timeout: 请求超时时间（秒）
        proxy: 代理设置

    Example:
        >>> remover = ExternalAPIRemover(
        ...     api_url="http://localhost:5000/api/remove-background",
        ...     api_key="your-api-key"
        ... )
        >>> result = await remover.remove_background(image_bytes)
    """

    remover_type = BackgroundRemoverType.EXTERNAL_API

    def __init__(
        self,
        api_url: str,
        api_key: str = "",
        timeout: int = 120,
        proxy: Optional[str] = None,
    ) -> None:
        """初始化外部API抠图服务.

        Args:
            api_url: API 服务地址
            api_key: API 密钥
            timeout: 请求超时时间（秒）
            proxy: 代理设置
        """
        self._api_url = api_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout
        self._proxy = proxy
        self._http_client: Optional[httpx.AsyncClient] = None
        self._http_client_loop: Optional[asyncio.AbstractEventLoop] = None

    @property
    def http_client(self) -> httpx.AsyncClient:
        """获取 HTTP 客户端.

        如果当前事件循环与创建客户端时的不同，会自动重新创建客户端。
        """
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            current_loop = None

        # 如果客户端存在但绑定的事件循环已改变或关闭，需要重新创建
        if self._http_client is not None:
            loop_changed = (
                self._http_client_loop is None
                or self._http_client_loop != current_loop
                or self._http_client_loop.is_closed()
            )
            if loop_changed:
                logger.debug("事件循环已改变，重新创建 HTTP 客户端")
                self._http_client = None
                self._http_client_loop = None

        if self._http_client is None:
            transport = None
            if self._proxy:
                transport = httpx.AsyncHTTPTransport(proxy=self._proxy)
            self._http_client = httpx.AsyncClient(
                timeout=self._timeout,
                transport=transport,
            )
            self._http_client_loop = current_loop
        return self._http_client

    async def remove_background(
        self,
        image: bytes,
        **kwargs,
    ) -> bytes:
        """去除图片背景.

        调用外部API进行抠图，API返回的是蒙版图片（白色=主体，黑色=透明），
        需要将蒙版应用到原图生成透明背景PNG。

        Args:
            image: 输入图片字节数据
            **kwargs: 额外参数

        Returns:
            处理后的透明背景PNG图片字节数据

        Raises:
            APIRequestError: API请求失败
            APITimeoutError: 请求超时
            AIServiceError: 处理失败
        """
        logger.info(f"开始调用外部API抠图服务: {self._api_url}")

        try:
            # 使用 base64 方式发送图片
            image_b64 = base64.b64encode(image).decode("utf-8")
            data_url = f"data:image/png;base64,{image_b64}"

            # 构建表单数据
            form_data = {
                "input_type": "base64",
                "image": data_url,
                "return_base64": "true",  # 请求返回base64结果
            }

            # 添加API密钥
            headers = {}
            if self._api_key:
                headers["X-API-Key"] = self._api_key

            # 发送请求
            response = await self.http_client.post(
                self._api_url,
                data=form_data,
                headers=headers,
            )

            if response.status_code != 200:
                error_msg = f"API请求失败: {response.status_code}"
                try:
                    error_data = response.json()
                    if "error" in error_data:
                        error_msg = error_data["error"]
                except Exception:
                    error_msg = response.text or error_msg
                logger.error(f"外部API抠图失败: {error_msg}")
                raise APIRequestError(error_msg, response.status_code)

            # 解析响应
            result = response.json()
            if not result.get("success", False):
                error_msg = result.get("error", "未知错误")
                raise AIServiceError(f"抠图失败: {error_msg}")

            # 获取蒙版图片
            mask_bytes = await self._get_mask_image(result)

            # 将蒙版应用到原图，生成透明背景PNG
            result_bytes = await self._apply_mask_to_image(image, mask_bytes)

            logger.info(f"外部API抠图完成，输出大小: {len(result_bytes)} bytes")
            return result_bytes

        except httpx.TimeoutException as e:
            logger.error(f"外部API请求超时: {self._timeout}s")
            raise APITimeoutError(self._timeout) from e

        except httpx.ConnectError as e:
            logger.error(f"无法连接到外部API服务: {e}")
            raise APIRequestError(f"无法连接到抠图服务: {e}") from e

        except (APIRequestError, APITimeoutError, AIServiceError):
            raise

        except Exception as e:
            logger.exception(f"外部API抠图未知错误: {e}")
            raise AIServiceError(f"抠图处理失败: {e}") from e

    async def _get_mask_image(self, result: dict) -> bytes:
        """从API响应获取蒙版图片.

        Args:
            result: API响应JSON

        Returns:
            蒙版图片字节数据
        """
        # 优先使用 base64 结果
        if "base64" in result and result["base64"]:
            b64_data = result["base64"]
            # 移除 data URL 前缀（如果有）
            if b64_data.startswith("data:"):
                b64_data = b64_data.split(",", 1)[1]
            return base64.b64decode(b64_data)

        # 否则下载图片
        if "result_url" in result:
            url = result["result_url"]
            # 如果是相对路径，拼接基础URL
            if url.startswith("/"):
                base_url = "/".join(self._api_url.split("/")[:3])
                url = base_url + url

            response = await self.http_client.get(url)
            if response.status_code != 200:
                raise AIServiceError(f"下载蒙版图片失败: {response.status_code}")
            return response.content

        raise AIServiceError("API响应中没有找到蒙版图片")

    async def _apply_mask_to_image(
        self,
        original_image: bytes,
        mask_image: bytes,
    ) -> bytes:
        """将蒙版应用到原图，生成透明背景PNG.

        蒙版规则：白色区域=保留主体，黑色区域=设为透明

        Args:
            original_image: 原始图片字节数据
            mask_image: 蒙版图片字节数据

        Returns:
            透明背景PNG图片字节数据
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._apply_mask_sync,
            original_image,
            mask_image,
        )

    def _apply_mask_sync(
        self,
        original_image: bytes,
        mask_image: bytes,
    ) -> bytes:
        """同步方式应用蒙版（在线程池中执行）.

        Args:
            original_image: 原始图片字节数据
            mask_image: 蒙版图片字节数据

        Returns:
            透明背景PNG图片字节数据
        """
        # 加载原图和蒙版
        original = Image.open(io.BytesIO(original_image))
        mask = Image.open(io.BytesIO(mask_image))

        # 确保原图是RGBA模式
        if original.mode != "RGBA":
            original = original.convert("RGBA")

        # 确保蒙版尺寸与原图一致
        if mask.size != original.size:
            mask = mask.resize(original.size, Image.Resampling.LANCZOS)

        # 将蒙版转为灰度图（L模式）
        if mask.mode != "L":
            mask = mask.convert("L")

        # 分离原图的RGBA通道
        r, g, b, a = original.split()

        # 使用蒙版作为新的alpha通道
        # 白色(255)=不透明，黑色(0)=透明
        result = Image.merge("RGBA", (r, g, b, mask))

        # 输出为PNG字节数据
        output = io.BytesIO()
        result.save(output, format="PNG", optimize=True)
        return output.getvalue()

    async def health_check(self) -> bool:
        """检查服务是否可用.

        Returns:
            服务是否可用
        """
        try:
            # 简单检查API连接
            headers = {}
            if self._api_key:
                headers["X-API-Key"] = self._api_key

            # 尝试发送一个OPTIONS请求或HEAD请求
            response = await self.http_client.options(
                self._api_url,
                headers=headers,
            )
            # 200, 204, 405 都说明服务可达
            if response.status_code in (200, 204, 405):
                logger.info("外部抠图API服务健康检查通过")
                return True

            # 尝试GET请求
            response = await self.http_client.get(
                self._api_url,
                headers=headers,
            )
            if response.status_code in (200, 405):
                logger.info("外部抠图API服务健康检查通过")
                return True

            return False

        except Exception as e:
            logger.warning(f"外部抠图API服务健康检查失败: {e}")
            return False

    async def close(self) -> None:
        """关闭 HTTP 客户端."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
            logger.debug("外部API抠图服务 HTTP 客户端已关闭")
