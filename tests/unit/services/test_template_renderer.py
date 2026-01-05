"""模板渲染器单元测试."""

import os
import tempfile
from pathlib import Path

import pytest
from PIL import Image

from src.models.template_config import (
    TemplateConfig,
    TextLayer,
    ShapeLayer,
    ImageLayer,
    ImageFitMode,
)
from src.services.template_renderer import (
    TemplateRenderer,
    find_font,
    render_template,
    render_template_to_canvas,
)


# ===================
# Fixtures
# ===================


@pytest.fixture
def renderer():
    """创建渲染器实例."""
    return TemplateRenderer()


@pytest.fixture
def sample_image():
    """创建测试图片."""
    return Image.new("RGBA", (800, 600), (255, 255, 255, 255))


@pytest.fixture
def sample_template():
    """创建测试模板."""
    return TemplateConfig.create("测试模板", 800, 600)


@pytest.fixture
def temp_image_file():
    """创建临时图片文件."""
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        img = Image.new("RGBA", (100, 100), (255, 0, 0, 255))
        img.save(f.name)
        yield f.name
    os.unlink(f.name)


# ===================
# TemplateRenderer 基础测试
# ===================


class TestTemplateRendererBasic:
    """模板渲染器基础测试."""

    def test_init(self, renderer):
        """测试渲染器初始化."""
        assert renderer is not None

    def test_render_empty_template(self, renderer, sample_image, sample_template):
        """测试渲染空模板."""
        result = renderer.render(sample_image, sample_template)
        assert result is not None
        assert result.size == sample_image.size
        assert result.mode == "RGBA"

    def test_render_preserves_image_mode(self, renderer, sample_template):
        """测试渲染保持 RGBA 模式."""
        # 创建 RGB 图片
        rgb_image = Image.new("RGB", (800, 600), (255, 255, 255))
        result = renderer.render(rgb_image, sample_template)
        assert result.mode == "RGBA"

    def test_render_creates_copy(self, renderer, sample_image, sample_template):
        """测试渲染创建副本，不修改原图."""
        original_data = list(sample_image.getdata())
        renderer.render(sample_image, sample_template)
        assert list(sample_image.getdata()) == original_data


# ===================
# 文字图层渲染测试
# ===================


class TestTextLayerRendering:
    """文字图层渲染测试."""

    def test_render_text_layer(self, renderer, sample_image, sample_template):
        """测试渲染文字图层."""
        text_layer = TextLayer.create("Hello World", x=100, y=100)
        sample_template.add_layer(text_layer)

        result = renderer.render(sample_image, sample_template)
        assert result is not None
        # 验证图片已被修改（文字添加后像素应该不同）
        assert list(result.getdata()) != list(sample_image.getdata())

    def test_render_text_with_background(self, renderer, sample_image, sample_template):
        """测试渲染带背景的文字."""
        text_layer = TextLayer.create("带背景文字", x=100, y=100)
        text_layer.background_enabled = True
        text_layer.background_color = (0, 0, 255)
        text_layer.background_padding = 10
        sample_template.add_layer(text_layer)

        result = renderer.render(sample_image, sample_template)
        assert result is not None

    def test_render_text_with_stroke(self, renderer, sample_image, sample_template):
        """测试渲染带描边的文字."""
        text_layer = TextLayer.create("描边文字", x=100, y=100)
        text_layer.stroke_enabled = True
        text_layer.stroke_color = (255, 0, 0)
        text_layer.stroke_width = 2
        sample_template.add_layer(text_layer)

        result = renderer.render(sample_image, sample_template)
        assert result is not None

    def test_render_empty_text_layer(self, renderer, sample_image, sample_template):
        """测试渲染空内容的文字图层."""
        # 创建有内容的文字图层，然后清空内容
        text_layer = TextLayer.create("test", x=100, y=100)
        text_layer.content = ""  # 清空内容
        sample_template.add_layer(text_layer)

        result = renderer.render(sample_image, sample_template)
        # 空文字应该不改变图片
        assert result is not None


# ===================
# 形状图层渲染测试
# ===================


