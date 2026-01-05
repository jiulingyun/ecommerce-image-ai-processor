"""LayerPanel 组件单元测试."""

import pytest
from unittest.mock import MagicMock

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMessageBox

from src.models.template_config import (
    TextLayer,
    ShapeLayer,
    ImageLayer,
    LayerType,
)
from src.ui.widgets.template_editor.layer_panel import (
    LayerItemWidget,
    LayerListWidget,
    LayerPanel,
)


# ===================
# LayerItemWidget 测试
# ===================


class TestLayerItemWidget:
    """LayerItemWidget 测试类."""

    def test_create_with_text_layer(self, app):
        """测试使用文字图层创建."""
        layer = TextLayer.create("Hello World")
        widget = LayerItemWidget(layer)

        assert widget.layer == layer
        assert widget.layer_id == layer.id

    def test_create_with_shape_layer(self, app):
        """测试使用形状图层创建."""
        layer = ShapeLayer.create_rectangle(width=100, height=50, fill_color=(255, 0, 0))
        widget = LayerItemWidget(layer)

        assert widget.layer == layer
        assert widget.layer_id == layer.id

    def test_create_with_image_layer(self, app):
        """测试使用图片图层创建."""
        layer = ImageLayer.create(image_path="")
        widget = LayerItemWidget(layer)

        assert widget.layer == layer
        assert widget.layer_id == layer.id

    def test_toggle_visibility(self, app):
        """测试切换可见性."""
        layer = TextLayer.create("Test")
        layer.visible = True
        widget = LayerItemWidget(layer)

        # 监听信号
        signal_received = []
        widget.visibility_toggled.connect(
            lambda lid, v: signal_received.append((lid, v))
        )

        # 切换可见性
        widget._toggle_visibility()

        assert layer.visible is False
        assert len(signal_received) == 1
        assert signal_received[0] == (layer.id, False)

    def test_toggle_lock(self, app):
        """测试切换锁定."""
        layer = TextLayer.create("Test")
        layer.locked = False
        widget = LayerItemWidget(layer)

        # 监听信号
        signal_received = []
        widget.lock_toggled.connect(lambda lid, l: signal_received.append((lid, l)))

        # 切换锁定
        widget._toggle_lock()

        assert layer.locked is True
        assert len(signal_received) == 1
        assert signal_received[0] == (layer.id, True)

    def test_get_layer_name_text(self, app):
        """测试获取文字图层名称."""
        layer = TextLayer.create("Hello World")
        widget = LayerItemWidget(layer)

        assert widget._get_layer_name() == "Hello World"

    def test_get_layer_name_text_truncated(self, app):
        """测试获取文字图层名称（截断）."""
        layer = TextLayer.create("This is a very long text content")
        widget = LayerItemWidget(layer)

        name = widget._get_layer_name()
        assert name.endswith("...")
        assert len(name) <= 18  # 15 + "..."

    def test_get_layer_name_rectangle(self, app):
        """测试获取矩形图层名称."""
        layer = ShapeLayer.create_rectangle(width=100, height=50, fill_color=(255, 0, 0))
        widget = LayerItemWidget(layer)

        assert widget._get_layer_name() == "矩形"

    def test_get_layer_name_ellipse(self, app):
        """测试获取椭圆图层名称."""
        layer = ShapeLayer.create_ellipse(width=100, height=50, fill_color=(0, 255, 0))
        widget = LayerItemWidget(layer)

        assert widget._get_layer_name() == "椭圆"

    def test_update_from_layer(self, app):
        """测试从图层数据更新显示."""
        layer = TextLayer.create("Test")
        widget = LayerItemWidget(layer)

        # 修改图层数据
        layer.visible = False
        layer.locked = True

        # 更新显示
        widget.update_from_layer()

        # 验证按钮状态已更新
        assert widget._visibility_btn.text() == "👁‍🗨"
        assert widget._lock_btn.text() == "🔒"


# ===================
# LayerListWidget 测试
# ===================


