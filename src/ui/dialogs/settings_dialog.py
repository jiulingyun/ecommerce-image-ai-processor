"""应用设置对话框.

提供应用级别的设置配置界面，包括：
- 通用设置：日志级别、队列大小等
- 输出设置：默认输出尺寸、质量等
- 路径设置：默认输出目录等
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from src.core.config_manager import get_config
from src.utils.constants import (
    APP_DATA_DIR,
    DEFAULT_OUTPUT_HEIGHT,
    DEFAULT_OUTPUT_QUALITY,
    DEFAULT_OUTPUT_WIDTH,
    MAX_QUEUE_SIZE,
)
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

# 日志级别选项
LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class GeneralSettingsWidget(QWidget):
    """通用设置面板."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # 日志设置组
        log_group = QGroupBox("日志设置")
        log_layout = QFormLayout(log_group)
        log_layout.setSpacing(8)

        self._log_level_combo = QComboBox()
        self._log_level_combo.addItems(LOG_LEVELS)
        log_layout.addRow("日志级别:", self._log_level_combo)

        layout.addWidget(log_group)

        # 队列设置组
        queue_group = QGroupBox("队列设置")
        queue_layout = QFormLayout(queue_group)
        queue_layout.setSpacing(8)

        self._max_queue_spinbox = QSpinBox()
        self._max_queue_spinbox.setMinimum(1)
        self._max_queue_spinbox.setMaximum(10)
        self._max_queue_spinbox.setValue(MAX_QUEUE_SIZE)
        self._max_queue_spinbox.setToolTip("同时处理的最大任务数量")
        queue_layout.addRow("最大队列大小:", self._max_queue_spinbox)

        layout.addWidget(queue_group)

        # 开发选项组
        dev_group = QGroupBox("开发选项")
        dev_layout = QVBoxLayout(dev_group)
        dev_layout.setSpacing(8)

        self._debug_checkbox = QCheckBox("启用调试模式")
        self._debug_checkbox.setToolTip("启用后将输出更详细的日志信息")
        dev_layout.addWidget(self._debug_checkbox)

        self._dev_tools_checkbox = QCheckBox("启用开发工具")
        self._dev_tools_checkbox.setToolTip("启用额外的开发调试工具")
        dev_layout.addWidget(self._dev_tools_checkbox)

        layout.addWidget(dev_group)

        layout.addStretch()

    def get_settings(self) -> dict:
        """获取当前设置."""
        return {
            "log_level": self._log_level_combo.currentText(),
            "max_queue_size": self._max_queue_spinbox.value(),
            "debug": self._debug_checkbox.isChecked(),
            "dev_tools": self._dev_tools_checkbox.isChecked(),
        }

    def set_settings(self, settings: dict) -> None:
        """设置当前值."""
        if "log_level" in settings:
            index = self._log_level_combo.findText(settings["log_level"])
            if index >= 0:
                self._log_level_combo.setCurrentIndex(index)

        if "max_queue_size" in settings:
            self._max_queue_spinbox.setValue(settings["max_queue_size"])

        if "debug" in settings:
            self._debug_checkbox.setChecked(settings["debug"])

        if "dev_tools" in settings:
            self._dev_tools_checkbox.setChecked(settings["dev_tools"])


