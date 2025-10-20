#!/bin/bash
# ==============================================================================
# HunyuanImage-3.0 容器启动脚本
# 支持三种运行模式：CLI、API、bash
# ==============================================================================

set -e

MODEL_PATH="/app/models/HunyuanImage-3.0"
WORKDIR="/app/HunyuanImage-3.0"

cd "$WORKDIR"

# 检查GPU是否可用
echo "========================================="
echo "检查GPU环境..."
echo "========================================="
nvidia-smi || echo "警告: nvidia-smi 命令失败，请确保--gpus参数正确"
echo ""

# 检查模型文件
echo "========================================="
echo "检查模型文件..."
echo "========================================="
if [ ! -d "$MODEL_PATH" ]; then
    echo "错误: 模型文件不存在于 $MODEL_PATH"
    echo "请确保Docker镜像正确构建"
    exit 1
fi
echo "✓ 模型文件已找到"
echo ""

# 根据第一个参数选择运行模式
MODE="${1:-api}"

case "$MODE" in
    "api")
        echo "========================================="
        echo "启动API服务模式"
        echo "========================================="
        echo "API将监听在 http://0.0.0.0:8000"
        echo "文档地址: http://0.0.0.0:8000/docs"
        echo ""
        exec python3 /app/api_server.py
        ;;

    "cli")
        echo "========================================="
        echo "CLI命令行模式"
        echo "========================================="
        shift  # 移除第一个参数(cli)

        if [ $# -eq 0 ]; then
            echo "用法: docker run ... cli --prompt '你的提示词' [其他参数]"
            echo ""
            echo "示例:"
            echo "  docker run ... cli --prompt '一只可爱的小猫' --output ./output.jpg"
            echo ""
            echo "可用参数请运行: docker run ... cli --help"
            exit 1
        fi

        exec python3 run_image_gen.py --model-id "$MODEL_PATH" "$@"
        ;;

    "bash")
        echo "========================================="
        echo "进入容器Shell"
        echo "========================================="
        echo "模型路径: $MODEL_PATH"
        echo "工作目录: $WORKDIR"
        echo ""
        exec /bin/bash
        ;;

    *)
        echo "错误: 未知的运行模式 '$MODE'"
        echo ""
        echo "可用模式:"
        echo "  api  - 启动RESTful API服务 (默认)"
        echo "  cli  - 命令行生成模式"
        echo "  bash - 进入容器Shell"
        echo ""
        echo "示例:"
        echo "  docker run ... api"
        echo "  docker run ... cli --prompt '提示词'"
        echo "  docker run ... bash"
        exit 1
        ;;
esac
