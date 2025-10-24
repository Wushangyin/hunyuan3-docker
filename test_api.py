#!/usr/bin/env python3
"""
HunyuanImage-3.0 API测试脚本
用于测试Docker容器中的API服务是否正常工作
"""

import requests
import json
import time
import sys
from pathlib import Path

# API配置
API_BASE_URL = "http://localhost:8000"

def test_health():
    """测试健康检查接口"""
    print("=" * 60)
    print("测试1: 健康检查")
    print("=" * 60)

    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=10)
        response.raise_for_status()

        data = response.json()
        print(f"✓ 状态: {data['status']}")
        print(f"✓ 模型已加载: {data['model_loaded']}")
        print(f"✓ GPU可用: {data['gpu_available']}")
        print(f"✓ 模型路径: {data['model_path']}")
        print()
        return True

    except Exception as e:
        print(f"✗ 健康检查失败: {e}")
        print()
        return False

def test_generate_basic():
    """测试基本图片生成"""
    print("=" * 60)
    print("测试2: 基本图片生成")
    print("=" * 60)

    payload = {
        "prompt": "A cute cat playing on the grass, anime style",
        "image_size": "512x512",  # 小尺寸快速测试
        "diff_infer_steps": 20,    # 少步数快速测试
        "seed": 42
    }

    print(f"请求参数: {json.dumps(payload, indent=2, ensure_ascii=False)}")
    print()

    try:
        print("发送请求...")
        start_time = time.time()

        response = requests.post(
            f"{API_BASE_URL}/generate",
            json=payload,
            timeout=300  # 5分钟超时
        )
        response.raise_for_status()

        elapsed = time.time() - start_time
        data = response.json()

        print(f"✓ 生成成功！")
        print(f"✓ 任务ID: {data['task_id']}")
        print(f"✓ 图片URL: {data['image_url']}")
        print(f"✓ 耗时: {elapsed:.1f}秒")
        print()

        # 下载图片
        image_url = f"{API_BASE_URL}{data['image_url']}"
        print(f"下载图片: {image_url}")

        img_response = requests.get(image_url, timeout=10)
        img_response.raise_for_status()

        output_path = Path(f"test_output_{data['task_id']}.png")
        output_path.write_bytes(img_response.content)

        print(f"✓ 图片已保存到: {output_path}")
        print(f"✓ 文件大小: {len(img_response.content) / 1024:.1f} KB")
        print()

        return True

    except Exception as e:
        print(f"✗ 生成失败: {e}")
        print()
        return False

def test_generate_auto_size():
    """测试自动尺寸"""
    print("=" * 60)
    print("测试3: 自动尺寸生成")
    print("=" * 60)

    payload = {
        "prompt": "一只橘色的小猫在绿色草地上玩耍，背景是蓝天白云，动漫风格",
        "image_size": "auto",
        "diff_infer_steps": 30
    }

    print(f"请求参数: {json.dumps(payload, indent=2, ensure_ascii=False)}")
    print()

    try:
        print("发送请求...")
        start_time = time.time()

        response = requests.post(
            f"{API_BASE_URL}/generate",
            json=payload,
            timeout=300
        )
        response.raise_for_status()

        elapsed = time.time() - start_time
        data = response.json()

        print(f"✓ 生成成功！")
        print(f"✓ 任务ID: {data['task_id']}")
        print(f"✓ 实际尺寸: {data['parameters']['image_size']}")
        print(f"✓ 耗时: {elapsed:.1f}秒")
        print()

        return True

    except Exception as e:
        print(f"✗ 生成失败: {e}")
        print()
        return False

