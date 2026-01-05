"""撤销/重做系统单元测试.

Tests:
    - CommandStack: 命令栈管理
    - 各种命令: AddLayerCommand, RemoveLayerCommand, etc.
    - UndoRedoManager: 高级管理器
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from copy import deepcopy

from PyQt6.QtWidgets import QApplication

from src.models.template_config import (
    TemplateConfig,
    TextLayer,
    ShapeLayer,
    ImageLayer,
    LayerType,
)
from src.ui.widgets.template_editor.undo_redo import (
    Command,
    CommandStack,
    AddLayerCommand,
    RemoveLayerCommand,
    ModifyLayerCommand,
    MoveLayerCommand,
    ResizeLayerCommand,
    BatchCommand,
    ModifyCanvasCommand,
    UndoRedoManager,
)


# ===================
# Fixtures
# ===================


@pytest.fixture
def template() -> TemplateConfig:
    """创建测试模板."""
    return TemplateConfig(
        name="测试模板",
        canvas_width=800,
        canvas_height=600,
        background_color=(255, 255, 255),
    )


@pytest.fixture
def text_layer() -> TextLayer:
    """创建测试文字图层."""
    return TextLayer.create(
        content="测试文字",
        x=100,
        y=100,
    )


@pytest.fixture
def shape_layer() -> ShapeLayer:
    """创建测试形状图层."""
    return ShapeLayer.create_rectangle(
        x=200,
        y=200,
        width=150,
        height=100,
    )


@pytest.fixture
def mock_canvas(template: TemplateConfig) -> MagicMock:
    """创建模拟画布."""
    canvas = MagicMock()
    canvas.template = template
    canvas._scene = MagicMock()
    canvas._layer_items = {}

    # mock remove_layer
    def remove_layer(layer_id: str):
        if template.remove_layer(layer_id):
            canvas._layer_items.pop(layer_id, None)
            return True
        return False

    canvas.remove_layer = remove_layer

    # mock _add_layer_item
    def add_layer_item(layer):
        canvas._layer_items[layer.id] = MagicMock()

    canvas._add_layer_item = add_layer_item

    # mock update_layer
    canvas.update_layer = MagicMock()

    return canvas


@pytest.fixture
def command_stack() -> CommandStack:
    """创建命令栈."""
    return CommandStack()


# ===================
# CommandStack Tests
# ===================


class TestCommandStack:
    """命令栈测试."""

    def test_initial_state(self, command_stack: CommandStack) -> None:
        """测试初始状态."""
        assert not command_stack.can_undo
        assert not command_stack.can_redo
        assert command_stack.undo_description == ""
        assert command_stack.redo_description == ""

    def test_push_command(
        self,
        command_stack: CommandStack,
        mock_canvas: MagicMock,
        text_layer: TextLayer,
    ) -> None:
        """测试推入命令."""
        cmd = AddLayerCommand(mock_canvas, text_layer)
        command_stack.push(cmd)

        assert command_stack.can_undo
        assert not command_stack.can_redo
        assert "添加图层" in command_stack.undo_description

    def test_undo_command(
        self,
        command_stack: CommandStack,
        mock_canvas: MagicMock,
        text_layer: TextLayer,
    ) -> None:
        """测试撤销命令."""
        template = mock_canvas.template
        cmd = AddLayerCommand(mock_canvas, text_layer)
        command_stack.push(cmd)

        # 执行后图层应存在
        assert template.get_layer_by_id(text_layer.id) is not None

        # 撤销
        result = command_stack.undo()
        assert result is True
        assert template.get_layer_by_id(text_layer.id) is None
        assert not command_stack.can_undo
        assert command_stack.can_redo

    def test_redo_command(
        self,
        command_stack: CommandStack,
        mock_canvas: MagicMock,
        text_layer: TextLayer,
    ) -> None:
        """测试重做命令."""
        template = mock_canvas.template
        cmd = AddLayerCommand(mock_canvas, text_layer)
        command_stack.push(cmd)
        command_stack.undo()

        # 图层已被撤销
        assert template.get_layer_by_id(text_layer.id) is None

        # 重做
        result = command_stack.redo()
        assert result is True
        assert template.get_layer_by_id(text_layer.id) is not None
        assert command_stack.can_undo
        assert not command_stack.can_redo

    def test_push_clears_redo_stack(
        self,
        command_stack: CommandStack,
        mock_canvas: MagicMock,
        text_layer: TextLayer,
        shape_layer: ShapeLayer,
    ) -> None:
        """测试推入新命令清空重做栈."""
        cmd1 = AddLayerCommand(mock_canvas, text_layer)
        command_stack.push(cmd1)
        command_stack.undo()

        # 此时可以重做
        assert command_stack.can_redo

        # 推入新命令
        cmd2 = AddLayerCommand(mock_canvas, shape_layer)
        command_stack.push(cmd2)

        # 重做栈被清空
        assert not command_stack.can_redo

    def test_max_depth(self, mock_canvas: MagicMock) -> None:
        """测试最大深度限制."""
        stack = CommandStack(max_depth=3)

        for i in range(5):
            layer = TextLayer.create(content=f"层{i}")
            cmd = AddLayerCommand(mock_canvas, layer)
            stack.push(cmd)

        # 只能撤销3次
        count = 0
        while stack.can_undo:
            stack.undo()
            count += 1
        assert count == 3

    def test_clear(
        self,
        command_stack: CommandStack,
        mock_canvas: MagicMock,
        text_layer: TextLayer,
    ) -> None:
        """测试清空命令栈."""
        cmd = AddLayerCommand(mock_canvas, text_layer)
        command_stack.push(cmd)
        command_stack.undo()

        command_stack.clear()

        assert not command_stack.can_undo
        assert not command_stack.can_redo

    def test_signals(
        self,
        command_stack: CommandStack,
        mock_canvas: MagicMock,
        text_layer: TextLayer,
    ) -> None:
        """测试信号发射."""
        can_undo_changes = []
        can_redo_changes = []
        stack_changes = []

        command_stack.can_undo_changed.connect(can_undo_changes.append)
        command_stack.can_redo_changed.connect(can_redo_changes.append)
        command_stack.stack_changed.connect(lambda: stack_changes.append(True))

        cmd = AddLayerCommand(mock_canvas, text_layer)
        command_stack.push(cmd)

        assert True in can_undo_changes  # can_undo became True
        assert len(stack_changes) >= 1

        command_stack.undo()
        assert True in can_redo_changes  # can_redo became True


# ===================
# AddLayerCommand Tests
# ===================


class TestAddLayerCommand:
    """添加图层命令测试."""

    def test_execute(
        self, mock_canvas: MagicMock, text_layer: TextLayer
    ) -> None:
        """测试执行添加."""
        template = mock_canvas.template
        cmd = AddLayerCommand(mock_canvas, text_layer)
        cmd.execute()

        layer = template.get_layer_by_id(text_layer.id)
        assert layer is not None
        assert layer.content == "测试文字"

    def test_undo(
        self, mock_canvas: MagicMock, text_layer: TextLayer
    ) -> None:
        """测试撤销添加."""
        template = mock_canvas.template
        cmd = AddLayerCommand(mock_canvas, text_layer)
        cmd.execute()
        cmd.undo()

        assert template.get_layer_by_id(text_layer.id) is None

    def test_description(
        self, mock_canvas: MagicMock, text_layer: TextLayer
    ) -> None:
        """测试描述."""
        cmd = AddLayerCommand(mock_canvas, text_layer)
        assert "添加图层" in cmd.description


# ===================
# RemoveLayerCommand Tests
# ===================


class TestRemoveLayerCommand:
    """删除图层命令测试."""

    def test_execute(
        self, mock_canvas: MagicMock, text_layer: TextLayer
    ) -> None:
        """测试执行删除."""
        template = mock_canvas.template
        template.add_layer(text_layer)
        cmd = RemoveLayerCommand(mock_canvas, text_layer.id)
        cmd.execute()

        assert template.get_layer_by_id(text_layer.id) is None

    def test_undo(
        self, mock_canvas: MagicMock, text_layer: TextLayer
    ) -> None:
        """测试撤销删除."""
        template = mock_canvas.template
        template.add_layer(text_layer)
        cmd = RemoveLayerCommand(mock_canvas, text_layer.id)
        cmd.execute()
        cmd.undo()

        layer = template.get_layer_by_id(text_layer.id)
        assert layer is not None
        assert layer.content == "测试文字"

    def test_description(
        self, mock_canvas: MagicMock, text_layer: TextLayer
    ) -> None:
        """测试描述."""
        template = mock_canvas.template
        template.add_layer(text_layer)
        cmd = RemoveLayerCommand(mock_canvas, text_layer.id)
        assert "删除图层" in cmd.description


# ===================
# ModifyLayerCommand Tests
# ===================


class TestModifyLayerCommand:
    """修改图层命令测试."""

    def test_execute(
        self, mock_canvas: MagicMock, text_layer: TextLayer
    ) -> None:
        """测试执行修改."""
        template = mock_canvas.template
        template.add_layer(text_layer)
        cmd = ModifyLayerCommand(
            mock_canvas, text_layer.id, "content", "测试文字", "新文字"
        )
        cmd.execute()

        layer = template.get_layer_by_id(text_layer.id)
        assert layer.content == "新文字"

    def test_undo(
        self, mock_canvas: MagicMock, text_layer: TextLayer
    ) -> None:
        """测试撤销修改."""
        template = mock_canvas.template
        template.add_layer(text_layer)
        cmd = ModifyLayerCommand(
            mock_canvas, text_layer.id, "content", "测试文字", "新文字"
        )
        cmd.execute()
        cmd.undo()

        layer = template.get_layer_by_id(text_layer.id)
        assert layer.content == "测试文字"

    def test_modify_multiple_properties(
        self, mock_canvas: MagicMock, text_layer: TextLayer
    ) -> None:
        """测试修改多个属性."""
        template = mock_canvas.template
        template.add_layer(text_layer)

        # 修改x坐标
        cmd1 = ModifyLayerCommand(mock_canvas, text_layer.id, "x", 100, 200)
        cmd1.execute()

        # 修改y坐标
        cmd2 = ModifyLayerCommand(mock_canvas, text_layer.id, "y", 100, 300)
        cmd2.execute()

        layer = template.get_layer_by_id(text_layer.id)
        assert layer.x == 200
        assert layer.y == 300

        # 撤销y
        cmd2.undo()
        layer = template.get_layer_by_id(text_layer.id)
        assert layer.y == 100

        # 撤销x
        cmd1.undo()
        layer = template.get_layer_by_id(text_layer.id)
        assert layer.x == 100


# ===================
# MoveLayerCommand Tests
# ===================


class TestMoveLayerCommand:
    """移动图层命令测试."""

    def test_execute(
        self, mock_canvas: MagicMock, text_layer: TextLayer
    ) -> None:
        """测试执行移动."""
        template = mock_canvas.template
        template.add_layer(text_layer)
        cmd = MoveLayerCommand(
            mock_canvas, text_layer.id, 100, 100, 300, 400
        )
        cmd.execute()

        layer = template.get_layer_by_id(text_layer.id)
        assert layer.x == 300
        assert layer.y == 400

    def test_undo(
        self, mock_canvas: MagicMock, text_layer: TextLayer
    ) -> None:
        """测试撤销移动."""
        template = mock_canvas.template
        template.add_layer(text_layer)
        cmd = MoveLayerCommand(
            mock_canvas, text_layer.id, 100, 100, 300, 400
        )
        cmd.execute()
        cmd.undo()

        layer = template.get_layer_by_id(text_layer.id)
        assert layer.x == 100
        assert layer.y == 100


# ===================
# ResizeLayerCommand Tests
# ===================


class TestResizeLayerCommand:
    """调整大小命令测试."""

    def test_execute(
        self, mock_canvas: MagicMock, text_layer: TextLayer
    ) -> None:
        """测试执行调整大小."""
        template = mock_canvas.template
        template.add_layer(text_layer)
        old_width = text_layer.width
        old_height = text_layer.height
        cmd = ResizeLayerCommand(
            mock_canvas, text_layer.id, old_width, old_height, 400, 100
        )
        cmd.execute()

        layer = template.get_layer_by_id(text_layer.id)
        assert layer.width == 400
        assert layer.height == 100

    def test_undo(
        self, mock_canvas: MagicMock, text_layer: TextLayer
    ) -> None:
        """测试撤销调整大小."""
        template = mock_canvas.template
        template.add_layer(text_layer)
        old_width = text_layer.width
        old_height = text_layer.height
        cmd = ResizeLayerCommand(
            mock_canvas, text_layer.id, old_width, old_height, 400, 100
        )
        cmd.execute()
        cmd.undo()

        layer = template.get_layer_by_id(text_layer.id)
        assert layer.width == old_width
        assert layer.height == old_height


# ===================
# BatchCommand Tests
# ===================


class TestBatchCommand:
    """批量命令测试."""

    def test_execute(
        self,
        mock_canvas: MagicMock,
        text_layer: TextLayer,
        shape_layer: ShapeLayer,
    ) -> None:
        """测试执行批量命令."""
        template = mock_canvas.template
        cmd1 = AddLayerCommand(mock_canvas, text_layer)
        cmd2 = AddLayerCommand(mock_canvas, shape_layer)
        batch = BatchCommand([cmd1, cmd2], "添加多个图层")
        batch.execute()

        assert template.get_layer_by_id(text_layer.id) is not None
        assert template.get_layer_by_id(shape_layer.id) is not None

    def test_undo(
        self,
        mock_canvas: MagicMock,
        text_layer: TextLayer,
        shape_layer: ShapeLayer,
    ) -> None:
        """测试撤销批量命令."""
        template = mock_canvas.template
        cmd1 = AddLayerCommand(mock_canvas, text_layer)
        cmd2 = AddLayerCommand(mock_canvas, shape_layer)
        batch = BatchCommand([cmd1, cmd2], "添加多个图层")
        batch.execute()
        batch.undo()

        # 两个图层都应该被删除
        assert template.get_layer_by_id(text_layer.id) is None
        assert template.get_layer_by_id(shape_layer.id) is None

    def test_description(
        self,
        mock_canvas: MagicMock,
        text_layer: TextLayer,
        shape_layer: ShapeLayer,
    ) -> None:
        """测试描述."""
        cmd1 = AddLayerCommand(mock_canvas, text_layer)
        cmd2 = AddLayerCommand(mock_canvas, shape_layer)
        batch = BatchCommand([cmd1, cmd2], "添加多个图层")
        assert batch.description == "添加多个图层"


# ===================
# ModifyCanvasCommand Tests
# ===================


class TestModifyCanvasCommand:
    """修改画布命令测试."""

    def test_execute_size(self, mock_canvas: MagicMock) -> None:
        """测试修改画布大小."""
        template = mock_canvas.template
        cmd = ModifyCanvasCommand(
            mock_canvas, "canvas_width", 800, 1200
        )
        cmd.execute()

        assert template.canvas_width == 1200

    def test_undo_size(self, mock_canvas: MagicMock) -> None:
        """测试撤销画布大小修改."""
        template = mock_canvas.template
        cmd = ModifyCanvasCommand(
            mock_canvas, "canvas_width", 800, 1200
        )
        cmd.execute()
        cmd.undo()

        assert template.canvas_width == 800

    def test_modify_background_color(self, mock_canvas: MagicMock) -> None:
        """测试修改背景颜色."""
        template = mock_canvas.template
        cmd = ModifyCanvasCommand(
            mock_canvas,
            "background_color",
            (255, 255, 255),
            (200, 200, 200),
        )
        cmd.execute()

        assert template.background_color == (200, 200, 200)


# ===================
# UndoRedoManager Tests
# ===================


class TestUndoRedoManager:
    """撤销管理器测试.

    注意: UndoRedoManager 设计为与 TemplateCanvas 配合使用。
    在集成测试中使用实际的 TemplateCanvas 来测试。
    这里仅测试基本的命令栈功能。
    """

    def test_command_stack_can_undo_redo(
        self, mock_canvas: MagicMock, text_layer: TextLayer
    ) -> None:
        """测试通过命令栈的撤销重做."""
        manager = UndoRedoManager(mock_canvas)
        template = mock_canvas.template

        # 添加图层
        template.add_layer(text_layer)
        manager.record_add_layer(text_layer)

        assert manager.can_undo
        assert not manager.can_redo

        # 撤销
        manager.undo()
        assert not manager.can_undo
        assert manager.can_redo

        # 重做
        manager.redo()
        assert manager.can_undo
        assert not manager.can_redo

    def test_clear(self, mock_canvas: MagicMock, text_layer: TextLayer) -> None:
        """测试清空."""
        manager = UndoRedoManager(mock_canvas)
        template = mock_canvas.template
        template.add_layer(text_layer)
        manager.record_add_layer(text_layer)
        manager.undo()

        manager.clear()

        assert not manager.can_undo
        assert not manager.can_redo


# ===================
# Integration Tests
# ===================


class TestUndoRedoIntegration:
    """撤销/重做集成测试."""

    def test_complex_workflow(self, mock_canvas: MagicMock) -> None:
        """测试复杂工作流程."""
        template = mock_canvas.template
        stack = CommandStack()

        # 添加文字图层
        text = TextLayer.create(content="标题", x=50, y=50)
        cmd1 = AddLayerCommand(mock_canvas, text)
        stack.push(cmd1)

        # 添加形状图层
        shape = ShapeLayer.create_rectangle(x=100, y=100)
        cmd2 = AddLayerCommand(mock_canvas, shape)
        stack.push(cmd2)

        # 移动文字图层
        cmd3 = MoveLayerCommand(mock_canvas, text.id, 50, 50, 150, 150)
        stack.push(cmd3)

        # 修改画布大小
        cmd4 = ModifyCanvasCommand(mock_canvas, "canvas_width", 800, 1200)
        stack.push(cmd4)

        # 验证当前状态
        assert len(template.get_layers()) == 2
        assert template.canvas_width == 1200

        # 撤销画布修改
        stack.undo()
        assert template.canvas_width == 800

        # 撤销移动
        stack.undo()
        layer = template.get_layer_by_id(text.id)
        assert layer.x == 50

        # 重做移动
        stack.redo()
        layer = template.get_layer_by_id(text.id)
        assert layer.x == 150

        # 新操作打断重做链
        cmd5 = ModifyLayerCommand(
            mock_canvas, text.id, "content", "标题", "新标题"
        )
        stack.push(cmd5)
        assert not stack.can_redo

        # 继续撤销
        stack.undo()  # 撤销内容修改
        stack.undo()  # 撤销移动
        stack.undo()  # 撤销添加shape
        stack.undo()  # 撤销添加text

        assert len(template.get_layers()) == 0

    def test_batch_operations(self, mock_canvas: MagicMock) -> None:
        """测试批量操作."""
        template = mock_canvas.template
        stack = CommandStack()

        # 创建多个图层
        layers = [
            TextLayer.create(content=f"文字{i}", x=i * 50, y=i * 50)
            for i in range(3)
        ]

        # 作为批量命令添加
        commands = [AddLayerCommand(mock_canvas, layer) for layer in layers]
        batch = BatchCommand(commands, "添加3个图层")
        stack.push(batch)

        # 应该有3个图层
        assert len(template.get_layers()) == 3

        # 一次撤销删除所有
        stack.undo()
        assert len(template.get_layers()) == 0

        # 一次重做恢复所有
        stack.redo()
        assert len(template.get_layers()) == 3
