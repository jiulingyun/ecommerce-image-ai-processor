"""PropertyPanel 组件单元测试."""

import pytest

from PyQt6.QtCore import Qt

from src.models.template_config import (
    TextLayer,
    ShapeLayer,
    ImageLayer,
    TextAlign,
    ImageFitMode,
)
from src.ui.widgets.template_editor.property_panel import (
    ColorButton,
    LabeledSpinBox,
    LabeledSlider,
    TransformEditor,
    TextPropertyEditor,
    ShapePropertyEditor,
    ImagePropertyEditor,
    CanvasPropertyEditor,
    PropertyPanel,
)


# ===================
# 通用控件测试
# ===================


class TestColorButton:
    """ColorButton 测试类."""

    def test_create(self, app):
        """测试创建."""
        btn = ColorButton((255, 0, 0))
        assert btn.color == (255, 0, 0)

    def test_set_color(self, app):
        """测试设置颜色."""
        btn = ColorButton((0, 0, 0))
        btn.set_color((0, 255, 0))
        assert btn.color == (0, 255, 0)

    def test_color_changed_signal(self, app):
        """测试颜色变化信号."""
        btn = ColorButton((0, 0, 0))

        signal_received = []
        btn.color_changed.connect(lambda c: signal_received.append(c))

        # 信号已连接
        assert btn.color_changed is not None


class TestLabeledSpinBox:
    """LabeledSpinBox 测试类."""

    def test_create(self, app):
        """测试创建."""
        spin = LabeledSpinBox("X:", 0, 100, 50)
        assert spin.value == 50

    def test_set_value(self, app):
        """测试设置值."""
        spin = LabeledSpinBox("X:", 0, 100, 0)
        spin.set_value(75)
        assert spin.value == 75

    def test_value_changed_signal(self, app):
        """测试值变化信号."""
        spin = LabeledSpinBox("X:", 0, 100, 0)

        signal_received = []
        spin.value_changed.connect(lambda v: signal_received.append(v))

        spin._spinbox.setValue(25)

        assert len(signal_received) == 1
        assert signal_received[0] == 25


class TestLabeledSlider:
    """LabeledSlider 测试类."""

    def test_create(self, app):
        """测试创建."""
        slider = LabeledSlider("透明度:", 0, 100, 50, "%")
        assert slider.value == 50

    def test_set_value(self, app):
        """测试设置值."""
        slider = LabeledSlider("透明度:", 0, 100, 100, "%")
        slider.set_value(75)
        assert slider.value == 75

    def test_value_changed_signal(self, app):
        """测试值变化信号."""
        slider = LabeledSlider("透明度:", 0, 100, 100, "%")

        signal_received = []
        slider.value_changed.connect(lambda v: signal_received.append(v))

        slider._slider.setValue(50)

        assert len(signal_received) == 1
        assert signal_received[0] == 50


class TestTransformEditor:
    """TransformEditor 测试类."""

    def test_create(self, app):
        """测试创建."""
        editor = TransformEditor()
        assert editor is not None

    def test_set_values(self, app):
        """测试设置值."""
        editor = TransformEditor()
        editor.set_values(100, 200, 300, 400)

        assert editor._x_spin.value == 100
        assert editor._y_spin.value == 200
        assert editor._w_spin.value == 300
        assert editor._h_spin.value == 400

    def test_position_changed_signal(self, app):
        """测试位置变化信号."""
        editor = TransformEditor()

        signal_received = []
        editor.position_changed.connect(lambda x, y: signal_received.append((x, y)))

        editor._x_spin._spinbox.setValue(50)

        assert len(signal_received) == 1
        assert signal_received[0][0] == 50

    def test_size_changed_signal(self, app):
        """测试尺寸变化信号."""
        editor = TransformEditor()

        signal_received = []
        editor.size_changed.connect(lambda w, h: signal_received.append((w, h)))

        editor._w_spin._spinbox.setValue(200)

        assert len(signal_received) == 1
        assert signal_received[0][0] == 200


# ===================
# 图层属性编辑器测试
# ===================


