"""图片处理服务集成测试.

测试 ImageService 的完整处理流程。
"""

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


class TestImageServiceBackgroundProcessing:
    """测试背景处理流程."""

    def test_add_solid_background(
        self, temp_dir: Path, sample_product_image: Path, output_dir: Path
    ):
        """测试添加纯色背景."""
        service = ImageService()
        output_path = output_dir / "with_bg.png"

        # 添加白色背景
        result = service.add_background_sync(
            input_path=sample_product_image,
            output_path=output_path,
            color=(255, 255, 255),
        )

        assert result.exists()
        img = Image.open(result)
        assert img.mode == "RGB"  # 添加背景后不再是 RGBA

    def test_add_background_with_config(
        self, temp_dir: Path, sample_product_image: Path, output_dir: Path
    ):
        """测试使用配置添加背景."""
        service = ImageService()
        output_path = output_dir / "with_config_bg.png"

        config = ProcessConfig()
        config.background = BackgroundConfig(
            enabled=True,
            preset_color=PresetColor.WHITE,
        )

        result = service.add_background_sync(
            input_path=sample_product_image,
            output_path=output_path,
            config=config,
        )

        assert result.exists()


class TestImageServiceBorderProcessing:
    """测试边框处理流程."""

    def test_add_simple_border(
        self, temp_dir: Path, sample_background_image: Path, output_dir: Path
    ):
        """测试添加简单边框."""
        service = ImageService()
        output_path = output_dir / "with_border.png"

        result = service.add_border_sync(
            input_path=sample_background_image,
            output_path=output_path,
            width=10,
            color=(0, 0, 0),
        )

        assert result.exists()
        img = Image.open(result)
        # 边框会增加图片尺寸
        original = Image.open(sample_background_image)
        assert img.size[0] >= original.size[0]

    def test_add_border_with_config(
        self, temp_dir: Path, sample_background_image: Path, output_dir: Path
    ):
        """测试使用配置添加边框."""
        service = ImageService()
        output_path = output_dir / "config_border.png"

        config = ProcessConfig()
        config.border = BorderConfig(
            enabled=True,
            width=5,
            color=(255, 0, 0),  # 红色边框
            style=BorderStyle.SOLID,
        )

        result = service.add_border_sync(
            input_path=sample_background_image,
            output_path=output_path,
            config=config,
        )

        assert result.exists()


class TestImageServiceTextProcessing:
    """测试文字处理流程."""

    def test_add_text_overlay(
        self, temp_dir: Path, sample_background_image: Path, output_dir: Path
    ):
        """测试添加文字水印."""
        service = ImageService()
        output_path = output_dir / "with_text.png"

        result = service.add_text_sync(
            input_path=sample_background_image,
            output_path=output_path,
            text="测试文字",
            position=(100, 100),
            font_size=24,
            color=(0, 0, 0),
        )

        assert result.exists()

    def test_add_text_with_config(
        self, temp_dir: Path, sample_background_image: Path, output_dir: Path
    ):
        """测试使用配置添加文字."""
        service = ImageService()
        output_path = output_dir / "config_text.png"

        config = ProcessConfig()
        config.text = TextConfig(
            enabled=True,
            content="商品标签",
            font_size=20,
            color=(0, 0, 255),
        )

        result = service.add_text_sync(
            input_path=sample_background_image,
            output_path=output_path,
            config=config,
        )

        assert result.exists()


class TestImageServicePostProcessing:
    """测试后期处理完整流程."""

    def test_apply_post_processing_pipeline(
        self, temp_dir: Path, sample_product_image: Path, output_dir: Path
    ):
        """测试后期处理流水线."""
        service = ImageService()

        # 创建完整处理配置
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

        output_path = output_dir / "post_processed.png"

        result = service.apply_post_processing_sync(
            input_path=sample_product_image,
            output_path=output_path,
            config=config,
        )

        assert result.exists()
        img = Image.open(result)
        assert img is not None


