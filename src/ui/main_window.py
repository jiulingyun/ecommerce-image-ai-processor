"""主窗口模块.

提供应用的主要用户界面，包括菜单栏、工具栏、状态栏和主工作区域。

布局结构:
    ┌─────────────────────────────────────────────────────────────┐
    │                         菜单栏                               │
    ├─────────────────────────────────────────────────────────────┤
    │                         工具栏                               │
    ├────────────────┬────────────────────┬───────────────────────┤
    │                │                    │                       │
    │   图片列表区    │     预览区域       │     配置面板          │
    │   (左侧面板)    │     (中间区域)     │     (右侧面板)        │
    │                │                    │                       │
    ├────────────────┴────────────────────┴───────────────────────┤
    │                         状态栏                               │
    └─────────────────────────────────────────────────────────────┘
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal, QSize, QEvent
from PyQt6.QtGui import QAction, QKeySequence, QCloseEvent, QResizeEvent
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMenuBar,
    QMessageBox,
    QProgressBar,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QStatusBar,
    QToolBar,
    QVBoxLayout,
    QWidget,
)


class ConstrainedScrollArea(QScrollArea):
    """约束内容宽度的滚动区域.
    
    确保内容宽度不超过滚动区域的可视区域宽度。
    """
    
    def resizeEvent(self, event: QResizeEvent) -> None:
        """Resize 事件处理."""
        super().resizeEvent(event)
        widget = self.widget()
        if widget:
            # 设置内容宽度为视口宽度（减去滚动条宽度）
            scrollbar_width = self.verticalScrollBar().width() if self.verticalScrollBar().isVisible() else 0
            available_width = self.viewport().width()
            widget.setFixedWidth(available_width)

from src.models.image_task import ImageTask
from src.ui.dialogs import SettingsDialog
from src.ui.widgets import (
    AIConfigPanel,
    ImagePairPanel,
    ImagePreview,
    OutputConfigPanel,
    ProcessConfigPanel,
    PromptConfigPanel,
    QueueProgressPanel,
    TaskListWidget,
)
from src.utils.constants import (
    APP_NAME,
    APP_VERSION,
    MAX_QUEUE_SIZE,
    WINDOW_MIN_HEIGHT,
    WINDOW_MIN_WIDTH,
)
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def _get_stylesheet() -> str:
    """加载样式表.

    Returns:
        样式表内容
    """
    style_path = Path(__file__).parent / "resources" / "styles.qss"
    if style_path.exists():
        try:
            return style_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.warning(f"加载样式表失败: {e}")
    return ""


class MainWindow(QMainWindow):
    """应用主窗口.

    提供应用的主要用户界面，包括菜单栏、工具栏、状态栏和主工作区域。

    Signals:
        images_imported: 图片导入信号，参数为图片路径列表
        process_started: 开始处理信号
        process_paused: 暂停处理信号
        process_cancelled: 取消处理信号
        queue_cleared: 队列清空信号
        settings_requested: 请求打开设置
        about_requested: 请求打开关于对话框

    Attributes:
        is_processing: 是否正在处理中
        queue_count: 当前队列数量
    """

    # 自定义信号
    images_imported = pyqtSignal(list)  # list[str]
    process_started = pyqtSignal()
    process_paused = pyqtSignal()
    process_cancelled = pyqtSignal()
    queue_cleared = pyqtSignal()
    settings_requested = pyqtSignal()
    about_requested = pyqtSignal()

    def __init__(self) -> None:
        """初始化主窗口."""
        super().__init__()

        # 状态属性
        self._is_processing: bool = False
        self._is_paused: bool = False
        self._queue_count: int = 0
        self._current_progress: int = 0

        # UI 组件引用
        self._toolbar: Optional[QToolBar] = None
        self._statusbar: Optional[QStatusBar] = None
        self._left_panel: Optional[QFrame] = None
        self._center_panel: Optional[QFrame] = None
        self._right_panel: Optional[QFrame] = None
        self._progress_bar: Optional[QProgressBar] = None
        self._status_label: Optional[QLabel] = None
        self._queue_label: Optional[QLabel] = None

        # 业务组件引用
        self._image_pair_panel: Optional[ImagePairPanel] = None
        self._task_list_widget: Optional[TaskListWidget] = None
        self._queue_progress_panel: Optional[QueueProgressPanel] = None
        self._image_preview: Optional[ImagePreview] = None
        self._ai_config_panel: Optional[AIConfigPanel] = None
        self._prompt_config_panel: Optional[PromptConfigPanel] = None
        self._process_config_panel: Optional[ProcessConfigPanel] = None
        self._output_config_panel: Optional[OutputConfigPanel] = None

        # 任务管理
        self._tasks: dict[str, ImageTask] = {}  # task_id -> ImageTask
        self._selected_task_id: Optional[str] = None

        # Action 引用
        self._action_export: Optional[QAction] = None
        self._action_start: Optional[QAction] = None
        self._action_pause: Optional[QAction] = None
        self._action_cancel: Optional[QAction] = None
        self._action_clear: Optional[QAction] = None
        self._action_settings: Optional[QAction] = None

        # 初始化
        self._setup_window()
        self._apply_stylesheet()
        self._setup_menubar()
        self._setup_toolbar()
        self._setup_central_widget()
        self._setup_statusbar()
        self._connect_signals()
        self._update_actions_state()

        logger.debug("主窗口初始化完成")

    # ========================
    # 属性
    # ========================

    @property
    def is_processing(self) -> bool:
        """是否正在处理中."""
        return self._is_processing

    @property
    def is_paused(self) -> bool:
        """是否已暂停."""
        return self._is_paused

    @property
    def queue_count(self) -> int:
        """当前队列数量."""
        return self._queue_count

    # ========================
    # 初始化方法
    # ========================

    def _setup_window(self) -> None:
        """设置窗口属性."""
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)

        # 默认窗口大小
        self.resize(1400, 900)

        # 窗口居中
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

    def _apply_stylesheet(self) -> None:
        """应用样式表."""
        stylesheet = _get_stylesheet()
        if stylesheet:
            self.setStyleSheet(stylesheet)
            logger.debug("样式表已应用")

    def _setup_menubar(self) -> None:
        """设置菜单栏."""
        menubar = self.menuBar()
        if menubar is None:
            return

        # 文件菜单
        file_menu = menubar.addMenu("文件(&F)")
        if file_menu:
            self._setup_file_menu(file_menu)

        # 编辑菜单
        edit_menu = menubar.addMenu("编辑(&E)")
        if edit_menu:
            self._setup_edit_menu(edit_menu)

        # 处理菜单
        process_menu = menubar.addMenu("处理(&P)")
        if process_menu:
            self._setup_process_menu(process_menu)

        # 帮助菜单
        help_menu = menubar.addMenu("帮助(&H)")
        if help_menu:
            self._setup_help_menu(help_menu)

    def _setup_file_menu(self, menu: QMenu) -> None:
        """设置文件菜单."""
        # 导出结果
        self._action_export = QAction("导出结果(&E)...", self)
        self._action_export.setShortcut(QKeySequence("Ctrl+Shift+E"))
        self._action_export.setStatusTip("导出处理结果")
        self._action_export.setEnabled(False)
        menu.addAction(self._action_export)

        menu.addSeparator()

        # 退出
        action_exit = QAction("退出(&X)", self)
        action_exit.setShortcut(QKeySequence.StandardKey.Quit)
        action_exit.setStatusTip("退出应用")
        action_exit.triggered.connect(self.close)
        menu.addAction(action_exit)

    def _setup_edit_menu(self, menu: QMenu) -> None:
        """设置编辑菜单."""
        # 设置
        self._action_settings = QAction("设置(&S)...", self)
        self._action_settings.setShortcut(QKeySequence("Ctrl+,"))
        self._action_settings.setStatusTip("打开应用设置")
        self._action_settings.triggered.connect(self._on_settings)
        menu.addAction(self._action_settings)

        menu.addSeparator()

        # 清空队列
        self._action_clear = QAction("清空队列(&C)", self)
        self._action_clear.setShortcut(QKeySequence("Ctrl+Shift+C"))
        self._action_clear.setStatusTip("清空处理队列")
        self._action_clear.triggered.connect(self._on_clear_queue)
        menu.addAction(self._action_clear)

    def _setup_process_menu(self, menu: QMenu) -> None:
        """设置处理菜单."""
        # 开始处理
        self._action_start = QAction("开始处理(&S)", self)
        self._action_start.setShortcut(QKeySequence("F5"))
        self._action_start.setStatusTip("开始处理队列中的图片")
        self._action_start.triggered.connect(self._on_start_process)
        menu.addAction(self._action_start)

        # 暂停处理
        self._action_pause = QAction("暂停处理(&P)", self)
        self._action_pause.setShortcut(QKeySequence("F6"))
        self._action_pause.setStatusTip("暂停当前处理")
        self._action_pause.triggered.connect(self._on_pause_process)
        menu.addAction(self._action_pause)

        # 取消处理
        self._action_cancel = QAction("取消处理(&X)", self)
        self._action_cancel.setShortcut(QKeySequence("F7"))
        self._action_cancel.setStatusTip("取消并停止处理")
        self._action_cancel.triggered.connect(self._on_cancel_process)
        menu.addAction(self._action_cancel)

    def _setup_help_menu(self, menu: QMenu) -> None:
        """设置帮助菜单."""
        # 使用帮助
        action_help = QAction("使用帮助(&H)", self)
        action_help.setShortcut(QKeySequence.StandardKey.HelpContents)
        action_help.setStatusTip("查看使用帮助")
        menu.addAction(action_help)

        menu.addSeparator()

        # 关于
        action_about = QAction("关于(&A)...", self)
        action_about.setStatusTip(f"关于 {APP_NAME}")
        action_about.triggered.connect(self._on_about)
        menu.addAction(action_about)

    def _setup_toolbar(self) -> None:
        """设置工具栏."""
        self._toolbar = QToolBar("主工具栏")
        self._toolbar.setMovable(False)
        self._toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(self._toolbar)

        # 开始处理按钮
        if self._action_start:
            self._action_start.setText("开始处理")
            self._toolbar.addAction(self._action_start)

        # 暂停按钮
        if self._action_pause:
            self._action_pause.setText("暂停")
            self._toolbar.addAction(self._action_pause)

        # 取消按钮
        if self._action_cancel:
            self._action_cancel.setText("取消")
            self._toolbar.addAction(self._action_cancel)

        self._toolbar.addSeparator()

        # 清空队列按钮
        if self._action_clear:
            self._action_clear.setText("清空队列")
            self._toolbar.addAction(self._action_clear)

        # 弹性空间
        spacer = QWidget()
        spacer.setSizePolicy(
            spacer.sizePolicy().horizontalPolicy().Expanding,
            spacer.sizePolicy().verticalPolicy().Preferred,
        )
        self._toolbar.addWidget(spacer)

        # 设置按钮
        if self._action_settings:
            self._action_settings.setText("设置")
            self._toolbar.addAction(self._action_settings)

    def _setup_central_widget(self) -> None:
        """设置中央区域."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 主布局
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 创建分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)

        # 左侧面板 - 图片列表/上传区域
        self._left_panel = self._create_left_panel()
        splitter.addWidget(self._left_panel)

        # 中间面板 - 预览区域
        self._center_panel = self._create_center_panel()
        splitter.addWidget(self._center_panel)

        # 右侧面板 - 配置面板
        self._right_panel = self._create_right_panel()
        splitter.addWidget(self._right_panel)

        # 设置分割比例 (约 1:2:1)
        splitter.setSizes([300, 600, 300])

        # 设置最小宽度
        self._left_panel.setMinimumWidth(250)
        self._center_panel.setMinimumWidth(400)
        self._right_panel.setMinimumWidth(280)

    def _create_left_panel(self) -> QFrame:
        """创建左侧面板 - 图片配对与任务列表.

        Returns:
            左侧面板 QFrame
        """
        panel = QFrame()
        panel.setProperty("panel", True)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # 图片配对面板
        self._image_pair_panel = ImagePairPanel()
        layout.addWidget(self._image_pair_panel)

        # 分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator)

        # 任务列表
        self._task_list_widget = TaskListWidget()
        layout.addWidget(self._task_list_widget, 1)

        # 分隔线
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.Shape.HLine)
        separator2.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator2)

        # 队列进度面板
        self._queue_progress_panel = QueueProgressPanel()
        layout.addWidget(self._queue_progress_panel)

        return panel

    def _create_center_panel(self) -> QFrame:
        """创建中间面板 - 预览区域.

        Returns:
            中间面板 QFrame
        """
        # 直接使用 ImagePreview 组件作为中间面板
        self._image_preview = ImagePreview()
        return self._image_preview

    def _create_right_panel(self) -> QScrollArea:
        """创建右侧面板 - 配置面板.

        Returns:
            右侧面板 QScrollArea
        """
        # 创建滚动区域以支持内容超出时滚动
        scroll_area = ConstrainedScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setStyleSheet("QScrollArea { background-color: #ffffff; border: none; }")

        # 内容容器
        content_widget = QWidget()
        content_widget.setObjectName("rightPanelContent")
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # AI 服务配置面板
        self._ai_config_panel = AIConfigPanel()
        layout.addWidget(self._ai_config_panel)

        # 分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setStyleSheet("background-color: #e8e8e8;")
        layout.addWidget(separator)

        # AI 提示词配置面板
        self._prompt_config_panel = PromptConfigPanel()
        layout.addWidget(self._prompt_config_panel)

        # 分隔线
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.Shape.HLine)
        separator2.setFrameShadow(QFrame.Shadow.Sunken)
        separator2.setStyleSheet("background-color: #e8e8e8;")
        layout.addWidget(separator2)

        # 后期处理配置面板
        self._process_config_panel = ProcessConfigPanel()
        layout.addWidget(self._process_config_panel)

        # 分隔线
        separator3 = QFrame()
        separator3.setFrameShape(QFrame.Shape.HLine)
        separator3.setFrameShadow(QFrame.Shadow.Sunken)
        separator3.setStyleSheet("background-color: #e8e8e8;")
        layout.addWidget(separator3)

        # 输出配置面板
        self._output_config_panel = OutputConfigPanel()
        layout.addWidget(self._output_config_panel)

        # 底部弹性空间
        layout.addStretch()

        scroll_area.setWidget(content_widget)
        return scroll_area

    def _setup_statusbar(self) -> None:
        """设置状态栏."""
        self._statusbar = QStatusBar()
        self.setStatusBar(self._statusbar)

        # 状态文本
        self._status_label = QLabel("就绪")
        self._statusbar.addWidget(self._status_label, 1)

        # 队列状态
        self._queue_label = QLabel(f"队列: 0/{MAX_QUEUE_SIZE}")
        self._statusbar.addPermanentWidget(self._queue_label)

        # 进度条
        self._progress_bar = QProgressBar()
        self._progress_bar.setFixedWidth(200)
        self._progress_bar.setVisible(False)
        self._statusbar.addPermanentWidget(self._progress_bar)

    def _connect_signals(self) -> None:
        """连接信号槽."""
        # 图片配对面板信号
        if self._image_pair_panel:
            self._image_pair_panel.task_added.connect(self._on_task_added)

        # 任务列表信号
        if self._task_list_widget:
            self._task_list_widget.task_selected.connect(self._on_task_selected)
            self._task_list_widget.task_deleted.connect(self._on_task_deleted)

        # 队列进度面板信号
        if self._queue_progress_panel:
            self._queue_progress_panel.start_clicked.connect(self._on_start_process)
            self._queue_progress_panel.pause_clicked.connect(self._on_pause_process)
            self._queue_progress_panel.cancel_clicked.connect(self._on_cancel_process)

    def _update_actions_state(self) -> None:
        """更新操作按钮状态."""
        has_queue = self._queue_count > 0
        is_idle = not self._is_processing

        # 开始 - 有队列且非处理中可用
        if self._action_start:
            self._action_start.setEnabled(has_queue and is_idle)

        # 暂停 - 处理中且未暂停可用
        if self._action_pause:
            self._action_pause.setEnabled(self._is_processing and not self._is_paused)
            if self._is_paused:
                self._action_pause.setText("继续")
            else:
                self._action_pause.setText("暂停")

        # 取消 - 处理中可用
        if self._action_cancel:
            self._action_cancel.setEnabled(self._is_processing)

        # 清空 - 有队列且非处理中可用
        if self._action_clear:
            self._action_clear.setEnabled(has_queue and is_idle)

        # 导出 - 有完成的结果可用（暂时禁用）
        if self._action_export:
            self._action_export.setEnabled(False)

    # ========================
    # 公共方法
    # ========================

    def update_queue_count(self, count: int) -> None:
        """更新队列数量.

        Args:
            count: 队列中的任务数量
        """
        self._queue_count = min(count, MAX_QUEUE_SIZE)
        if self._queue_label:
            self._queue_label.setText(f"队列: {self._queue_count}/{MAX_QUEUE_SIZE}")

        # 更新进度面板的任务数
        if self._queue_progress_panel:
            self._queue_progress_panel.set_total_tasks(self._queue_count)
        
        self._update_actions_state()

    def update_progress(self, progress: int, message: str = "") -> None:
        """更新处理进度.

        Args:
            progress: 进度值 (0-100)
            message: 状态消息
        """
        self._current_progress = progress
        if self._progress_bar:
            self._progress_bar.setValue(progress)
            self._progress_bar.setVisible(progress > 0 and progress < 100)
        if self._status_label and message:
            self._status_label.setText(message)

    def set_processing_state(self, is_processing: bool, is_paused: bool = False) -> None:
        """设置处理状态.

        Args:
            is_processing: 是否正在处理
            is_paused: 是否已暂停
        """
        self._is_processing = is_processing
        self._is_paused = is_paused
        self._update_actions_state()

        # 同步进度面板状态
        if self._queue_progress_panel:
            self._queue_progress_panel.set_processing_state(is_processing, is_paused)

        if not is_processing:
            self.update_progress(0, "就绪")

    def show_status_message(self, message: str, timeout: int = 3000) -> None:
        """在状态栏显示临时消息.

        Args:
            message: 消息内容
            timeout: 显示时长(毫秒)，0表示永久
        """
        if self._statusbar:
            self._statusbar.showMessage(message, timeout)

    # ========================
    # 槽函数
    # ========================

    def _on_start_process(self) -> None:
        """开始处理."""
        if self._queue_count == 0:
            QMessageBox.information(self, "提示", "队列为空，请先导入图片。")
            return

        self.set_processing_state(True)
        self.process_started.emit()
        self.update_progress(0, "正在处理...")
        logger.info("开始处理队列")

    def _on_pause_process(self) -> None:
        """暂停/继续处理."""
        if self._is_paused:
            # 继续处理
            self.set_processing_state(True, False)
            self.process_started.emit()  # 复用开始信号
            self.update_progress(self._current_progress, "正在处理...")
            logger.info("继续处理")
        else:
            # 暂停处理
            self.set_processing_state(True, True)
            self.process_paused.emit()
            self.update_progress(self._current_progress, "已暂停")
            logger.info("暂停处理")

    def _on_cancel_process(self) -> None:
        """取消处理."""
        reply = QMessageBox.question(
            self,
            "确认取消",
            "确定要取消当前处理吗？\n已完成的任务不会受影响。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.set_processing_state(False)
            self.process_cancelled.emit()
            self.update_progress(0, "已取消")
            logger.info("取消处理")

    def _on_clear_queue(self) -> None:
        """清空队列."""
        if self._queue_count == 0:
            return

        reply = QMessageBox.question(
            self,
            "确认清空",
            f"确定要清空队列中的 {self._queue_count} 个任务吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            # 清空任务
            self._tasks.clear()
            self._selected_task_id = None

            # 清空列表
            if self._task_list_widget:
                self._task_list_widget.clear_all()

            # 清空预览
            if self._image_preview:
                self._image_preview.clear()

            # 更新配对面板
            if self._image_pair_panel:
                self._image_pair_panel.set_queue_count(0)

            # 重置进度面板
            if self._queue_progress_panel:
                self._queue_progress_panel.reset()

            self.queue_cleared.emit()
            self.update_queue_count(0)
            self.show_status_message("队列已清空")
            logger.info("清空队列")

    def _on_task_added(self, background_path: str, product_path: str) -> None:
        """处理任务添加.

        Args:
            background_path: 背景图路径
            product_path: 商品图路径
        """
        # 检查队列是否已满
        if self._queue_count >= MAX_QUEUE_SIZE:
            QMessageBox.warning(
                self,
                "队列已满",
                f"队列最多支持 {MAX_QUEUE_SIZE} 个任务。\n请等待处理完成或清空队列。",
            )
            return

        # 创建任务
        task = ImageTask(
            background_path=background_path,
            product_path=product_path,
        )

        # 保存任务
        self._tasks[task.id] = task

        # 添加到列表
        if self._task_list_widget:
            self._task_list_widget.add_task(task)

        # 更新队列计数
        self.update_queue_count(len(self._tasks))

        # 更新配对面板的队列计数
        if self._image_pair_panel:
            self._image_pair_panel.set_queue_count(len(self._tasks))

        # 发送信号
        self.images_imported.emit([background_path, product_path])

        self.show_status_message(f"已添加任务: {task.background_filename}")
        logger.info(f"添加任务: {task.id}")

    def _on_task_selected(self, task: ImageTask) -> None:
        """处理任务选中.

        Args:
            task: 选中的任务
        """
        self._selected_task_id = task.id if task else None

        # 更新预览
        if self._image_preview:
            self._image_preview.set_task(task)

        if task:
            logger.debug(f"选中任务: {task.id}")

    def _on_task_deleted(self, task_id: str) -> None:
        """处理任务删除.

        Args:
            task_id: 任务 ID
        """
        # 移除任务
        if task_id in self._tasks:
            task = self._tasks.pop(task_id)
            logger.info(f"删除任务: {task_id}")

        # 从列表移除
        if self._task_list_widget:
            self._task_list_widget.remove_task(task_id)

        # 如果删除的是当前选中的任务，清空预览
        if self._selected_task_id == task_id:
            self._selected_task_id = None
            if self._image_preview:
                self._image_preview.clear()

        # 更新队列计数
        self.update_queue_count(len(self._tasks))

        # 更新配对面板的队列计数
        if self._image_pair_panel:
            self._image_pair_panel.set_queue_count(len(self._tasks))

        self.show_status_message("已删除任务")

    def _on_settings(self) -> None:
        """打开设置对话框."""
        self.settings_requested.emit()
        
        dialog = SettingsDialog(self)
        dialog.settings_changed.connect(self._on_settings_changed)
        dialog.exec()
        logger.debug("设置对话框已关闭")

    def _on_settings_changed(self) -> None:
        """设置变更处理."""
        self.show_status_message("设置已更新")
        logger.info("应用设置已变更")

    def _on_about(self) -> None:
        """显示关于对话框."""
        self.about_requested.emit()

        # 临时使用简单对话框（后续实现专用对话框）
        QMessageBox.about(
            self,
            f"关于 {APP_NAME}",
            f"<h3>{APP_NAME}</h3>"
            f"<p>版本: {APP_VERSION}</p>"
            "<p>一款基于 AI 的电商图片批量处理工具。</p>"
            "<p>支持背景去除、商品合成、边框添加等功能。</p>",
        )
        logger.debug("显示关于对话框")

    # ========================
    # 事件处理
    # ========================

    def closeEvent(self, event: QCloseEvent) -> None:
        """窗口关闭事件."""
        if self._is_processing:
            reply = QMessageBox.question(
                self,
                "确认退出",
                "正在处理中，确定要退出吗？\n当前处理将被取消。",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )

            if reply == QMessageBox.StandardButton.No:
                event.ignore()
                return

            # 发送取消信号
            self.process_cancelled.emit()

        logger.info("主窗口关闭")
        event.accept()
