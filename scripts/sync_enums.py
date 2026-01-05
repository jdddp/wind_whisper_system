#!/usr/bin/env python3
"""
枚举值同步脚本
将配置文件中的标准枚举值同步到数据库
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.manage_enum import EnumManager
from config.enum_config import EVENT_SEVERITY_VALUES, EVENT_TYPE_VALUES

def sync_event_severity():
    """同步事件严重程度枚举"""
    print("=== 同步事件严重程度枚举 ===")
    manager = EnumManager()
    
    # 获取当前数据库中的值
    current_values = manager.list_enum_values('eventseverity')
    print(f"当前数据库值: {current_values}")
    print(f"标准配置值: {EVENT_SEVERITY_VALUES}")
    
    # 添加缺失的值
    for value in EVENT_SEVERITY_VALUES:
        if value not in current_values:
            print(f"添加缺失的枚举值: {value}")
            manager.add_enum_value(value, 'eventseverity')
    
    # 检查多余的值
    extra_values = [v for v in current_values if v not in EVENT_SEVERITY_VALUES]
    if extra_values:
        print(f"数据库中存在额外的值: {extra_values}")
        print("如需清理，请使用 recreate 命令重建枚举")
    
    print("事件严重程度枚举同步完成")
    print()

def sync_event_types():
    """同步事件类型枚举（如果存在的话）"""
    print("=== 检查事件类型枚举 ===")
    manager = EnumManager()
    
    # 检查是否存在 eventtype 枚举
    try:
        current_values = manager.list_enum_values('eventtype')
        if current_values:
            print(f"当前 eventtype 枚举值: {current_values}")
            print(f"标准配置值: {EVENT_TYPE_VALUES}")
            
            # 添加缺失的值
            for value in EVENT_TYPE_VALUES:
                if value not in current_values:
                    print(f"添加缺失的枚举值: {value}")
                    manager.add_enum_value(value, 'eventtype')
        else:
            print("数据库中不存在 eventtype 枚举")
    except Exception as e:
        print(f"eventtype 枚举不存在或查询失败: {e}")
    
    print()

def clean_test_values():
    """清理测试值"""
    print("=== 清理测试值 ===")
    manager = EnumManager()
    
    current_values = manager.list_enum_values('eventseverity')
    test_values = [v for v in current_values if 'TEST' in v.upper()]
    
    if test_values:
        print(f"发现测试值: {test_values}")
        clean_values = [v for v in current_values if 'TEST' not in v.upper()]
        print(f"清理后的值: {clean_values}")
        
        confirm = input("是否清理测试值并重建枚举？(y/N): ")
        if confirm.lower() == 'y':
            manager.recreate_enum('eventseverity', clean_values)
            print("测试值清理完成")
        else:
            print("跳过清理")
    else:
        print("未发现测试值")
    
    print()

def main():
    print("数据库枚举值同步工具")
    print("=" * 40)
    
    if len(sys.argv) > 1 and sys.argv[1] == 'clean':
        clean_test_values()
    
    sync_event_severity()
    sync_event_types()
    
    print("同步完成！")
    print()
    print("使用说明:")
    print("  python scripts/sync_enums.py        # 同步枚举值")
    print("  python scripts/sync_enums.py clean  # 清理测试值并同步")

if __name__ == "__main__":
    main()