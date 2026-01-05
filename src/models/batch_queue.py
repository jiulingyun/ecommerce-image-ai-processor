"""批量处理队列模型.

提供批量图片处理的队列管理模型，支持最多10张图片的队列处理。

Features:
    - 队列任务管理
    - 处理进度追踪
    - 结果统计
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Callable, Optional

from pydantic import BaseModel, Field, field_validator

from src.models.image_task import ImageTask, TaskStatus
from src.models.process_config import ProcessConfig


# 常量
MAX_QUEUE_SIZE = 10  # 最大队列大小
DEFAULT_CONCURRENT_LIMIT = 3  # 默认并发数


class QueueStatus(str, Enum):
    """队列状态枚举."""

    IDLE = "idle"  # 空闲
    PROCESSING = "processing"  # 处理中
    PAUSED = "paused"  # 已暂停
    COMPLETED = "completed"  # 已完成
    CANCELLED = "cancelled"  # 已取消


class BatchTask(BaseModel):
    """批量处理任务.

    表示队列中的一个处理任务，基于 ImageTask 扩展队列相关信息。

    Attributes:
        id: 任务 ID
        queue_position: 队列位置（从 1 开始）
        task: 底层图片处理任务
        retry_count: 重试次数
        max_retries: 最大重试次数
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    queue_position: int = Field(ge=1, le=MAX_QUEUE_SIZE, description="队列位置")
    task: ImageTask = Field(..., description="图片处理任务")
    retry_count: int = Field(default=0, ge=0, description="已重试次数")
    max_retries: int = Field(default=3, ge=0, le=5, description="最大重试次数")
    added_at: datetime = Field(default_factory=datetime.utcnow)

    @property
    def status(self) -> TaskStatus:
        """获取任务状态."""
        return self.task.status

    @property
    def progress(self) -> int:
        """获取任务进度."""
        return self.task.progress

    @property
    def can_retry(self) -> bool:
        """是否可以重试."""
        return self.task.is_failed and self.retry_count < self.max_retries

    def increment_retry(self) -> None:
        """增加重试计数."""
        self.retry_count += 1
        self.task.update_status(TaskStatus.PENDING, progress=0)


class QueueStats(BaseModel):
    """队列统计信息.

    提供队列处理的实时统计数据。

    Attributes:
        total: 总任务数
        pending: 待处理数
        processing: 处理中数
        completed: 已完成数
        failed: 失败数
        cancelled: 已取消数
        progress: 总体进度 (0-100)
    """

    total: int = Field(default=0, ge=0)
    pending: int = Field(default=0, ge=0)
    processing: int = Field(default=0, ge=0)
    completed: int = Field(default=0, ge=0)
    failed: int = Field(default=0, ge=0)
    cancelled: int = Field(default=0, ge=0)
    progress: int = Field(default=0, ge=0, le=100)

    @property
    def finished(self) -> int:
        """已结束的任务数（完成 + 失败 + 取消）."""
        return self.completed + self.failed + self.cancelled

    @property
    def success_rate(self) -> float:
        """成功率."""
        if self.finished == 0:
            return 0.0
        return self.completed / self.finished * 100

    @classmethod
    def from_tasks(cls, tasks: list[BatchTask]) -> "QueueStats":
        """从任务列表创建统计信息."""
        total = len(tasks)
        pending = sum(1 for t in tasks if t.status == TaskStatus.PENDING)
        processing = sum(1 for t in tasks if t.status == TaskStatus.PROCESSING)
        completed = sum(1 for t in tasks if t.status == TaskStatus.COMPLETED)
        failed = sum(1 for t in tasks if t.status == TaskStatus.FAILED)
        cancelled = sum(1 for t in tasks if t.status == TaskStatus.CANCELLED)

        # 计算总体进度
        if total == 0:
            progress = 0
        else:
            total_progress = sum(t.progress for t in tasks)
            progress = total_progress // total

        return cls(
            total=total,
            pending=pending,
            processing=processing,
            completed=completed,
            failed=failed,
            cancelled=cancelled,
            progress=progress,
        )


