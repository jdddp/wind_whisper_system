# Wind Whisper RAG System - Docker Compose 部署指南

## 概述

本系统采用单容器架构，所有组件（包括应用、pgvector数据库等）都打包在一个Docker镜像中，简化了部署和管理。

## 前提条件

- Docker 已安装
- Docker Compose 已安装
- 基础镜像 `wind-whisper-rag-ready:latest` 已准备好

## 快速部署

### 1. 加载基础镜像（如果需要）

如果您有镜像tar文件：
```bash
docker load -i wind-whisper-rag-ready.tar
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
# 创建必要目录
mkdir -p data/attachments logs

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

### docker-compose.ready.yml
- 专门为基础镜像优化的配置文件
- 移除了不必要的代码映射和AI模型映射

## 端口映射

- `8000`: 主要API服务端口
- `8001`: 备用服务端口
- `8003`: 额外服务端口

## 数据持久化

- `postgres_data`: PostgreSQL数据库数据
- `./data/attachments`: 附件存储
- `./logs`: 应用日志

## 环境变量

可以通过修改docker-compose文件或创建`.env`文件来配置：

```bash
JWT_SECRET_KEY=your-secret-key-change-in-production
OPENAI_API_KEY=your-openai-api-key
OPENAI_BASE_URL=https://api.openai.com/v1
```

## 访问服务

部署成功后，可以通过以下地址访问：

- 主服务: http://localhost:8000
- API文档: http://localhost:8000/docs
- 健康检查: http://localhost:8000/health

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

## 升级部署

1. 停止现有服务：
```bash
./deploy_compose.sh stop
```

2. 更新镜像：
```bash
docker load -i new-wind-whisper-rag-ready.tar
```

3. 重新启动：
```bash
./deploy_compose.sh start
```

## 备份与恢复

### 备份数据
```bash
# 备份数据库
docker-compose exec app pg_dump -U postgres wind_whisper_rag > backup.sql

# 备份附件
tar -czf attachments_backup.tar.gz data/attachments/
```

### 恢复数据
```bash
# 恢复数据库
docker-compose exec -T app psql -U postgres wind_whisper_rag < backup.sql

# 恢复附件
tar -xzf attachments_backup.tar.gz
```

## 监控与维护

### 查看资源使用
```bash
docker stats wind-whisper-rag-ready
```

### 清理日志
```bash
# 清理Docker日志
docker system prune -f

# 清理应用日志
find logs/ -name "*.log" -mtime +7 -delete
```

## 联系支持

如有问题，请检查：
1. 系统日志：`./deploy_compose.sh logs`
2. 容器状态：`./deploy_compose.sh status`
3. 系统资源：`docker stats`