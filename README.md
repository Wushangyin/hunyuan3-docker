# HunyuanImage-3.0 Docker部署指南

腾讯混元图像3.0（80B参数）的Docker容器化部署方案，支持一键构建和启动。

---

## 系统要求

### 硬件要求

| 组件 | 最低配置 | 推荐配置 |
|------|---------|---------|
| **GPU数量** | 3张 | 4张 |
| **单卡显存** | 80GB | 80GB |
| **总显存** | 240GB | 320GB |
| **内存** | 64GB | 128GB |
| **存储** | 200GB可用空间 | 300GB可用空间 |
| **CPU** | 16核 | 32核+ |

**说明**：
- 支持NVIDIA GPU（需支持CUDA 12.8+）
- 3卡240GB配置可运行但显存使用率高（97-98%），可能出现OOM
- 4卡320GB配置更稳定，推荐用于生产环境

### 软件要求

- **操作系统**: Linux (推荐 Ubuntu 22.04+)
- **Docker**: 24.0.0+
- **NVIDIA驱动**: 535.xx+
- **NVIDIA Container Toolkit**: 已安装

---

## 快速开始

### 1. 环境检查

```bash
# 检查GPU
nvidia-smi

# 检查Docker
docker --version

# 检查NVIDIA Container Toolkit
docker run --rm --gpus all nvidia/cuda:12.8.0-base-ubuntu22.04 nvidia-smi
```

