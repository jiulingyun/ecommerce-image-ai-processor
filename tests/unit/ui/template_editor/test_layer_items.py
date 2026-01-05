"""图层图形项单元测试."""

import pytest
from unittest.mock import MagicMock, patch

from src.models.template_config import (
    TextLayer,
    ShapeLayer,
    ImageLayer,
    LayerType,
)
from src.ui.widgets.template_editor.layer_items import (
    LayerGraphicsItem,
    TextLayerItem,
    ShapeLayerItem,
    ImageLayerItem,
    create_layer_item,
    HandlePosition,
    HANDLE_SIZE,
)


# ===================
# 工厂函数测试
# ===================


class TestCreateLayerItem:
    """测试图层项工厂函数."""

    def test_should_create_text_layer_item(self, app):
        """应创建文字图层项."""
        layer = TextLayer.create("Test")
        item = create_layer_item(layer)
        assert isinstance(item, TextLayerItem)
        assert item.layer_id == layer.id

    def test_should_create_shape_layer_item_for_rectangle(self, app):
        """应为矩形创建形状图层项."""
        layer = ShapeLayer.create_rectangle()
        item = create_layer_item(layer)
        assert isinstance(item, ShapeLayerItem)
        assert item.layer_type == LayerType.RECTANGLE

    def test_should_create_shape_layer_item_for_ellipse(self, app):
        """应为椭圆创建形状图层项."""
        layer = ShapeLayer.create_ellipse()
        item = create_layer_item(layer)
        assert isinstance(item, ShapeLayerItem)
        assert item.layer_type == LayerType.ELLIPSE

    def test_should_create_image_layer_item(self, app):
        """应创建图片图层项."""
        layer = ImageLayer.create("/path/to/image.png")
        item = create_layer_item(layer)
        assert isinstance(item, ImageLayerItem)


# ===================
# 图层基类测试
# ===================


class TestLayerGraphicsItem:
    """测试图层图形项基类."""

    def test_should_initialize_from_layer(self, app):
        """应从图层数据初始化."""
        layer = TextLayer(x=100, y=50, width=200, height=100, z_index=5)
        item = TextLayerItem(layer)

        assert item.layer_id == layer.id
        assert item.layer_type == LayerType.TEXT
        assert item.pos().x() == 100
        assert item.pos().y() == 50
        assert item.zValue() == 5

    def test_should_reflect_visibility(self, app):
        """应反映可见性."""
        layer = TextLayer(visible=False)
        item = TextLayerItem(layer)
        assert not item.isVisible()

    def test_should_reflect_opacity(self, app):
        """应反映透明度."""
        layer = TextLayer(opacity=50)
        item = TextLayerItem(layer)
        assert item.opacity() == 0.5

    def test_should_be_movable_when_not_locked(self, app):
        """未锁定时应可移动."""
        layer = TextLayer(locked=False)
        item = TextLayerItem(layer)
        from PyQt6.QtWidgets import QGraphicsItem
        assert item.flags() & QGraphicsItem.GraphicsItemFlag.ItemIsMovable

    def test_should_not_be_movable_when_locked(self, app):
        """锁定时不应可移动."""
        layer = TextLayer(locked=True)
        item = TextLayerItem(layer)
        from PyQt6.QtWidgets import QGraphicsItem
        assert not (item.flags() & QGraphicsItem.GraphicsItemFlag.ItemIsMovable)

    def test_bounding_rect_should_include_layer_size(self, app):
        """边界矩形应包含图层尺寸."""
        layer = TextLayer(width=100, height=50)
        item = TextLayerItem(layer)
        rect = item.boundingRect()
        assert rect.width() >= 100
        assert rect.height() >= 50

    def test_update_from_layer_should_sync_position(self, app):
        """update_from_layer应同步位置."""
        layer = TextLayer(x=0, y=0)
        item = TextLayerItem(layer)

        layer.x = 200
        layer.y = 150
        layer.z_index = 10
        item.update_from_layer()

        assert item.pos().x() == 200
        assert item.pos().y() == 150
        assert item.zValue() == 10

    def test_sync_to_layer_should_update_model(self, app):
        """sync_to_layer应更新模型."""
        layer = TextLayer(x=0, y=0)
        item = TextLayerItem(layer)
        item.setPos(100, 200)
        item.sync_to_layer()

        assert layer.x == 100
        assert layer.y == 200


# ===================
# 文字图层项测试
# ===================


class TestTextLayerItem:
    """测试文字图层图形项."""

    def test_should_have_text_layer_reference(self, app):
        """应有文字图层引用."""
        layer = TextLayer(content="Test")
        item = TextLayerItem(layer)
        assert item.text_layer is layer
        assert item.text_layer.content == "Test"

    def test_should_access_text_properties(self, app):
        """应能访问文字属性."""
        layer = TextLayer(
            content="Hello",
            font_size=32,
            font_color=(255, 0, 0),
            bold=True,
        )
        item = TextLayerItem(layer)
        assert item.text_layer.content == "Hello"
        assert item.text_layer.font_size == 32
        assert item.text_layer.font_color == (255, 0, 0)
        assert item.text_layer.bold is True


