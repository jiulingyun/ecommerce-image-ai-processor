"""商品合成处理器单元测试."""

from __future__ import annotations

import io
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from PIL import Image

from src.core.composite_processor import (
    CompositeConfig,
    CompositeMode,
    CompositePosition,
    CompositeProcessor,
    SceneType,
    composite_product,
)
from src.services.ai_service import AIService
from src.utils.exceptions import ImageProcessError


# ===================
# Fixtures
# ===================
@pytest.fixture
def temp_dir():
    """创建临时目录."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_background_path(temp_dir: Path) -> Path:
    """创建测试用背景图片."""
    img = Image.new("RGB", (800, 600), (100, 150, 200))
    path = temp_dir / "background.jpg"
    img.save(path)
    return path


@pytest.fixture
def sample_product_path(temp_dir: Path) -> Path:
    """创建测试用商品图片."""
    img = Image.new("RGBA", (200, 200), (255, 0, 0, 255))
    path = temp_dir / "product.png"
    img.save(path)
    return path


@pytest.fixture
def sample_result_bytes() -> bytes:
    """生成模拟的 AI 合成结果."""
    img = Image.new("RGBA", (800, 600), (0, 255, 0, 255))
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture
def mock_ai_service(sample_result_bytes: bytes) -> MagicMock:
    """创建模拟的 AI 服务."""
    mock = MagicMock(spec=AIService)
    mock.composite_product = AsyncMock(return_value=sample_result_bytes)
    return mock


@pytest.fixture
def processor(mock_ai_service: MagicMock) -> CompositeProcessor:
    """创建合成处理器实例."""
    return CompositeProcessor(ai_service=mock_ai_service)


# ===================
# 位置计算测试
# ===================
class TestPositionCalculation:
    """测试位置计算功能."""

    def test_calculate_position_center(self, processor: CompositeProcessor) -> None:
        """测试居中位置计算."""
        bg = Image.new("RGB", (800, 600))
        prod = Image.new("RGBA", (200, 200))
        config = CompositeConfig(mode=CompositeMode.CENTER)

        position = processor._calculate_position(bg, prod, config)

        # 商品应该在中心位置
        expected_w = int(800 * 0.3)  # (0.5 + 0.1) / 2 = 0.3
        assert position.width > 0
        assert position.height > 0
        # 中心对齐
        center_x = position.x + position.width // 2
        center_y = position.y + position.height // 2
        assert abs(center_x - 400) < position.width  # 接近水平中心
        assert abs(center_y - 300) < position.height  # 接近垂直中心

    def test_calculate_position_left(self, processor: CompositeProcessor) -> None:
        """测试左侧位置计算."""
        bg = Image.new("RGB", (800, 600))
        prod = Image.new("RGBA", (200, 200))
        config = CompositeConfig(mode=CompositeMode.LEFT)

        position = processor._calculate_position(bg, prod, config)

        # X 应该靠近左边
        assert position.x < 800 // 2

    def test_calculate_position_right(self, processor: CompositeProcessor) -> None:
        """测试右侧位置计算."""
        bg = Image.new("RGB", (800, 600))
        prod = Image.new("RGBA", (200, 200))
        config = CompositeConfig(mode=CompositeMode.RIGHT)

        position = processor._calculate_position(bg, prod, config)

        # X + width 应该靠近右边
        assert position.x + position.width > 800 // 2

    def test_calculate_position_custom(self, processor: CompositeProcessor) -> None:
        """测试自定义位置."""
        bg = Image.new("RGB", (800, 600))
        prod = Image.new("RGBA", (200, 200))
        custom_pos = CompositePosition(x=100, y=100, width=150, height=150)
        config = CompositeConfig(mode=CompositeMode.CUSTOM, position=custom_pos)

        position = processor._calculate_position(bg, prod, config)

        assert position == custom_pos

    def test_calculate_target_size_maintains_aspect(
        self, processor: CompositeProcessor
    ) -> None:
        """测试目标尺寸计算保持纵横比."""
        config = CompositeConfig(maintain_aspect_ratio=True)

        target_w, target_h = processor._calculate_target_size(
            800, 600, 200, 100, config
        )

        # 检查纵横比保持
        original_ratio = 200 / 100
        result_ratio = target_w / target_h
        assert abs(original_ratio - result_ratio) < 0.1


# ===================
# 提示词构建测试
# ===================
class TestPromptBuilding:
    """测试提示词构建功能."""

    def test_build_prompt_basic(self, processor: CompositeProcessor) -> None:
        """测试基本提示词构建."""
        config = CompositeConfig(mode=CompositeMode.CENTER)
        position = CompositePosition(x=0, y=0, width=100, height=100)

        prompt = processor._build_composite_prompt(config, position)

        assert "composite" in prompt.lower()
        assert "product" in prompt.lower()

    def test_build_prompt_with_scene_type(
        self, processor: CompositeProcessor
    ) -> None:
        """测试带场景类型的提示词."""
        config = CompositeConfig(
            mode=CompositeMode.CENTER, scene_type=SceneType.INDOOR
        )
        position = CompositePosition(x=0, y=0, width=100, height=100)

        prompt = processor._build_composite_prompt(config, position)

        assert "indoor" in prompt.lower()

    def test_build_prompt_custom(self, processor: CompositeProcessor) -> None:
        """测试自定义提示词."""
        custom = "My custom prompt"
        config = CompositeConfig(custom_prompt=custom)
        position = CompositePosition(x=0, y=0, width=100, height=100)

        prompt = processor._build_composite_prompt(config, position)

        assert prompt == custom

    def test_build_prompt_with_shadow(self, processor: CompositeProcessor) -> None:
        """测试带阴影的提示词."""
        config = CompositeConfig(shadow_enabled=True)
        position = CompositePosition(x=0, y=0, width=100, height=100)

        prompt = processor._build_composite_prompt(config, position)

        assert "shadow" in prompt.lower()

    def test_build_prompt_with_reflection(
        self, processor: CompositeProcessor
    ) -> None:
        """测试带反射的提示词."""
        config = CompositeConfig(reflection_enabled=True)
        position = CompositePosition(x=0, y=0, width=100, height=100)

        prompt = processor._build_composite_prompt(config, position)

        assert "reflection" in prompt.lower()


# ===================
# 合成测试
# ===================
class TestComposite:
    """测试合成功能."""

    @pytest.mark.asyncio
    async def test_composite_success(
        self,
        processor: CompositeProcessor,
        sample_background_path: Path,
        sample_product_path: Path,
        temp_dir: Path,
    ) -> None:
        """测试成功合成."""
        output_path = temp_dir / "output.png"

        result = await processor.composite(
            background=sample_background_path,
            product=sample_product_path,
            output_path=output_path,
        )

        assert result == output_path
        assert output_path.exists()
        processor.ai_service.composite_product.assert_called_once()

    @pytest.mark.asyncio
    async def test_composite_returns_bytes(
        self,
        processor: CompositeProcessor,
        sample_background_path: Path,
        sample_product_path: Path,
    ) -> None:
        """测试返回字节数据."""
        result = await processor.composite(
            background=sample_background_path,
            product=sample_product_path,
            output_path=None,
        )

        assert isinstance(result, bytes)
        # 验证是有效的图片
        img = Image.open(io.BytesIO(result))
        assert img.size[0] > 0

    @pytest.mark.asyncio
    async def test_composite_with_config(
        self,
        processor: CompositeProcessor,
        sample_background_path: Path,
        sample_product_path: Path,
    ) -> None:
        """测试使用配置合成."""
        config = CompositeConfig(
            mode=CompositeMode.LEFT,
            scene_type=SceneType.STUDIO,
            shadow_enabled=True,
        )

        await processor.composite(
            background=sample_background_path,
            product=sample_product_path,
            config=config,
        )

        call_kwargs = processor.ai_service.composite_product.call_args[1]
        assert call_kwargs["position_hint"] == "left"

    @pytest.mark.asyncio
    async def test_composite_with_progress(
        self,
        processor: CompositeProcessor,
        sample_background_path: Path,
        sample_product_path: Path,
    ) -> None:
        """测试进度回调."""
        progress_updates = []

        def on_progress(progress: int, message: str) -> None:
            progress_updates.append((progress, message))

        await processor.composite(
            background=sample_background_path,
            product=sample_product_path,
            on_progress=on_progress,
        )

        assert len(progress_updates) > 0
        assert progress_updates[-1][0] == 100

    @pytest.mark.asyncio
    async def test_composite_from_bytes(
        self,
        processor: CompositeProcessor,
    ) -> None:
        """测试从字节数据合成."""
        # 创建测试图片字节
        bg_img = Image.new("RGB", (400, 300), (100, 100, 100))
        bg_buffer = io.BytesIO()
        bg_img.save(bg_buffer, format="PNG")
        bg_bytes = bg_buffer.getvalue()

        prod_img = Image.new("RGBA", (100, 100), (255, 0, 0, 255))
        prod_buffer = io.BytesIO()
        prod_img.save(prod_buffer, format="PNG")
        prod_bytes = prod_buffer.getvalue()

        result = await processor.composite(
            background=bg_bytes,
            product=prod_bytes,
        )

        assert isinstance(result, bytes)


# ===================
# 批量合成测试
# ===================
class TestBatchComposite:
    """测试批量合成功能."""

    @pytest.mark.asyncio
    async def test_batch_composite(
        self,
        processor: CompositeProcessor,
        sample_background_path: Path,
        sample_product_path: Path,
        temp_dir: Path,
    ) -> None:
        """测试批量合成."""
        items = [
            (sample_background_path, sample_product_path),
            (sample_background_path, sample_product_path),
        ]
        output_dir = temp_dir / "batch_output"

        results = await processor.batch_composite(items, output_dir)

        assert len(results) == 2
        assert all(isinstance(r, Path) for r in results)
        assert all(r.exists() for r in results)

    @pytest.mark.asyncio
    async def test_batch_composite_with_progress(
        self,
        processor: CompositeProcessor,
        sample_background_path: Path,
        sample_product_path: Path,
        temp_dir: Path,
    ) -> None:
        """测试批量合成进度回调."""
        items = [
            (sample_background_path, sample_product_path),
        ]
        output_dir = temp_dir / "batch_output"
        progress_updates = []

        def on_progress(current: int, total: int, message: str) -> None:
            progress_updates.append((current, total, message))

        await processor.batch_composite(items, output_dir, on_progress=on_progress)

        assert len(progress_updates) > 0
        assert progress_updates[-1][0] == 1
        assert progress_updates[-1][1] == 1


# ===================
# 便捷函数测试
# ===================
class TestConvenienceFunction:
    """测试便捷函数."""

    @pytest.mark.asyncio
    async def test_composite_product_function(
        self,
        sample_background_path: Path,
        sample_product_path: Path,
        sample_result_bytes: bytes,
    ) -> None:
        """测试 composite_product 便捷函数."""
        with patch(
            "src.core.composite_processor.get_ai_service"
        ) as mock_get:
            mock_service = MagicMock(spec=AIService)
            mock_service.composite_product = AsyncMock(
                return_value=sample_result_bytes
            )
            mock_get.return_value = mock_service

            result = await composite_product(
                background=sample_background_path,
                product=sample_product_path,
                mode=CompositeMode.CENTER,
            )

            assert isinstance(result, bytes)


# ===================
# 辅助方法测试
# ===================
class TestHelperMethods:
    """测试辅助方法."""

    def test_get_position_description(
        self, processor: CompositeProcessor
    ) -> None:
        """测试位置描述获取."""
        assert "center" in processor._get_position_description(CompositeMode.CENTER)
        assert "left" in processor._get_position_description(CompositeMode.LEFT)
        assert "right" in processor._get_position_description(CompositeMode.RIGHT)

    def test_get_position_hint(self, processor: CompositeProcessor) -> None:
        """测试位置提示获取."""
        assert processor._get_position_hint(CompositeMode.CENTER) == "center"
        assert processor._get_position_hint(CompositeMode.LEFT) == "left"
        assert processor._get_position_hint(CompositeMode.AUTO) == "auto"

    def test_get_scene_hints(self, processor: CompositeProcessor) -> None:
        """测试场景提示获取."""
        indoor_hint = processor._get_scene_hints(SceneType.INDOOR)
        assert "indoor" in indoor_hint.lower()

        outdoor_hint = processor._get_scene_hints(SceneType.OUTDOOR)
        assert "outdoor" in outdoor_hint.lower()