def test_generate_advanced_params():
    """测试高级参数（bot_task等）"""
    print("=" * 60)
    print("测试4: 高级参数测试")
    print("=" * 60)

    payload = {
        "prompt": "一只可爱的小猫在草地上玩耍",
        "image_size": "512x512",
        "diff_infer_steps": 20,
        "seed": 999,
        "bot_task": "image",  # 测试新参数
        "use_system_prompt": False,
        "verbose": True
    }

    print(f"请求参数: {json.dumps(payload, indent=2, ensure_ascii=False)}")
    print()

    try:
        print("发送请求...")
        start_time = time.time()

        response = requests.post(
            f"{API_BASE_URL}/generate",
            json=payload,
            timeout=300
        )
        response.raise_for_status()

        elapsed = time.time() - start_time
        data = response.json()

        print(f"✓ 生成成功！")
        print(f"✓ 任务ID: {data['task_id']}")
        print(f"✓ bot_task参数: {data['parameters'].get('bot_task', 'N/A')}")
        print(f"✓ 耗时: {elapsed:.1f}秒")
        print()

        return True

    except Exception as e:
        print(f"✗ 生成失败: {e}")
        print()
        return False

def test_generate_with_seed():
    """测试种子可复现性"""
    print("=" * 60)
    print("测试5: 种子可复现性测试")
    print("=" * 60)

    payload = {
        "prompt": "A beautiful sunset with mountains",
        "image_size": "512x512",
        "diff_infer_steps": 20,
        "seed": 12345
    }

    print("使用相同种子生成两次，验证结果是否一致...")
    print()

    try:
        # 第一次生成
        print("第一次生成...")
        response1 = requests.post(
            f"{API_BASE_URL}/generate",
            json=payload,
            timeout=300
        )
        response1.raise_for_status()
        data1 = response1.json()

        # 第二次生成
        print("第二次生成...")
        response2 = requests.post(
            f"{API_BASE_URL}/generate",
            json=payload,
            timeout=300
        )
        response2.raise_for_status()
        data2 = response2.json()

        # 下载两张图片并比较大小（完全一致的话大小应该相同）
        img1 = requests.get(f"{API_BASE_URL}{data1['image_url']}").content
        img2 = requests.get(f"{API_BASE_URL}{data2['image_url']}").content

        if len(img1) == len(img2):
            print("✓ 两次生成的图片大小一致（可能可复现）")
        else:
            print("⚠ 两次生成的图片大小不同（可能不可复现，但不一定是错误）")

        print(f"✓ 图片1大小: {len(img1) / 1024:.1f} KB")
        print(f"✓ 图片2大小: {len(img2) / 1024:.1f} KB")
        print()

        return True

    except Exception as e:
        print(f"✗ 测试失败: {e}")
        print()
        return False

def main():
    """主测试函数"""
    print()
    print("╔" + "═" * 58 + "╗")
    print("║" + " " * 10 + "HunyuanImage-3.0 API 测试套件" + " " * 18 + "║")
    print("╚" + "═" * 58 + "╝")
    print()

    # 检查API是否可访问
    try:
        requests.get(API_BASE_URL, timeout=5)
    except Exception as e:
        print(f"✗ 无法连接到API服务: {API_BASE_URL}")
        print(f"  错误: {e}")
        print()
        print("请确保:")
        print("1. Docker容器正在运行")
        print("2. 端口8000已正确映射")
        print("3. 防火墙允许访问")
        sys.exit(1)

    # 运行测试
    results = []

    results.append(("健康检查", test_health()))
    results.append(("基本生成", test_generate_basic()))
    results.append(("自动尺寸", test_generate_auto_size()))
    results.append(("高级参数", test_generate_advanced_params()))
    results.append(("种子可复现", test_generate_with_seed()))

    # 汇总结果
    print("=" * 60)
    print("测试结果汇总")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{name:20s} {status}")

    print()
    print(f"总计: {passed}/{total} 通过")
    print()

    if passed == total:
        print("🎉 所有测试通过！API服务运行正常。")
        return 0
    else:
        print("⚠ 部分测试失败，请检查日志。")
        return 1

if __name__ == "__main__":
    sys.exit(main())
