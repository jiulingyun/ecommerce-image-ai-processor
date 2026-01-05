"""模板与图层数据模型单元测试."""

import json
import tempfile
from pathlib import Path

import pytest

from src.models.template_config import (
    # 枚举
    LayerType,
    TextAlign,
    ImageFitMode,
    # 常量
    DEFAULT_CANVAS_SIZE,
    DEFAULT_TEXT_FONT_SIZE,
    DEFAULT_TEXT_COLOR,
    DEFAULT_SHAPE_FILL_COLOR,
    # 图层类
    LayerElement,
    TextLayer,
    ShapeLayer,
    ImageLayer,
    # 模板类
    TemplateConfig,
    # 辅助函数
    generate_layer_id,
    validate_rgb_color,
)


# ===================
# 辅助函数测试
# ===================


class TestGenerateLayerId:
    """测试图层ID生成函数."""

    def test_should_generate_8_char_id(self):
        """生成的ID应为8位字符."""
        layer_id = generate_layer_id()
        assert len(layer_id) == 8

    def test_should_generate_unique_ids(self):
        """多次生成的ID应唯一."""
        ids = [generate_layer_id() for _ in range(100)]
        assert len(set(ids)) == 100

    def test_should_only_contain_hex_chars(self):
        """ID应只包含十六进制字符."""
        layer_id = generate_layer_id()
        assert all(c in "0123456789abcdef" for c in layer_id)


class TestValidateRgbColor:
    """测试RGB颜色验证函数."""

    def test_should_accept_valid_color(self):
        """应接受有效的颜色值."""
        assert validate_rgb_color((0, 0, 0)) == (0, 0, 0)
        assert validate_rgb_color((255, 255, 255)) == (255, 255, 255)
        assert validate_rgb_color((128, 64, 32)) == (128, 64, 32)

    def test_should_reject_invalid_length(self):
        """应拒绝长度不正确的颜色."""
        with pytest.raises(ValueError, match="必须包含3个值"):
            validate_rgb_color((255, 255))  # type: ignore
        with pytest.raises(ValueError, match="必须包含3个值"):
            validate_rgb_color((255, 255, 255, 255))  # type: ignore

    def test_should_reject_out_of_range_values(self):
        """应拒绝超出范围的值."""
        with pytest.raises(ValueError, match="必须在0-255之间"):
            validate_rgb_color((256, 0, 0))
        with pytest.raises(ValueError, match="必须在0-255之间"):
            validate_rgb_color((0, -1, 0))


# ===================
# 文字图层测试
# ===================


class TestTextLayer:
    """测试文字图层."""

    def test_should_create_with_defaults(self):
        """应使用默认值创建."""
        layer = TextLayer()
        assert layer.type == LayerType.TEXT
        assert layer.content == "文字"
        assert layer.font_size == DEFAULT_TEXT_FONT_SIZE
        assert layer.font_color == DEFAULT_TEXT_COLOR
        assert layer.visible is True
        assert layer.locked is False

    def test_should_create_with_custom_values(self):
        """应使用自定义值创建."""
        layer = TextLayer(
            name="标题",
            content="促销活动",
            x=100,
            y=50,
            font_size=36,
            font_color=(255, 0, 0),
            bold=True,
        )
        assert layer.name == "标题"
        assert layer.content == "促销活动"
        assert layer.x == 100
        assert layer.y == 50
        assert layer.font_size == 36
        assert layer.font_color == (255, 0, 0)
        assert layer.bold is True

    def test_create_factory_method(self):
        """测试快速创建工厂方法."""
        layer = TextLayer.create(
            content="Hello",
            x=10,
            y=20,
            font_size=24,
        )
        assert layer.content == "Hello"
        assert layer.x == 10
        assert layer.y == 20
        assert layer.font_size == 24
        assert "文字_Hell" in layer.name

    def test_create_label_factory_method(self):
        """测试标签创建工厂方法."""
        layer = TextLayer.create_label(
            content="HOT",
            x=0,
            y=0,
            font_color=(255, 255, 255),
            background_color=(255, 0, 0),
        )
        assert layer.content == "HOT"
        assert layer.background_enabled is True
        assert layer.background_color == (255, 0, 0)
        assert layer.font_color == (255, 255, 255)

    def test_should_validate_font_size_range(self):
        """应验证字体大小范围."""
        with pytest.raises(ValueError):
            TextLayer(font_size=5)  # 小于最小值8
        with pytest.raises(ValueError):
            TextLayer(font_size=250)  # 大于最大值200

    def test_should_validate_color(self):
        """应验证颜色值."""
        with pytest.raises(ValueError):
            TextLayer(font_color=(300, 0, 0))

    def test_should_serialize_to_dict(self):
        """应能序列化为字典."""
        layer = TextLayer(content="Test", x=100, y=200)
        data = layer.model_dump()
        assert data["content"] == "Test"
        assert data["x"] == 100
        assert data["y"] == 200
        assert data["type"] == LayerType.TEXT

    def test_should_deserialize_from_dict(self):
        """应能从字典反序列化."""
        data = {
            "type": "text",
            "content": "Hello",
            "x": 50,
            "y": 100,
            "font_size": 32,
        }
        layer = TextLayer(**data)
        assert layer.content == "Hello"
        assert layer.x == 50
        assert layer.font_size == 32


