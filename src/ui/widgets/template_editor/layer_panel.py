"""图层管理面板组件.

提供图层列表显示和管理功能，包括排序、显示/隐藏、锁定等。

Features:
    - 显示所有图层列表
    - 拖拽调整图层顺序
    - 显示/隐藏切换
    - 锁定/解锁
    - 重命名
    - 删除（带确认）
    - 与画布选择同步
"""

from __future__ import annotations

from typing import Optional, List, TYPE_CHECKING

from PyQt6.QtCore import Qt, pyqtSignal, QMimeData, QPoint
from PyQt6.QtGui import QIcon, QDrag, QPixmap, QPainter, QColor
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
    QAbstractItemView,
    QFrame,
    QSizePolicy,
)

from src.models.template_config import (
    LayerType,
    AnyLayer,
    TextLayer,
    ShapeLayer,
    ImageLayer,
)

if TYPE_CHECKING:
    from src.models.template_config import TemplateConfig


# ===================
# 图层项组件
# ===================


class LayerItemWidget(QFrame):
    """图层项显示组件.

    显示单个图层的缩略图、名称和操作按钮。
    """

    # 信号
    visibility_toggled = pyqtSignal(str, bool)  # layer_id, visible
    lock_toggled = pyqtSignal(str, bool)  # layer_id, locked
    delete_requested = pyqtSignal(str)  # layer_id
    rename_requested = pyqtSignal(str, str)  # layer_id, new_name

    def __init__(self, layer: AnyLayer, parent: Optional[QWidget] = None) -> None:
        """初始化图层项组件.

        Args:
            layer: 图层数据
            parent: 父组件
        """
        super().__init__(parent)
        self._layer = layer
        self._is_editing_name = False
        self._is_selected = False

        # 确保背景色能正确应用
        self.setAutoFillBackground(True)
        
        self._setup_ui()
        self._update_display()

    @property
    def layer(self) -> AnyLayer:
        """获取图层数据."""
        return self._layer

    @property
    def layer_id(self) -> str:
        """获取图层ID."""
        return self._layer.id

    def _setup_ui(self) -> None:
        """设置UI."""
        self.setFrameStyle(QFrame.Shape.StyledPanel)
        
        # 使用水平布局，添加足够的内边距
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # 确保整体高度足够容纳内容和边框
        self.setMinimumHeight(48)

        # 图标/缩略图
        self._icon_label = QLabel()
        self._icon_label.setFixedSize(24, 24)
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._icon_label)

        # 名称标签和编辑框
        self._name_label = QLabel()
        self._name_label.setMinimumWidth(80)
        self._name_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout.addWidget(self._name_label)

        self._name_edit = QLineEdit()
        self._name_edit.setVisible(False)
        self._name_edit.returnPressed.connect(self._finish_rename)
        self._name_edit.editingFinished.connect(self._finish_rename)
        layout.addWidget(self._name_edit)

        # 可见性按钮
        self._visibility_btn = QPushButton("显")
        self._visibility_btn.setFixedSize(28, 24)
        self._visibility_btn.setFlat(True)
        self._visibility_btn.setToolTip("显示/隐藏")
        self._visibility_btn.clicked.connect(self._toggle_visibility)
        layout.addWidget(self._visibility_btn)

        # 锁定按钮
        self._lock_btn = QPushButton("锁")
        self._lock_btn.setFixedSize(28, 24)
        self._lock_btn.setFlat(True)
        self._lock_btn.setToolTip("锁定/解锁")
        self._lock_btn.clicked.connect(self._toggle_lock)
        layout.addWidget(self._lock_btn)

    def _update_display(self) -> None:
        """更新显示."""
        layer = self._layer

        # 更新图标
        icon_map = {
            LayerType.TEXT: "文",
            LayerType.RECTANGLE: "矩",
            LayerType.ELLIPSE: "圆",
            LayerType.IMAGE: "图",
        }
        self._icon_label.setText(icon_map.get(layer.type, "?"))

        # 更新名称
        name = self._get_layer_name()
        self._name_label.setText(name)

        # 更新可见性按钮
        self._visibility_btn.setText("显" if layer.visible else "隐")
        self._visibility_btn.setStyleSheet(
            "" if layer.visible else "color: gray;"
        )

        # 更新锁定按钮
        self._lock_btn.setText("锁" if layer.locked else "开")

        # 更新整体样式
        self.setProperty("hidden_layer", not layer.visible)
        self.style().unpolish(self)
        self.style().polish(self)

    def _get_layer_name(self) -> str:
        """获取图层显示名称."""
        layer = self._layer
        if isinstance(layer, TextLayer):
            # 文字图层显示内容预览
            content = layer.content[:15]
            if len(layer.content) > 15:
                content += "..."
            return content or "文字"
        elif isinstance(layer, ShapeLayer):
            return "矩形" if layer.is_rectangle else "椭圆"
        elif isinstance(layer, ImageLayer):
            if layer.image_path:
                from pathlib import Path
                return Path(layer.image_path).name[:15]
            return "图片"
        return f"图层 {layer.id[:6]}"

    def _toggle_visibility(self) -> None:
        """切换可见性."""
        new_visible = not self._layer.visible
        self._layer.visible = new_visible
        self._update_display()
        self.visibility_toggled.emit(self.layer_id, new_visible)

    def _toggle_lock(self) -> None:
        """切换锁定状态."""
        new_locked = not self._layer.locked
        self._layer.locked = new_locked
        self._update_display()
        self.lock_toggled.emit(self.layer_id, new_locked)

    def start_rename(self) -> None:
        """开始重命名."""
        if self._is_editing_name:
            return
        self._is_editing_name = True
        self._name_label.setVisible(False)
        self._name_edit.setVisible(True)
        self._name_edit.setText(self._get_layer_name())
        self._name_edit.selectAll()
        self._name_edit.setFocus()

    def _finish_rename(self) -> None:
        """完成重命名."""
        if not self._is_editing_name:
            return
        self._is_editing_name = False
        new_name = self._name_edit.text().strip()
        self._name_edit.setVisible(False)
        self._name_label.setVisible(True)

        if new_name and new_name != self._get_layer_name():
            # 对于文字图层，更新内容
            if isinstance(self._layer, TextLayer):
                self._layer.content = new_name
                self._update_display()
                self.rename_requested.emit(self.layer_id, new_name)

    def update_from_layer(self) -> None:
        """从图层数据更新显示."""
        self._update_display()

    def set_selected(self, selected: bool) -> None:
        """设置选中状态."""
        if self._is_selected != selected:
            self._is_selected = selected
            self.setProperty("selected", selected)
            # 强制重新应用样式
            self.style().unpolish(self)
            self.style().polish(self)
            self.update()

    def mouseDoubleClickEvent(self, event) -> None:
        """双击重命名."""
        self.start_rename()
        super().mouseDoubleClickEvent(event)


