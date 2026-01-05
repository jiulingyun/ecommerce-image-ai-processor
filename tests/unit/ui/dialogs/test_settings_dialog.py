"""设置对话框单元测试."""

from unittest.mock import MagicMock, patch

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialogButtonBox, QMessageBox

from src.ui.dialogs.settings_dialog import (
    GeneralSettingsWidget,
    OutputSettingsWidget,
    PathSettingsWidget,
    SettingsDialog,
)
from src.utils.constants import (
    DEFAULT_OUTPUT_HEIGHT,
    DEFAULT_OUTPUT_QUALITY,
    DEFAULT_OUTPUT_WIDTH,
)


class TestGeneralSettingsWidget:
    """GeneralSettingsWidget 测试."""

    def test_init(self, qtbot):
        """测试初始化."""
        widget = GeneralSettingsWidget()
        qtbot.addWidget(widget)

        assert widget._log_level_combo is not None
        assert widget._max_queue_spinbox is not None
        assert widget._debug_checkbox is not None
        assert widget._dev_tools_checkbox is not None

    def test_get_settings(self, qtbot):
        """测试获取设置."""
        widget = GeneralSettingsWidget()
        qtbot.addWidget(widget)

        # 设置值
        widget._log_level_combo.setCurrentText("DEBUG")
        widget._max_queue_spinbox.setValue(5)
        widget._debug_checkbox.setChecked(True)
        widget._dev_tools_checkbox.setChecked(True)

        settings = widget.get_settings()

        assert settings["log_level"] == "DEBUG"
        assert settings["max_queue_size"] == 5
        assert settings["debug"] is True
        assert settings["dev_tools"] is True

    def test_set_settings(self, qtbot):
        """测试设置值."""
        widget = GeneralSettingsWidget()
        qtbot.addWidget(widget)

        settings = {
            "log_level": "WARNING",
            "max_queue_size": 8,
            "debug": True,
            "dev_tools": False,
        }
        widget.set_settings(settings)

        assert widget._log_level_combo.currentText() == "WARNING"
        assert widget._max_queue_spinbox.value() == 8
        assert widget._debug_checkbox.isChecked() is True
        assert widget._dev_tools_checkbox.isChecked() is False

    def test_set_settings_partial(self, qtbot):
        """测试设置部分值."""
        widget = GeneralSettingsWidget()
        qtbot.addWidget(widget)

        # 只设置部分值
        settings = {"log_level": "ERROR"}
        widget.set_settings(settings)

        assert widget._log_level_combo.currentText() == "ERROR"

    def test_set_invalid_log_level(self, qtbot):
        """测试设置无效日志级别."""
        widget = GeneralSettingsWidget()
        qtbot.addWidget(widget)

        original_text = widget._log_level_combo.currentText()
        widget.set_settings({"log_level": "INVALID"})

        # 应保持原值
        assert widget._log_level_combo.currentText() == original_text


class TestOutputSettingsWidget:
    """OutputSettingsWidget 测试."""

    def test_init(self, qtbot):
        """测试初始化."""
        widget = OutputSettingsWidget()
        qtbot.addWidget(widget)

        assert widget._width_spinbox is not None
        assert widget._height_spinbox is not None
        assert widget._quality_slider is not None
        assert widget._quality_label is not None

    def test_default_values(self, qtbot):
        """测试默认值."""
        widget = OutputSettingsWidget()
        qtbot.addWidget(widget)

        assert widget._width_spinbox.value() == DEFAULT_OUTPUT_WIDTH
        assert widget._height_spinbox.value() == DEFAULT_OUTPUT_HEIGHT
        assert widget._quality_slider.value() == DEFAULT_OUTPUT_QUALITY

    def test_get_settings(self, qtbot):
        """测试获取设置."""
        widget = OutputSettingsWidget()
        qtbot.addWidget(widget)

        widget._width_spinbox.setValue(1200)
        widget._height_spinbox.setValue(800)
        widget._quality_slider.setValue(85)

        settings = widget.get_settings()

        assert settings["default_output_width"] == 1200
        assert settings["default_output_height"] == 800
        assert settings["default_output_quality"] == 85

    def test_set_settings(self, qtbot):
        """测试设置值."""
        widget = OutputSettingsWidget()
        qtbot.addWidget(widget)

        settings = {
            "default_output_width": 1600,
            "default_output_height": 900,
            "default_output_quality": 75,
        }
        widget.set_settings(settings)

        assert widget._width_spinbox.value() == 1600
        assert widget._height_spinbox.value() == 900
        assert widget._quality_slider.value() == 75
        assert widget._quality_label.text() == "75%"

    def test_quality_slider_updates_label(self, qtbot):
        """测试质量滑块更新标签."""
        widget = OutputSettingsWidget()
        qtbot.addWidget(widget)

        widget._quality_slider.setValue(60)

        assert widget._quality_label.text() == "60%"