如果缺少环境，请参考 [环境安装](#环境安装) 章节。

---

### 2. 构建镜像

```bash
# 克隆或解压项目文件
cd hunyuan3-docker/

# 开始构建（需要1-3小时，取决于网络速度）
docker build -t hunyuan-image-3.0:latest .
```

**构建过程说明**：
- 下载CUDA基础镜像 (~6GB)
- 安装PyTorch和依赖 (~2GB)
- 下载模型权重 (~170GB) ⚠️ 最耗时
- 安装性能优化组件

---

### 3. 启动服务

**方式A: 使用docker命令**

```bash
# 创建输出目录
mkdir -p ./outputs

# 启动API服务
docker run -d \
  --name hunyuan-api \
  --gpus all \
  -p 8000:8000 \
  -v $(pwd)/outputs:/app/outputs \
  --restart unless-stopped \
  hunyuan-image-3.0:latest
```

**方式B: 使用docker-compose（推荐）**

```bash
# 启动服务
docker compose up -d

# 查看日志
docker compose logs -f

# 停止服务
docker compose down
```

---

### 4. 测试API

```bash
# 健康检查
curl http://localhost:8000/health

# 生成图片
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "一只可爱的小猫在草地上玩耍，动漫风格",
    "image_size": "1024x1024",
    "diff_infer_steps": 50
  }'

# 访问API文档
open http://localhost:8000/docs
```

---

## 环境安装

### 安装Docker

```bash
# Ubuntu系统
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 将用户添加到docker组
sudo usermod -aG docker $USER

# 重新登录或刷新组
newgrp docker
```

### 安装NVIDIA Container Toolkit

```bash
# 添加仓库
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
  sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

# 安装
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit

# 配置Docker
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

# 验证
docker run --rm --gpus all nvidia/cuda:12.8.0-base-ubuntu22.04 nvidia-smi
```

---

## API使用说明

### API端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 服务信息 |
| `/health` | GET | 健康检查 |
| `/generate` | POST | 生成图片 |
| `/images/{filename}` | GET | 获取图片 |
| `/docs` | GET | Swagger API文档 |

### 生成图片示例

**基本用法**：

```bash
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "美丽的日落，金色的云朵，山脉轮廓",
    "image_size": "1024x1024",
    "diff_infer_steps": 50,
    "seed": 42
  }'
```

**响应示例**：

```json
{
  "task_id": "abc-123-def-456",
  "image_url": "/images/abc-123-def-456.png",
  "image_path": "/app/outputs/abc-123-def-456.png",
  "prompt": "美丽的日落...",
  "parameters": {
    "image_size": "1024x1024",
    "diff_infer_steps": 50,
    "seed": 42
  },
  "timestamp": "2025-10-20T10:30:00"
}
```

### 参数说明

| 参数 | 类型 | 必填 | 说明 | 默认值 |
|------|------|------|------|--------|
| `prompt` | string | ✅ | 文本提示词（中英文均可） | - |
| `image_size` | string | ❌ | 图片尺寸 | "auto" |
| `width` | int | ❌ | 图片宽度 (512-2048) | 1024 |
| `height` | int | ❌ | 图片高度 (512-2048) | 1024 |
| `diff_infer_steps` | int | ❌ | 推理步数 (1-100) | 50 |
| `seed` | int | ❌ | 随机种子（可复现） | 随机 |
| `bot_task` | string | ❌ | 任务类型 (image/auto/think/recaption) | "auto" |
| `use_system_prompt` | bool | ❌ | 是否使用系统提示词 | false |
| `system_prompt` | string | ❌ | 自定义系统提示词 | null |
| `verbose` | bool | ❌ | 显示详细进度信息 | true |
| `return_base64` | bool | ❌ | 返回base64编码 | false |

**图片尺寸选项**：
- `"auto"` - 自动选择最佳尺寸
- `"1024x1024"` - 正方形
- `"16:9"` - 宽屏
- `"9:16"` - 竖屏
- `"4:3"` - 横版
- `"3:4"` - 竖版

---

## 性能优化

### FlashAttention（3倍加速）

FlashAttention已在构建时自动安装。如果安装失败：

```bash
# 进入容器
docker exec -it hunyuan-api bash

# 手动安装
pip install flash-attn==2.8.3 --no-build-isolation

# 重启容器
exit
docker restart hunyuan-api
```

### GPU配置

**使用指定GPU**：

```bash
# 只使用GPU 0和1
docker run -d --gpus '"device=0,1"' -p 8000:8000 hunyuan-image-3.0:latest

# 只使用GPU 0
docker run -d --gpus '"device=0"' -p 8000:8000 hunyuan-image-3.0:latest
```

**监控GPU使用**：

```bash
# 实时监控
watch -n 1 nvidia-smi

# 查看容器资源
docker stats hunyuan-api
```

---

## 内网部署方案

### 方案1: 离线镜像包

**开发环境（有网）**：

```bash
# 1. 构建镜像
docker build -t hunyuan-image-3.0:latest .

# 2. 导出镜像（分卷压缩，每个10GB）
docker save hunyuan-image-3.0:latest | \
  gzip | \
  split -b 10G - hunyuan-image-3.0.tar.gz.part_

# 3. 生成校验和
sha256sum hunyuan-image-3.0.tar.gz.part_* > checksums.txt

# 4. 传输给客户（U盘/网盘）
```

**客户环境（内网）**：

```bash
# 1. 验证文件完整性
sha256sum -c checksums.txt

# 2. 合并并导入镜像
cat hunyuan-image-3.0.tar.gz.part_* | gunzip | docker load

# 3. 启动服务
docker compose up -d
```

### 方案2: 手动下载模型

如果网络不稳定，可以手动下载模型后挂载：

```bash
# 1. 手动下载模型（在有网环境）
pip install huggingface-hub
huggingface-cli download tencent/HunyuanImage-3.0 --local-dir ./models

# 2. 启动时挂载模型
docker run -d \
  --gpus all \
  -p 8000:8000 \
  -v $(pwd)/models:/app/models/HunyuanImage-3.0 \
  hunyuan-image-3.0:latest
```

---

## 常见问题

### Q1: 构建时模型下载失败

**症状**: `huggingface-cli download` 超时或失败

**解决方案**：

```bash
# 方法1: 使用国内镜像
export HF_ENDPOINT=https://hf-mirror.com
docker build -t hunyuan-image-3.0:latest .

# 方法2: 增加超时时间
# 在Dockerfile中的huggingface-cli命令后添加 --resume-download

# 方法3: 手动下载后挂载（参考内网部署方案2）
```

### Q2: GPU内存不足

**症状**: `CUDA out of memory`

**解决方案**：

```bash
# 1. 检查其他GPU进程
nvidia-smi

# 2. 释放GPU内存
sudo fuser -v /dev/nvidia*
# 杀掉不需要的进程

# 3. 使用更多GPU
docker run -d --gpus all ...  # 使用所有GPU

# 4. 减少并发请求
```

### Q3: 容器启动失败

**症状**: 容器无法启动或立即退出

**解决方案**：

```bash
# 1. 查看详细日志
docker logs hunyuan-api

# 2. 检查GPU是否可用
docker run --rm --gpus all nvidia/cuda:12.8.0-base-ubuntu22.04 nvidia-smi

# 3. 检查端口是否被占用
sudo netstat -tlnp | grep 8000

# 4. 进入容器调试
docker run -it --rm --gpus all hunyuan-image-3.0:latest bash
```

### Q4: 生成速度慢

**原因**: FlashAttention未安装

**解决方案**：

```bash
# 进入容器安装
docker exec -it hunyuan-api bash
pip install flash-attn==2.8.3 --no-build-isolation
exit

# 重启容器
docker restart hunyuan-api
```

### Q5: GitHub克隆失败（内网环境）

**症状**: `git clone github.com` 失败

**解决方案**：

提前在有网环境克隆代码，修改Dockerfile：

```dockerfile
# 注释掉 git clone 这一行
# RUN git clone https://github.com/Tencent-Hunyuan/HunyuanImage-3.0.git

# 改为复制本地代码
COPY HunyuanImage-3.0 /app/HunyuanImage-3.0
```

---

## 故障排除

### 检查清单

**环境检查**：
```bash
# ✅ GPU驱动
nvidia-smi

# ✅ Docker版本
docker --version  # 需要 >= 24.0

# ✅ NVIDIA Container Toolkit
docker run --rm --gpus all nvidia/cuda:12.8.0-base-ubuntu22.04 nvidia-smi

# ✅ 磁盘空间
df -h  # 至少200GB可用

# ✅ 内存
free -h  # 至少32GB

# ✅ 网络连接
ping -c 3 github.com
ping -c 3 huggingface.co
```

### 日志查看

```bash
# 查看容器日志
docker logs hunyuan-api

# 实时查看日志
docker logs -f hunyuan-api

# 查看最近100行
docker logs --tail 100 hunyuan-api

# 保存日志到文件
docker logs hunyuan-api > hunyuan.log 2>&1
```

### 重启服务

```bash
# 重启容器
docker restart hunyuan-api

# 完全重建
docker compose down
docker compose up -d

# 强制重建镜像
docker build --no-cache -t hunyuan-image-3.0:latest .
```

---

## 项目文件说明

```
hunyuan3-docker/
├── Dockerfile              # Docker镜像定义文件，包含CUDA环境、PyTorch安装、模型下载等构建步骤
├── docker-compose.yml      # Docker Compose编排配置，简化容器启动和GPU配置
├── requirements.txt        # Python依赖列表，Docker构建时自动安装
├── entrypoint.sh          # 容器启动脚本，支持API/CLI/Bash三种运行模式
├── api_server.py          # FastAPI服务实现，提供图片生成REST API接口
├── test_api.py            # API测试脚本，用于验证服务是否正常工作
├── .dockerignore          # Docker构建忽略文件，排除文档、缓存等不必要的文件
└── README.md              # 本文档，完整的部署和使用说明
```

---

## 技术栈

- **基础镜像**: nvidia/cuda:12.8.0-cudnn-devel-ubuntu22.04
- **深度学习框架**: PyTorch 2.7.1 (CUDA 12.8)
- **模型**: HunyuanImage-3.0 (80B MoE, Tencent)
- **API框架**: FastAPI + Uvicorn
- **性能优化**: FlashAttention 2.8.3, FlashInfer

---

## 性能指标

**典型生成时间**（4卡80GB GPU环境）：

| 分辨率 | 推理步数 | 生成时间 |
|--------|---------|---------|
| 512×512 | 50 | ~15秒 |
| 1024×1024 | 50 | ~30秒 |
| 1024×1024 | 100 | ~60秒 |
| 2048×2048 | 50 | ~90秒 |

**资源占用**：
- GPU显存: 每卡 30-40GB
- 系统内存: 20-30GB
- 磁盘空间: 120GB (镜像) + 输出图片

---

## 最佳实践

### 提示词建议

**好的提示词特点**：
- 详细描述场景、主体、背景
- 包含风格关键词（写实、动漫、油画等）
- 描述光线、色彩、构图

**示例**：
```
"一只橘色的小猫在绿色草地上玩耍，背景是蓝天白云，动漫风格，高清，细节丰富，柔和光线"
```

### 参数调优

- **快速预览**: `diff_infer_steps=20-30`
- **标准质量**: `diff_infer_steps=50`（推荐）
- **高质量**: `diff_infer_steps=100`
- **可复现**: 设置固定的 `seed` 值

### 批量生成

```python
import requests
import time

api_url = "http://localhost:8000/generate"

prompts = [
    "一只可爱的小猫",
    "美丽的日落",
    "未来城市"
]

for i, prompt in enumerate(prompts):
    response = requests.post(api_url, json={
        "prompt": prompt,
        "image_size": "1024x1024",
        "diff_infer_steps": 50
    })

    result = response.json()
    print(f"[{i+1}/{len(prompts)}] 生成完成: {result['image_url']}")
    time.sleep(2)  # 避免过载
```

---

## 维护建议

### 定期清理

```bash
# 清理旧的输出图片（保留30天内）
find ./outputs -type f -mtime +30 -delete

# 清理Docker缓存
docker system prune -f

# 查看Docker占用
docker system df
```

### 日志管理

docker-compose.yml 已配置日志轮转：
- 单个日志文件最大: 100MB
- 保留日志文件数: 5个

### 更新模型

```bash
# 停止服务
docker compose down

# 重新构建（下载最新模型）
docker build --no-cache -t hunyuan-image-3.0:latest .

# 启动服务
docker compose up -d
```

---

## 安全建议

1. **内网部署**: 避免将API直接暴露到公网
2. **反向代理**: 使用Nginx添加认证和限流
3. **HTTPS**: 生产环境启用TLS
4. **资源限制**: 配置Docker内存和CPU限制

**Nginx配置示例**：

```nginx
server {
    listen 80;
    server_name hunyuan.your-domain.com;

    client_max_body_size 50M;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 300s;

        # 限流
        limit_req zone=api burst=10 nodelay;
    }
}
```

---

## 版本信息

- **文档版本**: 1.2.0
- **更新日期**: 2025-10-25
- **模型版本**: HunyuanImage-3.0
- **Docker镜像**: hunyuan-image-3.0:latest

---

## 变更日志

### v1.2.0 (2025-10-25) - 官方标准对齐

**更新内容**：

1. **模型加载方式优化** ⭐ **重要更新**
   - 改用官方推荐的 `AutoModelForCausalLM` 加载方式
   - 添加 `trust_remote_code=True` 参数（官方要求）
   - 移除直接导入 `HunyuanImage3ForCausalMM` 的方式
   - 与GitHub官方仓库完全对齐

**影响**：
- ✅ 更符合官方最佳实践
- ✅ 提升未来兼容性和稳定性
- ✅ 代码更简洁易维护

**升级建议**：
重新构建镜像以应用此更新：
```bash
docker build -t hunyuan-image-3.0:latest .
```

### v1.1.0 (2025-10-23) - 兼容性修复

**修复内容**：

1. **Python版本升级**
   - 从 Python 3.10 升级到 Python 3.12（官方推荐版本）
   - 添加 deadsnakes PPA 源支持
   - 确保与官方要求完全匹配

2. **模型加载方式修复** ⚠️ **关键修复**
   - 修复模型导入：`AutoModelForCausalLM` → `HunyuanImage3ForCausalMM`
   - 使用官方正确的模型类：`from hunyuan_image_3.hunyuan import HunyuanImage3ForCausalMM`
   - 这是最关键的修复，之前的方式会导致模型无法加载

3. **API参数增强**
   - 新增 `bot_task` 参数：支持 image/auto/think/recaption 任务类型
   - 新增 `use_system_prompt` 参数：启用系统提示词功能
   - 新增 `system_prompt` 参数：自定义系统提示词
   - 新增 `verbose` 参数：控制详细进度显示
   - 更新 `image_size` 默认值为 "auto"（自动选择最佳尺寸）

4. **测试套件更新**
   - 添加高级参数测试用例
   - 测试新增的 bot_task 等参数
   - 从4个测试增加到5个测试

**影响**：
- ✅ 修复后的Docker镜像可以正常运行（不考虑硬件限制）
- ✅ 完全符合 HunyuanImage-3.0 官方要求
- ✅ API功能更加完善，支持更多官方特性

**升级建议**：
如果您之前构建过镜像，请重新构建以应用这些修复：
```bash
# 删除旧镜像
docker rmi hunyuan-image-3.0:latest

# 重新构建
docker build -t hunyuan-image-3.0:latest .
```

### v1.0.0 (2025-10-20) - 初始版本

- 基础Docker化部署方案
- FastAPI REST API服务
- 多GPU支持
- 基本测试套件

