"""编辑器工具栏组件.

提供模板编辑器的工具栏，包含添加图层、对齐、分布等常用操作。

Features:
    - 添加图层按钮（文字/矩形/圆形/图片）
    - 对齐工具（左/居中/右/顶部/垂直居中/底部）
    - 分布工具（水平/垂直均匀分布）
    - 复制/粘贴/删除快捷操作
"""

from __future__ import annotations

from typing import Optional, List, TYPE_CHECKING

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction, QIcon, QKeySequence
from PyQt6.QtWidgets import (
    QWidget,
    QToolBar,
    QToolButton,
    QMenu,
    QHBoxLayout,
    QSizePolicy,
    QFileDialog,
)

from src.models.template_config import (
    TextLayer,
    ShapeLayer,
    ImageLayer,
    AnyLayer,
)
from src.utils.logger import setup_logger

if TYPE_CHECKING:
    from src.ui.widgets.template_editor.canvas import TemplateCanvas

logger = setup_logger(__name__)


# ===================
# 对齐类型
# ===================


class AlignmentType:
    """对齐类型常量."""

    LEFT = "left"
    CENTER_H = "center_h"
    RIGHT = "right"
    TOP = "top"
    CENTER_V = "center_v"
    BOTTOM = "bottom"


class DistributeType:
    """分布类型常量."""

    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"


# ===================
# 编辑器工具栏
# ===================


