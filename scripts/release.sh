#!/bin/bash

# 电商图片AI处理工具 - 自动化发布脚本
# 
# 功能：
# 1. 检查本地是否有未推送的提交
# 2. 推送所有未推送的内容
# 3. 根据 VERSION 文件创建 git 标签
# 4. 推送标签触发 GitHub Actions 自动打包

set -e  # 遇到错误立即退出

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 获取脚本所在目录的父目录（项目根目录）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

print_info "当前工作目录: $PROJECT_ROOT"

# 检查是否在 git 仓库中
if [ ! -d ".git" ]; then
    print_error "当前目录不是 git 仓库"
    exit 1
fi

# 读取版本号
if [ ! -f "VERSION" ]; then
    print_error "VERSION 文件不存在"
    exit 1
fi

VERSION=$(cat VERSION | tr -d '[:space:]')
TAG_NAME="v${VERSION}"

print_info "当前版本: $VERSION"
print_info "标签名称: $TAG_NAME"

# 同步更新 constants.py 中的版本号
CONSTANTS_FILE="src/utils/constants.py"
if [ -f "$CONSTANTS_FILE" ]; then
    print_info "更新 $CONSTANTS_FILE 中的 APP_VERSION..."
    
    # 使用 sed 替换版本号（兼容 macOS 和 Linux）
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' "s/APP_VERSION = \".*\"/APP_VERSION = \"$VERSION\"/" "$CONSTANTS_FILE"
    else
        # Linux
        sed -i "s/APP_VERSION = \".*\"/APP_VERSION = \"$VERSION\"/" "$CONSTANTS_FILE"
    fi
    
    # 检查是否成功更新
    if grep -q "APP_VERSION = \"$VERSION\"" "$CONSTANTS_FILE"; then
        print_success "APP_VERSION 已更新为 $VERSION"
        
        # 如果有变更，自动提交
        if ! git diff --quiet "$CONSTANTS_FILE"; then
            print_info "提交版本号更新..."
            git add "$CONSTANTS_FILE"
            git commit -m "chore: update version to $VERSION"
            print_success "版本号更新已提交"
        fi
    else
        print_error "APP_VERSION 更新失败"
        exit 1
    fi
else
    print_error "$CONSTANTS_FILE 文件不存在"
    exit 1
fi

# 检查是否有未提交的修改
if ! git diff-index --quiet HEAD -- 2>/dev/null; then
    print_warning "检测到未提交的修改，请先提交所有修改"
    echo ""
    git status --short
    echo ""
    read -p "是否继续？(y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "已取消发布"
        exit 0
    fi
fi

# 检查是否有未推送的提交
print_info "检查是否有未推送的提交..."
UNPUSHED=$(git log @{u}.. --oneline 2>/dev/null | wc -l | tr -d ' ')

if [ "$UNPUSHED" -gt 0 ]; then
    print_warning "检测到 $UNPUSHED 个未推送的提交"
    git log @{u}.. --oneline --decorate --color
    echo ""
    print_info "正在推送提交到远端..."
    
    # 获取当前分支名
    CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
    
    if git push origin "$CURRENT_BRANCH"; then
        print_success "成功推送所有提交"
    else
        print_error "推送失败，请检查网络连接和权限"
        exit 1
    fi
else
    print_success "所有提交已推送到远端"
fi

# 检查标签是否已存在（本地）
if git rev-parse "$TAG_NAME" >/dev/null 2>&1; then
    print_warning "标签 $TAG_NAME 已存在于本地"
    read -p "是否删除并重新创建？(y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "删除本地标签 $TAG_NAME"
        git tag -d "$TAG_NAME"
        print_success "本地标签已删除"
    else
        print_info "已取消发布"
        exit 0
    fi
fi

# 检查标签是否已存在（远端）
if git ls-remote --tags origin | grep -q "refs/tags/$TAG_NAME"; then
    print_warning "标签 $TAG_NAME 已存在于远端"
    read -p "是否删除远端标签并重新创建？(y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "删除远端标签 $TAG_NAME"
        if git push origin --delete "$TAG_NAME"; then
            print_success "远端标签已删除"
        else
            print_error "删除远端标签失败"
            exit 1
        fi
    else
        print_info "已取消发布"
        exit 0
    fi
fi

# 创建标签
print_info "创建标签 $TAG_NAME"
#
# 生成发布说明（RELEASE_NOTES.md）：从上一个 tag 到当前 HEAD 的提交摘录
LAST_TAG=$(git describe --tags --abbrev=0 2>/dev/null || true)
if [ -n "$LAST_TAG" ]; then
    print_info "生成发布说明：从 $LAST_TAG 到 HEAD 的提交记录"
    git log "$LAST_TAG"..HEAD --no-merges --pretty=format:"- %s (%an)" > RELEASE_NOTES.md || true
else
    print_info "未检测到上一个标签，生成最近 10 条提交作为发布说明"
    git log -n 10 --no-merges --pretty=format:"- %s (%an)" > RELEASE_NOTES.md || true
fi

# 添加标题和版本信息到发布说明顶部
printf "Release version %s\n\n" "$VERSION" > RELEASE_NOTES_HEADER.md
cat RELEASE_NOTES.md >> RELEASE_NOTES_HEADER.md
mv RELEASE_NOTES_HEADER.md RELEASE_NOTES.md

if git tag -a "$TAG_NAME" -F RELEASE_NOTES.md; then
    print_success "标签创建成功"
else
    print_error "标签创建失败"
    exit 1
fi

# 推送标签
print_info "推送标签到远端..."
if git push origin "$TAG_NAME"; then
    print_success "标签推送成功！"
    echo ""
    print_success "🎉 发布流程已启动！"
    echo ""
    print_info "GitHub Actions 将自动构建以下平台的安装包："
    echo "  • Windows (x64)"
    echo "  • macOS (Apple Silicon)"
    echo "  • Linux (x64)"
    echo ""
    print_info "构建完成后，Release 将自动发布到："
    print_info "https://github.com/jiulingyun/ecommerce-image-ai-processor/releases"
    echo ""
    print_info "你可以在以下地址查看构建进度："
    print_info "https://github.com/jiulingyun/ecommerce-image-ai-processor/actions"
else
    print_error "标签推送失败"
    print_info "清理本地标签..."
    git tag -d "$TAG_NAME"
    exit 1
fi
