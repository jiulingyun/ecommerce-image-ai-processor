"""模板配置面板组件."""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap, QColor, QPainter
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.models.process_config import TemplateRenderConfig
from src.services.template_manager import TemplateManager, TemplateMetadata
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class TemplateConfigPanel(QFrame):
    """模板配置面板.

    提供模板选择和配置界面，用于在处理队列中应用模板渲染。

    Signals:
        config_changed: 配置变更信号，参数为 TemplateRenderConfig 对象
        edit_template_requested: 请求编辑模板信号，参数为模板 ID
    """

    config_changed = pyqtSignal(object)  # TemplateRenderConfig
    edit_template_requested = pyqtSignal(str)  # template_id

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """初始化模板配置面板."""
        super().__init__(parent)
        self._template_manager = TemplateManager()
        self._current_config = TemplateRenderConfig()
        self._template_list: list[TemplateMetadata] = []
        self._is_updating = False

        self._setup_ui()
        self._connect_signals()
        self._refresh_template_list()

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
        title_label = QLabel("模板配置")
        title_label.setProperty("heading", True)
        layout.addWidget(title_label)

        # 1. 启用开关
        enable_group = QGroupBox("模板模式")
        enable_layout = QVBoxLayout(enable_group)
        enable_layout.setSpacing(8)

        self._enable_checkbox = QCheckBox("启用模板渲染")
        self._enable_checkbox.setToolTip("启用后，将使用模板图层覆盖到处理后的图片上")
        enable_layout.addWidget(self._enable_checkbox)

        # 说明文字
        hint_label = QLabel("启用模板模式后，图片将按模板图层进行渲染合成")
        hint_label.setProperty("hint", True)
        hint_label.setWordWrap(True)
        enable_layout.addWidget(hint_label)

        layout.addWidget(enable_group)

        # 2. 模板选择区域
        select_group = QGroupBox("选择模板")
        select_layout = QVBoxLayout(select_group)
        select_layout.setSpacing(8)

        # 模板下拉框
        self._template_combo = QComboBox()
        self._template_combo.setPlaceholderText("请选择模板...")
        select_layout.addWidget(self._template_combo)

        # 模板信息
        self._template_info = QLabel()
        self._template_info.setProperty("hint", True)
        self._template_info.setWordWrap(True)
        select_layout.addWidget(self._template_info)

        # 预览区域
        self._preview_label = QLabel()
        self._preview_label.setFixedHeight(120)
        self._preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview_label.setStyleSheet(
            "background-color: #f0f0f0; border: 1px solid #ddd; border-radius: 4px;"
        )
        self._preview_label.setText("无预览")
        select_layout.addWidget(self._preview_label)

        layout.addWidget(select_group)

        # 3. 渲染选项
        options_group = QGroupBox("渲染选项")
        options_layout = QVBoxLayout(options_group)
        options_layout.setSpacing(8)

        self._use_canvas_size_checkbox = QCheckBox("使用模板画布尺寸")
        self._use_canvas_size_checkbox.setChecked(True)
        self._use_canvas_size_checkbox.setToolTip("启用后，输出图片将使用模板定义的画布尺寸")
        options_layout.addWidget(self._use_canvas_size_checkbox)

        self._skip_invisible_checkbox = QCheckBox("跳过不可见图层")
        self._skip_invisible_checkbox.setChecked(True)
        self._skip_invisible_checkbox.setToolTip("启用后，将跳过模板中标记为不可见的图层")
        options_layout.addWidget(self._skip_invisible_checkbox)

        layout.addWidget(options_group)

        # 4. 操作按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self._refresh_btn = QPushButton("刷新列表")
        self._refresh_btn.setProperty("secondary", True)
        self._refresh_btn.setToolTip("重新加载模板列表")
        btn_layout.addWidget(self._refresh_btn)

        btn_layout.addStretch()

        self._edit_btn = QPushButton("编辑模板")
        self._edit_btn.setProperty("secondary", True)
        self._edit_btn.setToolTip("在模板编辑器中打开当前选中的模板")
        self._edit_btn.setEnabled(False)
        btn_layout.addWidget(self._edit_btn)

        self._new_btn = QPushButton("新建模板")
        self._new_btn.setProperty("success", True)
        self._new_btn.setToolTip("创建新的模板")
        btn_layout.addWidget(self._new_btn)

        layout.addLayout(btn_layout)

        # 初始状态：禁用选择区域
        self._update_enabled_state()

    def _connect_signals(self) -> None:
        """连接信号."""
        self._enable_checkbox.toggled.connect(self._on_enable_changed)
        self._template_combo.currentIndexChanged.connect(self._on_template_changed)
        self._use_canvas_size_checkbox.toggled.connect(self._on_option_changed)
        self._skip_invisible_checkbox.toggled.connect(self._on_option_changed)
        self._refresh_btn.clicked.connect(self._refresh_template_list)
        self._edit_btn.clicked.connect(self._on_edit_clicked)
        self._new_btn.clicked.connect(self._on_new_clicked)

    def _refresh_template_list(self) -> None:
        """刷新模板列表."""
        self._is_updating = True
        try:
            # 保存当前选中的模板 ID
            current_id = self._get_selected_template_id()

            # 清空并重新加载
            self._template_combo.clear()
            self._template_list = self._template_manager.get_template_list(include_presets=True)

            # 添加到下拉框
            for metadata in self._template_list:
                display_name = metadata.name
                if metadata.is_preset:
                    display_name = f"[预设] {metadata.name}"
                self._template_combo.addItem(display_name, metadata.id)

            # 恢复选中状态
            if current_id:
                index = self._template_combo.findData(current_id)
                if index >= 0:
                    self._template_combo.setCurrentIndex(index)

            logger.info(f"已加载 {len(self._template_list)} 个模板")

        finally:
            self._is_updating = False

        # 更新 UI 状态
        self._update_template_info()

    def _get_selected_template_id(self) -> Optional[str]:
        """获取当前选中的模板 ID."""
        return self._template_combo.currentData()

    def _get_selected_metadata(self) -> Optional[TemplateMetadata]:
        """获取当前选中的模板元数据."""
        template_id = self._get_selected_template_id()
        if not template_id:
            return None
        for metadata in self._template_list:
            if metadata.id == template_id:
                return metadata
        return None

    def _update_enabled_state(self) -> None:
        """更新控件启用状态."""
        enabled = self._enable_checkbox.isChecked()
        self._template_combo.setEnabled(enabled)
        self._use_canvas_size_checkbox.setEnabled(enabled)
        self._skip_invisible_checkbox.setEnabled(enabled)
        self._edit_btn.setEnabled(enabled and self._get_selected_template_id() is not None)

    def _update_template_info(self) -> None:
        """更新模板信息显示."""
        metadata = self._get_selected_metadata()
        if metadata:
            info_text = f"尺寸: {metadata.canvas_width}×{metadata.canvas_height}  |  图层: {metadata.layer_count}"
            if metadata.description:
                info_text += f"\n{metadata.description}"
            self._template_info.setText(info_text)
            self._edit_btn.setEnabled(self._enable_checkbox.isChecked())

            # 生成预览
            self._update_preview(metadata)
        else:
            self._template_info.setText("")
            self._preview_label.setText("无预览")
            self._edit_btn.setEnabled(False)

    def _update_preview(self, metadata: TemplateMetadata) -> None:
        """更新模板预览.

        Args:
            metadata: 模板元数据
        """
        try:
            # 加载完整模板以生成预览
            template = self._template_manager.load_template(metadata.id)
            if not template:
                self._preview_label.setText("加载失败")
                return

            # 创建预览图
            preview_width = self._preview_label.width() - 4
            preview_height = self._preview_label.height() - 4

            # 计算缩放比例，保持宽高比
            scale_w = preview_width / template.canvas_width
            scale_h = preview_height / template.canvas_height
            scale = min(scale_w, scale_h)

            scaled_width = int(template.canvas_width * scale)
            scaled_height = int(template.canvas_height * scale)

            # 创建预览 pixmap
            pixmap = QPixmap(scaled_width, scaled_height)
            bg_color = template.background_color
            pixmap.fill(QColor(bg_color[0], bg_color[1], bg_color[2]))

            # 简单预览：只显示背景色和尺寸信息
            painter = QPainter(pixmap)
            painter.setPen(QColor(128, 128, 128))
            painter.drawText(
                pixmap.rect(),
                Qt.AlignmentFlag.AlignCenter,
                f"{template.canvas_width}×{template.canvas_height}\n{template.layer_count} 图层",
            )
            painter.end()

            self._preview_label.setPixmap(pixmap)

        except Exception as e:
            logger.error(f"生成预览失败: {e}")
            self._preview_label.setText("预览失败")

    def _on_enable_changed(self, checked: bool) -> None:
        """启用状态变更."""
        self._update_enabled_state()
        self._update_current_config()
        if not self._is_updating:
            self.config_changed.emit(self._current_config)

    def _on_template_changed(self, index: int) -> None:
        """模板选择变更."""
        if self._is_updating:
            return

        self._update_template_info()
        self._update_current_config()
        self.config_changed.emit(self._current_config)

    def _on_option_changed(self, checked: bool) -> None:
        """选项变更."""
        if self._is_updating:
            return

        self._update_current_config()
        self.config_changed.emit(self._current_config)

    def _update_current_config(self) -> None:
        """更新当前配置对象."""
        self._current_config = TemplateRenderConfig(
            enabled=self._enable_checkbox.isChecked(),
            template_id=self._get_selected_template_id(),
            use_canvas_size=self._use_canvas_size_checkbox.isChecked(),
            skip_invisible_layers=self._skip_invisible_checkbox.isChecked(),
        )

    def _on_edit_clicked(self) -> None:
        """编辑按钮点击."""
        template_id = self._get_selected_template_id()
        if template_id:
            self.edit_template_requested.emit(template_id)

    def _on_new_clicked(self) -> None:
        """新建按钮点击."""
        # 发送空字符串表示新建
        self.edit_template_requested.emit("")

    # ========================
    # 公共接口
    # ========================

    def get_config(self) -> TemplateRenderConfig:
        """获取当前配置.

        Returns:
            当前的模板渲染配置
        """
        self._update_current_config()
        return self._current_config

    def set_config(self, config: TemplateRenderConfig) -> None:
        """设置配置.

        Args:
            config: 模板渲染配置
        """
        self._is_updating = True
        try:
            self._current_config = config
            self._enable_checkbox.setChecked(config.enabled)

            # 设置模板选择
            if config.template_id:
                index = self._template_combo.findData(config.template_id)
                if index >= 0:
                    self._template_combo.setCurrentIndex(index)

            self._use_canvas_size_checkbox.setChecked(config.use_canvas_size)
            self._skip_invisible_checkbox.setChecked(config.skip_invisible_layers)

            self._update_enabled_state()
            self._update_template_info()

        finally:
            self._is_updating = False

    def refresh_templates(self) -> None:
        """刷新模板列表（供外部调用）."""
        self._refresh_template_list()

    def is_enabled(self) -> bool:
        """检查模板模式是否启用.

        Returns:
            是否启用模板模式
        """
        return self._enable_checkbox.isChecked()

    def get_selected_template_id(self) -> Optional[str]:
        """获取选中的模板 ID（供外部调用）.

        Returns:
            模板 ID，未选择返回 None
        """
        return self._get_selected_template_id()