class TestPathSettingsWidget:
    """PathSettingsWidget 测试."""

    def test_init(self, qtbot):
        """测试初始化."""
        widget = PathSettingsWidget()
        qtbot.addWidget(widget)

        assert widget._output_dir_input is not None
        assert widget._browse_output_btn is not None

    def test_get_settings_empty(self, qtbot):
        """测试获取空设置."""
        widget = PathSettingsWidget()
        qtbot.addWidget(widget)

        settings = widget.get_settings()

        assert settings["default_output_dir"] is None

    def test_get_settings_with_value(self, qtbot):
        """测试获取有值设置."""
        widget = PathSettingsWidget()
        qtbot.addWidget(widget)

        widget._output_dir_input.setText("/path/to/output")
        settings = widget.get_settings()

        assert settings["default_output_dir"] == "/path/to/output"

    def test_set_settings(self, qtbot):
        """测试设置值."""
        widget = PathSettingsWidget()
        qtbot.addWidget(widget)

        widget.set_settings({"default_output_dir": "/test/path"})

        assert widget._output_dir_input.text() == "/test/path"

    def test_set_settings_empty(self, qtbot):
        """测试设置空值."""
        widget = PathSettingsWidget()
        qtbot.addWidget(widget)

        widget._output_dir_input.setText("/existing/path")
        widget.set_settings({"default_output_dir": None})

        # None 值不应改变已有内容
        assert widget._output_dir_input.text() == "/existing/path"

    def test_output_dir_readonly(self, qtbot):
        """测试输出目录输入框只读."""
        widget = PathSettingsWidget()
        qtbot.addWidget(widget)

        assert widget._output_dir_input.isReadOnly()

    @patch("src.ui.dialogs.settings_dialog.QFileDialog.getExistingDirectory")
    def test_browse_output_dir(self, mock_dialog, qtbot):
        """测试浏览输出目录."""
        mock_dialog.return_value = "/selected/path"

        widget = PathSettingsWidget()
        qtbot.addWidget(widget)

        widget._browse_output_btn.click()

        assert widget._output_dir_input.text() == "/selected/path"

    @patch("src.ui.dialogs.settings_dialog.QFileDialog.getExistingDirectory")
    def test_browse_output_dir_cancel(self, mock_dialog, qtbot):
        """测试取消浏览."""
        mock_dialog.return_value = ""

        widget = PathSettingsWidget()
        qtbot.addWidget(widget)

        widget._output_dir_input.setText("/original/path")
        widget._browse_output_btn.click()

        # 取消时不应改变
        assert widget._output_dir_input.text() == "/original/path"


