"""AIConfigPanel 组件单元测试."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from PyQt6.QtWidgets import QApplication, QLineEdit

from src.models.api_config import APIConfig
from src.ui.widgets.ai_config_panel import AIConfigPanel


@pytest.fixture(scope="module")
def app():
    """创建 Qt 应用实例."""
    application = QApplication.instance()
    if not application:
        application = QApplication([])
    yield application


@pytest.fixture
def config_manager_mock():
    """Mock ConfigManager."""
    with patch("src.ui.widgets.ai_config_panel.get_config") as mock:
        manager = MagicMock()
        manager.get_user_config.return_value = {}
        mock.return_value = manager
        yield manager


@pytest.fixture
def panel(app, config_manager_mock):
    """创建 AIConfigPanel 实例."""
    widget = AIConfigPanel()
    yield widget
    widget.close()


class TestAIConfigPanelInit:
    """测试 AIConfigPanel 初始化."""

    def test_init_default(self, app, config_manager_mock):
        """测试默认初始化."""
        widget = AIConfigPanel()
        assert widget._api_key_input.text() == ""
        assert widget._api_key_input.echoMode() == QLineEdit.EchoMode.Password
        widget.close()

    def test_init_with_config(self, app, config_manager_mock):
        """测试带配置初始化."""
        config_manager_mock.get_user_config.return_value = {
            "api_key": "sk-test",
            "model": {"model": "qwen-image-edit-plus"}
        }
        widget = AIConfigPanel()
        assert widget._api_key_input.text() == "sk-test"
        assert widget._model_combo.currentText() == "qwen-image-edit-plus"
        widget.close()


class TestAIConfigPanelUI:
    """测试 AIConfigPanel UI 交互."""

    def test_toggle_visibility(self, panel):
        """测试切换可见性."""
        # 初始状态：密码模式
        assert panel._api_key_input.echoMode() == QLineEdit.EchoMode.Password
        assert not panel._is_password_visible

        # 切换显示
        panel._toggle_api_key_visibility()
        assert panel._api_key_input.echoMode() == QLineEdit.EchoMode.Normal
        assert panel._is_password_visible

        # 切换隐藏
        panel._toggle_api_key_visibility()
        assert panel._api_key_input.echoMode() == QLineEdit.EchoMode.Password
        assert not panel._is_password_visible

    def test_save_config_empty_key(self, panel):
        """测试保存空 Key."""
        panel._api_key_input.setText("")
        
        # Mock QMessageBox to prevent blocking
        with patch("src.ui.widgets.ai_config_panel.QMessageBox.warning") as mock_msg:
            panel._save_config()
            mock_msg.assert_called_once()
            
        # 验证配置未保存
        panel._config_manager.set_user_config.assert_not_called()

    def test_save_config_valid(self, panel):
        """测试保存有效配置."""
        panel._api_key_input.setText("sk-valid-key")
        panel._model_combo.setCurrentIndex(0)
        
        with patch("src.ui.widgets.ai_config_panel.QMessageBox.information") as mock_msg:
            # 监听信号
            signal_handler = MagicMock()
            panel.config_changed.connect(signal_handler)
            
            panel._save_config()
            
            mock_msg.assert_called_once()
            signal_handler.assert_called_once()
            
            # 验证 ConfigManager 调用
            panel._config_manager.set_user_config.assert_called_once()
            args = panel._config_manager.set_user_config.call_args
            assert args[0][0] == "api_config"
            assert args[0][1]["api_key"] == "sk-valid-key"

    def test_test_connection_no_key(self, panel):
        """测试无 Key 连接测试."""
        panel._api_key_input.setText("")
        
        with patch("src.ui.widgets.ai_config_panel.QMessageBox.warning") as mock_msg:
            panel._test_connection()
            mock_msg.assert_called_once()

    def test_test_connection_valid(self, panel):
        """测试有效 Key 连接测试."""
        panel._api_key_input.setText("sk-test")
        
        with patch("src.ui.widgets.ai_config_panel.QMessageBox.information") as mock_msg:
            with patch("src.ui.widgets.ai_config_panel.AIService") as mock_service:
                panel._test_connection()
                mock_service.assert_called() # 验证服务是否实例化
                mock_msg.assert_called_once()
