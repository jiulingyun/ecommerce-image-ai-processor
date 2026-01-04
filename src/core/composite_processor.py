"""商品合成处理器模块.

提供商品合成的核心算法，包括位置计算、尺寸适配和合成效果优化。

Features:
    - 智能位置计算
    - 多种合成模式
    - 尺寸自动适配
    - 光照融合优化
"""

from __future__ import annotations

import asyncio
import io
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable, Optional, Tuple

from PIL import Image

from src.models.api_config import APIConfig
from src.services.ai_service import AIService, get_ai_service
from src.utils.exceptions import ImageProcessError
from src.utils.image_utils import (
    bytes_to_image,
    ensure_rgba,
    image_to_bytes,
    load_image,
    save_image,
    validate_image_file,
)
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

# 进度回调类型
ProgressCallback = Callable[[int, str], None]


class CompositeMode(str, Enum):
    """合成模式枚举."""

    AUTO = "auto"  # 自动检测最佳位置
    CENTER = "center"  # 居中放置
    LEFT = "left"  # 左侧放置
    RIGHT = "right"  # 右侧放置
    TOP = "top"  # 顶部放置
    BOTTOM = "bottom"  # 底部放置
    CUSTOM = "custom"  # 自定义位置


class SceneType(str, Enum):
    """场景类型枚举."""

    INDOOR = "indoor"  # 室内场景
    OUTDOOR = "outdoor"  # 户外场景
    STUDIO = "studio"  # 工作室/纯色背景
    LIFESTYLE = "lifestyle"  # 生活场景
    MODEL = "model"  # 模特场景


@dataclass
class CompositePosition:
    """合成位置配置."""

    x: int  # X 坐标
    y: int  # Y 坐标
    width: int  # 商品宽度
    height: int  # 商品高度
    rotation: float = 0.0  # 旋转角度
    scale: float = 1.0  # 缩放比例


@dataclass
class CompositeConfig:
    """合成配置."""

    mode: CompositeMode = CompositeMode.AUTO
    scene_type: Optional[SceneType] = None
    position: Optional[CompositePosition] = None
    maintain_aspect_ratio: bool = True
    max_product_ratio: float = 0.5  # 商品最大占比
    min_product_ratio: float = 0.1  # 商品最小占比
    shadow_enabled: bool = True
    reflection_enabled: bool = False
    custom_prompt: Optional[str] = None


