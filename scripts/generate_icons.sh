#!/bin/bash

# 图标生成脚本
# 从源 PNG 图片生成各平台所需的图标文件

set -e

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_info() { echo -e "${YELLOW}ℹ️  $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }

# 获取脚本所在目录的父目录（项目根目录）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# 检查参数
if [ $# -eq 0 ]; then
    print_error "请提供源图片文件路径"
    echo "用法: $0 <源图片.png>"
    echo "示例: $0 ~/Desktop/icon.png"
    exit 1
fi

SOURCE_IMAGE="$1"

# 检查源文件是否存在
if [ ! -f "$SOURCE_IMAGE" ]; then
    print_error "文件不存在: $SOURCE_IMAGE"
    exit 1
fi

print_info "源图片: $SOURCE_IMAGE"

# 创建图标目录
ICON_DIR="resources/icons"
mkdir -p "$ICON_DIR"

# 生成 macOS 图标 (.icns)
print_info "生成 macOS 图标 (.icns)..."

# 创建临时图标集
ICONSET_DIR="icon.iconset"
mkdir -p "$ICONSET_DIR"

# 生成各种尺寸
sips -z 16 16     "$SOURCE_IMAGE" --out "$ICONSET_DIR/icon_16x16.png" > /dev/null 2>&1
sips -z 32 32     "$SOURCE_IMAGE" --out "$ICONSET_DIR/icon_16x16@2x.png" > /dev/null 2>&1
sips -z 32 32     "$SOURCE_IMAGE" --out "$ICONSET_DIR/icon_32x32.png" > /dev/null 2>&1
sips -z 64 64     "$SOURCE_IMAGE" --out "$ICONSET_DIR/icon_32x32@2x.png" > /dev/null 2>&1
sips -z 128 128   "$SOURCE_IMAGE" --out "$ICONSET_DIR/icon_128x128.png" > /dev/null 2>&1
sips -z 256 256   "$SOURCE_IMAGE" --out "$ICONSET_DIR/icon_128x128@2x.png" > /dev/null 2>&1
sips -z 256 256   "$SOURCE_IMAGE" --out "$ICONSET_DIR/icon_256x256.png" > /dev/null 2>&1
sips -z 512 512   "$SOURCE_IMAGE" --out "$ICONSET_DIR/icon_256x256@2x.png" > /dev/null 2>&1
sips -z 512 512   "$SOURCE_IMAGE" --out "$ICONSET_DIR/icon_512x512.png" > /dev/null 2>&1
sips -z 1024 1024 "$SOURCE_IMAGE" --out "$ICONSET_DIR/icon_512x512@2x.png" > /dev/null 2>&1

# 生成 .icns
iconutil -c icns "$ICONSET_DIR" -o "$ICON_DIR/icon.icns"
rm -rf "$ICONSET_DIR"
print_success "macOS 图标已生成: $ICON_DIR/icon.icns"

# 生成 Windows 图标 (.ico)
print_info "生成 Windows 图标 (.ico)..."

# 检查 ImageMagick 是否安装
if command -v convert &> /dev/null; then
    convert "$SOURCE_IMAGE" -define icon:auto-resize=256,128,64,48,32,16 "$ICON_DIR/icon.ico"
    print_success "Windows 图标已生成: $ICON_DIR/icon.ico"
else
    print_info "未安装 ImageMagick，跳过 .ico 生成"
    print_info "安装方法: brew install imagemagick"
    print_info "或使用在线工具: https://cloudconvert.com/png-to-ico"
fi

# 复制 Linux 图标 (PNG)
print_info "生成 Linux 图标 (.png)..."
cp "$SOURCE_IMAGE" "$ICON_DIR/icon.png"
print_success "Linux 图标已生成: $ICON_DIR/icon.png"

echo ""
print_success "🎉 所有图标已生成完成！"
echo ""
echo "生成的文件："
ls -lh "$ICON_DIR/"
echo ""
print_info "现在可以运行 pyinstaller app.spec 打包应用了"
