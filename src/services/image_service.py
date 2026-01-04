"""图片处理服务模块.

提供图片处理的业务逻辑封装，包括背景去除、商品合成等功能。

Features:
    - 背景去除完整流程
    - 商品合成完整流程
    - 图片后期处理
    - 进度回调支持
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Callable, Optional, Tuple

from PIL import Image

from src.models.api_config import APIConfig
from src.models.image_task import ImageTask, TaskStatus
from src.models.process_config import ProcessConfig
from src.services.ai_service import AIService, get_ai_service
from src.utils.constants import (
    DEFAULT_BACKGROUND_COLOR,
    DEFAULT_OUTPUT_QUALITY,
    DEFAULT_OUTPUT_SIZE,
)
from src.utils.exceptions import (
    AIServiceError,
    ImageProcessError,
)
from src.utils.image_utils import (
    bytes_to_image,
    ensure_rgba,
    fit_to_size,
    image_to_bytes,
    load_image,
    save_image,
    validate_image_file,
)
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

# 进度回调类型
ProgressCallback = Callable[[int, str], None]


class ImageService:
    """图片处理服务.

    封装图片处理的完整业务逻辑，包括背景去除、商品合成等功能。

    Attributes:
        ai_service: AI 服务实例

    Example:
        >>> service = ImageService()
        >>> result = await service.remove_background("input.jpg", "output.png")
    """

    def __init__(self, ai_service: Optional[AIService] = None) -> None:
        """初始化图片处理服务.

        Args:
            ai_service: AI 服务实例，如果为 None 则使用全局单例
        """
        self._ai_service = ai_service

    @property
    def ai_service(self) -> AIService:
        """获取 AI 服务实例."""
        if self._ai_service is None:
            self._ai_service = get_ai_service()
        return self._ai_service

    @ai_service.setter
    def ai_service(self, value: AIService) -> None:
        """设置 AI 服务实例."""
        self._ai_service = value

    async def remove_background(
        self,
        input_path: str | Path,
        output_path: Optional[str | Path] = None,
        prompt: Optional[str] = None,
        on_progress: Optional[ProgressCallback] = None,
    ) -> Path:
        """去除图片背景.

        加载图片，调用 AI 服务去除背景，保存透明 PNG。

        Args:
            input_path: 输入图片路径
            output_path: 输出图片路径，如果为 None 则自动生成
            prompt: 可选的提示词
            on_progress: 进度回调函数 (progress: int, message: str)

        Returns:
            输出文件路径

        Raises:
            ImageNotFoundError: 输入文件不存在
            UnsupportedImageFormatError: 不支持的图片格式
            AIServiceError: AI 处理失败
            ImageProcessError: 图片处理失败
        """
        input_path = Path(input_path)
        logger.info(f"开始背景去除: {input_path}")

        # 报告进度
        def report_progress(progress: int, message: str) -> None:
            if on_progress:
                on_progress(progress, message)
            logger.debug(f"进度 {progress}%: {message}")

        try:
            # Step 1: 验证输入文件 (10%)
            report_progress(10, "验证输入文件")
            validate_image_file(input_path)

            # Step 2: 加载图片 (20%)
            report_progress(20, "加载图片")
            image = await asyncio.get_event_loop().run_in_executor(
                None, load_image, input_path
            )

            # 确保是 RGBA 模式
            image = ensure_rgba(image)

            # Step 3: 转换为字节数据 (30%)
            report_progress(30, "准备处理数据")
            image_bytes = image_to_bytes(image, format="PNG")

            # Step 4: 调用 AI 服务 (30% -> 80%)
            report_progress(40, "AI 处理中...")
            result_bytes = await self.ai_service.remove_background(
                image_bytes, prompt=prompt
            )
            report_progress(80, "AI 处理完成")

            # Step 5: 保存结果 (90%)
            report_progress(90, "保存结果")
            output_path = self._get_output_path(input_path, output_path, "_nobg.png")
            result_image = bytes_to_image(result_bytes)

            await asyncio.get_event_loop().run_in_executor(
                None, save_image, result_image, output_path, DEFAULT_OUTPUT_QUALITY
            )

            # 完成 (100%)
            report_progress(100, "完成")
            logger.info(f"背景去除完成: {output_path}")

            return output_path

        except (AIServiceError, ImageProcessError):
            # 让这些异常直接传播
            raise
        except Exception as e:
            logger.exception(f"背景去除失败: {input_path}")
            raise ImageProcessError(f"背景去除失败: {e}") from e

    async def composite_product(
        self,
        background_path: str | Path,
        product_path: str | Path,
        output_path: Optional[str | Path] = None,
        prompt: Optional[str] = None,
        position_hint: Optional[str] = None,
        on_progress: Optional[ProgressCallback] = None,
    ) -> Path:
        """合成商品到背景图.

        加载背景和商品图，调用 AI 服务合成。

        Args:
            background_path: 背景图路径
            product_path: 商品图路径
            output_path: 输出图片路径
            prompt: 可选的合成提示词
            position_hint: 位置提示
            on_progress: 进度回调函数

        Returns:
            输出文件路径

        Raises:
            ImageNotFoundError: 输入文件不存在
            AIServiceError: AI 处理失败
            ImageProcessError: 图片处理失败
        """
        background_path = Path(background_path)
        product_path = Path(product_path)
        logger.info(f"开始商品合成: {background_path} + {product_path}")

        def report_progress(progress: int, message: str) -> None:
            if on_progress:
                on_progress(progress, message)
            logger.debug(f"进度 {progress}%: {message}")

        try:
            # Step 1: 验证文件 (10%)
            report_progress(10, "验证输入文件")
            validate_image_file(background_path)
            validate_image_file(product_path)

            # Step 2: 加载图片 (20%)
            report_progress(20, "加载图片")
            loop = asyncio.get_event_loop()
            bg_task = loop.run_in_executor(None, load_image, background_path)
            prod_task = loop.run_in_executor(None, load_image, product_path)
            bg_image, prod_image = await asyncio.gather(bg_task, prod_task)

            # Step 3: 转换格式 (30%)
            report_progress(30, "准备处理数据")
            bg_bytes = image_to_bytes(ensure_rgba(bg_image), format="PNG")
            prod_bytes = image_to_bytes(ensure_rgba(prod_image), format="PNG")

            # Step 4: AI 合成 (40% -> 80%)
            report_progress(40, "AI 合成中...")
            result_bytes = await self.ai_service.composite_product(
                background=bg_bytes,
                product=prod_bytes,
                prompt=prompt,
                position_hint=position_hint,
            )
            report_progress(80, "AI 合成完成")

            # Step 5: 保存结果 (90%)
            report_progress(90, "保存结果")
            output_path = self._get_output_path(
                background_path, output_path, "_composite.png"
            )
            result_image = bytes_to_image(result_bytes)

            await loop.run_in_executor(
                None, save_image, result_image, output_path, DEFAULT_OUTPUT_QUALITY
            )

            # 完成 (100%)
            report_progress(100, "完成")
            logger.info(f"商品合成完成: {output_path}")

            return output_path

        except AIServiceError:
            raise
        except Exception as e:
            logger.exception(f"商品合成失败: {background_path} + {product_path}")
            raise ImageProcessError(f"商品合成失败: {e}") from e

    async def process_task(
        self,
        task: ImageTask,
        config: Optional[ProcessConfig] = None,
        on_progress: Optional[ProgressCallback] = None,
    ) -> ImageTask:
        """处理完整的图片任务.

        执行完整的处理流程：背景去除 -> 商品合成 -> 后期处理。

        Args:
            task: 图片任务
            config: 处理配置
            on_progress: 进度回调

        Returns:
            更新后的任务对象
        """
        config = config or task.config or ProcessConfig()

        logger.info(f"开始处理任务: {task.id}")
        task.mark_processing()

        def report_progress(progress: int, message: str) -> None:
            task.progress = progress
            if on_progress:
                on_progress(progress, message)

        try:
            # Step 1: 去除商品背景 (0-30%)
            report_progress(5, "去除商品背景")
            product_nobg = await self._remove_product_background(
                task.product_path,
                lambda p, m: report_progress(int(5 + p * 0.25), m),
            )

            # Step 2: 合成商品到场景 (30-70%)
            report_progress(35, "合成商品到场景")
            composite_result = await self._composite_to_scene(
                task.background_path,
                product_nobg,
                lambda p, m: report_progress(int(35 + p * 0.35), m),
            )

            # Step 3: 后期处理 (70-90%)
            report_progress(75, "后期处理")
            final_result = await self._apply_post_processing(
                composite_result,
                config,
                lambda p, m: report_progress(int(75 + p * 0.15), m),
            )

            # Step 4: 保存输出 (90-100%)
            report_progress(95, "保存输出")
            output_path = await self._save_final_output(
                final_result,
                task,
                config,
            )

            # 完成
            task.mark_completed(str(output_path))
            report_progress(100, "完成")
            logger.info(f"任务完成: {task.id}")

            return task

        except Exception as e:
            logger.exception(f"任务处理失败: {task.id}")
            task.mark_failed(str(e))
            return task

    async def _remove_product_background(
        self,
        product_path: str,
        on_progress: Optional[ProgressCallback] = None,
    ) -> bytes:
        """去除商品背景（内部方法）."""
        image = load_image(product_path)
        image = ensure_rgba(image)
        image_bytes = image_to_bytes(image, format="PNG")

        if on_progress:
            on_progress(50, "调用 AI 服务")

        result = await self.ai_service.remove_background(image_bytes)

        if on_progress:
            on_progress(100, "背景去除完成")

        return result

    async def _composite_to_scene(
        self,
        background_path: str,
        product_bytes: bytes,
        on_progress: Optional[ProgressCallback] = None,
    ) -> bytes:
        """合成商品到场景（内部方法）."""
        bg_image = load_image(background_path)
        bg_image = ensure_rgba(bg_image)
        bg_bytes = image_to_bytes(bg_image, format="PNG")

        if on_progress:
            on_progress(50, "调用 AI 服务")

        result = await self.ai_service.composite_product(
            background=bg_bytes,
            product=product_bytes,
        )

        if on_progress:
            on_progress(100, "合成完成")

        return result

    async def _apply_post_processing(
        self,
        image_bytes: bytes,
        config: ProcessConfig,
        on_progress: Optional[ProgressCallback] = None,
    ) -> Image.Image:
        """应用后期处理（内部方法）."""
        image = bytes_to_image(image_bytes)
        loop = asyncio.get_event_loop()

        # 添加背景色
        if on_progress:
            on_progress(20, "添加背景")
        image = await loop.run_in_executor(
            None, self._add_background_color, image, config.background.color
        )

        # 添加边框
        if config.border.enabled:
            if on_progress:
                on_progress(40, "添加边框")
            image = await loop.run_in_executor(
                None,
                self._add_border,
                image,
                config.border.width,
                config.border.color,
            )

        # 添加文字
        if config.text.enabled and config.text.content:
            if on_progress:
                on_progress(60, "添加文字")
            image = await loop.run_in_executor(
                None,
                self._add_text,
                image,
                config.text.content,
                config.text.position,
                config.text.font_size,
                config.text.color,
            )

        # 调整尺寸
        if on_progress:
            on_progress(80, "调整尺寸")
        image = await loop.run_in_executor(
            None, fit_to_size, image, config.output.size, config.background.color
        )

        if on_progress:
            on_progress(100, "后期处理完成")

        return image

    async def _save_final_output(
        self,
        image: Image.Image,
        task: ImageTask,
        config: ProcessConfig,
    ) -> Path:
        """保存最终输出（内部方法）."""
        output_path = self._get_output_path(
            Path(task.background_path),
            task.output_path,
            "_final.jpg",
        )

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            save_image,
            image,
            output_path,
            config.output.quality,
        )

        return output_path

    def _get_output_path(
        self,
        input_path: Path,
        output_path: Optional[str | Path],
        suffix: str,
    ) -> Path:
        """获取输出路径."""
        if output_path:
            return Path(output_path)

        # 自动生成输出路径
        stem = input_path.stem
        return input_path.parent / f"{stem}{suffix}"

    def _add_background_color(
        self,
        image: Image.Image,
        color: Tuple[int, int, int],
    ) -> Image.Image:
        """添加背景色（同步方法）."""
        if image.mode != "RGBA":
            return image

        # 创建背景
        background = Image.new("RGB", image.size, color)
        # 合成
        background.paste(image, mask=image.split()[3])
        return background

    def _add_border(
        self,
        image: Image.Image,
        width: int,
        color: Tuple[int, int, int],
    ) -> Image.Image:
        """添加边框（同步方法）."""
        from PIL import ImageDraw

        # 确保是 RGB 模式
        if image.mode != "RGB":
            image = image.convert("RGB")

        draw = ImageDraw.Draw(image)
        w, h = image.size

        # 绘制边框
        for i in range(width):
            draw.rectangle(
                [i, i, w - 1 - i, h - 1 - i],
                outline=color,
            )

        return image

    def _add_text(
        self,
        image: Image.Image,
        text: str,
        position: Tuple[int, int],
        font_size: int,
        color: Tuple[int, int, int],
    ) -> Image.Image:
        """添加文字（同步方法）."""
        from PIL import ImageDraw, ImageFont

        if image.mode != "RGB":
            image = image.convert("RGB")

        draw = ImageDraw.Draw(image)

        # 尝试加载字体
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except OSError:
            # 使用默认字体
            font = ImageFont.load_default()

        draw.text(position, text, font=font, fill=color)
        return image


# 单例实例
_image_service_instance: Optional[ImageService] = None


def get_image_service(ai_service: Optional[AIService] = None) -> ImageService:
    """获取图片处理服务单例.

    Args:
        ai_service: AI 服务实例

    Returns:
        ImageService 实例
    """
    global _image_service_instance

    if _image_service_instance is None:
        _image_service_instance = ImageService(ai_service)
    elif ai_service is not None:
        _image_service_instance.ai_service = ai_service

    return _image_service_instance


def reset_image_service() -> None:
    """重置图片处理服务单例."""
    global _image_service_instance
    _image_service_instance = None
