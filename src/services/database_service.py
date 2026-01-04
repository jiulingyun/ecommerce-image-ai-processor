"""数据库服务模块."""

from pathlib import Path
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.utils.constants import DATABASE_PATH
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


# 延迟导入，避免循环依赖
def _get_base():
    """获取 SQLAlchemy Base."""
    from src.models.database import Base
    return Base


class DatabaseService:
    """数据库服务.

    管理 SQLite 数据库连接和会话。

    Attributes:
        db_path: 数据库文件路径
        engine: SQLAlchemy 引擎
    """

    def __init__(self, db_path: Optional[Path] = None) -> None:
        """初始化数据库服务.

        Args:
            db_path: 数据库文件路径，默认使用配置路径
        """
        self.db_path = db_path or DATABASE_PATH
        self._ensure_directory()

        # 创建引擎
        self.engine = create_engine(
            f"sqlite:///{self.db_path}",
            connect_args={"check_same_thread": False},
            echo=False,
        )

        # 创建会话工厂
        self.SessionLocal = sessionmaker(
            bind=self.engine,
            autocommit=False,
            autoflush=False,
        )

        logger.debug(f"数据库服务初始化完成: {self.db_path}")

    def _ensure_directory(self) -> None:
        """确保数据库目录存在."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def init_db(self) -> None:
        """初始化数据库表.

        创建所有定义的表结构。
        """
        Base = _get_base()
        Base.metadata.create_all(self.engine)
        logger.info("数据库表初始化完成")

    def get_session(self) -> Session:
        """获取数据库会话.

        Returns:
            SQLAlchemy Session 实例
        """
        return self.SessionLocal()

    def close(self) -> None:
        """关闭数据库连接."""
        self.engine.dispose()
        logger.debug("数据库连接已关闭")

    def __enter__(self) -> "DatabaseService":
        """上下文管理器入口."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """上下文管理器出口."""
        self.close()
