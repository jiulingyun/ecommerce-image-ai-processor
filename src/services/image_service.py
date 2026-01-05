"""图片处理服务模块.

提供图片处理的业务逻辑封装，包括背景去除、商品合成等功能。

Features:
    - 背景去除完整流程
    - 商品合成完整流程
    - 图片后期处理
    - 纯色背景添加
    - 边框添加（多种样式）
    - 进度回调支持
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Callable, Optional, Tuple, Union

from PIL import Image

from src.models.api_config import APIConfig
from src.models.image_task import ImageTask, TaskStatus
from src.models.process_config import (
    BackgroundConfig,
    BorderConfig,
    BorderStyle,
    OutputConfig,
    OutputFormat,
    PresetColor,
    ProcessConfig,
    QualityPreset,
    ResizeMode,
    TextConfig,
    TextPosition,
    TextAlign,
)
from src.services.ai_service import AIService, get_ai_service
from src.services.background_removal import (
    BackgroundRemoverType,
    BaseBackgroundRemover,
    get_background_remover,
)
from src.utils.constants import (
    DEFAULT_BACKGROUND_COLOR,
    DEFAULT_BORDER_COLOR,
    DEFAULT_BORDER_WIDTH,
    DEFAULT_OUTPUT_QUALITY,
    DEFAULT_OUTPUT_SIZE,
    PREVIEW_SIZE,
)
from src.utils.exceptions import (
    AIServiceError,
    ImageProcessError,
)
from src.utils.image_utils import (
    add_border,
    add_border_expand,
    add_solid_background,
    add_text,
    apply_background_with_padding,
    bytes_to_image,
    calculate_text_position,
    composite_with_background,
    create_background_preview,
    create_border_preview,
    create_text_preview,
    create_thumbnail,
    ensure_rgba,
    estimate_file_size,
    export_image,
    fit_to_size,
    format_file_size,
    get_available_fonts,
    get_text_size,
    image_to_bytes,
    load_image,
    resize_with_mode,
    save_image,
    validate_image_file,
)
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

# 进度回调类型
ProgressCallback = Callable[[int, str], None]


class ImageService:
    """图片处理服务.

    封装图片处理的完整业务逻辑，包括背景去除、商品合成、背景添加等功能。

    Attributes:
        ai_service: AI 服务实例

    Example:
        >>> service = ImageService()
        >>> result = await service.remove_background("input.jpg", "output.png")
        >>>
        >>> # 添加纯色背景
        >>> result = await service.add_background(
        ...     "transparent.png",
        ...     "output.jpg",
        ...     color=(255, 255, 255)
        ... )
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

        执行新的处理流程：抠图 -> 后期处理（背景/边框/文字）-> AI合成 -> 保存

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
            # Step 1: 抠图 (0-25%)
            report_progress(5, "抠图处理中")
            product_nobg = await self._remove_product_background(
                task.product_path,
                config,
                lambda p, m: report_progress(int(5 + p * 0.20), m),
            )

            # Step 2: 后期处理 - 对抠图结果添加背景/边框/文字 (25-50%)
            report_progress(30, "后期处理")
            processed_product = await self._apply_post_processing(
                product_nobg,
                config,
                lambda p, m: report_progress(int(30 + p * 0.20), m),
            )

            # Step 3: AI合成 - 将处理后的商品合成到场景 (50-90%)
            report_progress(55, "AI合成商品到场景")
            composite_result = await self._composite_to_scene(
                task.background_path,
                processed_product,
                lambda p, m: report_progress(int(55 + p * 0.35), m),
                config=config,
            )

            # Step 4: 保存输出 (90-100%)
            report_progress(95, "保存输出")
            # composite_result 是 bytes，需要转换为 Image
            final_image = bytes_to_image(composite_result)
            output_path = await self._save_final_output(
                final_image,
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
        config: ProcessConfig,
        on_progress: Optional[ProgressCallback] = None,
    ) -> bytes:
        """去除商品背景（内部方法）.
        
        使用配置中指定的抠图服务（外部API或AI）进行背景去除。
        
        Args:
            product_path: 商品图片路径
            config: 处理配置
            on_progress: 进度回调
            
        Returns:
            透明背景的PNG图片字节数据
        """
        image = load_image(product_path)
        image = ensure_rgba(image)
        image_bytes = image_to_bytes(image, format="PNG")

        # 检查是否启用抠图
        if not config.background_removal.enabled:
            logger.info("抠图已禁用，跳过")
            if on_progress:
                on_progress(100, "跳过抠图")
            return image_bytes

        if on_progress:
            on_progress(30, "初始化抠图服务")

        # 获取抠图服务
        bg_removal_config = config.background_removal
        if bg_removal_config.provider.value == "external_api":
            remover = get_background_remover(
                remover_type=BackgroundRemoverType.EXTERNAL_API,
                api_url=bg_removal_config.api_url,
                api_key=bg_removal_config.api_key,
                timeout=bg_removal_config.timeout,
                proxy=bg_removal_config.proxy,
            )
            if on_progress:
                on_progress(50, "调用外部抠图服务")
        else:
            remover = get_background_remover(
                remover_type=BackgroundRemoverType.AI,
            )
            if on_progress:
                on_progress(50, "调用AI抠图服务")

        result = await remover.remove_background(image_bytes)

        if on_progress:
            on_progress(100, "抠图完成")

        return result

    async def _composite_to_scene(
        self,
        background_path: str,
        product: Image.Image | bytes,
        on_progress: Optional[ProgressCallback] = None,
        config: Optional[ProcessConfig] = None,
    ) -> bytes:
        """合成商品到场景（内部方法）.
        
        Args:
            background_path: 背景图片路径
            product: 商品图片（PIL Image 或 bytes）
            on_progress: 进度回调
            config: 处理配置
            
        Returns:
            合成后的图片字节数据
        """
        bg_image = load_image(background_path)
        bg_image = ensure_rgba(bg_image)
        bg_bytes = image_to_bytes(bg_image, format="PNG")

        # 将 product 转换为 bytes
        if isinstance(product, Image.Image):
            product_bytes = image_to_bytes(product, format="PNG")
        else:
            product_bytes = product

        if on_progress:
            on_progress(50, "调用 AI 服务")

        result = await self.ai_service.composite_product(
            background=bg_bytes,
            product=product_bytes,
            config=config,
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
            # 计算文字位置
            text_position = config.text.get_effective_position(image.size)
            image = await loop.run_in_executor(
                None,
                self._add_text,
                image,
                config.text.content,
                text_position,
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

    # ==========================================
    # 背景添加功能
    # ==========================================

    async def add_background(
        self,
        input_path: Union[str, Path],
        output_path: Optional[Union[str, Path]] = None,
        config: Optional[BackgroundConfig] = None,
        color: Optional[Tuple[int, int, int]] = None,
        on_progress: Optional[ProgressCallback] = None,
    ) -> Path:
        """为图片添加纯色背景.

        将透明背景的图片处理为纯色背景。支持通过配置对象或直接指定 RGB 颜色。

        Args:
            input_path: 输入图片路径
            output_path: 输出图片路径，如果为 None 则自动生成
            config: 背景配置对象
            color: 直接指定 RGB 颜色（优先级低于 config）
            on_progress: 进度回调函数

        Returns:
            输出文件路径

        Raises:
            ImageNotFoundError: 输入文件不存在
            ImageProcessError: 图片处理失败

        Example:
            >>> service = ImageService()
            >>> # 使用配置对象
            >>> config = BackgroundConfig.from_hex("#F5F5F5")
            >>> result = await service.add_background("input.png", config=config)
            >>>
            >>> # 直接指定颜色
            >>> result = await service.add_background("input.png", color=(255, 255, 255))
        """
        input_path = Path(input_path)
        logger.info(f"开始添加背景: {input_path}")

        def report_progress(progress: int, message: str) -> None:
            if on_progress:
                on_progress(progress, message)
            logger.debug(f"进度 {progress}%: {message}")

        try:
            # Step 1: 确定背景颜色 (5%)
            report_progress(5, "准备背景配置")
            if config is not None:
                if not config.enabled:
                    # 背景添加未启用，直接复制原文件
                    output_path = self._get_output_path(input_path, output_path, "_bg.png")
                    import shutil
                    shutil.copy(input_path, output_path)
                    report_progress(100, "完成（背景添加未启用）")
                    return output_path
                if config.is_transparent():
                    # 透明背景，不处理
                    output_path = self._get_output_path(input_path, output_path, "_bg.png")
                    import shutil
                    shutil.copy(input_path, output_path)
                    report_progress(100, "完成（保持透明背景）")
                    return output_path
                bg_color = config.get_effective_color()
            elif color is not None:
                bg_color = color
            else:
                bg_color = DEFAULT_BACKGROUND_COLOR

            # Step 2: 验证输入文件 (10%)
            report_progress(10, "验证输入文件")
            validate_image_file(input_path)

            # Step 3: 加载图片 (30%)
            report_progress(30, "加载图片")
            loop = asyncio.get_event_loop()
            image = await loop.run_in_executor(None, load_image, input_path)
            image = ensure_rgba(image)

            # Step 4: 添加背景 (60%)
            report_progress(60, "添加背景")
            result_image = await loop.run_in_executor(
                None, add_solid_background, image, bg_color
            )

            # Step 5: 保存结果 (90%)
            report_progress(90, "保存结果")
            output_path = self._get_output_path(input_path, output_path, "_bg.jpg")
            await loop.run_in_executor(
                None, save_image, result_image, output_path, DEFAULT_OUTPUT_QUALITY
            )

            # 完成 (100%)
            report_progress(100, "完成")
            logger.info(f"背景添加完成: {output_path}")

            return output_path

        except Exception as e:
            logger.exception(f"背景添加失败: {input_path}")
            raise ImageProcessError(f"背景添加失败: {e}") from e

    async def add_background_with_resize(
        self,
        input_path: Union[str, Path],
        output_path: Optional[Union[str, Path]] = None,
        config: Optional[BackgroundConfig] = None,
        color: Optional[Tuple[int, int, int]] = None,
        target_size: Tuple[int, int] = DEFAULT_OUTPUT_SIZE,
        on_progress: Optional[ProgressCallback] = None,
    ) -> Path:
        """添加背景并调整尺寸.

        将图片适配到目标尺寸，用背景色填充空白区域。

        Args:
            input_path: 输入图片路径
            output_path: 输出图片路径
            config: 背景配置对象
            color: RGB 颜色
            target_size: 目标尺寸
            on_progress: 进度回调

        Returns:
            输出文件路径
        """
        input_path = Path(input_path)
        logger.info(f"开始添加背景并调整尺寸: {input_path}")

        def report_progress(progress: int, message: str) -> None:
            if on_progress:
                on_progress(progress, message)

        try:
            # 确定背景颜色
            if config is not None:
                bg_color = config.get_effective_color()
            elif color is not None:
                bg_color = color
            else:
                bg_color = DEFAULT_BACKGROUND_COLOR

            report_progress(10, "验证输入文件")
            validate_image_file(input_path)

            report_progress(30, "加载图片")
            loop = asyncio.get_event_loop()
            image = await loop.run_in_executor(None, load_image, input_path)

            report_progress(60, "调整尺寸并添加背景")
            result_image = await loop.run_in_executor(
                None, fit_to_size, image, target_size, bg_color
            )

            report_progress(90, "保存结果")
            output_path = self._get_output_path(input_path, output_path, "_bg.jpg")
            await loop.run_in_executor(
                None, save_image, result_image, output_path, DEFAULT_OUTPUT_QUALITY
            )

            report_progress(100, "完成")
            logger.info(f"背景添加完成: {output_path}")

            return output_path

        except Exception as e:
            logger.exception(f"背景添加失败: {input_path}")
            raise ImageProcessError(f"背景添加失败: {e}") from e

    def generate_background_preview(
        self,
        color: Optional[Tuple[int, int, int]] = None,
        config: Optional[BackgroundConfig] = None,
        size: Tuple[int, int] = PREVIEW_SIZE,
        sample_image: Optional[Union[str, Path, Image.Image]] = None,
    ) -> Image.Image:
        """生成背景颜色预览图.

        用于 UI 中显示选中的背景颜色效果。

        Args:
            color: RGB 颜色
            config: 背景配置对象
            size: 预览图尺寸
            sample_image: 可选的样本图片，用于显示背景效果

        Returns:
            预览图片

        Example:
            >>> service = ImageService()
            >>> preview = service.generate_background_preview(color=(245, 245, 245))
            >>> preview.show()
        """
        # 确定颜色
        if config is not None:
            if config.is_transparent():
                # 透明背景显示棋盘格
                return create_background_preview(
                    (200, 200, 200), size=size, with_checkerboard=True
                )
            bg_color = config.get_effective_color()
        elif color is not None:
            bg_color = color
        else:
            bg_color = DEFAULT_BACKGROUND_COLOR

        # 如果有样本图片，生成合成效果预览
        if sample_image is not None:
            if isinstance(sample_image, (str, Path)):
                sample_image = load_image(sample_image)

            # 缩小样本图片
            sample_thumb = create_thumbnail(sample_image, size)

            # 合成到背景
            return composite_with_background(
                sample_thumb, bg_color, target_size=size, position="center"
            )

        # 纯色预览
        return create_background_preview(bg_color, size=size)

    def get_preset_colors(self) -> list[dict]:
        """获取预设背景颜色列表.

        供 UI 颜色选择器使用。

        Returns:
            预设颜色信息列表，每项包含 name, preset, rgb, hex 字段

        Example:
            >>> service = ImageService()
            >>> colors = service.get_preset_colors()
            >>> for c in colors:
            ...     print(f"{c['name']}: {c['hex']}")
        """
        return BackgroundConfig.get_preset_colors()

    # ==========================================
    # 边框添加功能
    # ==========================================

    async def add_image_border(
        self,
        input_path: Union[str, Path],
        output_path: Optional[Union[str, Path]] = None,
        config: Optional[BorderConfig] = None,
        width: Optional[int] = None,
        color: Optional[Tuple[int, int, int]] = None,
        style: Optional[str] = None,
        expand: bool = False,
        on_progress: Optional[ProgressCallback] = None,
    ) -> Path:
        """为图片添加边框.

        支持多种边框样式，可通过配置对象或直接指定参数。

        Args:
            input_path: 输入图片路径
            output_path: 输出图片路径，如果为 None 则自动生成
            config: 边框配置对象
            width: 边框宽度 (1-20 像素)，优先级低于 config
            color: 边框颜色 RGB，优先级低于 config
            style: 边框样式，优先级低于 config
            expand: 是否扩展图片尺寸以容纳边框
            on_progress: 进度回调函数

        Returns:
            输出文件路径

        Raises:
            ImageNotFoundError: 输入文件不存在
            ImageProcessError: 图片处理失败

        Example:
            >>> service = ImageService()
            >>> # 使用配置对象
            >>> config = BorderConfig.from_hex("#000000", width=5, style=BorderStyle.SOLID)
            >>> result = await service.add_image_border("input.jpg", config=config)
            >>>
            >>> # 直接指定参数
            >>> result = await service.add_image_border(
            ...     "input.jpg",
            ...     width=3,
            ...     color=(255, 0, 0),
            ...     style="dashed"
            ... )
        """
        input_path = Path(input_path)
        logger.info(f"开始添加边框: {input_path}")

        def report_progress(progress: int, message: str) -> None:
            if on_progress:
                on_progress(progress, message)
            logger.debug(f"进度 {progress}%: {message}")

        try:
            # Step 1: 确定边框参数 (5%)
            report_progress(5, "准备边框配置")
            if config is not None:
                if not config.enabled:
                    # 边框未启用，直接复制原文件
                    output_path = self._get_output_path(input_path, output_path, "_border.jpg")
                    import shutil
                    shutil.copy(input_path, output_path)
                    report_progress(100, "完成（边框未启用）")
                    return output_path
                border_width = config.width
                border_color = config.get_effective_color()
                border_style = config.style.value
            else:
                border_width = width if width is not None else DEFAULT_BORDER_WIDTH
                border_color = color if color is not None else DEFAULT_BORDER_COLOR
                border_style = style if style is not None else "solid"

            # Step 2: 验证输入文件 (10%)
            report_progress(10, "验证输入文件")
            validate_image_file(input_path)

            # Step 3: 加载图片 (30%)
            report_progress(30, "加载图片")
            loop = asyncio.get_event_loop()
            image = await loop.run_in_executor(None, load_image, input_path)

            # Step 4: 添加边框 (60%)
            report_progress(60, "添加边框")
            if expand:
                result_image = await loop.run_in_executor(
                    None, add_border_expand, image, border_width, border_color, border_style
                )
            else:
                result_image = await loop.run_in_executor(
                    None, add_border, image, border_width, border_color, border_style
                )

            # Step 5: 保存结果 (90%)
            report_progress(90, "保存结果")
            output_path = self._get_output_path(input_path, output_path, "_border.jpg")
            await loop.run_in_executor(
                None, save_image, result_image, output_path, DEFAULT_OUTPUT_QUALITY
            )

            # 完成 (100%)
            report_progress(100, "完成")
            logger.info(f"边框添加完成: {output_path}")

            return output_path

        except Exception as e:
            logger.exception(f"边框添加失败: {input_path}")
            raise ImageProcessError(f"边框添加失败: {e}") from e

    def generate_border_preview(
        self,
        width: int = DEFAULT_BORDER_WIDTH,
        color: Optional[Tuple[int, int, int]] = None,
        config: Optional[BorderConfig] = None,
        style: Optional[str] = None,
        size: Tuple[int, int] = PREVIEW_SIZE,
        background_color: Tuple[int, int, int] = (255, 255, 255),
    ) -> Image.Image:
        """生成边框样式预览图.

        用于 UI 中显示选中的边框效果。

        Args:
            width: 边框宽度
            color: 边框颜色 RGB
            config: 边框配置对象
            style: 边框样式
            size: 预览图尺寸
            background_color: 背景颜色

        Returns:
            预览图片

        Example:
            >>> service = ImageService()
            >>> preview = service.generate_border_preview(
            ...     width=5,
            ...     color=(0, 0, 0),
            ...     style="dashed"
            ... )
            >>> preview.show()
        """
        # 确定参数
        if config is not None:
            border_width = config.width
            border_color = config.get_effective_color()
            border_style = config.style.value
        else:
            border_width = width
            border_color = color if color is not None else DEFAULT_BORDER_COLOR
            border_style = style if style is not None else "solid"

        return create_border_preview(
            width=border_width,
            color=border_color,
            style=border_style,
            size=size,
            background_color=background_color,
        )

    def get_border_styles(self) -> list[dict]:
        """获取所有可用的边框样式.

        供 UI 边框样式选择器使用。

        Returns:
            边框样式信息列表，每项包含 value, style, name 字段

        Example:
            >>> service = ImageService()
            >>> styles = service.get_border_styles()
            >>> for s in styles:
            ...     print(f"{s['name']}: {s['value']}")
        """
        return BorderConfig.get_available_styles()

    # ==========================================
    # 文字添加功能
    # ==========================================

    async def add_image_text(
        self,
        input_path: Union[str, Path],
        output_path: Optional[Union[str, Path]] = None,
        config: Optional[TextConfig] = None,
        text: Optional[str] = None,
        position: Optional[Tuple[int, int]] = None,
        font_size: int = 14,
        color: Optional[Tuple[int, int, int]] = None,
        on_progress: Optional[ProgressCallback] = None,
    ) -> Path:
        """为图片添加文字.

        支持多种文字样式，可通过配置对象或直接指定参数。

        Args:
            input_path: 输入图片路径
            output_path: 输出图片路径，如果为 None 则自动生成
            config: 文字配置对象
            text: 文字内容，优先级低于 config
            position: 文字位置 (x, y)，优先级低于 config
            font_size: 字体大小，优先级低于 config
            color: 文字颜色 RGB，优先级低于 config
            on_progress: 进度回调函数

        Returns:
            输出文件路径

        Raises:
            ImageNotFoundError: 输入文件不存在
            ImageProcessError: 图片处理失败

        Example:
            >>> service = ImageService()
            >>> # 使用配置对象
            >>> config = TextConfig(text="水印", preset_position=TextPosition.BOTTOM_RIGHT)
            >>> result = await service.add_image_text("input.jpg", config=config)
            >>>
            >>> # 直接指定参数
            >>> result = await service.add_image_text(
            ...     "input.jpg",
            ...     text="水印",
            ...     position=(10, 10),
            ...     font_size=24,
            ...     color=(128, 128, 128)
            ... )
        """
        input_path = Path(input_path)
        logger.info(f"开始添加文字: {input_path}")

        def report_progress(progress: int, message: str) -> None:
            if on_progress:
                on_progress(progress, message)
            logger.debug(f"进度 {progress}%: {message}")

        try:
            # Step 1: 确定文字参数 (5%)
            report_progress(5, "准备文字配置")

            if config is not None:
                if not config.enabled:
                    # 文字未启用，直接复制原文件
                    output_path = self._get_output_path(input_path, output_path, "_text.jpg")
                    import shutil
                    shutil.copy(input_path, output_path)
                    report_progress(100, "完成（文字未启用）")
                    return output_path
                text_content = config.content
                text_font_size = config.font_size
                text_color = config.get_effective_color()
                text_opacity = config.opacity
                text_font_family = config.font_family
                text_background_enabled = config.background_enabled
                text_background_color = config.background_color
                text_background_opacity = config.background_opacity
                text_background_padding = config.background_padding
                text_stroke_enabled = config.stroke_enabled
                text_stroke_color = config.stroke_color
                text_stroke_width = config.stroke_width
                text_position_preset = config.preset_position
                text_custom_position = config.custom_position
                text_margin = config.margin
            else:
                text_content = text if text is not None else ""
                text_font_size = font_size
                text_color = color if color is not None else (0, 0, 0)
                text_opacity = 100
                text_font_family = None
                text_background_enabled = False
                text_background_color = (0, 0, 0)
                text_background_opacity = 50
                text_background_padding = 5
                text_stroke_enabled = False
                text_stroke_color = (255, 255, 255)
                text_stroke_width = 1
                text_position_preset = None
                text_custom_position = position
                text_margin = 10

            if not text_content:
                # 没有文字内容，直接复制原文件
                output_path = self._get_output_path(input_path, output_path, "_text.jpg")
                import shutil
                shutil.copy(input_path, output_path)
                report_progress(100, "完成（无文字内容）")
                return output_path

            # Step 2: 验证输入文件 (10%)
            report_progress(10, "验证输入文件")
            validate_image_file(input_path)

            # Step 3: 加载图片 (30%)
            report_progress(30, "加载图片")
            loop = asyncio.get_event_loop()
            image = await loop.run_in_executor(None, load_image, input_path)

            # Step 4: 计算文字位置 (40%)
            report_progress(40, "计算文字位置")
            if text_custom_position is not None:
                final_position = text_custom_position
            elif text_position_preset is not None and text_position_preset != TextPosition.CUSTOM:
                # 计算预设位置
                text_size = get_text_size(text_content, text_font_family, text_font_size)
                final_position = calculate_text_position(
                    image.size,
                    text_size,
                    text_position_preset.value,
                    text_margin,
                )
            else:
                # 默认位置：右下角
                text_size = get_text_size(text_content, text_font_family, text_font_size)
                final_position = calculate_text_position(
                    image.size,
                    text_size,
                    "bottom_right",
                    text_margin,
                )

            # Step 5: 添加文字 (60%)
            report_progress(60, "添加文字")
            result_image = await loop.run_in_executor(
                None,
                add_text,
                image,
                text_content,
                final_position,
                text_font_size,
                text_color,
                text_opacity,
                text_font_family,
                text_background_enabled,
                text_background_color,
                text_background_opacity,
                text_background_padding,
                text_stroke_enabled,
                text_stroke_color,
                text_stroke_width,
            )

            # Step 6: 保存结果 (90%)
            report_progress(90, "保存结果")
            output_path = self._get_output_path(input_path, output_path, "_text.jpg")
            await loop.run_in_executor(
                None, save_image, result_image, output_path, DEFAULT_OUTPUT_QUALITY
            )

            # 完成 (100%)
            report_progress(100, "完成")
            logger.info(f"文字添加完成: {output_path}")

            return output_path

        except Exception as e:
            logger.exception(f"文字添加失败: {input_path}")
            raise ImageProcessError(f"文字添加失败: {e}") from e

    def generate_text_preview(
        self,
        text: str = "预览文字",
        font_size: int = 24,
        color: Optional[Tuple[int, int, int]] = None,
        config: Optional[TextConfig] = None,
        size: Tuple[int, int] = PREVIEW_SIZE,
        background_color: Tuple[int, int, int] = (255, 255, 255),
    ) -> Image.Image:
        """生成文字样式预览图.

        用于 UI 中显示选中的文字效果。

        Args:
            text: 预览文字内容
            font_size: 字体大小
            color: 文字颜色 RGB
            config: 文字配置对象
            size: 预览图尺寸
            background_color: 背景颜色

        Returns:
            预览图片

        Example:
            >>> service = ImageService()
            >>> preview = service.generate_text_preview(
            ...     text="水印预览",
            ...     font_size=24,
            ...     color=(128, 128, 128)
            ... )
            >>> preview.show()
        """
        # 确定参数
        if config is not None:
            preview_text = config.content or text
            preview_font_size = config.font_size
            preview_color = config.get_effective_color()
            preview_font_family = config.font_family
        else:
            preview_text = text
            preview_font_size = font_size
            preview_color = color if color is not None else (0, 0, 0)
            preview_font_family = None

        return create_text_preview(
            text=preview_text,
            font_size=preview_font_size,
            color=preview_color,
            background_color=background_color,
            size=size,
            font_family=preview_font_family,
        )

    def get_text_positions(self) -> list[dict]:
        """获取所有可用的文字位置.

        供 UI 位置选择器使用。

        Returns:
            文字位置信息列表，每项包含 value, position, name 字段

        Example:
            >>> service = ImageService()
            >>> positions = service.get_text_positions()
            >>> for p in positions:
            ...     print(f"{p['name']}: {p['value']}")
        """
        return TextConfig.get_available_positions()

    def get_text_aligns(self) -> list[dict]:
        """获取所有可用的文字对齐方式.

        供 UI 对齐选择器使用。

        Returns:
            对齐方式信息列表，每项包含 value, align, name 字段
        """
        return TextConfig.get_available_aligns()

    def get_available_fonts(self) -> list[dict]:
        """获取可用的字体列表.

        供 UI 字体选择器使用。

        Returns:
            字体信息列表，每项包含 name, path 字段
        """
        return get_available_fonts()

    # ==========================================
    # 图片输出功能
    # ==========================================

    async def export_image(
        self,
        input_path: Union[str, Path],
        output_path: Optional[Union[str, Path]] = None,
        config: Optional[OutputConfig] = None,
        format: Optional[str] = None,
        quality: Optional[int] = None,
        size: Optional[Tuple[int, int]] = None,
        on_progress: Optional[ProgressCallback] = None,
    ) -> Path:
        """导出图片.

        支持 JPG/PNG/WebP 格式输出，尺寸调整和质量压缩。

        Args:
            input_path: 输入图片路径
            output_path: 输出图片路径，如果为 None 则自动生成
            config: 输出配置对象
            format: 输出格式，优先级低于 config
            quality: 输出质量，优先级低于 config
            size: 输出尺寸，优先级低于 config
            on_progress: 进度回调函数

        Returns:
            输出文件路径

        Raises:
            ImageNotFoundError: 输入文件不存在
            ImageProcessError: 图片处理失败

        Example:
            >>> service = ImageService()
            >>> # 使用配置对象
            >>> config = OutputConfig.for_ecommerce()
            >>> result = await service.export_image("input.png", config=config)
            >>>
            >>> # 直接指定参数
            >>> result = await service.export_image(
            ...     "input.png",
            ...     format="jpeg",
            ...     quality=85,
            ...     size=(800, 800)
            ... )
        """
        input_path = Path(input_path)
        logger.info(f"开始导出图片: {input_path}")

        def report_progress(progress: int, message: str) -> None:
            if on_progress:
                on_progress(progress, message)
            logger.debug(f"进度 {progress}%: {message}")

        try:
            # Step 1: 确定输出参数 (5%)
            report_progress(5, "准备输出配置")

            if config is not None:
                out_format = config.format.value
                out_quality = config.get_effective_quality()
                out_size = config.size if config.resize_mode != ResizeMode.NONE else None
                out_resize_mode = config.resize_mode.value
                out_bg_color = config.background_color
                out_optimize = config.optimize
                out_extension = config.get_file_extension()
            else:
                out_format = format if format is not None else "jpeg"
                out_quality = quality if quality is not None else DEFAULT_OUTPUT_QUALITY
                out_size = size
                out_resize_mode = "fit"
                out_bg_color = (255, 255, 255)
                out_optimize = True
                out_extension = ".jpg" if out_format in ("jpeg", "jpg") else f".{out_format}"

            # Step 2: 验证输入文件 (10%)
            report_progress(10, "验证输入文件")
            validate_image_file(input_path)

            # Step 3: 加载图片 (30%)
            report_progress(30, "加载图片")
            loop = asyncio.get_event_loop()
            image = await loop.run_in_executor(None, load_image, input_path)

            # Step 4: 调整尺寸 (50%)
            if out_size is not None:
                report_progress(50, "调整尺寸")
                image = await loop.run_in_executor(
                    None, resize_with_mode, image, out_size, out_resize_mode, out_bg_color
                )
            else:
                report_progress(50, "保持原始尺寸")

            # Step 5: 导出图片 (90%)
            report_progress(70, "导出图片")
            output_path = self._get_output_path(
                input_path, output_path, f"_export{out_extension}"
            )
            await loop.run_in_executor(
                None,
                export_image,
                image,
                output_path,
                out_format,
                out_quality,
                None,  # size already applied
                out_resize_mode,
                out_bg_color,
                out_optimize,
            )

            # 完成 (100%)
            report_progress(100, "完成")
            logger.info(f"图片导出完成: {output_path}")

            return output_path

        except Exception as e:
            logger.exception(f"图片导出失败: {input_path}")
            raise ImageProcessError(f"图片导出失败: {e}") from e

    def estimate_export_size(
        self,
        input_path: Union[str, Path],
        config: Optional[OutputConfig] = None,
        format: str = "jpeg",
        quality: int = 85,
    ) -> dict:
        """估算导出文件大小.

        用于 UI 中显示预估的文件大小。

        Args:
            input_path: 输入图片路径
            config: 输出配置对象
            format: 输出格式
            quality: 输出质量

        Returns:
            包含 size_bytes 和 size_formatted 的字典

        Example:
            >>> service = ImageService()
            >>> info = service.estimate_export_size("input.png")
            >>> print(f"预估大小: {info['size_formatted']}")
        """
        image = load_image(input_path)

        # 确定参数
        if config is not None:
            out_format = config.format.value
            out_quality = config.get_effective_quality()
            if config.resize_mode != ResizeMode.NONE:
                image = resize_with_mode(
                    image, config.size, config.resize_mode.value, config.background_color
                )
        else:
            out_format = format
            out_quality = quality

        size_bytes = estimate_file_size(image, out_format, out_quality)

        return {
            "size_bytes": size_bytes,
            "size_formatted": format_file_size(size_bytes),
        }

    def get_output_formats(self) -> list[dict]:
        """获取所有可用的输出格式.

        供 UI 格式选择器使用。

        Returns:
            输出格式信息列表
        """
        return OutputConfig.get_available_formats()

    def get_quality_presets(self) -> list[dict]:
        """获取所有质量预设.

        供 UI 质量选择器使用。

        Returns:
            质量预设信息列表
        """
        return OutputConfig.get_quality_presets()

    def get_resize_modes(self) -> list[dict]:
        """获取所有尺寸调整模式.

        供 UI 尺寸模式选择器使用。

        Returns:
            尺寸模式信息列表
        """
        return OutputConfig.get_resize_modes()


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
