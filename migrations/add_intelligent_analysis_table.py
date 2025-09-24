"""
添加智能分析表的数据库迁移脚本
"""

from sqlalchemy import text
from models import engine, SessionLocal

def upgrade():
    """执行数据库升级"""
    with engine.connect() as connection:
        # 创建智能分析表
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS intelligent_analyses (
                analysis_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                turbine_id UUID NOT NULL REFERENCES turbines(turbine_id) ON DELETE CASCADE,
                analysis_mode VARCHAR(20) NOT NULL CHECK (analysis_mode IN ('llm', 'basic')),
                days_back INTEGER NOT NULL DEFAULT 30,
                summary TEXT NOT NULL,
                analysis_data JSONB,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE
            );
        """))
        
        # 创建索引以提高查询性能
        connection.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_intelligent_analyses_turbine_id 
            ON intelligent_analyses(turbine_id);
        """))
        
        connection.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_intelligent_analyses_created_at 
            ON intelligent_analyses(created_at DESC);
        """))
        
        # 为每个风机的最新分析创建唯一索引（确保每个风机只有一个最新分析）
        connection.execute(text("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_intelligent_analyses_latest_per_turbine 
            ON intelligent_analyses(turbine_id, analysis_mode) 
            WHERE created_at = (
                SELECT MAX(created_at) 
                FROM intelligent_analyses ia2 
                WHERE ia2.turbine_id = intelligent_analyses.turbine_id 
                AND ia2.analysis_mode = intelligent_analyses.analysis_mode
            );
        """))
        
        connection.commit()
        print("智能分析表创建成功")

def downgrade():
    """执行数据库降级"""
    with engine.connect() as connection:
        # 删除索引
        connection.execute(text("DROP INDEX IF EXISTS idx_intelligent_analyses_latest_per_turbine;"))
        connection.execute(text("DROP INDEX IF EXISTS idx_intelligent_analyses_created_at;"))
        connection.execute(text("DROP INDEX IF EXISTS idx_intelligent_analyses_turbine_id;"))
        
        # 删除表
        connection.execute(text("DROP TABLE IF EXISTS intelligent_analyses;"))
        
        connection.commit()
        print("智能分析表删除成功")

if __name__ == "__main__":
    upgrade()