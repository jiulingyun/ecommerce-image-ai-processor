"""TemplateManager 单元测试."""

import pytest
import tempfile
import shutil
from pathlib import Path

from src.models.template_config import (
    TemplateConfig,
    TextLayer,
    ShapeLayer,
)
from src.services.template_manager import (
    TemplateManager,
    TemplateMetadata,
    create_preset_templates,
    TEMPLATE_EXTENSION,
)


@pytest.fixture
def temp_dir():
    """创建临时目录."""
    temp = tempfile.mkdtemp()
    yield temp
    shutil.rmtree(temp, ignore_errors=True)


@pytest.fixture
def manager(temp_dir):
    """创建模板管理器."""
    return TemplateManager(templates_dir=temp_dir)


# ===================
# TemplateMetadata 测试
# ===================


class TestTemplateMetadata:
    """TemplateMetadata 测试类."""

    def test_from_template(self):
        """测试从模板创建元数据."""
        template = TemplateConfig.create("测试模板", width=1000, height=800)
        template.description = "测试描述"
        template.add_layer(TextLayer.create("Hello"))

        metadata = TemplateMetadata.from_template(template, "/path/to/file")

        assert metadata.id == template.id
        assert metadata.name == "测试模板"
        assert metadata.description == "测试描述"
        assert metadata.canvas_width == 1000
        assert metadata.canvas_height == 800
        assert metadata.layer_count == 1
        assert metadata.file_path == "/path/to/file"

    def test_to_dict(self):
        """测试转换为字典."""
        template = TemplateConfig.create("测试")
        metadata = TemplateMetadata.from_template(template)

        data = metadata.to_dict()

        assert data["id"] == template.id
        assert data["name"] == "测试"
        assert "created_at" in data
        assert "modified_at" in data


# ===================
# TemplateManager 测试
# ===================


class TestTemplateManager:
    """TemplateManager 测试类."""

    def test_create_manager(self, temp_dir):
        """测试创建管理器."""
        manager = TemplateManager(templates_dir=temp_dir)

        assert manager.templates_dir == Path(temp_dir)
        assert manager.presets_dir == Path(temp_dir) / "presets"

    def test_presets_initialized(self, manager):
        """测试预设模板初始化."""
        presets = manager.get_preset_templates()

        # 应该有预设模板
        assert len(presets) >= 1

    def test_save_template(self, manager):
        """测试保存模板."""
        template = TemplateConfig.create("我的模板")

        result = manager.save_template(template)

        assert result is True
        # 验证文件存在
        file_path = manager.templates_dir / f"{template.id}{TEMPLATE_EXTENSION}"
        assert file_path.exists()

    def test_save_preset_template_fails(self, manager):
        """测试保存预设模板失败."""
        template = TemplateConfig.create("预设")
        template.is_preset = True

        result = manager.save_template(template)

        assert result is False

    def test_load_template(self, manager):
        """测试加载模板."""
        # 先保存
        template = TemplateConfig.create("测试加载")
        template.add_layer(TextLayer.create("Hello"))
        manager.save_template(template)

        # 再加载
        loaded = manager.load_template(template.id)

        assert loaded is not None
        assert loaded.name == "测试加载"
        assert loaded.layer_count == 1

    def test_load_nonexistent_template(self, manager):
        """测试加载不存在的模板."""
        loaded = manager.load_template("nonexistent-id")
        assert loaded is None

    def test_load_preset_template(self, manager):
        """测试加载预设模板."""
        presets = manager.get_preset_templates()
        assert len(presets) > 0

        preset = manager.load_template(presets[0].id)
        assert preset is not None
        assert preset.is_preset is True

    def test_delete_template(self, manager):
        """测试删除模板."""
        template = TemplateConfig.create("待删除")
        manager.save_template(template)

        result = manager.delete_template(template.id)

        assert result is True
        assert manager.load_template(template.id) is None

    def test_delete_preset_fails(self, manager):
        """测试删除预设模板失败."""
        presets = manager.get_preset_templates()
        assert len(presets) > 0

        result = manager.delete_template(presets[0].id)

        assert result is False

    def test_rename_template(self, manager):
        """测试重命名模板."""
        template = TemplateConfig.create("原名称")
        manager.save_template(template)

        result = manager.rename_template(template.id, "新名称")

        assert result is True
        loaded = manager.load_template(template.id)
        assert loaded.name == "新名称"

    def test_rename_preset_fails(self, manager):
        """测试重命名预设模板失败."""
        presets = manager.get_preset_templates()
        assert len(presets) > 0

        result = manager.rename_template(presets[0].id, "新名称")

        assert result is False

    def test_save_template_as(self, manager):
        """测试另存为."""
        template = TemplateConfig.create("原模板")
        template.add_layer(TextLayer.create("内容"))
        manager.save_template(template)

        new_template = manager.save_template_as(template, "新模板")

        assert new_template is not None
        assert new_template.name == "新模板"
        assert new_template.id != template.id
        assert new_template.layer_count == 1

    def test_duplicate_template(self, manager):
        """测试复制模板."""
        template = TemplateConfig.create("原模板")
        manager.save_template(template)

        duplicated = manager.duplicate_template(template.id)

        assert duplicated is not None
        assert duplicated.id != template.id
        assert "副本" in duplicated.name

    def test_get_template_list(self, manager):
        """测试获取模板列表."""
        # 创建一些模板
        for i in range(3):
            t = TemplateConfig.create(f"模板{i}")
            manager.save_template(t)

        # 获取列表
        templates = manager.get_template_list(include_presets=False)

        assert len(templates) >= 3

    def test_get_template_list_with_presets(self, manager):
        """测试获取包含预设的模板列表."""
        templates = manager.get_template_list(include_presets=True)

        # 应该包含预设模板
        preset_count = sum(1 for t in templates if t.is_preset)
        assert preset_count >= 1

    def test_export_template(self, manager, temp_dir):
        """测试导出模板."""
        template = TemplateConfig.create("导出测试")
        manager.save_template(template)

        export_path = Path(temp_dir) / "exported.template.json"
        result = manager.export_template(template.id, str(export_path))

        assert result is True
        assert export_path.exists()

    def test_import_template(self, manager, temp_dir):
        """测试导入模板."""
        # 先导出一个模板
        template = TemplateConfig.create("导入测试")
        export_path = Path(temp_dir) / "to_import.template.json"
        with open(export_path, "w", encoding="utf-8") as f:
            f.write(template.to_json())

        # 导入
        imported = manager.import_template(str(export_path))

        assert imported is not None
        assert imported.name == "导入测试"
        # ID 应该不同
        assert imported.id != template.id


