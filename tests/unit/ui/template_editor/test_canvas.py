"""画布视图单元测试."""

import pytest
from unittest.mock import MagicMock, patch

from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtWidgets import QApplication

from src.models.template_config import (
    TemplateConfig,
    TextLayer,
    ShapeLayer,
    ImageLayer,
)
from src.ui.widgets.template_editor.canvas import (
    TemplateCanvas,
    TemplateScene,
    GRID_SIZE,
    MIN_ZOOM,
    MAX_ZOOM,
    ZOOM_STEP,
)


# ===================
# 场景测试
# ===================


class TestTemplateScene:
    """测试模板场景."""

    def test_should_initialize_with_canvas_size(self, app):
        """应以画布尺寸初始化."""
        scene = TemplateScene(800, 600)
        assert scene._canvas_width == 800
        assert scene._canvas_height == 600

    def test_should_have_grid_enabled_by_default(self, app):
        """默认应启用网格."""
        scene = TemplateScene(800, 600)
        assert scene._show_grid is True

    def test_should_toggle_grid(self, app):
        """应能切换网格显示."""
        scene = TemplateScene(800, 600)
        scene.set_show_grid(False)
        assert scene._show_grid is False

        scene.set_show_grid(True)
        assert scene._show_grid is True

    def test_should_update_canvas_size(self, app):
        """应能更新画布尺寸."""
        scene = TemplateScene(800, 600)
        scene.set_canvas_size(1920, 1080)
        assert scene._canvas_width == 1920
        assert scene._canvas_height == 1080


# ===================
# 画布视图测试
# ===================


class TestTemplateCanvas:
    """测试模板画布."""

    def test_should_initialize_without_template(self, app):
        """初始化时应无模板."""
        canvas = TemplateCanvas()
        assert canvas._template is None

    def test_should_set_custom_template(self, app):
        """应能设置自定义模板."""
        template = TemplateConfig(canvas_width=1000, canvas_height=800)
        canvas = TemplateCanvas()
        canvas.set_template(template)
        assert canvas._template is template

    def test_should_have_zoom_at_one(self, app):
        """初始缩放应为1."""
        canvas = TemplateCanvas()
        assert canvas._zoom_level == 1.0

    def test_should_have_empty_layer_items(self, app):
        """初始图层项应为空."""
        canvas = TemplateCanvas()
        assert len(canvas._layer_items) == 0


# ===================
# 图层管理测试
# ===================


class TestTemplateCanvasLayerManagement:
    """测试画布图层管理."""

    def test_should_add_text_layer(self, app):
        """应能添加文字图层."""
        canvas = TemplateCanvas()
        canvas.set_template(TemplateConfig())
        layer = TextLayer.create("Test")
        canvas.add_layer(layer)

        assert layer.id in canvas._layer_items
        assert len(canvas._template.layers) == 1

    def test_should_add_shape_layer(self, app):
        """应能添加形状图层."""
        canvas = TemplateCanvas()
        canvas.set_template(TemplateConfig())
        layer = ShapeLayer.create_rectangle()
        canvas.add_layer(layer)

        assert layer.id in canvas._layer_items

    def test_should_add_image_layer(self, app):
        """应能添加图片图层."""
        canvas = TemplateCanvas()
        canvas.set_template(TemplateConfig())
        layer = ImageLayer.create("/path/to/image.png")
        canvas.add_layer(layer)

        assert layer.id in canvas._layer_items

    def test_should_remove_layer(self, app):
        """应能移除图层."""
        canvas = TemplateCanvas()
        canvas.set_template(TemplateConfig())
        layer = TextLayer.create("Test")
        canvas.add_layer(layer)
        canvas.remove_layer(layer.id)

        assert layer.id not in canvas._layer_items
        assert len(canvas._template.layers) == 0

    def test_should_get_layer_item(self, app):
        """应能获取图层项."""
        canvas = TemplateCanvas()
        canvas.set_template(TemplateConfig())
        layer = TextLayer.create("Test")
        canvas.add_layer(layer)

        item = canvas.get_layer_item(layer.id)
        assert item is not None
        assert item.layer_id == layer.id

    def test_should_return_none_for_nonexistent_layer(self, app):
        """不存在的图层应返回None."""
        canvas = TemplateCanvas()
        item = canvas.get_layer_item("nonexistent")
        assert item is None

    def test_should_update_layer(self, app):
        """应能更新图层."""
        canvas = TemplateCanvas()
        canvas.set_template(TemplateConfig())
        layer = TextLayer(x=0, y=0)
        canvas.add_layer(layer)

        layer.x = 100
        layer.y = 200
        canvas.update_layer(layer.id)

        item = canvas.get_layer_item(layer.id)
        assert item.pos().x() == 100
        assert item.pos().y() == 200


# ===================
# 缩放测试
# ===================


