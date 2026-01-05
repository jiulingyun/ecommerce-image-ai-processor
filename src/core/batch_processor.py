"""批量处理器模块.

提供批量图片处理的核心功能，支持队列管理、并发控制和进度追踪。

Features:
    - 批量任务管理
    - 并发处理控制
    - 实时进度追踪
    - 自动重试机制
    - 暂停/恢复支持
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Callable, Optional

from src.models.batch_queue import (
    BatchProgressCallback,
    BatchQueue,
    BatchTask,
    QueueStats,
    QueueStatus,
)
from src.models.image_task import TaskStatus
from src.models.process_config import ProcessConfig
from src.services.image_service import ImageService, get_image_service
from src.utils.exceptions import ImageProcessError
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

# 类型别名
QueueProgressCallback = Callable[[QueueStats], None]
TaskProgressCallback = Callable[[str, int, str], None]


class BatchProcessor:
    """批量处理器.

    管理批量图片处理任务的执行，支持并发控制、进度追踪和错误处理。

    Attributes:
        queue: 批量处理队列
        image_service: 图片处理服务

    Example:
        >>> processor = BatchProcessor()
        >>> processor.add_task("bg1.jpg", "prod1.png")
        >>> processor.add_task("bg2.jpg", "prod2.png")
        >>> await processor.process_all(on_progress=my_callback)
    """

    def __init__(
        self,
        image_service: Optional[ImageService] = None,
        config: Optional[ProcessConfig] = None,
        concurrent_limit: int = 3,
    ) -> None:
        """初始化批量处理器.

        Args:
            image_service: 图片处理服务实例
            config: 全局处理配置
            concurrent_limit: 并发处理数量限制 (1-5)
        """
        self._image_service = image_service
        self._queue = BatchQueue(config=config, concurrent_limit=concurrent_limit)
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._is_cancelled = False
        self._is_paused = False
        self._pause_event = asyncio.Event()
        self._pause_event.set()  # 初始状态为非暂停

    @property
    def image_service(self) -> ImageService:
        """获取图片处理服务实例."""
        if self._image_service is None:
            self._image_service = get_image_service()
        return self._image_service

    @property
    def queue(self) -> BatchQueue:
        """获取批量处理队列."""
        return self._queue

    @property
    def is_processing(self) -> bool:
        """是否正在处理."""
        return self._queue.is_processing

    @property
    def is_paused(self) -> bool:
        """是否已暂停."""
        return self._is_paused

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
            config: 任务配置

        Returns:
            添加的 BatchTask

        Raises:
            ValueError: 队列已满
        """
        return self._queue.add_task(
            background_path=background_path,
            product_path=product_path,
            output_path=output_path,
            config=config,
        )

    def remove_task(self, task_id: str) -> Optional[BatchTask]:
        """从队列移除任务."""
        return self._queue.remove_task(task_id)

    def get_stats(self) -> QueueStats:
        """获取队列统计信息."""
        return self._queue.get_stats()

    def clear(self) -> None:
        """清空队列."""
        self._queue.clear()
        self._is_cancelled = False
        self._is_paused = False

    async def process_all(
        self,
        on_progress: Optional[BatchProgressCallback] = None,
        on_task_complete: Optional[Callable[[BatchTask], None]] = None,
        on_queue_complete: Optional[Callable[[QueueStats], None]] = None,
    ) -> QueueStats:
        """处理队列中的所有任务.

        Args:
            on_progress: 进度回调 (task_id, progress, message, stats)
            on_task_complete: 单个任务完成回调
            on_queue_complete: 队列处理完成回调

        Returns:
            最终的队列统计信息

        Example:
            >>> async def progress_callback(task_id, progress, message, stats):
            ...     print(f"任务 {task_id}: {progress}% - {message}")
            ...     print(f"总进度: {stats.progress}%")
            >>> await processor.process_all(on_progress=progress_callback)
        """
        if self._queue.is_empty:
            logger.warning("队列为空，无需处理")
            return self._queue.get_stats()

        # 初始化
        self._is_cancelled = False
        self._is_paused = False
        self._pause_event.set()
        self._semaphore = asyncio.Semaphore(self._queue.concurrent_limit)
        self._queue.start()

        logger.info(f"开始批量处理，共 {self._queue.size} 个任务")

        try:
            # 创建所有任务的协程
            tasks = [
                self._process_task(batch_task, on_progress, on_task_complete)
                for batch_task in self._queue.tasks
            ]

            # 并发执行所有任务
            await asyncio.gather(*tasks, return_exceptions=True)

            # 检查是否需要重试失败的任务
            await self._retry_failed_tasks(on_progress, on_task_complete)

        except Exception as e:
            logger.exception(f"批量处理异常: {e}")
        finally:
            # 标记队列完成
            if self._is_cancelled:
                self._queue.cancel()
            else:
                self._queue.mark_completed()

            final_stats = self._queue.get_stats()
            logger.info(
                f"批量处理完成: {final_stats.completed}/{final_stats.total} 成功, "
                f"{final_stats.failed} 失败"
            )

            if on_queue_complete:
                on_queue_complete(final_stats)

            return final_stats

    async def _process_task(
        self,
        batch_task: BatchTask,
        on_progress: Optional[BatchProgressCallback],
        on_task_complete: Optional[Callable[[BatchTask], None]],
    ) -> None:
        """处理单个任务.

        Args:
            batch_task: 批量任务
            on_progress: 进度回调
            on_task_complete: 任务完成回调
        """
        async with self._semaphore:  # type: ignore
            # 检查是否取消
            if self._is_cancelled:
                batch_task.task.mark_cancelled()
                return

            # 等待暂停恢复
            await self._pause_event.wait()

            task = batch_task.task
            task_id = batch_task.id

            logger.info(f"开始处理任务 {batch_task.queue_position}: {task.product_filename}")

            def task_progress(progress: int, message: str) -> None:
                """任务进度回调."""
                task.update_status(TaskStatus.PROCESSING, progress=progress)
                if on_progress:
                    stats = self._queue.get_stats()
                    on_progress(task_id, progress, message, stats)

            try:
                task.mark_processing()

                # 调用图片处理服务执行合成
                output_path = await self.image_service.composite_product(
                    background_path=task.background_path,
                    product_path=task.product_path,
                    output_path=task.output_path,
                    config=task.config,
                    on_progress=task_progress,
                )

                task.mark_completed(str(output_path))
                logger.info(f"任务 {batch_task.queue_position} 完成: {output_path}")

            except Exception as e:
                error_msg = str(e)
                task.mark_failed(error_msg)
                logger.error(f"任务 {batch_task.queue_position} 失败: {error_msg}")

            finally:
                if on_task_complete:
                    on_task_complete(batch_task)

    async def _retry_failed_tasks(
        self,
        on_progress: Optional[BatchProgressCallback],
        on_task_complete: Optional[Callable[[BatchTask], None]],
    ) -> None:
        """重试失败的任务."""
        retryable = self._queue.get_retryable_tasks()

        if not retryable:
            return

        logger.info(f"开始重试 {len(retryable)} 个失败任务")

        for batch_task in retryable:
            if self._is_cancelled:
                break

            batch_task.increment_retry()
            logger.info(
                f"重试任务 {batch_task.queue_position} (第 {batch_task.retry_count} 次)"
            )

            await self._process_task(batch_task, on_progress, on_task_complete)

    def pause(self) -> None:
        """暂停处理."""
        if self.is_processing and not self._is_paused:
            self._is_paused = True
            self._pause_event.clear()
            self._queue.pause()
            logger.info("批量处理已暂停")

    def resume(self) -> None:
        """恢复处理."""
        if self._is_paused:
            self._is_paused = False
            self._pause_event.set()
            self._queue.resume()
            logger.info("批量处理已恢复")

    def cancel(self) -> None:
        """取消处理."""
        self._is_cancelled = True
        self._pause_event.set()  # 确保不在暂停状态
        logger.info("批量处理已取消")

    async def process_single(
        self,
        task_id: str,
        on_progress: Optional[Callable[[int, str], None]] = None,
    ) -> Optional[BatchTask]:
        """处理单个指定任务.

        Args:
            task_id: 任务 ID
            on_progress: 进度回调

        Returns:
            处理后的任务，如果不存在返回 None
        """
        batch_task = self._queue.get_task(task_id)
        if batch_task is None:
            return None

        def progress_callback(progress: int, message: str) -> None:
            batch_task.task.update_status(TaskStatus.PROCESSING, progress=progress)
            if on_progress:
                on_progress(progress, message)

        await self._process_task(batch_task, None, None)
        return batch_task


# 单例实例
_batch_processor_instance: Optional[BatchProcessor] = None


def get_batch_processor(
    image_service: Optional[ImageService] = None,
    config: Optional[ProcessConfig] = None,
) -> BatchProcessor:
    """获取批量处理器单例.

    Args:
        image_service: 图片处理服务
        config: 全局处理配置

    Returns:
        BatchProcessor 实例
    """
    global _batch_processor_instance

    if _batch_processor_instance is None:
        _batch_processor_instance = BatchProcessor(
            image_service=image_service,
            config=config,
        )

    return _batch_processor_instance


def reset_batch_processor() -> None:
    """重置批量处理器单例."""
    global _batch_processor_instance
    _batch_processor_instance = None
