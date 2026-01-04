"""图片任务模型."""

import uuid
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from src.models.process_config import ProcessConfig


class TaskStatus(str, Enum):
    """任务状态枚举."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ImageTask(BaseModel):
    """图片处理任务.

    表示一个待处理的图片任务，包含输入图片路径、输出路径、
    处理配置和状态信息。

    Attributes:
        id: 任务唯一标识符
        background_path: 背景/场景图路径
        product_path: 商品图路径
        output_path: 输出文件路径
        config: 处理配置
        status: 任务状态
        progress: 处理进度 (0-100)
        error_message: 错误信息
        created_at: 创建时间
        updated_at: 更新时间
        completed_at: 完成时间
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    background_path: str = Field(..., description="背景/场景图路径")
    product_path: str = Field(..., description="商品图路径")
    output_path: Optional[str] = Field(default=None, description="输出文件路径")
    config: Optional[ProcessConfig] = Field(
        default=None, description="处理配置"
    )
    status: TaskStatus = Field(
        default=TaskStatus.PENDING, description="任务状态"
    )
    progress: int = Field(default=0, ge=0, le=100, description="处理进度")
    error_message: Optional[str] = Field(default=None, description="错误信息")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = Field(default=None)

    @field_validator("background_path", "product_path")
    @classmethod
    def validate_path(cls, v: str) -> str:
        """验证路径格式."""
        if not v or not v.strip():
            raise ValueError("路径不能为空")
        return v.strip()

    def update_status(
        self,
        status: TaskStatus,
        progress: Optional[int] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """更新任务状态.

        Args:
            status: 新状态
            progress: 进度值 (可选)
            error_message: 错误信息 (可选)
        """
        self.status = status
        self.updated_at = datetime.utcnow()

        if progress is not None:
            self.progress = max(0, min(100, progress))

        if error_message is not None:
            self.error_message = error_message

        if status == TaskStatus.COMPLETED:
            self.progress = 100
            self.completed_at = datetime.utcnow()
        elif status == TaskStatus.FAILED:
            self.completed_at = datetime.utcnow()

    def mark_processing(self, progress: int = 0) -> None:
        """标记为处理中."""
        self.update_status(TaskStatus.PROCESSING, progress)

    def mark_completed(self, output_path: Optional[str] = None) -> None:
        """标记为完成.

        Args:
            output_path: 输出文件路径
        """
        if output_path:
            self.output_path = output_path
        self.update_status(TaskStatus.COMPLETED, progress=100)

    def mark_failed(self, error_message: str) -> None:
        """标记为失败.

        Args:
            error_message: 错误信息
        """
        self.update_status(TaskStatus.FAILED, error_message=error_message)

    def mark_cancelled(self) -> None:
        """标记为已取消."""
        self.update_status(TaskStatus.CANCELLED)

    @property
    def is_pending(self) -> bool:
        """是否待处理."""
        return self.status == TaskStatus.PENDING

    @property
    def is_processing(self) -> bool:
        """是否处理中."""
        return self.status == TaskStatus.PROCESSING

    @property
    def is_completed(self) -> bool:
        """是否已完成."""
        return self.status == TaskStatus.COMPLETED

    @property
    def is_failed(self) -> bool:
        """是否失败."""
        return self.status == TaskStatus.FAILED

    @property
    def is_finished(self) -> bool:
        """是否已结束 (完成、失败或取消)."""
        return self.status in (
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
        )

    @property
    def background_filename(self) -> str:
        """获取背景图文件名."""
        return Path(self.background_path).name

    @property
    def product_filename(self) -> str:
        """获取商品图文件名."""
        return Path(self.product_path).name

    def to_dict(self) -> dict:
        """转换为字典."""
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: dict) -> "ImageTask":
        """从字典创建任务."""
        return cls.model_validate(data)