class EditorToolbar(QToolBar):
    """编辑器工具栏.

    提供模板编辑的常用操作工具。

    Signals:
        add_text_requested: 请求添加文字图层
        add_rectangle_requested: 请求添加矩形图层
        add_ellipse_requested: 请求添加圆形图层
        add_image_requested: 请求添加图片图层（带路径）
        align_requested: 请求对齐操作
        distribute_requested: 请求分布操作
        copy_requested: 请求复制
        paste_requested: 请求粘贴
        delete_requested: 请求删除

    Example:
        >>> toolbar = EditorToolbar()
        >>> toolbar.add_text_requested.connect(on_add_text)
        >>> toolbar.align_requested.connect(on_align)
    """

    # 信号定义
    add_text_requested = pyqtSignal()
    add_rectangle_requested = pyqtSignal()
    add_ellipse_requested = pyqtSignal()
    add_image_requested = pyqtSignal(str)  # image_path
    align_requested = pyqtSignal(str)  # alignment_type
    distribute_requested = pyqtSignal(str)  # distribute_type
    copy_requested = pyqtSignal()
    paste_requested = pyqtSignal()
    delete_requested = pyqtSignal()
    undo_requested = pyqtSignal()
    redo_requested = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """初始化工具栏.

        Args:
            parent: 父组件
        """
        super().__init__(parent)

        self.setObjectName("EditorToolbar")
        self.setMovable(False)
        self.setFloatable(False)

        self._setup_ui()

    def _setup_ui(self) -> None:
        """设置UI."""
        # ==================
        # 撤销/重做工具组
        # ==================
        self._add_undo_redo_actions()
        self.addSeparator()

        # ==================
        # 添加图层工具组
        # ==================
        self._add_layer_actions()
        self.addSeparator()

        # ==================
        # 对齐工具组
        # ==================
        self._add_alignment_actions()
        self.addSeparator()

        # ==================
        # 分布工具组
        # ==================
        self._add_distribute_actions()
        self.addSeparator()

        # ==================
        # 编辑操作组
        # ==================
        self._add_edit_actions()

    def _add_undo_redo_actions(self) -> None:
        """添加撤销/重做动作."""
        # 撤销
        self._action_undo = QAction("撤销", self)
        self._action_undo.setToolTip("撤销 (Ctrl+Z)")
        self._action_undo.setShortcut(QKeySequence.StandardKey.Undo)
        self._action_undo.setEnabled(False)
        self._action_undo.triggered.connect(self.undo_requested.emit)
        self.addAction(self._action_undo)

        # 重做
        self._action_redo = QAction("重做", self)
        self._action_redo.setToolTip("重做 (Ctrl+Y / Ctrl+Shift+Z)")
        self._action_redo.setShortcut(QKeySequence.StandardKey.Redo)
        self._action_redo.setEnabled(False)
        self._action_redo.triggered.connect(self.redo_requested.emit)
        self.addAction(self._action_redo)

    def set_undo_enabled(self, enabled: bool) -> None:
        """设置撤销按钮启用状态.

        Args:
            enabled: 是否启用
        """
        self._action_undo.setEnabled(enabled)

    def set_redo_enabled(self, enabled: bool) -> None:
        """设置重做按钮启用状态.

        Args:
            enabled: 是否启用
        """
        self._action_redo.setEnabled(enabled)

    def set_undo_tooltip(self, description: str) -> None:
        """设置撤销按钮提示.

        Args:
            description: 操作描述
        """
        if description:
            self._action_undo.setToolTip(f"撤销: {description} (Ctrl+Z)")
        else:
            self._action_undo.setToolTip("撤销 (Ctrl+Z)")

    def set_redo_tooltip(self, description: str) -> None:
        """设置重做按钮提示.

        Args:
            description: 操作描述
        """
        if description:
            self._action_redo.setToolTip(f"重做: {description} (Ctrl+Y)")
        else:
            self._action_redo.setToolTip("重做 (Ctrl+Y / Ctrl+Shift+Z)")

    def _add_layer_actions(self) -> None:
        """添加图层相关的动作."""
        # 添加文字
        self._action_add_text = QAction("文字", self)
        self._action_add_text.setToolTip("添加文字图层 (T)")
        self._action_add_text.setShortcut(QKeySequence("T"))
        self._action_add_text.triggered.connect(self.add_text_requested.emit)
        self.addAction(self._action_add_text)

        # 添加矩形
        self._action_add_rect = QAction("矩形", self)
        self._action_add_rect.setToolTip("添加矩形图层 (R)")
        self._action_add_rect.setShortcut(QKeySequence("R"))
        self._action_add_rect.triggered.connect(self.add_rectangle_requested.emit)
        self.addAction(self._action_add_rect)

        # 添加圆形
        self._action_add_ellipse = QAction("圆形", self)
        self._action_add_ellipse.setToolTip("添加圆形图层 (O)")
        self._action_add_ellipse.setShortcut(QKeySequence("O"))
        self._action_add_ellipse.triggered.connect(self.add_ellipse_requested.emit)
        self.addAction(self._action_add_ellipse)

        # 添加图片
        self._action_add_image = QAction("图片", self)
        self._action_add_image.setToolTip("添加图片图层 (I)")
        self._action_add_image.setShortcut(QKeySequence("I"))
        self._action_add_image.triggered.connect(self._on_add_image)
        self.addAction(self._action_add_image)

    def _add_alignment_actions(self) -> None:
        """添加对齐相关的动作."""
        # 对齐按钮（带下拉菜单）
        align_button = QToolButton(self)
        align_button.setText("对齐")
        align_button.setToolTip("对齐选中的图层")
        align_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)

        align_menu = QMenu(align_button)

        # 水平对齐
        action_left = align_menu.addAction("左对齐")
        action_left.setShortcut(QKeySequence("Ctrl+Shift+L"))
        action_left.triggered.connect(lambda: self.align_requested.emit(AlignmentType.LEFT))

        action_center_h = align_menu.addAction("水平居中")
        action_center_h.setShortcut(QKeySequence("Ctrl+Shift+C"))
        action_center_h.triggered.connect(lambda: self.align_requested.emit(AlignmentType.CENTER_H))

        action_right = align_menu.addAction("右对齐")
        action_right.setShortcut(QKeySequence("Ctrl+Shift+R"))
        action_right.triggered.connect(lambda: self.align_requested.emit(AlignmentType.RIGHT))

        align_menu.addSeparator()

        # 垂直对齐
        action_top = align_menu.addAction("顶部对齐")
        action_top.setShortcut(QKeySequence("Ctrl+Shift+T"))
        action_top.triggered.connect(lambda: self.align_requested.emit(AlignmentType.TOP))

        action_center_v = align_menu.addAction("垂直居中")
        action_center_v.setShortcut(QKeySequence("Ctrl+Shift+M"))
        action_center_v.triggered.connect(lambda: self.align_requested.emit(AlignmentType.CENTER_V))

        action_bottom = align_menu.addAction("底部对齐")
        action_bottom.setShortcut(QKeySequence("Ctrl+Shift+B"))
        action_bottom.triggered.connect(lambda: self.align_requested.emit(AlignmentType.BOTTOM))

        align_button.setMenu(align_menu)
        self.addWidget(align_button)

        # 保存对齐动作引用
        self._align_actions = {
            AlignmentType.LEFT: action_left,
            AlignmentType.CENTER_H: action_center_h,
            AlignmentType.RIGHT: action_right,
            AlignmentType.TOP: action_top,
            AlignmentType.CENTER_V: action_center_v,
            AlignmentType.BOTTOM: action_bottom,
        }

    def _add_distribute_actions(self) -> None:
        """添加分布相关的动作."""
        # 分布按钮（带下拉菜单）
        distribute_button = QToolButton(self)
        distribute_button.setText("分布")
        distribute_button.setToolTip("均匀分布选中的图层")
        distribute_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)

        distribute_menu = QMenu(distribute_button)

        action_h = distribute_menu.addAction("水平均匀分布")
        action_h.setShortcut(QKeySequence("Ctrl+Shift+H"))
        action_h.triggered.connect(lambda: self.distribute_requested.emit(DistributeType.HORIZONTAL))

        action_v = distribute_menu.addAction("垂直均匀分布")
        action_v.setShortcut(QKeySequence("Ctrl+Shift+V"))
        action_v.triggered.connect(lambda: self.distribute_requested.emit(DistributeType.VERTICAL))

        distribute_button.setMenu(distribute_menu)
        self.addWidget(distribute_button)

        # 保存分布动作引用
        self._distribute_actions = {
            DistributeType.HORIZONTAL: action_h,
            DistributeType.VERTICAL: action_v,
        }

    def _add_edit_actions(self) -> None:
        """添加编辑相关的动作."""
        # 复制
        self._action_copy = QAction("复制", self)
        self._action_copy.setToolTip("复制选中的图层 (Ctrl+C)")
        self._action_copy.setShortcut(QKeySequence.StandardKey.Copy)
        self._action_copy.triggered.connect(self.copy_requested.emit)
        self.addAction(self._action_copy)

        # 粘贴
        self._action_paste = QAction("粘贴", self)
        self._action_paste.setToolTip("粘贴图层 (Ctrl+V)")
        self._action_paste.setShortcut(QKeySequence.StandardKey.Paste)
        self._action_paste.triggered.connect(self.paste_requested.emit)
        self.addAction(self._action_paste)

        # 删除
        self._action_delete = QAction("删除", self)
        self._action_delete.setToolTip("删除选中的图层 (Delete)")
        self._action_delete.setShortcut(QKeySequence.StandardKey.Delete)
        self._action_delete.triggered.connect(self.delete_requested.emit)
        self.addAction(self._action_delete)

    def _on_add_image(self) -> None:
        """添加图片时打开文件选择对话框."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择图片",
            "",
            "图片文件 (*.png *.jpg *.jpeg *.gif *.bmp *.webp);;所有文件 (*)",
        )
        if file_path:
            self.add_image_requested.emit(file_path)


# ===================
# 对齐/分布管理器
# ===================


class AlignmentManager:
    """对齐管理器.

    提供图层对齐和分布的计算逻辑。

    Example:
        >>> manager = AlignmentManager(canvas)
        >>> manager.align_left(["layer1", "layer2"])
        >>> manager.distribute_horizontal(["layer1", "layer2", "layer3"])
    """

    def __init__(self, canvas: "TemplateCanvas") -> None:
        """初始化对齐管理器.

        Args:
            canvas: 画布组件
        """
        self._canvas = canvas

    def align(self, layer_ids: List[str], alignment_type: str) -> None:
        """对齐图层.

        Args:
            layer_ids: 图层ID列表
            alignment_type: 对齐类型
        """
        if len(layer_ids) < 2:
            return

        if alignment_type == AlignmentType.LEFT:
            self._align_left(layer_ids)
        elif alignment_type == AlignmentType.CENTER_H:
            self._align_center_horizontal(layer_ids)
        elif alignment_type == AlignmentType.RIGHT:
            self._align_right(layer_ids)
        elif alignment_type == AlignmentType.TOP:
            self._align_top(layer_ids)
        elif alignment_type == AlignmentType.CENTER_V:
            self._align_center_vertical(layer_ids)
        elif alignment_type == AlignmentType.BOTTOM:
            self._align_bottom(layer_ids)

    def distribute(self, layer_ids: List[str], distribute_type: str) -> None:
        """分布图层.

        Args:
            layer_ids: 图层ID列表
            distribute_type: 分布类型
        """
        if len(layer_ids) < 3:
            return

        if distribute_type == DistributeType.HORIZONTAL:
            self._distribute_horizontal(layer_ids)
        elif distribute_type == DistributeType.VERTICAL:
            self._distribute_vertical(layer_ids)

    def _get_layer_bounds(self, layer_id: str) -> Optional[tuple]:
        """获取图层边界.

        Returns:
            (x, y, width, height) 或 None
        """
        template = self._canvas.template
        if not template:
            return None

        layer = template.get_layer_by_id(layer_id)
        if not layer:
            return None

        return (layer.x, layer.y, layer.width, layer.height)

    def _set_layer_position(self, layer_id: str, x: int, y: int) -> None:
        """设置图层位置."""
        template = self._canvas.template
        if not template:
            return

        layer = template.get_layer_by_id(layer_id)
        if layer:
            layer.x = x
            layer.y = y
            template.update_layer(layer)
            self._canvas.update_layer(layer_id)

    def _align_left(self, layer_ids: List[str]) -> None:
        """左对齐."""
        bounds_list = [self._get_layer_bounds(lid) for lid in layer_ids]
        bounds_list = [b for b in bounds_list if b]

        if not bounds_list:
            return

        # 找到最左边的位置
        min_x = min(b[0] for b in bounds_list)

        # 移动所有图层到最左边
        for layer_id in layer_ids:
            bounds = self._get_layer_bounds(layer_id)
            if bounds:
                self._set_layer_position(layer_id, min_x, bounds[1])

    def _align_center_horizontal(self, layer_ids: List[str]) -> None:
        """水平居中对齐."""
        bounds_list = [self._get_layer_bounds(lid) for lid in layer_ids]
        bounds_list = [b for b in bounds_list if b]

        if not bounds_list:
            return

        # 找到水平中心位置（基于选区的中心）
        min_x = min(b[0] for b in bounds_list)
        max_x = max(b[0] + b[2] for b in bounds_list)
        center_x = (min_x + max_x) / 2

        # 移动所有图层使其水平居中
        for layer_id in layer_ids:
            bounds = self._get_layer_bounds(layer_id)
            if bounds:
                new_x = int(center_x - bounds[2] / 2)
                self._set_layer_position(layer_id, new_x, bounds[1])

    def _align_right(self, layer_ids: List[str]) -> None:
        """右对齐."""
        bounds_list = [self._get_layer_bounds(lid) for lid in layer_ids]
        bounds_list = [b for b in bounds_list if b]

        if not bounds_list:
            return

        # 找到最右边的位置
        max_right = max(b[0] + b[2] for b in bounds_list)

        # 移动所有图层到最右边
        for layer_id in layer_ids:
            bounds = self._get_layer_bounds(layer_id)
            if bounds:
                new_x = max_right - bounds[2]
                self._set_layer_position(layer_id, int(new_x), bounds[1])

    def _align_top(self, layer_ids: List[str]) -> None:
        """顶部对齐."""
        bounds_list = [self._get_layer_bounds(lid) for lid in layer_ids]
        bounds_list = [b for b in bounds_list if b]

        if not bounds_list:
            return

        # 找到最顶部的位置
        min_y = min(b[1] for b in bounds_list)

        # 移动所有图层到最顶部
        for layer_id in layer_ids:
            bounds = self._get_layer_bounds(layer_id)
            if bounds:
                self._set_layer_position(layer_id, bounds[0], min_y)

    def _align_center_vertical(self, layer_ids: List[str]) -> None:
        """垂直居中对齐."""
        bounds_list = [self._get_layer_bounds(lid) for lid in layer_ids]
        bounds_list = [b for b in bounds_list if b]

        if not bounds_list:
            return

        # 找到垂直中心位置（基于选区的中心）
        min_y = min(b[1] for b in bounds_list)
        max_y = max(b[1] + b[3] for b in bounds_list)
        center_y = (min_y + max_y) / 2

        # 移动所有图层使其垂直居中
        for layer_id in layer_ids:
            bounds = self._get_layer_bounds(layer_id)
            if bounds:
                new_y = int(center_y - bounds[3] / 2)
                self._set_layer_position(layer_id, bounds[0], new_y)

    def _align_bottom(self, layer_ids: List[str]) -> None:
        """底部对齐."""
        bounds_list = [self._get_layer_bounds(lid) for lid in layer_ids]
        bounds_list = [b for b in bounds_list if b]

        if not bounds_list:
            return

        # 找到最底部的位置
        max_bottom = max(b[1] + b[3] for b in bounds_list)

        # 移动所有图层到最底部
        for layer_id in layer_ids:
            bounds = self._get_layer_bounds(layer_id)
            if bounds:
                new_y = max_bottom - bounds[3]
                self._set_layer_position(layer_id, bounds[0], int(new_y))

    def _distribute_horizontal(self, layer_ids: List[str]) -> None:
        """水平均匀分布."""
        bounds_list = [(lid, self._get_layer_bounds(lid)) for lid in layer_ids]
        bounds_list = [(lid, b) for lid, b in bounds_list if b]

        if len(bounds_list) < 3:
            return

        # 按 X 坐标排序
        bounds_list.sort(key=lambda x: x[1][0])

        # 计算总宽度和间距
        first_x = bounds_list[0][1][0]
        last_x = bounds_list[-1][1][0] + bounds_list[-1][1][2]
        total_width = sum(b[1][2] for b in bounds_list)
        available_space = (last_x - first_x) - total_width
        gap = available_space / (len(bounds_list) - 1)

        # 分布图层
        current_x = first_x
        for layer_id, bounds in bounds_list:
            self._set_layer_position(layer_id, int(current_x), bounds[1])
            current_x += bounds[2] + gap

    def _distribute_vertical(self, layer_ids: List[str]) -> None:
        """垂直均匀分布."""
        bounds_list = [(lid, self._get_layer_bounds(lid)) for lid in layer_ids]
        bounds_list = [(lid, b) for lid, b in bounds_list if b]

        if len(bounds_list) < 3:
            return

        # 按 Y 坐标排序
        bounds_list.sort(key=lambda x: x[1][1])

        # 计算总高度和间距
        first_y = bounds_list[0][1][1]
        last_y = bounds_list[-1][1][1] + bounds_list[-1][1][3]
        total_height = sum(b[1][3] for b in bounds_list)
        available_space = (last_y - first_y) - total_height
        gap = available_space / (len(bounds_list) - 1)

        # 分布图层
        current_y = first_y
        for layer_id, bounds in bounds_list:
            self._set_layer_position(layer_id, bounds[0], int(current_y))
            current_y += bounds[3] + gap


# ===================
# 剪贴板管理器
# ===================


class ClipboardManager:
    """剪贴板管理器.

    管理图层的复制粘贴操作。

    Example:
        >>> clipboard = ClipboardManager(canvas)
        >>> clipboard.copy(["layer1", "layer2"])
        >>> clipboard.paste()
    """

    def __init__(self, canvas: "TemplateCanvas") -> None:
        """初始化剪贴板管理器.

        Args:
            canvas: 画布组件
        """
        self._canvas = canvas
        self._clipboard: List[AnyLayer] = []
        self._paste_offset = 20  # 粘贴时的偏移量

    @property
    def has_content(self) -> bool:
        """剪贴板是否有内容."""
        return len(self._clipboard) > 0

    def copy(self, layer_ids: List[str]) -> None:
        """复制图层.

        Args:
            layer_ids: 图层ID列表
        """
        template = self._canvas.template
        if not template:
            return

        self._clipboard.clear()

        for layer_id in layer_ids:
            layer = template.get_layer_by_id(layer_id)
            if layer:
                # 深拷贝图层
                layer_copy = layer.model_copy(deep=True)
                self._clipboard.append(layer_copy)

        logger.debug(f"复制了 {len(self._clipboard)} 个图层")

    def paste(self) -> List[str]:
        """粘贴图层.

        Returns:
            新创建的图层ID列表
        """
        if not self._clipboard or not self._canvas.template:
            return []

        new_layer_ids = []

        for layer in self._clipboard:
            # 创建新的图层副本
            import uuid
            new_layer = layer.model_copy(deep=True)
            new_layer.id = str(uuid.uuid4())
            new_layer.name = f"{layer.name} 副本"

            # 偏移位置
            new_layer.x += self._paste_offset
            new_layer.y += self._paste_offset

            # 添加到画布
            self._canvas.add_layer(new_layer)
            new_layer_ids.append(new_layer.id)

        # 增加偏移量，避免多次粘贴重叠
        self._paste_offset += 20
        if self._paste_offset > 100:
            self._paste_offset = 20

        logger.debug(f"粘贴了 {len(new_layer_ids)} 个图层")
        return new_layer_ids

    def clear(self) -> None:
        """清空剪贴板."""
        self._clipboard.clear()
        self._paste_offset = 20


# ===================
# 右键菜单
# ===================


class ContextMenuManager:
    """右键上下文菜单管理器.

    管理画布的右键菜单。

    Example:
        >>> menu_manager = ContextMenuManager(canvas, clipboard, alignment)
        >>> menu_manager.show_menu(position, layer_ids)
    """

    def __init__(
        self,
        canvas: "TemplateCanvas",
        clipboard: ClipboardManager,
        alignment: AlignmentManager,
    ) -> None:
        """初始化菜单管理器.

        Args:
            canvas: 画布组件
            clipboard: 剪贴板管理器
            alignment: 对齐管理器
        """
        self._canvas = canvas
        self._clipboard = clipboard
        self._alignment = alignment

    def show_menu(self, global_pos, layer_ids: List[str]) -> None:
        """显示右键菜单.

        Args:
            global_pos: 全局位置
            layer_ids: 选中的图层ID列表
        """
        menu = QMenu()

        # 复制/粘贴/删除
        if layer_ids:
            action_copy = menu.addAction("复制")
            action_copy.setShortcut(QKeySequence.StandardKey.Copy)
            action_copy.triggered.connect(lambda: self._clipboard.copy(layer_ids))

        action_paste = menu.addAction("粘贴")
        action_paste.setShortcut(QKeySequence.StandardKey.Paste)
        action_paste.setEnabled(self._clipboard.has_content)
        action_paste.triggered.connect(self._clipboard.paste)

        if layer_ids:
            action_delete = menu.addAction("删除")
            action_delete.setShortcut(QKeySequence.StandardKey.Delete)
            action_delete.triggered.connect(lambda: self._delete_layers(layer_ids))

        menu.addSeparator()

        # 对齐菜单（需要选中多个图层）
        if len(layer_ids) >= 2:
            align_menu = menu.addMenu("对齐")

            action_left = align_menu.addAction("左对齐")
            action_left.triggered.connect(
                lambda: self._alignment.align(layer_ids, AlignmentType.LEFT)
            )

            action_center_h = align_menu.addAction("水平居中")
            action_center_h.triggered.connect(
                lambda: self._alignment.align(layer_ids, AlignmentType.CENTER_H)
            )

            action_right = align_menu.addAction("右对齐")
            action_right.triggered.connect(
                lambda: self._alignment.align(layer_ids, AlignmentType.RIGHT)
            )

            align_menu.addSeparator()

            action_top = align_menu.addAction("顶部对齐")
            action_top.triggered.connect(
                lambda: self._alignment.align(layer_ids, AlignmentType.TOP)
            )

            action_center_v = align_menu.addAction("垂直居中")
            action_center_v.triggered.connect(
                lambda: self._alignment.align(layer_ids, AlignmentType.CENTER_V)
            )

            action_bottom = align_menu.addAction("底部对齐")
            action_bottom.triggered.connect(
                lambda: self._alignment.align(layer_ids, AlignmentType.BOTTOM)
            )

        # 分布菜单（需要选中3个以上图层）
        if len(layer_ids) >= 3:
            distribute_menu = menu.addMenu("分布")

            action_h = distribute_menu.addAction("水平均匀分布")
            action_h.triggered.connect(
                lambda: self._alignment.distribute(layer_ids, DistributeType.HORIZONTAL)
            )

            action_v = distribute_menu.addAction("垂直均匀分布")
            action_v.triggered.connect(
                lambda: self._alignment.distribute(layer_ids, DistributeType.VERTICAL)
            )

        menu.exec(global_pos)

    def _delete_layers(self, layer_ids: List[str]) -> None:
        """删除图层."""
        for layer_id in layer_ids:
            self._canvas.remove_layer(layer_id)
