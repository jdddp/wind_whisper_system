#!/bin/bash
# ===========================================================================
# Wind Whisper RAG System - Remote Sync Backup Script
# ===========================================================================
#
# 功能描述：
#   - 增量备份：使用 rsync 将整个工程目录（含 ./pg_data 数据库文件）同步到远程服务器
#   - 数据一致性：为了确保数据库文件不损坏，rsync 前必须停止服务，同步完自动重启
#
# 使用前提：
#   1. 已完成 SSH 免密登录配置 (ssh-copy-id)
#   2. 目标服务器已创建好存放目录
#
# ===========================================================================

# --- 配置区域 (请修改以下内容) ---
REMOTE_USER="jzp"
REMOTE_HOST="192.168.3.33"  # 请修改为您的远程服务器IP
REMOTE_DIR="/home/raid5/data_80suanfa/P2401002-风机监测产品项目/JZP/姜志鹏交接内容/2风机产线/4产线琐事/2风机专家知识管理平台/wind_whisper_rag_system" # 远程存放路径
SSH_PRIVATE_KEY="/home/jzp/.ssh/id_rsa" # SSH私钥路径，请确保该文件存在且权限为600
# -----------------------------

# 获取脚本所在目录的上一级目录（即项目根目录）
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_FILE="$PROJECT_DIR/logs/remote_sync_backup.log"

# 确保日志目录存在
mkdir -p "$(dirname "$LOG_FILE")"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "Starting backup sync process..."
log "Project Directory: $PROJECT_DIR"

# 1. 切换到项目目录
cd "$PROJECT_DIR" || { log "Error: Could not change to project directory"; exit 1; }

# 2. 停止服务 (CRITICAL STEP)
# 必须停止服务，否则正在写入的数据库文件同步过去后会损坏，无法启动！
log "Stopping services for safe backup..."
docker compose down >> "$LOG_FILE" 2>&1

# 3. 执行 Rsync 增量同步
# -a: 归档模式 (保留所有权限、时间戳、所有者等，对数据库文件至关重要)
# -v: 详细输出
# -z: 压缩传输
# --delete: 删除远程有但本地没有的文件 (保持完全一致的镜像)
# --exclude: 排除不需要的临时文件
log "Syncing files to ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_DIR}..."

# 检查私钥是否存在
if [ ! -f "$SSH_PRIVATE_KEY" ]; then
    log "Warning: SSH private key not found at $SSH_PRIVATE_KEY. Authentication may fail if not using agent."
fi

# 构建 SSH 选项
# -o BatchMode=yes: 禁止交互式密码输入
# -o StrictHostKeyChecking=no: 自动接受新主机指纹 (避免首次连接卡住)
# -i $SSH_PRIVATE_KEY: 指定私钥文件
SSH_OPTS="ssh -o BatchMode=yes -o StrictHostKeyChecking=no -i $SSH_PRIVATE_KEY"

sudo -n rsync -avz --delete -e "$SSH_OPTS" \
    --exclude '.git' \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude 'logs/*.log' \
    --exclude '*.out' \
    ./ \
    "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_DIR}" >> "$LOG_FILE" 2>&1

SYNC_STATUS=$?

if [ $SYNC_STATUS -eq 0 ]; then
    log "Rsync completed successfully."
else
    log "Error: Rsync failed with exit code $SYNC_STATUS"
fi

# 4. 重新启动服务
log "Restarting services..."
docker compose up -d >> "$LOG_FILE" 2>&1

log "Backup sync process finished."