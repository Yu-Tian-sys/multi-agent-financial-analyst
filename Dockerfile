# ========================================
# Stage 1: 构建前端
# ========================================
FROM node:20-alpine AS frontend-build

WORKDIR /app/frontend

# 先装依赖（利用 Docker 层缓存）
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install

# 复制源码并构建
COPY frontend/ ./
RUN npm run build


# ========================================
# Stage 2: 后端 + 前端静态文件
# ========================================
FROM python:3.11-slim

WORKDIR /app

# 系统依赖：chromadb / sentence-transformers / akshare 需要
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制后端源码
COPY src/ ./src/

# 复制前端构建产物（供 FastAPI 静态服务）
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

# 数据目录（SQLite + ChromaDB）
RUN mkdir -p /app/data /app/output

# 环境变量默认值（可被 docker-compose / .env 覆盖）
ENV DB_PATH=/app/data/agent.db
ENV CHROMA_PATH=/app/data/chroma
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 启动
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
