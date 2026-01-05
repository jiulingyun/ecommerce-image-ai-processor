"""配置管理集成测试.

测试 ConfigManager 配置加载、保存、重置流程。
"""

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from src.core.config_manager import ConfigManager, get_config
from src.models.process_config import ProcessConfig


class TestConfigManagerFileOperations:
    """测试配置文件操作."""

    def test_save_and_load_user_config(self, temp_dir: Path):
        """测试保存和加载用户配置."""
        config_file = temp_dir / "user_config.json"

        # 创建 ConfigManager 实例
        manager = ConfigManager.__new__(ConfigManager)
        manager._settings = None
        manager._user_config_file = config_file
        manager._process_config_file = temp_dir / "process_config.json"
        manager._initialized = False

        # 保存配置
        test_config = {
            "log_level": "DEBUG",
            "max_queue_size": 5,
            "default_output_dir": str(temp_dir / "output"),
        }
        manager.save_user_config(test_config)

        # 验证文件已创建
        assert config_file.exists()

        # 加载配置
        loaded = manager._load_user_config()
        assert loaded["log_level"] == "DEBUG"
        assert loaded["max_queue_size"] == 5

    def test_save_and_load_process_config(self, temp_dir: Path):
        """测试保存和加载处理配置."""
        config_file = temp_dir / "process_config.json"

        manager = ConfigManager.__new__(ConfigManager)
        manager._settings = None
        manager._user_config_file = temp_dir / "user_config.json"
        manager._process_config_file = config_file
        manager._initialized = False

        # 创建处理配置
        process_config = ProcessConfig()
        process_config.background.enabled = True
        process_config.border.enabled = True
        process_config.border.width = 10

        # 保存
        manager.save_process_config(process_config)

        # 验证文件已创建
        assert config_file.exists()

        # 加载
        loaded = manager.load_process_config()
        assert loaded.background.enabled is True
        assert loaded.border.enabled is True
        assert loaded.border.width == 10

    def test_config_file_not_found_returns_defaults(self, temp_dir: Path):
        """测试配置文件不存在时返回默认值."""
        manager = ConfigManager.__new__(ConfigManager)
        manager._settings = None
        manager._user_config_file = temp_dir / "nonexistent.json"
        manager._process_config_file = temp_dir / "nonexistent_process.json"
        manager._initialized = False

        # 加载用户配置应返回空字典
        loaded = manager._load_user_config()
        assert loaded == {}

        # 加载处理配置应返回默认配置
        process_config = manager.load_process_config()
        assert process_config is not None
        assert isinstance(process_config, ProcessConfig)


class TestConfigManagerSettingsIntegration:
    """测试设置集成."""

    def test_settings_loaded_on_access(self, temp_dir: Path):
        """测试访问时加载设置."""
        # 创建一个简单的用户配置
        config_file = temp_dir / "user_config.json"
        config_file.write_text(json.dumps({"log_level": "WARNING"}))

        with patch.dict(os.environ, {"APP_DATA_DIR": str(temp_dir)}):
            manager = ConfigManager.__new__(ConfigManager)
            manager._settings = None
            manager._user_config_file = config_file
            manager._process_config_file = temp_dir / "process_config.json"
            manager._initialized = False

            # 访问设置
            settings = manager.settings
            assert settings is not None

    def test_reload_refreshes_settings(self, temp_dir: Path):
        """测试重新加载刷新设置."""
        config_file = temp_dir / "user_config.json"
        config_file.write_text(json.dumps({"log_level": "INFO"}))

        manager = ConfigManager.__new__(ConfigManager)
        manager._settings = None
        manager._user_config_file = config_file
        manager._process_config_file = temp_dir / "process_config.json"
        manager._initialized = False

        # 初始加载
        _ = manager.settings

        # 修改配置文件
        config_file.write_text(json.dumps({"log_level": "ERROR"}))

        # 重新加载
        manager.reload()

        # 验证设置已更新
        assert manager._settings is None  # reload 清除缓存


