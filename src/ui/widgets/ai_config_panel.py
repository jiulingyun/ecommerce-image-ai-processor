"""AI 配置面板组件."""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.core.config_manager import get_config
from src.models.api_config import APIConfig, AIModelConfig
from src.services.ai_service import AIService
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class AIConfigPanel(QFrame):
    """AI 配置面板.

    提供 AI 服务配置界面，包括 API Key、模型选择和参数设置。

    Signals:
        config_changed: 配置变更信号，参数为 APIConfig 对象
    """

    config_changed = pyqtSignal(object)  # APIConfig

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """初始化 AI 配置面板."""
        super().__init__(parent)
        self._config_manager = get_config()
        # 初始化默认配置
        self._current_config = APIConfig()
        self._is_password_visible = False

        self._setup_ui()
        self._load_config()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """设置 UI."""
        self.setProperty("configPanel", True)
        self.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Preferred,
        )
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)

        # 标题
        title_label = QLabel("AI 服务配置")
        title_label.setProperty("heading", True)
        layout.addWidget(title_label)

        # 1. 服务商配置
        provider_group = QGroupBox("DashScope (通义千问)")
        provider_inner_layout = QVBoxLayout(provider_group)
        provider_inner_layout.setSpacing(12)
        
        # API Key 行
        api_key_label = QLabel("API Key:")
        provider_inner_layout.addWidget(api_key_label)
        
        key_layout = QHBoxLayout()
        key_layout.setSpacing(8)
        
        self._api_key_input = QLineEdit()
        self._api_key_input.setPlaceholderText("sk-...")
        self._api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        key_layout.addWidget(self._api_key_input)
        
        # 显示/隐藏按钮
        self._toggle_key_btn = QPushButton("👁")
        self._toggle_key_btn.setFixedSize(28, 28)
        self._toggle_key_btn.setStyleSheet("""
            QPushButton {
                border: none;
                background-color: transparent;
                border-radius: 4px;
                font-size: 14px;
                padding: 0;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
            }
        """)
        self._toggle_key_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._toggle_key_btn.setToolTip("显示/隐藏 API Key")
        self._toggle_key_btn.clicked.connect(self._toggle_api_key_visibility)
        key_layout.addWidget(self._toggle_key_btn)
        
        provider_inner_layout.addLayout(key_layout)

        # 模型选择行
        model_label = QLabel("模型:")
        provider_inner_layout.addWidget(model_label)
        
        self._model_combo = QComboBox()
        self._model_combo.addItems([
            "wanx-background-generation-v2",
            "qwen-image-edit-plus", 
            "wanx-style-cosplay-v1"
        ])
        provider_inner_layout.addWidget(self._model_combo)
        
        layout.addWidget(provider_group)

        # 2. 连接测试
        self._test_btn = QPushButton("测试连接")
        self._test_btn.setProperty("secondary", True)
        self._test_btn.clicked.connect(self._test_connection)
        layout.addWidget(self._test_btn)

        # 3. 高级设置
        advanced_group = QGroupBox("高级设置")
        advanced_inner_layout = QVBoxLayout(advanced_group)
        advanced_inner_layout.setSpacing(8)
        
        # API Base URL
        url_label = QLabel("API URL:")
        advanced_inner_layout.addWidget(url_label)
        
        self._base_url_input = QLineEdit()
        self._base_url_input.setPlaceholderText("默认")
        self._base_url_input.setEnabled(False)  # 暂时禁用
        advanced_inner_layout.addWidget(self._base_url_input)
        
        layout.addWidget(advanced_group)

        # 底部保存按钮
        self._save_btn = QPushButton("保存配置")
        self._save_btn.setProperty("success", True)
        self._save_btn.clicked.connect(self._save_config)
        layout.addWidget(self._save_btn)

    def _toggle_api_key_visibility(self) -> None:
        """切换 API Key 可见性."""
        self._is_password_visible = not self._is_password_visible
        if self._is_password_visible:
            self._api_key_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self._toggle_key_btn.setText("🔒")
        else:
            self._api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
            self._toggle_key_btn.setText("👁")

    def _load_config(self) -> None:
        """加载配置."""
        # 从 ConfigManager 加载
        config_dict = self._config_manager.get_user_config("api_config", {})
        
        if config_dict:
            try:
                # 尝试解析配置，注意 SecretStr 的处理
                api_key = config_dict.get("api_key")
                model_name = config_dict.get("model", {}).get("model", "wanx-background-generation-v2")
                
                if api_key:
                    self._api_key_input.setText(api_key)
                
                index = self._model_combo.findText(model_name)
                if index >= 0:
                    self._model_combo.setCurrentIndex(index)
                    
                self._current_config = APIConfig(
                    api_key=api_key,
                    model=AIModelConfig(model=model_name)
                )
            except Exception as e:
                logger.error(f"加载 API 配置失败: {e}")

    def _save_config(self) -> None:
        """保存配置."""
        api_key = self._api_key_input.text().strip()
        model_name = self._model_combo.currentText()
        
        if not api_key:
            QMessageBox.warning(self, "警告", "请输入 API Key")
            return
            
        try:
            # 更新当前配置对象
            self._current_config = APIConfig(
                api_key=api_key,
                model=AIModelConfig(model=model_name)
            )
            
            # 保存到 ConfigManager (保存明文 Key 到本地配置，实际生产应加密)
            config_data = {
                "api_key": api_key,
                "model": {
                    "model": model_name
                }
            }
            self._config_manager.set_user_config("api_config", config_data)
            
            self.config_changed.emit(self._current_config)
            QMessageBox.information(self, "成功", "配置已保存")
            logger.info("API 配置已保存")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存配置失败: {e}")
            logger.error(f"保存配置失败: {e}")

    def _connect_signals(self) -> None:
        """连接信号."""
        # 实时配置更新信号可以根据需求添加
        pass

    def _test_connection(self) -> None:
        """测试连接."""
        api_key = self._api_key_input.text().strip()
        if not api_key:
            QMessageBox.warning(self, "提示", "请先输入 API Key")
            return
            
        self._test_btn.setEnabled(False)
        self._test_btn.setText("正在测试...")
        
        # 使用 QTimer 模拟异步调用（实际应该用 asyncio 或 QThread，这里为了简单直接在 UI 线程）
        # 注意：这里直接调用可能会卡顿 UI，但在测试阶段可接受
        # 理想情况是使用 ai_service.health_check()
        
        try:
            # 临时构建服务实例
            config = APIConfig(api_key=api_key)
            service = AIService(config=config)
            
            # TODO: 这里应该异步调用
            # 暂时只做简单的对象创建验证，真正的网络测试需要异步
            # 由于目前没有异步 UI 框架支持，这里简单处理
            
            QMessageBox.information(self, "测试通过", "API 配置格式正确\n(实际连接需在处理时验证)")
            
        except Exception as e:
            QMessageBox.critical(self, "测试失败", f"配置无效: {e}")
        finally:
            self._test_btn.setEnabled(True)
            self._test_btn.setText("测试连接")

