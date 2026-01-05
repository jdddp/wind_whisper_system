#!/bin/bash
# ===========================================================================
# Wind Whisper RAG System - Database Backup Script
# ===========================================================================
#
# 功能描述：
#   - 备份PostgreSQL数据库到指定文件
#
# 使用方式：
#   ./scripts/backup.sh
#
# ===========================================================================

# 数据库连接信息
DB_USER="postgres"
DB_PASS="postgres123"
DB_NAME="wind_whisper_rag"
DB_HOST="localhost"
DB_PORT="5432"

# 备份文件路径
BACKUP_DIR="/suanfa-1/jzp/wind_whisper_rag_system-debug/backups"
BACKUP_FILE="$BACKUP_DIR/backup_$(date +%Y%m%d_%H%M%S).sql"

# 创建备份目录
mkdir -p $BACKUP_DIR

# 执行备份
PGPASSWORD=$DB_PASS pg_dump -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -F c -b -v -f $BACKUP_FILE

# 检查备份是否成功
if [ $? -eq 0 ]; then
  echo "Database backup successful: $BACKUP_FILE"
else
  echo "Database backup failed"
fi