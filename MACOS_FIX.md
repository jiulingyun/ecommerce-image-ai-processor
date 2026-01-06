# macOS 应用崩溃修复说明

## 问题描述

从 GitHub Actions 编译下载的 macOS 版本在启动时崩溃，错误信息：
```
Exception Type:    EXC_BAD_ACCESS (SIGSEGV)
Exception Subtype: KERN_INVALID_ADDRESS at 0x0000000000000008
```

崩溃发生在 Qt 框架初始化过程中：
```
CoreFoundation -> CFBundleCopyBundleURL -> QtCore (QLibraryInfoPrivate::paths)
```

## 根本原因

PyInstaller 打包的 PyQt6 应用在 macOS 上无法正确定位 Qt 框架和插件路径，导致在初始化时访问空指针崩溃。

## 解决方案

### 1. 创建 PyInstaller Hooks

**hooks/hook-PyQt6.py**
- 收集 Qt6 插件和动态库

**hooks/runtime_hook_pyqt6.py**
- 在应用运行时设置 Qt 插件路径环境变量

### 2. 更新 app.spec

添加以下配置：
- 引入 `collect_data_files` 和 `collect_submodules`
- 收集 PyQt6.Qt6 插件数据
- 添加 PyQt6 所有子模块到 hiddenimports
- 设置 hookspath 为 'hooks' 目录
- 添加 runtime_hooks

### 3. 更新 main.py

在应用启动前添加 macOS 特定的 Qt 路径配置：
- `QT_PLUGIN_PATH`: Qt 插件根目录
- `QT_QPA_PLATFORM_PLUGIN_PATH`: 平台插件目录
- `DYLD_FRAMEWORK_PATH`: Qt 框架路径

## 修复文件清单

1. **新增文件**
   - `hooks/hook-PyQt6.py`
   - `hooks/runtime_hook_pyqt6.py`

2. **修改文件**
   - `app.spec` - 添加 Qt hooks 和插件收集
   - `src/main.py` - 添加 macOS Qt 路径配置
   - `src/services/ai_providers/dashscope_provider.py` - 修复图片格式检测

## 重新打包

修复后需要重新打包应用：

```bash
# 本地测试
pyinstaller app.spec

# 或者推送新标签触发 GitHub Actions
bash scripts/release.sh
```

## 验证

打包后的应用应该能够正常启动，不再出现 `EXC_BAD_ACCESS` 错误。

## 技术细节

### Qt 插件系统

Qt 使用插件系统来加载平台特定的功能（如窗口系统、主题等）。在 macOS 上，Qt 需要：

1. **平台插件** (`platforms/libqcocoa.dylib`): macOS 原生窗口系统支持
2. **样式插件** (`styles/`): macOS 原生外观主题
3. **图片格式插件** (`imageformats/`): PNG, JPEG 等格式支持

### PyInstaller 打包问题

PyInstaller 在打包 Qt 应用时，需要明确告知：
- 哪些插件需要被包含
- 运行时如何定位这些插件

如果配置不当，Qt 会在初始化时尝试访问不存在的路径，导致崩溃。

### 环境变量作用

- `QT_PLUGIN_PATH`: 告诉 Qt 在哪里查找插件
- `QT_QPA_PLATFORM_PLUGIN_PATH`: 指定平台插件（QPA = Qt Platform Abstraction）
- `DYLD_FRAMEWORK_PATH`: macOS 动态链接器查找框架的路径

## 相关资源

- [PyInstaller Qt6 支持文档](https://pyinstaller.org/en/stable/runtime-information.html#qt6-support)
- [Qt 插件系统](https://doc.qt.io/qt-6/plugins-howto.html)
- [macOS 代码签名和公证](https://developer.apple.com/documentation/xcode/notarizing_macos_software_before_distribution)
