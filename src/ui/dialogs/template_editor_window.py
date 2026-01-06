"""模板编辑器窗口.

提供独立的模板编辑器窗口，支持创建、编辑和管理模板。

布局结构:
    ┌─────────────────────────────────────────────────────────────┐
    │                         工具栏                               │
    ├────────────────┬────────────────────┬───────────────────────┤
    │                │                    │                       │
    │   模板列表      │     画布编辑器     │     属性面板          │
    │   (左侧面板)    │     (中间区域)     │     (右侧面板)        │
    │                │                    │                       │
    ├────────────────┴────────────────────┴───────────────────────┤
    │   图层列表面板                                               │
    └─────────────────────────────────────────────────────────────┘
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional
import json

from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QAction, QKeySequence, QCloseEvent
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QMainWindow,
    QMenu,
    QMenuBar,
    QMessageBox,
    QSplitter,
    QStatusBar,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from src.models.template_config import (
    TemplateConfig,
    TextLayer,
    ShapeLayer,
    ImageLayer,
    LayerType,
)
from src.ui.widgets.template_editor import (
    TemplateCanvas,
    LayerPanel,
    PropertyPanel,
    TemplateListWidget,
    EditorToolbar,
    UndoRedoManager,
)
from src.services.template_manager import TemplateManager
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


# 窗口常量
WINDOW_MIN_WIDTH = 1200
WINDOW_MIN_HEIGHT = 800
WINDOW_TITLE = "模板编辑器"


class TemplateEditorWindow(QMainWindow):
    """模板编辑器窗口.

    提供完整的模板编辑功能，包括:
    - 模板列表管理
    - 画布编辑器
    - 图层管理
    - 属性编辑
    - 撤销/重做

    Signals:
        template_saved: 模板保存信号，参数为模板配置
        template_selected: 模板选中信号，参数为模板配置
    """

    template_saved = pyqtSignal(object)  # TemplateConfig
    template_selected = pyqtSignal(object)  # TemplateConfig

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """初始化模板编辑器窗口.

        Args:
            parent: 父组件
        """
        super().__init__(parent)

        # 模板管理器
        self._template_manager = TemplateManager()

        # 当前模板
        self._current_template: Optional[TemplateConfig] = None
        
        # 未保存状态标记
        self._is_modified = False

        # UI组件引用
        self._toolbar: Optional[EditorToolbar] = None
        self._statusbar: Optional[QStatusBar] = None
        self._canvas: Optional[TemplateCanvas] = None
        self._layer_panel: Optional[LayerPanel] = None
        self._property_panel: Optional[PropertyPanel] = None
        self._template_list: Optional[TemplateListWidget] = None

        # 撤销/重做管理器
        self._undo_manager: Optional[UndoRedoManager] = None

        # Action 引用
        self._action_new: Optional[QAction] = None
        self._action_open: Optional[QAction] = None
        self._action_save: Optional[QAction] = None
        self._action_save_as: Optional[QAction] = None
        self._action_undo: Optional[QAction] = None
        self._action_redo: Optional[QAction] = None

        # 初始化UI
        self._setup_window()
        self._setup_menubar()
        self._setup_toolbar()
        self._setup_central_widget()
        self._setup_statusbar()
        self._connect_signals()

        # 创建默认新模板
        self._create_new_template()
        
        logger.debug("模板编辑器窗口初始化完成")

    # ========================
    # 工具方法
    # ========================
    
    def _set_modified(self, modified: bool) -> None:
        """设置未保存状态.
        
        Args:
            modified: 是否已修改
        """
        if self._is_modified == modified:
            return
        
        self._is_modified = modified
        self._update_window_title()
    
    def _update_window_title(self) -> None:
        """更新窗口标题."""
        title = WINDOW_TITLE
        if self._current_template:
            title = f"{WINDOW_TITLE} - {self._current_template.name}"
        if self._is_modified:
            title += " *（未保存）"
        self.setWindowTitle(title)
    
    def keyPressEvent(self, event) -> None:
        """键盘事件处理."""
        # 方向键微调图层位置
        if self._canvas and self._canvas.selected_layers:
            from PyQt6.QtCore import Qt
            key = event.key()
            
            # 检查是否按下了方向键
            if key in (Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Up, Qt.Key.Key_Down):
                # 计算偏移量（Shift键加速）
                step = 10 if event.modifiers() & Qt.KeyboardModifier.ShiftModifier else 1
                
                dx = dy = 0
                if key == Qt.Key.Key_Left:
                    dx = -step
                elif key == Qt.Key.Key_Right:
                    dx = step
                elif key == Qt.Key.Key_Up:
                    dy = -step
                elif key == Qt.Key.Key_Down:
                    dy = step
                
                # 移动选中的图层
                for layer_id in self._canvas.selected_layers:
                    layer = self._current_template.get_layer_by_id(layer_id) if self._current_template else None
                    if layer:
                        layer.move_by(dx, dy)
                        self._current_template.update_layer(layer)
                        # 更新画布显示
                        self._canvas.update_layer(layer)
                        # 更新属性面板
                        if self._property_panel:
                            self._property_panel.set_layer(layer)
                
                # 标记为已修改
                self._set_modified(True)
                event.accept()
                return
        
        super().keyPressEvent(event)

    # ========================
    # 初始化方法
    # ========================

    def _setup_window(self) -> None:
        """设置窗口属性."""
        self.setWindowTitle(WINDOW_TITLE)
        self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self.resize(1400, 900)
        
        # 设置焦点策略以接收键盘事件
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        # 居中显示
        self._center_window()

    def _center_window(self) -> None:
        """将窗口居中显示."""
        screen = QApplication.primaryScreen()
        if screen:
            screen_geometry = screen.availableGeometry()
            window_geometry = self.frameGeometry()
            center_point = screen_geometry.center()
            window_geometry.moveCenter(center_point)
            self.move(window_geometry.topLeft())

    def _setup_menubar(self) -> None:
        """设置菜单栏."""
        menubar = self.menuBar()
        if not menubar:
            return

        # 文件菜单
        file_menu = menubar.addMenu("文件(&F)")
        if file_menu:
            self._setup_file_menu(file_menu)

        # 编辑菜单
        edit_menu = menubar.addMenu("编辑(&E)")
        if edit_menu:
            self._setup_edit_menu(edit_menu)

        # 图层菜单
        layer_menu = menubar.addMenu("图层(&L)")
        if layer_menu:
            self._setup_layer_menu(layer_menu)

    def _setup_file_menu(self, menu: QMenu) -> None:
        """设置文件菜单."""
        # 新建模板
        self._action_new = QAction("新建模板(&N)", self)
        self._action_new.setShortcut(QKeySequence.StandardKey.New)
        self._action_new.triggered.connect(self._on_new_template)
        menu.addAction(self._action_new)

        # 打开模板
        self._action_open = QAction("打开模板(&O)...", self)
        self._action_open.setShortcut(QKeySequence.StandardKey.Open)
        self._action_open.triggered.connect(self._on_open_template)
        menu.addAction(self._action_open)

        menu.addSeparator()

        # 保存模板
        self._action_save = QAction("保存模板(&S)", self)
        self._action_save.setShortcut(QKeySequence.StandardKey.Save)
        self._action_save.triggered.connect(self._on_save_template)
        menu.addAction(self._action_save)

        # 另存为
        self._action_save_as = QAction("另存为(&A)...", self)
        self._action_save_as.setShortcut(QKeySequence("Ctrl+Shift+S"))
        self._action_save_as.triggered.connect(self._on_save_template_as)
        menu.addAction(self._action_save_as)

        menu.addSeparator()

        # 关闭
        action_close = QAction("关闭(&C)", self)
        action_close.setShortcut(QKeySequence.StandardKey.Close)
        action_close.triggered.connect(self.close)
        menu.addAction(action_close)

    def _setup_edit_menu(self, menu: QMenu) -> None:
        """设置编辑菜单."""
        # 撤销
        self._action_undo = QAction("撤销(&U)", self)
        self._action_undo.setShortcut(QKeySequence.StandardKey.Undo)
        self._action_undo.setEnabled(False)
        self._action_undo.triggered.connect(self._on_undo)
        menu.addAction(self._action_undo)

        # 重做
        self._action_redo = QAction("重做(&R)", self)
        self._action_redo.setShortcut(QKeySequence.StandardKey.Redo)
        self._action_redo.setEnabled(False)
        self._action_redo.triggered.connect(self._on_redo)
        menu.addAction(self._action_redo)

    def _setup_layer_menu(self, menu: QMenu) -> None:
        """设置图层菜单."""
        # 添加文字图层
        action_add_text = QAction("添加文字图层(&T)", self)
        action_add_text.setShortcut(QKeySequence("Ctrl+T"))
        action_add_text.triggered.connect(self._on_add_text_layer)
        menu.addAction(action_add_text)

        # 添加矩形
        action_add_rect = QAction("添加矩形(&R)", self)
        action_add_rect.triggered.connect(self._on_add_rectangle)
        menu.addAction(action_add_rect)

        # 添加椭圆
        action_add_ellipse = QAction("添加椭圆(&E)", self)
        action_add_ellipse.triggered.connect(self._on_add_ellipse)
        menu.addAction(action_add_ellipse)

        # 添加图片
        action_add_image = QAction("添加图片(&I)...", self)
        action_add_image.triggered.connect(self._on_add_image)
        menu.addAction(action_add_image)

    def _setup_toolbar(self) -> None:
        """设置工具栏."""
        self._toolbar = EditorToolbar(self)
        self._toolbar.setMovable(False)
        self.addToolBar(self._toolbar)

    def _setup_central_widget(self) -> None:
        """设置中央区域."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 主分割器（水平分割：列表 | 画布 | 右侧面板）
        self._main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self._main_splitter.setHandleWidth(1)  # 细分割线
        main_layout.addWidget(self._main_splitter)

        # 1. 左侧：模板列表
        self._template_list = TemplateListWidget(manager=self._template_manager)
        self._template_list.setObjectName("templateListContainer")
        self._template_list.setMinimumWidth(200)
        self._template_list.setMaximumWidth(300)
        self._main_splitter.addWidget(self._template_list)

        # 2. 中间：画布区域
        # 使用容器包裹画布，以便后续添加标尺或滚动条控制
        canvas_container = QWidget()
        canvas_layout = QVBoxLayout(canvas_container)
        canvas_layout.setContentsMargins(0, 0, 0, 0)
        canvas_layout.setSpacing(0)
        
        self._canvas = TemplateCanvas()
        canvas_layout.addWidget(self._canvas)
        
        self._main_splitter.addWidget(canvas_container)

        # 3. 右侧：属性面板 + 图层面板
        right_panel_container = QWidget()
        right_panel_container.setObjectName("rightPanelContainer")
        right_layout = QVBoxLayout(right_panel_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        
        # 右侧分割器（垂直分割：属性 | 图层）
        self._right_splitter = QSplitter(Qt.Orientation.Vertical)
        self._right_splitter.setHandleWidth(1)
        right_layout.addWidget(self._right_splitter)

        # 3.1 属性面板 (Top)
        self._property_panel = PropertyPanel()
        self._property_panel.setMinimumHeight(200)
        self._right_splitter.addWidget(self._property_panel)

        # 3.2 图层面板 (Bottom)
        self._layer_panel = LayerPanel()
        self._layer_panel.setMinimumHeight(200)
        self._right_splitter.addWidget(self._layer_panel)

        # 添加到主分割器
        self._main_splitter.addWidget(right_panel_container)

        # 设置右侧面板宽度限制
        right_panel_container.setMinimumWidth(280)
        right_panel_container.setMaximumWidth(400)

        # 设置初始分割比例
        self._main_splitter.setStretchFactor(0, 0)  # 列表
        self._main_splitter.setStretchFactor(1, 1)  # 画布 (拉伸)
        self._main_splitter.setStretchFactor(2, 0)  # 右侧面板
        
        # 设置右侧垂直分割比例 (属性 4 : 图层 6)
        self._right_splitter.setStretchFactor(0, 4)
        self._right_splitter.setStretchFactor(1, 6)

        # 设置初始大小
        self._main_splitter.setSizes([250, 800, 320])

    def _setup_statusbar(self) -> None:
        """设置状态栏."""
        self._statusbar = QStatusBar()
        self.setStatusBar(self._statusbar)
        self._statusbar.showMessage("就绪")

    def _connect_signals(self) -> None:
        """连接信号槽."""
        # 工具栏信号
        if self._toolbar:
            self._toolbar.add_text_requested.connect(self._on_add_text_layer)
            self._toolbar.add_rectangle_requested.connect(self._on_add_rectangle)
            self._toolbar.add_ellipse_requested.connect(self._on_add_ellipse)
            self._toolbar.add_image_requested.connect(self._on_add_image_from_path)
            self._toolbar.undo_requested.connect(self._on_undo)
            self._toolbar.redo_requested.connect(self._on_redo)
            self._toolbar.delete_requested.connect(self._on_delete_selected)
            self._toolbar.copy_requested.connect(self._on_copy)
            self._toolbar.paste_requested.connect(self._on_paste)

        # 画布信号
        if self._canvas:
            self._canvas.layer_selected.connect(self._on_layer_selected)
            self._canvas.layer_deselected.connect(self._on_layer_deselected)
            self._canvas.selection_changed.connect(self._on_selection_changed)
            self._canvas.layer_moved.connect(self._on_layer_moved)
            self._canvas.layer_resized.connect(self._on_layer_resized)
            self._canvas.layer_content_changed.connect(self._on_layer_content_changed)

        # 图层面板信号
        if self._layer_panel:
            self._layer_panel.layer_selected.connect(self._on_panel_layer_selected)
            self._layer_panel.layer_visibility_changed.connect(
                self._on_layer_visibility_changed
            )
            self._layer_panel.layer_lock_changed.connect(self._on_layer_locked_changed)
            self._layer_panel.layer_order_changed.connect(self._on_layers_reordered)
            self._layer_panel.layer_delete_requested.connect(self._on_layer_deleted)
            # 连接添加图层按钮信号
            self._layer_panel.add_text_requested.connect(self._on_add_text_layer)
            self._layer_panel.add_rectangle_requested.connect(self._on_add_rectangle)
            self._layer_panel.add_ellipse_requested.connect(self._on_add_ellipse)
            self._layer_panel.add_image_requested.connect(self._on_add_image)
            self._layer_panel.layer_order_changed.connect(self._on_layers_reordered)
            self._layer_panel.layer_delete_requested.connect(self._on_layer_deleted)

        # 属性面板信号
        if self._property_panel:
            self._property_panel.layer_property_changed.connect(self._on_property_changed)
            self._property_panel.canvas_property_changed.connect(
                self._on_canvas_property_changed
            )

        # 模板列表信号
        if self._template_list:
            self._template_list.template_selected.connect(self._on_template_selected_by_id)
            self._template_list.template_deleted.connect(self._on_template_deleted)

    def _setup_undo_manager(self) -> None:
        """设置撤销管理器."""
        if self._canvas:
            self._undo_manager = UndoRedoManager(self._canvas, self)

            # 连接信号更新UI
            self._undo_manager._stack.can_undo_changed.connect(
                self._update_undo_actions
            )
            self._undo_manager._stack.can_redo_changed.connect(
                self._update_undo_actions
            )

    def _update_undo_actions(self) -> None:
        """更新撤销/重做按钮状态."""
        if self._undo_manager:
            can_undo = self._undo_manager.can_undo
            can_redo = self._undo_manager.can_redo

            if self._action_undo:
                self._action_undo.setEnabled(can_undo)

            if self._action_redo:
                self._action_redo.setEnabled(can_redo)

            if self._toolbar:
                self._toolbar.set_undo_enabled(can_undo)
                self._toolbar.set_redo_enabled(can_redo)

                if can_undo:
                    self._toolbar.set_undo_tooltip(self._undo_manager.undo_description)
                else:
                    self._toolbar.set_undo_tooltip("")

                if can_redo:
                    self._toolbar.set_redo_tooltip(self._undo_manager.redo_description)
                else:
                    self._toolbar.set_redo_tooltip("")

    # ========================
    # 模板管理
    # ========================

    def _create_new_template(self, name: str = "未命名模板") -> TemplateConfig:
        """创建新模板.

        Args:
            name: 模板名称

        Returns:
            新创建的模板
        """
        template = TemplateConfig(name=name)
        self._set_current_template(template)
        return template

    def _set_current_template(self, template: Optional[TemplateConfig]) -> None:
        """设置当前模板.

        Args:
            template: 模板配置
        """
        self._current_template = template

        # 更新画布
        if self._canvas:
            self._canvas.set_template(template)

        # 更新图层面板
        if self._layer_panel and template:
            self._layer_panel.set_layers(template.get_layers())

        # 更新属性面板为画布属性
        if self._property_panel and template:
            self._property_panel.set_canvas_properties(
                template.canvas_width,
                template.canvas_height,
                template.background_color,
            )
            self._property_panel.set_layer(None)

        # 重新设置撤销管理器
        self._setup_undo_manager()

        # 更新窗口标题
        if template:
            self.setWindowTitle(f"{WINDOW_TITLE} - {template.name}")
        else:
            self.setWindowTitle(WINDOW_TITLE)

        if self._statusbar:
            self._statusbar.showMessage(f"已加载模板: {template.name if template else '无'}")

    def _save_template(self) -> bool:
        """保存当前模板.

        Returns:
            是否保存成功
        """
        if not self._current_template:
            return False

        try:
            if self._template_manager.save_template(self._current_template):
                logger.info(f"模板已保存: {self._current_template.name}")
                if self._statusbar:
                    self._statusbar.showMessage(f"模板已保存: {self._current_template.name}")
                return True
            return False
        except Exception as e:
            logger.error(f"保存模板失败: {e}")
            QMessageBox.critical(self, "保存失败", f"无法保存模板:\n{e}")
            return False

    # ========================
    # 图层操作
    # ========================

    def _add_layer(self, layer) -> None:
        """添加图层到当前模板.

        Args:
            layer: 图层对象
        """
        if not self._current_template or not self._canvas:
            return

        # 添加到画布
        self._canvas.add_layer(layer)

        # 更新图层面板
        if self._layer_panel:
            self._layer_panel.set_layers(self._current_template.get_layers())

        # 记录撤销
        if self._undo_manager:
            self._undo_manager.record_add_layer(layer)
        
        # 标记为已修改
        self._set_modified(True)

        # 选中新图层
        self._canvas.select_layer(layer.id)

        if self._statusbar:
            self._statusbar.showMessage(f"已添加图层: {layer.name}")

    # ========================
    # 槽函数 - 菜单/工具栏
    # ========================

    def _on_new_template(self) -> None:
        """新建模板."""
        # TODO: 检查是否需要保存当前模板
        self._create_new_template()

    def _on_open_template(self) -> None:
        """打开模板文件."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "打开模板",
            str(self._template_dir),
            "模板文件 (*.json)",
        )

        if file_path:
            try:
                data = json.loads(Path(file_path).read_text(encoding="utf-8"))
                template = TemplateConfig(**data)
                self._set_current_template(template)
            except Exception as e:
                QMessageBox.critical(self, "打开失败", f"无法打开模板:\n{e}")

    def _on_save_template(self) -> None:
        """保存当前模板."""
        if self._current_template:
            if self._save_template():
                # 刷新列表并重新选中当前模板
                if self._template_list:
                    self._template_list.refresh()
                    self._template_list.select_template(self._current_template.id)
                self.template_saved.emit(self._current_template)
                # 清除未保存标记
                self._set_modified(False)

    def _on_save_template_as(self) -> None:
        """另存为."""
        if not self._current_template:
            return

        from PyQt6.QtWidgets import QInputDialog

        name, ok = QInputDialog.getText(
            self,
            "另存为",
            "请输入模板名称:",
            text=f"{self._current_template.name} - 副本",
        )

        if ok and name:
            new_template = self._template_manager.save_template_as(
                self._current_template, name
            )
            if new_template:
                self._set_current_template(new_template)
                # 刷新列表并选中新模板
                if self._template_list:
                    self._template_list.refresh()
                    self._template_list.select_template(new_template.id)
                
                self.template_saved.emit(new_template)
                # 清除未保存标记
                self._set_modified(False)
                if self._statusbar:
                    self._statusbar.showMessage(f"模板已保存为: {name}")

    def _on_undo(self) -> None:
        """撤销."""
        if self._undo_manager and self._undo_manager.can_undo:
            self._undo_manager.undo()

            # 刷新UI
            if self._current_template and self._layer_panel:
                self._layer_panel.set_layers(self._current_template.get_layers())

            if self._canvas:
                self._canvas.refresh_from_template()

    def _on_redo(self) -> None:
        """重做."""
        if self._undo_manager and self._undo_manager.can_redo:
            self._undo_manager.redo()

            # 刷新UI
            if self._current_template and self._layer_panel:
                self._layer_panel.set_layers(self._current_template.get_layers())

            if self._canvas:
                self._canvas.refresh_from_template()

    def _on_add_text_layer(self) -> None:
        """添加文字图层."""
        layer = TextLayer.create(
            content="新文字",
            x=100,
            y=100,
            font_size=24,
        )
        self._add_layer(layer)

    def _on_add_rectangle(self) -> None:
        """添加矩形."""
        layer = ShapeLayer.create_rectangle(
            x=100,
            y=100,
            width=150,
            height=100,
            fill_color=(200, 200, 200),
        )
        self._add_layer(layer)

    def _on_add_ellipse(self) -> None:
        """添加椭圆."""
        layer = ShapeLayer.create_ellipse(
            x=100,
            y=100,
            width=120,
            height=80,
            fill_color=(200, 200, 200),
        )
        self._add_layer(layer)

    def _on_add_image(self) -> None:
        """添加图片图层."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择图片",
            "",
            "图片文件 (*.png *.jpg *.jpeg *.webp *.bmp)",
        )

        if file_path:
            self._on_add_image_from_path(file_path)

    def _on_add_image_from_path(self, file_path: str) -> None:
        """从路径添加图片图层.

        Args:
            file_path: 图片路径
        """
        layer = ImageLayer.create(
            image_path=file_path,
            x=50,
            y=50,
        )
        self._add_layer(layer)

    def _on_delete_selected(self) -> None:
        """删除选中的图层."""
        if not self._canvas or not self._current_template:
            return

        selected = self._canvas.selected_layers
        if not selected:
            return

        for layer_id in selected:
            # 记录撤销
            if self._undo_manager:
                self._undo_manager.record_remove_layer(layer_id)
            else:
                self._canvas.remove_layer(layer_id)

        # 更新图层面板
        if self._layer_panel:
            self._layer_panel.set_layers(self._current_template.get_layers())

    def _on_copy(self) -> None:
        """复制选中图层."""
        # TODO: 实现复制功能
        pass

    def _on_paste(self) -> None:
        """粘贴图层."""
        # TODO: 实现粘贴功能
        pass

    # ========================
    # 槽函数 - 画布
    # ========================

    def _on_layer_selected(self, layer_id: str) -> None:
        """画布图层被选中.
        
        注意：此信号可能存在竞态，主要逻辑已移至 _on_selection_changed
        """
        pass

    def _on_layer_deselected(self, layer_id: str) -> None:
        """画布图层取消选中.
        
        注意：此信号可能存在竞态，主要逻辑已移至 _on_selection_changed
        """
        pass

    def _on_selection_changed(self, layer_ids: list[str]) -> None:
        """画布选择变更 - 统一处理选中逻辑.

        Args:
            layer_ids: 选中的图层ID列表
        """
        if not self._current_template:
            return
            
        if layer_ids:
            # 有选中图层，取第一个（单选模式）
            layer_id = layer_ids[0]
            layer = self._current_template.get_layer_by_id(layer_id)
            if layer:
                # 更新属性面板
                if self._property_panel:
                    self._property_panel.set_layer(layer)

                # 同步图层面板选择
                if self._layer_panel:
                    self._layer_panel.select_layer(layer_id)
        else:
            # 无选中，显示画布属性
            if self._property_panel:
                self._property_panel.set_canvas_properties(
                    self._current_template.canvas_width,
                    self._current_template.canvas_height,
                    self._current_template.background_color,
                )
                self._property_panel.set_layer(None)

    def _on_layer_moved(self, layer_id: str, x: int, y: int) -> None:
        """图层移动.

        Args:
            layer_id: 图层ID
            x: 新X坐标
            y: 新Y坐标
        """
        if not self._current_template:
            return

        # 模板数据已在 canvas._on_item_moved 中更新，这里只需刷新属性面板
        layer = self._current_template.get_layer_by_id(layer_id)
        if layer:
            # 标记为已修改
            self._set_modified(True)

            # 更新属性面板（传入最新的图层数据）
            if self._property_panel:
                self._property_panel.set_layer(layer)

    def _on_layer_resized(self, layer_id: str, width: int, height: int) -> None:
        """图层调整大小.

        Args:
            layer_id: 图层ID
            width: 新宽度
            height: 新高度
        """
        if not self._current_template:
            return

        # 模板数据已在 canvas._on_item_resized 中更新，这里只需刷新属性面板
        layer = self._current_template.get_layer_by_id(layer_id)
        if layer:
            # 标记为已修改
            self._set_modified(True)

            # 更新属性面板（传入最新的图层数据）
            if self._property_panel:
                self._property_panel.set_layer(layer)

    def _on_layer_content_changed(self, layer_id: str, content: str) -> None:
        """图层内容变更.

        Args:
            layer_id: 图层ID
            content: 新内容
        """
        # 更新属性面板
        if self._property_panel:
            self._property_panel.update_layer()

    # ========================
    # 槽函数 - 图层面板
    # ========================

    def _on_panel_layer_selected(self, layer_id: str) -> None:
        """图层面板选中图层.

        Args:
            layer_id: 图层ID
        """
        if self._canvas:
            self._canvas.select_layer(layer_id)

    def _on_layer_visibility_changed(self, layer_id: str, visible: bool) -> None:
        """图层可见性变更.

        Args:
            layer_id: 图层ID
            visible: 是否可见
        """
        if self._canvas:
            self._canvas.set_layer_visibility(layer_id, visible)

    def _on_layer_locked_changed(self, layer_id: str, locked: bool) -> None:
        """图层锁定状态变更.

        Args:
            layer_id: 图层ID
            locked: 是否锁定
        """
        if self._canvas:
            self._canvas.set_layer_locked(layer_id, locked)

    def _on_layers_reordered(self, layer_ids: list[str]) -> None:
        """图层重新排序.

        Args:
            layer_ids: 重新排序后的图层ID列表
        """
        if self._canvas:
            self._canvas.reorder_layers(layer_ids)

    def _on_layer_deleted(self, layer_id: str) -> None:
        """图层删除.

        Args:
            layer_id: 图层ID
        """
        if self._canvas and self._current_template:
            # 记录撤销
            if self._undo_manager:
                self._undo_manager.record_remove_layer(layer_id)
            else:
                self._canvas.remove_layer(layer_id)
            
            # 同步更新图层面板
            if self._layer_panel:
                self._layer_panel.remove_layer(layer_id)
            
            # 标记为已修改
            self._set_modified(True)

    # ========================
    # 槽函数 - 属性面板
    # ========================

    def _on_property_changed(
        self, layer_id: str, property_name: str, new_value
    ) -> None:
        """属性变更.

        Args:
            layer_id: 图层ID
            property_name: 属性名
            new_value: 新值
        """
        if not self._current_template:
            return

        layer = self._current_template.get_layer_by_id(layer_id)
        if layer:
            # 获取旧值
            old_value = getattr(layer, property_name, None)

            # 更新图层属性
            setattr(layer, property_name, new_value)
            self._current_template.update_layer(layer)
            
            # 标记为已修改
            self._set_modified(True)

            # 更新画布显示，并传递更新后的图层对象
            if self._canvas:
                self._canvas.update_layer(layer_id, layer)

            # 记录撤销
            if self._undo_manager:
                self._undo_manager.record_modify_layer(
                    layer_id, property_name, old_value, new_value
                )

    def _on_canvas_property_changed(
        self, property_name: str, new_value
    ) -> None:
        """画布属性变更.

        Args:
            property_name: 属性名
            new_value: 新值
        """
        if not self._current_template:
            return

        logger.info(f"_on_canvas_property_changed: {property_name} = {new_value}")

        # 获取旧值
        old_value = getattr(self._current_template, property_name, None)

        # 更新模板属性
        setattr(self._current_template, property_name, new_value)

        # 更新画布显示
        if self._canvas:
            self._canvas.refresh_from_template()

        # 记录撤销
        if self._undo_manager:
            self._undo_manager.record_modify_canvas(property_name, old_value, new_value)

    # ========================
    # 槽函数 - 模板列表
    # ========================

    def _on_template_selected_by_id(self, template_id: str) -> None:
        """模板列表选中模板 (ID).

        Args:
            template_id: 选中的模板ID
        """
        template = self._template_manager.load_template(template_id)
        if template:
            self._set_current_template(template)
            self.template_selected.emit(template)

    def _on_template_deleted(self, template_id: str) -> None:
        """模板删除.

        Args:
            template_id: 模板ID
        """
        # 如果删除的是当前模板，创建新模板
        if self._current_template and self._current_template.id == template_id:
            self._create_new_template()

    # ========================
    # 事件处理
    # ========================

    def closeEvent(self, event: QCloseEvent) -> None:
        """窗口关闭事件."""
        # TODO: 检查是否有未保存的更改
        event.accept()

    # ========================
    # 公共方法
    # ========================

    def get_current_template(self) -> Optional[TemplateConfig]:
        """获取当前模板.

        Returns:
            当前模板配置
        """
        return self._current_template

    def set_template(self, template: TemplateConfig) -> None:
        """设置模板.

        Args:
            template: 模板配置
        """
        self._set_current_template(template)
