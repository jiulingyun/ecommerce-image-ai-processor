"""处理参数配置面板组件.

提供背景颜色、边框宽度、文字内容等后期处理参数的配置界面。
"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from src.models.process_config import (
    BackgroundConfig,
    BorderConfig,
    BorderStyle,
    BORDER_STYLE_NAMES,
    PresetColor,
    PRESET_COLOR_VALUES,
    ProcessConfig,
    TextConfig,
    TextPosition,
    TEXT_POSITION_NAMES,
    rgb_to_hex,
    hex_to_rgb,
)
from src.utils.constants import (
    DEFAULT_BORDER_WIDTH,
    MAX_BORDER_WIDTH,
    MIN_BORDER_WIDTH,
)
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

# 预设颜色的中文名称
PRESET_COLOR_NAMES = {
    PresetColor.WHITE: "白色",
    PresetColor.BLACK: "黑色",
    PresetColor.LIGHT_GRAY: "浅灰",
    PresetColor.GRAY: "灰色",
    PresetColor.CREAM: "米色",
    PresetColor.LIGHT_BLUE: "浅蓝",
    PresetColor.LIGHT_PINK: "浅粉",
    PresetColor.LIGHT_GREEN: "浅绿",
}


class ColorButton(QPushButton):
    """颜色选择按钮."""

    color_changed = pyqtSignal(tuple)  # RGB tuple

    def __init__(
        self,
        color: tuple[int, int, int] = (255, 255, 255),
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._color = color
        self.setFixedSize(28, 28)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_style()
        self.clicked.connect(self._on_clicked)

    @property
    def color(self) -> tuple[int, int, int]:
        return self._color

    @color.setter
    def color(self, value: tuple[int, int, int]) -> None:
        self._color = value
        self._update_style()

    def _update_style(self) -> None:
        hex_color = rgb_to_hex(self._color)
        # 根据颜色亮度决定边框颜色
        brightness = (self._color[0] * 299 + self._color[1] * 587 + self._color[2] * 114) / 1000
        border_color = "#d9d9d9" if brightness > 128 else "#666666"
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {hex_color};
                border: 2px solid {border_color};
                border-radius: 4px;
            }}
            QPushButton:hover {{
                border-color: #1890ff;
            }}
        """)

    def _on_clicked(self) -> None:
        color = QColorDialog.getColor(
            QColor(*self._color),
            self,
            "选择颜色",
        )
        if color.isValid():
            self._color = (color.red(), color.green(), color.blue())
            self._update_style()
            self.color_changed.emit(self._color)


