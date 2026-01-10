"""版本检测服务.

提供 GitHub Release 版本检测功能，支持后台线程异步检测。
"""

from __future__ import annotations

import json
import re
import urllib.request
import urllib.error
from dataclasses import dataclass
from typing import Optional

from PyQt6.QtCore import QThread, pyqtSignal

from src.utils.constants import (
    APP_VERSION,
    GITHUB_API_LATEST_RELEASE,
    GITHUB_RELEASES_URL,
    VERSION_CHECK_TIMEOUT,
)
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class VersionInfo:
    """版本信息数据类."""

    version: str
    tag_name: str
    release_url: str
    release_notes: str
    published_at: str


class VersionChecker(QThread):
    """版本检测线程.

    在后台线程中检测 GitHub 最新版本，避免阻塞 UI。

    Signals:
        update_available: 发现新版本信号，参数为 VersionInfo
        check_finished: 检测完成信号，参数为是否有更新
        check_failed: 检测失败信号，参数为错误信息
    """

    update_available = pyqtSignal(object)  # VersionInfo
    check_finished = pyqtSignal(bool)  # has_update
    check_failed = pyqtSignal(str)  # error_message

    def __init__(self, parent=None) -> None:
        """初始化版本检测线程."""
        super().__init__(parent)
        self._current_version = APP_VERSION

    def run(self) -> None:
        """执行版本检测."""
        try:
            logger.info("开始检测版本更新...")
            latest = self._fetch_latest_release()

            if latest is None:
                self.check_finished.emit(False)
                return

            has_update = self._compare_versions(
                self._current_version, latest.version
            )

            if has_update:
                logger.info(
                    f"发现新版本: {latest.version} (当前: {self._current_version})"
                )
                self.update_available.emit(latest)
            else:
                logger.info(f"当前已是最新版本: {self._current_version}")

            self.check_finished.emit(has_update)

        except Exception as e:
            error_msg = f"版本检测失败: {e}"
            logger.warning(error_msg)
            self.check_failed.emit(error_msg)

    def _fetch_latest_release(self) -> Optional[VersionInfo]:
        """获取 GitHub 最新 Release 信息.

        Returns:
            VersionInfo 或 None（获取失败时）
        """
        try:
            request = urllib.request.Request(
                GITHUB_API_LATEST_RELEASE,
                headers={
                    "Accept": "application/vnd.github.v3+json",
                    "User-Agent": "ecommerce-image-ai-processor",
                },
            )

            with urllib.request.urlopen(
                request, timeout=VERSION_CHECK_TIMEOUT
            ) as response:
                data = json.loads(response.read().decode("utf-8"))

            tag_name = data.get("tag_name", "")
            # 移除 'v' 前缀
            version = tag_name.lstrip("v")

            return VersionInfo(
                version=version,
                tag_name=tag_name,
                release_url=data.get("html_url", GITHUB_RELEASES_URL),
                release_notes=data.get("body", ""),
                published_at=data.get("published_at", ""),
            )

        except urllib.error.URLError as e:
            logger.warning(f"网络请求失败: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.warning(f"JSON 解析失败: {e}")
            return None
        except Exception as e:
            logger.warning(f"获取版本信息失败: {e}")
            return None

    def _compare_versions(self, current: str, latest: str) -> bool:
        """比较版本号，判断是否有更新.

        支持语义化版本格式，如 1.0.2、1.0.2-preview、1.0.2-beta.1

        Args:
            current: 当前版本号
            latest: 最新版本号

        Returns:
            True 表示有新版本可用
        """
        try:
            current_parts = self._parse_version(current)
            latest_parts = self._parse_version(latest)

            # 比较主版本号
            for i in range(3):
                current_num = current_parts["numbers"][i] if i < len(current_parts["numbers"]) else 0
                latest_num = latest_parts["numbers"][i] if i < len(latest_parts["numbers"]) else 0

                if latest_num > current_num:
                    return True
                elif latest_num < current_num:
                    return False

            # 主版本号相同，比较预发布标识
            # 有预发布标识的版本低于无预发布标识的版本
            current_pre = current_parts["prerelease"]
            latest_pre = latest_parts["prerelease"]

            if current_pre and not latest_pre:
                # 当前是预发布版，最新是正式版
                return True
            elif not current_pre and latest_pre:
                # 当前是正式版，最新是预发布版
                return False
            elif current_pre and latest_pre:
                # 都是预发布版，按字符串比较
                return latest_pre > current_pre

            return False

        except Exception as e:
            logger.warning(f"版本比较失败: {e}")
            # 比较失败时，保守处理，不提示更新
            return False

    def _parse_version(self, version: str) -> dict:
        """解析版本号.

        Args:
            version: 版本字符串，如 "1.0.2-preview"

        Returns:
            包含 numbers 和 prerelease 的字典
        """
        # 分离版本号和预发布标识
        match = re.match(r"^(\d+(?:\.\d+)*)(?:-(.+))?$", version)
        if not match:
            return {"numbers": [0, 0, 0], "prerelease": ""}

        number_part = match.group(1)
        prerelease = match.group(2) or ""

        numbers = [int(n) for n in number_part.split(".")]
        # 补齐到3位
        while len(numbers) < 3:
            numbers.append(0)

        return {"numbers": numbers, "prerelease": prerelease}


def check_for_updates(
    on_update: Optional[callable] = None,
    on_finished: Optional[callable] = None,
    on_failed: Optional[callable] = None,
    parent=None,
) -> VersionChecker:
    """创建并启动版本检测线程.

    Args:
        on_update: 发现新版本时的回调，参数为 VersionInfo
        on_finished: 检测完成时的回调，参数为是否有更新
        on_failed: 检测失败时的回调，参数为错误信息
        parent: 父对象

    Returns:
        VersionChecker 线程实例
    """
    checker = VersionChecker(parent)

    if on_update:
        checker.update_available.connect(on_update)
    if on_finished:
        checker.check_finished.connect(on_finished)
    if on_failed:
        checker.check_failed.connect(on_failed)

    checker.start()
    return checker