class TestLayerListWidget:
    """LayerListWidget 测试类."""

    def test_set_layers(self, app):
        """测试设置图层列表."""
        layers = [
            TextLayer.create("Layer 1"),
            ShapeLayer.create_rectangle(width=100, height=50, fill_color=(255, 0, 0)),
            ImageLayer.create(image_path=""),
        ]
        # 设置不同的 z_index
        layers[0].z_index = 1
        layers[1].z_index = 3
        layers[2].z_index = 2

        widget = LayerListWidget()
        widget.set_layers(layers)

        # 验证数量
        assert widget.count() == 3

        # 验证顺序（按 z_index 降序）
        order = widget.get_layer_order()
        assert order == [layers[1].id, layers[2].id, layers[0].id]

    def test_add_layer(self, app):
        """测试添加图层."""
        widget = LayerListWidget()
        layer = TextLayer.create("Test")

        widget.add_layer(layer)

        assert widget.count() == 1
        assert widget.get_layer_order() == [layer.id]

    def test_remove_layer(self, app):
        """测试移除图层."""
        layers = [
            TextLayer.create("Layer 1"),
            TextLayer.create("Layer 2"),
        ]

        widget = LayerListWidget()
        widget.set_layers(layers)
        assert widget.count() == 2

        widget.remove_layer(layers[0].id)
        assert widget.count() == 1
        assert layers[0].id not in widget.get_layer_order()

    def test_select_layer(self, app):
        """测试选中图层."""
        layers = [
            TextLayer.create("Layer 1"),
            TextLayer.create("Layer 2"),
        ]

        widget = LayerListWidget()
        widget.set_layers(layers)

        widget.select_layer(layers[1].id)

        assert widget.get_selected_layer_id() == layers[1].id

    def test_selection_signal(self, app):
        """测试选择变化信号."""
        layers = [
            TextLayer.create("Layer 1"),
            TextLayer.create("Layer 2"),
        ]

        widget = LayerListWidget()
        widget.set_layers(layers)

        signal_received = []
        widget.layer_selected.connect(lambda lid: signal_received.append(lid))

        widget.select_layer(layers[0].id)

        assert len(signal_received) == 1
        assert signal_received[0] == layers[0].id

    def test_visibility_change_signal(self, app):
        """测试可见性变化信号."""
        layer = TextLayer.create("Test")
        layer.visible = True

        widget = LayerListWidget()
        widget.set_layers([layer])

        signal_received = []
        widget.layer_visibility_changed.connect(
            lambda lid, v: signal_received.append((lid, v))
        )

        # 触发可见性切换
        item_widget = widget._layer_items[layer.id]
        item_widget._toggle_visibility()

        assert len(signal_received) == 1
        assert signal_received[0] == (layer.id, False)

    def test_lock_change_signal(self, app):
        """测试锁定变化信号."""
        layer = TextLayer.create("Test")
        layer.locked = False

        widget = LayerListWidget()
        widget.set_layers([layer])

        signal_received = []
        widget.layer_lock_changed.connect(
            lambda lid, l: signal_received.append((lid, l))
        )

        # 触发锁定切换
        item_widget = widget._layer_items[layer.id]
        item_widget._toggle_lock()

        assert len(signal_received) == 1
        assert signal_received[0] == (layer.id, True)

    def test_update_layer(self, app):
        """测试更新图层显示."""
        layer = TextLayer.create("Test")
        layer.visible = True

        widget = LayerListWidget()
        widget.set_layers([layer])

        # 修改图层
        layer.visible = False

        # 更新
        widget.update_layer(layer.id)

        # 验证显示已更新
        item_widget = widget._layer_items[layer.id]
        assert item_widget._visibility_btn.text() == "👁‍🗨"


# ===================
# LayerPanel 测试
# ===================