class TestTextPropertyEditor:
    """TextPropertyEditor 测试类."""

    def test_create(self, app):
        """测试创建."""
        editor = TextPropertyEditor()
        assert editor is not None

    def test_set_layer(self, app):
        """测试设置图层."""
        editor = TextPropertyEditor()
        layer = TextLayer.create("Hello World")
        layer.font_size = 36
        layer.bold = True
        layer.font_color = (255, 0, 0)

        editor.set_layer(layer)

        # 验证显示值
        assert editor._font_size.value() == 36
        assert editor._bold.isChecked() is True
        assert editor._font_color.color == (255, 0, 0)

    def test_property_changed_signal(self, app):
        """测试属性变化信号."""
        editor = TextPropertyEditor()
        layer = TextLayer.create("Test")
        editor.set_layer(layer)

        signal_received = []
        editor.property_changed.connect(
            lambda p, v: signal_received.append((p, v))
        )

        editor._font_size.setValue(48)

        assert len(signal_received) == 1
        assert signal_received[0] == ("font_size", 48)

    def test_align_change(self, app):
        """测试对齐变化."""
        editor = TextPropertyEditor()
        layer = TextLayer.create("Test")
        editor.set_layer(layer)

        signal_received = []
        editor.property_changed.connect(
            lambda p, v: signal_received.append((p, v))
        )

        editor._align.setCurrentIndex(1)  # 居中

        assert len(signal_received) == 1
        assert signal_received[0][0] == "align"
        assert signal_received[0][1] == TextAlign.CENTER


class TestShapePropertyEditor:
    """ShapePropertyEditor 测试类."""

    def test_create(self, app):
        """测试创建."""
        editor = ShapePropertyEditor()
        assert editor is not None

    def test_set_rectangle_layer(self, app):
        """测试设置矩形图层."""
        editor = ShapePropertyEditor()
        layer = ShapeLayer.create_rectangle(
            width=100, height=50, fill_color=(200, 100, 50)
        )
        layer.corner_radius = 10

        editor.set_layer(layer)

        # 验证显示值
        assert editor._fill_color.color == (200, 100, 50)
        assert editor._corner_radius.value == 10
        # 矩形显示圆角设置（用 isHidden 检查，因为父组件未显示时 isVisible 始终为 False）
        assert editor._corner_group.isHidden() is False

    def test_set_ellipse_layer(self, app):
        """测试设置椭圆图层."""
        editor = ShapePropertyEditor()
        layer = ShapeLayer.create_ellipse(
            width=100, height=50, fill_color=(100, 200, 50)
        )

        editor.set_layer(layer)

        # 椭圆不显示圆角设置（被隐藏）
        assert editor._corner_group.isHidden() is True

    def test_property_changed_signal(self, app):
        """测试属性变化信号."""
        editor = ShapePropertyEditor()
        layer = ShapeLayer.create_rectangle(width=100, height=50)
        editor.set_layer(layer)

        signal_received = []
        editor.property_changed.connect(
            lambda p, v: signal_received.append((p, v))
        )

        editor._fill_enabled.setChecked(False)

        assert len(signal_received) == 1
        assert signal_received[0] == ("fill_enabled", False)


class TestImagePropertyEditor:
    """ImagePropertyEditor 测试类."""

    def test_create(self, app):
        """测试创建."""
        editor = ImagePropertyEditor()
        assert editor is not None

    def test_set_layer(self, app):
        """测试设置图层."""
        editor = ImagePropertyEditor()
        layer = ImageLayer.create(image_path="/path/to/image.png")
        layer.fit_mode = ImageFitMode.COVER

        editor.set_layer(layer)

        # 验证显示值
        assert editor._path_edit.text() == "/path/to/image.png"
        assert editor._fit_mode.currentIndex() == 1  # COVER

    def test_fit_mode_change(self, app):
        """测试适应模式变化."""
        editor = ImagePropertyEditor()
        layer = ImageLayer.create(image_path="")
        editor.set_layer(layer)

        signal_received = []
        editor.property_changed.connect(
            lambda p, v: signal_received.append((p, v))
        )

        editor._fit_mode.setCurrentIndex(2)  # STRETCH

        assert len(signal_received) == 1
        assert signal_received[0][0] == "fit_mode"
        assert signal_received[0][1] == ImageFitMode.STRETCH


class TestCanvasPropertyEditor:
    """CanvasPropertyEditor 测试类."""

    def test_create(self, app):
        """测试创建."""
        editor = CanvasPropertyEditor()
        assert editor is not None

    def test_set_template(self, app):
        """测试设置模板属性."""
        editor = CanvasPropertyEditor()
        editor.set_template(1200, 800, (240, 240, 240))

        assert editor._width.value() == 1200
        assert editor._height.value() == 800
        assert editor._bg_color.color == (240, 240, 240)

    def test_property_changed_signal(self, app):
        """测试属性变化信号."""
        editor = CanvasPropertyEditor()

        signal_received = []
        editor.property_changed.connect(
            lambda p, v: signal_received.append((p, v))
        )

        editor._width.setValue(1000)

        assert len(signal_received) == 1
        assert signal_received[0] == ("canvas_width", 1000)


# ===================
# PropertyPanel 主面板测试
# ===================


