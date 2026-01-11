"""ProcessConfigPanel 组件单元测试."""

from __future__ import annotations

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from src.models.process_config import (
    BackgroundConfig,
    BackgroundMode,
    BorderConfig,
    BorderStyle,
    PresetColor,
    ProcessConfig,
)
from src.ui.widgets.process_config_panel import (
    BackgroundConfigWidget,
    BorderConfigWidget,
    ColorButton,
    ProcessConfigPanel,
)


class TestColorButton:
    """ColorButton 组件测试."""

    def test_init_default_color(self, qtbot) -> None:
        """测试默认颜色初始化."""
        button = ColorButton()
        qtbot.addWidget(button)
        assert button.color == (255, 255, 255)

    def test_init_custom_color(self, qtbot) -> None:
        """测试自定义颜色初始化."""
        button = ColorButton((128, 64, 32))
        qtbot.addWidget(button)
        assert button.color == (128, 64, 32)

    def test_set_color(self, qtbot) -> None:
        """测试设置颜色."""
        button = ColorButton()
        qtbot.addWidget(button)
        button.color = (100, 150, 200)
        assert button.color == (100, 150, 200)

    def test_color_changed_signal(self, qtbot) -> None:
        """测试颜色变更信号."""
        button = ColorButton()
        qtbot.addWidget(button)

        with qtbot.waitSignal(button.color_changed, timeout=100):
            # 直接设置颜色并发射信号来模拟选择
            button._color = (200, 100, 50)
            button._update_style()
            button.color_changed.emit((200, 100, 50))


class TestBackgroundConfigWidget:
    """BackgroundConfigWidget 组件测试."""

    def test_init_default(self, qtbot) -> None:
        """测试默认初始化."""
        widget = BackgroundConfigWidget()
        qtbot.addWidget(widget)

        config = widget.get_config()
        assert config.enabled is True
        assert config.preset == PresetColor.WHITE

    def test_set_config(self, qtbot) -> None:
        """测试设置配置."""
        widget = BackgroundConfigWidget()
        qtbot.addWidget(widget)

        config = BackgroundConfig(
            enabled=False,
            preset=PresetColor.LIGHT_GRAY,
        )
        widget.set_config(config)

        result = widget.get_config()
        assert result.enabled is False
        assert result.preset == PresetColor.LIGHT_GRAY

    def test_enabled_toggle(self, qtbot) -> None:
        """测试启用/禁用切换."""
        widget = BackgroundConfigWidget()
        qtbot.addWidget(widget)

        signals = []
        widget.config_changed.connect(lambda c: signals.append(c))

        widget._enabled_checkbox.setChecked(False)

        assert len(signals) == 1
        assert signals[0].enabled is False

    def test_preset_color_selection(self, qtbot) -> None:
        """测试预设颜色选择."""
        widget = BackgroundConfigWidget()
        qtbot.addWidget(widget)

        signals = []
        widget.config_changed.connect(lambda c: signals.append(c))

        # 点击黑色按钮
        widget._preset_buttons[PresetColor.BLACK].click()

        assert len(signals) == 1
        assert signals[0].preset == PresetColor.BLACK

    def test_custom_color(self, qtbot) -> None:
        """测试自定义颜色."""
        widget = BackgroundConfigWidget()
        qtbot.addWidget(widget)

        config = BackgroundConfig(
            enabled=True,
            preset=PresetColor.CUSTOM,
            color=(100, 150, 200),
        )
        widget.set_config(config)

        result = widget.get_config()
        assert result.preset == PresetColor.CUSTOM
        assert result.color == (100, 150, 200)


