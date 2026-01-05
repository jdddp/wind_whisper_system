"""
更新EventSeverity枚举，添加新的状态值
"""

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

def update_event_severity_enum():
    """更新EventSeverity枚举类型"""
    
    # 数据库连接参数
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': os.getenv('DB_PORT', '5432'),
        'database': os.getenv('DB_NAME', 'wind_whisper_rag'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', 'password')
    }
    
    try:
        # 连接数据库
        conn = psycopg2.connect(**db_config)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        print("正在更新EventSeverity枚举...")
        
        # 添加新的枚举值
        new_values = ['Normal', 'Watch', 'Alarm', 'Maintenance', 'Unknown']
        
        for value in new_values:
            try:
                cursor.execute(f"ALTER TYPE eventseverity ADD VALUE IF NOT EXISTS '{value}';")
                print(f"添加枚举值: {value}")
            except psycopg2.Error as e:
                if "already exists" in str(e):
                    print(f"枚举值 {value} 已存在，跳过")
                else:
                    print(f"添加枚举值 {value} 时出错: {e}")
        
        # 查询当前枚举值
        cursor.execute("""
            SELECT enumlabel 
            FROM pg_enum 
            WHERE enumtypid = (
                SELECT oid 
                FROM pg_type 
                WHERE typname = 'eventseverity'
            )
            ORDER BY enumsortorder;
        """)
        
        current_values = [row[0] for row in cursor.fetchall()]
        print(f"当前EventSeverity枚举值: {current_values}")
        
        cursor.close()
        conn.close()
        
        print("EventSeverity枚举更新完成！")
        return True
        
    except Exception as e:
        print(f"更新EventSeverity枚举失败: {e}")
        return False

if __name__ == "__main__":
    update_event_severity_enum()