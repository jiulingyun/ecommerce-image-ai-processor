#!/usr/bin/env python3
"""AI 功能端到端演示脚本.

演示背景去除和商品合成功能。

Usage:
    python scripts/demo_ai_features.py

需要先配置 .env 文件中的 DASHSCOPE_API_KEY。
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
from PIL import Image
from pydantic import SecretStr

from src.models.api_config import APIConfig
from src.services.ai_service import AIService
from src.services.ai_providers import AIProviderType
from src.services.image_service import ImageService
from src.core.result_validator import validate_background_removal_result
from src.utils.image_utils import bytes_to_image, save_image


# 加载环境变量
load_dotenv()


def create_test_images(output_dir: Path) -> tuple[Path, Path]:
    """创建测试用图片.
    
    Returns:
        (背景图路径, 商品图路径)
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 创建模拟背景图 - 简单的室内场景
    bg = Image.new("RGB", (800, 600), (240, 235, 230))  # 米色背景
    # 添加一些简单的装饰
    from PIL import ImageDraw
    draw = ImageDraw.Draw(bg)
    # 画一个简单的桌面
    draw.rectangle([0, 400, 800, 600], fill=(139, 119, 101))  # 棕色桌面
    # 画窗户轮廓
    draw.rectangle([300, 50, 500, 250], outline=(100, 100, 100), width=3)
    draw.line([400, 50, 400, 250], fill=(100, 100, 100), width=2)
    draw.line([300, 150, 500, 150], fill=(100, 100, 100), width=2)
    
    bg_path = output_dir / "test_background.jpg"
    bg.save(bg_path, quality=95)
    print(f"✓ 创建背景图: {bg_path}")
    
    # 创建模拟商品图 - 红色商品盒子
    prod = Image.new("RGBA", (300, 300), (255, 255, 255, 0))  # 透明背景
    draw = ImageDraw.Draw(prod)
    # 画一个红色盒子
    draw.rectangle([50, 50, 250, 250], fill=(220, 60, 60, 255))
    # 添加高光
    draw.rectangle([50, 50, 250, 80], fill=(240, 100, 100, 255))
    # 添加阴影效果
    draw.rectangle([50, 220, 250, 250], fill=(180, 40, 40, 255))
    
    prod_path = output_dir / "test_product.png"
    prod.save(prod_path)
    print(f"✓ 创建商品图: {prod_path}")
    
    return bg_path, prod_path


async def demo_background_removal(
    ai_service: AIService,
    image_path: Path,
    output_dir: Path,
) -> Path | None:
    """演示背景去除功能."""
    print("\n" + "=" * 50)
    print("📸 测试背景去除功能")
    print("=" * 50)
    
    output_path = output_dir / "result_nobg.png"
    
    try:
        # 读取图片
        with open(image_path, "rb") as f:
            image_bytes = f.read()
        
        print(f"输入图片: {image_path}")
        print(f"文件大小: {len(image_bytes) / 1024:.1f} KB")
        print("正在调用 AI 服务...")
        
        # 调用背景去除
        result_bytes = await ai_service.remove_background(image_bytes)
        
        # 验证结果
        validation = validate_background_removal_result(result_bytes)
        print(f"验证状态: {validation.status.value}")
        if validation.has_warnings:
            for msg in validation.warning_messages:
                print(f"  ⚠️ {msg}")
        
        # 保存结果
        result_image = bytes_to_image(result_bytes)
        save_image(result_image, output_path)
        
        print(f"✅ 背景去除成功!")
        print(f"输出图片: {output_path}")
        print(f"输出尺寸: {result_image.size}")
        print(f"输出模式: {result_image.mode}")
        
        return output_path
        
    except Exception as e:
        print(f"❌ 背景去除失败: {e}")
        return None


