#!/usr/bin/env python3
"""
数据库枚举值维护脚本
用于管理 eventseverity 枚举类型
"""

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import os
import sys
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class EnumManager:
    def __init__(self):
        self.db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': os.getenv('DB_PORT', '5432'),
            'database': os.getenv('DB_NAME', 'wind_whisper_rag'),
            'user': os.getenv('DB_USER', 'postgres'),
            'password': os.getenv('DB_PASSWORD', 'postgres123')
        }
    
    def connect(self):
        """连接数据库"""
        try:
            conn = psycopg2.connect(**self.db_config)
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            return conn
        except Exception as e:
            print(f"数据库连接失败: {e}")
            return None
    
    def list_enum_values(self, enum_name='eventseverity'):
        """列出枚举值"""
        conn = self.connect()
        if not conn:
            return []
        
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT enumlabel 
                FROM pg_enum 
                WHERE enumtypid = (
                    SELECT oid 
                    FROM pg_type 
                    WHERE typname = %s
                )
                ORDER BY enumsortorder;
            """, (enum_name,))
            
            values = [row[0] for row in cursor.fetchall()]
            cursor.close()
            conn.close()
            return values
        except Exception as e:
            print(f"查询枚举值失败: {e}")
            return []
    
    def add_enum_value(self, value, enum_name='eventseverity'):
        """添加枚举值"""
        conn = self.connect()
        if not conn:
            return False
        
        try:
            cursor = conn.cursor()
            cursor.execute(f"ALTER TYPE {enum_name} ADD VALUE IF NOT EXISTS %s;", (value,))
            print(f"成功添加枚举值: {value}")
            cursor.close()
            conn.close()
            return True
        except Exception as e:
            print(f"添加枚举值失败: {e}")
            return False
    
    def recreate_enum(self, enum_name, new_values):
        """重建枚举类型（用于删除不需要的值）"""
        conn = self.connect()
        if not conn:
            return False
        
        try:
            cursor = conn.cursor()
            
            # 创建新的枚举类型
            new_enum_name = f"{enum_name}_new"
            values_str = "', '".join(new_values)
            cursor.execute(f"CREATE TYPE {new_enum_name} AS ENUM ('{values_str}');")
            print(f"创建新枚举类型: {new_enum_name}")
            
            # 更新表结构（需要根据实际表结构调整）
            cursor.execute(f"""
                ALTER TABLE timeline_events 
                ALTER COLUMN event_severity TYPE {new_enum_name} 
                USING event_severity::text::{new_enum_name};
            """)
            print("更新表结构")
            
            # 删除旧枚举类型
            cursor.execute(f"DROP TYPE {enum_name};")
            print(f"删除旧枚举类型: {enum_name}")
            
            # 重命名新枚举类型
            cursor.execute(f"ALTER TYPE {new_enum_name} RENAME TO {enum_name};")
            print(f"重命名枚举类型: {new_enum_name} -> {enum_name}")
            
            cursor.close()
            conn.close()
            return True
        except Exception as e:
            print(f"重建枚举类型失败: {e}")
            return False

def main():
    if len(sys.argv) < 2:
        print("用法:")
        print("  python manage_enum.py list                    # 列出所有枚举值")
        print("  python manage_enum.py add <value>             # 添加枚举值")
        print("  python manage_enum.py recreate <val1,val2>    # 重建枚举（用逗号分隔值）")
        return
    
    manager = EnumManager()
    command = sys.argv[1]
    
    if command == 'list':
        values = manager.list_enum_values()
        print("当前 eventseverity 枚举值:")
        for i, value in enumerate(values, 1):
            print(f"  {i}. {value}")
    
    elif command == 'add':
        if len(sys.argv) < 3:
            print("请提供要添加的枚举值")
            return
        value = sys.argv[2]
        manager.add_enum_value(value)
    
    elif command == 'recreate':
        if len(sys.argv) < 3:
            print("请提供新的枚举值列表（用逗号分隔）")
            return
        new_values = [v.strip() for v in sys.argv[2].split(',')]
        print(f"将重建枚举，新值: {new_values}")
        confirm = input("确认操作？(y/N): ")
        if confirm.lower() == 'y':
            manager.recreate_enum('eventseverity', new_values)
        else:
            print("操作已取消")
    
    else:
        print(f"未知命令: {command}")

if __name__ == "__main__":
    main()