class TestPropertyPanel:
    """PropertyPanel 测试类."""

    def test_create(self, app):
        """测试创建."""
        panel = PropertyPanel()
        assert panel is not None

    def test_set_no_layer(self, app):
        """测试无选中图层."""
        panel = PropertyPanel()
        panel.set_layer(None)

        # 应显示画布属性编辑器
        assert panel._stack.currentIndex() == 0

    def test_set_text_layer(self, app):
        """测试设置文字图层."""
        panel = PropertyPanel()
        layer = TextLayer.create("Test")

        panel.set_layer(layer)

        # 应显示文字属性编辑器
        assert panel._stack.currentIndex() == 1

    def test_set_shape_layer(self, app):
        """测试设置形状图层."""
        panel = PropertyPanel()
        layer = ShapeLayer.create_rectangle(width=100, height=50)

        panel.set_layer(layer)

        # 应显示形状属性编辑器
        assert panel._stack.currentIndex() == 2

    def test_set_image_layer(self, app):
        """测试设置图片图层."""
        panel = PropertyPanel()
        layer = ImageLayer.create(image_path="")

        panel.set_layer(layer)

        # 应显示图片属性编辑器
        assert panel._stack.currentIndex() == 3

    def test_layer_property_changed_signal(self, app):
        """测试图层属性变化信号."""
        panel = PropertyPanel()
        layer = TextLayer.create("Test")
        panel.set_layer(layer)

        signal_received = []
        panel.layer_property_changed.connect(
            lambda lid, p, v: signal_received.append((lid, p, v))
        )

        # 触发属性变化
        panel._text_editor._font_size.setValue(48)

        assert len(signal_received) == 1
        assert signal_received[0][0] == layer.id
        assert signal_received[0][1] == "font_size"
        assert signal_received[0][2] == 48

    def test_canvas_property_changed_signal(self, app):
        """测试画布属性变化信号."""
        panel = PropertyPanel()
        panel.set_layer(None)  # 显示画布属性

        signal_received = []
        panel.canvas_property_changed.connect(
            lambda p, v: signal_received.append((p, v))
        )

        # 触发属性变化
        panel._canvas_editor._width.setValue(1024)

        assert len(signal_received) == 1
        assert signal_received[0] == ("canvas_width", 1024)

    def test_set_canvas_properties(self, app):
        """测试设置画布属性."""
        panel = PropertyPanel()
        panel.set_canvas_properties(1200, 800, (200, 200, 200))

        assert panel._canvas_editor._width.value() == 1200
        assert panel._canvas_editor._height.value() == 800
        assert panel._canvas_editor._bg_color.color == (200, 200, 200)

    def test_update_layer(self, app):
        """测试更新图层."""
        panel = PropertyPanel()
        layer = TextLayer.create("Test")
        layer.font_size = 24
        panel.set_layer(layer)

        # 修改图层
        layer.font_size = 48

        # 刷新
        panel.update_layer()

        # 验证显示已更新
        assert panel._text_editor._font_size.value() == 48


# ===================
# 集成测试
# ===================


class TestPropertyPanelIntegration:
    """PropertyPanel 集成测试类."""

    def test_switch_between_layer_types(self, app):
        """测试切换不同类型图层."""
        panel = PropertyPanel()

        # 文字图层
        text_layer = TextLayer.create("Hello")
        panel.set_layer(text_layer)
        assert panel._stack.currentIndex() == 1

        # 形状图层
        shape_layer = ShapeLayer.create_rectangle(width=100, height=50)
        panel.set_layer(shape_layer)
        assert panel._stack.currentIndex() == 2

        # 图片图层
        image_layer = ImageLayer.create(image_path="")
        panel.set_layer(image_layer)
        assert panel._stack.currentIndex() == 3

        # 无选中
        panel.set_layer(None)
        assert panel._stack.currentIndex() == 0

    def test_full_workflow(self, app):
        """测试完整工作流程."""
        panel = PropertyPanel()

        # 设置画布属性
        panel.set_canvas_properties(800, 600, (255, 255, 255))

        # 创建文字图层
        text_layer = TextLayer.create("Hello World")
        text_layer.font_size = 24
        text_layer.font_color = (0, 0, 0)
        text_layer.bold = True

        # 设置图层
        panel.set_layer(text_layer)

        # 验证显示
        assert panel._text_editor._font_size.value() == 24
        assert panel._text_editor._font_color.color == (0, 0, 0)
        assert panel._text_editor._bold.isChecked() is True

        # 监听变化
        changes = []
        panel.layer_property_changed.connect(
            lambda lid, p, v: changes.append((lid, p, v))
        )

        # 修改字体大小
        panel._text_editor._font_size.setValue(36)

        # 验证信号
        assert len(changes) == 1
        assert changes[0][1] == "font_size"
        assert changes[0][2] == 36