class OutputSettingsWidget(QWidget):
    """输出设置面板."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # 尺寸设置组
        size_group = QGroupBox("默认输出尺寸")
        size_layout = QFormLayout(size_group)
        size_layout.setSpacing(8)

        # 宽度
        self._width_spinbox = QSpinBox()
        self._width_spinbox.setMinimum(100)
        self._width_spinbox.setMaximum(4096)
        self._width_spinbox.setValue(DEFAULT_OUTPUT_WIDTH)
        self._width_spinbox.setSuffix(" px")
        size_layout.addRow("宽度:", self._width_spinbox)

        # 高度
        self._height_spinbox = QSpinBox()
        self._height_spinbox.setMinimum(100)
        self._height_spinbox.setMaximum(4096)
        self._height_spinbox.setValue(DEFAULT_OUTPUT_HEIGHT)
        self._height_spinbox.setSuffix(" px")
        size_layout.addRow("高度:", self._height_spinbox)

        layout.addWidget(size_group)

        # 质量设置组
        quality_group = QGroupBox("输出质量")
        quality_layout = QVBoxLayout(quality_group)
        quality_layout.setSpacing(8)

        # 质量滑块
        quality_row = QHBoxLayout()
        self._quality_slider = QSlider(Qt.Orientation.Horizontal)
        self._quality_slider.setMinimum(1)
        self._quality_slider.setMaximum(100)
        self._quality_slider.setValue(DEFAULT_OUTPUT_QUALITY)
        self._quality_slider.valueChanged.connect(self._on_quality_changed)
        quality_row.addWidget(self._quality_slider)

        self._quality_label = QLabel(f"{DEFAULT_OUTPUT_QUALITY}%")
        self._quality_label.setFixedWidth(50)
        quality_row.addWidget(self._quality_label)

        quality_layout.addLayout(quality_row)

        # 质量说明
        hint_label = QLabel("较高的质量会产生更大的文件")
        hint_label.setStyleSheet("color: #666; font-size: 11px;")
        quality_layout.addWidget(hint_label)

        layout.addWidget(quality_group)

        layout.addStretch()

    def _on_quality_changed(self, value: int) -> None:
        """质量值变化."""
        self._quality_label.setText(f"{value}%")

    def get_settings(self) -> dict:
        """获取当前设置."""
        return {
            "default_output_width": self._width_spinbox.value(),
            "default_output_height": self._height_spinbox.value(),
            "default_output_quality": self._quality_slider.value(),
        }

    def set_settings(self, settings: dict) -> None:
        """设置当前值."""
        if "default_output_width" in settings:
            self._width_spinbox.setValue(settings["default_output_width"])

        if "default_output_height" in settings:
            self._height_spinbox.setValue(settings["default_output_height"])

        if "default_output_quality" in settings:
            quality = settings["default_output_quality"]
            self._quality_slider.setValue(quality)
            self._quality_label.setText(f"{quality}%")


class PathSettingsWidget(QWidget):
    """路径设置面板."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # 输出目录设置组
        output_group = QGroupBox("输出目录")
        output_layout = QVBoxLayout(output_group)
        output_layout.setSpacing(8)

        # 输出目录选择
        output_row = QHBoxLayout()
        self._output_dir_input = QLineEdit()
        self._output_dir_input.setPlaceholderText("选择默认输出目录...")
        self._output_dir_input.setReadOnly(True)
        output_row.addWidget(self._output_dir_input)

        self._browse_output_btn = QPushButton("浏览...")
        self._browse_output_btn.clicked.connect(self._browse_output_dir)
        output_row.addWidget(self._browse_output_btn)

        output_layout.addLayout(output_row)

        # 说明
        hint_label = QLabel("处理完成的图片将保存到此目录")
        hint_label.setStyleSheet("color: #666; font-size: 11px;")
        output_layout.addWidget(hint_label)

        layout.addWidget(output_group)

        # 数据目录信息组
        data_group = QGroupBox("应用数据")
        data_layout = QFormLayout(data_group)
        data_layout.setSpacing(8)

        # 数据目录（只读）
        data_dir_label = QLabel(str(APP_DATA_DIR))
        data_dir_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        data_dir_label.setStyleSheet("color: #666;")
        data_layout.addRow("数据目录:", data_dir_label)

        # 打开数据目录按钮
        open_data_btn = QPushButton("打开数据目录")
        open_data_btn.clicked.connect(self._open_data_dir)
        data_layout.addRow("", open_data_btn)

        layout.addWidget(data_group)

        layout.addStretch()

    def _browse_output_dir(self) -> None:
        """浏览输出目录."""
        current = self._output_dir_input.text()
        start_dir = current if current else str(Path.home())

        dir_path = QFileDialog.getExistingDirectory(
            self,
            "选择输出目录",
            start_dir,
            QFileDialog.Option.ShowDirsOnly,
        )

        if dir_path:
            self._output_dir_input.setText(dir_path)

    def _open_data_dir(self) -> None:
        """打开数据目录."""
        import subprocess
        import sys

        if sys.platform == "darwin":
            subprocess.run(["open", str(APP_DATA_DIR)])
        elif sys.platform == "win32":
            subprocess.run(["explorer", str(APP_DATA_DIR)])
        else:
            subprocess.run(["xdg-open", str(APP_DATA_DIR)])

    def get_settings(self) -> dict:
        """获取当前设置."""
        output_dir = self._output_dir_input.text().strip()
        return {
            "default_output_dir": output_dir if output_dir else None,
        }

    def set_settings(self, settings: dict) -> None:
        """设置当前值."""
        if "default_output_dir" in settings and settings["default_output_dir"]:
            self._output_dir_input.setText(settings["default_output_dir"])


