"""配置管理器模块."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from src.models.app_settings import Settings
from src.models.process_config import ProcessConfig
from src.utils.constants import APP_DATA_DIR
from src.utils.exceptions import ConfigError
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

# 配置文件路径
USER_CONFIG_FILE = APP_DATA_DIR / "config.json"
DEFAULT_PROCESS_CONFIG_FILE = APP_DATA_DIR / "default_process_config.json"


class ConfigManager:
    """配置管理器.

    负责应用配置的加载、保存和管理。

    Attributes:
        settings: 应用设置
        process_config: 默认处理配置
    """

    _instance: Optional["ConfigManager"] = None

    def __new__(cls) -> "ConfigManager":
        """单例模式."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        """初始化配置管理器."""
        if self._initialized:
            return

        self._settings: Optional[Settings] = None
        self._process_config: Optional[ProcessConfig] = None
        self._initialized = True

        # 确保配置目录存在
        APP_DATA_DIR.mkdir(parents=True, exist_ok=True)

        logger.debug("配置管理器初始化完成")

    @property
    def settings(self) -> Settings:
        """获取应用设置."""
        if self._settings is None:
            self._settings = self._load_settings()
        return self._settings

    @property
    def process_config(self) -> ProcessConfig:
        """获取默认处理配置."""
        if self._process_config is None:
            self._process_config = self._load_process_config()
        return self._process_config

    def _load_settings(self) -> Settings:
        """加载应用设置.

        优先从环境变量加载，然后从配置文件加载。

        Returns:
            Settings 实例
        """
        try:
            settings = Settings()
            logger.debug(f"应用设置加载完成: log_level={settings.log_level}")
            return settings
        except Exception as e:
            logger.error(f"加载应用设置失败: {e}")
            raise ConfigError(f"加载应用设置失败: {e}")

    def _load_process_config(self) -> ProcessConfig:
        """加载默认处理配置.

        如果配置文件存在则从文件加载，否则返回默认配置。

        Returns:
            ProcessConfig 实例
        """
        if DEFAULT_PROCESS_CONFIG_FILE.exists():
            try:
                content = DEFAULT_PROCESS_CONFIG_FILE.read_text(encoding="utf-8")
                config = ProcessConfig.from_json(content)
                logger.debug("从文件加载默认处理配置")
                return config
            except Exception as e:
                logger.warning(f"加载处理配置文件失败，使用默认配置: {e}")

        return ProcessConfig()

    def save_process_config(self, config: ProcessConfig) -> None:
        """保存处理配置为默认配置.

        Args:
            config: 处理配置
        """
        try:
            DEFAULT_PROCESS_CONFIG_FILE.write_text(
                config.to_json(), encoding="utf-8"
            )
            self._process_config = config
            logger.info("默认处理配置已保存")
        except Exception as e:
            logger.error(f"保存处理配置失败: {e}")
            raise ConfigError(f"保存处理配置失败: {e}")

    def save_user_config(self, config: dict[str, Any]) -> None:
        """保存用户配置.

        Args:
            config: 配置字典
        """
        try:
            # 合并现有配置
            existing = self._load_user_config()
            existing.update(config)

            USER_CONFIG_FILE.write_text(
                json.dumps(existing, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            logger.debug("用户配置已保存")
        except Exception as e:
            logger.error(f"保存用户配置失败: {e}")
            raise ConfigError(f"保存用户配置失败: {e}")

    def _load_user_config(self) -> dict[str, Any]:
        """加载用户配置文件."""
        if USER_CONFIG_FILE.exists():
            try:
                content = USER_CONFIG_FILE.read_text(encoding="utf-8")
                return json.loads(content)
            except Exception as e:
                logger.warning(f"加载用户配置文件失败: {e}")
        return {}

    def get_user_config(self, key: str, default: Any = None) -> Any:
        """获取用户配置项.

        Args:
            key: 配置键
            default: 默认值

        Returns:
            配置值
        """
        config = self._load_user_config()
        return config.get(key, default)

    def set_user_config(self, key: str, value: Any) -> None:
        """设置用户配置项.

        Args:
            key: 配置键
            value: 配置值
        """
        self.save_user_config({key: value})

    def reload(self) -> None:
        """重新加载所有配置."""
        self._settings = None
        self._process_config = None
        logger.info("配置已重新加载")

    def reset_to_defaults(self) -> None:
        """重置为默认配置."""
        # 删除配置文件
        if USER_CONFIG_FILE.exists():
            USER_CONFIG_FILE.unlink()

        if DEFAULT_PROCESS_CONFIG_FILE.exists():
            DEFAULT_PROCESS_CONFIG_FILE.unlink()

        # 重新加载
        self.reload()
        logger.info("配置已重置为默认值")


# 全局配置管理器实例
config_manager = ConfigManager()


def get_config() -> ConfigManager:
    """获取配置管理器实例.

    Returns:
        ConfigManager 单例实例
    """
    return config_manager