# ===================
# 形状图层项测试
# ===================


class TestShapeLayerItem:
    """测试形状图层图形项."""

    def test_should_have_shape_layer_reference(self, app):
        """应有形状图层引用."""
        layer = ShapeLayer.create_rectangle()
        item = ShapeLayerItem(layer)
        assert item.shape_layer is layer

    def test_should_identify_rectangle(self, app):
        """应识别矩形."""
        layer = ShapeLayer.create_rectangle()
        item = ShapeLayerItem(layer)
        assert item.shape_layer.is_rectangle is True
        assert item.shape_layer.is_ellipse is False

    def test_should_identify_ellipse(self, app):
        """应识别椭圆."""
        layer = ShapeLayer.create_ellipse()
        item = ShapeLayerItem(layer)
        assert item.shape_layer.is_ellipse is True
        assert item.shape_layer.is_rectangle is False


# ===================
# 图片图层项测试
# ===================


class TestImageLayerItem:
    """测试图片图层图形项."""

    def test_should_have_image_layer_reference(self, app):
        """应有图片图层引用."""
        layer = ImageLayer.create("/path/to/image.png")
        item = ImageLayerItem(layer)
        assert item.image_layer is layer

    def test_should_handle_missing_image(self, app):
        """应处理缺失的图片."""
        layer = ImageLayer(image_path="/nonexistent/path.png")
        item = ImageLayerItem(layer)
        # 不应抛出异常
        assert item._pixmap is None

    def test_should_handle_empty_path(self, app):
        """应处理空路径."""
        layer = ImageLayer(image_path="")
        item = ImageLayerItem(layer)
        assert item._pixmap is None


# ===================
# 信号测试
# ===================


class TestLayerSignals:
    """测试图层信号."""

    def test_should_have_signals(self, app):
        """应有信号对象."""
        layer = TextLayer()
        item = TextLayerItem(layer)
        assert hasattr(item, "signals")
        assert hasattr(item.signals, "selected")
        assert hasattr(item.signals, "deselected")
        assert hasattr(item.signals, "position_changed")
        assert hasattr(item.signals, "size_changed")
        assert hasattr(item.signals, "edit_started")
        assert hasattr(item.signals, "edit_finished")


# ===================
# 文字编辑测试
# ===================


class TestTextLayerItemEditing:
    """测试文字图层编辑功能."""

    def test_should_not_be_editing_initially(self, app):
        """初始应不在编辑模式."""
        layer = TextLayer(content="Test")
        item = TextLayerItem(layer)
        assert item.is_editing is False

    def test_should_start_editing(self, app):
        """应能开始编辑."""
        layer = TextLayer(content="Test")
        item = TextLayerItem(layer)
        item.start_editing()
        assert item.is_editing is True

    def test_should_not_start_editing_when_locked(self, app):
        """锁定时不应能开始编辑."""
        layer = TextLayer(content="Test", locked=True)
        item = TextLayerItem(layer)
        item.start_editing()
        assert item.is_editing is False

    def test_should_finish_editing(self, app):
        """应能结束编辑."""
        layer = TextLayer(content="Old")
        item = TextLayerItem(layer)
        item.start_editing()
        item.finish_editing("New")
        assert item.is_editing is False
        assert layer.content == "New"

    def test_should_cancel_editing(self, app):
        """应能取消编辑."""
        layer = TextLayer(content="Original")
        item = TextLayerItem(layer)
        item.start_editing()
        item.cancel_editing()
        assert item.is_editing is False
        assert layer.content == "Original"  # 内容未改变

    def test_should_emit_edit_started_signal(self, app):
        """开始编辑时应发出信号."""
        layer = TextLayer(content="Test")
        item = TextLayerItem(layer)
        signal_received = []

        def on_edit_started(layer_id):
            signal_received.append(layer_id)

        item.signals.edit_started.connect(on_edit_started)
        item.start_editing()

        assert len(signal_received) == 1
        assert signal_received[0] == layer.id

    def test_should_emit_edit_finished_signal(self, app):
        """结束编辑时应发出信号."""
        layer = TextLayer(content="Old")
        item = TextLayerItem(layer)
        signal_received = []

        def on_edit_finished(layer_id, content):
            signal_received.append((layer_id, content))

        item.signals.edit_finished.connect(on_edit_finished)
        item.start_editing()
        item.finish_editing("New")

        assert len(signal_received) == 1
        assert signal_received[0] == (layer.id, "New")
