"""属性编辑面板组件.

提供统一的属性编辑面板，根据选中图层类型动态显示对应的属性编辑器。

Features:
    - 位置和尺寸数值输入
    - 颜色选择器
    - 滑块调节透明度、圆角等
    - 属性变更实时同步
    - 无选中时显示画布属性
"""

from __future__ import annotations

from typing import Optional, List, Callable, Any, TYPE_CHECKING

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QIntValidator, QDoubleValidator
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QDoubleSpinBox,
    QSlider,
    QComboBox,
    QCheckBox,
    QPushButton,
    QColorDialog,
    QGroupBox,
    QScrollArea,
    QFrame,
    QSizePolicy,
    QFileDialog,
    QStackedWidget,
)

from src.models.template_config import (
    LayerType,
    AnyLayer,
    TextLayer,
    ShapeLayer,
    ImageLayer,
    TextAlign,
    ImageFitMode,
)

if TYPE_CHECKING:
    from src.models.template_config import TemplateConfig


# ===================
# 通用属性控件
# ===================


class ColorButton(QPushButton):
    """颜色选择按钮."""

    color_changed = pyqtSignal(tuple)  # (r, g, b)

    def __init__(
        self,
        color: tuple = (255, 255, 255),
        parent: Optional[QWidget] = None,
    ) -> None:
        """初始化颜色按钮.

        Args:
            color: 初始颜色 (r, g, b)
            parent: 父组件
        """
        super().__init__(parent)
        self._color = color
        self.setFixedSize(60, 24)
        self._update_style()
        self.clicked.connect(self._pick_color)

    @property
    def color(self) -> tuple:
        """获取当前颜色."""
        return self._color

    def set_color(self, color: tuple) -> None:
        """设置颜色."""
        self._color = color
        self._update_style()

    def _update_style(self) -> None:
        """更新按钮样式."""
        r, g, b = self._color
        # 计算文字颜色（确保可读性）
        brightness = (r * 299 + g * 587 + b * 114) / 1000
        text_color = "#000" if brightness > 128 else "#fff"
        self.setStyleSheet(
            f"QPushButton {{ background-color: rgb({r},{g},{b}); "
            f"color: {text_color}; border: 1px solid #ccc; }}"
        )
        self.setText(f"#{r:02x}{g:02x}{b:02x}")

    def _pick_color(self) -> None:
        """打开颜色选择器."""
        r, g, b = self._color
        color = QColorDialog.getColor(
            QColor(r, g, b),
            self,
            "选择颜色",
        )
        if color.isValid():
            new_color = (color.red(), color.green(), color.blue())
            self._color = new_color
            self._update_style()
            self.color_changed.emit(new_color)


class LabeledSpinBox(QWidget):
    """带标签的数值输入框."""

    value_changed = pyqtSignal(int)

    def __init__(
        self,
        label: str,
        min_val: int = 0,
        max_val: int = 9999,
        value: int = 0,
        parent: Optional[QWidget] = None,
    ) -> None:
        """初始化.

        Args:
            label: 标签文本
            min_val: 最小值
            max_val: 最大值
            value: 初始值
            parent: 父组件
        """
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        self._label = QLabel(label)
        # 移除固定宽度，让其自适应但保持紧凑
        self._label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Preferred)
        layout.addWidget(self._label)

        self._spinbox = QSpinBox()
        self._spinbox.setRange(min_val, max_val)
        self._spinbox.setValue(value)
        self._spinbox.setMinimumWidth(50)  # 确保最小宽度
        self._spinbox.valueChanged.connect(self.value_changed.emit)
        layout.addWidget(self._spinbox, 1)

    @property
    def value(self) -> int:
        """获取当前值."""
        return self._spinbox.value()

    def set_value(self, value: int) -> None:
        """设置值."""
        self._spinbox.blockSignals(True)
        self._spinbox.setValue(value)
        self._spinbox.blockSignals(False)


