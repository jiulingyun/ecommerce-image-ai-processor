"""模板列表管理组件.

提供模板列表显示和管理功能。

Features:
    - 显示模板列表（含预设和用户模板）
    - 新建、选择、重命名、删除模板
    - 导入/导出模板
"""

from __future__ import annotations

from typing import Optional, List

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QLabel,
    QPushButton,
    QLineEdit,
    QMenu,
    QMessageBox,
    QInputDialog,
    QFileDialog,
    QFrame,
    QSplitter,
    QGroupBox,
)

from src.services.template_manager import TemplateManager, TemplateMetadata
from src.models.template_config import TemplateConfig


# ===================
# 模板列表项
# ===================


class TemplateListItem(QListWidgetItem):
    """模板列表项."""

    def __init__(self, metadata: TemplateMetadata) -> None:
        """初始化."""
        super().__init__()
        self._metadata = metadata
        self._update_display()

    @property
    def metadata(self) -> TemplateMetadata:
        """获取元数据."""
        return self._metadata

    @property
    def template_id(self) -> str:
        """获取模板 ID."""
        return self._metadata.id

    def _update_display(self) -> None:
        """更新显示."""
        m = self._metadata
        prefix = "📋 " if m.is_preset else "📄 "
        self.setText(f"{prefix}{m.name}")
        self.setToolTip(
            f"名称: {m.name}\n"
            f"尺寸: {m.canvas_width}×{m.canvas_height}\n"
            f"图层数: {m.layer_count}\n"
            f"描述: {m.description or '无'}"
        )
        # 预设模板使用不同样式
        if m.is_preset:
            self.setForeground(Qt.GlobalColor.darkBlue)


# ===================
# 模板列表组件
# ===================