# ===================
# 形状图层测试
# ===================


class TestShapeLayer:
    """测试形状图层."""

    def test_should_create_rectangle_by_default(self):
        """默认应创建矩形."""
        layer = ShapeLayer()
        assert layer.type == LayerType.RECTANGLE
        assert layer.is_rectangle is True
        assert layer.is_ellipse is False

    def test_should_create_ellipse(self):
        """应能创建椭圆."""
        layer = ShapeLayer(type=LayerType.ELLIPSE)
        assert layer.type == LayerType.ELLIPSE
        assert layer.is_ellipse is True
        assert layer.is_rectangle is False

    def test_create_rectangle_factory(self):
        """测试矩形创建工厂方法."""
        layer = ShapeLayer.create_rectangle(
            x=10,
            y=20,
            width=200,
            height=100,
            fill_color=(255, 200, 200),
            corner_radius=10,
        )
        assert layer.type == LayerType.RECTANGLE
        assert layer.x == 10
        assert layer.y == 20
        assert layer.width == 200
        assert layer.height == 100
        assert layer.fill_color == (255, 200, 200)
        assert layer.corner_radius == 10

    def test_create_ellipse_factory(self):
        """测试椭圆创建工厂方法."""
        layer = ShapeLayer.create_ellipse(
            x=50,
            y=50,
            width=100,
            height=100,
            fill_color=(200, 200, 255),
        )
        assert layer.type == LayerType.ELLIPSE
        assert layer.width == 100
        assert layer.fill_color == (200, 200, 255)

    def test_should_have_fill_and_stroke_options(self):
        """应支持填充和描边选项."""
        layer = ShapeLayer(
            fill_enabled=True,
            fill_color=(255, 0, 0),
            fill_opacity=80,
            stroke_enabled=True,
            stroke_color=(0, 0, 0),
            stroke_width=2,
        )
        assert layer.fill_enabled is True
        assert layer.fill_opacity == 80
        assert layer.stroke_enabled is True
        assert layer.stroke_width == 2


# ===================
# 图片图层测试
# ===================


class TestImageLayer:
    """测试图片图层."""

    def test_should_create_with_defaults(self):
        """应使用默认值创建."""
        layer = ImageLayer()
        assert layer.type == LayerType.IMAGE
        assert layer.image_path == ""
        assert layer.fit_mode == ImageFitMode.CONTAIN
        assert layer.has_image is False

    def test_should_detect_has_image(self):
        """应检测是否已设置图片."""
        layer = ImageLayer(image_path="/path/to/image.png")
        assert layer.has_image is True

    def test_create_factory_method(self):
        """测试创建工厂方法."""
        layer = ImageLayer.create(
            image_path="/path/to/logo.png",
            x=100,
            y=100,
            width=50,
            height=50,
        )
        assert layer.image_path == "/path/to/logo.png"
        assert layer.name == "logo.png"
        assert layer.x == 100


# ===================
# 图层基类测试
# ===================


