"""模板管理服务.

提供模板的持久化存储功能，包括保存、加载、列表管理和预设模板。

Features:
    - 保存模板到本地文件（.template.json）
    - 从文件加载模板
    - 模板列表管理
    - 模板重命名和删除
    - 预设模板
"""

from __future__ import annotations

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from src.models.template_config import (
    TemplateConfig,
    TextLayer,
    ShapeLayer,
    ImageLayer,
    LayerType,
    TextAlign,
)
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


# ===================
# 常量定义
# ===================

# 模板文件扩展名
TEMPLATE_EXTENSION = ".template.json"

# 默认模板目录名
DEFAULT_TEMPLATES_DIR = "templates"

# 预设模板目录名
PRESET_TEMPLATES_DIR = "presets"


# ===================
# 模板元数据
# ===================


class TemplateMetadata:
    """模板元数据.

    用于模板列表显示，不包含完整图层数据。
    """

    def __init__(
        self,
        id: str,
        name: str,
        description: str = "",
        canvas_width: int = 800,
        canvas_height: int = 800,
        layer_count: int = 0,
        is_preset: bool = False,
        file_path: str = "",
        created_at: Optional[datetime] = None,
        modified_at: Optional[datetime] = None,
    ) -> None:
        """初始化模板元数据."""
        self.id = id
        self.name = name
        self.description = description
        self.canvas_width = canvas_width
        self.canvas_height = canvas_height
        self.layer_count = layer_count
        self.is_preset = is_preset
        self.file_path = file_path
        self.created_at = created_at or datetime.now()
        self.modified_at = modified_at or datetime.now()

    @classmethod
    def from_template(cls, template: TemplateConfig, file_path: str = "") -> "TemplateMetadata":
        """从模板创建元数据."""
        return cls(
            id=template.id,
            name=template.name,
            description=template.description,
            canvas_width=template.canvas_width,
            canvas_height=template.canvas_height,
            layer_count=template.layer_count,
            is_preset=template.is_preset,
            file_path=file_path,
        )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "canvas_width": self.canvas_width,
            "canvas_height": self.canvas_height,
            "layer_count": self.layer_count,
            "is_preset": self.is_preset,
            "file_path": self.file_path,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "modified_at": self.modified_at.isoformat() if self.modified_at else None,
        }


# ===================
# 模板管理器
# ===================


