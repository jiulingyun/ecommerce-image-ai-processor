# 打包和发布指南

本文档说明如何使用自动化工具打包和发布应用程序。

## 📦 自动化打包流程

项目使用 GitHub Actions 自动构建 Windows、macOS 和 Linux 三个平台的安装包。

### 前置要求

1. 项目已推送到 GitHub
2. 本地已安装 git
3. 有推送权限

### 发布步骤

#### 1. 更新版本号

编辑项目根目录下的 `VERSION` 文件：

```bash
echo "1.0.1" > VERSION
```

#### 2. 提交所有更改

```bash
git add .
git commit -m "Release v1.0.1"
```

#### 3. 运行发布脚本

```bash
./scripts/release.sh
```

脚本会自动执行以下操作：
- ✅ 检查是否有未提交的修改
- ✅ 检查是否有未推送的提交
- ✅ 推送所有提交到远端
- ✅ 根据 VERSION 文件创建标签（如 `v1.0.1`）
- ✅ 检查并处理已存在的标签（本地和远端）
- ✅ 推送标签触发 GitHub Actions

#### 4. 等待构建完成

推送标签后，GitHub Actions 会自动开始构建：

1. 访问 GitHub Actions 页面查看进度：
   ```
   https://github.com/jiulingyun/ecommerce-image-ai-processor/actions
   ```

2. 构建完成后，自动创建 Release：
   ```
   https://github.com/jiulingyun/ecommerce-image-ai-processor/releases
   ```

3. 构建内容包括：
   - `ecommerce-image-processor-windows-v1.0.1.zip` - Windows 版本
   - `ecommerce-image-processor-macos-v1.0.1.zip` - macOS 版本
   - `ecommerce-image-processor-linux-v1.0.1.tar.gz` - Linux 版本

## 🛠️ 本地测试打包

如果需要在本地测试打包（不发布），可以手动运行 PyInstaller：

### 安装 PyInstaller

```bash
pip install pyinstaller
```

### 执行打包

```bash
pyinstaller app.spec
```

打包后的文件在 `dist/` 目录下。

### 测试运行

**macOS:**
```bash
open "dist/电商图片AI处理工具.app"
```

**Windows:**
```bash
dist\电商图片AI处理工具\电商图片AI处理工具.exe
```

**Linux:**
```bash
./dist/电商图片AI处理工具/电商图片AI处理工具
```

## 📝 发布清单

发布新版本前，请确保：

- [ ] 更新了 `VERSION` 文件
- [ ] 更新了 `CHANGELOG.md`（如有）
- [ ] 所有测试通过
- [ ] 文档已更新
- [ ] 所有修改已提交
- [ ] 在 `.github/workflows/build.yml` 的 Release body 中更新了更新日志

## 🔧 自定义配置

### 修改应用名称

编辑 `app.spec` 文件：

```python
app_name = '你的应用名称'
```

### 添加应用图标

1. 准备图标文件：
   - Windows: `.ico` 格式
   - macOS: `.icns` 格式
   - Linux: `.png` 格式

2. 修改 `app.spec`：
   ```python
   icon='path/to/icon.ico'  # Windows/Linux
   ```

3. macOS 的 BUNDLE 配置中设置：
   ```python
   app = BUNDLE(
       ...
       icon='path/to/icon.icns',
   )
   ```

### 排除不需要的依赖

编辑 `app.spec` 的 `excludes` 列表，添加不需要打包的模块：

```python
excludes = [
    'matplotlib',
    'numpy',
    'pandas',
    # 添加更多...
]
```

## 🐛 常见问题

### Q: 构建失败怎么办？

A: 
1. 检查 GitHub Actions 日志查看具体错误
2. 确保 `requirements.txt` 包含所有依赖
3. 检查代码在目标平台上的兼容性

### Q: 如何删除已发布的 Release？

A: 
1. 在 GitHub Release 页面手动删除
2. 删除对应的 git 标签：
   ```bash
   git tag -d v1.0.1
   git push origin --delete v1.0.1
   ```

### Q: 如何跳过某个平台的构建？

A: 编辑 `.github/workflows/build.yml`，注释掉对应的 job。

## 📚 更多资源

- [PyInstaller 文档](https://pyinstaller.org/)
- [GitHub Actions 文档](https://docs.github.com/actions)
- [PyQt6 打包指南](https://www.riverbankcomputing.com/static/Docs/PyQt6/)
