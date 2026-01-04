# 电商图片批量AI合成与处理桌面工具

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![PyQt6](https://img.shields.io/badge/PyQt6-6.6+-green.svg)](https://www.riverbankcomputing.com/software/pyqt/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

一款面向电商运营的桌面软件，通过 GPT-Image-1.5 AI 模型批量处理商品图片，实现背景去除、商品合成，并添加自定义背景、边框和文字。

## ✨ 功能特性

- 🎨 **AI 智能合成**: 基于 GPT-Image-1.5 模型，实现精准的背景去除和商品合成
- 📦 **批量处理**: 支持最多 10 张图片的队列处理
- 🖼️ **后期美化**: 添加自定义背景色、边框和品牌文字
- ⚙️ **灵活配置**: 可调节输出尺寸、质量和各种处理参数
- 💾 **配置预设**: 保存和加载处理配置模板
- 📊 **进度追踪**: 实时显示处理进度和状态

## 🛠️ 技术栈

- **语言**: Python 3.11+
- **GUI**: PyQt6
- **图片处理**: Pillow
- **AI 服务**: OpenAI API (GPT-Image-1.5)
- **数据库**: SQLite + SQLAlchemy
- **配置**: Pydantic

## 📋 系统要求

- Python 3.11 或更高版本
- Windows 10/11 或 macOS
- 网络连接（用于 AI API 调用）

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/yang/ecommerce-image-ai-processor.git
cd ecommerce-image-ai-processor
```

### 2. 创建虚拟环境

```bash
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# 或
.venv\Scripts\activate  # Windows
```

### 3. 安装依赖

```bash
# 生产环境
pip install -r requirements.txt

# 开发环境
pip install -r requirements-dev.txt
```

### 4. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，配置 API 密钥等
```

### 5. 运行应用

```bash
python -m src.main
```

## 📁 项目结构

```
ecommerce-image-ai-processor/
├── src/                    # 源代码
│   ├── ui/                 # 用户界面
│   ├── core/               # 核心业务逻辑
│   ├── services/           # 服务层
│   ├── models/             # 数据模型
│   ├── repositories/       # 数据访问层
│   └── utils/              # 工具函数
├── tests/                  # 测试代码
├── resources/              # 资源文件
├── docs/                   # 文档
└── scripts/                # 脚本
```

## 🧪 开发

### 运行测试

```bash
pytest
```

### 代码格式化

```bash
black src tests
isort src tests
```

### 类型检查

```bash
mypy src
```

### 代码检查

```bash
ruff check src
```

## 📦 打包

```bash
pyinstaller --name="电商图片处理工具" --windowed src/main.py
```

## 🔧 配置说明

### API 配置

应用支持通过以下方式配置 OpenAI API：

1. **应用内设置**: 在设置对话框中输入 API 密钥（推荐）
2. **环境变量**: 设置 `OPENAI_API_KEY` 环境变量
3. **系统密钥库**: 自动使用系统安全存储

### 处理参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| 输出尺寸 | 图片输出尺寸 | 800×800 |
| 输出质量 | JPG 压缩质量 | 85 |
| 边框宽度 | 边框像素宽度 | 0 (无边框) |
| 背景颜色 | RGB 颜色值 | 白色 |

## 📄 许可证

本项目采用 [MIT 许可证](LICENSE)。

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

**Made with ❤️ for E-commerce**
