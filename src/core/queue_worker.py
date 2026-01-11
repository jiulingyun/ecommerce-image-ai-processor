"""队列工作器模块.

在 Qt 线程中运行异步批处理任务，连接 UI 和批处理器。

Features:
    - Qt 线程中执行异步任务
    - 实时进度更新
    - 暂停/恢复/取消支持
    - 与主窗口信号集成
"""

from __future__ import annotations

import asyncio
from typing import Callable, Dict, Optional

from PyQt6.QtCore import QObject, QThread, pyqtSignal, pyqtSlot

from src.core.batch_processor import BatchProcessor
from src.models.batch_queue import BatchTask, QueueStats
from src.models.image_task import ImageTask
from src.models.process_config import ProcessConfig
from src.services.image_service import ImageService, get_image_service
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class QueueWorker(QObject):
    """队列工作器.

    在后台线程中执行批量图片处理任务。

    Signals:
        task_started: 任务开始信号 (task_id)
        task_progress: 任务进度信号 (task_id, progress, message)
        task_completed: 任务完成信号 (task_id, output_path)
        task_failed: 任务失败信号 (task_id, error_message)
        queue_progress: 队列进度信号 (QueueStats)
        queue_completed: 队列完成信号 (QueueStats)
        error_occurred: 错误发生信号 (Exception)
    """

    # 信号定义
    task_started = pyqtSignal(str)  # task_id
    task_progress = pyqtSignal(str, int, str)  # task_id, progress, message
    task_completed = pyqtSignal(str, str)  # task_id, output_path
    task_failed = pyqtSignal(str, str)  # task_id, error_message
    queue_progress = pyqtSignal(object)  # QueueStats
    queue_completed = pyqtSignal(object)  # QueueStats
    error_occurred = pyqtSignal(object)  # Exception

    def __init__(
        self,
        parent: Optional[QObject] = None,
    ) -> None:
        """初始化队列工作器.

        Args:
            parent: 父对象
        """
        super().__init__(parent)
        self._processor: Optional[BatchProcessor] = None
        self._tasks: Dict[str, ImageTask] = {}  # 从 MainWindow 同步的任务
        self._is_running = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._concurrent_limit: int = 3  # 默认并发数

    @property
    def is_running(self) -> bool:
        """是否正在运行."""
        return self._is_running

    @property
    def is_paused(self) -> bool:
        """是否已暂停."""
        if self._processor:
            return self._processor.is_paused
        return False

    def set_tasks(self, tasks: Dict[str, ImageTask]) -> None:
        """设置要处理的任务.

        Args:
            tasks: 任务字典 {task_id: ImageTask}
        """
        self._tasks = tasks.copy()

    def set_config(self, config: Optional[ProcessConfig] = None) -> None:
        """设置处理配置.

        Args:
            config: 处理配置
        """
        if self._processor:
            self._processor.queue.config = config

    def set_concurrent_limit(self, limit: int) -> None:
        """设置并发处理数量.

        Args:
            limit: 并发数量 (1-10)
        """
        self._concurrent_limit = max(1, min(10, limit))

    @pyqtSlot()
    def start_processing(self) -> None:
        """开始处理队列."""
        if self._is_running:
            logger.warning("处理已在进行中")
            return

        if not self._tasks:
            logger.warning("没有任务需要处理")
            return

        self._is_running = True
        logger.info(f"开始处理 {len(self._tasks)} 个任务")

        # 创建处理器
        self._processor = BatchProcessor(
            image_service=get_image_service(),
            concurrent_limit=self._concurrent_limit,
        )

        # 将任务添加到处理器队列（使用已存在的 ImageTask 以保持引用）
        for task_id, task in self._tasks.items():
            try:
                self._processor.queue.add_existing_task(task)
            except Exception as e:
                logger.error(f"添加任务失败: {task_id}, {e}")

        # 在新的事件循环中运行
        try:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)

            self._loop.run_until_complete(self._run_processing())

        except Exception as e:
            logger.exception(f"处理异常: {e}")
            self.error_occurred.emit(e)
        finally:
            if self._loop:
                self._loop.close()
                self._loop = None
            self._is_running = False
            logger.debug(f"QueueWorker 已停止，_is_running={self._is_running}")

    async def _run_processing(self) -> None:
        """运行处理（异步）."""
        if not self._processor:
            return

        def on_progress(task_id: str, progress: int, message: str, stats: QueueStats) -> None:
            """进度回调."""
            self.task_progress.emit(task_id, progress, message)
            self.queue_progress.emit(stats)

        def on_task_complete(batch_task: BatchTask) -> None:
            """任务完成回调."""
            task = batch_task.task
            # 使用 ImageTask.id 而不是 BatchTask.id，因为 MainWindow 使用的是 ImageTask.id
            logger.info(f"on_task_complete: task.id={task.id}, status={task.status}, output={task.output_path}")
            if task.is_completed:
                logger.info(f"Emitting task_completed signal for {task.id}")
                self.task_completed.emit(task.id, task.output_path or "")
            elif task.is_failed:
                logger.info(f"Emitting task_failed signal for {task.id}")
                self.task_failed.emit(task.id, task.error_message or "未知错误")

        def on_queue_complete(stats: QueueStats) -> None:
            """队列完成回调."""
            self.queue_completed.emit(stats)

        # 执行处理
        await self._processor.process_all(
            on_progress=on_progress,
            on_task_complete=on_task_complete,
            on_queue_complete=on_queue_complete,
        )

    @pyqtSlot()
    def pause_processing(self) -> None:
        """暂停处理."""
        if self._processor and self._is_running:
            self._processor.pause()
            logger.info("处理已暂停")

    @pyqtSlot()
    def resume_processing(self) -> None:
        """恢复处理."""
        if self._processor and self._is_running:
            self._processor.resume()
            logger.info("处理已恢复")

    @pyqtSlot()
    def cancel_processing(self) -> None:
        """取消处理."""
        if self._processor:
            self._processor.cancel()
            # 注意：不在这里设置 _is_running = False
            # 它会在 start_processing 的 finally 块中自动设置
            logger.info("处理已取消")


