# ==============================================================================
# HunyuanImage-3.0 Docker Image
# 适用于多GPU环境
# ==============================================================================

FROM nvidia/cuda:12.8.0-cudnn-devel-ubuntu22.04

# 设置环境变量
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    CUDA_HOME=/usr/local/cuda \
    PATH=/usr/local/cuda/bin:$PATH \
    LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    software-properties-common \
    && add-apt-repository ppa:deadsnakes/ppa -y \
    && apt-get update && apt-get install -y \
    python3.12 \
    python3.12-dev \
    python3.12-distutils \
    python3-pip \
    git \
    wget \
    curl \
    vim \
    build-essential \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 设置Python 3.12为默认版本
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1 \
    && update-alternatives --set python3 /usr/bin/python3.12

# 升级pip
RUN pip3 install --no-cache-dir --upgrade pip setuptools wheel

# 安装PyTorch with CUDA 12.8
RUN pip3 install --no-cache-dir \
    torch==2.7.1 \
    torchvision==0.22.1 \
    torchaudio==2.7.1 \
    --index-url https://download.pytorch.org/whl/cu128

# 克隆HunyuanImage-3.0仓库
RUN git clone https://github.com/Tencent-Hunyuan/HunyuanImage-3.0.git /app/HunyuanImage-3.0

# 切换到项目目录
WORKDIR /app/HunyuanImage-3.0

# 安装腾讯云SDK
RUN pip3 install --no-cache-dir \
    -i https://mirrors.tencent.com/pypi/simple/ \
    --upgrade tencentcloud-sdk-python

# 安装项目依赖
COPY requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt || \
    pip3 install --no-cache-dir -r requirements.txt

# 安装性能优化组件（可选，加速推理3倍）
RUN pip3 install --no-cache-dir flash-attn==2.8.3 --no-build-isolation || \
    echo "Flash Attention installation failed, skipping..."

# 安装FlashInfer（用于MoE优化）
RUN pip3 install --no-cache-dir flashinfer || \
    echo "FlashInfer installation failed, skipping..."

# 下载模型权重（约170GB，这是镜像最大的部分）
# 使用huggingface-cli下载
RUN pip3 install --no-cache-dir huggingface-hub[cli] && \
    huggingface-cli download tencent/HunyuanImage-3.0 \
    --local-dir /app/models/HunyuanImage-3.0 \
    --local-dir-use-symlinks False

# 复制启动脚本和API服务代码
COPY entrypoint.sh /app/entrypoint.sh
COPY api_server.py /app/api_server.py
RUN chmod +x /app/entrypoint.sh

# 暴露API端口
EXPOSE 8000

# 设置入口点
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["api"]
