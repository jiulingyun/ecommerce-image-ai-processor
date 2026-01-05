"""输出配置面板单元测试."""

import pytest
from PyQt6.QtCore import Qt

from src.ui.widgets.output_config_panel import (
    FormatConfigWidget,
    OutputConfigPanel,
    OutputFormat,
    QualityConfigWidget,
    QualityPreset,
    ResizeConfigWidget,
    ResizeMode,
)
from src.utils.constants import (
    DEFAULT_OUTPUT_HEIGHT,
    DEFAULT_OUTPUT_QUALITY,
    DEFAULT_OUTPUT_WIDTH,
)


class TestOutputFormat:
    """OutputFormat 枚举测试."""

    def test_values(self):
        """测试枚举值."""
        assert OutputFormat.JPEG.value == "JPEG"
        assert OutputFormat.PNG.value == "PNG"
        assert OutputFormat.WEBP.value == "WebP"


class TestQualityPreset:
    """QualityPreset 枚举测试."""

    def test_values(self):
        """测试枚举值."""
        assert QualityPreset.LOW.label == "低质量"
        assert QualityPreset.LOW.quality == 60

        assert QualityPreset.MEDIUM.label == "中等"
        assert QualityPreset.MEDIUM.quality == 80

        assert QualityPreset.HIGH.label == "高质量"
        assert QualityPreset.HIGH.quality == 95

        assert QualityPreset.CUSTOM.label == "自定义"
        assert QualityPreset.CUSTOM.quality is None


class TestResizeMode:
    """ResizeMode 枚举测试."""

    def test_values(self):
        """测试枚举值."""
        assert ResizeMode.ORIGINAL.label == "保持原尺寸"
        assert ResizeMode.FIT.label == "适应尺寸"
        assert ResizeMode.FILL.label == "填充尺寸"
        assert ResizeMode.STRETCH.label == "拉伸尺寸"
        assert ResizeMode.CUSTOM.label == "自定义尺寸"

    def test_descriptions(self):
        """测试描述."""
        assert "原始" in ResizeMode.ORIGINAL.description
        assert "缩放" in ResizeMode.FIT.description


class TestFormatConfigWidget:
    """FormatConfigWidget 测试."""

    def test_init(self, qtbot):
        """测试初始化."""
        widget = FormatConfigWidget()
        qtbot.addWidget(widget)

        assert widget._jpeg_radio is not None
        assert widget._png_radio is not None
        assert widget._webp_radio is not None
        assert widget._hint_label is not None

    def test_default_format(self, qtbot):
        """测试默认格式."""
        widget = FormatConfigWidget()
        qtbot.addWidget(widget)

        assert widget._jpeg_radio.isChecked()
        assert widget.get_format() == OutputFormat.JPEG

    def test_set_format_jpeg(self, qtbot):
        """测试设置 JPEG 格式."""
        widget = FormatConfigWidget()
        qtbot.addWidget(widget)

        widget.set_format(OutputFormat.JPEG)
        assert widget._jpeg_radio.isChecked()
        assert widget.get_format() == OutputFormat.JPEG

    def test_set_format_png(self, qtbot):
        """测试设置 PNG 格式."""
        widget = FormatConfigWidget()
        qtbot.addWidget(widget)

        widget.set_format(OutputFormat.PNG)
        assert widget._png_radio.isChecked()
        assert widget.get_format() == OutputFormat.PNG

    def test_set_format_webp(self, qtbot):
        """测试设置 WebP 格式."""
        widget = FormatConfigWidget()
        qtbot.addWidget(widget)

        widget.set_format(OutputFormat.WEBP)
        assert widget._webp_radio.isChecked()
        assert widget.get_format() == OutputFormat.WEBP

    def test_format_changed_signal(self, qtbot):
        """测试格式变更信号."""
        widget = FormatConfigWidget()
        qtbot.addWidget(widget)

        signals = []
        widget.format_changed.connect(lambda f: signals.append(f))

        widget._png_radio.setChecked(True)
        assert "PNG" in signals

    def test_hint_label_updates(self, qtbot):
        """测试提示标签更新."""
        widget = FormatConfigWidget()
        qtbot.addWidget(widget)

        widget._png_radio.setChecked(True)
        assert "PNG" in widget._hint_label.text()

        widget._webp_radio.setChecked(True)
        assert "WebP" in widget._hint_label.text()


