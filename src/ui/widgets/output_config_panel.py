"""输出配置面板.

提供图片输出配置界面，包括：
- 输出格式选择 (JPG/PNG/WebP)
- 质量预设
- 尺寸调整模式
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QRadioButton,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from src.utils.constants import (
    DEFAULT_OUTPUT_HEIGHT,
    DEFAULT_OUTPUT_QUALITY,
    DEFAULT_OUTPUT_WIDTH,
)
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class OutputFormat(Enum):
    """输出格式枚举."""

    JPEG = "JPEG"
    PNG = "PNG"
    WEBP = "WebP"


class QualityPreset(Enum):
    """质量预设枚举."""

    LOW = ("低质量", 60)
    MEDIUM = ("中等", 80)
    HIGH = ("高质量", 95)
    CUSTOM = ("自定义", None)

    def __init__(self, label: str, quality: Optional[int]) -> None:
        self._label = label
        self._quality = quality

    @property
    def label(self) -> str:
        return self._label

    @property
    def quality(self) -> Optional[int]:
        return self._quality


class ResizeMode(Enum):
    """尺寸调整模式枚举."""

    ORIGINAL = ("保持原尺寸", "保持图片原始尺寸不变")
    FIT = ("适应尺寸", "按比例缩放以适应目标尺寸")
    FILL = ("填充尺寸", "缩放并裁剪以填充目标尺寸")
    STRETCH = ("拉伸尺寸", "拉伸图片以匹配目标尺寸")
    CUSTOM = ("自定义尺寸", "指定输出的宽度和高度")

    def __init__(self, label: str, description: str) -> None:
        self._label = label
        self._description = description

    @property
    def label(self) -> str:
        return self._label

    @property
    def description(self) -> str:
        return self._description


class FormatConfigWidget(QWidget):
    """输出格式配置组件."""

    format_changed = pyqtSignal(str)  # 格式名称

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # 格式选择按钮组
        self._btn_group = QButtonGroup(self)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        self._jpeg_radio = QRadioButton("JPEG")
        self._jpeg_radio.setChecked(True)
        self._jpeg_radio.setToolTip("适合照片，文件较小")
        self._btn_group.addButton(self._jpeg_radio)
        btn_layout.addWidget(self._jpeg_radio)

        self._png_radio = QRadioButton("PNG")
        self._png_radio.setToolTip("支持透明背景，无损压缩")
        self._btn_group.addButton(self._png_radio)
        btn_layout.addWidget(self._png_radio)

        self._webp_radio = QRadioButton("WebP")
        self._webp_radio.setToolTip("现代格式，压缩效率高")
        self._btn_group.addButton(self._webp_radio)
        btn_layout.addWidget(self._webp_radio)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # 格式说明
        self._hint_label = QLabel("JPEG: 适合照片，文件较小")
        self._hint_label.setProperty("hint", True)
        layout.addWidget(self._hint_label)

        # 连接信号
        self._btn_group.buttonToggled.connect(self._on_format_changed)

    def _on_format_changed(self, button: QRadioButton, checked: bool) -> None:
        """格式变更."""
        if not checked:
            return

        format_name = button.text()
        if format_name == "JPEG":
            self._hint_label.setText("JPEG: 适合照片，文件较小")
        elif format_name == "PNG":
            self._hint_label.setText("PNG: 支持透明背景，无损压缩")
        elif format_name == "WebP":
            self._hint_label.setText("WebP: 现代格式，压缩效率高")

        self.format_changed.emit(format_name)

    def get_format(self) -> OutputFormat:
        """获取当前格式."""
        if self._jpeg_radio.isChecked():
            return OutputFormat.JPEG
        elif self._png_radio.isChecked():
            return OutputFormat.PNG
        else:
            return OutputFormat.WEBP

    def set_format(self, fmt: OutputFormat) -> None:
        """设置格式."""
        if fmt == OutputFormat.JPEG:
            self._jpeg_radio.setChecked(True)
        elif fmt == OutputFormat.PNG:
            self._png_radio.setChecked(True)
        else:
            self._webp_radio.setChecked(True)


class QualityConfigWidget(QWidget):
    """质量配置组件."""

    quality_changed = pyqtSignal(int)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # 预设选择
        preset_layout = QHBoxLayout()
        preset_layout.setSpacing(8)

        self._preset_combo = QComboBox()
        for preset in QualityPreset:
            self._preset_combo.addItem(preset.label, preset)
        self._preset_combo.setCurrentIndex(2)  # 默认高质量
        self._preset_combo.currentIndexChanged.connect(self._on_preset_changed)
        preset_layout.addWidget(self._preset_combo)

        preset_layout.addStretch()
        layout.addLayout(preset_layout)

        # 质量滑块
        slider_layout = QHBoxLayout()
        slider_layout.setSpacing(8)

        self._quality_slider = QSlider(Qt.Orientation.Horizontal)
        self._quality_slider.setMinimum(1)
        self._quality_slider.setMaximum(100)
        self._quality_slider.setValue(DEFAULT_OUTPUT_QUALITY)
        self._quality_slider.valueChanged.connect(self._on_slider_changed)
        slider_layout.addWidget(self._quality_slider, 1)

        self._quality_label = QLabel(f"{DEFAULT_OUTPUT_QUALITY}%")
        self._quality_label.setFixedWidth(45)
        self._quality_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        slider_layout.addWidget(self._quality_label)

        layout.addLayout(slider_layout)

        # 质量说明
        hint_label = QLabel("较高的质量会产生更大的文件")
        hint_label.setProperty("hint", True)
        layout.addWidget(hint_label)

        # 初始化预设
        self._on_preset_changed(2)

    def _on_preset_changed(self, index: int) -> None:
        """预设变更."""
        preset = self._preset_combo.itemData(index)
        if preset and preset.quality is not None:
            self._quality_slider.setValue(preset.quality)
            self._quality_slider.setEnabled(False)
        else:
            self._quality_slider.setEnabled(True)

    def _on_slider_changed(self, value: int) -> None:
        """滑块值变更."""
        self._quality_label.setText(f"{value}%")

        # 更新预设
        current_preset = self._preset_combo.currentData()
        if current_preset != QualityPreset.CUSTOM:
            # 检查是否匹配预设
            matched = False
            for i, preset in enumerate(QualityPreset):
                if preset.quality == value:
                    self._preset_combo.blockSignals(True)
                    self._preset_combo.setCurrentIndex(i)
                    self._preset_combo.blockSignals(False)
                    matched = True
                    break

            if not matched:
                # 切换到自定义
                self._preset_combo.blockSignals(True)
                self._preset_combo.setCurrentIndex(
                    list(QualityPreset).index(QualityPreset.CUSTOM)
                )
                self._preset_combo.blockSignals(False)

        self.quality_changed.emit(value)

    def get_quality(self) -> int:
        """获取当前质量."""
        return self._quality_slider.value()

    def set_quality(self, quality: int) -> None:
        """设置质量."""
        self._quality_slider.setValue(quality)


class ResizeConfigWidget(QWidget):
    """尺寸调整配置组件."""

    resize_changed = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # 模式选择
        self._mode_combo = QComboBox()
        for mode in ResizeMode:
            self._mode_combo.addItem(mode.label, mode)
        self._mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        layout.addWidget(self._mode_combo)

        # 模式说明
        self._mode_hint = QLabel()
        self._mode_hint.setProperty("hint", True)
        self._mode_hint.setWordWrap(True)
        layout.addWidget(self._mode_hint)

        # 尺寸输入区域
        self._size_container = QWidget()
        size_layout = QGridLayout(self._size_container)
        size_layout.setContentsMargins(0, 4, 0, 0)
        size_layout.setSpacing(8)

        # 宽度
        width_label = QLabel("宽度:")
        size_layout.addWidget(width_label, 0, 0)

        self._width_spinbox = QSpinBox()
        self._width_spinbox.setMinimum(100)
        self._width_spinbox.setMaximum(4096)
        self._width_spinbox.setValue(DEFAULT_OUTPUT_WIDTH)
        self._width_spinbox.setSuffix(" px")
        self._width_spinbox.valueChanged.connect(lambda: self.resize_changed.emit())
        size_layout.addWidget(self._width_spinbox, 0, 1)

        # 高度
        height_label = QLabel("高度:")
        size_layout.addWidget(height_label, 1, 0)

        self._height_spinbox = QSpinBox()
        self._height_spinbox.setMinimum(100)
        self._height_spinbox.setMaximum(4096)
        self._height_spinbox.setValue(DEFAULT_OUTPUT_HEIGHT)
        self._height_spinbox.setSuffix(" px")
        self._height_spinbox.valueChanged.connect(lambda: self.resize_changed.emit())
        size_layout.addWidget(self._height_spinbox, 1, 1)

        layout.addWidget(self._size_container)

        # 初始化状态
        self._on_mode_changed(0)

    def _on_mode_changed(self, index: int) -> None:
        """模式变更."""
        mode = self._mode_combo.itemData(index)
        if mode:
            self._mode_hint.setText(mode.description)

            # 根据模式显示/隐藏尺寸输入
            show_size = mode not in (ResizeMode.ORIGINAL,)
            self._size_container.setVisible(show_size)

        self.resize_changed.emit()

    def get_mode(self) -> ResizeMode:
        """获取当前模式."""
        return self._mode_combo.currentData()

    def set_mode(self, mode: ResizeMode) -> None:
        """设置模式."""
        for i in range(self._mode_combo.count()):
            if self._mode_combo.itemData(i) == mode:
                self._mode_combo.setCurrentIndex(i)
                break

    def get_size(self) -> tuple[int, int]:
        """获取目标尺寸."""
        return self._width_spinbox.value(), self._height_spinbox.value()

    def set_size(self, width: int, height: int) -> None:
        """设置目标尺寸."""
        self._width_spinbox.setValue(width)
        self._height_spinbox.setValue(height)


class OutputConfigPanel(QFrame):
    """输出配置面板.

    提供图片输出相关配置，包括格式、质量和尺寸设置。

    Signals:
        config_changed: 配置变更信号
    """

    config_changed = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setProperty("configPanel", True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # 标题
        title_label = QLabel("输出配置")
        title_label.setProperty("heading", True)
        layout.addWidget(title_label)

        # 格式配置
        format_group = QGroupBox("输出格式")
        format_layout = QVBoxLayout(format_group)
        format_layout.setContentsMargins(8, 8, 8, 8)

        self._format_widget = FormatConfigWidget()
        self._format_widget.format_changed.connect(lambda _: self.config_changed.emit())
        format_layout.addWidget(self._format_widget)

        layout.addWidget(format_group)

        # 质量配置
        quality_group = QGroupBox("输出质量")
        quality_layout = QVBoxLayout(quality_group)
        quality_layout.setContentsMargins(8, 8, 8, 8)

        self._quality_widget = QualityConfigWidget()
        self._quality_widget.quality_changed.connect(lambda _: self.config_changed.emit())
        quality_layout.addWidget(self._quality_widget)

        layout.addWidget(quality_group)

        # 尺寸配置
        resize_group = QGroupBox("尺寸调整")
        resize_layout = QVBoxLayout(resize_group)
        resize_layout.setContentsMargins(8, 8, 8, 8)

        self._resize_widget = ResizeConfigWidget()
        self._resize_widget.resize_changed.connect(self.config_changed.emit)
        resize_layout.addWidget(self._resize_widget)

        layout.addWidget(resize_group)

    def get_config(self) -> dict:
        """获取当前配置.

        Returns:
            配置字典
        """
        return {
            "format": self._format_widget.get_format(),
            "quality": self._quality_widget.get_quality(),
            "resize_mode": self._resize_widget.get_mode(),
            "output_size": self._resize_widget.get_size(),
        }

    def set_config(self, config: dict) -> None:
        """设置配置.

        Args:
            config: 配置字典
        """
        if "format" in config:
            self._format_widget.set_format(config["format"])

        if "quality" in config:
            self._quality_widget.set_quality(config["quality"])

        if "resize_mode" in config:
            self._resize_widget.set_mode(config["resize_mode"])

        if "output_size" in config:
            width, height = config["output_size"]
            self._resize_widget.set_size(width, height)

    def get_format(self) -> OutputFormat:
        """获取输出格式."""
        return self._format_widget.get_format()

    def get_quality(self) -> int:
        """获取输出质量."""
        return self._quality_widget.get_quality()

    def get_resize_mode(self) -> ResizeMode:
        """获取尺寸调整模式."""
        return self._resize_widget.get_mode()

    def get_output_size(self) -> tuple[int, int]:
        """获取输出尺寸."""
        return self._resize_widget.get_size()
