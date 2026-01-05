"""队列进度面板组件.

显示处理队列的整体进度、状态统计和实时反馈。
"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.models.image_task import TaskStatus
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class QueueProgressPanel(QFrame):
    """队列进度面板.

    显示处理队列的整体进度信息，包括：
    - 总体进度条
    - 已完成/总数统计
    - 当前处理状态
    - 预估剩余时间

    Signals:
        start_clicked: 开始处理按钮点击
        pause_clicked: 暂停按钮点击
        cancel_clicked: 取消按钮点击
    """

    start_clicked = pyqtSignal()
    pause_clicked = pyqtSignal()
    cancel_clicked = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        
        # 状态
        self._total_tasks = 0
        self._completed_tasks = 0
        self._failed_tasks = 0
        self._current_task_progress = 0
        self._is_processing = False
        self._is_paused = False
        self._elapsed_seconds = 0
        
        # 计时器
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_timer_tick)
        
        self._setup_ui()
        self._update_display()

    def _setup_ui(self) -> None:
        """设置 UI."""
        self.setProperty("card", True)
        self.setStyleSheet("""
            QueueProgressPanel[card="true"] {
                background-color: #fafafa;
                border: 1px solid #e8e8e8;
                border-radius: 8px;
                padding: 12px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # 第一行：标题和状态
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)

        self._title_label = QLabel("处理进度")
        self._title_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #333;")
        header_layout.addWidget(self._title_label)

        header_layout.addStretch()

        self._status_label = QLabel("就绪")
        self._status_label.setStyleSheet("font-size: 12px; color: #666;")
        header_layout.addWidget(self._status_label)

        layout.addLayout(header_layout)

        # 第二行：进度条
        self._progress_bar = QProgressBar()
        self._progress_bar.setFixedHeight(8)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #e8e8e8;
                border: none;
                border-radius: 4px;
            }
            QProgressBar::chunk {
                background-color: #1890ff;
                border-radius: 4px;
            }
        """)
        layout.addWidget(self._progress_bar)

        # 第三行：统计信息
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(16)

        # 完成数
        self._completed_label = QLabel("已完成: 0/0")
        self._completed_label.setStyleSheet("font-size: 12px; color: #52c41a;")
        stats_layout.addWidget(self._completed_label)

        # 失败数
        self._failed_label = QLabel("失败: 0")
        self._failed_label.setStyleSheet("font-size: 12px; color: #ff4d4f;")
        stats_layout.addWidget(self._failed_label)

        stats_layout.addStretch()

        # 用时/预估
        self._time_label = QLabel("")
        self._time_label.setStyleSheet("font-size: 12px; color: #999;")
        stats_layout.addWidget(self._time_label)

        layout.addLayout(stats_layout)

        # 第四行：操作按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self._start_btn = QPushButton("开始处理")
        self._start_btn.setProperty("primary", True)
        self._start_btn.setFixedHeight(32)
        self._start_btn.clicked.connect(self._on_start_clicked)
        btn_layout.addWidget(self._start_btn)

        self._pause_btn = QPushButton("暂停")
        self._pause_btn.setProperty("secondary", True)
        self._pause_btn.setFixedHeight(32)
        self._pause_btn.setVisible(False)
        self._pause_btn.clicked.connect(self._on_pause_clicked)
        btn_layout.addWidget(self._pause_btn)

        self._cancel_btn = QPushButton("取消")
        self._cancel_btn.setProperty("danger", True)
        self._cancel_btn.setFixedHeight(32)
        self._cancel_btn.setVisible(False)
        self._cancel_btn.clicked.connect(self._on_cancel_clicked)
        btn_layout.addWidget(self._cancel_btn)

        btn_layout.addStretch()

        layout.addLayout(btn_layout)

    def _update_display(self) -> None:
        """更新显示内容."""
        # 计算整体进度
        if self._total_tasks > 0:
            # 每个完成任务占 100/总数 的进度
            completed_progress = (self._completed_tasks + self._failed_tasks) * 100 / self._total_tasks
            # 当前任务进度贡献
            current_contribution = self._current_task_progress / self._total_tasks
            overall_progress = int(completed_progress + current_contribution)
        else:
            overall_progress = 0

        self._progress_bar.setValue(overall_progress)

        # 更新统计
        self._completed_label.setText(f"已完成: {self._completed_tasks}/{self._total_tasks}")
        
        if self._failed_tasks > 0:
            self._failed_label.setText(f"失败: {self._failed_tasks}")
            self._failed_label.setVisible(True)
        else:
            self._failed_label.setVisible(False)

        # 更新状态
        if not self._is_processing:
            if self._total_tasks == 0:
                self._status_label.setText("就绪")
                self._status_label.setStyleSheet("font-size: 12px; color: #666;")
            elif self._completed_tasks + self._failed_tasks >= self._total_tasks:
                self._status_label.setText("已完成")
                self._status_label.setStyleSheet("font-size: 12px; color: #52c41a;")
            else:
                self._status_label.setText("等待开始")
                self._status_label.setStyleSheet("font-size: 12px; color: #faad14;")
        else:
            if self._is_paused:
                self._status_label.setText("已暂停")
                self._status_label.setStyleSheet("font-size: 12px; color: #faad14;")
            else:
                self._status_label.setText("处理中...")
                self._status_label.setStyleSheet("font-size: 12px; color: #1890ff;")

        # 更新时间显示
        if self._is_processing and self._elapsed_seconds > 0:
            elapsed_str = self._format_time(self._elapsed_seconds)
            # 预估剩余时间
            if self._completed_tasks > 0:
                avg_time = self._elapsed_seconds / self._completed_tasks
                remaining_tasks = self._total_tasks - self._completed_tasks - self._failed_tasks
                estimated_remaining = int(avg_time * remaining_tasks)
                remaining_str = self._format_time(estimated_remaining)
                self._time_label.setText(f"用时: {elapsed_str} | 预计剩余: {remaining_str}")
            else:
                self._time_label.setText(f"用时: {elapsed_str}")
        elif self._elapsed_seconds > 0 and not self._is_processing:
            elapsed_str = self._format_time(self._elapsed_seconds)
            self._time_label.setText(f"总用时: {elapsed_str}")
        else:
            self._time_label.setText("")

        # 更新按钮状态
        self._update_buttons()

    def _update_buttons(self) -> None:
        """更新按钮状态."""
        has_tasks = self._total_tasks > 0
        all_done = self._completed_tasks + self._failed_tasks >= self._total_tasks

        if self._is_processing:
            self._start_btn.setVisible(False)
            self._pause_btn.setVisible(True)
            self._cancel_btn.setVisible(True)
            
            if self._is_paused:
                self._pause_btn.setText("继续")
            else:
                self._pause_btn.setText("暂停")
        else:
            self._start_btn.setVisible(True)
            self._pause_btn.setVisible(False)
            self._cancel_btn.setVisible(False)
            
            self._start_btn.setEnabled(has_tasks and not all_done)

    def _format_time(self, seconds: int) -> str:
        """格式化时间显示."""
        if seconds < 60:
            return f"{seconds}秒"
        elif seconds < 3600:
            minutes = seconds // 60
            secs = seconds % 60
            return f"{minutes}分{secs}秒"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours}时{minutes}分"

    def _on_timer_tick(self) -> None:
        """计时器触发."""
        if self._is_processing and not self._is_paused:
            self._elapsed_seconds += 1
            self._update_display()

    def _on_start_clicked(self) -> None:
        """开始按钮点击."""
        self.start_clicked.emit()

    def _on_pause_clicked(self) -> None:
        """暂停按钮点击."""
        self.pause_clicked.emit()

    def _on_cancel_clicked(self) -> None:
        """取消按钮点击."""
        self.cancel_clicked.emit()

    # ========================
    # 公共方法
    # ========================

    def set_total_tasks(self, count: int) -> None:
        """设置总任务数.

        Args:
            count: 任务总数
        """
        self._total_tasks = count
        self._update_display()

    def set_processing_state(self, is_processing: bool, is_paused: bool = False) -> None:
        """设置处理状态.

        Args:
            is_processing: 是否正在处理
            is_paused: 是否已暂停
        """
        was_processing = self._is_processing
        self._is_processing = is_processing
        self._is_paused = is_paused

        if is_processing and not was_processing:
            # 开始处理
            self._elapsed_seconds = 0
            self._timer.start(1000)
        elif not is_processing and was_processing:
            # 停止处理
            self._timer.stop()
        elif is_processing and is_paused:
            # 暂停
            self._timer.stop()
        elif is_processing and not is_paused and was_processing:
            # 继续
            self._timer.start(1000)

        self._update_display()

    def update_task_completed(self, success: bool = True) -> None:
        """更新任务完成状态.

        Args:
            success: 是否成功完成
        """
        if success:
            self._completed_tasks += 1
        else:
            self._failed_tasks += 1
        self._current_task_progress = 0
        self._update_display()

    def update_current_progress(self, progress: int) -> None:
        """更新当前任务进度.

        Args:
            progress: 进度值 (0-100)
        """
        self._current_task_progress = max(0, min(100, progress))
        self._update_display()

    def reset(self) -> None:
        """重置状态."""
        self._total_tasks = 0
        self._completed_tasks = 0
        self._failed_tasks = 0
        self._current_task_progress = 0
        self._is_processing = False
        self._is_paused = False
        self._elapsed_seconds = 0
        self._timer.stop()
        self._update_display()

    def get_stats(self) -> dict:
        """获取统计信息.

        Returns:
            统计信息字典
        """
        return {
            "total": self._total_tasks,
            "completed": self._completed_tasks,
            "failed": self._failed_tasks,
            "elapsed_seconds": self._elapsed_seconds,
            "is_processing": self._is_processing,
            "is_paused": self._is_paused,
        }