class TestQualityConfigWidget:
    """QualityConfigWidget 测试."""

    def test_init(self, qtbot):
        """测试初始化."""
        widget = QualityConfigWidget()
        qtbot.addWidget(widget)

        assert widget._preset_combo is not None
        assert widget._quality_slider is not None
        assert widget._quality_label is not None

    def test_default_quality(self, qtbot):
        """测试默认质量."""
        widget = QualityConfigWidget()
        qtbot.addWidget(widget)

        # 默认高质量预设
        assert widget._preset_combo.currentIndex() == 2
        assert widget.get_quality() == QualityPreset.HIGH.quality

    def test_get_quality(self, qtbot):
        """测试获取质量."""
        widget = QualityConfigWidget()
        qtbot.addWidget(widget)

        widget._quality_slider.setValue(75)
        assert widget.get_quality() == 75

    def test_set_quality(self, qtbot):
        """测试设置质量."""
        widget = QualityConfigWidget()
        qtbot.addWidget(widget)

        widget.set_quality(50)
        assert widget._quality_slider.value() == 50
        assert widget._quality_label.text() == "50%"

    def test_preset_changes_quality(self, qtbot):
        """测试预设变更更新质量."""
        widget = QualityConfigWidget()
        qtbot.addWidget(widget)

        # 切换到低质量
        widget._preset_combo.setCurrentIndex(0)
        assert widget.get_quality() == QualityPreset.LOW.quality

        # 切换到中等
        widget._preset_combo.setCurrentIndex(1)
        assert widget.get_quality() == QualityPreset.MEDIUM.quality

    def test_slider_disabled_for_preset(self, qtbot):
        """测试预设时滑块禁用."""
        widget = QualityConfigWidget()
        qtbot.addWidget(widget)

        # 预设模式下滑块禁用
        widget._preset_combo.setCurrentIndex(0)
        assert not widget._quality_slider.isEnabled()

        # 自定义模式下滑块启用
        widget._preset_combo.setCurrentIndex(3)  # CUSTOM
        assert widget._quality_slider.isEnabled()

    def test_quality_changed_signal(self, qtbot):
        """测试质量变更信号."""
        widget = QualityConfigWidget()
        qtbot.addWidget(widget)

        # 切换到自定义模式
        widget._preset_combo.setCurrentIndex(3)

        signals = []
        widget.quality_changed.connect(lambda v: signals.append(v))

        widget._quality_slider.setValue(70)
        assert 70 in signals


class TestResizeConfigWidget:
    """ResizeConfigWidget 测试."""

    def test_init(self, qtbot):
        """测试初始化."""
        widget = ResizeConfigWidget()
        qtbot.addWidget(widget)

        assert widget._mode_combo is not None
        assert widget._mode_hint is not None
        assert widget._width_spinbox is not None
        assert widget._height_spinbox is not None

    def test_default_mode(self, qtbot):
        """测试默认模式."""
        widget = ResizeConfigWidget()
        qtbot.addWidget(widget)

        assert widget.get_mode() == ResizeMode.ORIGINAL

    def test_default_size(self, qtbot):
        """测试默认尺寸."""
        widget = ResizeConfigWidget()
        qtbot.addWidget(widget)

        width, height = widget.get_size()
        assert width == DEFAULT_OUTPUT_WIDTH
        assert height == DEFAULT_OUTPUT_HEIGHT

    def test_set_mode(self, qtbot):
        """测试设置模式."""
        widget = ResizeConfigWidget()
        qtbot.addWidget(widget)

        widget.set_mode(ResizeMode.FIT)
        assert widget.get_mode() == ResizeMode.FIT

    def test_set_size(self, qtbot):
        """测试设置尺寸."""
        widget = ResizeConfigWidget()
        qtbot.addWidget(widget)

        widget.set_size(1200, 900)
        width, height = widget.get_size()
        assert width == 1200
        assert height == 900

    def test_size_hidden_for_original_mode(self, qtbot):
        """测试原尺寸模式隐藏尺寸输入."""
        widget = ResizeConfigWidget()
        qtbot.addWidget(widget)
        widget.show()  # 需要显示之后才能测试 isVisible

        widget.set_mode(ResizeMode.ORIGINAL)
        assert widget._size_container.isHidden()

    def test_size_visible_for_other_modes(self, qtbot):
        """测试其他模式显示尺寸输入."""
        widget = ResizeConfigWidget()
        qtbot.addWidget(widget)
        widget.show()  # 需要显示之后才能测试 isVisible

        widget.set_mode(ResizeMode.FIT)
        assert not widget._size_container.isHidden()

        widget.set_mode(ResizeMode.CUSTOM)
        assert not widget._size_container.isHidden()

    def test_mode_hint_updates(self, qtbot):
        """测试模式描述更新."""
        widget = ResizeConfigWidget()
        qtbot.addWidget(widget)

        widget.set_mode(ResizeMode.FIT)
        assert ResizeMode.FIT.description in widget._mode_hint.text()

    def test_resize_changed_signal(self, qtbot):
        """测试尺寸变更信号."""
        widget = ResizeConfigWidget()
        qtbot.addWidget(widget)

        signals = []
        widget.resize_changed.connect(lambda: signals.append(True))

        widget._width_spinbox.setValue(1000)
        assert len(signals) > 0