async def demo_composite(
    ai_service: AIService,
    background_path: Path,
    product_path: Path,
    output_dir: Path,
) -> Path | None:
    """演示商品合成功能."""
    print("\n" + "=" * 50)
    print("🎨 测试商品合成功能")
    print("=" * 50)
    
    output_path = output_dir / "result_composite.png"
    
    try:
        # 读取图片
        with open(background_path, "rb") as f:
            bg_bytes = f.read()
        with open(product_path, "rb") as f:
            prod_bytes = f.read()
        
        print(f"背景图: {background_path}")
        print(f"商品图: {product_path}")
        print("正在调用 AI 服务进行合成...")
        
        # 调用合成
        result_bytes = await ai_service.composite_product(
            background=bg_bytes,
            product=prod_bytes,
            position_hint="center",
        )
        
        # 保存结果
        result_image = bytes_to_image(result_bytes)
        save_image(result_image, output_path)
        
        print(f"✅ 商品合成成功!")
        print(f"输出图片: {output_path}")
        print(f"输出尺寸: {result_image.size}")
        
        return output_path
        
    except Exception as e:
        print(f"❌ 商品合成失败: {e}")
        return None


async def demo_image_service(
    ai_service: AIService,
    background_path: Path,
    product_path: Path,
    output_dir: Path,
) -> None:
    """演示 ImageService 完整流程."""
    print("\n" + "=" * 50)
    print("🔄 测试 ImageService 完整流程")
    print("=" * 50)
    
    try:
        service = ImageService(ai_service=ai_service)
        
        # 测试背景去除
        print("\n1. 背景去除...")
        nobg_path = await service.remove_background(
            product_path,
            output_dir / "service_nobg.png",
            on_progress=lambda p, m: print(f"   [{p}%] {m}"),
        )
        print(f"   输出: {nobg_path}")
        
        # 测试合成
        print("\n2. 商品合成...")
        composite_path = await service.composite_product(
            background_path,
            product_path,
            output_dir / "service_composite.png",
            on_progress=lambda p, m: print(f"   [{p}%] {m}"),
        )
        print(f"   输出: {composite_path}")
        
        print("\n✅ ImageService 测试完成!")
        
    except Exception as e:
        print(f"❌ ImageService 测试失败: {e}")


async def main():
    """主函数."""
    print("=" * 50)
    print("🚀 AI 功能端到端演示 (阿里云百炼 DashScope)")
    print("=" * 50)
    
    # 检查 API Key - 支持 DASHSCOPE_API_KEY 或 OPENAI_API_KEY
    api_key = os.getenv("DASHSCOPE_API_KEY") or os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        print("❌ 错误: 未找到 DASHSCOPE_API_KEY 环境变量")
        print("请在 .env 文件中配置 DASHSCOPE_API_KEY")
        return
    
    print(f"提供者: 阿里云百炼 (DashScope)")
    print(f"模型: qwen-image-edit-plus")
    print(f"API Key: {api_key[:8]}...{api_key[-4:]}")
    
    # 创建输出目录
    output_dir = PROJECT_ROOT / "demo_output"
    output_dir.mkdir(exist_ok=True)
    print(f"输出目录: {output_dir}")
    
    # 创建测试图片
    print("\n📁 准备测试图片...")
    bg_path, prod_path = create_test_images(output_dir)
    
    # 创建 AI 服务 - 使用 DashScope 提供者
    config = APIConfig(
        api_key=SecretStr(api_key),
        timeout=120,  # 图片处理需要较长时间
    )
    ai_service = AIService(config, provider_type=AIProviderType.DASHSCOPE)
    
    # 健康检查
    print("\n🔍 检查 AI 服务连接...")
    is_healthy = await ai_service.health_check()
    if not is_healthy:
        print("⚠️ AI 服务健康检查未通过，但仍尝试继续...")
    else:
        print("✓ AI 服务连接正常")
    
    # 运行演示
    try:
        # 1. 背景去除
        await demo_background_removal(ai_service, prod_path, output_dir)
        
        # 2. 商品合成
        await demo_composite(ai_service, bg_path, prod_path, output_dir)
        
        # 3. ImageService 完整流程
        await demo_image_service(ai_service, bg_path, prod_path, output_dir)
        
    finally:
        await ai_service.close()
    
    print("\n" + "=" * 50)
    print("🎉 演示完成!")
    print(f"请查看输出目录: {output_dir}")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