class LabeledSlider(QWidget):
    """带标签和数值显示的滑块."""

    value_changed = pyqtSignal(int)

    def __init__(
        self,
        label: str,
        min_val: int = 0,
        max_val: int = 100,
        value: int = 100,
        suffix: str = "%",
        parent: Optional[QWidget] = None,
    ) -> None:
        """初始化.

        Args:
            label: 标签文本
            min_val: 最小值
            max_val: 最大值
            value: 初始值
            suffix: 数值后缀
            parent: 父组件
        """
        super().__init__(parent)
        self._suffix = suffix

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self._label = QLabel(label)
        self._label.setFixedWidth(50)
        layout.addWidget(self._label)

        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setRange(min_val, max_val)
        self._slider.setValue(value)
        self._slider.valueChanged.connect(self._on_value_changed)
        layout.addWidget(self._slider, 1)

        self._value_label = QLabel(f"{value}{suffix}")
        self._value_label.setFixedWidth(40)
        self._value_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self._value_label)

    @property
    def value(self) -> int:
        """获取当前值."""
        return self._slider.value()

    def set_value(self, value: int) -> None:
        """设置值."""
        self._slider.blockSignals(True)
        self._slider.setValue(value)
        self._value_label.setText(f"{value}{self._suffix}")
        self._slider.blockSignals(False)

    def _on_value_changed(self, value: int) -> None:
        """值变化处理."""
        self._value_label.setText(f"{value}{self._suffix}")
        self.value_changed.emit(value)


# ===================
# 位置/尺寸编辑器
# ===================


class TransformEditor(QGroupBox):
    """位置和尺寸编辑器."""

    position_changed = pyqtSignal(int, int)  # x, y
    size_changed = pyqtSignal(int, int)  # width, height

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """初始化."""
        super().__init__("位置与尺寸", parent)

        layout = QGridLayout(self)
        layout.setSpacing(4)

        # X, Y
        self._x_spin = LabeledSpinBox("X:", -9999, 9999, 0)
        self._y_spin = LabeledSpinBox("Y:", -9999, 9999, 0)
        self._x_spin.value_changed.connect(self._emit_position)
        self._y_spin.value_changed.connect(self._emit_position)
        layout.addWidget(self._x_spin, 0, 0)
        layout.addWidget(self._y_spin, 0, 1)

        # Width, Height
        self._w_spin = LabeledSpinBox("W:", 1, 9999, 100)
        self._h_spin = LabeledSpinBox("H:", 1, 9999, 100)
        self._w_spin.value_changed.connect(self._emit_size)
        self._h_spin.value_changed.connect(self._emit_size)
        layout.addWidget(self._w_spin, 1, 0)
        layout.addWidget(self._h_spin, 1, 1)

    def set_values(self, x: int, y: int, width: int, height: int) -> None:
        """设置所有值."""
        self._x_spin.set_value(x)
        self._y_spin.set_value(y)
        self._w_spin.set_value(width)
        self._h_spin.set_value(height)

    def _emit_position(self) -> None:
        """发射位置变化信号."""
        self.position_changed.emit(self._x_spin.value, self._y_spin.value)

    def _emit_size(self) -> None:
        """发射尺寸变化信号."""
        self.size_changed.emit(self._w_spin.value, self._h_spin.value)


# ===================
# 文字图层属性编辑器
# ===================