class BackgroundConfigWidget(QGroupBox):
    """背景配置子面板."""

    config_changed = pyqtSignal(object)  # BackgroundConfig

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__("背景设置", parent)
        self._config = BackgroundConfig()
        self._is_updating = False
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # 启用开关
        self._enabled_checkbox = QCheckBox("启用背景填充")
        self._enabled_checkbox.setChecked(True)
        layout.addWidget(self._enabled_checkbox)

        # 预设颜色网格
        preset_label = QLabel("预设颜色:")
        layout.addWidget(preset_label)

        preset_grid = QGridLayout()
        preset_grid.setSpacing(4)
        self._preset_buttons: dict[PresetColor, QPushButton] = {}

        row, col = 0, 0
        for preset, rgb in PRESET_COLOR_VALUES.items():
            if preset in (PresetColor.TRANSPARENT, PresetColor.CUSTOM):
                continue

            btn = QPushButton()
            btn.setFixedHeight(28)
            btn.setMinimumWidth(24)
            btn.setToolTip(PRESET_COLOR_NAMES.get(preset, preset.value))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            hex_color = rgb_to_hex(rgb)
            brightness = (rgb[0] * 299 + rgb[1] * 587 + rgb[2] * 114) / 1000
            border_color = "#d9d9d9" if brightness > 128 else "#666666"
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {hex_color};
                    border: 2px solid {border_color};
                    border-radius: 4px;
                }}
                QPushButton:hover {{
                    border-color: #1890ff;
                }}
                QPushButton:checked {{
                    border-color: #1890ff;
                    border-width: 3px;
                }}
            """)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, p=preset: self._on_preset_selected(p))
            self._preset_buttons[preset] = btn
            preset_grid.addWidget(btn, row, col)
            col += 1
            if col >= 4:
                col = 0
                row += 1

        layout.addLayout(preset_grid)

        # 自定义颜色
        custom_layout = QHBoxLayout()
        custom_label = QLabel("自定义:")
        custom_layout.addWidget(custom_label)

        self._custom_color_btn = ColorButton((255, 255, 255))
        custom_layout.addWidget(self._custom_color_btn)

        self._hex_input = QLineEdit()
        self._hex_input.setPlaceholderText("#FFFFFF")
        self._hex_input.setMinimumWidth(75)
        custom_layout.addWidget(self._hex_input, 1)

        custom_layout.addStretch()
        layout.addLayout(custom_layout)

        # 默认选中白色
        self._preset_buttons[PresetColor.WHITE].setChecked(True)

    def _connect_signals(self) -> None:
        self._enabled_checkbox.toggled.connect(self._on_config_changed)
        self._custom_color_btn.color_changed.connect(self._on_custom_color_changed)
        self._hex_input.editingFinished.connect(self._on_hex_input_changed)

    def _on_preset_selected(self, preset: PresetColor) -> None:
        if self._is_updating:
            return
        # 取消其他预设按钮的选中状态
        for p, btn in self._preset_buttons.items():
            btn.setChecked(p == preset)
        self._config = BackgroundConfig(
            enabled=self._enabled_checkbox.isChecked(),
            preset=preset,
        )
        self._update_custom_display()
        self._emit_config_changed()

    def _on_custom_color_changed(self, color: tuple[int, int, int]) -> None:
        if self._is_updating:
            return
        # 取消所有预设按钮选中
        for btn in self._preset_buttons.values():
            btn.setChecked(False)
        self._config = BackgroundConfig(
            enabled=self._enabled_checkbox.isChecked(),
            preset=PresetColor.CUSTOM,
            color=color,
        )
        self._hex_input.setText(rgb_to_hex(color))
        self._emit_config_changed()

    def _on_hex_input_changed(self) -> None:
        if self._is_updating:
            return
        hex_value = self._hex_input.text().strip()
        if not hex_value:
            return
        try:
            rgb = hex_to_rgb(hex_value)
            self._custom_color_btn.color = rgb
            for btn in self._preset_buttons.values():
                btn.setChecked(False)
            self._config = BackgroundConfig(
                enabled=self._enabled_checkbox.isChecked(),
                preset=PresetColor.CUSTOM,
                color=rgb,
            )
            self._emit_config_changed()
        except ValueError:
            pass  # 无效的颜色格式，忽略

    def _on_config_changed(self) -> None:
        if self._is_updating:
            return
        self._config = BackgroundConfig(
            enabled=self._enabled_checkbox.isChecked(),
            preset=self._config.preset,
            color=self._config.color,
        )
        self._emit_config_changed()

    def _update_custom_display(self) -> None:
        color = self._config.get_effective_color()
        self._custom_color_btn.color = color
        self._hex_input.setText(rgb_to_hex(color))

    def _emit_config_changed(self) -> None:
        self.config_changed.emit(self._config)

    def get_config(self) -> BackgroundConfig:
        return self._config

    def set_config(self, config: BackgroundConfig) -> None:
        self._is_updating = True
        self._config = config
        self._enabled_checkbox.setChecked(config.enabled)

        # 更新预设按钮状态
        for preset, btn in self._preset_buttons.items():
            btn.setChecked(preset == config.preset)

        self._update_custom_display()
        self._is_updating = False


class BorderConfigWidget(QGroupBox):
    """边框配置子面板."""

    config_changed = pyqtSignal(object)  # BorderConfig

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__("边框设置", parent)
        self._config = BorderConfig()
        self._is_updating = False
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # 启用开关
        self._enabled_checkbox = QCheckBox("启用边框")
        self._enabled_checkbox.setChecked(False)
        layout.addWidget(self._enabled_checkbox)

        # 边框宽度
        width_layout = QHBoxLayout()
        width_label = QLabel("宽度:")
        width_layout.addWidget(width_label)

        self._width_slider = QSlider(Qt.Orientation.Horizontal)
        self._width_slider.setMinimum(MIN_BORDER_WIDTH)
        self._width_slider.setMaximum(MAX_BORDER_WIDTH)
        self._width_slider.setValue(DEFAULT_BORDER_WIDTH)
        width_layout.addWidget(self._width_slider, 1)

        self._width_spinbox = QSpinBox()
        self._width_spinbox.setMinimum(MIN_BORDER_WIDTH)
        self._width_spinbox.setMaximum(MAX_BORDER_WIDTH)
        self._width_spinbox.setValue(DEFAULT_BORDER_WIDTH)
        self._width_spinbox.setSuffix(" px")
        self._width_spinbox.setMaximumWidth(70)
        width_layout.addWidget(self._width_spinbox)

        layout.addLayout(width_layout)

        # 边框样式
        style_layout = QHBoxLayout()
        style_label = QLabel("样式:")
        style_layout.addWidget(style_label)

        self._style_combo = QComboBox()
        for style in BorderStyle:
            self._style_combo.addItem(BORDER_STYLE_NAMES[style], style.value)
        style_layout.addWidget(self._style_combo, 1)

        layout.addLayout(style_layout)

        # 边框颜色
        color_layout = QHBoxLayout()
        color_label = QLabel("颜色:")
        color_layout.addWidget(color_label)

        self._color_btn = ColorButton((0, 0, 0))
        color_layout.addWidget(self._color_btn)

        self._hex_input = QLineEdit()
        self._hex_input.setPlaceholderText("#000000")
        self._hex_input.setText("#000000")
        self._hex_input.setMinimumWidth(75)
        color_layout.addWidget(self._hex_input, 1)

        layout.addLayout(color_layout)

    def _connect_signals(self) -> None:
        self._enabled_checkbox.toggled.connect(self._on_config_changed)
        self._width_slider.valueChanged.connect(self._on_width_slider_changed)
        self._width_spinbox.valueChanged.connect(self._on_width_spinbox_changed)
        self._style_combo.currentIndexChanged.connect(self._on_config_changed)
        self._color_btn.color_changed.connect(self._on_color_changed)
        self._hex_input.editingFinished.connect(self._on_hex_input_changed)

    def _on_width_slider_changed(self, value: int) -> None:
        if self._is_updating:
            return
        self._is_updating = True
        self._width_spinbox.setValue(value)
        self._is_updating = False
        self._on_config_changed()

    def _on_width_spinbox_changed(self, value: int) -> None:
        if self._is_updating:
            return
        self._is_updating = True
        self._width_slider.setValue(value)
        self._is_updating = False
        self._on_config_changed()

    def _on_color_changed(self, color: tuple[int, int, int]) -> None:
        if self._is_updating:
            return
        self._hex_input.setText(rgb_to_hex(color))
        self._on_config_changed()

    def _on_hex_input_changed(self) -> None:
        if self._is_updating:
            return
        hex_value = self._hex_input.text().strip()
        if not hex_value:
            return
        try:
            rgb = hex_to_rgb(hex_value)
            self._is_updating = True
            self._color_btn.color = rgb
            self._is_updating = False
            self._on_config_changed()
        except ValueError:
            pass

    def _on_config_changed(self) -> None:
        if self._is_updating:
            return
        style_value = self._style_combo.currentData()
        self._config = BorderConfig(
            enabled=self._enabled_checkbox.isChecked(),
            width=self._width_slider.value(),
            style=BorderStyle(style_value) if style_value else BorderStyle.SOLID,
            color=self._color_btn.color,
        )
        self.config_changed.emit(self._config)

    def get_config(self) -> BorderConfig:
        return self._config

    def set_config(self, config: BorderConfig) -> None:
        self._is_updating = True
        self._config = config
        self._enabled_checkbox.setChecked(config.enabled)
        self._width_slider.setValue(config.width)
        self._width_spinbox.setValue(config.width)

        index = self._style_combo.findData(config.style.value)
        if index >= 0:
            self._style_combo.setCurrentIndex(index)

        self._color_btn.color = config.color
        self._hex_input.setText(rgb_to_hex(config.color))
        self._is_updating = False


class TextConfigWidget(QGroupBox):
    """文字配置子面板."""

    config_changed = pyqtSignal(object)  # TextConfig

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__("文字设置", parent)
        self._config = TextConfig()
        self._is_updating = False
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # 启用开关
        self._enabled_checkbox = QCheckBox("启用文字")
        self._enabled_checkbox.setChecked(False)
        layout.addWidget(self._enabled_checkbox)

        # 文字内容
        content_label = QLabel("内容:")
        layout.addWidget(content_label)

        self._content_input = QLineEdit()
        self._content_input.setPlaceholderText("输入文字内容...")
        layout.addWidget(self._content_input)

        # 位置选择
        position_layout = QHBoxLayout()
        position_label = QLabel("位置:")
        position_layout.addWidget(position_label)

        self._position_combo = QComboBox()
        for pos in TextPosition:
            if pos != TextPosition.CUSTOM:
                self._position_combo.addItem(TEXT_POSITION_NAMES[pos], pos.value)
        position_layout.addWidget(self._position_combo, 1)

        layout.addLayout(position_layout)

        # 字体大小
        font_layout = QHBoxLayout()
        font_label = QLabel("大小:")
        font_layout.addWidget(font_label)

        self._font_size_spinbox = QSpinBox()
        self._font_size_spinbox.setMinimum(8)
        self._font_size_spinbox.setMaximum(200)
        self._font_size_spinbox.setValue(14)
        self._font_size_spinbox.setSuffix(" px")
        font_layout.addWidget(self._font_size_spinbox)

        font_layout.addStretch()
        layout.addLayout(font_layout)

        # 文字颜色
        color_layout = QHBoxLayout()
        color_label = QLabel("颜色:")
        color_layout.addWidget(color_label)

        self._color_btn = ColorButton((0, 0, 0))
        color_layout.addWidget(self._color_btn)

        self._hex_input = QLineEdit()
        self._hex_input.setPlaceholderText("#000000")
        self._hex_input.setText("#000000")
        self._hex_input.setMinimumWidth(75)
        color_layout.addWidget(self._hex_input, 1)

        layout.addLayout(color_layout)

    def _connect_signals(self) -> None:
        self._enabled_checkbox.toggled.connect(self._on_config_changed)
        self._content_input.textChanged.connect(self._on_config_changed)
        self._position_combo.currentIndexChanged.connect(self._on_config_changed)
        self._font_size_spinbox.valueChanged.connect(self._on_config_changed)
        self._color_btn.color_changed.connect(self._on_color_changed)
        self._hex_input.editingFinished.connect(self._on_hex_input_changed)

    def _on_color_changed(self, color: tuple[int, int, int]) -> None:
        if self._is_updating:
            return
        self._hex_input.setText(rgb_to_hex(color))
        self._on_config_changed()

    def _on_hex_input_changed(self) -> None:
        if self._is_updating:
            return
        hex_value = self._hex_input.text().strip()
        if not hex_value:
            return
        try:
            rgb = hex_to_rgb(hex_value)
            self._is_updating = True
            self._color_btn.color = rgb
            self._is_updating = False
            self._on_config_changed()
        except ValueError:
            pass

    def _on_config_changed(self) -> None:
        if self._is_updating:
            return
        pos_value = self._position_combo.currentData()
        self._config = TextConfig(
            enabled=self._enabled_checkbox.isChecked(),
            content=self._content_input.text(),
            preset_position=TextPosition(pos_value) if pos_value else TextPosition.BOTTOM_RIGHT,
            font_size=self._font_size_spinbox.value(),
            color=self._color_btn.color,
        )
        self.config_changed.emit(self._config)

    def get_config(self) -> TextConfig:
        return self._config

    def set_config(self, config: TextConfig) -> None:
        self._is_updating = True
        self._config = config
        self._enabled_checkbox.setChecked(config.enabled)
        self._content_input.setText(config.content)

        index = self._position_combo.findData(config.preset_position.value)
        if index >= 0:
            self._position_combo.setCurrentIndex(index)

        self._font_size_spinbox.setValue(config.font_size)
        self._color_btn.color = config.color
        self._hex_input.setText(rgb_to_hex(config.color))
        self._is_updating = False


class ProcessConfigPanel(QFrame):
    """处理参数配置面板.

    提供背景、边框、文字等后期处理参数的统一配置界面。

    Signals:
        config_changed: 配置变更信号，参数为 ProcessConfig 对象
    """

    config_changed = pyqtSignal(object)  # ProcessConfig

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._config = ProcessConfig()
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        self.setProperty("configPanel", True)
        self.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Preferred,
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)

        # 标题
        title_label = QLabel("后期处理配置")
        title_label.setProperty("heading", True)
        layout.addWidget(title_label)

        # 背景配置
        self._background_widget = BackgroundConfigWidget()
        layout.addWidget(self._background_widget)

        # 边框配置
        self._border_widget = BorderConfigWidget()
        layout.addWidget(self._border_widget)

        # 文字配置
        self._text_widget = TextConfigWidget()
        layout.addWidget(self._text_widget)

    def _connect_signals(self) -> None:
        self._background_widget.config_changed.connect(self._on_background_changed)
        self._border_widget.config_changed.connect(self._on_border_changed)
        self._text_widget.config_changed.connect(self._on_text_changed)

    def _on_background_changed(self, config: BackgroundConfig) -> None:
        self._config = ProcessConfig(
            prompt=self._config.prompt,
            background=config,
            border=self._config.border,
            text=self._config.text,
            output=self._config.output,
        )
        self.config_changed.emit(self._config)

    def _on_border_changed(self, config: BorderConfig) -> None:
        self._config = ProcessConfig(
            prompt=self._config.prompt,
            background=self._config.background,
            border=config,
            text=self._config.text,
            output=self._config.output,
        )
        self.config_changed.emit(self._config)

    def _on_text_changed(self, config: TextConfig) -> None:
        self._config = ProcessConfig(
            prompt=self._config.prompt,
            background=self._config.background,
            border=self._config.border,
            text=config,
            output=self._config.output,
        )
        self.config_changed.emit(self._config)

    def get_config(self) -> ProcessConfig:
        """获取当前处理配置."""
        return self._config

    def set_config(self, config: ProcessConfig) -> None:
        """设置处理配置."""
        self._config = config
        self._background_widget.set_config(config.background)
        self._border_widget.set_config(config.border)
        self._text_widget.set_config(config.text)

    def get_background_config(self) -> BackgroundConfig:
        """获取背景配置."""
        return self._background_widget.get_config()

    def get_border_config(self) -> BorderConfig:
        """获取边框配置."""
        return self._border_widget.get_config()

    def get_text_config(self) -> TextConfig:
        """获取文字配置."""
        return self._text_widget.get_config()
