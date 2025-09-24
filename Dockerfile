#===============================================================================
# Wind Whisper RAG System - Docker镜像构建文件
#===============================================================================
#
# 功能描述:
#   构建包含完整RAG系统的Docker镜像，集成以下组件：
#   - PyTorch深度学习框架（支持CUDA加速）
#   - PostgreSQL数据库（含pgvector向量扩展）
#   - FastAPI Web应用服务
#   - Supervisor进程管理器
#
# 基础镜像:
#   pytorch/pytorch:2.6.0-cuda11.8-cudnn9-runtime
#   - PyTorch 2.6.0 (支持CUDA 11.8)
#   - CUDNN 9 (GPU加速库)
#   - Ubuntu 20.04 LTS
#
# 构建命令:
#   docker build -t wind-whisper-rag:latest .
#
# 运行命令:
#   docker run -d -p 8003:8003 -v $(pwd):/app wind-whisper-rag:latest
#
# 作者: Wind Whisper Team
# 版本: 2.0.0
# 更新时间: 2024-01-20
#===============================================================================

# 基础镜像 - PyTorch官方镜像，支持CUDA加速
FROM pytorch/pytorch:2.6.0-cuda11.8-cudnn9-runtime

#===============================================================================
# 环境配置
#===============================================================================

# 设置环境变量避免交互式提示
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Asia/Shanghai
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# 设置工作目录
WORKDIR /app

#===============================================================================
# 系统依赖安装
#===============================================================================

# 更新包管理器并安装系统依赖
# - postgresql: PostgreSQL数据库服务器
# - postgresql-contrib: PostgreSQL扩展包
# - postgresql-server-dev-all: PostgreSQL开发头文件
# - supervisor: 进程管理器
# - git: 版本控制工具
# - build-essential: 编译工具链
RUN apt-get update && apt-get install -y \
    postgresql \
    postgresql-contrib \
    postgresql-server-dev-all \
    supervisor \
    git \
    build-essential \
    curl \
    wget \
    vim \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

#===============================================================================
# pgvector扩展安装
#===============================================================================

# 复制本地pgvector源码并编译安装
# pgvector是PostgreSQL的向量相似度搜索扩展，为RAG系统提供向量存储能力
COPY pgvector /tmp/pgvector
RUN cd /tmp/pgvector \
    && make clean \
    && make \
    && make install \
    && cd / \
    && rm -rf /tmp/pgvector \
    && echo "pgvector扩展安装完成"

#===============================================================================
# Python依赖安装
#===============================================================================

# 复制Python依赖文件并安装
# 使用阿里云镜像源加速下载
COPY requirements.txt .
RUN pip3 install --upgrade pip \
    && pip3 install --no-cache-dir -r requirements.txt \
        -i https://mirrors.aliyun.com/pypi/simple/ \
        --trusted-host mirrors.aliyun.com \
    && pip3 list \
    && echo "Python依赖安装完成"

#===============================================================================
# 目录结构创建
#===============================================================================

# 创建应用运行所需的目录结构
# 注意：应用代码通过docker-compose卷映射，不在镜像中复制
RUN mkdir -p \
    /app/data/attachments \
    /app/data/uploads \
    /app/data/knowledge_base \
    /app/logs \
    /app/temp \
    && chmod -R 755 /app/data \
    && chmod -R 755 /app/logs \
    && echo "目录结构创建完成"

#===============================================================================
# PostgreSQL数据库配置
#===============================================================================

# 切换到postgres用户进行数据库初始化
USER postgres

# 启动PostgreSQL服务并进行初始化配置
# - 设置postgres用户密码
# - 创建应用数据库
RUN /etc/init.d/postgresql start && \
    echo "正在配置PostgreSQL数据库..." && \
    psql --command "ALTER USER postgres PASSWORD 'postgres123';" && \
    psql --command "CREATE DATABASE wind_whisper_rag OWNER postgres;" && \
    psql --command "GRANT ALL PRIVILEGES ON DATABASE wind_whisper_rag TO postgres;" && \
    echo "PostgreSQL数据库配置完成"

# 切换回root用户
USER root

#===============================================================================
# Supervisor进程管理配置
#===============================================================================

# 创建Supervisor配置文件
# Supervisor用于管理多个服务进程：PostgreSQL、初始化脚本、Web应用
RUN echo "正在创建Supervisor配置..." && \
    echo '[supervisord]' > /etc/supervisor/conf.d/supervisord.conf && \
    echo 'nodaemon=true' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo 'user=root' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo 'logfile=/var/log/supervisor/supervisord.log' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo 'pidfile=/var/run/supervisord.pid' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo '' >> /etc/supervisor/conf.d/supervisord.conf && \
    \
    echo '# PostgreSQL数据库服务' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo '[program:postgresql]' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo 'command=/usr/lib/postgresql/14/bin/postgres -D /var/lib/postgresql/14/main -c config_file=/etc/postgresql/14/main/postgresql.conf' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo 'user=postgres' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo 'autostart=true' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo 'autorestart=true' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo 'redirect_stderr=true' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo 'stdout_logfile=/var/log/supervisor/postgresql.log' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo 'priority=100' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo '' >> /etc/supervisor/conf.d/supervisord.conf && \
    \
    echo '# 系统初始化脚本（一次性执行）' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo '[program:init_admin]' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo 'command=python3 /app/scripts/init_admin.py' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo 'directory=/app' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo 'user=root' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo 'autostart=true' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo 'autorestart=false' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo 'startsecs=0' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo 'startretries=1' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo 'exitcodes=0' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo 'redirect_stderr=true' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo 'stdout_logfile=/var/log/supervisor/init_admin.log' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo 'environment=DATABASE_URL="postgresql://postgres:postgres123@localhost:5432/wind_whisper_rag"' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo 'priority=200' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo '' >> /etc/supervisor/conf.d/supervisord.conf && \
    \
    echo '# FastAPI Web应用服务' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo '[program:app]' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo 'command=uvicorn main:app --host 0.0.0.0 --port 8003 --reload' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo 'directory=/app' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo 'user=root' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo 'autostart=true' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo 'autorestart=true' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo 'redirect_stderr=true' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo 'stdout_logfile=/var/log/supervisor/app.log' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo 'environment=DATABASE_URL="postgresql://postgres:postgres123@localhost:5432/wind_whisper_rag"' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo 'priority=300' >> /etc/supervisor/conf.d/supervisord.conf && \
    echo "Supervisor配置创建完成"

# 创建日志目录
RUN mkdir -p /var/log/supervisor && \
    chmod 755 /var/log/supervisor

#===============================================================================
# 容器运行配置
#===============================================================================

# 暴露Web应用端口
EXPOSE 8003

# 设置健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8003/health || exit 1

# 启动Supervisor进程管理器
# Supervisor将自动启动并管理所有配置的服务
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]