class TextPropertyEditor(QWidget):
    """文字图层属性编辑器."""

    property_changed = pyqtSignal(str, object)  # property_name, value

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """初始化."""
        super().__init__(parent)
        self._layer: Optional[TextLayer] = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        """设置UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)  # 减少间距

        # 位置尺寸
        self._transform = TransformEditor()
        self._transform.position_changed.connect(self._on_position_changed)
        self._transform.size_changed.connect(self._on_size_changed)
        layout.addWidget(self._transform)

        # 字体样式组
        font_group = QGroupBox("字体样式")
        font_layout = QGridLayout(font_group)
        font_layout.setContentsMargins(4, 8, 4, 4)
        font_layout.setSpacing(4)

        # 字体大小
        font_layout.addWidget(QLabel("大小:"), 0, 0)
        self._font_size = QSpinBox()
        self._font_size.setRange(8, 200)
        self._font_size.setValue(24)
        self._font_size.setMinimumWidth(60)
        self._font_size.valueChanged.connect(
            lambda v: self._emit_change("font_size", v)
        )
        font_layout.addWidget(self._font_size, 0, 1)

        # 字体颜色
        font_layout.addWidget(QLabel("颜色:"), 0, 2)
        self._font_color = ColorButton((0, 0, 0))
        self._font_color.setFixedSize(50, 24) # 稍微减小宽度
        self._font_color.color_changed.connect(
            lambda c: self._emit_change("font_color", c)
        )
        font_layout.addWidget(self._font_color, 0, 3)

        # 对齐方式
        font_layout.addWidget(QLabel("对齐:"), 1, 0)
        self._align = QComboBox()
        self._align.addItems(["左对齐", "居中", "右对齐"])
        self._align.currentIndexChanged.connect(self._on_align_changed)
        font_layout.addWidget(self._align, 1, 1, 1, 3)

        # 样式复选框
        style_layout = QHBoxLayout()
        style_layout.setSpacing(8)
        self._bold = QCheckBox("粗体")
        self._bold.toggled.connect(lambda v: self._emit_change("bold", v))
        style_layout.addWidget(self._bold)

        self._italic = QCheckBox("斜体")
        self._italic.toggled.connect(lambda v: self._emit_change("italic", v))
        style_layout.addWidget(self._italic)

        self._underline = QCheckBox("下划线")
        self._underline.toggled.connect(lambda v: self._emit_change("underline", v))
        style_layout.addWidget(self._underline)
        font_layout.addLayout(style_layout, 2, 0, 1, 4)

        layout.addWidget(font_group)

        # 背景设置组
        bg_group = QGroupBox("背景")
        bg_layout = QGridLayout(bg_group)
        bg_layout.setContentsMargins(4, 8, 4, 4)
        bg_layout.setSpacing(4)

        self._bg_enabled = QCheckBox("启用背景")
        self._bg_enabled.toggled.connect(
            lambda v: self._emit_change("background_enabled", v)
        )
        bg_layout.addWidget(self._bg_enabled, 0, 0, 1, 2)

        bg_layout.addWidget(QLabel("颜色:"), 0, 2)
        self._bg_color = ColorButton((255, 255, 255))
        self._bg_color.setFixedSize(50, 24)
        self._bg_color.color_changed.connect(
            lambda c: self._emit_change("background_color", c)
        )
        bg_layout.addWidget(self._bg_color, 0, 3)

        self._bg_opacity = LabeledSlider("透明度:", 0, 100, 100, "%")
        self._bg_opacity.value_changed.connect(
            lambda v: self._emit_change("background_opacity", v)
        )
        bg_layout.addWidget(self._bg_opacity, 1, 0, 1, 4)

        layout.addWidget(bg_group)

        # 描边设置组
        stroke_group = QGroupBox("描边")
        stroke_layout = QGridLayout(stroke_group)
        stroke_layout.setContentsMargins(4, 8, 4, 4)
        stroke_layout.setSpacing(4)

        self._stroke_enabled = QCheckBox("启用描边")
        self._stroke_enabled.toggled.connect(
            lambda v: self._emit_change("stroke_enabled", v)
        )
        stroke_layout.addWidget(self._stroke_enabled, 0, 0, 1, 2)

        stroke_layout.addWidget(QLabel("颜色:"), 0, 2)
        self._stroke_color = ColorButton((255, 255, 255))
        self._stroke_color.setFixedSize(50, 24)
        self._stroke_color.color_changed.connect(
            lambda c: self._emit_change("stroke_color", c)
        )
        stroke_layout.addWidget(self._stroke_color, 0, 3)

        stroke_layout.addWidget(QLabel("宽度:"), 1, 0)
        self._stroke_width = QSpinBox()
        self._stroke_width.setRange(1, 10)
        self._stroke_width.setMinimumWidth(60)
        self._stroke_width.valueChanged.connect(
            lambda v: self._emit_change("stroke_width", v)
        )
        stroke_layout.addWidget(self._stroke_width, 1, 1)

        layout.addWidget(stroke_group)

        # 透明度
        self._opacity = LabeledSlider("透明度:", 0, 100, 100, "%")
        self._opacity.value_changed.connect(lambda v: self._emit_change("opacity", v))
        layout.addWidget(self._opacity)

        layout.addStretch()

    def set_layer(self, layer: TextLayer) -> None:
        """设置图层."""
        self._layer = layer
        self._update_display()

    def _update_display(self) -> None:
        """更新显示."""
        if not self._layer:
            return

        layer = self._layer

        # 位置尺寸
        self._transform.set_values(layer.x, layer.y, layer.width, layer.height)

        # 字体
        self._font_size.blockSignals(True)
        self._font_size.setValue(layer.font_size)
        self._font_size.blockSignals(False)

        self._font_color.set_color(layer.font_color)

        self._align.blockSignals(True)
        align_map = {TextAlign.LEFT: 0, TextAlign.CENTER: 1, TextAlign.RIGHT: 2}
        self._align.setCurrentIndex(align_map.get(layer.align, 0))
        self._align.blockSignals(False)

        self._bold.blockSignals(True)
        self._bold.setChecked(layer.bold)
        self._bold.blockSignals(False)

        self._italic.blockSignals(True)
        self._italic.setChecked(layer.italic)
        self._italic.blockSignals(False)

        self._underline.blockSignals(True)
        self._underline.setChecked(layer.underline)
        self._underline.blockSignals(False)

        # 背景
        self._bg_enabled.blockSignals(True)
        self._bg_enabled.setChecked(layer.background_enabled)
        self._bg_enabled.blockSignals(False)

        self._bg_color.set_color(layer.background_color)
        self._bg_opacity.set_value(layer.background_opacity)

        # 描边
        self._stroke_enabled.blockSignals(True)
        self._stroke_enabled.setChecked(layer.stroke_enabled)
        self._stroke_enabled.blockSignals(False)

        self._stroke_color.set_color(layer.stroke_color)

        self._stroke_width.blockSignals(True)
        self._stroke_width.setValue(layer.stroke_width)
        self._stroke_width.blockSignals(False)

        # 透明度
        self._opacity.set_value(layer.opacity)

    def _emit_change(self, prop: str, value: Any) -> None:
        """发射属性变化信号."""
        self.property_changed.emit(prop, value)

    def _on_position_changed(self, x: int, y: int) -> None:
        """位置变化."""
        self.property_changed.emit("x", x)
        self.property_changed.emit("y", y)

    def _on_size_changed(self, w: int, h: int) -> None:
        """尺寸变化."""
        self.property_changed.emit("width", w)
        self.property_changed.emit("height", h)

    def _on_align_changed(self, index: int) -> None:
        """对齐变化."""
        align_map = {0: TextAlign.LEFT, 1: TextAlign.CENTER, 2: TextAlign.RIGHT}
        self._emit_change("align", align_map.get(index, TextAlign.LEFT))


# ===================
# 形状图层属性编辑器
# ===================


class ShapePropertyEditor(QWidget):
    """形状图层属性编辑器."""

    property_changed = pyqtSignal(str, object)  # property_name, value

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """初始化."""
        super().__init__(parent)
        self._layer: Optional[ShapeLayer] = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        """设置UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # 位置尺寸
        self._transform = TransformEditor()
        self._transform.position_changed.connect(self._on_position_changed)
        self._transform.size_changed.connect(self._on_size_changed)
        layout.addWidget(self._transform)

        # 填充设置组
        fill_group = QGroupBox("填充")
        fill_layout = QGridLayout(fill_group)
        fill_layout.setSpacing(4)

        self._fill_enabled = QCheckBox("启用填充")
        self._fill_enabled.toggled.connect(
            lambda v: self._emit_change("fill_enabled", v)
        )
        fill_layout.addWidget(self._fill_enabled, 0, 0, 1, 2)

        fill_layout.addWidget(QLabel("颜色:"), 1, 0)
        self._fill_color = ColorButton((200, 200, 200))
        self._fill_color.color_changed.connect(
            lambda c: self._emit_change("fill_color", c)
        )
        fill_layout.addWidget(self._fill_color, 1, 1)

        self._fill_opacity = LabeledSlider("透明度:", 0, 100, 100, "%")
        self._fill_opacity.value_changed.connect(
            lambda v: self._emit_change("fill_opacity", v)
        )
        fill_layout.addWidget(self._fill_opacity, 2, 0, 1, 2)

        layout.addWidget(fill_group)

        # 描边设置组
        stroke_group = QGroupBox("描边")
        stroke_layout = QGridLayout(stroke_group)
        stroke_layout.setSpacing(4)

        self._stroke_enabled = QCheckBox("启用描边")
        self._stroke_enabled.toggled.connect(
            lambda v: self._emit_change("stroke_enabled", v)
        )
        stroke_layout.addWidget(self._stroke_enabled, 0, 0, 1, 2)

        stroke_layout.addWidget(QLabel("颜色:"), 1, 0)
        self._stroke_color = ColorButton((0, 0, 0))
        self._stroke_color.color_changed.connect(
            lambda c: self._emit_change("stroke_color", c)
        )
        stroke_layout.addWidget(self._stroke_color, 1, 1)

        stroke_layout.addWidget(QLabel("宽度:"), 2, 0)
        self._stroke_width = QSpinBox()
        self._stroke_width.setRange(0, 20)
        self._stroke_width.valueChanged.connect(
            lambda v: self._emit_change("stroke_width", v)
        )
        stroke_layout.addWidget(self._stroke_width, 2, 1)

        layout.addWidget(stroke_group)

        # 圆角设置（仅矩形）
        self._corner_group = QGroupBox("圆角")
        corner_layout = QHBoxLayout(self._corner_group)
        self._corner_radius = LabeledSlider("半径:", 0, 100, 0, "px")
        self._corner_radius.value_changed.connect(
            lambda v: self._emit_change("corner_radius", v)
        )
        corner_layout.addWidget(self._corner_radius)
        layout.addWidget(self._corner_group)

        # 透明度
        self._opacity = LabeledSlider("透明度:", 0, 100, 100, "%")
        self._opacity.value_changed.connect(lambda v: self._emit_change("opacity", v))
        layout.addWidget(self._opacity)

        layout.addStretch()

    def set_layer(self, layer: ShapeLayer) -> None:
        """设置图层."""
        self._layer = layer
        self._update_display()

    def _update_display(self) -> None:
        """更新显示."""
        if not self._layer:
            return

        layer = self._layer

        # 位置尺寸
        self._transform.set_values(layer.x, layer.y, layer.width, layer.height)

        # 填充
        self._fill_enabled.blockSignals(True)
        self._fill_enabled.setChecked(layer.fill_enabled)
        self._fill_enabled.blockSignals(False)

        self._fill_color.set_color(layer.fill_color)
        self._fill_opacity.set_value(layer.fill_opacity)

        # 描边
        self._stroke_enabled.blockSignals(True)
        self._stroke_enabled.setChecked(layer.stroke_enabled)
        self._stroke_enabled.blockSignals(False)

        self._stroke_color.set_color(layer.stroke_color)

        self._stroke_width.blockSignals(True)
        self._stroke_width.setValue(layer.stroke_width)
        self._stroke_width.blockSignals(False)

        # 圆角（仅矩形显示）
        self._corner_group.setVisible(layer.is_rectangle)
        self._corner_radius.set_value(layer.corner_radius)

        # 透明度
        self._opacity.set_value(layer.opacity)

    def _emit_change(self, prop: str, value: Any) -> None:
        """发射属性变化信号."""
        self.property_changed.emit(prop, value)

    def _on_position_changed(self, x: int, y: int) -> None:
        """位置变化."""
        self.property_changed.emit("x", x)
        self.property_changed.emit("y", y)

    def _on_size_changed(self, w: int, h: int) -> None:
        """尺寸变化."""
        self.property_changed.emit("width", w)
        self.property_changed.emit("height", h)