class QueueWorkerThread(QThread):
    """队列工作线程.

    管理 QueueWorker 的线程生命周期。

    Example:
        >>> worker_thread = QueueWorkerThread()
        >>> worker_thread.worker.set_tasks(tasks)
        >>> worker_thread.start_processing()
    """

    def __init__(self, parent: Optional[QObject] = None) -> None:
        """初始化工作线程.

        Args:
            parent: 父对象
        """
        super().__init__(parent)
        self._worker = QueueWorker()
        self._worker.moveToThread(self)

    @property
    def worker(self) -> QueueWorker:
        """获取工作器."""
        return self._worker

    def start_processing(self) -> None:
        """开始处理."""
        if not self.isRunning():
            self.start()
        # 通过信号触发处理
        self._worker.start_processing()

    def stop(self) -> None:
        """停止线程."""
        self._worker.cancel_processing()
        self.quit()
        self.wait()


class QueueController(QObject):
    """队列控制器.

    高级 API，管理工作线程和 UI 交互。

    Signals:
        progress_updated: 进度更新信号 (progress: int, message: str)
        task_completed: 任务完成信号 (task_id: str, output_path: str)
        task_failed: 任务失败信号 (task_id: str, error: str)
        all_completed: 全部完成信号 (stats: QueueStats)
        error_occurred: 错误发生信号 (exception: Exception)

    Example:
        >>> controller = QueueController(main_window)
        >>> controller.set_tasks(tasks)
        >>> controller.start()
    """

    progress_updated = pyqtSignal(int, str)  # progress, message
    task_started = pyqtSignal(str)  # task_id - 任务开始处理
    task_progress = pyqtSignal(str, int)  # task_id, progress - 任务进度更新
    task_completed = pyqtSignal(str, str)  # task_id, output_path
    task_failed = pyqtSignal(str, str)  # task_id, error
    all_completed = pyqtSignal(object)  # QueueStats
    error_occurred = pyqtSignal(object)  # Exception

    def __init__(self, parent: Optional[QObject] = None) -> None:
        """初始化控制器.

        Args:
            parent: 父对象（通常是 MainWindow）
        """
        super().__init__(parent)
        self._thread: Optional[QThread] = None
        self._worker: Optional[QueueWorker] = None
        self._tasks: Dict[str, ImageTask] = {}
        self._config: Optional[ProcessConfig] = None
        self._processing_tasks: set = set()  # 跟踪已开始处理的任务
        self._concurrent_limit: int = 3  # 默认并发数

    @property
    def is_running(self) -> bool:
        """是否正在运行."""
        return self._worker is not None and self._worker.is_running

    @property
    def is_paused(self) -> bool:
        """是否已暂停."""
        return self._worker is not None and self._worker.is_paused

    def set_tasks(self, tasks: Dict[str, ImageTask]) -> None:
        """设置任务.

        Args:
            tasks: 任务字典
        """
        self._tasks = tasks.copy()

    def set_config(self, config: Optional[ProcessConfig]) -> None:
        """设置配置.

        Args:
            config: 处理配置
        """
        self._config = config

    def set_concurrent_limit(self, limit: int) -> None:
        """设置并发处理数量.

        Args:
            limit: 并发数量 (1-10)
        """
        self._concurrent_limit = max(1, min(10, limit))

    def start(self) -> None:
        """开始处理."""
        if self.is_running:
            logger.warning("已在处理中")
            return

        if not self._tasks:
            logger.warning("没有任务")
            return
        
        # 清理之前的线程和工作器
        if self._thread and self._thread.isRunning():
            logger.warning("之前的线程仍在运行，等待完成...")
            self.stop()
        
        self._worker = None
        self._thread = None
        self._processing_tasks.clear()  # 清空处理中任务集合

        # 创建工作线程
        self._thread = QThread(self)
        self._worker = QueueWorker()
        self._worker.moveToThread(self._thread)

        # 设置任务和配置
        self._worker.set_tasks(self._tasks)
        self._worker.set_concurrent_limit(self._concurrent_limit)
        if self._config:
            self._worker.set_config(self._config)

        # 连接信号
        self._thread.started.connect(self._worker.start_processing)
        self._worker.task_progress.connect(self._on_task_progress)
        self._worker.task_completed.connect(self._on_task_completed)
        self._worker.task_failed.connect(self._on_task_failed)
        self._worker.queue_progress.connect(self._on_queue_progress)
        self._worker.queue_completed.connect(self._on_all_completed)
        self._worker.error_occurred.connect(self._on_error)

        # 启动线程
        self._thread.start()
        logger.info("队列处理已启动")

    def pause(self) -> None:
        """暂停处理."""
        if self._worker:
            self._worker.pause_processing()

    def resume(self) -> None:
        """恢复处理."""
        if self._worker:
            self._worker.resume_processing()

    def cancel(self) -> None:
        """取消处理."""
        if self._worker:
            self._worker.cancel_processing()

    def stop(self) -> None:
        """停止处理."""
        if self._worker:
            self._worker.cancel_processing()
        if self._thread:
            self._thread.quit()
            self._thread.wait(5000)  # 等待最多5秒
            if self._thread.isRunning():
                logger.warning("线程未在5秒内停止，强制终止")
                self._thread.terminate()
                self._thread.wait()
        self._worker = None
        self._thread = None

    def _on_task_progress(self, task_id: str, progress: int, message: str) -> None:
        """任务进度回调."""
        # 首次收到任务进度时，发送 task_started 信号
        if task_id not in self._processing_tasks:
            self._processing_tasks.add(task_id)
            self.task_started.emit(task_id)
        # 发送任务进度更新
        self.task_progress.emit(task_id, progress)
        self.progress_updated.emit(progress, message)

    def _on_task_completed(self, task_id: str, output_path: str) -> None:
        """任务完成回调."""
        self.task_completed.emit(task_id, output_path)

    def _on_task_failed(self, task_id: str, error: str) -> None:
        """任务失败回调."""
        self.task_failed.emit(task_id, error)

    def _on_queue_progress(self, stats: QueueStats) -> None:
        """队列进度回调."""
        self.progress_updated.emit(stats.progress, f"已完成 {stats.completed}/{stats.total}")

    def _on_all_completed(self, stats: QueueStats) -> None:
        """全部完成回调."""
        self.all_completed.emit(stats)
        # 清理线程
        if self._thread:
            self._thread.quit()
            self._thread.wait(1000)

    def _on_error(self, exception: Exception) -> None:
        """错误回调."""
        self.error_occurred.emit(exception)


# 全局控制器
_queue_controller: Optional[QueueController] = None


def get_queue_controller(parent: Optional[QObject] = None) -> QueueController:
    """获取队列控制器.

    如果指定了 parent，创建新的控制器并绑定到该 parent。
    这确保每个 MainWindow 都有自己的控制器实例。

    Args:
        parent: 父对象

    Returns:
        QueueController 实例
    """
    global _queue_controller
    if parent is not None:
        # 每次有新 parent 时，创建新的控制器
        _queue_controller = QueueController(parent)
    elif _queue_controller is None:
        _queue_controller = QueueController()
    return _queue_controller


def reset_queue_controller() -> None:
    """重置队列控制器（测试用）."""
    global _queue_controller
    _queue_controller = None
