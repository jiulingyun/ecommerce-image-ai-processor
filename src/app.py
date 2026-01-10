"""应用初始化和管理."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Optional

from src.utils.logger import setup_logger

if TYPE_CHECKING:
    from src.services.version_checker import VersionChecker, VersionInfo

logger = setup_logger(__name__)


class Application:
    """应用管理类.

    负责应用的初始化、配置加载和资源管理。

    Attributes:
        config: 应用配置
        main_window: 主窗口实例
    """

    def __init__(self) -> None:
        """初始化应用管理器."""
        self._main_window: Optional["MainWindow"] = None  # noqa: F821
        self._db_service: Optional["DatabaseService"] = None  # noqa: F821
        self._version_checker: Optional["VersionChecker"] = None
        self._initialized: bool = False

    def initialize(self) -> None:
        """初始化应用.

        执行以下初始化步骤:
        1. 确保应用数据目录存在
        2. 加载配置
        3. 初始化数据库
        4. 初始化服务
        """
        if self._initialized:
            logger.warning("应用已初始化，跳过重复初始化")
            return

        logger.info("开始初始化应用...")

        # 1. 确保数据目录存在
        self._ensure_data_directory()

        # 2. 加载配置
        self._load_settings()

        # 3. 初始化数据库
        self._init_database()

        # 4. 初始化服务
        self._init_services()

        self._initialized = True
        logger.info("应用初始化完成")

    def _ensure_data_directory(self) -> None:
        """确保应用数据目录存在."""
        from src.utils.constants import APP_DATA_DIR

        APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
        logger.debug(f"数据目录: {APP_DATA_DIR}")

    def _load_settings(self) -> None:
        """加载应用设置."""
        from src.models.app_settings import Settings

        self.settings = Settings()
        logger.debug(f"日志级别: {self.settings.log_level}")

    def _init_database(self) -> None:
        """初始化数据库."""
        from src.services.database_service import DatabaseService

        self._db_service = DatabaseService()
        self._db_service.init_db()
        logger.debug("数据库初始化完成")

    def _init_services(self) -> None:
        """初始化各服务."""
        # TODO: 初始化 AI 服务、图片服务等
        logger.debug("服务初始化完成")

    def show_main_window(self) -> None:
        """显示主窗口."""
        from src.ui.main_window import MainWindow
        from src.ui.theme_manager import Theme, apply_theme

        if self._main_window is None:
            # 应用主题（自动跟随系统）
            apply_theme(Theme.AUTO)
            logger.info("已应用系统主题")
            
            self._main_window = MainWindow()

        self._main_window.show()
        logger.info("主窗口已显示")

        # 启动时检测版本更新（后台线程）
        self._check_for_updates()

    def _check_for_updates(self) -> None:
        """检测版本更新.

        在后台线程中检测 GitHub Release 最新版本。
        如果网络不可用，静默失败，仅输出日志。
        """
        from src.services.version_checker import VersionChecker

        self._version_checker = VersionChecker()
        self._version_checker.update_available.connect(self._on_update_available)
        self._version_checker.start()
        logger.debug("已启动版本检测线程")

    def _on_update_available(self, version_info: "VersionInfo") -> None:
        """发现新版本时的回调.

        Args:
            version_info: 新版本信息
        """
        from src.ui.dialogs import UpdateDialog

        if self._main_window:
            dialog = UpdateDialog(version_info, self._main_window)
            dialog.exec()

    def cleanup(self) -> None:
        """清理应用资源."""
        logger.info("开始清理应用资源...")

        # 停止版本检测线程
        if self._version_checker and self._version_checker.isRunning():
            self._version_checker.quit()
            self._version_checker.wait(1000)
            logger.debug("版本检测线程已停止")

        # 关闭数据库连接
        if self._db_service:
            self._db_service.close()
            logger.debug("数据库连接已关闭")

        logger.info("应用资源清理完成")

    @property
    def is_initialized(self) -> bool:
        """返回应用是否已初始化."""
        return self._initialized

    @property
    def db_service(self) -> Optional["DatabaseService"]:  # noqa: F821
        """返回数据库服务实例."""
        return self._db_service
