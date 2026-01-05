"""撤销/重做功能模块.

使用命令模式实现模板编辑器的撤销和重做功能。

Features:
    - 命令模式架构
    - 支持图层添加/删除撤销
    - 支持属性修改撤销
    - 支持位置/大小变更撤销
    - 命令栈管理
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, TYPE_CHECKING

from PyQt6.QtCore import QObject, pyqtSignal

from src.models.template_config import (
    AnyLayer,
    TextLayer,
    ShapeLayer,
    ImageLayer,
)
from src.utils.logger import setup_logger

if TYPE_CHECKING:
    from src.ui.widgets.template_editor.canvas import TemplateCanvas

logger = setup_logger(__name__)


# ===================
# 命令基类
# ===================


class Command(ABC):
    """命令基类.

    所有可撤销操作都应该实现这个接口。

    Example:
        >>> class MyCommand(Command):
        ...     def execute(self):
        ...         # 执行操作
        ...         pass
        ...     def undo(self):
        ...         # 撤销操作
        ...         pass
    """

    @abstractmethod
    def execute(self) -> None:
        """执行命令."""
        pass

    @abstractmethod
    def undo(self) -> None:
        """撤销命令."""
        pass

    def redo(self) -> None:
        """重做命令（默认调用 execute）."""
        self.execute()

    @property
    def description(self) -> str:
        """命令描述（用于显示）."""
        return self.__class__.__name__


# ===================
# 命令栈管理器
# ===================


class CommandStack(QObject):
    """命令栈管理器.

    管理撤销和重做命令栈。

    Signals:
        can_undo_changed: 可撤销状态改变
        can_redo_changed: 可重做状态改变
        stack_changed: 栈状态改变

    Example:
        >>> stack = CommandStack()
        >>> stack.push(AddLayerCommand(...))
        >>> stack.undo()
        >>> stack.redo()
    """

    # 信号定义
    can_undo_changed = pyqtSignal(bool)
    can_redo_changed = pyqtSignal(bool)
    stack_changed = pyqtSignal()

    # 默认最大栈深度
    DEFAULT_MAX_DEPTH = 50

    def __init__(
        self,
        max_depth: int = DEFAULT_MAX_DEPTH,
        parent: Optional[QObject] = None,
    ) -> None:
        """初始化命令栈.

        Args:
            max_depth: 最大栈深度
            parent: 父对象
        """
        super().__init__(parent)

        self._undo_stack: List[Command] = []
        self._redo_stack: List[Command] = []
        self._max_depth = max_depth
        self._is_executing = False

    @property
    def can_undo(self) -> bool:
        """是否可以撤销."""
        return len(self._undo_stack) > 0

    @property
    def can_redo(self) -> bool:
        """是否可以重做."""
        return len(self._redo_stack) > 0

    @property
    def undo_count(self) -> int:
        """撤销栈深度."""
        return len(self._undo_stack)

    @property
    def redo_count(self) -> int:
        """重做栈深度."""
        return len(self._redo_stack)

    @property
    def undo_description(self) -> str:
        """下一个撤销操作的描述."""
        if self._undo_stack:
            return self._undo_stack[-1].description
        return ""

    @property
    def redo_description(self) -> str:
        """下一个重做操作的描述."""
        if self._redo_stack:
            return self._redo_stack[-1].description
        return ""

    def push(self, command: Command, execute: bool = True) -> None:
        """推入命令.

        Args:
            command: 命令对象
            execute: 是否立即执行
        """
        if self._is_executing:
            return

        self._is_executing = True

        try:
            # 执行命令
            if execute:
                command.execute()

            # 添加到撤销栈
            self._undo_stack.append(command)

            # 清空重做栈
            self._redo_stack.clear()

            # 限制栈深度
            while len(self._undo_stack) > self._max_depth:
                self._undo_stack.pop(0)

            # 发送信号
            self._emit_state_changed()

            logger.debug(f"命令入栈: {command.description}")

        finally:
            self._is_executing = False

    def undo(self) -> bool:
        """撤销.

        Returns:
            是否成功撤销
        """
        if not self.can_undo or self._is_executing:
            return False

        self._is_executing = True

        try:
            command = self._undo_stack.pop()
            command.undo()
            self._redo_stack.append(command)

            self._emit_state_changed()

            logger.debug(f"撤销: {command.description}")
            return True

        finally:
            self._is_executing = False

    def redo(self) -> bool:
        """重做.

        Returns:
            是否成功重做
        """
        if not self.can_redo or self._is_executing:
            return False

        self._is_executing = True

        try:
            command = self._redo_stack.pop()
            command.redo()
            self._undo_stack.append(command)

            self._emit_state_changed()

            logger.debug(f"重做: {command.description}")
            return True

        finally:
            self._is_executing = False

    def clear(self) -> None:
        """清空所有命令栈."""
        self._undo_stack.clear()
        self._redo_stack.clear()
        self._emit_state_changed()
        logger.debug("命令栈已清空")

    def _emit_state_changed(self) -> None:
        """发送状态改变信号."""
        self.can_undo_changed.emit(self.can_undo)
        self.can_redo_changed.emit(self.can_redo)
        self.stack_changed.emit()


# ===================
# 图层相关命令
# ===================


class AddLayerCommand(Command):
    """添加图层命令."""

    def __init__(self, canvas: "TemplateCanvas", layer: AnyLayer) -> None:
        """初始化添加图层命令.

        Args:
            canvas: 画布组件
            layer: 图层数据
        """
        self._canvas = canvas
        self._layer = layer
        self._layer_data = layer.model_dump()

    def execute(self) -> None:
        """执行：添加图层."""
        # 重新创建图层（确保ID一致）
        layer = self._recreate_layer()
        if layer and self._canvas.template:
            self._canvas.template.add_layer(layer)
            self._canvas._add_layer_item(layer)

    def undo(self) -> None:
        """撤销：删除图层."""
        if self._canvas.template:
            self._canvas.remove_layer(self._layer.id)

    @property
    def description(self) -> str:
        """命令描述."""
        return f"添加图层 '{self._layer.name}'"

    def _recreate_layer(self) -> Optional[AnyLayer]:
        """重新创建图层."""
        layer_type = self._layer_data.get("type")
        if layer_type == "text":
            return TextLayer(**self._layer_data)
        elif layer_type in ("rectangle", "ellipse"):
            return ShapeLayer(**self._layer_data)
        elif layer_type == "image":
            return ImageLayer(**self._layer_data)
        return None


class RemoveLayerCommand(Command):
    """删除图层命令."""

    def __init__(self, canvas: "TemplateCanvas", layer_id: str) -> None:
        """初始化删除图层命令.

        Args:
            canvas: 画布组件
            layer_id: 图层ID
        """
        self._canvas = canvas
        self._layer_id = layer_id
        self._layer_data: Optional[dict] = None

        # 保存图层数据
        if canvas.template:
            layer = canvas.template.get_layer_by_id(layer_id)
            if layer:
                self._layer_data = layer.model_dump()

    def execute(self) -> None:
        """执行：删除图层."""
        self._canvas.remove_layer(self._layer_id)

    def undo(self) -> None:
        """撤销：恢复图层."""
        if self._layer_data and self._canvas.template:
            layer = self._recreate_layer()
            if layer:
                self._canvas.template.add_layer(layer)
                self._canvas._add_layer_item(layer)

    @property
    def description(self) -> str:
        """命令描述."""
        name = self._layer_data.get("name", "") if self._layer_data else ""
        return f"删除图层 '{name}'"

    def _recreate_layer(self) -> Optional[AnyLayer]:
        """重新创建图层."""
        if not self._layer_data:
            return None

        layer_type = self._layer_data.get("type")
        if layer_type == "text":
            return TextLayer(**self._layer_data)
        elif layer_type in ("rectangle", "ellipse"):
            return ShapeLayer(**self._layer_data)
        elif layer_type == "image":
            return ImageLayer(**self._layer_data)
        return None


class ModifyLayerCommand(Command):
    """修改图层属性命令."""

    def __init__(
        self,
        canvas: "TemplateCanvas",
        layer_id: str,
        property_name: str,
        old_value: Any,
        new_value: Any,
    ) -> None:
        """初始化修改图层命令.

        Args:
            canvas: 画布组件
            layer_id: 图层ID
            property_name: 属性名
            old_value: 旧值
            new_value: 新值
        """
        self._canvas = canvas
        self._layer_id = layer_id
        self._property_name = property_name
        self._old_value = old_value
        self._new_value = new_value

    def execute(self) -> None:
        """执行：设置新值."""
        self._set_property(self._new_value)

    def undo(self) -> None:
        """撤销：恢复旧值."""
        self._set_property(self._old_value)

    @property
    def description(self) -> str:
        """命令描述."""
        return f"修改 {self._property_name}"

    def _set_property(self, value: Any) -> None:
        """设置属性值."""
        if self._canvas.template:
            layer = self._canvas.template.get_layer_by_id(self._layer_id)
            if layer:
                setattr(layer, self._property_name, value)
                self._canvas.template.update_layer(layer)
                self._canvas.update_layer(self._layer_id)


class MoveLayerCommand(Command):
    """移动图层命令."""

    def __init__(
        self,
        canvas: "TemplateCanvas",
        layer_id: str,
        old_x: int,
        old_y: int,
        new_x: int,
        new_y: int,
    ) -> None:
        """初始化移动图层命令.

        Args:
            canvas: 画布组件
            layer_id: 图层ID
            old_x: 旧X坐标
            old_y: 旧Y坐标
            new_x: 新X坐标
            new_y: 新Y坐标
        """
        self._canvas = canvas
        self._layer_id = layer_id
        self._old_x = old_x
        self._old_y = old_y
        self._new_x = new_x
        self._new_y = new_y

    def execute(self) -> None:
        """执行：移动到新位置."""
        self._set_position(self._new_x, self._new_y)

    def undo(self) -> None:
        """撤销：移动回旧位置."""
        self._set_position(self._old_x, self._old_y)

    @property
    def description(self) -> str:
        """命令描述."""
        return "移动图层"

    def _set_position(self, x: int, y: int) -> None:
        """设置图层位置."""
        if self._canvas.template:
            layer = self._canvas.template.get_layer_by_id(self._layer_id)
            if layer:
                layer.x = x
                layer.y = y
                self._canvas.template.update_layer(layer)
                self._canvas.update_layer(self._layer_id)


class ResizeLayerCommand(Command):
    """调整图层大小命令."""

    def __init__(
        self,
        canvas: "TemplateCanvas",
        layer_id: str,
        old_width: int,
        old_height: int,
        new_width: int,
        new_height: int,
        old_x: Optional[int] = None,
        old_y: Optional[int] = None,
        new_x: Optional[int] = None,
        new_y: Optional[int] = None,
    ) -> None:
        """初始化调整大小命令.

        Args:
            canvas: 画布组件
            layer_id: 图层ID
            old_width: 旧宽度
            old_height: 旧高度
            new_width: 新宽度
            new_height: 新高度
            old_x: 旧X坐标（可选，调整大小可能改变位置）
            old_y: 旧Y坐标
            new_x: 新X坐标
            new_y: 新Y坐标
        """
        self._canvas = canvas
        self._layer_id = layer_id
        self._old_width = old_width
        self._old_height = old_height
        self._new_width = new_width
        self._new_height = new_height
        self._old_x = old_x
        self._old_y = old_y
        self._new_x = new_x
        self._new_y = new_y

    def execute(self) -> None:
        """执行：设置新大小."""
        self._set_size(
            self._new_width,
            self._new_height,
            self._new_x,
            self._new_y,
        )

    def undo(self) -> None:
        """撤销：恢复旧大小."""
        self._set_size(
            self._old_width,
            self._old_height,
            self._old_x,
            self._old_y,
        )

    @property
    def description(self) -> str:
        """命令描述."""
        return "调整图层大小"

    def _set_size(
        self,
        width: int,
        height: int,
        x: Optional[int],
        y: Optional[int],
    ) -> None:
        """设置图层大小."""
        if self._canvas.template:
            layer = self._canvas.template.get_layer_by_id(self._layer_id)
            if layer:
                layer.width = width
                layer.height = height
                if x is not None:
                    layer.x = x
                if y is not None:
                    layer.y = y
                self._canvas.template.update_layer(layer)
                self._canvas.update_layer(self._layer_id)


class BatchCommand(Command):
    """批量命令.

    将多个命令组合为一个命令，一起撤销/重做。
    """

    def __init__(self, commands: List[Command], description: str = "批量操作") -> None:
        """初始化批量命令.

        Args:
            commands: 命令列表
            description: 命令描述
        """
        self._commands = commands
        self._description = description

    def execute(self) -> None:
        """执行所有命令."""
        for cmd in self._commands:
            cmd.execute()

    def undo(self) -> None:
        """撤销所有命令（逆序）."""
        for cmd in reversed(self._commands):
            cmd.undo()

    @property
    def description(self) -> str:
        """命令描述."""
        return self._description


class ModifyCanvasCommand(Command):
    """修改画布属性命令."""

    def __init__(
        self,
        canvas: "TemplateCanvas",
        property_name: str,
        old_value: Any,
        new_value: Any,
    ) -> None:
        """初始化修改画布命令.

        Args:
            canvas: 画布组件
            property_name: 属性名（canvas_width, canvas_height, background_color）
            old_value: 旧值
            new_value: 新值
        """
        self._canvas = canvas
        self._property_name = property_name
        self._old_value = old_value
        self._new_value = new_value

    def execute(self) -> None:
        """执行：设置新值."""
        self._set_property(self._new_value)

    def undo(self) -> None:
        """撤销：恢复旧值."""
        self._set_property(self._old_value)

    @property
    def description(self) -> str:
        """命令描述."""
        return f"修改画布 {self._property_name}"

    def _set_property(self, value: Any) -> None:
        """设置画布属性."""
        if self._canvas.template:
            if self._property_name == "canvas_width":
                self._canvas.template.canvas_width = value
                self._canvas._scene.set_canvas_size(
                    value,
                    self._canvas.template.canvas_height,
                )
            elif self._property_name == "canvas_height":
                self._canvas.template.canvas_height = value
                self._canvas._scene.set_canvas_size(
                    self._canvas.template.canvas_width,
                    value,
                )
            elif self._property_name == "background_color":
                self._canvas.template.background_color = value
                self._canvas._scene.set_background_color(value)


# ===================
# 撤销/重做管理器
# ===================


class UndoRedoManager(QObject):
    """撤销/重做管理器.

    封装命令栈，提供更高级的撤销/重做功能。

    Signals:
        state_changed: 状态改变

    Example:
        >>> manager = UndoRedoManager(canvas)
        >>> manager.add_layer(layer)  # 自动记录命令
        >>> manager.undo()
    """

    # 信号
    state_changed = pyqtSignal()

    def __init__(
        self,
        canvas: "TemplateCanvas",
        parent: Optional[QObject] = None,
    ) -> None:
        """初始化管理器.

        Args:
            canvas: 画布组件
            parent: 父对象
        """
        super().__init__(parent)

        self._canvas = canvas
        self._stack = CommandStack(parent=self)

        # 连接信号
        self._stack.stack_changed.connect(self.state_changed.emit)

    @property
    def can_undo(self) -> bool:
        """是否可以撤销."""
        return self._stack.can_undo

    @property
    def can_redo(self) -> bool:
        """是否可以重做."""
        return self._stack.can_redo

    @property
    def undo_description(self) -> str:
        """撤销描述."""
        return self._stack.undo_description

    @property
    def redo_description(self) -> str:
        """重做描述."""
        return self._stack.redo_description

    def undo(self) -> bool:
        """撤销."""
        return self._stack.undo()

    def redo(self) -> bool:
        """重做."""
        return self._stack.redo()

    def clear(self) -> None:
        """清空命令栈."""
        self._stack.clear()

    def push(self, command: Command, execute: bool = True) -> None:
        """推入命令."""
        self._stack.push(command, execute)

    # ==================
    # 便捷方法
    # ==================

    def record_add_layer(self, layer: AnyLayer) -> None:
        """记录添加图层操作（已执行后调用）.

        Args:
            layer: 添加的图层
        """
        cmd = AddLayerCommand(self._canvas, layer)
        self._stack.push(cmd, execute=False)  # 已经执行过，不需要再执行

    def record_remove_layer(self, layer_id: str) -> None:
        """记录删除图层操作（执行前调用）.

        Args:
            layer_id: 要删除的图层ID
        """
        cmd = RemoveLayerCommand(self._canvas, layer_id)
        self._stack.push(cmd, execute=True)

    def record_move_layer(
        self,
        layer_id: str,
        old_x: int,
        old_y: int,
        new_x: int,
        new_y: int,
    ) -> None:
        """记录移动图层操作（已执行后调用）.

        Args:
            layer_id: 图层ID
            old_x: 旧X坐标
            old_y: 旧Y坐标
            new_x: 新X坐标
            new_y: 新Y坐标
        """
        cmd = MoveLayerCommand(
            self._canvas,
            layer_id,
            old_x,
            old_y,
            new_x,
            new_y,
        )
        self._stack.push(cmd, execute=False)

    def record_resize_layer(
        self,
        layer_id: str,
        old_width: int,
        old_height: int,
        new_width: int,
        new_height: int,
        old_x: Optional[int] = None,
        old_y: Optional[int] = None,
        new_x: Optional[int] = None,
        new_y: Optional[int] = None,
    ) -> None:
        """记录调整大小操作（已执行后调用）."""
        cmd = ResizeLayerCommand(
            self._canvas,
            layer_id,
            old_width,
            old_height,
            new_width,
            new_height,
            old_x,
            old_y,
            new_x,
            new_y,
        )
        self._stack.push(cmd, execute=False)

    def record_modify_layer(
        self,
        layer_id: str,
        property_name: str,
        old_value: Any,
        new_value: Any,
    ) -> None:
        """记录修改属性操作（已执行后调用）."""
        cmd = ModifyLayerCommand(
            self._canvas,
            layer_id,
            property_name,
            old_value,
            new_value,
        )
        self._stack.push(cmd, execute=False)

    def record_modify_canvas(
        self,
        property_name: str,
        old_value: Any,
        new_value: Any,
    ) -> None:
        """记录修改画布属性操作（已执行后调用）."""
        cmd = ModifyCanvasCommand(
            self._canvas,
            property_name,
            old_value,
            new_value,
        )
        self._stack.push(cmd, execute=False)