# ===================
# 图层列表组件
# ===================


class LayerListWidget(QListWidget):
    """图层列表组件.

    显示所有图层，支持拖拽排序。
    """

    # 信号
    layer_selected = pyqtSignal(str)  # layer_id
    layer_order_changed = pyqtSignal(list)  # [layer_id, ...]
    layer_visibility_changed = pyqtSignal(str, bool)  # layer_id, visible
    layer_lock_changed = pyqtSignal(str, bool)  # layer_id, locked
    layer_delete_requested = pyqtSignal(str)  # layer_id
    layer_rename_requested = pyqtSignal(str, str)  # layer_id, new_name

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """初始化图层列表."""
        super().__init__(parent)

        self._layer_items: dict[str, LayerItemWidget] = {}

        # 启用拖拽
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)

        # 样式 - 增加列表项之间的间距
        self.setSpacing(6)

        # 信号
        self.itemSelectionChanged.connect(self._on_selection_changed)

    def set_layers(self, layers: List[AnyLayer]) -> None:
        """设置图层列表.

        Args:
            layers: 图层列表（按 z_index 降序排列显示）
        """
        self.clear()
        self._layer_items.clear()

        # 按 z_index 降序排列（最上层在顶部）
        sorted_layers = sorted(layers, key=lambda l: l.z_index, reverse=True)

        for layer in sorted_layers:
            self._add_layer_item(layer)

    def _add_layer_item(self, layer: AnyLayer) -> None:
        """添加图层项."""
        item_widget = LayerItemWidget(layer)
        item_widget.visibility_toggled.connect(
            lambda lid, v: self.layer_visibility_changed.emit(lid, v)
        )
        item_widget.lock_toggled.connect(
            lambda lid, l: self.layer_lock_changed.emit(lid, l)
        )
        item_widget.delete_requested.connect(
            lambda lid: self.layer_delete_requested.emit(lid)
        )
        item_widget.rename_requested.connect(
            lambda lid, n: self.layer_rename_requested.emit(lid, n)
        )

        list_item = QListWidgetItem(self)
        list_item.setData(Qt.ItemDataRole.UserRole, layer.id)
        list_item.setSizeHint(item_widget.sizeHint())
        self.addItem(list_item)
        self.setItemWidget(list_item, item_widget)

        self._layer_items[layer.id] = item_widget

    def add_layer(self, layer: AnyLayer) -> None:
        """添加单个图层."""
        self._add_layer_item(layer)

    def remove_layer(self, layer_id: str) -> None:
        """移除图层."""
        for i in range(self.count()):
            item = self.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == layer_id:
                self.takeItem(i)
                break
        self._layer_items.pop(layer_id, None)

    def update_layer(self, layer_id: str) -> None:
        """更新图层显示."""
        if layer_id in self._layer_items:
            self._layer_items[layer_id].update_from_layer()

    def select_layer(self, layer_id: str) -> None:
        """选中指定图层.
        
        注意: 此方法不会触发 layer_selected 信号，仅更新UI状态。
        """
        # 先检查是否已经选中
        if self.get_selected_layer_id() == layer_id:
            return
            
        # 阻断信号以避免递归
        self.blockSignals(True)
        for i in range(self.count()):
            item = self.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == layer_id:
                self.setCurrentItem(item)
                break
        self.blockSignals(False)
        
        # 仅更新图层项的选中视觉状态，不发射信号
        self._update_selection_visual()

    def get_selected_layer_id(self) -> Optional[str]:
        """获取选中的图层ID."""
        item = self.currentItem()
        if item:
            return item.data(Qt.ItemDataRole.UserRole)
        return None

    def get_layer_order(self) -> List[str]:
        """获取当前图层顺序（从上到下）."""
        return [
            self.item(i).data(Qt.ItemDataRole.UserRole)
            for i in range(self.count())
        ]

    def _update_selection_visual(self) -> None:
        """更新图层项的选中视觉状态."""
        selected_id = self.get_selected_layer_id()
        for layer_id, item_widget in self._layer_items.items():
            item_widget.set_selected(layer_id == selected_id)

    def _on_selection_changed(self) -> None:
        """选择变化处理 - 用户交互触发."""
        # 更新视觉状态
        self._update_selection_visual()
        
        # 发射信号
        selected_id = self.get_selected_layer_id()
        if selected_id:
            self.layer_selected.emit(selected_id)

    def dropEvent(self, event) -> None:
        """拖放事件 - 更新图层顺序."""
        super().dropEvent(event)
        # 发送新顺序
        self.layer_order_changed.emit(self.get_layer_order())