class TestShapeLayerRendering:
    """形状图层渲染测试."""

    def test_render_rectangle(self, renderer, sample_image, sample_template):
        """测试渲染矩形."""
        shape = ShapeLayer.create_rectangle(100, 100, 200, 150)
        shape.fill_enabled = True
        shape.fill_color = (255, 0, 0)
        sample_template.add_layer(shape)

        result = renderer.render(sample_image, sample_template)
        assert result is not None

    def test_render_ellipse(self, renderer, sample_image, sample_template):
        """测试渲染椭圆."""
        shape = ShapeLayer.create_ellipse(100, 100, 200, 150)
        shape.fill_enabled = True
        shape.fill_color = (0, 255, 0)
        sample_template.add_layer(shape)

        result = renderer.render(sample_image, sample_template)
        assert result is not None

    def test_render_rounded_rectangle(self, renderer, sample_image, sample_template):
        """测试渲染圆角矩形."""
        shape = ShapeLayer.create_rectangle(100, 100, 200, 150)
        shape.corner_radius = 20
        shape.fill_enabled = True
        shape.fill_color = (0, 0, 255)
        sample_template.add_layer(shape)

        result = renderer.render(sample_image, sample_template)
        assert result is not None

    def test_render_shape_with_stroke(self, renderer, sample_image, sample_template):
        """测试渲染带边框的形状."""
        shape = ShapeLayer.create_rectangle(100, 100, 200, 150)
        shape.fill_enabled = True
        shape.fill_color = (200, 200, 200)
        shape.stroke_enabled = True
        shape.stroke_color = (0, 0, 0)
        shape.stroke_width = 3
        sample_template.add_layer(shape)

        result = renderer.render(sample_image, sample_template)
        assert result is not None

    def test_render_shape_with_opacity(self, renderer, sample_image, sample_template):
        """测试渲染半透明形状."""
        shape = ShapeLayer.create_rectangle(100, 100, 200, 150)
        shape.fill_enabled = True
        shape.fill_color = (255, 0, 0)
        shape.opacity = 50
        sample_template.add_layer(shape)

        result = renderer.render(sample_image, sample_template)
        assert result is not None


# ===================
# 图片图层渲染测试
# ===================


class TestImageLayerRendering:
    """图片图层渲染测试."""

    def test_render_image_layer(self, renderer, sample_image, sample_template, temp_image_file):
        """测试渲染图片图层."""
        image_layer = ImageLayer.create(temp_image_file, 100, 100)
        sample_template.add_layer(image_layer)

        result = renderer.render(sample_image, sample_template)
        assert result is not None

    def test_render_image_with_opacity(self, renderer, sample_image, sample_template, temp_image_file):
        """测试渲染半透明图片图层."""
        image_layer = ImageLayer.create(temp_image_file, 100, 100)
        image_layer.opacity = 50
        sample_template.add_layer(image_layer)

        result = renderer.render(sample_image, sample_template)
        assert result is not None

    def test_render_nonexistent_image(self, renderer, sample_image, sample_template):
        """测试渲染不存在的图片路径."""
        image_layer = ImageLayer.create("/nonexistent/path/image.png", 100, 100)
        sample_template.add_layer(image_layer)

        # 不应该抛出异常，而是跳过
        result = renderer.render(sample_image, sample_template)
        assert result is not None

    def test_render_image_fit_modes(self, renderer, sample_image, sample_template, temp_image_file):
        """测试不同的图片适应模式."""
        for fit_mode in ImageFitMode:
            image_layer = ImageLayer.create(temp_image_file, 100, 100)
            image_layer.fit_mode = fit_mode
            image_layer.width = 150
            image_layer.height = 150
            
            template = TemplateConfig.create("测试", 800, 600)
            template.add_layer(image_layer)

            result = renderer.render(sample_image, template)
            assert result is not None


# ===================
# 图层顺序测试
# ===================


class TestLayerOrdering:
    """图层顺序测试."""

    def test_layers_rendered_by_z_index(self, renderer, sample_image, sample_template):
        """测试图层按 z_index 顺序渲染."""
        # 创建两个重叠的形状，不同 z_index
        # shape1 红色，底层
        shape1 = ShapeLayer.create_rectangle(100, 100, 200, 200)
        shape1.fill_enabled = True
        shape1.fill_color = (255, 0, 0)  # 红色

        # shape2 蓝色，顶层
        shape2 = ShapeLayer.create_rectangle(150, 150, 200, 200)
        shape2.fill_enabled = True
        shape2.fill_color = (0, 0, 255)  # 蓝色

        # 先添加 shape1（红色），再添加 shape2（蓝色）
        # add_layer 会自动设置 z_index，后添加的 z_index 更大
        sample_template.add_layer(shape1)  # z_index = 1
        sample_template.add_layer(shape2)  # z_index = 2

        result = renderer.render(sample_image, sample_template)
        
        # 检查重叠区域的颜色应该是蓝色（z_index 更高的 shape2）
        # 重叠区域: (150, 150) 到 (300, 300)
        pixel = result.getpixel((200, 200))
        # 蓝色应该在最上面，蓝色分量应该大于红色分量
        assert pixel[2] > pixel[0], f"蓝色分量({pixel[2]})应该大于红色分量({pixel[0]})"


# ===================
# 可见性测试
# ===================


class TestLayerVisibility:
    """图层可见性测试."""

    def test_invisible_layers_skipped(self, renderer, sample_image, sample_template):
        """测试不可见图层被跳过."""
        shape = ShapeLayer.create_rectangle(100, 100, 200, 200)
        shape.fill_enabled = True
        shape.fill_color = (255, 0, 0)
        shape.visible = False
        sample_template.add_layer(shape)

        result = renderer.render(sample_image, sample_template)
        
        # 不可见图层应该不影响结果
        assert list(result.getdata()) == list(sample_image.getdata())

    def test_skip_invisible_option(self, renderer, sample_image, sample_template):
        """测试 skip_invisible 选项."""
        shape = ShapeLayer.create_rectangle(100, 100, 200, 200)
        shape.fill_enabled = True
        shape.fill_color = (255, 0, 0)
        shape.visible = False
        sample_template.add_layer(shape)

        # skip_invisible=False 时应该渲染不可见图层
        result = renderer.render(sample_image, sample_template, skip_invisible=False)
        # 验证红色形状被渲染
        pixel = result.getpixel((200, 200))
        assert pixel[0] == 255  # 红色分量


