"""工具栏队列进度组件.

紧凑版队列进度显示，适合放在工具栏中。
"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QWidget,
)

from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class ToolbarQueueProgress(QWidget):
    """工具栏队列进度组件.

    显示紧凑的队列处理进度信息：
    - 状态标签
    - 进度条
    - 统计信息（已完成/总数）
    - 用时
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        
        # 状态
        self._total_tasks = 0
        self._completed_tasks = 0
        self._failed_tasks = 0
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
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(12)

        # 状态标签
        self._status_label = QLabel("就绪")
        self._status_label.setProperty("hint", True)
        self._status_label.setMinimumWidth(60)
        layout.addWidget(self._status_label)

        # 进度条
        self._progress_bar = QProgressBar()
        self._progress_bar.setFixedHeight(16)
        self._progress_bar.setFixedWidth(200)
        self._progress_bar.setTextVisible(False)
        layout.addWidget(self._progress_bar)

        # 统计信息
        self._stats_label = QLabel("0/0")
        self._stats_label.setProperty("hint", True)
        self._stats_label.setMinimumWidth(50)
        layout.addWidget(self._stats_label)

        # 失败数（仅在有失败时显示）
        self._failed_label = QLabel()
        self._failed_label.setProperty("error", True)
        self._failed_label.setVisible(False)
        layout.addWidget(self._failed_label)

        # 用时
        self._time_label = QLabel()
        self._time_label.setProperty("hint", True)
        self._time_label.setMinimumWidth(80)
        layout.addWidget(self._time_label)

    def _update_display(self) -> None:
        """更新显示内容."""
        # 计算整体进度
        if self._total_tasks > 0:
            completed_progress = (self._completed_tasks + self._failed_tasks) * 100 / self._total_tasks
            overall_progress = int(completed_progress)
        else:
            overall_progress = 0

        self._progress_bar.setValue(overall_progress)

        # 更新统计
        self._stats_label.setText(f"{self._completed_tasks}/{self._total_tasks}")
        
        if self._failed_tasks > 0:
            self._failed_label.setText(f"失败: {self._failed_tasks}")
            self._failed_label.setVisible(True)
        else:
            self._failed_label.setVisible(False)

        # 更新状态
        if not self._is_processing:
            if self._total_tasks == 0:
                self._status_label.setText("就绪")
            elif self._completed_tasks + self._failed_tasks >= self._total_tasks:
                self._status_label.setText("已完成")
            else:
                self._status_label.setText("等待")
        else:
            if self._is_paused:
                self._status_label.setText("已暂停")
            else:
                self._status_label.setText("处理中")

        # 更新时间显示
        if self._is_processing and self._elapsed_seconds > 0:
            elapsed_str = self._format_time(self._elapsed_seconds)
            # 预估剩余时间
            if self._completed_tasks > 0:
                avg_time = self._elapsed_seconds / self._completed_tasks
                remaining_tasks = self._total_tasks - self._completed_tasks - self._failed_tasks
                estimated_remaining = int(avg_time * remaining_tasks)
                remaining_str = self._format_time(estimated_remaining)
                self._time_label.setText(f"{elapsed_str} / 剩余 {remaining_str}")
            else:
                self._time_label.setText(elapsed_str)
        elif self._elapsed_seconds > 0 and not self._is_processing:
            elapsed_str = self._format_time(self._elapsed_seconds)
            self._time_label.setText(f"总计 {elapsed_str}")
        else:
            self._time_label.setText("")

    def _format_time(self, seconds: int) -> str:
        """格式化时间显示."""
        if seconds < 60:
            return f"{seconds}秒"
        elif seconds < 3600:
            minutes = seconds // 60
            secs = seconds % 60
            return f"{minutes}:{secs:02d}"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours}:{minutes:02d}:{seconds % 60:02d}"

    def _on_timer_tick(self) -> None:
        """计时器触发."""
        if self._is_processing and not self._is_paused:
            self._elapsed_seconds += 1
            self._update_display()

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
        self._update_display()

    def reset(self) -> None:
        """重置状态."""
        self._total_tasks = 0
        self._completed_tasks = 0
        self._failed_tasks = 0
        self._is_processing = False
        self._is_paused = False
        self._elapsed_seconds = 0
        self._timer.stop()
        self._update_display()

    def increment_completed(self) -> None:
        """增加完成数."""
        self._completed_tasks += 1
        self._update_display()
