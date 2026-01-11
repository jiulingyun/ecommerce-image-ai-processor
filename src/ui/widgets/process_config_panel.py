"""处理参数配置面板组件.

提供背景颜色、边框宽度、文字内容等后期处理参数的配置界面。
"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QColorDialog,
    QComboBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from src.models.process_config import (
    AI_BACKGROUND_PRESETS,
    AI_ENHANCE_PRESETS,
    AIEditingConfig,
    AIEditingMode,
    BackgroundConfig,
    BackgroundMode,
    BorderConfig,
    BorderStyle,
    BORDER_STYLE_NAMES,
    PresetColor,
    PRESET_COLOR_VALUES,
    ProcessConfig,
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
    """背景配置子面板.
    
    支持纯色填充和 AI 生成背景两种模式。
    """

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
        self._enabled_checkbox = QCheckBox("启用背景抠图与填充")
        self._enabled_checkbox.setChecked(True)
        layout.addWidget(self._enabled_checkbox)

        # 背景模式切换
        mode_layout = QHBoxLayout()
        mode_label = QLabel("背景模式:")
        mode_layout.addWidget(mode_label)

        self._mode_group = QButtonGroup(self)
        self._solid_radio = QRadioButton("纯色填充")
        self._solid_radio.setChecked(True)
        self._ai_radio = QRadioButton("AI 生成")
        self._mode_group.addButton(self._solid_radio, 0)
        self._mode_group.addButton(self._ai_radio, 1)
        mode_layout.addWidget(self._solid_radio)
        mode_layout.addWidget(self._ai_radio)
        mode_layout.addStretch()
        layout.addLayout(mode_layout)

        # 堆叠组件：纯色模式 / AI 模式
        self._mode_stack = QStackedWidget()
        layout.addWidget(self._mode_stack)

        # === 纯色模式面板 ===
        solid_panel = QWidget()
        solid_layout = QVBoxLayout(solid_panel)
        solid_layout.setContentsMargins(0, 0, 0, 0)
        solid_layout.setSpacing(8)

        # 预设颜色网格
        preset_label = QLabel("预设颜色:")
        solid_layout.addWidget(preset_label)

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

        solid_layout.addLayout(preset_grid)

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
        solid_layout.addLayout(custom_layout)

        self._mode_stack.addWidget(solid_panel)

        # === AI 模式面板 ===
        ai_panel = QWidget()
        ai_layout = QVBoxLayout(ai_panel)
        ai_layout.setContentsMargins(0, 0, 0, 0)
        ai_layout.setSpacing(8)

        # AI 预设选择
        preset_ai_layout = QHBoxLayout()
        preset_ai_label = QLabel("预设场景:")
        preset_ai_layout.addWidget(preset_ai_label)

        self._ai_preset_combo = QComboBox()
        for key, info in AI_BACKGROUND_PRESETS.items():
            self._ai_preset_combo.addItem(info["name"], key)
        preset_ai_layout.addWidget(self._ai_preset_combo, 1)
        ai_layout.addLayout(preset_ai_layout)

        # AI 提示词输入
        prompt_label = QLabel("提示词:")
        ai_layout.addWidget(prompt_label)

        self._ai_prompt_input = QPlainTextEdit()
        self._ai_prompt_input.setPlaceholderText("描述你想要的背景效果...")
        self._ai_prompt_input.setMaximumHeight(80)
        # 设置默认提示词
        default_prompt = AI_BACKGROUND_PRESETS.get("clean_white", {}).get("prompt", "")
        self._ai_prompt_input.setPlainText(default_prompt)
        ai_layout.addWidget(self._ai_prompt_input)

        self._mode_stack.addWidget(ai_panel)

        # 默认选中白色
        self._preset_buttons[PresetColor.WHITE].setChecked(True)

    def _connect_signals(self) -> None:
        self._enabled_checkbox.toggled.connect(self._on_config_changed)
        self._mode_group.idClicked.connect(self._on_mode_changed)
        self._custom_color_btn.color_changed.connect(self._on_custom_color_changed)
        self._hex_input.editingFinished.connect(self._on_hex_input_changed)
        self._ai_preset_combo.currentIndexChanged.connect(self._on_ai_preset_changed)
        self._ai_prompt_input.textChanged.connect(self._on_ai_prompt_changed)

    def _on_mode_changed(self, button_id: int) -> None:
        """背景模式切换."""
        if self._is_updating:
            return
        self._mode_stack.setCurrentIndex(button_id)
        self._rebuild_config()
        self._emit_config_changed()

    def _on_ai_preset_changed(self, index: int) -> None:
        """AI 预设选择变更."""
        if self._is_updating:
            return
        preset_key = self._ai_preset_combo.currentData()
        preset_info = AI_BACKGROUND_PRESETS.get(preset_key, {})
        prompt = preset_info.get("prompt", "")
        
        # 如果不是自定义，自动填充提示词
        if preset_key != "custom":
            self._is_updating = True
            self._ai_prompt_input.setPlainText(prompt)
            self._is_updating = False
        else:
            # 自定义模式清空提示词
            self._is_updating = True
            self._ai_prompt_input.setPlainText("")
            self._is_updating = False
        
        self._rebuild_config()
        self._emit_config_changed()

    def _on_ai_prompt_changed(self) -> None:
        """AI 提示词变更."""
        if self._is_updating:
            return
        self._rebuild_config()
        self._emit_config_changed()

    def _on_preset_selected(self, preset: PresetColor) -> None:
        if self._is_updating:
            return
        # 取消其他预设按钮的选中状态
        for p, btn in self._preset_buttons.items():
            btn.setChecked(p == preset)
        self._rebuild_config()
        self._update_custom_display()
        self._emit_config_changed()

    def _on_custom_color_changed(self, color: tuple[int, int, int]) -> None:
        if self._is_updating:
            return
        # 取消所有预设按钮选中
        for btn in self._preset_buttons.values():
            btn.setChecked(False)
        self._hex_input.setText(rgb_to_hex(color))
        self._rebuild_config()
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
            self._rebuild_config()
            self._emit_config_changed()
        except ValueError:
            pass  # 无效的颜色格式，忽略

    def _on_config_changed(self) -> None:
        if self._is_updating:
            return
        self._rebuild_config()
        self._emit_config_changed()

    def _rebuild_config(self) -> None:
        """根据 UI 状态重建配置."""
        is_ai_mode = self._ai_radio.isChecked()
        
        if is_ai_mode:
            # AI 模式
            self._config = BackgroundConfig(
                enabled=self._enabled_checkbox.isChecked(),
                mode=BackgroundMode.AI_GENERATED,
                ai_preset=self._ai_preset_combo.currentData() or "clean_white",
                ai_prompt=self._ai_prompt_input.toPlainText(),
            )
        else:
            # 纯色模式
            # 获取当前选中的预设颜色
            selected_preset = PresetColor.CUSTOM
            for preset, btn in self._preset_buttons.items():
                if btn.isChecked():
                    selected_preset = preset
                    break
            
            self._config = BackgroundConfig(
                enabled=self._enabled_checkbox.isChecked(),
                mode=BackgroundMode.SOLID_COLOR,
                preset=selected_preset,
                color=self._custom_color_btn.color,
            )

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

        # 设置背景模式
        if config.mode == BackgroundMode.AI_GENERATED:
            self._ai_radio.setChecked(True)
            self._mode_stack.setCurrentIndex(1)
            # 设置 AI 预设
            index = self._ai_preset_combo.findData(config.ai_preset)
            if index >= 0:
                self._ai_preset_combo.setCurrentIndex(index)
            # 设置 AI 提示词
            self._ai_prompt_input.setPlainText(config.ai_prompt or config.get_effective_ai_prompt())
        else:
            self._solid_radio.setChecked(True)
            self._mode_stack.setCurrentIndex(0)
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



class AIEditingConfigWidget(QGroupBox):
    """AI 编辑配置子面板.
    
    控制 AI 编辑功能的启用/禁用以及单图增强预设。
    """

    config_changed = pyqtSignal(object)  # AIEditingConfig

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__("AI 图片编辑", parent)
        self._config = AIEditingConfig()
        self._is_updating = False
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # 说明文案
        hint_label = QLabel("单图模式下可启用 AI 增强（双图模式始终使用 AI 合成）")
        hint_label.setProperty("hint", True)
        hint_label.setWordWrap(True)
        layout.addWidget(hint_label)

        # 启用开关（仅控制单图模式的 AI 增强）
        self._enabled_checkbox = QCheckBox("单图模式启用 AI 增强")
        self._enabled_checkbox.setChecked(True)
        self._enabled_checkbox.setToolTip(
            "单图模式：勾选后 AI 将对主图进行增强处理\n"
            "双图模式：始终使用 AI 合成，此开关不影响"
        )
        layout.addWidget(self._enabled_checkbox)

        # 单图增强设置容器
        self._enhance_container = QWidget()
        enhance_layout = QVBoxLayout(self._enhance_container)
        enhance_layout.setContentsMargins(0, 0, 0, 0)
        enhance_layout.setSpacing(8)

        # 增强效果标签
        enhance_hint = QLabel("增强效果选择：")
        enhance_hint.setProperty("hint", True)
        enhance_layout.addWidget(enhance_hint)

        # 增强预设选择
        preset_layout = QHBoxLayout()
        preset_label = QLabel("预设效果:")
        preset_layout.addWidget(preset_label)

        self._enhance_preset_combo = QComboBox()
        for key, info in AI_ENHANCE_PRESETS.items():
            self._enhance_preset_combo.addItem(info["name"], key)
        preset_layout.addWidget(self._enhance_preset_combo, 1)
        enhance_layout.addLayout(preset_layout)

        # 自定义提示词输入
        prompt_label = QLabel("自定义提示词:")
        enhance_layout.addWidget(prompt_label)

        self._enhance_prompt_input = QPlainTextEdit()
        self._enhance_prompt_input.setPlaceholderText("描述你想要的 AI 增强效果...")
        self._enhance_prompt_input.setMaximumHeight(60)
        # 设置默认提示词
        default_prompt = AI_ENHANCE_PRESETS.get("optimize_lighting", {}).get("prompt", "")
        self._enhance_prompt_input.setPlainText(default_prompt)
        enhance_layout.addWidget(self._enhance_prompt_input)

        layout.addWidget(self._enhance_container)

    def _connect_signals(self) -> None:
        self._enabled_checkbox.toggled.connect(self._on_config_changed)
        self._enhance_preset_combo.currentIndexChanged.connect(self._on_preset_changed)
        self._enhance_prompt_input.textChanged.connect(self._on_prompt_changed)

    def _on_preset_changed(self, index: int) -> None:
        """增强预设选择变更."""
        if self._is_updating:
            return
        preset_key = self._enhance_preset_combo.currentData()
        preset_info = AI_ENHANCE_PRESETS.get(preset_key, {})
        prompt = preset_info.get("prompt", "")
        
        # 如果不是自定义，自动填充提示词
        if preset_key != "custom":
            self._is_updating = True
            self._enhance_prompt_input.setPlainText(prompt)
            self._is_updating = False
        else:
            # 自定义模式清空提示词
            self._is_updating = True
            self._enhance_prompt_input.setPlainText("")
            self._is_updating = False
        
        self._rebuild_config()
        self._emit_config_changed()

    def _on_prompt_changed(self) -> None:
        """提示词变更."""
        if self._is_updating:
            return
        self._rebuild_config()
        self._emit_config_changed()

    def _on_config_changed(self) -> None:
        if self._is_updating:
            return
        self._rebuild_config()
        self._emit_config_changed()

    def _rebuild_config(self) -> None:
        """根据 UI 状态重建配置."""
        self._config = AIEditingConfig(
            enabled=self._enabled_checkbox.isChecked(),
            mode=AIEditingMode.COMPOSITE,  # 默认合成模式，实际会根据任务类型自动切换
            enhance_preset=self._enhance_preset_combo.currentData() or "optimize_lighting",
            enhance_prompt=self._enhance_prompt_input.toPlainText(),
        )

    def _emit_config_changed(self) -> None:
        self.config_changed.emit(self._config)

    def get_config(self) -> AIEditingConfig:
        return self._config

    def set_config(self, config: AIEditingConfig) -> None:
        self._is_updating = True
        self._config = config
        self._enabled_checkbox.setChecked(config.enabled)

        # 设置增强预设
        index = self._enhance_preset_combo.findData(config.enhance_preset)
        if index >= 0:
            self._enhance_preset_combo.setCurrentIndex(index)

        # 设置提示词
        self._enhance_prompt_input.setPlainText(
            config.enhance_prompt or config.get_effective_enhance_prompt()
        )

        self._is_updating = False


class ProcessConfigPanel(QFrame):
    """处理参数配置面板.

    提供 AI 编辑、背景、边框等后期处理参数的统一配置界面。

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

        # AI 编辑配置
        self._ai_editing_widget = AIEditingConfigWidget()
        layout.addWidget(self._ai_editing_widget)

        # 背景配置
        self._background_widget = BackgroundConfigWidget()
        layout.addWidget(self._background_widget)

        # 边框配置
        self._border_widget = BorderConfigWidget()
        layout.addWidget(self._border_widget)

    def _connect_signals(self) -> None:
        self._ai_editing_widget.config_changed.connect(self._on_ai_editing_changed)
        self._background_widget.config_changed.connect(self._on_background_changed)
        self._border_widget.config_changed.connect(self._on_border_changed)

    def _on_ai_editing_changed(self, config: AIEditingConfig) -> None:
        self._config = ProcessConfig(
            ai_editing=config,
            prompt=self._config.prompt,
            background=self._config.background,
            border=self._config.border,
            output=self._config.output,
        )
        self.config_changed.emit(self._config)

    def _on_background_changed(self, config: BackgroundConfig) -> None:
        self._config = ProcessConfig(
            ai_editing=self._config.ai_editing,
            prompt=self._config.prompt,
            background=config,
            border=self._config.border,
            output=self._config.output,
        )
        self.config_changed.emit(self._config)

    def _on_border_changed(self, config: BorderConfig) -> None:
        self._config = ProcessConfig(
            ai_editing=self._config.ai_editing,
            prompt=self._config.prompt,
            background=self._config.background,
            border=config,
            output=self._config.output,
        )
        self.config_changed.emit(self._config)

    def get_config(self) -> ProcessConfig:
        """获取当前处理配置."""
        return self._config

    def set_config(self, config: ProcessConfig) -> None:
        """设置处理配置."""
        self._config = config
        self._ai_editing_widget.set_config(config.ai_editing)
        self._background_widget.set_config(config.background)
        self._border_widget.set_config(config.border)

    def get_ai_editing_config(self) -> AIEditingConfig:
        """获取 AI 编辑配置."""
        return self._ai_editing_widget.get_config()

    def get_background_config(self) -> BackgroundConfig:
        """获取背景配置."""
        return self._background_widget.get_config()

    def get_border_config(self) -> BorderConfig:
        """获取边框配置."""
        return self._border_widget.get_config()