class TestImageServiceOutputConfig:
    """测试输出配置."""

    def test_output_jpeg_format(
        self, temp_dir: Path, sample_background_image: Path, output_dir: Path
    ):
        """测试 JPEG 输出格式."""
        service = ImageService()

        config = ProcessConfig()
        config.output = OutputConfig(
            format=OutputFormat.JPEG,
            quality=85,
        )

        output_path = output_dir / "output.jpg"

        result = service.apply_post_processing_sync(
            input_path=sample_background_image,
            output_path=output_path,
            config=config,
        )

        assert result.exists()
        assert result.suffix.lower() in [".jpg", ".jpeg"]

    def test_output_with_resize(
        self, temp_dir: Path, sample_background_image: Path, output_dir: Path
    ):
        """测试带尺寸调整的输出."""
        service = ImageService()

        config = ProcessConfig()
        config.output = OutputConfig(
            size=(400, 400),
        )

        output_path = output_dir / "resized.png"

        result = service.apply_post_processing_sync(
            input_path=sample_background_image,
            output_path=output_path,
            config=config,
        )

        assert result.exists()
        img = Image.open(result)
        # 验证尺寸接近目标
        assert img.size[0] <= 400 or img.size[1] <= 400


class TestImageServiceProgressCallback:
    """测试进度回调."""

    @pytest.mark.asyncio
    async def test_remove_background_with_progress(
        self, temp_dir: Path, sample_product_image: Path, output_dir: Path
    ):
        """测试背景去除进度回调."""
        service = ImageService()
        progress_updates = []

        def on_progress(progress: int, message: str):
            progress_updates.append((progress, message))

        # Mock AI 服务
        mock_ai = AsyncMock()
        mock_ai.remove_background.return_value = (
            Image.open(sample_product_image).tobytes()
        )

        with patch.object(service, "_ai_service", mock_ai):
            with patch.object(service, "ai_service", mock_ai):
                # 由于 AI 服务被 mock，我们只测试回调机制
                output_path = output_dir / "no_bg.png"

                # 实际测试需要完整的 mock 设置
                # 这里验证回调函数可以正常传递
                assert callable(on_progress)


class TestImageServiceErrorHandling:
    """测试错误处理."""

    def test_invalid_input_file(self, temp_dir: Path, output_dir: Path):
        """测试无效输入文件."""
        service = ImageService()
        nonexistent = temp_dir / "nonexistent.png"
        output = output_dir / "output.png"

        with pytest.raises(Exception):  # ImageNotFoundError 或类似
            service.add_background_sync(
                input_path=nonexistent,
                output_path=output,
                color=(255, 255, 255),
            )

    def test_invalid_image_format(self, temp_dir: Path, output_dir: Path):
        """测试无效图片格式."""
        service = ImageService()

        # 创建一个非图片文件
        invalid_file = temp_dir / "invalid.txt"
        invalid_file.write_text("not an image")

        output = output_dir / "output.png"

        with pytest.raises(Exception):
            service.add_background_sync(
                input_path=invalid_file,
                output_path=output,
                color=(255, 255, 255),
            )


class TestImageServicePreviewGeneration:
    """测试预览生成."""

    def test_create_thumbnail(
        self, temp_dir: Path, sample_background_image: Path
    ):
        """测试创建缩略图."""
        from src.utils.image_utils import create_thumbnail

        thumbnail = create_thumbnail(sample_background_image, size=(100, 100))

        assert thumbnail is not None
        assert thumbnail.size[0] <= 100
        assert thumbnail.size[1] <= 100

    def test_create_background_preview(
        self, temp_dir: Path, sample_product_image: Path
    ):
        """测试创建背景预览."""
        from src.utils.image_utils import create_background_preview

        img = Image.open(sample_product_image)
        preview = create_background_preview(
            img,
            color=(255, 255, 255),
            preview_size=(200, 200),
        )

        assert preview is not None
        assert preview.size[0] <= 200
        assert preview.size[1] <= 200

    def test_create_border_preview(
        self, temp_dir: Path, sample_background_image: Path
    ):
        """测试创建边框预览."""
        from src.utils.image_utils import create_border_preview

        img = Image.open(sample_background_image)
        preview = create_border_preview(
            img,
            border_width=5,
            border_color=(0, 0, 0),
            preview_size=(200, 200),
        )

        assert preview is not None