class TestLayerElement:
    """测试图层基类功能."""

    def test_bounds_property(self):
        """测试边界框属性."""
        layer = TextLayer(x=100, y=50, width=200, height=100)
        assert layer.bounds == (100, 50, 300, 150)

    def test_center_property(self):
        """测试中心点属性."""
        layer = TextLayer(x=100, y=100, width=200, height=100)
        assert layer.center == (200, 150)

    def test_move_to(self):
        """测试移动到指定位置."""
        layer = TextLayer(x=0, y=0)
        layer.move_to(100, 200)
        assert layer.x == 100
        assert layer.y == 200

    def test_move_to_should_not_go_negative(self):
        """移动不应产生负坐标."""
        layer = TextLayer(x=50, y=50)
        layer.move_to(-10, -20)
        assert layer.x == 0
        assert layer.y == 0

    def test_move_by(self):
        """测试相对移动."""
        layer = TextLayer(x=100, y=100)
        layer.move_by(50, -30)
        assert layer.x == 150
        assert layer.y == 70

    def test_resize(self):
        """测试调整尺寸."""
        layer = TextLayer(width=100, height=100)
        layer.resize(200, 150)
        assert layer.width == 200
        assert layer.height == 150

    def test_resize_minimum(self):
        """调整尺寸最小为1."""
        layer = TextLayer(width=100, height=100)
        layer.resize(0, -10)
        assert layer.width == 1
        assert layer.height == 1

    def test_clone(self):
        """测试克隆图层."""
        original = TextLayer(name="Original", content="Test", x=100, y=200)
        cloned = original.clone()

        # 应有新ID
        assert cloned.id != original.id
        # 内容应相同
        assert cloned.content == original.content
        assert cloned.x == original.x
        # 名称应标记为副本
        assert "_副本" in cloned.name


# ===================
# 模板配置测试
# ===================


class TestTemplateConfig:
    """测试模板配置."""

    def test_should_create_with_defaults(self):
        """应使用默认值创建."""
        template = TemplateConfig()
        assert template.canvas_width == DEFAULT_CANVAS_SIZE[0]
        assert template.canvas_height == DEFAULT_CANVAS_SIZE[1]
        assert template.layer_count == 0
        assert template.is_preset is False

    def test_should_create_with_custom_values(self):
        """应使用自定义值创建."""
        template = TemplateConfig(
            name="促销模板",
            canvas_width=1000,
            canvas_height=1000,
            description="用于促销活动的模板",
        )
        assert template.name == "促销模板"
        assert template.canvas_size == (1000, 1000)
        assert template.description == "用于促销活动的模板"

    def test_create_factory_method(self):
        """测试创建工厂方法."""
        template = TemplateConfig.create(
            name="测试模板",
            width=1200,
            height=800,
        )
        assert template.name == "测试模板"
        assert template.canvas_width == 1200
        assert template.canvas_height == 800

    def test_add_layer(self):
        """测试添加图层."""
        template = TemplateConfig()
        text = TextLayer.create("Hello")
        template.add_layer(text)

        assert template.layer_count == 1

    def test_add_multiple_layers_auto_z_index(self):
        """添加多个图层应自动设置z_index."""
        template = TemplateConfig()
        layer1 = TextLayer.create("First")
        layer2 = TextLayer.create("Second")
        layer3 = ShapeLayer.create_rectangle()

        template.add_layer(layer1)
        template.add_layer(layer2)
        template.add_layer(layer3)

        layers = template.get_layers()
        assert layers[0].z_index == 0
        assert layers[1].z_index == 1
        assert layers[2].z_index == 2

    def test_get_layer_by_id(self):
        """测试根据ID获取图层."""
        template = TemplateConfig()
        text = TextLayer.create("Test")
        template.add_layer(text)

        found = template.get_layer_by_id(text.id)
        assert found is not None
        assert found.id == text.id

    def test_get_layer_by_id_not_found(self):
        """获取不存在的图层应返回None."""
        template = TemplateConfig()
        assert template.get_layer_by_id("nonexistent") is None

    def test_remove_layer(self):
        """测试删除图层."""
        template = TemplateConfig()
        text = TextLayer.create("Test")
        template.add_layer(text)

        result = template.remove_layer(text.id)
        assert result is True
        assert template.layer_count == 0

    def test_remove_nonexistent_layer(self):
        """删除不存在的图层应返回False."""
        template = TemplateConfig()
        result = template.remove_layer("nonexistent")
        assert result is False

    def test_update_layer(self):
        """测试更新图层."""
        template = TemplateConfig()
        text = TextLayer.create("Original")
        template.add_layer(text)

        # 修改图层
        text.content = "Updated"
        text.x = 500
        result = template.update_layer(text)

        assert result is True
        updated = template.get_layer_by_id(text.id)
        assert updated is not None
        assert updated.content == "Updated"
        assert updated.x == 500

    def test_get_layers_sorted(self):
        """测试获取排序后的图层列表."""
        template = TemplateConfig()

        layer1 = TextLayer.create("First")
        layer1.z_index = 10
        layer2 = TextLayer.create("Second")
        layer2.z_index = 5
        layer3 = TextLayer.create("Third")
        layer3.z_index = 20

        template.layers.append(layer1.model_dump())
        template.layers.append(layer2.model_dump())
        template.layers.append(layer3.model_dump())

        sorted_layers = template.get_layers_sorted()
        assert sorted_layers[0].z_index == 5
        assert sorted_layers[1].z_index == 10
        assert sorted_layers[2].z_index == 20

    def test_clear_layers(self):
        """测试清空图层."""
        template = TemplateConfig()
        template.add_layer(TextLayer.create("Test1"))
        template.add_layer(TextLayer.create("Test2"))

        template.clear_layers()
        assert template.layer_count == 0


