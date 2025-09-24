"""
添加时间线表的数据库迁移脚本
"""

from sqlalchemy import text
from models import engine, SessionLocal

def upgrade():
    """执行数据库升级"""
    with engine.connect() as connection:
        # 创建时间线事件表
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS timeline_events (
                event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                turbine_id UUID NOT NULL REFERENCES turbines(turbine_id) ON DELETE CASCADE,
                event_time TIMESTAMP WITH TIME ZONE NOT NULL,
                event_type VARCHAR(20) NOT NULL CHECK (event_type IN ('maintenance', 'fault', 'inspection', 'repair', 'upgrade', 'monitoring', 'other')),
                event_severity VARCHAR(20) NOT NULL DEFAULT 'low' CHECK (event_severity IN ('low', 'medium', 'high', 'critical')),
                title VARCHAR(200) NOT NULL,
                summary TEXT NOT NULL,
                key_points JSONB,
                confidence_score NUMERIC(3,2) CHECK (confidence_score >= 0 AND confidence_score <= 1),
                is_verified BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE
            );
        """))
        
        # 创建时间线源记录关联表
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS timeline_source_logs (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                event_id UUID NOT NULL REFERENCES timeline_events(event_id) ON DELETE CASCADE,
                log_id UUID NOT NULL REFERENCES expert_logs(log_id) ON DELETE CASCADE,
                relevance_score NUMERIC(3,2) DEFAULT 1.0 CHECK (relevance_score >= 0 AND relevance_score <= 1),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                UNIQUE(event_id, log_id)
            );
        """))
        
        # 创建索引
        connection.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_timeline_events_turbine_id ON timeline_events(turbine_id);
        """))
        
        connection.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_timeline_events_event_time ON timeline_events(event_time);
        """))
        
        connection.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_timeline_events_event_type ON timeline_events(event_type);
        """))
        
        connection.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_timeline_source_logs_event_id ON timeline_source_logs(event_id);
        """))
        
        connection.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_timeline_source_logs_log_id ON timeline_source_logs(log_id);
        """))
        
        # 创建更新时间戳的触发器
        connection.execute(text("""
            CREATE OR REPLACE FUNCTION update_timeline_events_updated_at()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = NOW();
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """))
        
        connection.execute(text("""
            DROP TRIGGER IF EXISTS trigger_update_timeline_events_updated_at ON timeline_events;
            CREATE TRIGGER trigger_update_timeline_events_updated_at
                BEFORE UPDATE ON timeline_events
                FOR EACH ROW
                EXECUTE FUNCTION update_timeline_events_updated_at();
        """))
        
        connection.commit()
        print("时间线表创建成功")

def downgrade():
    """执行数据库降级"""
    with engine.connect() as connection:
        # 删除触发器和函数
        connection.execute(text("DROP TRIGGER IF EXISTS trigger_update_timeline_events_updated_at ON timeline_events;"))
        connection.execute(text("DROP FUNCTION IF EXISTS update_timeline_events_updated_at();"))
        
        # 删除表（注意顺序，先删除有外键的表）
        connection.execute(text("DROP TABLE IF EXISTS timeline_source_logs;"))
        connection.execute(text("DROP TABLE IF EXISTS timeline_events;"))
        
        connection.commit()
        print("时间线表删除成功")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "downgrade":
        downgrade()
    else:
        upgrade()