#!/usr/bin/env python3
"""
HunyuanImage-3.0 API Server
提供RESTful API接口用于文生图服务
"""

import sys
import base64
import uuid
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
import uvicorn

# 添加HunyuanImage-3.0到Python路径
sys.path.insert(0, '/app/HunyuanImage-3.0')

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 全局变量
MODEL_PATH = "/app/models/HunyuanImage-3.0"
OUTPUT_DIR = Path("/app/outputs")
OUTPUT_DIR.mkdir(exist_ok=True)

# 创建FastAPI应用
app = FastAPI(
    title="HunyuanImage-3.0 API",
    description="腾讯混元图像3.0 文生图API服务",
    version="1.0.0"
)

# ============================================================================
# 请求/响应模型
# ============================================================================

class GenerateRequest(BaseModel):
    """图片生成请求"""
    prompt: str = Field(..., description="文本提示词（中英文均可）", min_length=1)
    width: Optional[int] = Field(1024, description="图片宽度", ge=512, le=2048)
    height: Optional[int] = Field(1024, description="图片高度", ge=512, le=2048)
    diff_infer_steps: Optional[int] = Field(50, description="推理步数（扩散步数）", ge=1, le=100)
    seed: Optional[int] = Field(None, description="随机种子（可选，用于可复现生成）")
    image_size: Optional[str] = Field("auto", description="图片尺寸（可选：'auto', '1024x1024', '16:9'等，优先级高于width/height）")
    bot_task: Optional[str] = Field("auto", description="任务类型：image, auto, think, recaption")
    use_system_prompt: Optional[bool] = Field(False, description="是否使用系统提示词")
    system_prompt: Optional[str] = Field(None, description="自定义系统提示词")
    verbose: Optional[bool] = Field(True, description="是否显示详细进度信息")
    return_base64: Optional[bool] = Field(False, description="是否返回base64编码的图片")

class GenerateResponse(BaseModel):
    """图片生成响应"""
    task_id: str = Field(..., description="任务ID")
    image_url: str = Field(..., description="图片访问URL")
    image_path: str = Field(..., description="服务器上的图片路径")
    image_base64: Optional[str] = Field(None, description="base64编码的图片（如果请求）")
    prompt: str = Field(..., description="使用的提示词")
    parameters: dict = Field(..., description="生成参数")
    timestamp: str = Field(..., description="生成时间")

class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    model_loaded: bool
    gpu_available: bool
    model_path: str

# ============================================================================
# 模型加载（延迟加载）
# ============================================================================

pipeline = None

def load_model():
    """加载HunyuanImage-3.0模型"""
    global pipeline

    if pipeline is not None:
        return

    logger.info("开始加载HunyuanImage-3.0模型...")
    logger.info(f"模型路径: {MODEL_PATH}")

    try:
        import torch
        from transformers import AutoModelForCausalLM

        # 检查FlashAttention和FlashInfer是否可用
        try:
            import flash_attn
            attn_impl = "flash_attention_2"
            logger.info("✓ FlashAttention已安装，使用flash_attention_2")
        except ImportError:
            attn_impl = "sdpa"
            logger.info("FlashAttention未安装，使用sdpa（速度较慢）")

        try:
            import flashinfer
            moe_impl = "flashinfer"
            logger.info("✓ FlashInfer已安装，使用flashinfer")
        except ImportError:
            moe_impl = "eager"
            logger.info("FlashInfer未安装，使用eager（速度较慢）")

        # 加载模型（使用官方推荐方式）
        logger.info("正在加载模型权重，这可能需要几分钟...")
        kwargs = dict(
            trust_remote_code=True,  # 官方要求的关键参数
            attn_implementation=attn_impl,
            torch_dtype="auto",
            device_map="auto",  # 自动分配到多GPU
            moe_impl=moe_impl
        )
        pipeline = AutoModelForCausalLM.from_pretrained(MODEL_PATH, **kwargs)

        # 加载tokenizer
        logger.info("正在加载tokenizer...")
        pipeline.load_tokenizer(MODEL_PATH)

        # 显示GPU信息
        if torch.cuda.device_count() > 1:
            logger.info(f"✓ 检测到{torch.cuda.device_count()}个GPU，模型已自动分布")
            for i in range(torch.cuda.device_count()):
                logger.info(f"  GPU {i}: {torch.cuda.get_device_name(i)}")

        logger.info("✓ 模型加载完成")

    except Exception as e:
        logger.error(f"模型加载失败: {e}")
        raise