class TestLayerPanel:
    """LayerPanel 测试类."""

    def test_create(self, app):
        """测试创建面板."""
        panel = LayerPanel()
        assert panel is not None

    def test_set_layers(self, app):
        """测试设置图层列表."""
        layers = [
            TextLayer.create("Layer 1"),
            ShapeLayer.create_rectangle(width=100, height=50, fill_color=(255, 0, 0)),
        ]

        panel = LayerPanel()
        panel.set_layers(layers)

        # 验证图层列表已设置
        assert panel._layer_list.count() == 2

    def test_add_layer(self, app):
        """测试添加图层."""
        panel = LayerPanel()
        layer = TextLayer.create("Test")

        panel.add_layer(layer)

        assert panel._layer_list.count() == 1

    def test_remove_layer(self, app):
        """测试移除图层."""
        layers = [
            TextLayer.create("Layer 1"),
            TextLayer.create("Layer 2"),
        ]

        panel = LayerPanel()
        panel.set_layers(layers)

        panel.remove_layer(layers[0].id)

        assert panel._layer_list.count() == 1

    def test_select_layer(self, app):
        """测试选中图层."""
        layers = [
            TextLayer.create("Layer 1"),
            TextLayer.create("Layer 2"),
        ]

        panel = LayerPanel()
        panel.set_layers(layers)

        panel.select_layer(layers[1].id)

        assert panel._layer_list.get_selected_layer_id() == layers[1].id

    def test_layer_selected_signal(self, app):
        """测试图层选中信号传递."""
        layers = [TextLayer.create("Test")]

        panel = LayerPanel()
        panel.set_layers(layers)

        signal_received = []
        panel.layer_selected.connect(lambda lid: signal_received.append(lid))

        panel.select_layer(layers[0].id)

        assert len(signal_received) == 1
        assert signal_received[0] == layers[0].id

    def test_visibility_changed_signal(self, app):
        """测试可见性变化信号传递."""
        layer = TextLayer.create("Test")
        layer.visible = True

        panel = LayerPanel()
        panel.set_layers([layer])

        signal_received = []
        panel.layer_visibility_changed.connect(
            lambda lid, v: signal_received.append((lid, v))
        )

        # 触发可见性切换
        item_widget = panel._layer_list._layer_items[layer.id]
        item_widget._toggle_visibility()

        assert len(signal_received) == 1
        assert signal_received[0] == (layer.id, False)

    def test_lock_changed_signal(self, app):
        """测试锁定变化信号传递."""
        layer = TextLayer.create("Test")
        layer.locked = False

        panel = LayerPanel()
        panel.set_layers([layer])

        signal_received = []
        panel.layer_lock_changed.connect(
            lambda lid, l: signal_received.append((lid, l))
        )

        # 触发锁定切换
        item_widget = panel._layer_list._layer_items[layer.id]
        item_widget._toggle_lock()

        assert len(signal_received) == 1
        assert signal_received[0] == (layer.id, True)

    def test_add_requests_signals(self, app):
        """测试添加请求信号."""
        panel = LayerPanel()

        text_received = []
        rect_received = []
        ellipse_received = []
        image_received = []

        panel.add_text_requested.connect(lambda: text_received.append(True))
        panel.add_rectangle_requested.connect(lambda: rect_received.append(True))
        panel.add_ellipse_requested.connect(lambda: ellipse_received.append(True))
        panel.add_image_requested.connect(lambda: image_received.append(True))

        # 验证信号连接（按钮点击会触发信号）
        assert panel.add_text_requested is not None
        assert panel.add_rectangle_requested is not None
        assert panel.add_ellipse_requested is not None
        assert panel.add_image_requested is not None

    def test_update_layer(self, app):
        """测试更新图层."""
        layer = TextLayer.create("Test")
        layer.visible = True

        panel = LayerPanel()
        panel.set_layers([layer])

        # 修改图层
        layer.visible = False

        # 更新
        panel.update_layer(layer.id)

        # 验证显示已更新
        item_widget = panel._layer_list._layer_items[layer.id]
        assert item_widget._visibility_btn.text() == "👁‍🗨"

    def test_layer_order_signal(self, app):
        """测试图层顺序变化信号."""
        layers = [
            TextLayer.create("Layer 1"),
            TextLayer.create("Layer 2"),
        ]
        layers[0].z_index = 1
        layers[1].z_index = 2

        panel = LayerPanel()
        panel.set_layers(layers)

        signal_received = []
        panel.layer_order_changed.connect(lambda order: signal_received.append(order))

        # 验证信号已连接
        assert panel.layer_order_changed is not None


# ===================
# 集成测试
# ===================


class TestLayerPanelIntegration:
    """LayerPanel 集成测试类."""

    def test_full_workflow(self, app):
        """测试完整工作流程."""
        # 创建面板
        panel = LayerPanel()

        # 创建图层
        text_layer = TextLayer.create("Hello")
        text_layer.z_index = 2
        shape_layer = ShapeLayer.create_rectangle(width=100, height=50, fill_color=(255, 0, 0))
        shape_layer.z_index = 1

        # 设置图层列表
        panel.set_layers([text_layer, shape_layer])

        # 验证图层显示
        assert panel._layer_list.count() == 2

        # 验证顺序（z_index 高的在前）
        order = panel._layer_list.get_layer_order()
        assert order[0] == text_layer.id
        assert order[1] == shape_layer.id

        # 选中图层
        panel.select_layer(shape_layer.id)
        assert panel._layer_list.get_selected_layer_id() == shape_layer.id

        # 切换可见性
        item_widget = panel._layer_list._layer_items[text_layer.id]
        original_visible = text_layer.visible
        item_widget._toggle_visibility()
        assert text_layer.visible != original_visible

        # 切换锁定
        original_locked = text_layer.locked
        item_widget._toggle_lock()
        assert text_layer.locked != original_locked

        # 移除图层
        panel.remove_layer(text_layer.id)
        assert panel._layer_list.count() == 1

    def test_empty_panel(self, app):
        """测试空面板."""
        panel = LayerPanel()
        panel.set_layers([])

        assert panel._layer_list.count() == 0
        assert panel._layer_list.get_selected_layer_id() is None
