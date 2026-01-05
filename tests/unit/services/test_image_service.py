"""图片处理服务单元测试."""

from __future__ import annotations

import io
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from PIL import Image
from pydantic import SecretStr

from src.models.api_config import APIConfig
from src.models.image_task import ImageTask, TaskStatus
from src.models.process_config import (
    BackgroundConfig,
    BorderConfig,
    BorderStyle,
    PresetColor,
    ProcessConfig,
)
from src.services.ai_service import AIService
from src.services.image_service import (
    ImageService,
    get_image_service,
    reset_image_service,
)
from src.utils.exceptions import (
    AIServiceError,
    ImageNotFoundError,
    ImageProcessError,
)


# ===================
# Fixtures
# ===================
@pytest.fixture
def temp_dir():
    """创建临时目录."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_image_path(temp_dir: Path) -> Path:
    """创建测试用图片文件."""
    img = Image.new("RGBA", (100, 100), (255, 0, 0, 255))
    path = temp_dir / "test_image.png"
    img.save(path)
    return path


@pytest.fixture
def sample_background_path(temp_dir: Path) -> Path:
    """创建测试用背景图片."""
    img = Image.new("RGB", (200, 200), (0, 128, 255))
    path = temp_dir / "test_background.jpg"
    img.save(path)
    return path


@pytest.fixture
def sample_result_bytes() -> bytes:
    """生成模拟的 AI 处理结果."""
    img = Image.new("RGBA", (100, 100), (0, 255, 0, 128))
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture
def mock_ai_service(sample_result_bytes: bytes) -> MagicMock:
    """创建模拟的 AI 服务."""
    mock = MagicMock(spec=AIService)
    mock.remove_background = AsyncMock(return_value=sample_result_bytes)
    mock.composite_product = AsyncMock(return_value=sample_result_bytes)
    return mock


@pytest.fixture
def image_service(mock_ai_service: MagicMock) -> ImageService:
    """创建图片处理服务实例."""
    return ImageService(ai_service=mock_ai_service)


@pytest.fixture
def sample_config() -> ProcessConfig:
    """创建测试用处理配置."""
    return ProcessConfig(
        background={"color": (255, 255, 255)},
        border={"enabled": True, "width": 2, "color": (0, 0, 0)},
        text={"enabled": False},
        output={"size": (800, 800), "quality": 85},
    )


# ===================
# 初始化测试
# ===================
class TestImageServiceInit:
    """测试 ImageService 初始化."""

    def test_init_with_ai_service(self, mock_ai_service: MagicMock) -> None:
        """测试使用 AI 服务初始化."""
        service = ImageService(ai_service=mock_ai_service)
        assert service._ai_service is mock_ai_service

    def test_init_without_ai_service(self) -> None:
        """测试不使用 AI 服务初始化."""
        service = ImageService()
        assert service._ai_service is None


# ===================
# 背景去除测试
# ===================
class TestRemoveBackground:
    """测试背景去除功能."""

    @pytest.mark.asyncio
    async def test_remove_background_success(
        self,
        image_service: ImageService,
        sample_image_path: Path,
        temp_dir: Path,
    ) -> None:
        """测试成功去除背景."""
        output_path = temp_dir / "output.png"

        result = await image_service.remove_background(
            sample_image_path,
            output_path,
        )

        assert result == output_path
        assert output_path.exists()

        # 验证调用了 AI 服务
        image_service.ai_service.remove_background.assert_called_once()

    @pytest.mark.asyncio
    async def test_remove_background_auto_output_path(
        self,
        image_service: ImageService,
        sample_image_path: Path,
    ) -> None:
        """测试自动生成输出路径."""
        result = await image_service.remove_background(sample_image_path)

        expected = sample_image_path.parent / "test_image_nobg.png"
        assert result == expected
        assert result.exists()

    @pytest.mark.asyncio
    async def test_remove_background_with_progress(
        self,
        image_service: ImageService,
        sample_image_path: Path,
    ) -> None:
        """测试带进度回调."""
        progress_updates = []

        def on_progress(progress: int, message: str) -> None:
            progress_updates.append((progress, message))

        await image_service.remove_background(
            sample_image_path,
            on_progress=on_progress,
        )

        # 验证进度更新
        assert len(progress_updates) > 0
        assert progress_updates[-1][0] == 100
        assert any(p[0] == 10 for p in progress_updates)  # 验证文件
        assert any(p[0] == 40 for p in progress_updates)  # AI 处理

    @pytest.mark.asyncio
    async def test_remove_background_file_not_found(
        self,
        image_service: ImageService,
    ) -> None:
        """测试文件不存在错误."""
        with pytest.raises(ImageNotFoundError):
            await image_service.remove_background("/nonexistent/path.png")

    @pytest.mark.asyncio
    async def test_remove_background_ai_error(
        self,
        image_service: ImageService,
        sample_image_path: Path,
    ) -> None:
        """测试 AI 服务错误."""
        image_service.ai_service.remove_background = AsyncMock(
            side_effect=AIServiceError("AI 服务错误")
        )

        with pytest.raises(AIServiceError):
            await image_service.remove_background(sample_image_path)


# ===================
# 商品合成测试
# ===================
class TestCompositeProduct:
    """测试商品合成功能."""

    @pytest.mark.asyncio
    async def test_composite_product_success(
        self,
        image_service: ImageService,
        sample_background_path: Path,
        sample_image_path: Path,
        temp_dir: Path,
    ) -> None:
        """测试成功合成商品."""
        output_path = temp_dir / "composite_output.png"

        result = await image_service.composite_product(
            sample_background_path,
            sample_image_path,
            output_path,
        )

        assert result == output_path
        assert output_path.exists()
        image_service.ai_service.composite_product.assert_called_once()

    @pytest.mark.asyncio
    async def test_composite_product_with_position(
        self,
        image_service: ImageService,
        sample_background_path: Path,
        sample_image_path: Path,
    ) -> None:
        """测试使用位置提示合成."""
        await image_service.composite_product(
            sample_background_path,
            sample_image_path,
            position_hint="center",
        )

        call_kwargs = image_service.ai_service.composite_product.call_args[1]
        assert call_kwargs["position_hint"] == "center"


# ===================
# 任务处理测试
# ===================
class TestProcessTask:
    """测试任务处理功能."""

    @pytest.mark.asyncio
    async def test_process_task_success(
        self,
        image_service: ImageService,
        sample_background_path: Path,
        sample_image_path: Path,
        sample_config: ProcessConfig,
    ) -> None:
        """测试成功处理任务."""
        task = ImageTask(
            background_path=str(sample_background_path),
            product_path=str(sample_image_path),
            config=sample_config,
        )

        result = await image_service.process_task(task)

        assert result.status == TaskStatus.COMPLETED
        assert result.progress == 100
        assert result.output_path is not None

    @pytest.mark.asyncio
    async def test_process_task_with_progress(
        self,
        image_service: ImageService,
        sample_background_path: Path,
        sample_image_path: Path,
    ) -> None:
        """测试任务处理进度回调."""
        task = ImageTask(
            background_path=str(sample_background_path),
            product_path=str(sample_image_path),
        )

        progress_updates = []

        def on_progress(progress: int, message: str) -> None:
            progress_updates.append((progress, message))

        await image_service.process_task(task, on_progress=on_progress)

        assert len(progress_updates) > 0
        # 验证有关键进度点
        progress_values = [p[0] for p in progress_updates]
        assert 5 in progress_values  # 开始
        assert 100 in progress_values  # 完成

    @pytest.mark.asyncio
    async def test_process_task_failure(
        self,
        image_service: ImageService,
        sample_background_path: Path,
        sample_image_path: Path,
    ) -> None:
        """测试任务处理失败."""
        image_service.ai_service.remove_background = AsyncMock(
            side_effect=AIServiceError("AI 错误")
        )

        task = ImageTask(
            background_path=str(sample_background_path),
            product_path=str(sample_image_path),
        )

        result = await image_service.process_task(task)

        assert result.status == TaskStatus.FAILED
        assert result.error_message is not None


# ===================
# 后期处理测试
# ===================
class TestPostProcessing:
    """测试后期处理功能."""

    def test_add_background_color(self, image_service: ImageService) -> None:
        """测试添加背景色."""
        # 创建带透明通道的图片
        img = Image.new("RGBA", (100, 100), (255, 0, 0, 128))

        result = image_service._add_background_color(img, (255, 255, 255))

        assert result.mode == "RGB"
        # 背景应该是白色和红色混合

    def test_add_border(self, image_service: ImageService) -> None:
        """测试添加边框."""
        img = Image.new("RGB", (100, 100), (255, 255, 255))

        result = image_service._add_border(img, 2, (0, 0, 0))

        assert result.size == (100, 100)
        # 检查边框像素
        assert result.getpixel((0, 0)) == (0, 0, 0)
        assert result.getpixel((1, 1)) == (0, 0, 0)

    def test_add_text(self, image_service: ImageService) -> None:
        """测试添加文字."""
        img = Image.new("RGB", (200, 200), (255, 255, 255))

        result = image_service._add_text(
            img,
            "Test",
            (10, 10),
            14,
            (0, 0, 0),
        )

        assert result.size == (200, 200)


# ===================
# 单例测试
# ===================
class TestSingleton:
    """测试单例模式."""

    def test_get_image_service_singleton(self) -> None:
        """测试获取单例."""
        reset_image_service()

        service1 = get_image_service()
        service2 = get_image_service()

        assert service1 is service2

        reset_image_service()

    def test_get_image_service_with_ai_service(
        self, mock_ai_service: MagicMock
    ) -> None:
        """测试使用 AI 服务获取单例."""
        reset_image_service()

        service = get_image_service(ai_service=mock_ai_service)

        assert service._ai_service is mock_ai_service

        reset_image_service()

    def test_reset_image_service(self) -> None:
        """测试重置单例."""
        service1 = get_image_service()
        reset_image_service()
        service2 = get_image_service()

        assert service1 is not service2

        reset_image_service()


# ===================
# 辅助方法测试
# ===================
class TestHelperMethods:
    """测试辅助方法."""

    def test_get_output_path_with_provided_path(
        self, image_service: ImageService
    ) -> None:
        """测试使用提供的输出路径."""
        input_path = Path("/path/to/input.jpg")
        output_path = Path("/path/to/output.png")

        result = image_service._get_output_path(input_path, output_path, "_test.png")

        assert result == output_path

    def test_get_output_path_auto_generate(
        self, image_service: ImageService
    ) -> None:
        """测试自动生成输出路径."""
        input_path = Path("/path/to/input.jpg")

        result = image_service._get_output_path(input_path, None, "_nobg.png")

        assert result == Path("/path/to/input_nobg.png")


# ===================
# 背景添加功能测试
# ===================
class TestAddBackground:
    """测试背景添加功能."""

    @pytest.fixture
    def transparent_image_path(self, temp_dir: Path) -> Path:
        """创建带透明背景的测试图片."""
        img = Image.new("RGBA", (100, 100), (255, 0, 0, 0))
        # 在中间画一个不透明的圆
        from PIL import ImageDraw
        draw = ImageDraw.Draw(img)
        draw.ellipse([25, 25, 75, 75], fill=(255, 0, 0, 255))
        path = temp_dir / "transparent.png"
        img.save(path)
        return path

    @pytest.mark.asyncio
    async def test_add_background_with_color(
        self,
        image_service: ImageService,
        transparent_image_path: Path,
        temp_dir: Path,
    ) -> None:
        """测试使用 RGB 颜色添加背景."""
        output_path = temp_dir / "output_bg.jpg"

        result = await image_service.add_background(
            transparent_image_path,
            output_path,
            color=(255, 255, 255),
        )

        assert result == output_path
        assert output_path.exists()

        # 验证输出图片
        output_img = Image.open(output_path)
        assert output_img.mode == "RGB"

    @pytest.mark.asyncio
    async def test_add_background_with_config(
        self,
        image_service: ImageService,
        transparent_image_path: Path,
        temp_dir: Path,
    ) -> None:
        """测试使用配置对象添加背景."""
        config = BackgroundConfig.from_preset(PresetColor.LIGHT_GRAY)
        output_path = temp_dir / "output_config.jpg"

        result = await image_service.add_background(
            transparent_image_path,
            output_path,
            config=config,
        )

        assert result == output_path
        assert output_path.exists()

    @pytest.mark.asyncio
    async def test_add_background_with_hex_color(
        self,
        image_service: ImageService,
        transparent_image_path: Path,
        temp_dir: Path,
    ) -> None:
        """测试使用 HEX 颜色添加背景."""
        config = BackgroundConfig.from_hex("#F5F5F5")
        output_path = temp_dir / "output_hex.jpg"

        result = await image_service.add_background(
            transparent_image_path,
            output_path,
            config=config,
        )

        assert result == output_path
        assert output_path.exists()

    @pytest.mark.asyncio
    async def test_add_background_disabled(
        self,
        image_service: ImageService,
        transparent_image_path: Path,
        temp_dir: Path,
    ) -> None:
        """测试背景添加未启用时直接复制文件."""
        config = BackgroundConfig(enabled=False)
        output_path = temp_dir / "output_disabled.png"

        result = await image_service.add_background(
            transparent_image_path,
            output_path,
            config=config,
        )

        assert result.exists()
        # 应该是直接复制，文件大小应该相同
        assert result.stat().st_size == transparent_image_path.stat().st_size

    @pytest.mark.asyncio
    async def test_add_background_with_progress(
        self,
        image_service: ImageService,
        transparent_image_path: Path,
        temp_dir: Path,
    ) -> None:
        """测试带进度回调."""
        progress_updates = []

        def on_progress(progress: int, message: str) -> None:
            progress_updates.append((progress, message))

        await image_service.add_background(
            transparent_image_path,
            color=(255, 255, 255),
            on_progress=on_progress,
        )

        # 验证进度更新
        assert len(progress_updates) > 0
        assert progress_updates[-1][0] == 100

    @pytest.mark.asyncio
    async def test_add_background_auto_output_path(
        self,
        image_service: ImageService,
        transparent_image_path: Path,
    ) -> None:
        """测试自动生成输出路径."""
        result = await image_service.add_background(
            transparent_image_path,
            color=(255, 255, 255),
        )

        assert result.exists()
        assert "_bg" in result.name

    @pytest.mark.asyncio
    async def test_add_background_file_not_found(
        self,
        image_service: ImageService,
    ) -> None:
        """测试文件不存在错误."""
        with pytest.raises(ImageProcessError):
            await image_service.add_background("/nonexistent/path.png")


class TestAddBackgroundWithResize:
    """测试背景添加并调整尺寸功能."""

    @pytest.fixture
    def small_image_path(self, temp_dir: Path) -> Path:
        """创建小尺寸测试图片."""
        img = Image.new("RGBA", (50, 50), (255, 0, 0, 255))
        path = temp_dir / "small.png"
        img.save(path)
        return path

    @pytest.mark.asyncio
    async def test_add_background_with_resize(
        self,
        image_service: ImageService,
        small_image_path: Path,
        temp_dir: Path,
    ) -> None:
        """测试添加背景并调整尺寸."""
        output_path = temp_dir / "resized_bg.jpg"
        target_size = (200, 200)

        result = await image_service.add_background_with_resize(
            small_image_path,
            output_path,
            color=(255, 255, 255),
            target_size=target_size,
        )

        assert result == output_path
        assert output_path.exists()

        # 验证输出尺寸
        output_img = Image.open(output_path)
        assert output_img.size == target_size


class TestGenerateBackgroundPreview:
    """测试背景预览生成."""

    def test_generate_preview_with_color(
        self, image_service: ImageService
    ) -> None:
        """测试使用颜色生成预览."""
        preview = image_service.generate_background_preview(
            color=(245, 245, 245),
            size=(100, 100),
        )

        assert preview.size == (100, 100)
        assert preview.mode == "RGB"
        # 检查颜色
        assert preview.getpixel((50, 50)) == (245, 245, 245)

    def test_generate_preview_with_config(
        self, image_service: ImageService
    ) -> None:
        """测试使用配置生成预览."""
        config = BackgroundConfig.from_preset(PresetColor.LIGHT_BLUE)
        preview = image_service.generate_background_preview(
            config=config,
            size=(100, 100),
        )

        assert preview.size == (100, 100)
        # 浅蓝色
        assert preview.getpixel((50, 50)) == (227, 242, 253)

    def test_generate_preview_transparent(
        self, image_service: ImageService
    ) -> None:
        """测试透明背景预览（棋盘格）."""
        config = BackgroundConfig.from_preset(PresetColor.TRANSPARENT)
        preview = image_service.generate_background_preview(
            config=config,
            size=(100, 100),
        )

        assert preview.size == (100, 100)

    def test_generate_preview_with_sample_image(
        self,
        image_service: ImageService,
        sample_image_path: Path,
    ) -> None:
        """测试使用样本图片生成预览."""
        preview = image_service.generate_background_preview(
            color=(255, 255, 255),
            size=(150, 150),
            sample_image=sample_image_path,
        )

        assert preview.size == (150, 150)


class TestGetPresetColors:
    """测试获取预设颜色."""

    def test_get_preset_colors(self, image_service: ImageService) -> None:
        """测试获取预设颜色列表."""
        colors = image_service.get_preset_colors()

        assert len(colors) > 0
        # 验证结构
        for color in colors:
            assert "name" in color
            assert "preset" in color
            assert "rgb" in color
            assert "hex" in color

        # 验证包含白色
        white = next((c for c in colors if c["name"] == "white"), None)
        assert white is not None
        assert white["rgb"] == (255, 255, 255)
        assert white["hex"] == "#FFFFFF"


# ===================
# 边框添加功能测试
# ===================
class TestAddImageBorder:
    """测试边框添加功能."""

    @pytest.mark.asyncio
    async def test_add_border_with_params(
        self,
        image_service: ImageService,
        sample_image_path: Path,
        temp_dir: Path,
    ) -> None:
        """测试使用参数添加边框."""
        output_path = temp_dir / "output_border.jpg"

        result = await image_service.add_image_border(
            sample_image_path,
            output_path,
            width=5,
            color=(0, 0, 0),
            style="solid",
        )

        assert result == output_path
        assert output_path.exists()

        # 验证输出图片
        output_img = Image.open(output_path)
        assert output_img.mode == "RGB"

    @pytest.mark.asyncio
    async def test_add_border_with_config(
        self,
        image_service: ImageService,
        sample_image_path: Path,
        temp_dir: Path,
    ) -> None:
        """测试使用配置对象添加边框."""
        config = BorderConfig.from_hex("#FF0000", width=3, style=BorderStyle.DASHED)
        output_path = temp_dir / "output_config_border.jpg"

        result = await image_service.add_image_border(
            sample_image_path,
            output_path,
            config=config,
        )

        assert result == output_path
        assert output_path.exists()

    @pytest.mark.asyncio
    async def test_add_border_disabled(
        self,
        image_service: ImageService,
        sample_image_path: Path,
        temp_dir: Path,
    ) -> None:
        """测试边框未启用时直接复制文件."""
        config = BorderConfig(enabled=False)
        output_path = temp_dir / "output_disabled_border.jpg"

        result = await image_service.add_image_border(
            sample_image_path,
            output_path,
            config=config,
        )

        assert result.exists()

    @pytest.mark.asyncio
    async def test_add_border_expand(
        self,
        image_service: ImageService,
        sample_image_path: Path,
        temp_dir: Path,
    ) -> None:
        """测试扩展尺寸添加边框."""
        # 获取原图尺寸
        orig_img = Image.open(sample_image_path)
        orig_w, orig_h = orig_img.size
        border_width = 10

        output_path = temp_dir / "output_expand_border.jpg"

        result = await image_service.add_image_border(
            sample_image_path,
            output_path,
            width=border_width,
            color=(255, 0, 0),
            expand=True,
        )

        assert result.exists()

        # 验证尺寸扩展
        output_img = Image.open(output_path)
        assert output_img.width == orig_w + border_width * 2
        assert output_img.height == orig_h + border_width * 2

    @pytest.mark.asyncio
    async def test_add_border_all_styles(
        self,
        image_service: ImageService,
        sample_image_path: Path,
        temp_dir: Path,
    ) -> None:
        """测试所有边框样式."""
        styles = ["solid", "dashed", "dotted", "double", "groove", "ridge", "inset", "outset"]

        for style in styles:
            output_path = temp_dir / f"border_{style}.jpg"
            result = await image_service.add_image_border(
                sample_image_path,
                output_path,
                width=5,
                color=(0, 0, 0),
                style=style,
            )
            assert result.exists(), f"Style {style} failed"

    @pytest.mark.asyncio
    async def test_add_border_with_progress(
        self,
        image_service: ImageService,
        sample_image_path: Path,
        temp_dir: Path,
    ) -> None:
        """测试带进度回调."""
        progress_updates = []

        def on_progress(progress: int, message: str) -> None:
            progress_updates.append((progress, message))

        await image_service.add_image_border(
            sample_image_path,
            width=5,
            color=(0, 0, 0),
            on_progress=on_progress,
        )

        assert len(progress_updates) > 0
        assert progress_updates[-1][0] == 100


class TestGenerateBorderPreview:
    """测试边框预览生成."""

    def test_generate_preview_with_params(
        self, image_service: ImageService
    ) -> None:
        """测试使用参数生成预览."""
        preview = image_service.generate_border_preview(
            width=5,
            color=(0, 0, 0),
            style="solid",
            size=(100, 100),
        )

        assert preview.size == (100, 100)
        assert preview.mode == "RGB"
        # 检查边框像素（角落应该是黑色）
        assert preview.getpixel((0, 0)) == (0, 0, 0)

    def test_generate_preview_with_config(
        self, image_service: ImageService
    ) -> None:
        """测试使用配置生成预览."""
        config = BorderConfig.from_rgb(255, 0, 0, width=3, style=BorderStyle.SOLID)
        preview = image_service.generate_border_preview(
            config=config,
            size=(100, 100),
        )

        assert preview.size == (100, 100)
        # 边框应该是红色
        assert preview.getpixel((0, 0)) == (255, 0, 0)

    def test_generate_preview_different_styles(
        self, image_service: ImageService
    ) -> None:
        """测试不同样式的预览."""
        styles = ["solid", "dashed", "dotted", "double"]

        for style in styles:
            preview = image_service.generate_border_preview(
                width=5,
                color=(0, 0, 0),
                style=style,
                size=(100, 100),
            )
            assert preview.size == (100, 100)


class TestGetBorderStyles:
    """测试获取边框样式."""

    def test_get_border_styles(self, image_service: ImageService) -> None:
        """测试获取边框样式列表."""
        styles = image_service.get_border_styles()

        assert len(styles) == 8  # 8 种样式

        # 验证结构
        for style in styles:
            assert "value" in style
            assert "style" in style
            assert "name" in style

        # 验证包含实线样式
        solid = next((s for s in styles if s["value"] == "solid"), None)
        assert solid is not None
        assert solid["name"] == "实线"