class TestOutputConfigPanel:
    """OutputConfigPanel 测试."""

    def test_init(self, qtbot):
        """测试初始化."""
        panel = OutputConfigPanel()
        qtbot.addWidget(panel)

        assert panel._format_widget is not None
        assert panel._quality_widget is not None
        assert panel._resize_widget is not None

    def test_get_config(self, qtbot):
        """测试获取配置."""
        panel = OutputConfigPanel()
        qtbot.addWidget(panel)

        config = panel.get_config()

        assert "format" in config
        assert "quality" in config
        assert "resize_mode" in config
        assert "output_size" in config

    def test_set_config(self, qtbot):
        """测试设置配置."""
        panel = OutputConfigPanel()
        qtbot.addWidget(panel)

        config = {
            "format": OutputFormat.PNG,
            "quality": 80,
            "resize_mode": ResizeMode.FIT,
            "output_size": (1600, 1200),
        }
        panel.set_config(config)

        assert panel.get_format() == OutputFormat.PNG
        assert panel.get_quality() == 80
        assert panel.get_resize_mode() == ResizeMode.FIT
        assert panel.get_output_size() == (1600, 1200)

    def test_get_format(self, qtbot):
        """测试获取格式."""
        panel = OutputConfigPanel()
        qtbot.addWidget(panel)

        assert panel.get_format() == OutputFormat.JPEG  # 默认

    def test_get_quality(self, qtbot):
        """测试获取质量."""
        panel = OutputConfigPanel()
        qtbot.addWidget(panel)

        quality = panel.get_quality()
        assert isinstance(quality, int)
        assert 1 <= quality <= 100

    def test_get_resize_mode(self, qtbot):
        """测试获取尺寸模式."""
        panel = OutputConfigPanel()
        qtbot.addWidget(panel)

        mode = panel.get_resize_mode()
        assert isinstance(mode, ResizeMode)

    def test_get_output_size(self, qtbot):
        """测试获取输出尺寸."""
        panel = OutputConfigPanel()
        qtbot.addWidget(panel)

        width, height = panel.get_output_size()
        assert width == DEFAULT_OUTPUT_WIDTH
        assert height == DEFAULT_OUTPUT_HEIGHT

    def test_config_changed_signal(self, qtbot):
        """测试配置变更信号."""
        panel = OutputConfigPanel()
        qtbot.addWidget(panel)

        signals = []
        panel.config_changed.connect(lambda: signals.append(True))

        # 修改格式
        panel._format_widget._png_radio.setChecked(True)
        assert len(signals) > 0

    def test_partial_config(self, qtbot):
        """测试部分配置."""
        panel = OutputConfigPanel()
        qtbot.addWidget(panel)

        # 只设置部分配置
        panel.set_config({"format": OutputFormat.WEBP})
        assert panel.get_format() == OutputFormat.WEBP
        # 其他值保持默认
        assert panel.get_resize_mode() == ResizeMode.ORIGINAL