class CompositeProcessor:
    """商品合成处理器.

    实现商品合成的核心算法，包括智能位置计算、尺寸适配和 AI 合成调用。

    Attributes:
        ai_service: AI 服务实例

    Example:
        >>> processor = CompositeProcessor()
        >>> result = await processor.composite(
        ...     background="scene.jpg",
        ...     product="product.png",
        ...     config=CompositeConfig(mode=CompositeMode.CENTER),
        ... )
    """

    def __init__(self, ai_service: Optional[AIService] = None) -> None:
        """初始化合成处理器.

        Args:
            ai_service: AI 服务实例
        """
        self._ai_service = ai_service

    @property
    def ai_service(self) -> AIService:
        """获取 AI 服务实例."""
        if self._ai_service is None:
            self._ai_service = get_ai_service()
        return self._ai_service

    async def composite(
        self,
        background: str | Path | bytes,
        product: str | Path | bytes,
        output_path: Optional[str | Path] = None,
        config: Optional[CompositeConfig] = None,
        on_progress: Optional[ProgressCallback] = None,
    ) -> Path | bytes:
        """执行商品合成.

        Args:
            background: 背景图（路径或字节数据）
            product: 商品图（路径或字节数据）
            output_path: 输出路径，如果为 None 则返回字节数据
            config: 合成配置
            on_progress: 进度回调

        Returns:
            输出路径或合成后的字节数据
        """
        config = config or CompositeConfig()

        def report_progress(progress: int, message: str) -> None:
            if on_progress:
                on_progress(progress, message)
            logger.debug(f"进度 {progress}%: {message}")

        try:
            # Step 1: 加载图片 (0-20%)
            report_progress(5, "加载图片")
            bg_image, bg_bytes = await self._load_image(background)
            prod_image, prod_bytes = await self._load_image(product)
            report_progress(20, "图片加载完成")

            # Step 2: 计算合成位置 (20-30%)
            report_progress(25, "计算合成位置")
            position = self._calculate_position(bg_image, prod_image, config)
            report_progress(30, "位置计算完成")

            # Step 3: 预处理商品图 (30-40%)
            report_progress(35, "预处理商品图")
            processed_product = await self._preprocess_product(
                prod_image, position, config
            )
            processed_bytes = image_to_bytes(processed_product, format="PNG")
            report_progress(40, "预处理完成")

            # Step 4: 构建合成提示词 (40-45%)
            report_progress(42, "构建提示词")
            prompt = self._build_composite_prompt(config, position)
            report_progress(45, "提示词构建完成")

            # Step 5: 调用 AI 合成 (45-85%)
            report_progress(50, "AI 合成中...")
            result_bytes = await self.ai_service.composite_product(
                background=bg_bytes,
                product=processed_bytes,
                prompt=prompt,
                position_hint=self._get_position_hint(config.mode),
            )
            report_progress(85, "AI 合成完成")

            # Step 6: 后处理 (85-95%)
            report_progress(90, "后处理")
            final_image = bytes_to_image(result_bytes)

            # Step 7: 输出结果 (95-100%)
            if output_path:
                report_progress(95, "保存结果")
                output_path = Path(output_path)
                await asyncio.get_event_loop().run_in_executor(
                    None, save_image, final_image, output_path, 95
                )
                report_progress(100, "完成")
                return output_path
            else:
                report_progress(100, "完成")
                return image_to_bytes(final_image, format="PNG")

        except Exception as e:
            logger.exception("商品合成失败")
            raise ImageProcessError(f"商品合成失败: {e}") from e

    async def _load_image(
        self, source: str | Path | bytes
    ) -> Tuple[Image.Image, bytes]:
        """加载图片.

        Args:
            source: 图片来源

        Returns:
            (Image 对象, 字节数据) 元组
        """
        if isinstance(source, bytes):
            image = bytes_to_image(source)
            return image, source
        else:
            path = Path(source)
            validate_image_file(path)
            loop = asyncio.get_event_loop()
            image = await loop.run_in_executor(None, load_image, path)
            image = ensure_rgba(image)
            image_bytes = image_to_bytes(image, format="PNG")
            return image, image_bytes

    def _calculate_position(
        self,
        background: Image.Image,
        product: Image.Image,
        config: CompositeConfig,
    ) -> CompositePosition:
        """计算商品合成位置.

        根据配置和图片尺寸计算最佳合成位置。

        Args:
            background: 背景图
            product: 商品图
            config: 合成配置

        Returns:
            合成位置配置
        """
        bg_w, bg_h = background.size
        prod_w, prod_h = product.size

        # 如果已指定位置，直接使用
        if config.position:
            return config.position

        # 计算商品目标尺寸
        target_w, target_h = self._calculate_target_size(
            bg_w, bg_h, prod_w, prod_h, config
        )

        # 根据模式计算位置
        if config.mode == CompositeMode.CENTER:
            x = (bg_w - target_w) // 2
            y = (bg_h - target_h) // 2
        elif config.mode == CompositeMode.LEFT:
            x = int(bg_w * 0.1)
            y = (bg_h - target_h) // 2
        elif config.mode == CompositeMode.RIGHT:
            x = int(bg_w * 0.9) - target_w
            y = (bg_h - target_h) // 2
        elif config.mode == CompositeMode.TOP:
            x = (bg_w - target_w) // 2
            y = int(bg_h * 0.1)
        elif config.mode == CompositeMode.BOTTOM:
            x = (bg_w - target_w) // 2
            y = int(bg_h * 0.9) - target_h
        else:  # AUTO 模式
            # 默认使用黄金比例位置
            x = int(bg_w * 0.382) - target_w // 2
            y = int(bg_h * 0.5) - target_h // 2

        # 确保在边界内
        x = max(0, min(x, bg_w - target_w))
        y = max(0, min(y, bg_h - target_h))

        return CompositePosition(
            x=x,
            y=y,
            width=target_w,
            height=target_h,
            scale=target_w / prod_w,
        )

    def _calculate_target_size(
        self,
        bg_w: int,
        bg_h: int,
        prod_w: int,
        prod_h: int,
        config: CompositeConfig,
    ) -> Tuple[int, int]:
        """计算商品目标尺寸.

        Args:
            bg_w: 背景宽度
            bg_h: 背景高度
            prod_w: 商品宽度
            prod_h: 商品高度
            config: 合成配置

        Returns:
            (目标宽度, 目标高度) 元组
        """
        # 计算理想占比
        ideal_ratio = (config.max_product_ratio + config.min_product_ratio) / 2

        # 计算目标尺寸
        if config.maintain_aspect_ratio:
            # 保持纵横比
            aspect_ratio = prod_w / prod_h

            # 先按宽度计算
            target_w = int(bg_w * ideal_ratio)
            target_h = int(target_w / aspect_ratio)

            # 如果高度超出限制，按高度重新计算
            max_h = int(bg_h * config.max_product_ratio)
            if target_h > max_h:
                target_h = max_h
                target_w = int(target_h * aspect_ratio)
        else:
            target_w = int(bg_w * ideal_ratio)
            target_h = int(bg_h * ideal_ratio)

        return target_w, target_h

    async def _preprocess_product(
        self,
        product: Image.Image,
        position: CompositePosition,
        config: CompositeConfig,
    ) -> Image.Image:
        """预处理商品图.

        调整尺寸、应用变换等。

        Args:
            product: 原始商品图
            position: 目标位置配置
            config: 合成配置

        Returns:
            预处理后的商品图
        """
        # 确保是 RGBA 模式
        product = ensure_rgba(product)

        # 调整尺寸
        if (position.width, position.height) != product.size:
            product = product.resize(
                (position.width, position.height),
                Image.Resampling.LANCZOS,
            )

        # 应用旋转
        if position.rotation != 0:
            product = product.rotate(
                position.rotation,
                resample=Image.Resampling.BICUBIC,
                expand=True,
            )

        return product

    def _build_composite_prompt(
        self,
        config: CompositeConfig,
        position: CompositePosition,
    ) -> str:
        """构建合成提示词.

        根据配置生成优化的 AI 合成提示词。

        Args:
            config: 合成配置
            position: 位置配置

        Returns:
            提示词字符串
        """
        # 如果有自定义提示词，使用它
        if config.custom_prompt:
            return config.custom_prompt

        # 构建基础提示词
        prompts = [
            "Seamlessly composite the product into the background scene.",
        ]

        # 添加位置描述
        position_desc = self._get_position_description(config.mode)
        prompts.append(f"Place the product at {position_desc}.")

        # 添加场景适配
        if config.scene_type:
            scene_hints = self._get_scene_hints(config.scene_type)
            prompts.append(scene_hints)

        # 添加效果要求
        prompts.append(
            "Match the lighting and perspective of the scene. "
            "Maintain the product's original appearance and details."
        )

        # 添加阴影
        if config.shadow_enabled:
            prompts.append("Add natural shadow under the product.")

        # 添加反射
        if config.reflection_enabled:
            prompts.append("Add subtle reflection effect if appropriate.")

        return " ".join(prompts)

    def _get_position_description(self, mode: CompositeMode) -> str:
        """获取位置描述."""
        descriptions = {
            CompositeMode.AUTO: "the optimal position",
            CompositeMode.CENTER: "the center of the scene",
            CompositeMode.LEFT: "the left side of the scene",
            CompositeMode.RIGHT: "the right side of the scene",
            CompositeMode.TOP: "the top area of the scene",
            CompositeMode.BOTTOM: "the bottom area of the scene",
            CompositeMode.CUSTOM: "the specified position",
        }
        return descriptions.get(mode, "an appropriate position")

    def _get_position_hint(self, mode: CompositeMode) -> str:
        """获取位置提示（传给 AI 服务）."""
        hints = {
            CompositeMode.AUTO: "auto",
            CompositeMode.CENTER: "center",
            CompositeMode.LEFT: "left",
            CompositeMode.RIGHT: "right",
            CompositeMode.TOP: "top",
            CompositeMode.BOTTOM: "bottom",
            CompositeMode.CUSTOM: "custom",
        }
        return hints.get(mode, "center")

    def _get_scene_hints(self, scene_type: SceneType) -> str:
        """获取场景提示."""
        hints = {
            SceneType.INDOOR: (
                "This is an indoor scene. Adjust product lighting to match "
                "indoor ambient light. Consider warm artificial lighting."
            ),
            SceneType.OUTDOOR: (
                "This is an outdoor scene. Match natural daylight and "
                "outdoor environment. Consider sun direction and sky reflection."
            ),
            SceneType.STUDIO: (
                "This is a studio shot with controlled lighting. "
                "Maintain clean, professional product presentation."
            ),
            SceneType.LIFESTYLE: (
                "This is a lifestyle scene. Make the product look naturally "
                "placed as if in everyday use."
            ),
            SceneType.MODEL: (
                "This is a model shot. Position the product naturally on "
                "or with the model. Match skin tone and clothing context."
            ),
        }
        return hints.get(scene_type, "")

    async def batch_composite(
        self,
        items: list[Tuple[str | Path, str | Path]],
        output_dir: str | Path,
        config: Optional[CompositeConfig] = None,
        on_progress: Optional[Callable[[int, int, str], None]] = None,
    ) -> list[Path]:
        """批量合成商品.

        Args:
            items: 列表，每项为 (背景路径, 商品路径) 元组
            output_dir: 输出目录
            config: 合成配置
            on_progress: 进度回调 (current, total, message)

        Returns:
            输出文件路径列表
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        results = []
        total = len(items)

        for i, (bg_path, prod_path) in enumerate(items):
            if on_progress:
                on_progress(i + 1, total, f"处理 {Path(bg_path).name}")

            try:
                bg_name = Path(bg_path).stem
                output_path = output_dir / f"{bg_name}_composite.png"

                result = await self.composite(
                    background=bg_path,
                    product=prod_path,
                    output_path=output_path,
                    config=config,
                )
                results.append(result)

            except Exception as e:
                logger.error(f"批量合成失败 [{i+1}/{total}]: {e}")
                results.append(None)

        return [r for r in results if r is not None]


# 便捷函数
async def composite_product(
    background: str | Path | bytes,
    product: str | Path | bytes,
    output_path: Optional[str | Path] = None,
    mode: CompositeMode = CompositeMode.AUTO,
    scene_type: Optional[SceneType] = None,
    **kwargs,
) -> Path | bytes:
    """便捷的商品合成函数.

    Args:
        background: 背景图
        product: 商品图
        output_path: 输出路径
        mode: 合成模式
        scene_type: 场景类型
        **kwargs: 其他配置参数

    Returns:
        输出路径或字节数据
    """
    config = CompositeConfig(
        mode=mode,
        scene_type=scene_type,
        **kwargs,
    )

    processor = CompositeProcessor()
    return await processor.composite(
        background=background,
        product=product,
        output_path=output_path,
        config=config,
    )