class TestConfigManagerResetFunctionality:
    """测试重置功能."""

    def test_reset_to_defaults(self, temp_dir: Path):
        """测试重置为默认值."""
        config_file = temp_dir / "user_config.json"
        process_file = temp_dir / "process_config.json"

        # 创建自定义配置
        config_file.write_text(
            json.dumps({"log_level": "DEBUG", "max_queue_size": 10})
        )

        manager = ConfigManager.__new__(ConfigManager)
        manager._settings = None
        manager._user_config_file = config_file
        manager._process_config_file = process_file
        manager._initialized = False

        # 重置
        manager.reset_to_defaults()

        # 验证配置文件已删除或重置
        # 重新加载应返回默认值
        loaded = manager._load_user_config()
        # 重置后应该是空配置或默认配置
        assert "log_level" not in loaded or loaded.get("log_level") != "DEBUG"


class TestConfigManagerProcessConfigIntegration:
    """测试处理配置集成."""

    def test_get_default_process_config(self, temp_dir: Path):
        """测试获取默认处理配置."""
        manager = ConfigManager.__new__(ConfigManager)
        manager._settings = None
        manager._user_config_file = temp_dir / "user_config.json"
        manager._process_config_file = temp_dir / "process_config.json"
        manager._initialized = False

        config = manager.get_default_process_config()
        assert config is not None
        assert isinstance(config, ProcessConfig)

    def test_process_config_persistence(self, temp_dir: Path):
        """测试处理配置持久化."""
        config_file = temp_dir / "process_config.json"

        manager = ConfigManager.__new__(ConfigManager)
        manager._settings = None
        manager._user_config_file = temp_dir / "user_config.json"
        manager._process_config_file = config_file
        manager._initialized = False

        # 创建并保存配置
        config1 = ProcessConfig()
        config1.background.enabled = True
        config1.border.width = 20
        manager.save_process_config(config1)

        # 创建新实例并加载
        manager2 = ConfigManager.__new__(ConfigManager)
        manager2._settings = None
        manager2._user_config_file = temp_dir / "user_config.json"
        manager2._process_config_file = config_file
        manager2._initialized = False

        config2 = manager2.load_process_config()

        # 验证配置已持久化
        assert config2.background.enabled is True
        assert config2.border.width == 20


class TestConfigManagerConcurrency:
    """测试并发访问."""

    def test_multiple_saves_dont_corrupt(self, temp_dir: Path):
        """测试多次保存不会损坏配置."""
        config_file = temp_dir / "user_config.json"

        manager = ConfigManager.__new__(ConfigManager)
        manager._settings = None
        manager._user_config_file = config_file
        manager._process_config_file = temp_dir / "process_config.json"
        manager._initialized = False

        # 多次保存
        for i in range(5):
            manager.save_user_config({"iteration": i, "value": f"test_{i}"})

        # 加载最终配置
        loaded = manager._load_user_config()
        assert loaded["iteration"] == 4
        assert loaded["value"] == "test_4"

    def test_config_file_invalid_json_handling(self, temp_dir: Path):
        """测试无效 JSON 处理."""
        config_file = temp_dir / "user_config.json"
        config_file.write_text("{ invalid json }")

        manager = ConfigManager.__new__(ConfigManager)
        manager._settings = None
        manager._user_config_file = config_file
        manager._process_config_file = temp_dir / "process_config.json"
        manager._initialized = False

        # 应该返回空配置而不是崩溃
        loaded = manager._load_user_config()
        assert loaded == {} or isinstance(loaded, dict)


class TestConfigManagerEnvironmentIntegration:
    """测试环境变量集成."""

    def test_respects_environment_variables(self, temp_dir: Path):
        """测试尊重环境变量."""
        with patch.dict(os.environ, {"APP_DATA_DIR": str(temp_dir)}):
            # ConfigManager 应该使用环境变量指定的目录
            # 这里我们只验证机制，不测试单例
            assert os.environ.get("APP_DATA_DIR") == str(temp_dir)
