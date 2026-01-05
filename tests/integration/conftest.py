"""集成测试配置和共享 fixtures."""

import os
import tempfile
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock

import pytest
from PIL import Image

from src.core.config_manager import ConfigManager
from src.models.process_config import ProcessConfig
from src.services.ai_service import AIService


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """临时目录 fixture."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_background_image(temp_dir: Path) -> Path:
    """创建示例背景图片."""
    img = Image.new("RGB", (800, 800), color=(255, 255, 255))
    path = temp_dir / "background.png"
    img.save(path)
    return path


@pytest.fixture
def sample_product_image(temp_dir: Path) -> Path:
    """创建示例商品图片."""
    # 创建带透明背景的商品图
    img = Image.new("RGBA", (400, 400), color=(0, 0, 0, 0))
    # 在中间画一个商品形状
    for x in range(100, 300):
        for y in range(100, 300):
            img.putpixel((x, y), (200, 100, 50, 255))
    path = temp_dir / "product.png"
    img.save(path)
    return path


@pytest.fixture
def sample_result_image(temp_dir: Path) -> Path:
    """创建示例处理结果图片."""
    img = Image.new("RGB", (800, 800), color=(240, 240, 240))
    path = temp_dir / "result.png"
    img.save(path)
    return path


@pytest.fixture
def process_config() -> ProcessConfig:
    """创建默认处理配置."""
    return ProcessConfig()


@pytest.fixture
def mock_ai_service() -> MagicMock:
    """创建模拟 AI 服务."""
    mock = MagicMock(spec=AIService)
    mock.is_available.return_value = True
    return mock


@pytest.fixture
def config_manager(temp_dir: Path) -> Generator[ConfigManager, None, None]:
    """创建配置管理器 fixture.
    
    使用临时目录存储配置，测试后自动清理。
    """
    # 临时修改配置目录
    original_data_dir = os.environ.get("APP_DATA_DIR")
    os.environ["APP_DATA_DIR"] = str(temp_dir)
    
    # 创建新的 ConfigManager 实例
    manager = ConfigManager.__new__(ConfigManager)
    manager._settings = None
    manager._user_config_file = temp_dir / "user_config.json"
    manager._process_config_file = temp_dir / "process_config.json"
    manager._initialized = False
    
    yield manager
    
    # 恢复环境变量
    if original_data_dir:
        os.environ["APP_DATA_DIR"] = original_data_dir
    elif "APP_DATA_DIR" in os.environ:
        del os.environ["APP_DATA_DIR"]


@pytest.fixture
def output_dir(temp_dir: Path) -> Path:
    """创建输出目录."""
    output = temp_dir / "output"
    output.mkdir(parents=True, exist_ok=True)
    return output
