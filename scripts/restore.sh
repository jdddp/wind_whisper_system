#!/bin/bash
# ===========================================================================
# Wind Whisper RAG System - Database Restore Script
# ===========================================================================
#
# 功能描述：
#   - 从备份文件恢复PostgreSQL数据库
#
# 使用方式：
#   ./scripts/restore.sh /path/to/your/backup.sql
#
# ===========================================================================

# 数据库连接信息
DB_USER="postgres"
DB_PASS="postgres123"
DB_NAME="wind_whisper_rag"
DB_HOST="localhost"
DB_PORT="5432"

# 备份文件路径
BACKUP_FILE=$1

# 检查备份文件是否存在
if [ -z "$BACKUP_FILE" ]; then
  echo "Usage: $0 /path/to/your/backup.sql"
  exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
  echo "Backup file not found: $BACKUP_FILE"
  exit 1
fi

# 执行恢复
PGPASSWORD=$DB_PASS pg_restore -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c -v $BACKUP_FILE

# 检查恢复是否成功
if [ $? -eq 0 ]; then
  echo "Database restore successful from: $BACKUP_FILE"
else
  echo "Database restore failed"
fi