class BatchQueue(BaseModel):
    """批量处理队列.

    管理批量图片处理任务的队列，支持最多 10 张图片。

    Attributes:
        id: 队列 ID
        tasks: 任务列表
        status: 队列状态
        config: 全局处理配置
        concurrent_limit: 并发限制
        created_at: 创建时间
        started_at: 开始时间
        completed_at: 完成时间

    Example:
        >>> queue = BatchQueue()
        >>> queue.add_task(background_path="bg.jpg", product_path="prod.png")
        >>> stats = queue.get_stats()
        >>> print(f"队列中有 {stats.total} 个任务")
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tasks: list[BatchTask] = Field(default_factory=list)
    status: QueueStatus = Field(default=QueueStatus.IDLE)
    config: Optional[ProcessConfig] = Field(
        default=None,
        description="全局处理配置（应用于所有任务）",
    )
    concurrent_limit: int = Field(
        default=DEFAULT_CONCURRENT_LIMIT,
        ge=1,
        le=5,
        description="并发处理数量限制",
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)

    @field_validator("tasks")
    @classmethod
    def validate_queue_size(cls, v: list[BatchTask]) -> list[BatchTask]:
        """验证队列大小."""
        if len(v) > MAX_QUEUE_SIZE:
            raise ValueError(f"队列最多支持 {MAX_QUEUE_SIZE} 个任务")
        return v

    @property
    def is_empty(self) -> bool:
        """队列是否为空."""
        return len(self.tasks) == 0

    @property
    def is_full(self) -> bool:
        """队列是否已满."""
        return len(self.tasks) >= MAX_QUEUE_SIZE

    @property
    def size(self) -> int:
        """队列大小."""
        return len(self.tasks)

    @property
    def remaining_capacity(self) -> int:
        """剩余容量."""
        return MAX_QUEUE_SIZE - len(self.tasks)

    @property
    def is_processing(self) -> bool:
        """是否正在处理."""
        return self.status == QueueStatus.PROCESSING

    @property
    def is_completed(self) -> bool:
        """是否已完成."""
        return self.status == QueueStatus.COMPLETED

    def add_task(
        self,
        background_path: str,
        product_path: str,
        output_path: Optional[str] = None,
        config: Optional[ProcessConfig] = None,
    ) -> BatchTask:
        """添加任务到队列.

        Args:
            background_path: 背景图路径
            product_path: 商品图路径
            output_path: 输出路径
            config: 任务配置（优先于全局配置）

        Returns:
            添加的 BatchTask

        Raises:
            ValueError: 队列已满
        """
        if self.is_full:
            raise ValueError(f"队列已满，最多支持 {MAX_QUEUE_SIZE} 个任务")

        # 创建图片任务
        task = ImageTask(
            background_path=background_path,
            product_path=product_path,
            output_path=output_path,
            config=config or self.config,
        )

        # 创建批量任务
        batch_task = BatchTask(
            queue_position=len(self.tasks) + 1,
            task=task,
        )

        self.tasks.append(batch_task)
        return batch_task

    def remove_task(self, task_id: str) -> Optional[BatchTask]:
        """从队列移除任务.

        Args:
            task_id: 任务 ID

        Returns:
            移除的任务，如果不存在返回 None
        """
        for i, task in enumerate(self.tasks):
            if task.id == task_id:
                removed = self.tasks.pop(i)
                # 重新分配队列位置
                self._reassign_positions()
                return removed
        return None

    def get_task(self, task_id: str) -> Optional[BatchTask]:
        """获取指定任务.

        Args:
            task_id: 任务 ID

        Returns:
            任务对象，如果不存在返回 None
        """
        for task in self.tasks:
            if task.id == task_id:
                return task
        return None

    def get_pending_tasks(self) -> list[BatchTask]:
        """获取待处理的任务列表."""
        return [t for t in self.tasks if t.status == TaskStatus.PENDING]

    def get_processing_tasks(self) -> list[BatchTask]:
        """获取处理中的任务列表."""
        return [t for t in self.tasks if t.status == TaskStatus.PROCESSING]

    def get_completed_tasks(self) -> list[BatchTask]:
        """获取已完成的任务列表."""
        return [t for t in self.tasks if t.status == TaskStatus.COMPLETED]

    def get_failed_tasks(self) -> list[BatchTask]:
        """获取失败的任务列表."""
        return [t for t in self.tasks if t.status == TaskStatus.FAILED]

    def get_retryable_tasks(self) -> list[BatchTask]:
        """获取可重试的任务列表."""
        return [t for t in self.tasks if t.can_retry]

    def get_stats(self) -> QueueStats:
        """获取队列统计信息."""
        return QueueStats.from_tasks(self.tasks)

    def clear(self) -> None:
        """清空队列."""
        self.tasks.clear()
        self.status = QueueStatus.IDLE
        self.started_at = None
        self.completed_at = None

    def start(self) -> None:
        """开始处理队列."""
        if self.is_empty:
            raise ValueError("队列为空，无法开始处理")
        self.status = QueueStatus.PROCESSING
        self.started_at = datetime.utcnow()

    def pause(self) -> None:
        """暂停处理."""
        if self.is_processing:
            self.status = QueueStatus.PAUSED

    def resume(self) -> None:
        """恢复处理."""
        if self.status == QueueStatus.PAUSED:
            self.status = QueueStatus.PROCESSING

    def cancel(self) -> None:
        """取消处理."""
        self.status = QueueStatus.CANCELLED
        # 取消所有待处理和处理中的任务
        for task in self.tasks:
            if task.status in (TaskStatus.PENDING, TaskStatus.PROCESSING):
                task.task.mark_cancelled()

    def mark_completed(self) -> None:
        """标记队列处理完成."""
        self.status = QueueStatus.COMPLETED
        self.completed_at = datetime.utcnow()

    def check_all_finished(self) -> bool:
        """检查是否所有任务都已结束."""
        return all(t.task.is_finished for t in self.tasks)

    def _reassign_positions(self) -> None:
        """重新分配队列位置."""
        for i, task in enumerate(self.tasks):
            task.queue_position = i + 1

    def to_dict(self) -> dict:
        """转换为字典."""
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: dict) -> "BatchQueue":
        """从字典创建队列."""
        return cls.model_validate(data)


# 进度回调类型
BatchProgressCallback = Callable[[str, int, str, QueueStats], None]
"""批量处理进度回调.

Args:
    task_id: 当前任务 ID
    progress: 当前任务进度 (0-100)
    message: 进度消息
    stats: 队列统计信息
"""
