"""核心业务逻辑模块."""

from src.core.composite_processor import (
    CompositeConfig,
    CompositeMode,
    CompositePosition,
    CompositeProcessor,
    SceneType,
    composite_product,
)
from src.core.result_validator import (
    ResultValidator,
    ValidationConfig,
    ValidationIssue,
    ValidationLevel,
    ValidationResult,
    ValidationStatus,
    validate_background_removal_result,
    validate_composite_result,
    validate_result,
)

__all__ = [
    # 合成处理器
    "CompositeConfig",
    "CompositeMode",
    "CompositePosition",
    "CompositeProcessor",
    "SceneType",
    "composite_product",
    # 结果验证器
    "ResultValidator",
    "ValidationConfig",
    "ValidationIssue",
    "ValidationLevel",
    "ValidationResult",
    "ValidationStatus",
    "validate_background_removal_result",
    "validate_composite_result",
    "validate_result",
]
