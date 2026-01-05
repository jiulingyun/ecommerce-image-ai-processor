"""模板编辑器测试 fixtures."""

import pytest
from PyQt6.QtWidgets import QApplication


@pytest.fixture(scope="module")
def app():
    """创建 Qt 应用实例."""
    application = QApplication.instance()
    if not application:
        application = QApplication([])
    yield application
