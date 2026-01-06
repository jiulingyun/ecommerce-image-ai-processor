"""主题管理器.

支持浅色和暗色主题，并可以自动跟随系统主题。
"""

from __future__ import annotations

import subprocess
from enum import Enum
from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QObject, pyqtSignal

from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class Theme(Enum):
    """主题枚举."""
    LIGHT = "light"
    DARK = "dark"
    AUTO = "auto"  # 跟随系统


class ThemeManager(QObject):
    """主题管理器.
    
    负责加载和切换应用主题，支持：
    - 浅色模式
    - 暗色模式
    - 自动跟随系统主题
    
    Signals:
        theme_changed: 主题改变信号，参数为新的主题
    """
    
    theme_changed = pyqtSignal(Theme)
    
    def __init__(self, parent: Optional[QObject] = None) -> None:
        """初始化主题管理器.
        
        Args:
            parent: 父对象
        """
        super().__init__(parent)
        self._current_theme = Theme.DARK  # 默认暗色
        self._resources_dir = Path(__file__).parent / "resources"
        
    @property
    def current_theme(self) -> Theme:
        """当前主题."""
        return self._current_theme
    
    def detect_system_theme(self) -> Theme:
        """检测系统主题.
        
        Returns:
            系统当前主题 (LIGHT 或 DARK)
        """
        try:
            import platform
            system = platform.system()
            
            if system == "Darwin":  # macOS
                # 使用 defaults 命令检测系统主题
                result = subprocess.run(
                    ["defaults", "read", "-g", "AppleInterfaceStyle"],
                    capture_output=True,
                    text=True
                )
                # 如果返回 "Dark"，则是暗色模式；否则是浅色模式
                is_dark = result.returncode == 0 and "Dark" in result.stdout
                return Theme.DARK if is_dark else Theme.LIGHT
                
            elif system == "Windows":
                # Windows 10/11 注册表检测
                try:
                    import winreg
                    key = winreg.OpenKey(
                        winreg.HKEY_CURRENT_USER,
                        r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
                    )
                    value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
                    winreg.CloseKey(key)
                    return Theme.LIGHT if value == 1 else Theme.DARK
                except Exception:
                    pass
                    
            else:  # Linux
                # 尝试检测 GTK 主题
                try:
                    result = subprocess.run(
                        ["gsettings", "get", "org.gnome.desktop.interface", "gtk-theme"],
                        capture_output=True,
                        text=True,
                        timeout=1
                    )
                    if result.returncode == 0:
                        theme_name = result.stdout.strip().lower()
                        is_dark = "dark" in theme_name
                        return Theme.DARK if is_dark else Theme.LIGHT
                except Exception:
                    pass
                    
        except Exception as e:
            logger.warning(f"检测系统主题失败: {e}")
        
        # 默认返回浅色模式
        return Theme.LIGHT
    
    def load_stylesheet(self, theme: Theme) -> str:
        """加载主题样式表.
        
        Args:
            theme: 要加载的主题
            
        Returns:
            样式表内容
        """
        if theme == Theme.AUTO:
            theme = self.detect_system_theme()
        
        # 确定样式文件名
        if theme == Theme.LIGHT:
            filename = "styles_light.qss"
        else:
            filename = "styles_dark.qss"
        
        style_path = self._resources_dir / filename
        
        try:
            if style_path.exists():
                content = style_path.read_text(encoding="utf-8")
                logger.info(f"已加载 {theme.value} 主题样式")
                return content
            else:
                logger.warning(f"样式文件不存在: {style_path}")
                return ""
        except Exception as e:
            logger.error(f"加载样式表失败: {e}")
            return ""
    
    def apply_theme(self, theme: Theme, app: Optional[QApplication] = None) -> None:
        """应用主题.
        
        Args:
            theme: 要应用的主题
            app: QApplication 实例，如果为 None 则使用 QApplication.instance()
        """
        if app is None:
            app = QApplication.instance()
        
        if app is None:
            logger.error("无法获取 QApplication 实例")
            return
        
        # 如果是 AUTO 模式，检测系统主题
        actual_theme = theme
        if theme == Theme.AUTO:
            actual_theme = self.detect_system_theme()
            logger.info(f"自动检测到系统主题: {actual_theme.value}")
        
        # 加载并应用样式表
        stylesheet = self.load_stylesheet(actual_theme)
        app.setStyleSheet(stylesheet)
        
        # 更新当前主题
        old_theme = self._current_theme
        self._current_theme = actual_theme
        
        # 发送信号
        if old_theme != actual_theme:
            self.theme_changed.emit(actual_theme)
            logger.info(f"主题已切换: {old_theme.value} -> {actual_theme.value}")
    
    def toggle_theme(self) -> None:
        """切换主题（浅色 <-> 暗色）."""
        new_theme = Theme.LIGHT if self._current_theme == Theme.DARK else Theme.DARK
        self.apply_theme(new_theme)


# 全局主题管理器实例
_theme_manager: Optional[ThemeManager] = None


def get_theme_manager() -> ThemeManager:
    """获取全局主题管理器实例.
    
    Returns:
        ThemeManager 实例
    """
    global _theme_manager
    if _theme_manager is None:
        _theme_manager = ThemeManager()
    return _theme_manager


def apply_theme(theme: Theme = Theme.AUTO) -> None:
    """应用主题的快捷函数.
    
    Args:
        theme: 要应用的主题，默认 AUTO（跟随系统）
    """
    manager = get_theme_manager()
    manager.apply_theme(theme)
