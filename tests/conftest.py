"""Pytest 配置和共享 fixtures."""

import pytest


@pytest.fixture
def sample_config() -> dict:
    """返回示例处理配置."""
    return {
        "background": {"color": (255, 255, 255)},
        "border": {"enabled": False, "width": 2, "color": (0, 0, 0)},
        "text": {
            "enabled": False,
            "content": "",
            "position": (10, 10),
            "font_size": 14,
            "color": (0, 0, 0),
        },
        "output": {"size": (800, 800), "quality": 85},
    }