# ===================
# 序列化/反序列化测试
# ===================


class TestTemplateSerialization:
    """测试模板序列化和反序列化."""

    def test_to_json(self):
        """测试序列化为JSON."""
        template = TemplateConfig(name="Test")
        template.add_layer(TextLayer.create("Hello"))

        json_str = template.to_json()
        data = json.loads(json_str)

        assert data["name"] == "Test"
        assert len(data["layers"]) == 1
        assert data["layers"][0]["content"] == "Hello"

    def test_from_json(self):
        """测试从JSON反序列化."""
        json_str = json.dumps({
            "name": "Loaded",
            "canvas_width": 1000,
            "canvas_height": 800,
            "layers": [
                {"type": "text", "content": "Test", "x": 100, "y": 50}
            ],
        })

        template = TemplateConfig.from_json(json_str)
        assert template.name == "Loaded"
        assert template.canvas_width == 1000
        assert template.layer_count == 1

    def test_roundtrip_serialization(self):
        """测试序列化往返."""
        original = TemplateConfig(name="Original", canvas_width=1200)
        original.add_layer(TextLayer.create("Text1", x=100, y=50))
        original.add_layer(ShapeLayer.create_rectangle(x=200, y=200))

        json_str = original.to_json()
        restored = TemplateConfig.from_json(json_str)

        assert restored.name == original.name
        assert restored.canvas_width == original.canvas_width
        assert restored.layer_count == original.layer_count

    def test_save_and_load_file(self):
        """测试保存和加载文件."""
        template = TemplateConfig(name="FileTest")
        template.add_layer(TextLayer.create("FileContent"))

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            template.save_to_file(temp_path)
            loaded = TemplateConfig.from_file(temp_path)

            assert loaded.name == "FileTest"
            assert loaded.layer_count == 1
        finally:
            Path(temp_path).unlink(missing_ok=True)


# ===================
# 图层类型反序列化测试
# ===================


class TestLayerDeserialization:
    """测试不同类型图层的反序列化."""

    def test_deserialize_text_layer(self):
        """测试反序列化文字图层."""
        template = TemplateConfig()
        template.layers.append({
            "type": "text",
            "content": "Hello",
            "font_size": 32,
        })

        layers = template.get_layers()
        assert len(layers) == 1
        assert isinstance(layers[0], TextLayer)
        assert layers[0].content == "Hello"

    def test_deserialize_rectangle_layer(self):
        """测试反序列化矩形图层."""
        template = TemplateConfig()
        template.layers.append({
            "type": "rectangle",
            "width": 200,
            "height": 100,
            "fill_color": (255, 0, 0),
        })

        layers = template.get_layers()
        assert len(layers) == 1
        assert isinstance(layers[0], ShapeLayer)
        assert layers[0].is_rectangle is True

    def test_deserialize_ellipse_layer(self):
        """测试反序列化椭圆图层."""
        template = TemplateConfig()
        template.layers.append({
            "type": "ellipse",
            "width": 100,
            "height": 100,
        })

        layers = template.get_layers()
        assert len(layers) == 1
        assert isinstance(layers[0], ShapeLayer)
        assert layers[0].is_ellipse is True

    def test_deserialize_image_layer(self):
        """测试反序列化图片图层."""
        template = TemplateConfig()
        template.layers.append({
            "type": "image",
            "image_path": "/path/to/image.png",
        })

        layers = template.get_layers()
        assert len(layers) == 1
        assert isinstance(layers[0], ImageLayer)
        assert layers[0].image_path == "/path/to/image.png"

    def test_skip_invalid_layer(self):
        """应跳过无效的图层数据."""
        template = TemplateConfig()
        template.layers.append({"invalid": "data"})
        template.layers.append({"type": "unknown_type"})

        layers = template.get_layers()
        assert len(layers) == 0