class TemplateManager:
    """模板管理器.

    管理模板的保存、加载、列表和预设。

    Example:
        >>> manager = TemplateManager()
        >>> template = TemplateConfig.create("我的模板")
        >>> manager.save_template(template)
        >>> loaded = manager.load_template(template.id)
    """

    def __init__(self, templates_dir: Optional[str] = None) -> None:
        """初始化模板管理器.

        Args:
            templates_dir: 模板存储目录，默认为用户目录下的 templates
        """
        if templates_dir:
            self._templates_dir = Path(templates_dir)
        else:
            # 默认使用用户目录
            self._templates_dir = Path.home() / ".ecommerce-image-ai" / DEFAULT_TEMPLATES_DIR

        self._presets_dir = self._templates_dir / PRESET_TEMPLATES_DIR

        # 确保目录存在
        self._ensure_directories()

        # 初始化预设模板
        self._init_presets()

    @property
    def templates_dir(self) -> Path:
        """模板目录."""
        return self._templates_dir

    @property
    def presets_dir(self) -> Path:
        """预设模板目录."""
        return self._presets_dir

    def _ensure_directories(self) -> None:
        """确保目录存在."""
        self._templates_dir.mkdir(parents=True, exist_ok=True)
        self._presets_dir.mkdir(parents=True, exist_ok=True)

    def _init_presets(self) -> None:
        """初始化预设模板."""
        # 检查是否已有预设模板
        existing = list(self._presets_dir.glob(f"*{TEMPLATE_EXTENSION}"))
        if existing:
            return

        # 创建预设模板
        presets = create_preset_templates()
        for preset in presets:
            self._save_to_file(preset, self._presets_dir)
            logger.info(f"创建预设模板: {preset.name}")

    def _get_template_path(self, template_id: str, is_preset: bool = False) -> Path:
        """获取模板文件路径."""
        directory = self._presets_dir if is_preset else self._templates_dir
        return directory / f"{template_id}{TEMPLATE_EXTENSION}"

    def _save_to_file(self, template: TemplateConfig, directory: Path) -> Path:
        """保存模板到指定目录."""
        file_path = directory / f"{template.id}{TEMPLATE_EXTENSION}"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(template.to_json())
        return file_path

    def _load_from_file(self, file_path: Path) -> Optional[TemplateConfig]:
        """从文件加载模板."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                json_str = f.read()
            return TemplateConfig.from_json(json_str)
        except Exception as e:
            logger.error(f"加载模板失败: {file_path}, 错误: {e}")
            return None

    # ========================
    # 公共方法
    # ========================

    def save_template(self, template: TemplateConfig) -> bool:
        """保存模板.

        Args:
            template: 模板配置

        Returns:
            是否保存成功
        """
        try:
            # 预设模板不能覆盖
            if template.is_preset:
                logger.warning("预设模板不能被覆盖")
                return False

            self._save_to_file(template, self._templates_dir)
            logger.info(f"模板已保存: {template.name}")
            return True
        except Exception as e:
            logger.error(f"保存模板失败: {e}")
            return False

    def save_template_as(
        self,
        template: TemplateConfig,
        new_name: str,
    ) -> Optional[TemplateConfig]:
        """另存为新模板.

        Args:
            template: 原模板
            new_name: 新名称

        Returns:
            新模板，失败返回 None
        """
        try:
            # 创建副本
            new_template = TemplateConfig.from_json(template.to_json())
            # 生成新 ID
            from src.models.template_config import generate_layer_id
            new_template.id = generate_layer_id()
            new_template.name = new_name
            new_template.is_preset = False

            self._save_to_file(new_template, self._templates_dir)
            logger.info(f"模板另存为: {new_name}")
            return new_template
        except Exception as e:
            logger.error(f"另存模板失败: {e}")
            return None

    def load_template(self, template_id: str) -> Optional[TemplateConfig]:
        """加载模板.

        Args:
            template_id: 模板 ID

        Returns:
            模板配置，不存在返回 None
        """
        # 先从用户模板查找
        path = self._get_template_path(template_id, is_preset=False)
        if path.exists():
            return self._load_from_file(path)

        # 再从预设模板查找
        path = self._get_template_path(template_id, is_preset=True)
        if path.exists():
            return self._load_from_file(path)

        logger.warning(f"模板不存在: {template_id}")
        return None

    def load_template_from_file(self, file_path: str) -> Optional[TemplateConfig]:
        """从指定文件加载模板.

        Args:
            file_path: 文件路径

        Returns:
            模板配置
        """
        return self._load_from_file(Path(file_path))

    def delete_template(self, template_id: str) -> bool:
        """删除模板.

        Args:
            template_id: 模板 ID

        Returns:
            是否删除成功
        """
        # 不能删除预设模板
        preset_path = self._get_template_path(template_id, is_preset=True)
        if preset_path.exists():
            logger.warning("不能删除预设模板")
            return False

        # 删除用户模板
        path = self._get_template_path(template_id, is_preset=False)
        if path.exists():
            try:
                path.unlink()
                logger.info(f"模板已删除: {template_id}")
                return True
            except Exception as e:
                logger.error(f"删除模板失败: {e}")
                return False

        return False

    def rename_template(self, template_id: str, new_name: str) -> bool:
        """重命名模板.

        Args:
            template_id: 模板 ID
            new_name: 新名称

        Returns:
            是否重命名成功
        """
        template = self.load_template(template_id)
        if not template:
            return False

        if template.is_preset:
            logger.warning("不能重命名预设模板")
            return False

        template.name = new_name
        return self.save_template(template)

    def get_template_list(self, include_presets: bool = True) -> List[TemplateMetadata]:
        """获取模板列表.

        Args:
            include_presets: 是否包含预设模板

        Returns:
            模板元数据列表
        """
        result: List[TemplateMetadata] = []

        # 用户模板
        for file_path in self._templates_dir.glob(f"*{TEMPLATE_EXTENSION}"):
            if file_path.parent == self._presets_dir:
                continue
            template = self._load_from_file(file_path)
            if template:
                metadata = TemplateMetadata.from_template(template, str(file_path))
                # 获取文件修改时间
                stat = file_path.stat()
                metadata.modified_at = datetime.fromtimestamp(stat.st_mtime)
                result.append(metadata)

        # 预设模板
        if include_presets:
            for file_path in self._presets_dir.glob(f"*{TEMPLATE_EXTENSION}"):
                template = self._load_from_file(file_path)
                if template:
                    metadata = TemplateMetadata.from_template(template, str(file_path))
                    result.append(metadata)

        # 按修改时间排序（最新的在前）
        result.sort(key=lambda m: m.modified_at or datetime.min, reverse=True)

        return result

    def get_preset_templates(self) -> List[TemplateMetadata]:
        """获取预设模板列表."""
        result: List[TemplateMetadata] = []
        for file_path in self._presets_dir.glob(f"*{TEMPLATE_EXTENSION}"):
            template = self._load_from_file(file_path)
            if template:
                result.append(TemplateMetadata.from_template(template, str(file_path)))
        return result

    def duplicate_template(self, template_id: str) -> Optional[TemplateConfig]:
        """复制模板.

        Args:
            template_id: 原模板 ID

        Returns:
            新模板
        """
        template = self.load_template(template_id)
        if not template:
            return None

        return self.save_template_as(template, f"{template.name} - 副本")

    def export_template(self, template_id: str, export_path: str) -> bool:
        """导出模板到指定路径.

        Args:
            template_id: 模板 ID
            export_path: 导出路径

        Returns:
            是否导出成功
        """
        template = self.load_template(template_id)
        if not template:
            return False

        try:
            with open(export_path, "w", encoding="utf-8") as f:
                f.write(template.to_json())
            logger.info(f"模板已导出: {export_path}")
            return True
        except Exception as e:
            logger.error(f"导出模板失败: {e}")
            return False

    def import_template(self, import_path: str) -> Optional[TemplateConfig]:
        """从指定路径导入模板.

        Args:
            import_path: 导入路径

        Returns:
            导入的模板
        """
        template = self.load_template_from_file(import_path)
        if not template:
            return None

        # 生成新 ID 避免冲突
        from src.models.template_config import generate_layer_id
        template.id = generate_layer_id()
        template.is_preset = False

        if self.save_template(template):
            return template
        return None


# ===================
# 预设模板创建
# ===================


def create_preset_templates() -> List[TemplateConfig]:
    """创建预设模板集合."""
    presets = []

    # 1. 电商主图模板 - 800x800
    main_image = TemplateConfig.create(
        name="电商主图",
        width=800,
        height=800,
        description="适用于淘宝、京东等平台的商品主图",
    )
    main_image.is_preset = True
    main_image.background_color = (255, 255, 255)

    # 添加标题区域背景
    title_bg = ShapeLayer.create_rectangle(
        x=0, y=0, width=800, height=120,
        fill_color=(255, 0, 0),
        name="标题背景",
    )
    title_bg.fill_opacity = 90
    main_image.add_layer(title_bg)

    # 添加标题文字
    title_text = TextLayer.create(
        content="促销标题",
        x=50, y=30,
        font_size=48,
        font_color=(255, 255, 255),
        name="标题",
    )
    title_text.bold = True
    main_image.add_layer(title_text)

    # 添加价格标签
    price_bg = ShapeLayer.create_rectangle(
        x=550, y=650, width=200, height=100,
        fill_color=(255, 200, 0),
        corner_radius=10,
        name="价格背景",
    )
    main_image.add_layer(price_bg)

    price_text = TextLayer.create(
        content="¥99",
        x=580, y=670,
        font_size=56,
        font_color=(255, 0, 0),
        name="价格",
    )
    price_text.bold = True
    main_image.add_layer(price_text)

    presets.append(main_image)

    # 2. 促销海报模板 - 750x1334 (手机屏幕比例)
    promo_poster = TemplateConfig.create(
        name="促销海报",
        width=750,
        height=1334,
        description="适用于手机端展示的促销海报",
    )
    promo_poster.is_preset = True
    promo_poster.background_color = (240, 240, 240)

    # 顶部横幅
    top_banner = ShapeLayer.create_rectangle(
        x=0, y=0, width=750, height=200,
        fill_color=(231, 76, 60),
        name="顶部横幅",
    )
    promo_poster.add_layer(top_banner)

    banner_text = TextLayer.create(
        content="限时特惠",
        x=225, y=60,
        font_size=72,
        font_color=(255, 255, 255),
        name="横幅文字",
    )
    banner_text.bold = True
    promo_poster.add_layer(banner_text)

    # 产品区域背景
    product_area = ShapeLayer.create_rectangle(
        x=50, y=250, width=650, height=600,
        fill_color=(255, 255, 255),
        corner_radius=20,
        name="产品区域",
    )
    promo_poster.add_layer(product_area)

    # 底部信息区
    bottom_info = ShapeLayer.create_rectangle(
        x=0, y=1134, width=750, height=200,
        fill_color=(52, 73, 94),
        name="底部信息",
    )
    promo_poster.add_layer(bottom_info)

    contact_text = TextLayer.create(
        content="扫码了解详情",
        x=270, y=1200,
        font_size=32,
        font_color=(255, 255, 255),
        name="联系文字",
    )
    promo_poster.add_layer(contact_text)

    presets.append(promo_poster)

    # 3. 简约横幅模板 - 1200x300
    simple_banner = TemplateConfig.create(
        name="简约横幅",
        width=1200,
        height=300,
        description="适用于网站横幅广告",
    )
    simple_banner.is_preset = True
    simple_banner.background_color = (41, 128, 185)

    # 左侧装饰圆
    left_circle = ShapeLayer.create_ellipse(
        x=0, y=0, width=400, height=400,
        fill_color=(52, 152, 219),
        name="装饰圆",
    )
    left_circle.fill_opacity = 50
    simple_banner.add_layer(left_circle)

    # 主标题
    main_title = TextLayer.create(
        content="新品上市",
        x=400, y=80,
        font_size=64,
        font_color=(255, 255, 255),
        name="主标题",
    )
    main_title.bold = True
    simple_banner.add_layer(main_title)

    # 副标题
    sub_title = TextLayer.create(
        content="限时优惠，不容错过",
        x=400, y=170,
        font_size=28,
        font_color=(236, 240, 241),
        name="副标题",
    )
    simple_banner.add_layer(sub_title)

    # 按钮
    btn_bg = ShapeLayer.create_rectangle(
        x=950, y=110, width=180, height=80,
        fill_color=(231, 76, 60),
        corner_radius=40,
        name="按钮背景",
    )
    simple_banner.add_layer(btn_bg)

    btn_text = TextLayer.create(
        content="立即购买",
        x=975, y=130,
        font_size=28,
        font_color=(255, 255, 255),
        name="按钮文字",
    )
    simple_banner.add_layer(btn_text)

    presets.append(simple_banner)

    # 4. 空白模板 - 800x800
    blank = TemplateConfig.create(
        name="空白画布",
        width=800,
        height=800,
        description="从零开始创建你的设计",
    )
    blank.is_preset = True
    blank.background_color = (255, 255, 255)

    presets.append(blank)

    return presets