class TestSettingsDialog:
    """SettingsDialog 测试."""

    @patch("src.ui.dialogs.settings_dialog.get_config")
    def test_init(self, mock_get_config, qtbot):
        """测试初始化."""
        mock_config = MagicMock()
        mock_config.settings = MagicMock(
            log_level="INFO",
            max_queue_size=3,
            debug=False,
            dev_tools=False,
            default_output_width=800,
            default_output_height=800,
            default_output_quality=95,
        )
        mock_config._load_user_config.return_value = {}
        mock_get_config.return_value = mock_config

        dialog = SettingsDialog()
        qtbot.addWidget(dialog)

        assert dialog._tab_widget is not None
        assert dialog._general_widget is not None
        assert dialog._output_widget is not None
        assert dialog._path_widget is not None
        assert dialog._button_box is not None
        assert dialog._reset_btn is not None

    @patch("src.ui.dialogs.settings_dialog.get_config")
    def test_window_properties(self, mock_get_config, qtbot):
        """测试窗口属性."""
        mock_config = MagicMock()
        mock_config.settings = MagicMock(
            log_level="INFO",
            max_queue_size=3,
            debug=False,
            dev_tools=False,
            default_output_width=800,
            default_output_height=800,
            default_output_quality=95,
        )
        mock_config._load_user_config.return_value = {}
        mock_get_config.return_value = mock_config

        dialog = SettingsDialog()
        qtbot.addWidget(dialog)

        assert dialog.windowTitle() == "应用设置"
        assert dialog.minimumWidth() == 500
        assert dialog.minimumHeight() == 450

    @patch("src.ui.dialogs.settings_dialog.get_config")
    def test_tabs(self, mock_get_config, qtbot):
        """测试标签页."""
        mock_config = MagicMock()
        mock_config.settings = MagicMock(
            log_level="INFO",
            max_queue_size=3,
            debug=False,
            dev_tools=False,
            default_output_width=800,
            default_output_height=800,
            default_output_quality=95,
        )
        mock_config._load_user_config.return_value = {}
        mock_get_config.return_value = mock_config

        dialog = SettingsDialog()
        qtbot.addWidget(dialog)

        assert dialog._tab_widget.count() == 3
        assert dialog._tab_widget.tabText(0) == "通用"
        assert dialog._tab_widget.tabText(1) == "输出"
        assert dialog._tab_widget.tabText(2) == "路径"

    @patch("src.ui.dialogs.settings_dialog.get_config")
    def test_load_settings(self, mock_get_config, qtbot):
        """测试加载设置."""
        mock_config = MagicMock()
        mock_config.settings = MagicMock(
            log_level="DEBUG",
            max_queue_size=5,
            debug=True,
            dev_tools=True,
            default_output_width=1200,
            default_output_height=900,
            default_output_quality=80,
        )
        mock_config._load_user_config.return_value = {
            "default_output_dir": "/test/output"
        }
        mock_get_config.return_value = mock_config

        dialog = SettingsDialog()
        qtbot.addWidget(dialog)

        # 验证值已加载
        assert dialog._general_widget._log_level_combo.currentText() == "DEBUG"
        assert dialog._general_widget._max_queue_spinbox.value() == 5
        assert dialog._general_widget._debug_checkbox.isChecked() is True
        assert dialog._output_widget._width_spinbox.value() == 1200
        assert dialog._output_widget._height_spinbox.value() == 900
        assert dialog._output_widget._quality_slider.value() == 80
        assert dialog._path_widget._output_dir_input.text() == "/test/output"

    @patch("src.ui.dialogs.settings_dialog.get_config")
    def test_get_all_settings(self, mock_get_config, qtbot):
        """测试获取所有设置."""
        mock_config = MagicMock()
        mock_config.settings = MagicMock(
            log_level="INFO",
            max_queue_size=3,
            debug=False,
            dev_tools=False,
            default_output_width=800,
            default_output_height=800,
            default_output_quality=95,
        )
        mock_config._load_user_config.return_value = {}
        mock_get_config.return_value = mock_config

        dialog = SettingsDialog()
        qtbot.addWidget(dialog)

        settings = dialog.get_all_settings()

        assert "log_level" in settings
        assert "max_queue_size" in settings
        assert "debug" in settings
        assert "dev_tools" in settings
        assert "default_output_width" in settings
        assert "default_output_height" in settings
        assert "default_output_quality" in settings
        assert "default_output_dir" in settings

    @patch("src.ui.dialogs.settings_dialog.get_config")
    def test_save_settings(self, mock_get_config, qtbot):
        """测试保存设置."""
        mock_config = MagicMock()
        mock_config.settings = MagicMock(
            log_level="INFO",
            max_queue_size=3,
            debug=False,
            dev_tools=False,
            default_output_width=800,
            default_output_height=800,
            default_output_quality=95,
        )
        mock_config._load_user_config.return_value = {}
        mock_get_config.return_value = mock_config

        dialog = SettingsDialog()
        qtbot.addWidget(dialog)

        # 修改设置
        dialog._general_widget._log_level_combo.setCurrentText("WARNING")
        dialog._output_widget._width_spinbox.setValue(1000)

        # 保存
        result = dialog._save_settings()

        assert result is True
        mock_config.save_user_config.assert_called_once()
        mock_config.reload.assert_called_once()

    @patch("src.ui.dialogs.settings_dialog.get_config")
    def test_save_settings_emits_signal(self, mock_get_config, qtbot):
        """测试保存设置发出信号."""
        mock_config = MagicMock()
        mock_config.settings = MagicMock(
            log_level="INFO",
            max_queue_size=3,
            debug=False,
            dev_tools=False,
            default_output_width=800,
            default_output_height=800,
            default_output_quality=95,
        )
        mock_config._load_user_config.return_value = {}
        mock_get_config.return_value = mock_config

        dialog = SettingsDialog()
        qtbot.addWidget(dialog)

        signal_received = []
        dialog.settings_changed.connect(lambda: signal_received.append(True))

        dialog._save_settings()

        assert len(signal_received) == 1

    @patch("src.ui.dialogs.settings_dialog.get_config")
    def test_save_settings_error(self, mock_get_config, qtbot):
        """测试保存设置错误."""
        mock_config = MagicMock()
        mock_config.settings = MagicMock(
            log_level="INFO",
            max_queue_size=3,
            debug=False,
            dev_tools=False,
            default_output_width=800,
            default_output_height=800,
            default_output_quality=95,
        )
        mock_config._load_user_config.return_value = {}
        mock_config.save_user_config.side_effect = Exception("Save error")
        mock_get_config.return_value = mock_config

        dialog = SettingsDialog()
        qtbot.addWidget(dialog)

        with patch.object(QMessageBox, "critical"):
            result = dialog._save_settings()

        assert result is False

    @patch("src.ui.dialogs.settings_dialog.get_config")
    @patch.object(QMessageBox, "question")
    def test_reset_confirmed(self, mock_question, mock_get_config, qtbot):
        """测试确认重置."""
        mock_question.return_value = QMessageBox.StandardButton.Yes

        mock_config = MagicMock()
        mock_config.settings = MagicMock(
            log_level="INFO",
            max_queue_size=3,
            debug=False,
            dev_tools=False,
            default_output_width=800,
            default_output_height=800,
            default_output_quality=95,
        )
        mock_config._load_user_config.return_value = {}
        mock_get_config.return_value = mock_config

        dialog = SettingsDialog()
        qtbot.addWidget(dialog)

        with patch.object(QMessageBox, "information"):
            dialog._on_reset()

        mock_config.reset_to_defaults.assert_called_once()

    @patch("src.ui.dialogs.settings_dialog.get_config")
    @patch.object(QMessageBox, "question")
    def test_reset_cancelled(self, mock_question, mock_get_config, qtbot):
        """测试取消重置."""
        mock_question.return_value = QMessageBox.StandardButton.No

        mock_config = MagicMock()
        mock_config.settings = MagicMock(
            log_level="INFO",
            max_queue_size=3,
            debug=False,
            dev_tools=False,
            default_output_width=800,
            default_output_height=800,
            default_output_quality=95,
        )
        mock_config._load_user_config.return_value = {}
        mock_get_config.return_value = mock_config

        dialog = SettingsDialog()
        qtbot.addWidget(dialog)

        dialog._on_reset()

        mock_config.reset_to_defaults.assert_not_called()

    @patch("src.ui.dialogs.settings_dialog.get_config")
    def test_button_box_buttons(self, mock_get_config, qtbot):
        """测试按钮组."""
        mock_config = MagicMock()
        mock_config.settings = MagicMock(
            log_level="INFO",
            max_queue_size=3,
            debug=False,
            dev_tools=False,
            default_output_width=800,
            default_output_height=800,
            default_output_quality=95,
        )
        mock_config._load_user_config.return_value = {}
        mock_get_config.return_value = mock_config

        dialog = SettingsDialog()
        qtbot.addWidget(dialog)

        ok_btn = dialog._button_box.button(QDialogButtonBox.StandardButton.Ok)
        cancel_btn = dialog._button_box.button(QDialogButtonBox.StandardButton.Cancel)
        apply_btn = dialog._button_box.button(QDialogButtonBox.StandardButton.Apply)

        assert ok_btn is not None
        assert cancel_btn is not None
        assert apply_btn is not None
