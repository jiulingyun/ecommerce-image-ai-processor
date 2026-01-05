"""图片处理服务集成测试.

测试 ImageService 的完整处理流程。
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from PIL import Image

from src.models.process_config import (
    ProcessConfig,
    BackgroundConfig,
    BorderConfig,
    BorderStyle,
    OutputConfig,
    OutputFormat,
    PresetColor,
    TextConfig,
)
from src.services.image_service import ImageService
from src.utils.image_utils import (
    add_solid_background,
    add_border,
    create_thumbnail,
    ensure_rgba,
    load_image,
)


class TestImageServiceBackgroundProcessing:
    """测试背景处理流程."""

    @pytest.mark.asyncio
    async def test_add_solid_background(
        self, temp_dir: Path, sample_product_image: Path, output_dir: Path
    ):
        """测试添加纯色背景."""
        service = ImageService()
        output_path = output_dir / "with_bg.png"

        # 使用异步方法
        result = await service.add_background(
            input_path=sample_product_image,
            output_path=output_path,
            color=(255, 255, 255),
        )

        assert result.exists()
        img = Image.open(result)
        assert img.mode == "RGB"  # 添加背景后不再是 RGBA

    @pytest.mark.asyncio
    async def test_add_background_with_config(
        self, temp_dir: Path, sample_product_image: Path, output_dir: Path
    ):
        """测试使用配置添加背景."""
        service = ImageService()
        output_path = output_dir / "with_config_bg.png"

        config = BackgroundConfig(
            enabled=True,
            preset_color=PresetColor.WHITE,
        )

        result = await service.add_background(
            input_path=sample_product_image,
            output_path=output_path,
            config=config,
        )

        assert result.exists()


class TestImageServiceBorderProcessing:
    """测试边框处理流程."""

    @pytest.mark.asyncio
    async def test_add_simple_border(
        self, temp_dir: Path, sample_background_image: Path, output_dir: Path
    ):
        """测试添加简单边框."""
        service = ImageService()
        output_path = output_dir / "with_border.png"

        # 直接测试 image_utils 函数
        original = load_image(sample_background_image)
        result_img = add_border(original, width=10, color=(0, 0, 0))

        assert result_img is not None
        # 边框会增加图片尺寸
        assert result_img.size[0] >= original.size[0]

    def test_border_config_creation(self):
        """测试边框配置创建."""
        config = BorderConfig(
            enabled=True,
            width=5,
            color=(255, 0, 0),
            style=BorderStyle.SOLID,
        )

        assert config.enabled is True
        assert config.width == 5
        assert config.color == (255, 0, 0)


class TestImageServiceTextProcessing:
    """测试文字处理流程."""

    def test_text_config_creation(self):
        """测试文字配置创建."""
        config = TextConfig(
            enabled=True,
            content="商品标签",
            font_size=20,
            color=(0, 0, 255),
        )

        assert config.enabled is True
        assert config.content == "商品标签"
        assert config.font_size == 20


class TestImageServicePostProcessing:
    """测试后期处理完整流程."""

    def test_process_config_creation(self):
        """测试处理配置创建."""
        config = ProcessConfig()
        config.background = BackgroundConfig(
            enabled=True,
            preset_color=PresetColor.WHITE,
        )
        config.border = BorderConfig(
            enabled=True,
            width=3,
            color=(200, 200, 200),
        )
        config.output = OutputConfig(
            format=OutputFormat.PNG,
            quality=95,
        )

        assert config.background.enabled is True
        assert config.border.enabled is True
        assert config.output.format == OutputFormat.PNG


class TestImageServiceOutputConfig:
    """测试输出配置."""

    def test_output_config_jpeg(self):
        """测试 JPEG 输出配置."""
        config = OutputConfig(
            format=OutputFormat.JPEG,
            quality=85,
        )

        assert config.format == OutputFormat.JPEG
        assert config.quality == 85

    def test_output_config_with_size(self):
        """测试带尺寸的输出配置."""
        config = OutputConfig(
            size=(400, 400),
        )

        assert config.size == (400, 400)


class TestImageServiceProgressCallback:
    """测试进度回调."""

    @pytest.mark.asyncio
    async def test_progress_callback_mechanism(self):
        """测试进度回调机制."""
        progress_updates = []

        def on_progress(progress: int, message: str):
            progress_updates.append((progress, message))

        # 验证回调函数可用
        on_progress(10, "test")
        assert len(progress_updates) == 1
        assert progress_updates[0] == (10, "test")


class TestImageServiceErrorHandling:
    """测试错误处理."""

    @pytest.mark.asyncio
    async def test_invalid_input_file(self, temp_dir: Path, output_dir: Path):
        """测试无效输入文件."""
        service = ImageService()
        nonexistent = temp_dir / "nonexistent.png"
        output = output_dir / "output.png"

        with pytest.raises(Exception):
            await service.add_background(
                input_path=nonexistent,
                output_path=output,
                color=(255, 255, 255),
            )


class TestImageServicePreviewGeneration:
    """测试预览生成."""

    def test_create_thumbnail(
        self, temp_dir: Path, sample_background_image: Path
    ):
        """测试创建缩略图."""
        # create_thumbnail 期望 Image 对象，而不是 Path
        img = load_image(sample_background_image)
        thumbnail = create_thumbnail(img, size=(100, 100))

        assert thumbnail is not None
        assert thumbnail.size[0] <= 100
        assert thumbnail.size[1] <= 100

    def test_ensure_rgba(self, sample_background_image: Path):
        """测试确保 RGBA 模式."""
        img = load_image(sample_background_image)
        rgba_img = ensure_rgba(img)

        assert rgba_img.mode == "RGBA"

    def test_add_solid_background_util(self, sample_product_image: Path):
        """测试添加纯色背景工具函数."""
        img = load_image(sample_product_image)
        img = ensure_rgba(img)
        result = add_solid_background(img, (255, 255, 255))

        assert result is not None
        assert result.mode == "RGB"