# ===================
# 图片图层属性编辑器
# ===================


class ImagePropertyEditor(QWidget):
    """图片图层属性编辑器."""

    property_changed = pyqtSignal(str, object)  # property_name, value

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """初始化."""
        super().__init__(parent)
        self._layer: Optional[ImageLayer] = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        """设置UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # 位置尺寸
        self._transform = TransformEditor()
        self._transform.position_changed.connect(self._on_position_changed)
        self._transform.size_changed.connect(self._on_size_changed)
        layout.addWidget(self._transform)

        # 图片设置组
        img_group = QGroupBox("图片")
        img_layout = QVBoxLayout(img_group)
        img_layout.setSpacing(4)

        # 图片路径
        path_layout = QHBoxLayout()
        self._path_edit = QLineEdit()
        self._path_edit.setPlaceholderText("图片路径...")
        self._path_edit.setReadOnly(True)
        path_layout.addWidget(self._path_edit, 1)

        self._browse_btn = QPushButton("浏览...")
        self._browse_btn.clicked.connect(self._browse_image)
        path_layout.addWidget(self._browse_btn)
        img_layout.addLayout(path_layout)

        # 适应模式
        fit_layout = QHBoxLayout()
        fit_layout.addWidget(QLabel("适应模式:"))
        self._fit_mode = QComboBox()
        self._fit_mode.addItems(["包含", "覆盖", "拉伸"])
        self._fit_mode.currentIndexChanged.connect(self._on_fit_mode_changed)
        fit_layout.addWidget(self._fit_mode, 1)
        img_layout.addLayout(fit_layout)

        # 保持比例
        self._preserve_ratio = QCheckBox("保持宽高比")
        self._preserve_ratio.toggled.connect(
            lambda v: self._emit_change("preserve_aspect_ratio", v)
        )
        img_layout.addWidget(self._preserve_ratio)

        layout.addWidget(img_group)

        # 透明度
        self._opacity = LabeledSlider("透明度:", 0, 100, 100, "%")
        self._opacity.value_changed.connect(lambda v: self._emit_change("opacity", v))
        layout.addWidget(self._opacity)

        layout.addStretch()

    def set_layer(self, layer: ImageLayer) -> None:
        """设置图层."""
        self._layer = layer
        self._update_display()

    def _update_display(self) -> None:
        """更新显示."""
        if not self._layer:
            return

        layer = self._layer

        # 位置尺寸
        self._transform.set_values(layer.x, layer.y, layer.width, layer.height)

        # 图片
        self._path_edit.setText(layer.image_path or "")

        self._fit_mode.blockSignals(True)
        fit_map = {
            ImageFitMode.CONTAIN: 0,
            ImageFitMode.COVER: 1,
            ImageFitMode.STRETCH: 2,
        }
        self._fit_mode.setCurrentIndex(fit_map.get(layer.fit_mode, 0))
        self._fit_mode.blockSignals(False)

        self._preserve_ratio.blockSignals(True)
        self._preserve_ratio.setChecked(layer.preserve_aspect_ratio)
        self._preserve_ratio.blockSignals(False)

        # 透明度
        self._opacity.set_value(layer.opacity)

    def _emit_change(self, prop: str, value: Any) -> None:
        """发射属性变化信号."""
        self.property_changed.emit(prop, value)

    def _on_position_changed(self, x: int, y: int) -> None:
        """位置变化."""
        self.property_changed.emit("x", x)
        self.property_changed.emit("y", y)

    def _on_size_changed(self, w: int, h: int) -> None:
        """尺寸变化."""
        self.property_changed.emit("width", w)
        self.property_changed.emit("height", h)

    def _browse_image(self) -> None:
        """浏览图片."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "选择图片",
            "",
            "图片文件 (*.png *.jpg *.jpeg *.bmp *.gif)",
        )
        if path:
            self._path_edit.setText(path)
            self._emit_change("image_path", path)

    def _on_fit_mode_changed(self, index: int) -> None:
        """适应模式变化."""
        fit_map = {
            0: ImageFitMode.CONTAIN,
            1: ImageFitMode.COVER,
            2: ImageFitMode.STRETCH,
        }
        self._emit_change("fit_mode", fit_map.get(index, ImageFitMode.CONTAIN))


