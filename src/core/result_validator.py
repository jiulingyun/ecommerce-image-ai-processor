"""AI 处理结果验证器模块.

提供 AI 处理结果的验证功能，确保输出质量符合要求。

Features:
    - 图片格式验证
    - 尺寸验证
    - 透明度检测
    - 质量评估
    - 边缘情况处理
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple

from PIL import Image

from src.utils.exceptions import ImageProcessError
from src.utils.image_utils import bytes_to_image, has_transparency
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class ValidationLevel(str, Enum):
    """验证级别枚举."""

    STRICT = "strict"  # 严格验证
    NORMAL = "normal"  # 正常验证
    LENIENT = "lenient"  # 宽松验证


class ValidationStatus(str, Enum):
    """验证状态枚举."""

    PASSED = "passed"  # 验证通过
    WARNING = "warning"  # 有警告但通过
    FAILED = "failed"  # 验证失败


@dataclass
class ValidationIssue:
    """验证问题."""

    code: str  # 问题代码
    message: str  # 问题描述
    severity: str  # 严重程度: error, warning, info
    suggestion: Optional[str] = None  # 修复建议


@dataclass
class ValidationResult:
    """验证结果."""

    status: ValidationStatus
    issues: List[ValidationIssue] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    @property
    def is_valid(self) -> bool:
        """是否验证通过."""
        return self.status != ValidationStatus.FAILED

    @property
    def has_warnings(self) -> bool:
        """是否有警告."""
        return any(issue.severity == "warning" for issue in self.issues)

    @property
    def error_messages(self) -> List[str]:
        """获取错误消息列表."""
        return [
            issue.message for issue in self.issues if issue.severity == "error"
        ]

    @property
    def warning_messages(self) -> List[str]:
        """获取警告消息列表."""
        return [
            issue.message for issue in self.issues if issue.severity == "warning"
        ]

    def add_issue(self, issue: ValidationIssue) -> None:
        """添加问题."""
        self.issues.append(issue)
        # 如果有错误，更新状态
        if issue.severity == "error" and self.status != ValidationStatus.FAILED:
            self.status = ValidationStatus.FAILED
        elif (
            issue.severity == "warning"
            and self.status == ValidationStatus.PASSED
        ):
            self.status = ValidationStatus.WARNING


@dataclass
class ValidationConfig:
    """验证配置."""

    level: ValidationLevel = ValidationLevel.NORMAL
    min_width: int = 100
    min_height: int = 100
    max_width: int = 8192
    max_height: int = 8192
    require_transparency: bool = False
    min_file_size: int = 1024  # 1KB
    max_file_size: int = 50 * 1024 * 1024  # 50MB
    allowed_formats: List[str] = field(
        default_factory=lambda: ["PNG", "JPEG", "WEBP"]
    )
    check_blank: bool = True
    blank_threshold: float = 0.95  # 空白像素占比阈值


class ResultValidator:
    """AI 处理结果验证器.

    验证 AI 处理后的图片是否符合质量要求。

    Attributes:
        config: 验证配置

    Example:
        >>> validator = ResultValidator()
        >>> result = validator.validate(image_bytes)
        >>> if result.is_valid:
        ...     print("验证通过")
    """

    def __init__(self, config: Optional[ValidationConfig] = None) -> None:
        """初始化验证器.

        Args:
            config: 验证配置
        """
        self.config = config or ValidationConfig()

    def validate(
        self,
        data: bytes | Image.Image,
        expected_size: Optional[Tuple[int, int]] = None,
        operation: str = "unknown",
    ) -> ValidationResult:
        """验证处理结果.

        Args:
            data: 图片数据（字节或 Image 对象）
            expected_size: 期望的尺寸 (宽, 高)
            operation: 操作类型（用于日志）

        Returns:
            验证结果
        """
        result = ValidationResult(status=ValidationStatus.PASSED)

        try:
            # 加载图片
            if isinstance(data, bytes):
                result.metadata["file_size"] = len(data)
                image = bytes_to_image(data)
            else:
                image = data

            result.metadata["width"] = image.width
            result.metadata["height"] = image.height
            result.metadata["format"] = image.format
            result.metadata["mode"] = image.mode

            # 执行各项验证
            self._validate_format(image, result)
            self._validate_size(image, result, expected_size)
            self._validate_file_size(data, result)
            self._validate_transparency(image, result)
            self._validate_content(image, result)

            logger.info(
                f"验证完成 [{operation}]: {result.status.value}, "
                f"问题数: {len(result.issues)}"
            )

        except Exception as e:
            logger.error(f"验证过程出错: {e}")
            result.add_issue(
                ValidationIssue(
                    code="VALIDATION_ERROR",
                    message=f"验证过程出错: {e}",
                    severity="error",
                )
            )

        return result

    def validate_background_removal(
        self,
        data: bytes | Image.Image,
    ) -> ValidationResult:
        """验证背景去除结果.

        Args:
            data: 处理后的图片数据

        Returns:
            验证结果
        """
        result = self.validate(data, operation="background_removal")

        # 额外检查透明通道
        if isinstance(data, bytes):
            image = bytes_to_image(data)
        else:
            image = data

        if image.mode != "RGBA":
            result.add_issue(
                ValidationIssue(
                    code="NO_ALPHA_CHANNEL",
                    message="背景去除结果应该包含透明通道 (RGBA)",
                    severity="warning",
                    suggestion="检查 AI 服务配置，确保输出包含 alpha 通道",
                )
            )

        # 检查透明像素比例
        if image.mode == "RGBA":
            transparency_ratio = self._calculate_transparency_ratio(image)
            result.metadata["transparency_ratio"] = transparency_ratio

            if transparency_ratio < 0.01:
                result.add_issue(
                    ValidationIssue(
                        code="LOW_TRANSPARENCY",
                        message="几乎没有透明像素，背景可能未被正确去除",
                        severity="warning",
                        suggestion="尝试使用不同的提示词或调整参数",
                    )
                )

        return result

    def validate_composite(
        self,
        data: bytes | Image.Image,
        background_size: Optional[Tuple[int, int]] = None,
    ) -> ValidationResult:
        """验证合成结果.

        Args:
            data: 合成后的图片数据
            background_size: 背景图尺寸

        Returns:
            验证结果
        """
        result = self.validate(
            data, expected_size=background_size, operation="composite"
        )

        if isinstance(data, bytes):
            image = bytes_to_image(data)
        else:
            image = data

        # 检查合成后的内容是否有变化
        if self.config.check_blank:
            variance = self._calculate_variance(image)
            result.metadata["color_variance"] = variance

            if variance < 100:  # 方差过低表示图像可能过于单一
                result.add_issue(
                    ValidationIssue(
                        code="LOW_VARIANCE",
                        message="图像颜色方差过低，可能合成效果不佳",
                        severity="warning",
                        suggestion="检查输入图片或调整合成参数",
                    )
                )

        return result

    def _validate_format(
        self,
        image: Image.Image,
        result: ValidationResult,
    ) -> None:
        """验证图片格式."""
        if image.format and image.format.upper() not in self.config.allowed_formats:
            if self.config.level == ValidationLevel.STRICT:
                result.add_issue(
                    ValidationIssue(
                        code="INVALID_FORMAT",
                        message=f"不支持的图片格式: {image.format}",
                        severity="error",
                    )
                )
            else:
                result.add_issue(
                    ValidationIssue(
                        code="UNEXPECTED_FORMAT",
                        message=f"非预期的图片格式: {image.format}",
                        severity="warning",
                    )
                )

    def _validate_size(
        self,
        image: Image.Image,
        result: ValidationResult,
        expected_size: Optional[Tuple[int, int]] = None,
    ) -> None:
        """验证图片尺寸."""
        width, height = image.size

        # 检查最小尺寸
        if width < self.config.min_width or height < self.config.min_height:
            result.add_issue(
                ValidationIssue(
                    code="SIZE_TOO_SMALL",
                    message=f"图片尺寸过小: {width}x{height}，"
                    f"最小要求 {self.config.min_width}x{self.config.min_height}",
                    severity="error" if self.config.level == ValidationLevel.STRICT else "warning",
                )
            )

        # 检查最大尺寸
        if width > self.config.max_width or height > self.config.max_height:
            result.add_issue(
                ValidationIssue(
                    code="SIZE_TOO_LARGE",
                    message=f"图片尺寸过大: {width}x{height}，"
                    f"最大允许 {self.config.max_width}x{self.config.max_height}",
                    severity="warning",
                )
            )

        # 检查期望尺寸
        if expected_size:
            exp_w, exp_h = expected_size
            # 允许 10% 的误差
            tolerance = 0.1
            if (
                abs(width - exp_w) / exp_w > tolerance
                or abs(height - exp_h) / exp_h > tolerance
            ):
                result.add_issue(
                    ValidationIssue(
                        code="SIZE_MISMATCH",
                        message=f"尺寸不匹配: 期望 {exp_w}x{exp_h}, 实际 {width}x{height}",
                        severity="info",
                    )
                )

    def _validate_file_size(
        self,
        data: bytes | Image.Image,
        result: ValidationResult,
    ) -> None:
        """验证文件大小."""
        if isinstance(data, bytes):
            size = len(data)

            if size < self.config.min_file_size:
                result.add_issue(
                    ValidationIssue(
                        code="FILE_TOO_SMALL",
                        message=f"文件过小: {size} bytes，可能是损坏的图片",
                        severity="warning",
                    )
                )

            if size > self.config.max_file_size:
                result.add_issue(
                    ValidationIssue(
                        code="FILE_TOO_LARGE",
                        message=f"文件过大: {size / 1024 / 1024:.1f} MB",
                        severity="warning",
                    )
                )

    def _validate_transparency(
        self,
        image: Image.Image,
        result: ValidationResult,
    ) -> None:
        """验证透明度."""
        if self.config.require_transparency and not has_transparency(image):
            result.add_issue(
                ValidationIssue(
                    code="NO_TRANSPARENCY",
                    message="图片缺少透明通道，但配置要求透明度",
                    severity="error" if self.config.level == ValidationLevel.STRICT else "warning",
                )
            )

    def _validate_content(
        self,
        image: Image.Image,
        result: ValidationResult,
    ) -> None:
        """验证图片内容."""
        if not self.config.check_blank:
            return

        # 检查是否为空白图片
        blank_ratio = self._calculate_blank_ratio(image)
        result.metadata["blank_ratio"] = blank_ratio

        if blank_ratio > self.config.blank_threshold:
            result.add_issue(
                ValidationIssue(
                    code="MOSTLY_BLANK",
                    message=f"图片大部分为空白: {blank_ratio:.1%}",
                    severity="warning",
                    suggestion="AI 可能未能正确处理图片，建议重试",
                )
            )

    def _calculate_blank_ratio(self, image: Image.Image) -> float:
        """计算空白像素比例."""
        try:
            # 转换为 RGBA
            if image.mode != "RGBA":
                img = image.convert("RGBA")
            else:
                img = image

            pixels = list(img.getdata())
            total = len(pixels)

            # 统计"空白"像素（透明或纯白）
            blank_count = 0
            for pixel in pixels:
                r, g, b, a = pixel
                if a < 10 or (r > 250 and g > 250 and b > 250):
                    blank_count += 1

            return blank_count / total if total > 0 else 0

        except Exception as e:
            logger.warning(f"计算空白比例失败: {e}")
            return 0

    def _calculate_transparency_ratio(self, image: Image.Image) -> float:
        """计算透明像素比例."""
        try:
            if image.mode != "RGBA":
                return 0

            pixels = list(image.getdata())
            total = len(pixels)
            transparent = sum(1 for p in pixels if p[3] < 128)

            return transparent / total if total > 0 else 0

        except Exception as e:
            logger.warning(f"计算透明比例失败: {e}")
            return 0

    def _calculate_variance(self, image: Image.Image) -> float:
        """计算图像颜色方差."""
        try:
            # 转换为 RGB
            if image.mode != "RGB":
                img = image.convert("RGB")
            else:
                img = image

            # 计算统计信息
            import statistics

            pixels = list(img.getdata())
            if not pixels:
                return 0

            # 计算亮度方差
            luminance = [
                0.299 * p[0] + 0.587 * p[1] + 0.114 * p[2] for p in pixels
            ]

            if len(luminance) < 2:
                return 0

            return statistics.variance(luminance)

        except Exception as e:
            logger.warning(f"计算方差失败: {e}")
            return 0


# 便捷验证函数
def validate_result(
    data: bytes | Image.Image,
    level: ValidationLevel = ValidationLevel.NORMAL,
) -> ValidationResult:
    """快速验证处理结果.

    Args:
        data: 图片数据
        level: 验证级别

    Returns:
        验证结果
    """
    config = ValidationConfig(level=level)
    validator = ResultValidator(config)
    return validator.validate(data)


def validate_background_removal_result(
    data: bytes | Image.Image,
) -> ValidationResult:
    """验证背景去除结果.

    Args:
        data: 处理后的图片数据

    Returns:
        验证结果
    """
    config = ValidationConfig(require_transparency=True)
    validator = ResultValidator(config)
    return validator.validate_background_removal(data)


def validate_composite_result(
    data: bytes | Image.Image,
    background_size: Optional[Tuple[int, int]] = None,
) -> ValidationResult:
    """验证合成结果.

    Args:
        data: 合成后的图片数据
        background_size: 背景图尺寸

    Returns:
        验证结果
    """
    validator = ResultValidator()
    return validator.validate_composite(data, background_size)