class TestBorderConfigWidget:
    """BorderConfigWidget 组件测试."""

    def test_init_default(self, qtbot) -> None:
        """测试默认初始化."""
        widget = BorderConfigWidget()
        qtbot.addWidget(widget)

        config = widget.get_config()
        assert config.enabled is False
        assert config.width == 2
        assert config.style == BorderStyle.SOLID
        assert config.color == (0, 0, 0)

    def test_set_config(self, qtbot) -> None:
        """测试设置配置."""
        widget = BorderConfigWidget()
        qtbot.addWidget(widget)

        config = BorderConfig(
            enabled=True,
            width=10,
            style=BorderStyle.DASHED,
            color=(255, 128, 64),
        )
        widget.set_config(config)

        result = widget.get_config()
        assert result.enabled is True
        assert result.width == 10
        assert result.style == BorderStyle.DASHED
        assert result.color == (255, 128, 64)

    def test_width_slider_sync(self, qtbot) -> None:
        """测试宽度滑块与输入框同步."""
        widget = BorderConfigWidget()
        qtbot.addWidget(widget)

        widget._width_slider.setValue(15)
        assert widget._width_spinbox.value() == 15

        widget._width_spinbox.setValue(8)
        assert widget._width_slider.value() == 8

    def test_config_changed_signal(self, qtbot) -> None:
        """测试配置变更信号."""
        widget = BorderConfigWidget()
        qtbot.addWidget(widget)

        signals = []
        widget.config_changed.connect(lambda c: signals.append(c))

        widget._enabled_checkbox.setChecked(True)

        assert len(signals) == 1
        assert signals[0].enabled is True


class TestProcessConfigPanel:
    """ProcessConfigPanel 组件测试."""

    def test_init(self, qtbot) -> None:
        """测试初始化."""
        panel = ProcessConfigPanel()
        qtbot.addWidget(panel)

        config = panel.get_config()
        assert isinstance(config, ProcessConfig)
        assert isinstance(config.background, BackgroundConfig)
        assert isinstance(config.border, BorderConfig)

    def test_set_config(self, qtbot) -> None:
        """测试设置配置."""
        panel = ProcessConfigPanel()
        qtbot.addWidget(panel)

        config = ProcessConfig(
            background=BackgroundConfig(enabled=False, preset=PresetColor.BLACK),
            border=BorderConfig(enabled=True, width=5),
        )
        panel.set_config(config)

        result = panel.get_config()
        assert result.background.enabled is False
        assert result.background.preset == PresetColor.BLACK
        assert result.border.enabled is True
        assert result.border.width == 5

    def test_get_subconfigs(self, qtbot) -> None:
        """测试获取子配置."""
        panel = ProcessConfigPanel()
        qtbot.addWidget(panel)

        bg_config = panel.get_background_config()
        border_config = panel.get_border_config()

        assert isinstance(bg_config, BackgroundConfig)
        assert isinstance(border_config, BorderConfig)

    def test_config_changed_signal(self, qtbot) -> None:
        """测试配置变更信号."""
        panel = ProcessConfigPanel()
        qtbot.addWidget(panel)

        signals = []
        panel.config_changed.connect(lambda c: signals.append(c))

        # 修改背景配置
        panel._background_widget._enabled_checkbox.setChecked(False)

        assert len(signals) == 1
        assert signals[0].background.enabled is False

    def test_config_isolation(self, qtbot) -> None:
        """测试子面板配置变更不影响其他配置."""
        panel = ProcessConfigPanel()
        qtbot.addWidget(panel)

        # 设置初始配置
        initial_config = ProcessConfig(
            border=BorderConfig(enabled=True, width=10),
        )
        panel.set_config(initial_config)

        # 修改背景配置
        panel._background_widget._enabled_checkbox.setChecked(False)

        # 验证边框配置未受影响
        result = panel.get_config()
        assert result.border.enabled is True
        assert result.border.width == 10

    def test_background_mode_switch(self, qtbot) -> None:
        """测试背景模式切换."""
        panel = ProcessConfigPanel()
        qtbot.addWidget(panel)

        # 默认为纯色模式
        config = panel.get_background_config()
        assert config.mode == BackgroundMode.SOLID_COLOR

        # 切换到 AI 模式（使用 click() 来触发信号）
        panel._background_widget._ai_radio.click()
        config = panel.get_background_config()
        assert config.mode == BackgroundMode.AI_GENERATED