# ===================
# 预设模板测试
# ===================


class TestPresetTemplates:
    """预设模板测试类."""

    def test_create_preset_templates(self):
        """测试创建预设模板."""
        presets = create_preset_templates()

        assert len(presets) >= 4

        # 检查每个预设
        for preset in presets:
            assert preset.is_preset is True
            assert preset.name
            assert preset.canvas_width > 0
            assert preset.canvas_height > 0

    def test_preset_has_layers(self):
        """测试预设模板包含图层."""
        presets = create_preset_templates()

        # 至少有一个预设应该包含图层
        has_layers = any(p.layer_count > 0 for p in presets)
        assert has_layers


# ===================
# 集成测试
# ===================


class TestTemplateManagerIntegration:
    """模板管理器集成测试."""

    def test_full_workflow(self, manager):
        """测试完整工作流程."""
        # 1. 创建模板
        template = TemplateConfig.create("工作流测试")
        template.add_layer(TextLayer.create("标题"))
        template.add_layer(ShapeLayer.create_rectangle(width=100, height=50))

        # 2. 保存
        assert manager.save_template(template) is True

        # 3. 加载
        loaded = manager.load_template(template.id)
        assert loaded.name == "工作流测试"
        assert loaded.layer_count == 2

        # 4. 重命名
        manager.rename_template(template.id, "新名称")
        loaded = manager.load_template(template.id)
        assert loaded.name == "新名称"

        # 5. 复制
        duplicated = manager.duplicate_template(template.id)
        assert duplicated is not None

        # 6. 列表
        templates = manager.get_template_list(include_presets=False)
        assert len(templates) >= 2

        # 7. 删除
        manager.delete_template(duplicated.id)
        assert manager.load_template(duplicated.id) is None

    def test_preset_workflow(self, manager):
        """测试预设模板工作流程."""
        # 获取预设
        presets = manager.get_preset_templates()
        assert len(presets) > 0

        # 加载预设
        preset = manager.load_template(presets[0].id)
        assert preset is not None
        assert preset.is_preset is True

        # 基于预设创建新模板
        new_template = manager.save_template_as(preset, "我的版本")
        assert new_template is not None
        assert new_template.is_preset is False

        # 新模板应该可以编辑
        new_template.name = "修改后的名称"
        manager.save_template(new_template)

        loaded = manager.load_template(new_template.id)
        assert loaded.name == "修改后的名称"