class SettingsDialog(QDialog):
    """应用设置对话框.

    提供应用级别配置的统一设置界面。

    Signals:
        settings_changed: 设置已变更信号
    """

    settings_changed = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._config_manager = get_config()
        self._setup_ui()
        self._load_settings()

    def _setup_ui(self) -> None:
        """设置 UI."""
        self.setWindowTitle("应用设置")
        self.setMinimumSize(500, 450)
        self.resize(550, 500)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # 标签页
        self._tab_widget = QTabWidget()

        # 通用设置标签页
        self._general_widget = GeneralSettingsWidget()
        self._tab_widget.addTab(self._general_widget, "通用")

        # 输出设置标签页
        self._output_widget = OutputSettingsWidget()
        self._tab_widget.addTab(self._output_widget, "输出")

        # 路径设置标签页
        self._path_widget = PathSettingsWidget()
        self._tab_widget.addTab(self._path_widget, "路径")

        layout.addWidget(self._tab_widget)

        # 按钮区域
        btn_layout = QHBoxLayout()

        # 重置按钮
        self._reset_btn = QPushButton("重置为默认")
        self._reset_btn.clicked.connect(self._on_reset)
        btn_layout.addWidget(self._reset_btn)

        btn_layout.addStretch()

        # 标准按钮
        self._button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Apply
        )
        self._button_box.accepted.connect(self._on_accept)
        self._button_box.rejected.connect(self.reject)
        self._button_box.button(
            QDialogButtonBox.StandardButton.Apply
        ).clicked.connect(self._on_apply)

        btn_layout.addWidget(self._button_box)

        layout.addLayout(btn_layout)

    def _load_settings(self) -> None:
        """从配置管理器加载设置."""
        try:
            # 加载应用设置
            settings = self._config_manager.settings

            general_settings = {
                "log_level": settings.log_level,
                "max_queue_size": settings.max_queue_size,
                "debug": settings.debug,
                "dev_tools": settings.dev_tools,
            }
            self._general_widget.set_settings(general_settings)

            output_settings = {
                "default_output_width": settings.default_output_width,
                "default_output_height": settings.default_output_height,
                "default_output_quality": settings.default_output_quality,
            }
            self._output_widget.set_settings(output_settings)

            # 加载用户配置
            user_config = self._config_manager._load_user_config()
            path_settings = {
                "default_output_dir": user_config.get("default_output_dir"),
            }
            self._path_widget.set_settings(path_settings)

            logger.debug("设置对话框加载完成")

        except Exception as e:
            logger.error(f"加载设置失败: {e}")

    def _save_settings(self) -> bool:
        """保存设置.

        Returns:
            是否保存成功
        """
        try:
            # 收集所有设置
            general = self._general_widget.get_settings()
            output = self._output_widget.get_settings()
            path = self._path_widget.get_settings()

            # 合并并保存
            all_settings = {**general, **output, **path}
            self._config_manager.save_user_config(all_settings)

            # 重新加载配置以应用变更
            self._config_manager.reload()

            self.settings_changed.emit()
            logger.info("设置已保存")
            return True

        except Exception as e:
            logger.error(f"保存设置失败: {e}")
            QMessageBox.critical(self, "错误", f"保存设置失败: {e}")
            return False

    def _on_accept(self) -> None:
        """确定按钮点击."""
        if self._save_settings():
            self.accept()

    def _on_apply(self) -> None:
        """应用按钮点击."""
        if self._save_settings():
            QMessageBox.information(self, "提示", "设置已应用")

    def _on_reset(self) -> None:
        """重置按钮点击."""
        reply = QMessageBox.question(
            self,
            "确认重置",
            "确定要将所有设置重置为默认值吗？\n此操作不可撤销。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                self._config_manager.reset_to_defaults()
                self._load_settings()
                self.settings_changed.emit()
                QMessageBox.information(self, "提示", "设置已重置为默认值")
                logger.info("设置已重置为默认值")
            except Exception as e:
                logger.error(f"重置设置失败: {e}")
                QMessageBox.critical(self, "错误", f"重置设置失败: {e}")

    def get_all_settings(self) -> dict:
        """获取所有当前设置.

        Returns:
            所有设置的字典
        """
        general = self._general_widget.get_settings()
        output = self._output_widget.get_settings()
        path = self._path_widget.get_settings()
        return {**general, **output, **path}
