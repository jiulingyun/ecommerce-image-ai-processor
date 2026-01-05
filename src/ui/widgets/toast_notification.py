"""Toast 通知组件.

提供轻量级的消息通知功能，用于显示操作反馈、警告和错误信息。

Features:
    - 多种消息类型（成功、警告、错误、信息）
    - 自动消失动画
    - 可点击关闭
    - 队列管理多个通知
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from PyQt6.QtCore import (
    QPropertyAnimation,
    QTimer,
    Qt,
    pyqtSignal,
    QEasingCurve,
    QPoint,
)
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QGraphicsOpacityEffect,
)

from src.utils.error_messages import ErrorSeverity, UserFriendlyError


class ToastType(str, Enum):
    """通知类型."""

    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    INFO = "info"


# 类型样式配置
TOAST_STYLES = {
    ToastType.SUCCESS: {
        "background": "#f6ffed",
        "border": "#b7eb8f",
        "icon": "✓",
        "icon_color": "#52c41a",
    },
    ToastType.WARNING: {
        "background": "#fffbe6",
        "border": "#ffe58f",
        "icon": "⚠",
        "icon_color": "#faad14",
    },
    ToastType.ERROR: {
        "background": "#fff2f0",
        "border": "#ffccc7",
        "icon": "✕",
        "icon_color": "#ff4d4f",
    },
    ToastType.INFO: {
        "background": "#e6f7ff",
        "border": "#91d5ff",
        "icon": "ℹ",
        "icon_color": "#1890ff",
    },
}


class ToastNotification(QFrame):
    """单个 Toast 通知组件.

    显示一条消息通知，支持自动消失和手动关闭。

    Signals:
        closed: 通知关闭时发出

    Example:
        >>> toast = ToastNotification(
        ...     title="操作成功",
        ...     message="图片处理完成",
        ...     toast_type=ToastType.SUCCESS,
        ... )
        >>> toast.show()
    """

    closed = pyqtSignal()

    def __init__(
        self,
        title: str,
        message: str,
        toast_type: ToastType = ToastType.INFO,
        duration: int = 4000,
        closable: bool = True,
        parent: Optional[QWidget] = None,
    ) -> None:
        """初始化通知组件.

        Args:
            title: 通知标题
            message: 通知内容
            toast_type: 通知类型
            duration: 显示时长（毫秒），0 表示不自动关闭
            closable: 是否可手动关闭
            parent: 父组件
        """
        super().__init__(parent)
        self._title = title
        self._message = message
        self._toast_type = toast_type
        self._duration = duration
        self._closable = closable
        self._opacity_effect: Optional[QGraphicsOpacityEffect] = None
        self._fade_animation: Optional[QPropertyAnimation] = None

        self._setup_ui()
        self._apply_style()

        # 设置自动关闭计时器
        if duration > 0:
            QTimer.singleShot(duration, self._start_fade_out)

    def _setup_ui(self) -> None:
        """设置 UI."""
        self.setFixedWidth(360)
        self.setMaximumHeight(120)

        # 主布局
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(16, 12, 16, 12)
        main_layout.setSpacing(12)

        # 图标
        style = TOAST_STYLES[self._toast_type]
        icon_label = QLabel(style["icon"])
        icon_label.setStyleSheet(f"""
            font-size: 18px;
            color: {style["icon_color"]};
        """)
        icon_label.setFixedWidth(24)
        main_layout.addWidget(icon_label)

        # 内容区域
        content_layout = QVBoxLayout()
        content_layout.setSpacing(4)

        # 标题
        title_label = QLabel(self._title)
        title_label.setStyleSheet("""
            font-weight: bold;
            font-size: 14px;
            color: #262626;
        """)
        title_label.setWordWrap(True)
        content_layout.addWidget(title_label)

        # 消息内容
        if self._message:
            message_label = QLabel(self._message)
            message_label.setStyleSheet("""
                font-size: 13px;
                color: #595959;
            """)
            message_label.setWordWrap(True)
            content_layout.addWidget(message_label)

        main_layout.addLayout(content_layout, 1)

        # 关闭按钮
        if self._closable:
            close_btn = QPushButton("×")
            close_btn.setFixedSize(20, 20)
            close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            close_btn.setStyleSheet("""
                QPushButton {
                    border: none;
                    background: transparent;
                    color: #8c8c8c;
                    font-size: 16px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    color: #595959;
                }
            """)
            close_btn.clicked.connect(self._start_fade_out)
            main_layout.addWidget(close_btn, 0, Qt.AlignmentFlag.AlignTop)

        # 设置透明度效果
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self._opacity_effect.setOpacity(1.0)
        self.setGraphicsEffect(self._opacity_effect)

    def _apply_style(self) -> None:
        """应用样式."""
        style = TOAST_STYLES[self._toast_type]
        self.setStyleSheet(f"""
            ToastNotification {{
                background-color: {style["background"]};
                border: 1px solid {style["border"]};
                border-radius: 8px;
            }}
        """)

    def _start_fade_out(self) -> None:
        """开始淡出动画."""
        if self._fade_animation is not None:
            return  # 已经在执行动画

        self._fade_animation = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._fade_animation.setDuration(300)
        self._fade_animation.setStartValue(1.0)
        self._fade_animation.setEndValue(0.0)
        self._fade_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._fade_animation.finished.connect(self._on_fade_finished)
        self._fade_animation.start()

    def _on_fade_finished(self) -> None:
        """淡出完成."""
        self.closed.emit()
        self.deleteLater()

    @classmethod
    def from_error(
        cls,
        error: UserFriendlyError,
        parent: Optional[QWidget] = None,
    ) -> "ToastNotification":
        """从 UserFriendlyError 创建通知.

        Args:
            error: 用户友好的错误对象
            parent: 父组件

        Returns:
            ToastNotification 实例
        """
        # 映射错误级别到通知类型
        severity_map = {
            ErrorSeverity.INFO: ToastType.INFO,
            ErrorSeverity.WARNING: ToastType.WARNING,
            ErrorSeverity.ERROR: ToastType.ERROR,
            ErrorSeverity.CRITICAL: ToastType.ERROR,
        }
        toast_type = severity_map.get(error.severity, ToastType.ERROR)

        # 错误通知显示更长时间
        duration = 6000 if error.severity in (ErrorSeverity.ERROR, ErrorSeverity.CRITICAL) else 4000

        return cls(
            title=error.title,
            message=error.message,
            toast_type=toast_type,
            duration=duration,
            parent=parent,
        )


class ToastManager(QWidget):
    """Toast 通知管理器.

    管理多个通知的显示和排列。

    Example:
        >>> manager = ToastManager(parent_window)
        >>> manager.show_success("操作成功", "已保存配置")
        >>> manager.show_error("操作失败", "网络连接错误")
    """

    MAX_VISIBLE = 5  # 最多同时显示的通知数

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """初始化管理器.

        Args:
            parent: 父组件（通常是主窗口）
        """
        super().__init__(parent)
        self._notifications: list[ToastNotification] = []
        self._pending: list[ToastNotification] = []

        # 设置为透明无边框
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
        )

        # 设置布局
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(8)
        self._layout.addStretch()

    def show_toast(
        self,
        title: str,
        message: str = "",
        toast_type: ToastType = ToastType.INFO,
        duration: int = 4000,
    ) -> ToastNotification:
        """显示通知.

        Args:
            title: 标题
            message: 内容
            toast_type: 类型
            duration: 显示时长

        Returns:
            创建的通知组件
        """
        toast = ToastNotification(
            title=title,
            message=message,
            toast_type=toast_type,
            duration=duration,
            parent=self,
        )

        if len(self._notifications) >= self.MAX_VISIBLE:
            # 队列等待
            self._pending.append(toast)
        else:
            self._add_toast(toast)

        return toast

    def show_success(self, title: str, message: str = "") -> ToastNotification:
        """显示成功通知."""
        return self.show_toast(title, message, ToastType.SUCCESS)

    def show_warning(self, title: str, message: str = "") -> ToastNotification:
        """显示警告通知."""
        return self.show_toast(title, message, ToastType.WARNING)

    def show_error(self, title: str, message: str = "") -> ToastNotification:
        """显示错误通知."""
        return self.show_toast(title, message, ToastType.ERROR, duration=6000)

    def show_info(self, title: str, message: str = "") -> ToastNotification:
        """显示信息通知."""
        return self.show_toast(title, message, ToastType.INFO)

    def show_user_error(self, error: UserFriendlyError) -> ToastNotification:
        """显示用户友好的错误通知.

        Args:
            error: UserFriendlyError 对象

        Returns:
            创建的通知组件
        """
        toast = ToastNotification.from_error(error, parent=self)

        if len(self._notifications) >= self.MAX_VISIBLE:
            self._pending.append(toast)
        else:
            self._add_toast(toast)

        return toast

    def _add_toast(self, toast: ToastNotification) -> None:
        """添加通知到显示区域."""
        toast.closed.connect(lambda: self._remove_toast(toast))
        self._notifications.append(toast)
        self._layout.insertWidget(self._layout.count() - 1, toast)
        self._update_position()
        self.show()
        self.raise_()

    def _remove_toast(self, toast: ToastNotification) -> None:
        """移除通知."""
        if toast in self._notifications:
            self._notifications.remove(toast)
            self._layout.removeWidget(toast)

        # 检查是否有等待的通知
        if self._pending and len(self._notifications) < self.MAX_VISIBLE:
            next_toast = self._pending.pop(0)
            self._add_toast(next_toast)

        # 没有通知时隐藏
        if not self._notifications:
            self.hide()
        else:
            self._update_position()

    def _update_position(self) -> None:
        """更新位置到父窗口右上角."""
        if self.parent() is None:
            return

        parent = self.parent()
        if hasattr(parent, "geometry"):
            parent_rect = parent.geometry()
            # 计算所需高度
            total_height = sum(t.sizeHint().height() for t in self._notifications)
            total_height += 8 * (len(self._notifications) - 1) if self._notifications else 0
            total_height += 20  # 边距

            self.setGeometry(
                parent_rect.width() - 380,  # 右侧留 20px 边距
                20,  # 顶部留 20px 边距
                360,
                max(total_height, 60),
            )

    def clear_all(self) -> None:
        """清除所有通知."""
        for toast in list(self._notifications):
            toast._start_fade_out()
        self._pending.clear()


# 全局 Toast 管理器
_toast_manager: Optional[ToastManager] = None


def get_toast_manager(parent: Optional[QWidget] = None) -> ToastManager:
    """获取全局 Toast 管理器.

    Args:
        parent: 父组件（仅首次调用有效）

    Returns:
        ToastManager 实例
    """
    global _toast_manager
    if _toast_manager is None:
        _toast_manager = ToastManager(parent)
    return _toast_manager


def show_toast(
    title: str,
    message: str = "",
    toast_type: ToastType = ToastType.INFO,
) -> Optional[ToastNotification]:
    """快捷显示通知.

    Args:
        title: 标题
        message: 内容
        toast_type: 类型

    Returns:
        通知组件，如果管理器未初始化则返回 None
    """
    if _toast_manager is None:
        return None
    return _toast_manager.show_toast(title, message, toast_type)


def show_success(title: str, message: str = "") -> Optional[ToastNotification]:
    """快捷显示成功通知."""
    if _toast_manager is None:
        return None
    return _toast_manager.show_success(title, message)


def show_warning(title: str, message: str = "") -> Optional[ToastNotification]:
    """快捷显示警告通知."""
    if _toast_manager is None:
        return None
    return _toast_manager.show_warning(title, message)


def show_error(title: str, message: str = "") -> Optional[ToastNotification]:
    """快捷显示错误通知."""
    if _toast_manager is None:
        return None
    return _toast_manager.show_error(title, message)


def show_info(title: str, message: str = "") -> Optional[ToastNotification]:
    """快捷显示信息通知."""
    if _toast_manager is None:
        return None
    return _toast_manager.show_info(title, message)
