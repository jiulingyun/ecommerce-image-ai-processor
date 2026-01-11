"""TaskListWidget 组件单元测试."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from PyQt6.QtWidgets import QApplication

from src.models.image_task import ImageTask, TaskStatus
from src.ui.widgets.task_list_widget import TaskListWidget, TaskListItem


@pytest.fixture(scope="module")
def app():
    """创建 Qt 应用实例."""
    application = QApplication.instance()
    if not application:
        application = QApplication([])
    yield application


@pytest.fixture
def task_list(app):
    """创建 TaskListWidget 实例."""
    widget = TaskListWidget()
    yield widget
    widget.close()


@pytest.fixture
def test_image_bg():
    """创建测试背景图片文件."""
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        png_data = bytes([
            0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,
            0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,
            0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
            0x08, 0x06, 0x00, 0x00, 0x00, 0x1F, 0x15, 0xC4,
            0x89, 0x00, 0x00, 0x00, 0x0A, 0x49, 0x44, 0x41,
            0x54, 0x78, 0x9C, 0x63, 0x00, 0x01, 0x00, 0x00,
            0x05, 0x00, 0x01, 0x0D, 0x0A, 0x2D, 0xB4, 0x00,
            0x00, 0x00, 0x00, 0x49, 0x45, 0x4E, 0x44, 0xAE,
            0x42, 0x60, 0x82
        ])
        f.write(png_data)
        f.flush()
        yield Path(f.name)
    Path(f.name).unlink(missing_ok=True)


@pytest.fixture
def test_image_prod():
    """创建测试商品图片文件."""
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
        jpg_data = bytes([
            0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46,
            0x49, 0x46, 0x00, 0x01, 0x01, 0x00, 0x00, 0x01,
            0x00, 0x01, 0x00, 0x00, 0xFF, 0xDB, 0x00, 0x43,
            0x00, 0x08, 0x06, 0x06, 0x07, 0x06, 0x05, 0x08,
            0x07, 0x07, 0x07, 0x09, 0x09, 0x08, 0x0A, 0x0C,
            0x14, 0x0D, 0x0C, 0x0B, 0x0B, 0x0C, 0x19, 0x12,
            0x13, 0x0F, 0x14, 0x1D, 0x1A, 0x1F, 0x1E, 0x1D,
            0x1A, 0x1C, 0x1C, 0x20, 0x24, 0x2E, 0x27, 0x20,
            0x22, 0x2C, 0x23, 0x1C, 0x1C, 0x28, 0x37, 0x29,
            0x2C, 0x30, 0x31, 0x34, 0x34, 0x34, 0x1F, 0x27,
            0x39, 0x3D, 0x38, 0x32, 0x3C, 0x2E, 0x33, 0x34,
            0x32, 0xFF, 0xC0, 0x00, 0x0B, 0x08, 0x00, 0x01,
            0x00, 0x01, 0x01, 0x01, 0x11, 0x00, 0xFF, 0xC4,
            0x00, 0x1F, 0x00, 0x00, 0x01, 0x05, 0x01, 0x01,
            0x01, 0x01, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00, 0x01, 0x02, 0x03, 0x04,
            0x05, 0x06, 0x07, 0x08, 0x09, 0x0A, 0x0B, 0xFF,
            0xDA, 0x00, 0x08, 0x01, 0x01, 0x00, 0x00, 0x3F,
            0x00, 0xFB, 0xD5, 0x00, 0x00, 0x00, 0x00, 0xFF,
            0xD9
        ])
        f.write(jpg_data)
        f.flush()
        yield Path(f.name)
    Path(f.name).unlink(missing_ok=True)


@pytest.fixture
def sample_task(test_image_bg, test_image_prod):
    """创建示例任务."""
    return ImageTask(
        image_paths=[str(test_image_bg), str(test_image_prod)],
    )


class TestTaskListWidgetInit:
    """测试 TaskListWidget 初始化."""

    def test_init_default(self, app):
        """测试默认初始化."""
        widget = TaskListWidget()
        assert widget.task_count == 0
        widget.close()

    def test_task_count_initial(self, task_list):
        """测试初始任务数量."""
        assert task_list.task_count == 0

    def test_selected_task_initial(self, task_list):
        """测试初始选中任务."""
        assert task_list.get_selected_task() is None


class TestTaskListWidgetAddTask:
    """测试添加任务."""

    def test_add_task(self, task_list, sample_task):
        """测试添加任务."""
        task_list.add_task(sample_task)
        assert task_list.task_count == 1

    def test_add_multiple_tasks(self, task_list, test_image_bg, test_image_prod):
        """测试添加多个任务."""
        task1 = ImageTask(
            image_paths=[str(test_image_bg), str(test_image_prod)],
        )
        task2 = ImageTask(
            image_paths=[str(test_image_bg), str(test_image_prod)],
        )

        task_list.add_task(task1)
        task_list.add_task(task2)

        assert task_list.task_count == 2

    def test_task_ids_unique(self, task_list, test_image_bg, test_image_prod):
        """测试任务 ID 唯一."""
        task1 = ImageTask(
            image_paths=[str(test_image_bg), str(test_image_prod)],
        )
        task2 = ImageTask(
            image_paths=[str(test_image_bg), str(test_image_prod)],
        )

        task_list.add_task(task1)
        task_list.add_task(task2)

        assert task1.id != task2.id


class TestTaskListWidgetRemoveTask:
    """测试移除任务."""

    def test_remove_task(self, task_list, sample_task):
        """测试移除任务."""
        task_list.add_task(sample_task)
        assert task_list.task_count == 1

        task_list.remove_task(sample_task.id)
        assert task_list.task_count == 0

    def test_remove_nonexistent_task(self, task_list, sample_task):
        """测试移除不存在的任务."""
        task_list.add_task(sample_task)
        task_list.remove_task("nonexistent-id")
        assert task_list.task_count == 1


class TestTaskListWidgetClearAll:
    """测试清空所有任务."""

    def test_clear_all(self, task_list, test_image_bg, test_image_prod):
        """测试清空所有任务."""
        for _ in range(3):
            task = ImageTask(
                image_paths=[str(test_image_bg), str(test_image_prod)],
            )
            task_list.add_task(task)

        assert task_list.task_count == 3

        task_list.clear_all()
        assert task_list.task_count == 0


class TestTaskListWidgetSelection:
    """测试任务选择."""

    def test_task_selected_signal(self, task_list, sample_task):
        """测试任务选中信号."""
        signal_handler = MagicMock()
        task_list.task_selected.connect(signal_handler)

        task_list.add_task(sample_task)
        # 模拟选中 - 通过内部列表
        task_list._list_widget.setCurrentRow(0)
        # 触发点击事件
        item = task_list._list_widget.item(0)
        if item:
            task_list._on_item_clicked(item)

        signal_handler.assert_called()

    def test_selected_task_method(self, task_list, sample_task):
        """测试选中任务方法."""
        task_list.add_task(sample_task)
        task_list._list_widget.setCurrentRow(0)

        # 选中后应该有任务
        selected = task_list.get_selected_task()
        assert selected is not None
        assert selected.id == sample_task.id


class TestTaskListWidgetDelete:
    """测试任务删除."""

    def test_task_deleted_signal(self, task_list, sample_task):
        """测试任务删除信号."""
        signal_handler = MagicMock()
        task_list.task_deleted.connect(signal_handler)

        task_list.add_task(sample_task)

        # 获取列表项并触发删除 - 通过内部列表
        item = task_list._list_widget.item(0)
        widget = task_list._list_widget.itemWidget(item)
        if widget:
            widget._on_delete()

        signal_handler.assert_called_once_with(sample_task.id)


class TestTaskListWidgetGetTask:
    """测试获取任务."""

    def test_get_task(self, task_list, sample_task):
        """测试获取任务."""
        task_list.add_task(sample_task)
        task = task_list.get_task(sample_task.id)
        assert task is not None
        assert task.id == sample_task.id

    def test_get_nonexistent_task(self, task_list, sample_task):
        """测试获取不存在的任务."""
        task_list.add_task(sample_task)
        task = task_list.get_task("nonexistent-id")
        assert task is None


class TestTaskListWidgetGetAllTasks:
    """测试获取所有任务."""

    def test_get_all_tasks(self, task_list, test_image_bg, test_image_prod):
        """测试获取所有任务."""
        tasks_added = []
        for _ in range(3):
            task = ImageTask(
                image_paths=[str(test_image_bg), str(test_image_prod)],
            )
            tasks_added.append(task)
            task_list.add_task(task)

        # 使用 tasks 属性获取所有任务
        all_tasks = task_list.tasks
        assert len(all_tasks) == 3

    def test_get_all_tasks_empty(self, task_list):
        """测试空列表获取所有任务."""
        all_tasks = task_list.tasks
        assert len(all_tasks) == 0


class TestTaskListItem:
    """测试 TaskListItem."""

    def test_init(self, app, sample_task):
        """测试初始化."""
        item = TaskListItem(sample_task)
        assert item.task_id == sample_task.id
        item.close()

    def test_task_property(self, app, sample_task):
        """测试任务属性."""
        item = TaskListItem(sample_task)
        assert item.task.id == sample_task.id
        item.close()

    def test_delete_clicked_signal(self, app, sample_task):
        """测试删除点击信号."""
        item = TaskListItem(sample_task)
        signal_handler = MagicMock()
        item.delete_clicked.connect(signal_handler)

        item._on_delete()

        signal_handler.assert_called_once_with(sample_task.id)
        item.close()

    def test_update_task(self, app, sample_task):
        """测试更新任务."""
        item = TaskListItem(sample_task)

        # 更新状态
        sample_task.mark_processing(50)
        item.update_task(sample_task)

        assert item.task.status == TaskStatus.PROCESSING
        assert item.task.progress == 50
        item.close()
