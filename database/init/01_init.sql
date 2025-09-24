-- 启用pgvector扩展
CREATE EXTENSION IF NOT EXISTS vector;

-- 创建UUID扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 设置时区
SET timezone = 'Asia/Shanghai';