# ===================
# 画布/模板属性编辑器
# ===================


class CanvasPropertyEditor(QWidget):
    """画布/模板属性编辑器."""

    property_changed = pyqtSignal(str, object)  # property_name, value

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """初始化."""
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """设置UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # 画布尺寸组
        size_group = QGroupBox("画布尺寸")
        size_layout = QGridLayout(size_group)
        size_layout.setSpacing(4)

        size_layout.addWidget(QLabel("宽度:"), 0, 0)
        self._width = QSpinBox()
        self._width.setRange(100, 4096)
        self._width.setValue(800)
        self._width.valueChanged.connect(
            lambda v: self._emit_change("canvas_width", v)
        )
        size_layout.addWidget(self._width, 0, 1)

        size_layout.addWidget(QLabel("高度:"), 1, 0)
        self._height = QSpinBox()
        self._height.setRange(100, 4096)
        self._height.setValue(800)
        self._height.valueChanged.connect(
            lambda v: self._emit_change("canvas_height", v)
        )
        size_layout.addWidget(self._height, 1, 1)

        layout.addWidget(size_group)

        # 背景设置组
        bg_group = QGroupBox("背景")
        bg_layout = QHBoxLayout(bg_group)

        bg_layout.addWidget(QLabel("颜色:"))
        self._bg_color = ColorButton((255, 255, 255))
        self._bg_color.color_changed.connect(
            lambda c: self._emit_change("background_color", c)
        )
        bg_layout.addWidget(self._bg_color)
        bg_layout.addStretch()

        layout.addWidget(bg_group)

        # 提示
        hint_label = QLabel("选择图层以编辑其属性")
        hint_label.setStyleSheet("color: gray; font-style: italic;")
        hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint_label)

        layout.addStretch()

    def set_template(
        self,
        width: int,
        height: int,
        bg_color: tuple,
    ) -> None:
        """设置模板属性."""
        self._width.blockSignals(True)
        self._width.setValue(width)
        self._width.blockSignals(False)

        self._height.blockSignals(True)
        self._height.setValue(height)
        self._height.blockSignals(False)

        self._bg_color.set_color(bg_color)

    def _emit_change(self, prop: str, value: Any) -> None:
        """发射属性变化信号."""
        self.property_changed.emit(prop, value)


# ===================
# 属性面板主组件
# ===================


class PropertyPanel(QWidget):
    """属性编辑面板.

    根据选中图层类型动态切换属性编辑器。
    """

    # 信号
    layer_property_changed = pyqtSignal(str, str, object)  # layer_id, prop, value
    canvas_property_changed = pyqtSignal(str, object)  # prop, value

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """初始化属性面板."""
        super().__init__(parent)
        self.setAutoFillBackground(True)
        self._current_layer: Optional[AnyLayer] = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        """设置UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # 标题
        title_label = QLabel("属性")
        title_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(title_label)

        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        layout.addWidget(scroll, 1)

        # 堆叠组件
        self._stack = QStackedWidget()
        scroll.setWidget(self._stack)

        # 画布属性编辑器 (索引 0)
        self._canvas_editor = CanvasPropertyEditor()
        self._canvas_editor.property_changed.connect(self._on_canvas_property_changed)
        self._stack.addWidget(self._canvas_editor)

        # 文字属性编辑器 (索引 1)
        self._text_editor = TextPropertyEditor()
        self._text_editor.property_changed.connect(self._on_layer_property_changed)
        self._stack.addWidget(self._text_editor)

        # 形状属性编辑器 (索引 2)
        self._shape_editor = ShapePropertyEditor()
        self._shape_editor.property_changed.connect(self._on_layer_property_changed)
        self._stack.addWidget(self._shape_editor)

        # 图片属性编辑器 (索引 3)
        self._image_editor = ImagePropertyEditor()
        self._image_editor.property_changed.connect(self._on_layer_property_changed)
        self._stack.addWidget(self._image_editor)

    def set_layer(self, layer: Optional[AnyLayer]) -> None:
        """设置当前图层.

        Args:
            layer: 图层数据，None 表示无选中
        """
        self._current_layer = layer

        if layer is None:
            # 显示画布属性
            self._stack.setCurrentIndex(0)
        elif isinstance(layer, TextLayer):
            self._text_editor.set_layer(layer)
            self._stack.setCurrentIndex(1)
        elif isinstance(layer, ShapeLayer):
            self._shape_editor.set_layer(layer)
            self._stack.setCurrentIndex(2)
        elif isinstance(layer, ImageLayer):
            self._image_editor.set_layer(layer)
            self._stack.setCurrentIndex(3)
        else:
            self._stack.setCurrentIndex(0)

    def set_canvas_properties(
        self,
        width: int,
        height: int,
        bg_color: tuple,
    ) -> None:
        """设置画布属性."""
        self._canvas_editor.set_template(width, height, bg_color)

    def update_layer(self) -> None:
        """刷新当前图层显示."""
        if self._current_layer:
            self.set_layer(self._current_layer)

    def _on_layer_property_changed(self, prop: str, value: Any) -> None:
        """图层属性变化."""
        if self._current_layer:
            self.layer_property_changed.emit(self._current_layer.id, prop, value)

    def _on_canvas_property_changed(self, prop: str, value: Any) -> None:
        """画布属性变化."""
        self.canvas_property_changed.emit(prop, value)
