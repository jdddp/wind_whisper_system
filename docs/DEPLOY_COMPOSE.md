# Wind Whisper RAG System - Docker Compose 部署指南

## 概述

本系统采用单容器架构，所有组件（包括应用、pgvector数据库等）都打包在一个Docker镜像中，简化了部署和管理。

## 快速部署

### 1. 加载基础镜像（如果需要）

```bash
docker load -i wind-whisper-rag-env.tar
```

### 2. 使用部署脚本

```bash
# 启动服务
./deploy_compose.sh start

# 查看状态
./deploy_compose.sh status

# 查看日志
./deploy_compose.sh logs

# 停止服务
./deploy_compose.sh stop

# 重启服务
./deploy_compose.sh restart

# 清理所有数据
./deploy_compose.sh clean
```

### 3. 手动部署（可选）

如果不使用脚本，也可以手动执行：

```bash

# 启动服务
docker-compose up -d

# 查看状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

## 配置文件说明

### docker-compose.yml
- 主要的compose配置文件
- 已更新为使用基础镜像而不是构建

### docker-compose-src.yml
- 原始的非./pd_data得本地数据持久化的配置文件


## 环境变量

可以通过修改docker-compose文件或创建`.env`文件来配置：

```bash
JWT_SECRET_KEY=your-secret-key-change-in-production
OPENAI_API_KEY=your-openai-api-key
OPENAI_BASE_URL=https://api.openai.com/v1
```


## 故障排除

### 1. 镜像不存在
```bash
# 检查镜像
docker images | grep wind-whisper-rag

# 如果没有，需要先加载或构建镜像
```

### 2. 端口冲突
```bash
# 检查端口占用
netstat -tlnp | grep :8000

# 修改docker-compose.yml中的端口映射
```

### 3. 权限问题
```bash
# 设置目录权限
chmod -R 755 data/ logs/
```

### 4. 查看详细日志
```bash
# 查看容器日志
docker-compose logs app

# 进入容器调试
docker-compose exec app bash
```