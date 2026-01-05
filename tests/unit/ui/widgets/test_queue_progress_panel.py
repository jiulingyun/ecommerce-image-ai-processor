"""QueueProgressPanel 组件单元测试."""

from __future__ import annotations

import pytest
from PyQt6.QtCore import QTimer

from src.ui.widgets.queue_progress_panel import QueueProgressPanel


class TestQueueProgressPanel:
    """QueueProgressPanel 组件测试."""

    def test_init_default(self, qtbot) -> None:
        """测试默认初始化."""
        panel = QueueProgressPanel()
        qtbot.addWidget(panel)

        stats = panel.get_stats()
        assert stats["total"] == 0
        assert stats["completed"] == 0
        assert stats["failed"] == 0
        assert stats["is_processing"] is False
        assert stats["is_paused"] is False

    def test_set_total_tasks(self, qtbot) -> None:
        """测试设置总任务数."""
        panel = QueueProgressPanel()
        qtbot.addWidget(panel)

        panel.set_total_tasks(5)

        stats = panel.get_stats()
        assert stats["total"] == 5

    def test_set_processing_state(self, qtbot) -> None:
        """测试设置处理状态."""
        panel = QueueProgressPanel()
        qtbot.addWidget(panel)

        panel.set_total_tasks(3)
        panel.set_processing_state(True)

        stats = panel.get_stats()
        assert stats["is_processing"] is True
        assert stats["is_paused"] is False

    def test_set_paused_state(self, qtbot) -> None:
        """测试设置暂停状态."""
        panel = QueueProgressPanel()
        qtbot.addWidget(panel)

        panel.set_total_tasks(3)
        panel.set_processing_state(True, is_paused=True)

        stats = panel.get_stats()
        assert stats["is_processing"] is True
        assert stats["is_paused"] is True

    def test_update_task_completed_success(self, qtbot) -> None:
        """测试更新任务完成 - 成功."""
        panel = QueueProgressPanel()
        qtbot.addWidget(panel)

        panel.set_total_tasks(3)
        panel.update_task_completed(success=True)

        stats = panel.get_stats()
        assert stats["completed"] == 1
        assert stats["failed"] == 0

    def test_update_task_completed_failure(self, qtbot) -> None:
        """测试更新任务完成 - 失败."""
        panel = QueueProgressPanel()
        qtbot.addWidget(panel)

        panel.set_total_tasks(3)
        panel.update_task_completed(success=False)

        stats = panel.get_stats()
        assert stats["completed"] == 0
        assert stats["failed"] == 1

    def test_update_current_progress(self, qtbot) -> None:
        """测试更新当前进度."""
        panel = QueueProgressPanel()
        qtbot.addWidget(panel)

        panel.set_total_tasks(2)
        panel.update_current_progress(50)

        # 进度条值应为 50/2 = 25
        assert panel._progress_bar.value() == 25

    def test_reset(self, qtbot) -> None:
        """测试重置."""
        panel = QueueProgressPanel()
        qtbot.addWidget(panel)

        panel.set_total_tasks(5)
        panel.set_processing_state(True)
        panel.update_task_completed(success=True)
        panel.update_task_completed(success=False)

        panel.reset()

        stats = panel.get_stats()
        assert stats["total"] == 0
        assert stats["completed"] == 0
        assert stats["failed"] == 0
        assert stats["is_processing"] is False

    def test_start_signal(self, qtbot) -> None:
        """测试开始信号."""
        panel = QueueProgressPanel()
        qtbot.addWidget(panel)

        panel.set_total_tasks(3)

        with qtbot.waitSignal(panel.start_clicked, timeout=100):
            panel._start_btn.click()

    def test_pause_signal(self, qtbot) -> None:
        """测试暂停信号."""
        panel = QueueProgressPanel()
        qtbot.addWidget(panel)

        panel.set_total_tasks(3)
        panel.set_processing_state(True)

        with qtbot.waitSignal(panel.pause_clicked, timeout=100):
            panel._pause_btn.click()

    def test_cancel_signal(self, qtbot) -> None:
        """测试取消信号."""
        panel = QueueProgressPanel()
        qtbot.addWidget(panel)

        panel.set_total_tasks(3)
        panel.set_processing_state(True)

        with qtbot.waitSignal(panel.cancel_clicked, timeout=100):
            panel._cancel_btn.click()

    def test_button_visibility_idle(self, qtbot) -> None:
        """测试按钮可见性 - 空闲状态."""
        panel = QueueProgressPanel()
        qtbot.addWidget(panel)

        panel.set_total_tasks(3)

        # 使用 isHidden() 来检查，因为 isVisible() 在父组件未显示时总是返回 False
        assert not panel._start_btn.isHidden()
        assert panel._pause_btn.isHidden()
        assert panel._cancel_btn.isHidden()

    def test_button_visibility_processing(self, qtbot) -> None:
        """测试按钮可见性 - 处理中状态."""
        panel = QueueProgressPanel()
        qtbot.addWidget(panel)

        panel.set_total_tasks(3)
        panel.set_processing_state(True)

        assert panel._start_btn.isHidden()
        assert not panel._pause_btn.isHidden()
        assert not panel._cancel_btn.isHidden()

    def test_format_time_seconds(self, qtbot) -> None:
        """测试时间格式化 - 秒."""
        panel = QueueProgressPanel()
        qtbot.addWidget(panel)

        assert panel._format_time(45) == "45秒"

    def test_format_time_minutes(self, qtbot) -> None:
        """测试时间格式化 - 分钟."""
        panel = QueueProgressPanel()
        qtbot.addWidget(panel)

        assert panel._format_time(125) == "2分5秒"

    def test_format_time_hours(self, qtbot) -> None:
        """测试时间格式化 - 小时."""
        panel = QueueProgressPanel()
        qtbot.addWidget(panel)

        assert panel._format_time(3725) == "1时2分"

    def test_progress_calculation(self, qtbot) -> None:
        """测试进度计算."""
        panel = QueueProgressPanel()
        qtbot.addWidget(panel)

        panel.set_total_tasks(4)
        panel.update_task_completed(success=True)  # 1/4 = 25%
        panel.update_task_completed(success=True)  # 2/4 = 50%

        assert panel._progress_bar.value() == 50

    def test_start_button_disabled_when_empty(self, qtbot) -> None:
        """测试队列为空时开始按钮禁用."""
        panel = QueueProgressPanel()
        qtbot.addWidget(panel)

        assert not panel._start_btn.isEnabled()

    def test_start_button_enabled_with_tasks(self, qtbot) -> None:
        """测试有任务时开始按钮启用."""
        panel = QueueProgressPanel()
        qtbot.addWidget(panel)

        panel.set_total_tasks(3)

        assert panel._start_btn.isEnabled()