# ===================
# 图层管理面板
# ===================


class LayerPanel(QWidget):
    """图层管理面板.

    包含图层列表和操作按钮。
    """

    # 信号
    layer_selected = pyqtSignal(str)  # layer_id
    layer_visibility_changed = pyqtSignal(str, bool)  # layer_id, visible
    layer_lock_changed = pyqtSignal(str, bool)  # layer_id, locked
    layer_order_changed = pyqtSignal(list)  # [layer_id, ...]
    layer_delete_requested = pyqtSignal(str)  # layer_id
    add_text_requested = pyqtSignal()
    add_rectangle_requested = pyqtSignal()
    add_ellipse_requested = pyqtSignal()
    add_image_requested = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """初始化图层管理面板."""
        super().__init__(parent)
        self.setAutoFillBackground(True)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """设置UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # 标题
        title_label = QLabel("图层")
        title_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(title_label)

        # 图层列表
        self._layer_list = LayerListWidget()
        self._layer_list.layer_selected.connect(self.layer_selected.emit)
        self._layer_list.layer_visibility_changed.connect(self.layer_visibility_changed.emit)
        self._layer_list.layer_lock_changed.connect(self.layer_lock_changed.emit)
        self._layer_list.layer_order_changed.connect(self.layer_order_changed.emit)
        self._layer_list.layer_delete_requested.connect(self._confirm_delete)
        layout.addWidget(self._layer_list, 1)

        # 操作按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(2)
        
        # 获取标准图标
        from PyQt6.QtWidgets import QStyle
        style = self.style()

        # 添加文字按钮
        btn_add_text = QPushButton()
        btn_add_text.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_FileIcon))
        btn_add_text.setFixedSize(36, 32)
        btn_add_text.setToolTip("添加文字图层")
        btn_add_text.clicked.connect(self.add_text_requested.emit)
        btn_layout.addWidget(btn_add_text)

        # 添加矩形按钮
        btn_add_rect = QPushButton()
        btn_add_rect.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_DialogYesButton))
        btn_add_rect.setFixedSize(36, 32)
        btn_add_rect.setToolTip("添加矩形")
        btn_add_rect.clicked.connect(self.add_rectangle_requested.emit)
        btn_layout.addWidget(btn_add_rect)

        # 添加椭圆按钮
        btn_add_ellipse = QPushButton()
        btn_add_ellipse.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_DialogNoButton))
        btn_add_ellipse.setFixedSize(36, 32)
        btn_add_ellipse.setToolTip("添加椭圆")
        btn_add_ellipse.clicked.connect(self.add_ellipse_requested.emit)
        btn_layout.addWidget(btn_add_ellipse)

        # 添加图片按钮
        btn_add_image = QPushButton()
        btn_add_image.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_DirIcon))
        btn_add_image.setFixedSize(36, 32)
        btn_add_image.setToolTip("添加图片")
        btn_add_image.clicked.connect(self.add_image_requested.emit)
        btn_layout.addWidget(btn_add_image)

        btn_layout.addStretch()

        # 删除按钮
        btn_delete = QPushButton()
        btn_delete.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_TrashIcon))
        btn_delete.setFixedSize(36, 32)
        btn_delete.setToolTip("删除选中图层")
        btn_delete.clicked.connect(self._delete_selected)
        btn_layout.addWidget(btn_delete)

        layout.addLayout(btn_layout)

    def set_layers(self, layers: List[AnyLayer]) -> None:
        """设置图层列表."""
        self._layer_list.set_layers(layers)

    def add_layer(self, layer: AnyLayer) -> None:
        """添加图层."""
        self._layer_list.add_layer(layer)

    def remove_layer(self, layer_id: str) -> None:
        """移除图层."""
        self._layer_list.remove_layer(layer_id)

    def update_layer(self, layer_id: str) -> None:
        """更新图层."""
        self._layer_list.update_layer(layer_id)

    def select_layer(self, layer_id: str) -> None:
        """选中图层."""
        self._layer_list.select_layer(layer_id)

    def _delete_selected(self) -> None:
        """删除选中图层."""
        layer_id = self._layer_list.get_selected_layer_id()
        if layer_id:
            self._confirm_delete(layer_id)

    def _confirm_delete(self, layer_id: str) -> None:
        """确认删除图层."""
        reply = QMessageBox.question(
            self,
            "确认删除",
            "确定要删除此图层吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.layer_delete_requested.emit(layer_id)
