"""批量队列模型单元测试."""

from __future__ import annotations

import pytest

from src.models.batch_queue import (
    BatchQueue,
    BatchTask,
    QueueStats,
    QueueStatus,
    MAX_QUEUE_SIZE,
    DEFAULT_CONCURRENT_LIMIT,
)
from src.models.image_task import ImageTask, TaskStatus


# ===================
# QueueStats 测试
# ===================
class TestQueueStats:
    """测试 QueueStats 模型."""

    def test_default_values(self) -> None:
        """测试默认值."""
        stats = QueueStats()
        assert stats.total == 0
        assert stats.pending == 0
        assert stats.processing == 0
        assert stats.completed == 0
        assert stats.failed == 0
        assert stats.cancelled == 0
        assert stats.progress == 0

    def test_finished_property(self) -> None:
        """测试已结束任务计数."""
        stats = QueueStats(
            total=10,
            completed=5,
            failed=2,
            cancelled=1,
        )
        assert stats.finished == 8

    def test_success_rate_zero(self) -> None:
        """测试无完成任务时的成功率."""
        stats = QueueStats(total=5, pending=5)
        assert stats.success_rate == 0.0

    def test_success_rate_calculation(self) -> None:
        """测试成功率计算."""
        stats = QueueStats(
            total=10,
            completed=7,
            failed=3,
        )
        assert stats.success_rate == 70.0

    def test_from_tasks_empty(self) -> None:
        """测试从空任务列表创建."""
        stats = QueueStats.from_tasks([])
        assert stats.total == 0
        assert stats.progress == 0

    def test_from_tasks(self) -> None:
        """测试从任务列表创建."""
        task1 = ImageTask(image_paths=["bg1.jpg", "prod1.png"])
        task2 = ImageTask(image_paths=["bg2.jpg", "prod2.png"])
        task2.mark_completed()

        batch_tasks = [
            BatchTask(queue_position=1, task=task1),
            BatchTask(queue_position=2, task=task2),
        ]

        stats = QueueStats.from_tasks(batch_tasks)
        assert stats.total == 2
        assert stats.pending == 1
        assert stats.completed == 1
        assert stats.progress == 50  # (0 + 100) // 2


# ===================
# BatchTask 测试
# ===================
class TestBatchTask:
    """测试 BatchTask 模型."""

    def test_create_batch_task(self) -> None:
        """测试创建批量任务."""
        task = ImageTask(image_paths=["bg.jpg", "prod.png"])
        batch_task = BatchTask(queue_position=1, task=task)

        assert batch_task.queue_position == 1
        assert batch_task.retry_count == 0
        assert batch_task.max_retries == 3
        assert batch_task.status == TaskStatus.PENDING

    def test_status_property(self) -> None:
        """测试状态属性."""
        task = ImageTask(image_paths=["bg.jpg", "prod.png"])
        batch_task = BatchTask(queue_position=1, task=task)

        assert batch_task.status == TaskStatus.PENDING

        task.mark_processing()
        assert batch_task.status == TaskStatus.PROCESSING

    def test_progress_property(self) -> None:
        """测试进度属性."""
        task = ImageTask(image_paths=["bg.jpg", "prod.png"])
        batch_task = BatchTask(queue_position=1, task=task)

        assert batch_task.progress == 0

        task.update_status(TaskStatus.PROCESSING, progress=50)
        assert batch_task.progress == 50

    def test_can_retry_false_not_failed(self) -> None:
        """测试非失败任务不可重试."""
        task = ImageTask(image_paths=["bg.jpg", "prod.png"])
        batch_task = BatchTask(queue_position=1, task=task)

        assert batch_task.can_retry is False

    def test_can_retry_true(self) -> None:
        """测试失败任务可重试."""
        task = ImageTask(image_paths=["bg.jpg", "prod.png"])
        batch_task = BatchTask(queue_position=1, task=task)
        task.mark_failed("测试错误")

        assert batch_task.can_retry is True

    def test_can_retry_exhausted(self) -> None:
        """测试重试次数用尽."""
        task = ImageTask(image_paths=["bg.jpg", "prod.png"])
        batch_task = BatchTask(queue_position=1, task=task, max_retries=2)

        task.mark_failed("错误1")
        assert batch_task.can_retry is True

        batch_task.increment_retry()
        task.mark_failed("错误2")
        assert batch_task.can_retry is True

        batch_task.increment_retry()
        task.mark_failed("错误3")
        assert batch_task.can_retry is False

    def test_increment_retry(self) -> None:
        """测试增加重试计数."""
        task = ImageTask(image_paths=["bg.jpg", "prod.png"])
        batch_task = BatchTask(queue_position=1, task=task)
        task.mark_failed("测试错误")

        assert batch_task.retry_count == 0
        batch_task.increment_retry()
        assert batch_task.retry_count == 1
        assert batch_task.status == TaskStatus.PENDING


