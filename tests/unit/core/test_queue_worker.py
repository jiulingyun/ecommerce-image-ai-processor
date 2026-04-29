"""队列控制器单元测试."""

from unittest.mock import MagicMock

from src.core.queue_worker import QueueController


class TestQueueControllerStop:
    """测试队列控制器停止逻辑."""

    def test_stop_does_not_terminate_thread_when_timeout(self):
        """线程超时未退出时，不应直接 terminate."""
        controller = QueueController()
        worker = MagicMock()
        thread = MagicMock()
        thread.wait.return_value = False

        controller._worker = worker
        controller._thread = thread

        stopped = controller.stop(timeout_ms=123)

        assert stopped is False
        worker.cancel_processing.assert_called_once()
        thread.quit.assert_called_once()
        thread.wait.assert_called_once_with(123)
        thread.terminate.assert_not_called()
        assert controller._worker is worker
        assert controller._thread is thread

    def test_stop_clears_refs_after_graceful_shutdown(self):
        """线程正常退出后，应清理运行时引用."""
        controller = QueueController()
        worker = MagicMock()
        thread = MagicMock()
        thread.wait.return_value = True

        controller._worker = worker
        controller._thread = thread

        stopped = controller.stop(timeout_ms=456)

        assert stopped is True
        worker.cancel_processing.assert_called_once()
        thread.quit.assert_called_once()
        thread.wait.assert_called_once_with(456)
        assert controller._worker is None
        assert controller._thread is None