# ============================================================================
# API端点
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """应用启动时的操作"""
    logger.info("=" * 60)
    logger.info("HunyuanImage-3.0 API服务启动中...")
    logger.info("=" * 60)

    # 检查GPU
    import torch
    if torch.cuda.is_available():
        logger.info(f"✓ 检测到 {torch.cuda.device_count()} 个GPU")
        for i in range(torch.cuda.device_count()):
            logger.info(f"  GPU {i}: {torch.cuda.get_device_name(i)}")
    else:
        logger.warning("⚠ 未检测到GPU")

    # 延迟加载模型（第一次请求时加载）
    logger.info("模型将在第一次请求时加载")
    logger.info("=" * 60)

@app.get("/", response_model=dict)
async def root():
    """根路径"""
    return {
        "name": "HunyuanImage-3.0 API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "generate": "/generate",
            "docs": "/docs"
        }
    }

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查"""
    import torch

    return HealthResponse(
        status="healthy",
        model_loaded=(pipeline is not None),
        gpu_available=torch.cuda.is_available(),
        model_path=MODEL_PATH
    )

@app.post("/generate", response_model=GenerateResponse)
async def generate_image(request: GenerateRequest, background_tasks: BackgroundTasks):
    """
    生成图片

    **示例请求:**
    ```json
    {
        "prompt": "一只可爱的小猫在草地上玩耍，动漫风格",
        "image_size": "1024x1024",
        "diff_infer_steps": 50,
        "seed": 42
    }
    ```

    **或使用宽高参数:**
    ```json
    {
        "prompt": "一只可爱的小猫在草地上玩耍，动漫风格",
        "width": 1024,
        "height": 1024,
        "diff_infer_steps": 50
    }
    ```

    **或使用自动尺寸:**
    ```json
    {
        "prompt": "一只可爱的小猫在草地上玩耍，动漫风格",
        "image_size": "auto",
        "diff_infer_steps": 50
    }
    ```
    """
    try:
        # 确保模型已加载
        if pipeline is None:
            logger.info("首次请求，正在加载模型...")
            load_model()

        # 生成任务ID
        task_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()

        # 构建输出文件路径
        output_filename = f"{task_id}.png"
        output_path = OUTPUT_DIR / output_filename

        logger.info(f"任务 {task_id}: 开始生成图片")
        logger.info(f"提示词: {request.prompt}")

        # 调用模型生成图片
        try:
            import torch

            # 构建图片尺寸参数
            # 优先使用image_size参数（如'auto', '16:9'），否则使用width和height
            if request.image_size:
                image_size = request.image_size
            else:
                image_size = f"{request.width}x{request.height}"

            logger.info(f"任务 {task_id}: 生成参数 - 尺寸:{image_size}, 步数:{request.diff_infer_steps}, 种子:{request.seed}, 任务类型:{request.bot_task}")

            # 使用HunyuanImage-3.0的generate_image方法
            image = pipeline.generate_image(
                prompt=request.prompt,
                seed=request.seed,
                image_size=image_size,
                diff_infer_steps=request.diff_infer_steps,
                bot_task=request.bot_task,
                use_system_prompt=request.use_system_prompt,
                system_prompt=request.system_prompt,
                verbose=request.verbose,
                stream=True  # 显示进度
            )

            # 保存图片
            image.save(str(output_path))
            logger.info(f"任务 {task_id}: 图片已保存到 {output_path}")

        except Exception as e:
            logger.error(f"任务 {task_id}: 生成失败 - {e}")
            raise HTTPException(status_code=500, detail=f"图片生成失败: {str(e)}")

        # 构建响应
        response_data = {
            "task_id": task_id,
            "image_url": f"/images/{output_filename}",
            "image_path": str(output_path),
            "prompt": request.prompt,
            "parameters": {
                "image_size": image_size,
                "diff_infer_steps": request.diff_infer_steps,
                "seed": request.seed,
                "bot_task": request.bot_task,
                "use_system_prompt": request.use_system_prompt,
                "verbose": request.verbose
            },
            "timestamp": timestamp
        }

        # 如果请求base64编码
        if request.return_base64:
            with open(output_path, "rb") as f:
                image_bytes = f.read()
                image_base64 = base64.b64encode(image_bytes).decode('utf-8')
                response_data["image_base64"] = image_base64

        return GenerateResponse(**response_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"请求处理失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/images/{filename}")
async def get_image(filename: str):
    """获取生成的图片"""
    image_path = OUTPUT_DIR / filename

    if not image_path.exists():
        raise HTTPException(status_code=404, detail="图片不存在")

    return FileResponse(image_path, media_type="image/png")

# ============================================================================
# 主程序
# ============================================================================

if __name__ == "__main__":
    # 启动服务
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