class TemplateListWidget(QFrame):
    """模板列表组件.

    显示和管理模板列表。
    """

    # 信号
    template_selected = pyqtSignal(str)  # template_id
    template_created = pyqtSignal(str)  # template_id
    template_deleted = pyqtSignal(str)  # template_id

    def __init__(
        self,
        manager: Optional[TemplateManager] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        """初始化.

        Args:
            manager: 模板管理器
            parent: 父组件
        """
        super().__init__(parent)
        self._manager = manager or TemplateManager()
        self._setup_ui()
        self._refresh_list()

    def _setup_ui(self) -> None:
        """设置 UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # 标题和工具按钮
        header = QHBoxLayout()
        title = QLabel("模板")
        title.setStyleSheet("font-weight: bold;")
        header.addWidget(title)
        header.addStretch()

        # 新建按钮
        self._new_btn = QPushButton("+")
        self._new_btn.setFixedSize(24, 24)
        self._new_btn.setToolTip("新建模板")
        self._new_btn.clicked.connect(self._on_new_template)
        header.addWidget(self._new_btn)

        # 刷新按钮
        self._refresh_btn = QPushButton("⟳")
        self._refresh_btn.setFixedSize(24, 24)
        self._refresh_btn.setToolTip("刷新列表")
        self._refresh_btn.clicked.connect(self._refresh_list)
        header.addWidget(self._refresh_btn)

        layout.addLayout(header)

        # 预设模板组
        preset_group = QGroupBox("预设模板")
        preset_layout = QVBoxLayout(preset_group)
        preset_layout.setContentsMargins(4, 4, 4, 4)

        self._preset_list = QListWidget()
        self._preset_list.setMaximumHeight(150)
        self._preset_list.itemClicked.connect(self._on_preset_clicked)
        self._preset_list.itemDoubleClicked.connect(self._on_preset_double_clicked)
        preset_layout.addWidget(self._preset_list)

        layout.addWidget(preset_group)

        # 我的模板组
        my_group = QGroupBox("我的模板")
        my_layout = QVBoxLayout(my_group)
        my_layout.setContentsMargins(4, 4, 4, 4)

        self._my_list = QListWidget()
        self._my_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._my_list.customContextMenuRequested.connect(self._show_context_menu)
        self._my_list.itemClicked.connect(self._on_my_template_clicked)
        self._my_list.itemDoubleClicked.connect(self._on_my_template_double_clicked)
        my_layout.addWidget(self._my_list)

        layout.addWidget(my_group, 1)

        # 底部操作按钮
        btn_layout = QHBoxLayout()

        self._import_btn = QPushButton("导入")
        self._import_btn.clicked.connect(self._on_import)
        btn_layout.addWidget(self._import_btn)

        self._export_btn = QPushButton("导出")
        self._export_btn.clicked.connect(self._on_export)
        btn_layout.addWidget(self._export_btn)

        btn_layout.addStretch()

        self._delete_btn = QPushButton("删除")
        self._delete_btn.clicked.connect(self._on_delete)
        btn_layout.addWidget(self._delete_btn)

        layout.addLayout(btn_layout)

    def _refresh_list(self) -> None:
        """刷新模板列表."""
        # 清空列表
        self._preset_list.clear()
        self._my_list.clear()

        # 预设模板
        presets = self._manager.get_preset_templates()
        for meta in presets:
            item = TemplateListItem(meta)
            self._preset_list.addItem(item)

        # 用户模板
        all_templates = self._manager.get_template_list(include_presets=False)
        for meta in all_templates:
            if not meta.is_preset:
                item = TemplateListItem(meta)
                self._my_list.addItem(item)

    def _on_preset_clicked(self, item: TemplateListItem) -> None:
        """预设模板点击."""
        self._my_list.clearSelection()

    def _on_preset_double_clicked(self, item: TemplateListItem) -> None:
        """预设模板双击 - 基于预设创建新模板."""
        template = self._manager.load_template(item.template_id)
        if template:
            # 另存为新模板
            name, ok = QInputDialog.getText(
                self,
                "新建模板",
                "请输入模板名称:",
                text=f"{template.name} - 我的版本",
            )
            if ok and name:
                new_template = self._manager.save_template_as(template, name)
                if new_template:
                    self._refresh_list()
                    self.template_created.emit(new_template.id)
                    self.template_selected.emit(new_template.id)

    def _on_my_template_clicked(self, item: TemplateListItem) -> None:
        """用户模板点击."""
        self._preset_list.clearSelection()
        self.template_selected.emit(item.template_id)

    def _on_my_template_double_clicked(self, item: TemplateListItem) -> None:
        """用户模板双击 - 打开模板."""
        self.template_selected.emit(item.template_id)

    def _show_context_menu(self, pos) -> None:
        """显示右键菜单."""
        item = self._my_list.itemAt(pos)
        if not item:
            return

        menu = QMenu(self)

        open_action = menu.addAction("打开")
        open_action.triggered.connect(lambda: self._on_my_template_double_clicked(item))

        rename_action = menu.addAction("重命名")
        rename_action.triggered.connect(lambda: self._on_rename(item))

        menu.addSeparator()

        duplicate_action = menu.addAction("复制")
        duplicate_action.triggered.connect(lambda: self._on_duplicate(item))

        export_action = menu.addAction("导出")
        export_action.triggered.connect(self._on_export)

        menu.addSeparator()

        delete_action = menu.addAction("删除")
        delete_action.triggered.connect(self._on_delete)

        menu.exec(self._my_list.mapToGlobal(pos))

    def _on_new_template(self) -> None:
        """新建模板."""
        name, ok = QInputDialog.getText(
            self,
            "新建模板",
            "请输入模板名称:",
            text="未命名模板",
        )
        if ok and name:
            template = TemplateConfig.create(name)
            if self._manager.save_template(template):
                self._refresh_list()
                self.template_created.emit(template.id)
                self.template_selected.emit(template.id)

    def _on_rename(self, item: TemplateListItem) -> None:
        """重命名模板."""
        name, ok = QInputDialog.getText(
            self,
            "重命名",
            "请输入新名称:",
            text=item.metadata.name,
        )
        if ok and name and name != item.metadata.name:
            if self._manager.rename_template(item.template_id, name):
                self._refresh_list()

    def _on_duplicate(self, item: TemplateListItem) -> None:
        """复制模板."""
        new_template = self._manager.duplicate_template(item.template_id)
        if new_template:
            self._refresh_list()
            self.template_created.emit(new_template.id)

    def _on_delete(self) -> None:
        """删除选中模板."""
        item = self._my_list.currentItem()
        if not item:
            return

        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除模板 \"{item.metadata.name}\" 吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            template_id = item.template_id
            if self._manager.delete_template(template_id):
                self._refresh_list()
                self.template_deleted.emit(template_id)

    def _on_import(self) -> None:
        """导入模板."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "导入模板",
            "",
            "模板文件 (*.template.json);;所有文件 (*)",
        )
        if path:
            template = self._manager.import_template(path)
            if template:
                self._refresh_list()
                self.template_created.emit(template.id)
                QMessageBox.information(
                    self,
                    "导入成功",
                    f"模板 \"{template.name}\" 已导入",
                )
            else:
                QMessageBox.warning(self, "导入失败", "无法导入该模板文件")

    def _on_export(self) -> None:
        """导出选中模板."""
        item = self._my_list.currentItem()
        if not item:
            # 尝试从预设列表获取
            item = self._preset_list.currentItem()
        if not item:
            return

        default_name = f"{item.metadata.name}.template.json"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "导出模板",
            default_name,
            "模板文件 (*.template.json)",
        )
        if path:
            if self._manager.export_template(item.template_id, path):
                QMessageBox.information(
                    self,
                    "导出成功",
                    f"模板已导出到:\n{path}",
                )
            else:
                QMessageBox.warning(self, "导出失败", "无法导出该模板")

    def get_selected_template_id(self) -> Optional[str]:
        """获取选中的模板 ID."""
        item = self._my_list.currentItem()
        if item:
            return item.template_id
        item = self._preset_list.currentItem()
        if item:
            return item.template_id
        return None

    def select_template(self, template_id: str) -> None:
        """选中指定模板."""
        # 先在用户模板中查找
        for i in range(self._my_list.count()):
            item = self._my_list.item(i)
            if isinstance(item, TemplateListItem) and item.template_id == template_id:
                self._my_list.setCurrentItem(item)
                self._preset_list.clearSelection()
                return

        # 再在预设模板中查找
        for i in range(self._preset_list.count()):
            item = self._preset_list.item(i)
            if isinstance(item, TemplateListItem) and item.template_id == template_id:
                self._preset_list.setCurrentItem(item)
                self._my_list.clearSelection()
                return

    def refresh(self) -> None:
        """刷新列表."""
        self._refresh_list()
