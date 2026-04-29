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

import logging
import os
import threading
from enum import Enum, auto
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal, QSize, QEvent, QTimer
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

from src.core.config_manager import get_config
from src.core.queue_worker import QueueController, get_queue_controller
from src.models.api_config import APIConfig
from src.models.batch_queue import QueueStats
from src.models.image_task import ImageTask, TaskStatus
from src.models.process_config import ProcessConfig
from src.services.ai_service import get_ai_service
from src.ui.dialogs import AboutDialog, SettingsDialog, TemplateEditorWindow
from src.ui.widgets import (
    ImageUploadPanel,
    ImagePreview,
    OutputConfigPanel,
    ProcessConfigPanel,
    PromptConfigPanel,
    TaskListWidget,
    TemplateConfigPanel,
    ToastManager,
    get_toast_manager,
)
from src.ui.widgets.toolbar_queue_progress import ToolbarQueueProgress
from src.utils.error_messages import (
    get_user_friendly_error,
    UserFriendlyError,
)
from src.utils.constants import (
    APP_NAME,
    APP_VERSION,
    MAX_QUEUE_SIZE,
    WINDOW_MIN_HEIGHT,
    WINDOW_MIN_WIDTH,
    APP_URL,
    APP_AUTHOR
)
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class ProcessingRunState(Enum):
    """主窗口处理流程 UI 状态机（与后台协作式暂停/取消配合）."""

    IDLE = auto()
    PROCESSING = auto()
    PAUSING = auto()  # 已请求暂停，等待当前阶段结束
    PAUSED = auto()
    CANCELLING = auto()  # 已请求取消，等待当前阶段结束


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
        self._is_cancelling: bool = False
        self._run_state: ProcessingRunState = ProcessingRunState.IDLE
        self._queue_count: int = 0
        self._current_progress: int = 0

        # 暂停：轮询后端是否真正停住，避免 UI 提前显示「已暂停」
        self._pause_settle_timer = QTimer(self)
        self._pause_settle_timer.setInterval(200)
        self._pause_settle_timer.timeout.connect(self._on_pause_settled)
        # 取消：长时间未结束时提示强制结束
        self._cancel_watch_timer = QTimer(self)
        self._cancel_watch_timer.setSingleShot(True)
        self._cancel_watch_timer.timeout.connect(self._on_cancel_watch_timeout)

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
        self._image_upload_panel: Optional[ImageUploadPanel] = None
        self._task_list_widget: Optional[TaskListWidget] = None
        self._image_preview: Optional[ImagePreview] = None
        self._prompt_config_panel: Optional[PromptConfigPanel] = None
        self._process_config_panel: Optional[ProcessConfigPanel] = None
        self._template_config_panel: Optional[TemplateConfigPanel] = None
        self._output_config_panel: Optional[OutputConfigPanel] = None

        # 任务管理
        self._tasks: dict[str, ImageTask] = {}  # task_id -> ImageTask
        self._selected_task_id: Optional[str] = None
        
        # 工具栏进度组件
        self._toolbar_progress: Optional[ToolbarQueueProgress] = None

        # Action 引用
        self._action_export: Optional[QAction] = None
        self._action_start: Optional[QAction] = None
        self._action_pause: Optional[QAction] = None
        self._action_cancel: Optional[QAction] = None
        self._action_clear: Optional[QAction] = None
        self._action_settings: Optional[QAction] = None
        self._action_template_editor: Optional[QAction] = None

        # Toast 通知管理器
        self._toast_manager: Optional[ToastManager] = None

        # 队列控制器
        self._queue_controller: Optional[QueueController] = None

        # 初始化
        self._setup_window()
        self._setup_menubar()
        self._setup_toolbar()
        self._setup_central_widget()
        self._setup_statusbar()
        self._setup_toast_manager()
        self._setup_queue_controller()
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

        # 模板菜单
        template_menu = menubar.addMenu("模板(&T)")
        if template_menu:
            self._setup_template_menu(template_menu)

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

    def _setup_template_menu(self, menu: QMenu) -> None:
        """设置模板菜单."""
        # 模板编辑器
        self._action_template_editor = QAction("模板编辑器(&E)...", self)
        self._action_template_editor.setShortcut(QKeySequence("Ctrl+Shift+T"))
        self._action_template_editor.setStatusTip("打开模板编辑器，创建和编辑模板")
        self._action_template_editor.triggered.connect(self._on_open_template_editor)
        menu.addAction(self._action_template_editor)

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

        self._toolbar.addSeparator()

        # 队列进度信息（中间区域）
        self._toolbar_progress = ToolbarQueueProgress()
        self._toolbar.addWidget(self._toolbar_progress)

        # 弹性空间
        spacer = QWidget()
        spacer.setSizePolicy(
            spacer.sizePolicy().horizontalPolicy().Expanding,
            spacer.sizePolicy().verticalPolicy().Preferred,
        )
        self._toolbar.addWidget(spacer)

        # 模板编辑器按钮
        if self._action_template_editor:
            self._action_template_editor.setText("模板编辑器")
            self._toolbar.addAction(self._action_template_editor)

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
        """创建左侧面板 - 图片上传与任务列表.

        Returns:
            左侧面板 QFrame
        """
        panel = QFrame()
        panel.setProperty("panel", True)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # 图片上传面板（多图上传）
        self._image_upload_panel = ImageUploadPanel()
        layout.addWidget(self._image_upload_panel)

        # 分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator)

        # 任务列表（占据所有剩余空间）
        self._task_list_widget = TaskListWidget()
        layout.addWidget(self._task_list_widget, 1)

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
        # scroll_area.setStyleSheet("QScrollArea { background-color: #ffffff; border: none; }")

        # 内容容器
        content_widget = QWidget()
        content_widget.setObjectName("rightPanelContent")
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # AI 提示词配置面板
        self._prompt_config_panel = PromptConfigPanel()
        layout.addWidget(self._prompt_config_panel)

        # 分隔线
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.Shape.HLine)
        separator2.setFrameShadow(QFrame.Shadow.Sunken)
        # separator2.setStyleSheet("background-color: #e8e8e8;")
        layout.addWidget(separator2)

        # 后期处理配置面板
        self._process_config_panel = ProcessConfigPanel()
        layout.addWidget(self._process_config_panel)

        # 分隔线
        separator3 = QFrame()
        separator3.setFrameShape(QFrame.Shape.HLine)
        separator3.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator3)

        # 模板配置面板
        self._template_config_panel = TemplateConfigPanel()
        layout.addWidget(self._template_config_panel)

        # 分隔线
        separator4 = QFrame()
        separator4.setFrameShape(QFrame.Shape.HLine)
        separator4.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator4)

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

    def _setup_toast_manager(self) -> None:
        """设置 Toast 通知管理器."""
        self._toast_manager = get_toast_manager(self)

    def _setup_queue_controller(self) -> None:
        """设置队列控制器."""
        self._queue_controller = get_queue_controller(self)
        
        # 连接控制器信号
        self._queue_controller.progress_updated.connect(self._on_queue_progress)
        self._queue_controller.task_started.connect(self._on_queue_task_started)
        self._queue_controller.task_progress.connect(self._on_queue_task_progress)
        self._queue_controller.task_completed.connect(self._on_queue_task_completed)
        self._queue_controller.task_failed.connect(self._on_queue_task_failed)
        self._queue_controller.task_cancelled.connect(self._on_queue_task_cancelled)
        self._queue_controller.all_completed.connect(self._on_queue_completed)
        self._queue_controller.error_occurred.connect(self._on_queue_error)

    def _connect_signals(self) -> None:
        """连接信号槽."""
        # 图片上传面板信号
        if self._image_upload_panel:
            self._image_upload_panel.task_added.connect(self._on_task_added)

        # 任务列表信号
        if self._task_list_widget:
            self._task_list_widget.task_selected.connect(self._on_task_selected)
            self._task_list_widget.task_deleted.connect(self._on_task_deleted)
            self._task_list_widget.task_retry.connect(self._on_task_retry)

        # 模板配置面板信号
        if self._template_config_panel:
            self._template_config_panel.edit_template_requested.connect(self._on_edit_template_requested)

    def _on_edit_template_requested(self, template_id: str) -> None:
        """处理编辑模板请求.

        Args:
            template_id: 模板 ID，空字符串表示新建
        """
        self._open_template_editor(template_id if template_id else None)

    def _collect_current_config(self) -> ProcessConfig:
        """从右侧面板收集当前配置.

        Returns:
            当前的处理配置
        """
        # 获取提示词配置
        prompt_config = None
        if self._prompt_config_panel:
            prompt_config = self._prompt_config_panel.get_config()

        # 获取后期处理配置（背景、边框、文字）
        process_config = ProcessConfig()
        if self._process_config_panel:
            process_config = self._process_config_panel.get_config()

        # 获取输出配置
        output_config = None
        if self._output_config_panel:
            output_dict = self._output_config_panel.get_config()
            # output_config_panel 使用自己的枚举，需要转换为 process_config 的枚举
            from src.models.process_config import (
                OutputConfig,
                OutputFormat as ModelOutputFormat,
                ResizeMode as ModelResizeMode,
            )
            
            # 转换输出格式
            ui_format = output_dict.get("format")
            format_map = {
                "JPEG": ModelOutputFormat.JPEG,
                "PNG": ModelOutputFormat.PNG,
                "WEBP": ModelOutputFormat.WEBP,
                "WebP": ModelOutputFormat.WEBP,
            }
            model_format = format_map.get(
                ui_format.value if hasattr(ui_format, 'value') else str(ui_format),
                ModelOutputFormat.JPEG
            )
            
            # 转换尺寸模式
            ui_resize_mode = output_dict.get("resize_mode")
            resize_map = {
                "ORIGINAL": ModelResizeMode.NONE,
                "FIT": ModelResizeMode.FIT,
                "FILL": ModelResizeMode.FILL,
                "STRETCH": ModelResizeMode.STRETCH,
                "CUSTOM": ModelResizeMode.FIT,
            }
            resize_mode_name = ui_resize_mode.name if hasattr(ui_resize_mode, 'name') else str(ui_resize_mode)
            model_resize_mode = resize_map.get(resize_mode_name, ModelResizeMode.NONE)
            
            output_size = output_dict.get("output_size", (1024, 1024))
            output_config = OutputConfig(
                format=model_format,
                quality=output_dict.get("quality", 95),
                resize_mode=model_resize_mode,
                size=output_size,
            )

        # 加载抠图服务配置（从用户配置中加载）
        # 抠图服务的 enabled 状态由背景配置的 enabled 控制
        from src.core.config_manager import get_config
        from src.models.process_config import BackgroundRemovalConfig, BackgroundRemovalProvider
        
        # 获取背景配置的启用状态
        bg_enabled = process_config.background.enabled if process_config else True
        
        bg_removal_config = None
        try:
            config_manager = get_config()
            bg_removal_data = config_manager.get_user_config("background_removal", {})
            if bg_removal_data:
                provider = bg_removal_data.get("provider", "external_api")
                bg_removal_config = BackgroundRemovalConfig(
                    enabled=bg_enabled,  # 由背景配置控制
                    provider=BackgroundRemovalProvider(provider),
                    api_url=bg_removal_data.get("api_url", "http://localhost:5000/api/remove-background"),
                    api_key=bg_removal_data.get("api_key", ""),
                    proxy=bg_removal_data.get("proxy"),
                    timeout=bg_removal_data.get("timeout", 120),
                )
            else:
                # 没有配置时也要创建默认配置，尊重 enabled 状态
                bg_removal_config = BackgroundRemovalConfig(enabled=bg_enabled)
        except Exception as e:
            logger.warning(f"加载抠图服务配置失败: {e}")
            bg_removal_config = BackgroundRemovalConfig(enabled=bg_enabled)

        # 获取模板配置
        template_config = None
        processing_mode = None
        if self._template_config_panel:
            template_config = self._template_config_panel.get_config()
            if template_config and template_config.enabled:
                from src.models.process_config import ProcessingMode
                processing_mode = ProcessingMode.TEMPLATE

        # 组合所有配置
        from src.models.process_config import ProcessingMode
        return ProcessConfig(
            mode=processing_mode or ProcessingMode.SIMPLE,
            ai_editing=process_config.ai_editing,
            prompt=prompt_config,
            background_removal=bg_removal_config,
            background=process_config.background,
            border=process_config.border,
            text=process_config.text,
            template=template_config,
            output=output_config,
        )

    def _toolbar_phase(self) -> str:
        """工具栏进度条旁文案阶段（与 ToolbarQueueProgress.ui_phase 对齐）."""
        if self._run_state == ProcessingRunState.PAUSING:
            return "pausing"
        if self._run_state == ProcessingRunState.CANCELLING:
            return "cancelling"
        return ""

    def _set_run_state(
        self,
        state: ProcessingRunState,
        *,
        status_message: Optional[str] = None,
        reset_progress_to_zero: bool = False,
    ) -> None:
        """统一切换 RunState，并同步工具栏进度与按钮."""
        self._run_state = state
        if state == ProcessingRunState.IDLE:
            self._pause_settle_timer.stop()
            self._cancel_watch_timer.stop()
            self._is_processing = False
            self._is_paused = False
            self._is_cancelling = False
            if self._toolbar_progress:
                self._toolbar_progress.set_processing_state(False, False, "")
            self._update_actions_state()
            self.update_progress(0, status_message if status_message is not None else "就绪")
            return

        self._is_processing = True
        self._is_paused = state == ProcessingRunState.PAUSED
        if self._toolbar_progress:
            self._toolbar_progress.set_processing_state(
                True, self._is_paused, self._toolbar_phase()
            )
        self._update_actions_state()
        if status_message is not None:
            prog = 0 if reset_progress_to_zero else self._current_progress
            self.update_progress(prog, status_message)

    def _decorate_progress_message(self, message: str) -> str:
        """在暂停中/取消中阶段为底部进度文案加上一致语义."""
        if self._run_state == ProcessingRunState.PAUSING:
            return f"{message} · 将暂停" if message else "暂停中（等待当前步骤完成）"
        if self._run_state == ProcessingRunState.CANCELLING:
            return f"{message} · 取消中" if message else "取消中（等待当前步骤结束）"
        return message

    def _on_pause_settled(self) -> None:
        """协作式暂停：当前阶段结束后将 UI 切到「已暂停」，避免与进度条冲突."""
        if self._run_state != ProcessingRunState.PAUSING:
            return
        if self._queue_controller and not self._queue_controller.is_paused:
            return
        self._pause_settle_timer.stop()
        self._set_run_state(
            ProcessingRunState.PAUSED,
            status_message="已暂停（点击「继续」恢复处理）",
        )

    def _kill_process_and_exit(self, exit_code: int = 0) -> None:
        """优先安全退出，必要时保留延迟兜底."""
        fallback_delay_s = 5.0
        graceful_stopped = True

        if self._queue_controller:
            graceful_stopped = self._queue_controller.stop(timeout_ms=3000)

        app = QApplication.instance()
        fallback_timer: Optional[threading.Timer] = None

        if not graceful_stopped:
            logger.error("后台线程仍未完全退出，将先请求应用正常关闭，并保留延迟兜底")
            fallback_timer = threading.Timer(
                fallback_delay_s,
                lambda: os._exit(exit_code),
            )
            fallback_timer.daemon = True
            fallback_timer.start()

        if app and fallback_timer is not None:
            app.aboutToQuit.connect(fallback_timer.cancel)

        logging.shutdown()

        if app:
            app.exit(exit_code)
            app.quit()
            if graceful_stopped:
                return
            return

        os._exit(exit_code)

    def _on_cancel_watch_timeout(self) -> None:
        """取消长时间未结束时提示强制结束."""
        if self._run_state != ProcessingRunState.CANCELLING:
            return
        reply = QMessageBox.question(
            self,
            "取消耗时较长",
            "取消已等待较长时间仍未结束，是否强制结束后台任务？\n"
            "（未完成项将标记为已取消）",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            logger.error("取消超时后用户选择强制结束，应用将立即退出")
            self._kill_process_and_exit(0)

    def _task_needs_ai(self, task: ImageTask, config: ProcessConfig) -> bool:
        """判断任务是否依赖 AI 服务."""
        # 多图任务一定需要 AI 合成
        if task.image_count > 1:
            return True

        # 单图启用 AI 增强时需要 AI
        if config.ai_editing.enabled:
            return True

        # 启用抠图且使用 AI 抠图提供者时需要 AI
        if (
            config.background.enabled
            and config.background_removal.enabled
            and config.background_removal.provider.value == "ai"
        ):
            return True

        return False

    def _ensure_ai_service_available(
        self,
        tasks: dict[str, ImageTask],
        config: ProcessConfig,
    ) -> bool:
        """若任务依赖 AI，则在启动前校验 AI 服务配置是否可用."""
        needs_ai = any(self._task_needs_ai(task, config) for task in tasks.values())
        if not needs_ai:
            return True

        config_manager = get_config()
        api_config_data = config_manager.get_user_config("api_config", {})
        api_key = str(api_config_data.get("api_key", "")).strip()
        if not api_key:
            QMessageBox.warning(
                self,
                "AI服务不可用",
                "AI服务不可用，请检查设置后重试",
            )
            return False

        try:
            # 只做快速本地校验：配置可解析且服务实例可构建。
            # 避免在 UI 线程中同步执行网络健康检查导致卡顿。
            model_data = api_config_data.get("model") or {"model": "qwen-image-edit-plus"}
            api_config = APIConfig(api_key=api_key, model=model_data)
            get_ai_service(config=api_config)
            return True
        except Exception:
            QMessageBox.warning(
                self,
                "AI服务不可用",
                "AI服务不可用，请检查设置后重试",
            )
            return False

    def _force_stop_processing(
        self,
        reason: str = "",
        *,
        silent: bool = False,
        emit_cancelled: bool = True,
    ) -> None:
        """强制停止队列线程并将未完成任务标记为已取消."""
        self._pause_settle_timer.stop()
        self._cancel_watch_timer.stop()
        if self._queue_controller:
            self._queue_controller.stop()
        self._is_cancelling = False
        for tid, t in list(self._tasks.items()):
            if t.status in (TaskStatus.PENDING, TaskStatus.PROCESSING):
                t.mark_cancelled()
                if self._task_list_widget:
                    self._task_list_widget.update_task_status(tid, TaskStatus.CANCELLED)
        if silent:
            self._set_run_state(ProcessingRunState.IDLE, status_message="就绪")
        else:
            tip = "后台已强制结束"
            if reason:
                tip = f"{tip}：{reason}"
            self._set_run_state(ProcessingRunState.IDLE, status_message="已强制结束")
            self.show_warning("处理已终止", tip)
        if emit_cancelled:
            self.process_cancelled.emit()

    def _update_actions_state(self) -> None:
        """更新操作按钮状态."""
        has_queue = self._queue_count > 0
        st = self._run_state
        idle_like = st == ProcessingRunState.IDLE

        if self._action_start:
            self._action_start.setEnabled(has_queue and idle_like)

        if self._action_pause:
            if st in (
                ProcessingRunState.PROCESSING,
                ProcessingRunState.PAUSING,
                ProcessingRunState.PAUSED,
            ):
                self._action_pause.setEnabled(True)
                self._action_pause.setText(
                    "继续"
                    if st in (ProcessingRunState.PAUSING, ProcessingRunState.PAUSED)
                    else "暂停"
                )
            else:
                self._action_pause.setEnabled(False)
                self._action_pause.setText("暂停")

        if self._action_cancel:
            self._action_cancel.setEnabled(
                st
                in (
                    ProcessingRunState.PROCESSING,
                    ProcessingRunState.PAUSING,
                    ProcessingRunState.PAUSED,
                )
            )

        if self._action_clear:
            self._action_clear.setEnabled(
                has_queue and (idle_like or st == ProcessingRunState.CANCELLING)
            )

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
        config_manager = get_config()
        max_queue_size = config_manager.settings.max_queue_size
        self._queue_count = min(count, max_queue_size)
        if self._queue_label:
            self._queue_label.setText(f"队列: {self._queue_count}/{max_queue_size}")

        # 更新工具栏进度的任务数
        if self._toolbar_progress:
            self._toolbar_progress.set_total_tasks(self._queue_count)
        
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

        供测试与少量内部路径使用；常规流程由 _set_run_state 驱动。

        Args:
            is_processing: 是否正在处理
            is_paused: 是否已暂停
        """
        if not is_processing:
            self._pause_settle_timer.stop()
            self._cancel_watch_timer.stop()
            self._set_run_state(ProcessingRunState.IDLE)
            return

        self._is_cancelling = False
        self._cancel_watch_timer.stop()
        if is_paused:
            self._pause_settle_timer.stop()
            self._set_run_state(ProcessingRunState.PAUSED)
        else:
            self._pause_settle_timer.stop()
            self._set_run_state(ProcessingRunState.PROCESSING)

    def show_status_message(self, message: str, timeout: int = 3000) -> None:
        """在状态栏显示临时消息.

        Args:
            message: 消息内容
            timeout: 显示时长(毫秒)，0表示永久
        """
        if self._statusbar:
            self._statusbar.showMessage(message, timeout)

    def show_success(self, title: str, message: str = "") -> None:
        """显示成功通知.

        Args:
            title: 标题
            message: 消息内容
        """
        if self._toast_manager:
            self._toast_manager.show_success(title, message)

    def show_warning(self, title: str, message: str = "") -> None:
        """显示警告通知.

        Args:
            title: 标题
            message: 消息内容
        """
        if self._toast_manager:
            self._toast_manager.show_warning(title, message)

    def show_error_toast(self, title: str, message: str = "") -> None:
        """显示错误通知.

        Args:
            title: 标题
            message: 消息内容
        """
        if self._toast_manager:
            self._toast_manager.show_error(title, message)

    def show_info(self, title: str, message: str = "") -> None:
        """显示信息通知.

        Args:
            title: 标题
            message: 消息内容
        """
        if self._toast_manager:
            self._toast_manager.show_info(title, message)

    def handle_exception(self, exception: Exception, show_dialog: bool = False) -> None:
        """统一处理异常.

        将异常转换为用户友好的错误消息并显示。

        Args:
            exception: 异常对象
            show_dialog: 是否显示对话框（严重错误时使用）
        """
        # 记录日志
        logger.exception(f"发生异常: {exception}")

        # 转换为用户友好的错误
        user_error = get_user_friendly_error(exception, include_details=True)

        if show_dialog:
            # 显示错误对话框
            QMessageBox.critical(
                self,
                user_error.title,
                f"{user_error.message}\n\n💡 建议: {user_error.suggestion}",
            )
        else:
            # 显示 Toast 通知
            if self._toast_manager:
                self._toast_manager.show_user_error(user_error)

    def handle_user_error(self, error: UserFriendlyError, show_dialog: bool = False) -> None:
        """显示用户友好的错误.

        Args:
            error: UserFriendlyError 对象
            show_dialog: 是否显示对话框
        """
        if show_dialog:
            QMessageBox.critical(
                self,
                error.title,
                f"{error.message}\n\n💡 建议: {error.suggestion}",
            )
        else:
            if self._toast_manager:
                self._toast_manager.show_user_error(error)

    # ========================
    # 槽函数
    # ========================

    def _on_start_process(self) -> None:
        """开始处理."""
        if self._queue_count == 0:
            QMessageBox.information(self, "提示", "队列为空，请先导入图片。")
            return

        if not self._queue_controller:
            logger.error("队列控制器未初始化")
            return

        # 过滤掉已结束的任务（完成/失败/取消），只处理待处理的任务
        pending_tasks = {
            task_id: task
            for task_id, task in self._tasks.items()
            if not task.is_finished
        }
        
        if not pending_tasks:
            QMessageBox.information(self, "提示", "所有任务已完成，请添加新任务。")
            return
        
        logger.info(f"开始处理，总任务: {len(self._tasks)}, 待处理: {len(pending_tasks)}")
        self._start_processing_tasks(pending_tasks, "正在处理...")

    def _on_pause_process(self) -> None:
        """暂停/继续处理."""
        if not self._queue_controller:
            return

        if self._run_state == ProcessingRunState.PAUSED:
            self._pause_settle_timer.stop()
            self._queue_controller.resume()
            self._set_run_state(
                ProcessingRunState.PROCESSING,
                status_message="正在处理...",
            )
            self.process_started.emit()  # 复用开始信号
            logger.info("继续处理")
        elif self._run_state == ProcessingRunState.PROCESSING:
            self._queue_controller.pause()
            self._run_state = ProcessingRunState.PAUSING
            self._is_processing = True
            self._is_paused = False
            if self._toolbar_progress:
                self._toolbar_progress.set_processing_state(True, False, "pausing")
            self._update_actions_state()
            self.update_progress(
                self._current_progress,
                "暂停中（当前步骤完成后将暂停）",
            )
            self._pause_settle_timer.start()
            self.process_paused.emit()
            logger.info("请求暂停（协作式）")
        elif self._run_state == ProcessingRunState.PAUSING:
            # 用户在“暂停中”时点继续，撤销暂停请求
            self._pause_settle_timer.stop()
            self._queue_controller.resume()
            self._set_run_state(
                ProcessingRunState.PROCESSING,
                status_message="正在处理...",
            )
            logger.info("暂停中取消暂停请求，继续处理")
        else:
            logger.debug("忽略暂停：当前状态 %s", self._run_state)

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
            if self._queue_controller:
                self._queue_controller.cancel()
            self._is_cancelling = True
            self._pause_settle_timer.stop()
            self._set_run_state(
                ProcessingRunState.CANCELLING,
                status_message="取消中（当前步骤完成后将停止）",
            )
            self._cancel_watch_timer.start(30_000)
            self.show_status_message("正在取消任务，请稍候...")
            logger.info("取消处理中任务")

    def _on_clear_queue(self) -> None:
        """清空队列."""
        if self._queue_count == 0:
            return

        extra = ""
        if self._run_state == ProcessingRunState.CANCELLING:
            extra = "\n\n将强制终止后台处理并清空队列。"
        reply = QMessageBox.question(
            self,
            "确认清空",
            f"确定要清空队列中的 {self._queue_count} 个任务吗？{extra}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            if self._run_state == ProcessingRunState.CANCELLING:
                self._force_stop_processing(
                    reason="清空队列",
                    silent=True,
                    emit_cancelled=False,
                )
            # 清空任务
            self._tasks.clear()
            self._selected_task_id = None

            # 清空列表
            if self._task_list_widget:
                self._task_list_widget.clear_all()

            # 清空预览
            if self._image_preview:
                self._image_preview.clear()

            # 更新上传面板
            if self._image_upload_panel:
                self._image_upload_panel.set_queue_count(0)

            # 重置工具栏进度
            if self._toolbar_progress:
                self._toolbar_progress.reset()

            self.queue_cleared.emit()
            self.update_queue_count(0)
            self.show_status_message("队列已清空")
            logger.info("清空队列")

    def _on_task_added(self, image_paths: list) -> None:
        """处理任务添加.

        Args:
            image_paths: 图片路径列表（1-3张）
        """
        # 从配置中获取最大队列大小
        config_manager = get_config()
        max_queue_size = config_manager.settings.max_queue_size

        # 检查队列是否已满
        if self._queue_count >= max_queue_size:
            QMessageBox.warning(
                self,
                "队列已满",
                f"队列最多支持 {max_queue_size} 个任务。\n请等待处理完成或清空队列。",
            )
            return

        # 创建任务
        task = ImageTask(image_paths=image_paths)

        # 保存任务
        self._tasks[task.id] = task

        # 添加到列表
        if self._task_list_widget:
            self._task_list_widget.add_task(task)

        # 更新队列计数
        self.update_queue_count(len(self._tasks))

        # 更新上传面板的队列计数
        if self._image_upload_panel:
            self._image_upload_panel.set_queue_count(len(self._tasks))

        # 发送信号
        self.images_imported.emit(image_paths)

        # 状态提示
        image_count = task.image_count
        if image_count == 1:
            self.show_status_message(f"已添加单图任务: {task.first_image_filename}")
            logger.info(f"添加单图任务: {task.id}")
        else:
            self.show_status_message(f"已添加{image_count}图合成任务: {task.first_image_filename}")
            logger.info(f"添加{image_count}图合成任务: {task.id}")

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

        # 更新上传面板的队列计数
        if self._image_upload_panel:
            self._image_upload_panel.set_queue_count(len(self._tasks))

        self.show_status_message("已删除任务")

    def _on_task_retry(self, task_id: str) -> None:
        """处理任务重试.

        Args:
            task_id: 任务 ID
        """
        if self._is_processing:
            self.show_warning("请稍候", "当前正在处理任务，请完成或取消后再重试。")
            return

        # 重置任务状态
        if task_id in self._tasks:
            task = self._tasks[task_id]
            task.status = TaskStatus.PENDING
            task.error_message = None
            task.output_path = None
            task.progress = 0

            # 更新任务列表显示
            if self._task_list_widget:
                self._task_list_widget.update_task_status(task_id, TaskStatus.PENDING)

            self.show_status_message(f"正在重试: {task.first_image_filename}")
            logger.info(f"手动重试任务: {task_id}")
            self._start_processing_tasks({task_id: task}, "正在重试任务...")
        else:
            logger.warning(f"任务不存在: {task_id}")

    # ========================
    # 队列控制器回调
    # ========================

    def _on_queue_task_started(self, task_id: str) -> None:
        """队列任务开始处理回调.

        Args:
            task_id: 任务 ID
        """
        # 更新任务状态
        if task_id in self._tasks:
            self._tasks[task_id].status = TaskStatus.PROCESSING
            logger.info(f"任务开始处理: {task_id}")

        # 更新任务列表显示
        if self._task_list_widget:
            self._task_list_widget.update_task_status(task_id, TaskStatus.PROCESSING)

    def _on_queue_task_progress(self, task_id: str, progress: int) -> None:
        """队列任务进度更新回调.

        Args:
            task_id: 任务 ID
            progress: 进度 (0-100)
        """
        if self._run_state == ProcessingRunState.PAUSED:
            return
        # 更新任务进度
        if task_id in self._tasks:
            self._tasks[task_id].progress = progress

        # 更新任务列表显示
        if self._task_list_widget:
            self._task_list_widget.update_task_progress(task_id, progress)

    def _on_queue_progress(self, progress: int, message: str) -> None:
        """队列进度更新回调.

        Args:
            progress: 进度百分比 (0-100)
            message: 状态消息
        """
        if self._run_state == ProcessingRunState.PAUSED:
            return
        self._current_progress = progress
        self.update_progress(progress, self._decorate_progress_message(message))

    def _on_queue_task_completed(self, task_id: str, output_path: str) -> None:
        """队列任务完成回调.

        Args:
            task_id: 任务 ID
            output_path: 输出文件路径
        """
        logger.info(f"_on_queue_task_completed called: task_id={task_id}, output_path={output_path}")
        
        # 更新任务状态
        if task_id in self._tasks:
            self._tasks[task_id].status = TaskStatus.COMPLETED
            self._tasks[task_id].output_path = output_path
            logger.info(f"Updated task {task_id} status to COMPLETED")
        else:
            logger.warning(f"Task {task_id} not found in self._tasks")

        # 更新任务列表显示
        if self._task_list_widget:
            self._task_list_widget.update_task_status(task_id, TaskStatus.COMPLETED)

        # 更新工具栏进度
        if self._toolbar_progress:
            self._toolbar_progress.increment_completed()

        # 如果是当前选中的任务，更新预览显示结果图
        if self._selected_task_id == task_id and self._image_preview and output_path:
            self._image_preview.set_result_image(output_path)

        logger.info(f"任务完成: {task_id} -> {output_path}")

    def _on_queue_task_failed(self, task_id: str, error: str) -> None:
        """队列任务失败回调.

        Args:
            task_id: 任务 ID
            error: 错误信息
        """
        # 更新任务状态
        if task_id in self._tasks:
            self._tasks[task_id].status = TaskStatus.FAILED
            self._tasks[task_id].error_message = error

        # 更新任务列表显示
        if self._task_list_widget:
            self._task_list_widget.update_task_status(task_id, TaskStatus.FAILED)

        # 显示错误通知
        self.show_error_toast("任务失败", error)

        logger.error(f"任务失败: {task_id} - {error}")

    def _on_queue_task_cancelled(self, task_id: str) -> None:
        """队列任务取消回调."""
        if task_id in self._tasks:
            self._tasks[task_id].status = TaskStatus.CANCELLED
            self._tasks[task_id].error_message = None

        if self._task_list_widget:
            self._task_list_widget.update_task_status(task_id, TaskStatus.CANCELLED)

        logger.info(f"任务已取消: {task_id}")

    def _on_queue_completed(self, stats: QueueStats) -> None:
        """队列处理完成回调.

        Args:
            stats: 队列统计信息
        """
        logger.info(f"_on_queue_completed called: stats={stats}")
        was_cancelling = self._is_cancelling
        self._pause_settle_timer.stop()
        self._cancel_watch_timer.stop()
        self.set_processing_state(False)
        
        # 显示完成消息
        success_count = stats.completed
        failed_count = stats.failed
        total = stats.total
        
        if was_cancelling:
            # 同步刷新取消状态，避免未触发单任务回调时 UI 仍显示旧状态
            if self._task_list_widget:
                for task_id, task in self._tasks.items():
                    if task.status == TaskStatus.CANCELLED:
                        self._task_list_widget.update_task_status(task_id, TaskStatus.CANCELLED)
            self.process_cancelled.emit()
            self.show_info(
                "处理已取消",
                f"已完成 {success_count}/{total} 个，取消 {stats.cancelled} 个"
            )
            self.update_progress(0, "已取消")
        elif failed_count == 0:
            self.show_success(
                "处理完成",
                f"成功处理 {success_count}/{total} 个任务"
            )
        else:
            self.show_warning(
                "处理完成",
                f"完成 {success_count}/{total} 个，失败 {failed_count} 个"
            )

        if not was_cancelling:
            self.update_progress(100, f"已完成: {success_count}/{total}")
        logger.info(f"队列处理完成: 成功 {success_count}, 失败 {failed_count}")

    def _on_queue_error(self, exception: Exception) -> None:
        """队列错误回调.

        Args:
            exception: 异常对象
        """
        self.set_processing_state(False)
        self.handle_exception(exception, show_dialog=True)
        logger.exception(f"队列处理错误: {exception}")

    def _start_processing_tasks(
        self,
        tasks: dict[str, ImageTask],
        status_message: str,
    ) -> None:
        """启动指定任务集合的处理流程."""
        if not self._queue_controller:
            logger.error("队列控制器未初始化")
            return

        current_config = self._collect_current_config()
        if not self._ensure_ai_service_available(tasks, current_config):
            self.show_status_message("AI服务不可用，请检查设置后重试")
            logger.warning("AI 服务不可用，已阻止启动需要 AI 的任务")
            return

        for task in tasks.values():
            task.config = current_config

        config_manager = get_config()
        concurrent_limit = config_manager.settings.concurrent_limit
        if len(tasks) == 1:
            concurrent_limit = 1

        self._queue_controller.set_tasks(tasks)
        self._queue_controller.set_concurrent_limit(concurrent_limit)
        self._queue_controller.start()

        self._is_cancelling = False
        self._pause_settle_timer.stop()
        self._cancel_watch_timer.stop()
        self._set_run_state(
            ProcessingRunState.PROCESSING,
            status_message=status_message,
            reset_progress_to_zero=True,
        )
        self.process_started.emit()
        logger.info(f"开始处理任务集合: {len(tasks)} 个")

    def _on_settings(self) -> None:
        """打开设置对话框."""
        self.settings_requested.emit()
        
        dialog = SettingsDialog(self)
        dialog.settings_changed.connect(self._on_settings_changed)
        dialog.ai_config_changed.connect(self._on_ai_config_changed)
        dialog.exec()
        logger.debug("设置对话框已关闭")

    def _on_settings_changed(self) -> None:
        """设置变更处理."""
        self.show_status_message("设置已更新")
        logger.info("应用设置已变更")

    def _on_ai_config_changed(self, config: APIConfig) -> None:
        """AI 配置变更处理.

        Args:
            config: 新的 API 配置
        """
        # 更新 AI 服务单例的配置
        ai_service = get_ai_service(config=config)
        self.show_status_message("AI 配置已更新")
        logger.info("AI 服务配置已更新")

    def _on_open_template_editor(self) -> None:
        """打开模板编辑器."""
        self._open_template_editor()

    def _open_template_editor(self, template_id: Optional[str] = None) -> None:
        """打开模板编辑器.

        Args:
            template_id: 要编辑的模板 ID，None 表示新建
        """
        editor = TemplateEditorWindow(self)
        # 连接编辑器关闭信号，刷新模板列表
        editor.destroyed.connect(self._on_template_editor_closed)

        # 如果指定了模板 ID，先加载模板
        if template_id:
            from src.services.template_manager import TemplateManager
            manager = TemplateManager()
            template = manager.load_template(template_id)
            if template:
                editor.set_template(template)
                logger.info(f"打开模板编辑器，加载模板: {template.name}")
            else:
                logger.warning(f"无法加载模板: {template_id}")
        else:
            logger.info("打开模板编辑器，新建模板")

        editor.show()

    def _on_template_editor_closed(self) -> None:
        """模板编辑器关闭后刷新模板列表."""
        if self._template_config_panel:
            self._template_config_panel.refresh_templates()
            logger.debug("模板列表已刷新")

    def _on_about(self) -> None:
        """显示关于对话框."""
        self.about_requested.emit()

        dialog = AboutDialog(self)
        dialog.exec()
        logger.debug("关于对话框已关闭")

    # ========================
    # 事件处理
    # ========================

    def closeEvent(self, event: QCloseEvent) -> None:
        """窗口关闭事件."""
        if self._run_state != ProcessingRunState.IDLE:
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

            self._force_stop_processing(
                reason="退出应用",
                silent=True,
                emit_cancelled=True,
            )

        logger.info("主窗口关闭")
        event.accept()