class TestTemplateCanvasZoom:
    """测试画布缩放."""

    def test_should_zoom_in(self, app):
        """应能放大."""
        canvas = TemplateCanvas()
        initial_zoom = canvas._zoom_level
        canvas.zoom_in()
        assert canvas._zoom_level > initial_zoom

    def test_should_zoom_out(self, app):
        """应能缩小."""
        canvas = TemplateCanvas()
        initial_zoom = canvas._zoom_level
        canvas.zoom_out()
        assert canvas._zoom_level < initial_zoom

    def test_should_not_exceed_max_zoom(self, app):
        """不应超过最大缩放."""
        canvas = TemplateCanvas()
        for _ in range(100):
            canvas.zoom_in()
        assert canvas._zoom_level <= MAX_ZOOM

    def test_should_not_go_below_min_zoom(self, app):
        """不应低于最小缩放."""
        canvas = TemplateCanvas()
        for _ in range(100):
            canvas.zoom_out()
        assert canvas._zoom_level >= MIN_ZOOM

    def test_should_reset_zoom(self, app):
        """应能重置缩放."""
        canvas = TemplateCanvas()
        canvas.zoom_in()
        canvas.zoom_in()
        canvas.zoom_reset()
        assert canvas._zoom_level == 1.0

    def test_should_set_zoom_level(self, app):
        """应能设置缩放级别."""
        canvas = TemplateCanvas()
        canvas.set_zoom(2.0)
        assert canvas._zoom_level == 2.0

    def test_should_clamp_zoom_level(self, app):
        """应限制缩放级别范围."""
        canvas = TemplateCanvas()
        canvas.set_zoom(10.0)
        assert canvas._zoom_level == MAX_ZOOM

        canvas.set_zoom(0.01)
        assert canvas._zoom_level == MIN_ZOOM


# ===================
# 选择测试
# ===================


class TestTemplateCanvasSelection:
    """测试画布选择功能."""

    def test_should_select_layer(self, app):
        """应能选择图层."""
        canvas = TemplateCanvas()
        canvas.set_template(TemplateConfig())
        layer = TextLayer.create("Test")
        canvas.add_layer(layer)
        canvas.select_layer(layer.id)

        item = canvas.get_layer_item(layer.id)
        assert item.isSelected()

    def test_should_deselect_all(self, app):
        """应能取消所有选择."""
        canvas = TemplateCanvas()
        canvas.set_template(TemplateConfig())
        layer1 = TextLayer.create("Test1")
        layer2 = TextLayer.create("Test2")
        canvas.add_layer(layer1)
        canvas.add_layer(layer2)

        canvas.select_layer(layer1.id)
        canvas.select_layer(layer2.id)
        canvas.deselect_all()

        item1 = canvas.get_layer_item(layer1.id)
        item2 = canvas.get_layer_item(layer2.id)
        assert not item1.isSelected()
        assert not item2.isSelected()

    def test_should_get_selected_layers(self, app):
        """应能获取已选图层."""
        canvas = TemplateCanvas()
        canvas.set_template(TemplateConfig())
        layer1 = TextLayer.create("Test1")
        layer2 = TextLayer.create("Test2")
        canvas.add_layer(layer1)
        canvas.add_layer(layer2)

        canvas.select_layer(layer1.id)
        selected = canvas.selected_layers

        assert layer1.id in selected
        assert layer2.id not in selected


# ===================
# 模板操作测试
# ===================


class TestTemplateCanvasTemplateOperations:
    """测试模板操作."""

    def test_should_set_template(self, app):
        """应能设置模板."""
        canvas = TemplateCanvas()
        new_template = TemplateConfig(canvas_width=1920, canvas_height=1080)
        new_template.add_layer(TextLayer.create("New"))

        canvas.set_template(new_template)

        assert canvas._template is new_template
        assert len(canvas._layer_items) == 1

    def test_should_clear_old_layers_on_set_template(self, app):
        """设置新模板应清除旧图层."""
        canvas = TemplateCanvas()
        canvas.set_template(TemplateConfig())
        canvas.add_layer(TextLayer.create("Old"))

        new_template = TemplateConfig()
        canvas.set_template(new_template)

        assert len(canvas._layer_items) == 0

    def test_should_get_template(self, app):
        """应能获取模板."""
        template = TemplateConfig(canvas_width=1000)
        canvas = TemplateCanvas()
        canvas.set_template(template)
        assert canvas.template is template


# ===================
# 网格显示测试
# ===================


class TestTemplateCanvasGrid:
    """测试网格显示."""

    def test_should_have_grid_visible_by_default(self, app):
        """默认应显示网格."""
        canvas = TemplateCanvas()
        assert canvas.show_grid is True

    def test_should_toggle_grid(self, app):
        """应能切换网格."""
        canvas = TemplateCanvas()
        canvas.set_show_grid(False)
        assert canvas.show_grid is False

        canvas.set_show_grid(True)
        assert canvas.show_grid is True


# ===================
# 信号测试
# ===================


class TestTemplateCanvasSignals:
    """测试画布信号."""

    def test_should_have_signals(self, app):
        """应有信号."""
        canvas = TemplateCanvas()
        assert hasattr(canvas, "layer_selected")
        assert hasattr(canvas, "layer_deselected")
        assert hasattr(canvas, "layer_moved")
        assert hasattr(canvas, "layer_resized")
        assert hasattr(canvas, "selection_changed")
        assert hasattr(canvas, "zoom_changed")

    def test_should_emit_zoom_changed_on_zoom_in(self, app):
        """放大时应发出zoom_changed信号."""
        canvas = TemplateCanvas()
        signal_received = []

        def on_zoom_changed(level):
            signal_received.append(level)

        canvas.zoom_changed.connect(on_zoom_changed)
        canvas.zoom_in()

        assert len(signal_received) == 1
        assert signal_received[0] > 1.0

    def test_should_emit_zoom_changed_on_zoom_out(self, app):
        """缩小时应发出zoom_changed信号."""
        canvas = TemplateCanvas()
        signal_received = []

        def on_zoom_changed(level):
            signal_received.append(level)

        canvas.zoom_changed.connect(on_zoom_changed)
        canvas.zoom_out()

        assert len(signal_received) == 1
        assert signal_received[0] < 1.0