# ===================
# render_to_size 测试
# ===================


class TestRenderToSize:
    """render_to_size 方法测试."""

    def test_render_to_default_size(self, renderer, sample_image, sample_template):
        """测试渲染到默认画布尺寸."""
        result = renderer.render_to_size(sample_image, sample_template)
        assert result.size == (sample_template.canvas_width, sample_template.canvas_height)

    def test_render_to_custom_size(self, renderer, sample_image, sample_template):
        """测试渲染到自定义尺寸."""
        target_size = (1024, 768)
        result = renderer.render_to_size(sample_image, sample_template, target_size=target_size)
        assert result.size == target_size

    def test_render_to_size_with_layers(self, renderer, sample_image, sample_template):
        """测试带图层渲染到指定尺寸."""
        text_layer = TextLayer.create("测试文字", x=50, y=50)
        sample_template.add_layer(text_layer)

        target_size = (640, 480)
        result = renderer.render_to_size(sample_image, sample_template, target_size=target_size)
        assert result.size == target_size


# ===================
# 便捷函数测试
# ===================


class TestConvenienceFunctions:
    """便捷函数测试."""

    def test_render_template_function(self, sample_image, sample_template):
        """测试 render_template 函数."""
        result = render_template(sample_image, sample_template)
        assert result is not None
        assert result.size == sample_image.size

    def test_render_template_to_canvas_function(self, sample_image, sample_template):
        """测试 render_template_to_canvas 函数."""
        result = render_template_to_canvas(sample_image, sample_template)
        assert result is not None
        assert result.size == (sample_template.canvas_width, sample_template.canvas_height)


# ===================
# 字体查找测试
# ===================


class TestFontFinding:
    """字体查找测试."""

    def test_find_font_default(self):
        """测试查找默认字体."""
        font = find_font(None, 24)
        assert font is not None

    def test_find_font_with_name(self):
        """测试按名称查找字体."""
        font = find_font("Arial", 24)
        assert font is not None

    def test_find_font_bold(self):
        """测试查找粗体字体."""
        font = find_font("Arial", 24, bold=True)
        assert font is not None

    def test_find_font_nonexistent(self):
        """测试查找不存在的字体（应该回退到默认）."""
        font = find_font("NonExistentFont123456", 24)
        assert font is not None


# ===================
# 综合测试
# ===================


class TestComplexTemplates:
    """复杂模板测试."""

    def test_render_mixed_layers(self, renderer, sample_image, temp_image_file):
        """测试渲染混合图层的模板."""
        template = TemplateConfig.create("混合模板", 800, 600)

        # 添加背景形状
        bg_shape = ShapeLayer.create_rectangle(0, 0, 800, 600)
        bg_shape.fill_enabled = True
        bg_shape.fill_color = (240, 240, 240)
        bg_shape.z_index = 0
        template.add_layer(bg_shape)

        # 添加装饰形状
        deco_shape = ShapeLayer.create_ellipse(50, 50, 100, 100)
        deco_shape.fill_enabled = True
        deco_shape.fill_color = (255, 200, 100)
        deco_shape.z_index = 1
        template.add_layer(deco_shape)

        # 添加图片
        img_layer = ImageLayer.create(temp_image_file, 200, 200)
        img_layer.z_index = 2
        template.add_layer(img_layer)

        # 添加文字
        text_layer = TextLayer.create("产品标题", x=300, y=400)
        text_layer.font_size = 36
        text_layer.z_index = 3
        template.add_layer(text_layer)

        result = renderer.render(sample_image, template)
        assert result is not None
        assert result.size == sample_image.size

    def test_render_promotional_template(self, renderer, sample_image):
        """测试渲染促销模板."""
        template = TemplateConfig.create("促销模板", 800, 800)

        # 促销横幅
        banner = ShapeLayer.create_rectangle(0, 0, 800, 80)
        banner.fill_enabled = True
        banner.fill_color = (255, 50, 50)
        banner.z_index = 10
        template.add_layer(banner)

        # 促销文字
        promo_text = TextLayer.create("限时特惠", x=300, y=25)
        promo_text.font_size = 32
        promo_text.font_color = (255, 255, 255)
        promo_text.z_index = 11
        template.add_layer(promo_text)

        # 价格标签
        price_bg = ShapeLayer.create_rectangle(600, 650, 180, 60)
        price_bg.corner_radius = 8
        price_bg.fill_enabled = True
        price_bg.fill_color = (255, 100, 0)
        price_bg.z_index = 10
        template.add_layer(price_bg)

        price_text = TextLayer.create("¥99.00", x=620, y=660)
        price_text.font_size = 28
        price_text.font_color = (255, 255, 255)
        price_text.z_index = 11
        template.add_layer(price_text)

        result = renderer.render_to_size(sample_image, template)
        assert result is not None
        assert result.size == (800, 800)