# ===================
# BatchQueue 测试
# ===================
class TestBatchQueue:
    """测试 BatchQueue 模型."""

    def test_create_queue(self) -> None:
        """测试创建队列."""
        queue = BatchQueue()

        assert queue.status == QueueStatus.IDLE
        assert queue.is_empty is True
        assert queue.is_full is False
        assert queue.size == 0
        assert queue.concurrent_limit == DEFAULT_CONCURRENT_LIMIT

    def test_add_task(self) -> None:
        """测试添加任务."""
        queue = BatchQueue()
        batch_task = queue.add_task(
            image_paths=["bg.jpg", "prod.png"],
        )

        assert queue.size == 1
        assert batch_task.queue_position == 1

    def test_add_multiple_tasks(self) -> None:
        """测试添加多个任务."""
        queue = BatchQueue()

        for i in range(5):
            queue.add_task(
                image_paths=[f"bg{i}.jpg", f"prod{i}.png"],
            )

        assert queue.size == 5
        assert queue.remaining_capacity == MAX_QUEUE_SIZE - 5

    def test_add_task_queue_full(self) -> None:
        """测试队列已满时添加任务."""
        queue = BatchQueue()

        for i in range(MAX_QUEUE_SIZE):
            queue.add_task(
                image_paths=[f"bg{i}.jpg", f"prod{i}.png"],
            )

        assert queue.is_full is True

        with pytest.raises(ValueError, match="队列已满"):
            queue.add_task(
                image_paths=["bg_extra.jpg", "prod_extra.png"],
            )

    def test_remove_task(self) -> None:
        """测试移除任务."""
        queue = BatchQueue()
        task1 = queue.add_task(image_paths=["bg1.jpg", "prod1.png"])
        task2 = queue.add_task(image_paths=["bg2.jpg", "prod2.png"])

        removed = queue.remove_task(task1.id)

        assert removed is not None
        assert removed.id == task1.id
        assert queue.size == 1
        # 检查位置重新分配
        assert queue.tasks[0].queue_position == 1

    def test_remove_nonexistent_task(self) -> None:
        """测试移除不存在的任务."""
        queue = BatchQueue()
        queue.add_task(image_paths=["bg.jpg", "prod.png"])

        removed = queue.remove_task("nonexistent-id")
        assert removed is None

    def test_get_task(self) -> None:
        """测试获取任务."""
        queue = BatchQueue()
        task = queue.add_task(image_paths=["bg.jpg", "prod.png"])

        found = queue.get_task(task.id)
        assert found is not None
        assert found.id == task.id

    def test_get_pending_tasks(self) -> None:
        """测试获取待处理任务."""
        queue = BatchQueue()
        task1 = queue.add_task(image_paths=["bg1.jpg", "prod1.png"])
        task2 = queue.add_task(image_paths=["bg2.jpg", "prod2.png"])
        task2.task.mark_completed()

        pending = queue.get_pending_tasks()
        assert len(pending) == 1
        assert pending[0].id == task1.id

    def test_get_completed_tasks(self) -> None:
        """测试获取已完成任务."""
        queue = BatchQueue()
        task1 = queue.add_task(image_paths=["bg1.jpg", "prod1.png"])
        task2 = queue.add_task(image_paths=["bg2.jpg", "prod2.png"])
        task2.task.mark_completed()

        completed = queue.get_completed_tasks()
        assert len(completed) == 1
        assert completed[0].id == task2.id

    def test_get_failed_tasks(self) -> None:
        """测试获取失败任务."""
        queue = BatchQueue()
        task = queue.add_task(image_paths=["bg.jpg", "prod.png"])
        task.task.mark_failed("测试错误")

        failed = queue.get_failed_tasks()
        assert len(failed) == 1

    def test_get_retryable_tasks(self) -> None:
        """测试获取可重试任务."""
        queue = BatchQueue()
        task = queue.add_task(image_paths=["bg.jpg", "prod.png"])
        task.task.mark_failed("测试错误")

        retryable = queue.get_retryable_tasks()
        assert len(retryable) == 1

    def test_get_stats(self) -> None:
        """测试获取统计信息."""
        queue = BatchQueue()
        queue.add_task(image_paths=["bg1.jpg", "prod1.png"])
        task2 = queue.add_task(image_paths=["bg2.jpg", "prod2.png"])
        task2.task.mark_completed()

        stats = queue.get_stats()
        assert stats.total == 2
        assert stats.pending == 1
        assert stats.completed == 1

    def test_clear(self) -> None:
        """测试清空队列."""
        queue = BatchQueue()
        queue.add_task(image_paths=["bg1.jpg", "prod1.png"])
        queue.add_task(image_paths=["bg2.jpg", "prod2.png"])
        queue.start()

        queue.clear()

        assert queue.is_empty is True
        assert queue.status == QueueStatus.IDLE

    def test_start(self) -> None:
        """测试开始处理."""
        queue = BatchQueue()
        queue.add_task(image_paths=["bg.jpg", "prod.png"])

        queue.start()

        assert queue.status == QueueStatus.PROCESSING
        assert queue.started_at is not None

    def test_start_empty_queue(self) -> None:
        """测试空队列开始处理."""
        queue = BatchQueue()

        with pytest.raises(ValueError, match="队列为空"):
            queue.start()

    def test_pause_resume(self) -> None:
        """测试暂停和恢复."""
        queue = BatchQueue()
        queue.add_task(image_paths=["bg.jpg", "prod.png"])
        queue.start()

        queue.pause()
        assert queue.status == QueueStatus.PAUSED

        queue.resume()
        assert queue.status == QueueStatus.PROCESSING

    def test_cancel(self) -> None:
        """测试取消处理."""
        queue = BatchQueue()
        task = queue.add_task(image_paths=["bg.jpg", "prod.png"])
        queue.start()

        queue.cancel()

        assert queue.status == QueueStatus.CANCELLED
        assert task.status == TaskStatus.CANCELLED

    def test_mark_completed(self) -> None:
        """测试标记完成."""
        queue = BatchQueue()
        queue.add_task(image_paths=["bg.jpg", "prod.png"])
        queue.start()

        queue.mark_completed()

        assert queue.status == QueueStatus.COMPLETED
        assert queue.completed_at is not None

    def test_check_all_finished(self) -> None:
        """测试检查所有任务完成."""
        queue = BatchQueue()
        task1 = queue.add_task(image_paths=["bg1.jpg", "prod1.png"])
        task2 = queue.add_task(image_paths=["bg2.jpg", "prod2.png"])

        assert queue.check_all_finished() is False

        task1.task.mark_completed()
        assert queue.check_all_finished() is False

        task2.task.mark_failed("错误")
        assert queue.check_all_finished() is True

    def test_serialization(self) -> None:
        """测试序列化."""
        queue = BatchQueue()
        queue.add_task(image_paths=["bg.jpg", "prod.png"])

        data = queue.to_dict()

        assert "id" in data
        assert "tasks" in data
        assert "status" in data

        restored = BatchQueue.from_dict(data)
        assert restored.size == queue.size


# ===================
# QueueStatus 测试
# ===================
class TestQueueStatus:
    """测试 QueueStatus 枚举."""

    def test_queue_status_values(self) -> None:
        """测试队列状态枚举值."""
        assert QueueStatus.IDLE.value == "idle"
        assert QueueStatus.PROCESSING.value == "processing"
        assert QueueStatus.PAUSED.value == "paused"
        assert QueueStatus.COMPLETED.value == "completed"
        assert QueueStatus.CANCELLED.value == "cancelled"
