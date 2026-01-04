"""数据库 ORM 模型."""

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class TaskHistory(Base):
    """任务历史记录表."""

    __tablename__ = "task_history"

    id = Column(String(36), primary_key=True)
    background_path = Column(Text, nullable=False)
    product_path = Column(Text, nullable=False)
    output_path = Column(Text)
    status = Column(String(20), default="pending")
    progress = Column(Integer, default=0)
    error_message = Column(Text)
    config_json = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime)

    def __repr__(self) -> str:
        return f"<TaskHistory(id={self.id}, status={self.status})>"


class ProcessConfigRecord(Base):
    """处理配置预设表."""

    __tablename__ = "process_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text)
    config_json = Column(Text, nullable=False)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<ProcessConfigRecord(name={self.name})>"


class AppSettingRecord(Base):
    """应用设置表."""

    __tablename__ = "app_settings"

    key = Column(String(100), primary_key=True)
    value = Column(Text)
    value_type = Column(String(20), default="string")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<AppSettingRecord(key={self.key})>"


class ProcessStats(Base):
    """处理统计表."""

    __tablename__ = "process_stats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False, unique=True)
    total_tasks = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    total_time_ms = Column(Integer, default=0)

    def __repr__(self) -> str:
        return f"<ProcessStats(date={self.date}, total={self.total_tasks})>"
