# ==============================================
# 病理AI药研情报库 - Docker镜像 (P8标准)
# ==============================================
# 特性：
# - 多阶段构建减小镜像体积
# - 非root用户运行（安全）
# - 健康检查完善
# - 优化Python包安装
# ==============================================

# ==================== 阶段1: 构建阶段 ====================
FROM python:3.10-slim AS builder

# 设置构建参数
ARG BUILD_DATE
ARG VERSION=dev
ARG VCS_REF

# 添加元数据标签
LABEL org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.title="Pathology AI Backend" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.authors="pathology-ai-team" \
      org.opencontainers.image.vendor="Pathology AI"

# 设置工作目录
WORKDIR /build

# 安装构建依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖到临时目录
RUN pip install --user --no-cache-dir -r requirements.txt && \
    pip cache purge

# ==================== 阶段2: 运行阶段 ====================
FROM python:3.10-slim AS runtime

# 安全标签
LABEL maintainer="pathology-ai-team" \
      security.scan="enabled" \
      security.base-image="python:3.10-slim"

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH="/home/appuser/.local/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1

# 安装运行时依赖（最小化）
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq5 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 创建非特权用户（安全最佳实践）
RUN groupadd -r appuser && \
    useradd -r -g appuser -s /bin/bash -d /app appuser && \
    mkdir -p /app/logs /app/static && \
    chown -R appuser:appuser /app

# 从构建阶段复制Python包
COPY --from=builder /root/.local /home/appuser/.local

# 设置工作目录
WORKDIR /app

# 复制应用代码
COPY --chown=appuser:appuser . .

# 创建必要的目录
RUN mkdir -p logs static && \
    chown -R appuser:appuser /app

# 切换到非root用户
USER appuser

# 暴露端口
EXPOSE 8000

# 健康检查（多重检查）
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 启动命令（使用gunicorn生产级服务器）
CMD ["gunicorn", "main:app", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "2", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--worker-connections", "1000", \
     "--max-requests", "10000", \
     "--max-requests-jitter", "1000", \
     "--timeout", "60", \
     "--keep-alive", "5", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--log-level", "info"]
