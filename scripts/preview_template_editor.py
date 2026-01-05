#!/usr/bin/env python3
"""模板编辑器预览脚本.

运行方式:
    python scripts/preview_template_editor.py
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QPushButton,
    QLabel,
    QToolBar,
)
from PyQt6.QtCore import Qt

from src.models.template_config import (
    TemplateConfig,
    TextLayer,
    ShapeLayer,
    ImageLayer,
)
from src.ui.widgets.template_editor import TemplateCanvas


class TemplateEditorPreview(QMainWindow):
    """模板编辑器预览窗口."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("模板编辑器预览")
        self.setMinimumSize(1200, 800)

        # 创建中心组件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)

        # 创建工具栏
        toolbar = QToolBar()
        self.addToolBar(toolbar)

        # 添加图层按钮
        btn_add_text = QPushButton("添加文字")
        btn_add_text.clicked.connect(self._add_text_layer)
        toolbar.addWidget(btn_add_text)

        btn_add_rect = QPushButton("添加矩形")
        btn_add_rect.clicked.connect(self._add_rectangle)
        toolbar.addWidget(btn_add_rect)

        btn_add_ellipse = QPushButton("添加椭圆")
        btn_add_ellipse.clicked.connect(self._add_ellipse)
        toolbar.addWidget(btn_add_ellipse)

        btn_add_image = QPushButton("添加图片")
        btn_add_image.clicked.connect(self._add_image_layer)
        toolbar.addWidget(btn_add_image)

        toolbar.addSeparator()

        # 缩放控制
        btn_zoom_in = QPushButton("放大")
        btn_zoom_in.clicked.connect(lambda: self._canvas.zoom_in())
        toolbar.addWidget(btn_zoom_in)

        btn_zoom_out = QPushButton("缩小")
        btn_zoom_out.clicked.connect(lambda: self._canvas.zoom_out())
        toolbar.addWidget(btn_zoom_out)

        btn_zoom_reset = QPushButton("重置缩放")
        btn_zoom_reset.clicked.connect(lambda: self._canvas.zoom_reset())
        toolbar.addWidget(btn_zoom_reset)

        btn_fit = QPushButton("适应窗口")
        btn_fit.clicked.connect(lambda: self._canvas.fit_in_view())
        toolbar.addWidget(btn_fit)

        toolbar.addSeparator()

        # 网格控制
        btn_toggle_grid = QPushButton("切换网格")
        btn_toggle_grid.clicked.connect(self._toggle_grid)
        toolbar.addWidget(btn_toggle_grid)

        # 创建画布
        self._canvas = TemplateCanvas()
        layout.addWidget(self._canvas)

        # 状态栏
        self._status_label = QLabel("提示: 双击文字图层可编辑文字内容")
        layout.addWidget(self._status_label)

        # 初始化模板
        self._init_template()

        # 连接信号
        self._canvas.layer_selected.connect(self._on_layer_selected)
        self._canvas.layer_content_changed.connect(self._on_content_changed)
        self._canvas.zoom_changed.connect(self._on_zoom_changed)

    def _init_template(self):
        """初始化模板."""
        template = TemplateConfig(
            name="测试模板",
            canvas_width=800,
            canvas_height=600,
            background_color=(240, 240, 240),
        )

        # 添加一些示例图层
        # 背景矩形
        bg_rect = ShapeLayer.create_rectangle()
        bg_rect.x = 50
        bg_rect.y = 50
        bg_rect.width = 700
        bg_rect.height = 500
        bg_rect.fill_color = (255, 255, 255)
        bg_rect.stroke_enabled = True
        bg_rect.stroke_color = (200, 200, 200)
        bg_rect.stroke_width = 2
        bg_rect.corner_radius = 10
        template.add_layer(bg_rect)

        # 标题文字
        title = TextLayer.create("模板编辑器预览")
        title.x = 100
        title.y = 80
        title.width = 600
        title.height = 60
        title.font_size = 32
        title.bold = True
        title.font_color = (51, 51, 51)
        title.align = "center"
        template.add_layer(title)

        # 说明文字
        desc = TextLayer.create("双击此文字可以编辑\n支持多行文字和自动换行")
        desc.x = 100
        desc.y = 180
        desc.width = 300
        desc.height = 100
        desc.font_size = 16
        desc.font_color = (102, 102, 102)
        desc.background_enabled = True
        desc.background_color = (255, 255, 230)
        desc.background_padding = 10
        template.add_layer(desc)

        # 带描边的文字
        stroke_text = TextLayer.create("描边效果")
        stroke_text.x = 450
        stroke_text.y = 200
        stroke_text.width = 200
        stroke_text.height = 50
        stroke_text.font_size = 24
        stroke_text.font_color = (255, 255, 255)
        stroke_text.stroke_enabled = True
        stroke_text.stroke_color = (0, 0, 0)
        stroke_text.stroke_width = 2
        template.add_layer(stroke_text)

        # 椭圆
        ellipse = ShapeLayer.create_ellipse()
        ellipse.x = 100
        ellipse.y = 320
        ellipse.width = 150
        ellipse.height = 150
        ellipse.fill_color = (100, 149, 237)  # 矢车菊蓝
        ellipse.fill_opacity = 80
        template.add_layer(ellipse)

        # 另一个矩形
        rect2 = ShapeLayer.create_rectangle()
        rect2.x = 300
        rect2.y = 350
        rect2.width = 200
        rect2.height = 100
        rect2.fill_color = (255, 182, 193)  # 浅粉红
        rect2.stroke_enabled = True
        rect2.stroke_color = (255, 105, 180)  # 热粉红
        rect2.stroke_width = 3
        template.add_layer(rect2)

        self._canvas.set_template(template)

    def _add_text_layer(self):
        """添加文字图层."""
        layer = TextLayer.create("新文字")
        layer.x = 200
        layer.y = 200
        layer.width = 150
        layer.height = 40
        layer.font_size = 18
        self._canvas.add_layer(layer)
        self._status_label.setText(f"已添加文字图层: {layer.id[:8]}")

    def _add_rectangle(self):
        """添加矩形图层."""
        layer = ShapeLayer.create_rectangle()
        layer.x = 250
        layer.y = 250
        layer.width = 120
        layer.height = 80
        layer.fill_color = (200, 200, 255)
        self._canvas.add_layer(layer)
        self._status_label.setText(f"已添加矩形图层: {layer.id[:8]}")

    def _add_ellipse(self):
        """添加椭圆图层."""
        layer = ShapeLayer.create_ellipse()
        layer.x = 300
        layer.y = 300
        layer.width = 100
        layer.height = 100
        layer.fill_color = (255, 200, 200)
        self._canvas.add_layer(layer)
        self._status_label.setText(f"已添加椭圆图层: {layer.id[:8]}")

    def _add_image_layer(self):
        """添加图片图层."""
        from PyQt6.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择图片",
            "",
            "图片文件 (*.png *.jpg *.jpeg *.gif *.bmp *.webp)"
        )
        if file_path:
            layer = ImageLayer.create(file_path)
            layer.x = 200
            layer.y = 200
            layer.width = 200
            layer.height = 150
            self._canvas.add_layer(layer)
            self._status_label.setText(f"已添加图片图层: {layer.id[:8]}")

    def _toggle_grid(self):
        """切换网格显示."""
        current = self._canvas.show_grid
        self._canvas.set_show_grid(not current)
        self._status_label.setText(f"网格: {'显示' if not current else '隐藏'}")

    def _on_layer_selected(self, layer_id: str):
        """图层被选中."""
        self._status_label.setText(f"选中图层: {layer_id[:8]}...")

    def _on_content_changed(self, layer_id: str, content: str):
        """图层内容变化."""
        preview = content[:20] + "..." if len(content) > 20 else content
        self._status_label.setText(f"内容已更新: {preview}")

    def _on_zoom_changed(self, level: float):
        """缩放变化."""
        self._status_label.setText(f"缩放: {level:.0%}")


def main():
    app = QApplication(sys.argv)
    window = TemplateEditorPreview()
    window.show()

    print("模板编辑器预览已启动!")
    print("操作说明:")
    print("  - 点击选择图层")
    print("  - 拖拽移动图层")
    print("  - 拖拽控制点调整大小")
    print("  - 双击文字图层进入编辑模式")
    print("  - Ctrl+滚轮 缩放")
    print("  - 中键拖拽 或 空格+拖拽 平移画布")
    print("  - Delete 删除选中图层")

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
