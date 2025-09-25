#!/usr/bin/env python3
"""
数据库清空脚本 - Wind Whisper RAG System
============================================

功能描述：
- 清空时间线事件、专家记录、风机数据等业务数据
- 保留用户账户数据（可选）
- 按正确的外键依赖顺序删除，避免约束冲突
- 提供安全确认机制，防止误删

使用方式：
    python scripts/clear_database.py [--include-users] [--force]

参数说明：
    --include-users: 同时删除用户数据（默认保留）
    --force: 跳过确认提示，直接执行删除

注意事项：
- 此操作不可逆，请谨慎使用
- 建议在执行前备份重要数据
- 生产环境请勿使用此脚本

作者：Wind Whisper Team
版本：v1.0.0
"""

import os
import sys
import argparse
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import Base
from models.turbine import Turbine
from models.timeline import TimelineEvent, TimelineSourceLog
from models.expert_log import ExpertLog
from models.attachment import Attachment
from models.log_chunk import LogChunk
from models.intelligent_analysis import IntelligentAnalysis
from models.user import User

def get_database_url():
    """获取数据库连接URL"""
    # 从环境变量读取
    database_url = os.getenv('DATABASE_URL')
    if database_url:
        return database_url
    
    # 默认配置（与docker-compose.yml保持一致）
    return 'postgresql://postgres:postgres123@localhost:5432/wind_whisper_rag'

def confirm_deletion(include_users=False):
    """确认删除操作"""
    print("=" * 60)
    print("🚨 数据库清空操作确认")
    print("=" * 60)
    print()
    print("⚠️  警告：此操作将永久删除以下数据：")
    print("   • 所有时间线事件记录")
    print("   • 所有专家日志记录")
    print("   • 所有风机数据")
    print("   • 所有附件文件记录")
    print("   • 所有智能分析结果")
    
    if include_users:
        print("   • 所有用户账户数据")
    else:
        print("   • 保留用户账户数据")
    
    print()
    print("💡 建议：执行前请确保已备份重要数据")
    print()
    
    # 三次确认机制
    confirmations = [
        "确认要清空数据库吗？(yes/no): ",
        "您确定要继续吗？此操作不可撤销！(yes/no): ",
        "最后确认：真的要删除所有数据吗？(yes/no): "
    ]
    
    for i, prompt in enumerate(confirmations, 1):
        response = input(f"[{i}/3] {prompt}").strip().lower()
        if response not in ['yes', 'y']:
            print("❌ 操作已取消")
            return False
    
    print("✅ 确认删除，开始执行...")
    return True

def get_table_counts(session):
    """获取各表的记录数量"""
    tables = [
        ('timeline_source_logs', '时间线源日志'),
        ('timeline_events', '时间线事件'),
        ('attachments', '附件'),
        ('log_chunks', '日志块'),
        ('expert_logs', '专家日志'),
        ('intelligent_analyses', '智能分析'),
        ('turbines', '风机'),
        ('users', '用户')
    ]
    
    counts = {}
    for table_name, display_name in tables:
        try:
            result = session.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
            count = result.scalar()
            counts[table_name] = {'count': count, 'display': display_name}
        except Exception as e:
            counts[table_name] = {'count': 0, 'display': display_name, 'error': str(e)}
    
    return counts

def clear_database(include_users=False, force=False):
    """清空数据库"""
    try:
        # 获取数据库连接
        database_url = get_database_url()
        engine = create_engine(database_url)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        session = SessionLocal()
        
        print(f"🔗 连接数据库: {database_url.split('@')[1] if '@' in database_url else database_url}")
        
        # 获取删除前的数据统计
        print("\n📊 删除前数据统计:")
        before_counts = get_table_counts(session)
        for table_name, info in before_counts.items():
            if 'error' in info:
                print(f"   {info['display']}: 查询失败 ({info['error']})")
            else:
                print(f"   {info['display']}: {info['count']} 条记录")
        
        # 确认删除
        if not force and not confirm_deletion(include_users):
            return False
        
        print(f"\n🗑️  开始清空数据库... ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")
        
        # 按依赖关系顺序删除数据
        deletion_steps = [
            (TimelineSourceLog, "时间线源日志关联"),
            (TimelineEvent, "时间线事件"),
            (Attachment, "附件记录"),
            (LogChunk, "日志向量块"),
            (ExpertLog, "专家日志"),
            (IntelligentAnalysis, "智能分析结果"),
            (Turbine, "风机数据")
        ]
        
        if include_users:
            deletion_steps.append((User, "用户账户"))
        
        deleted_counts = {}
        
        for model_class, description in deletion_steps:
            try:
                # 获取删除前数量
                count_before = session.query(model_class).count()
                
                if count_before > 0:
                    print(f"   正在删除 {description}... ({count_before} 条记录)")
                    
                    # 执行删除
                    deleted = session.query(model_class).delete()
                    session.commit()
                    
                    deleted_counts[description] = deleted
                    print(f"   ✅ 已删除 {description}: {deleted} 条记录")
                else:
                    print(f"   ⏭️  跳过 {description}: 无数据")
                    deleted_counts[description] = 0
                    
            except Exception as e:
                print(f"   ❌ 删除 {description} 失败: {str(e)}")
                session.rollback()
                raise e
        
        # 获取删除后的数据统计
        print("\n📊 删除后数据统计:")
        after_counts = get_table_counts(session)
        for table_name, info in after_counts.items():
            if 'error' in info:
                print(f"   {info['display']}: 查询失败 ({info['error']})")
            else:
                print(f"   {info['display']}: {info['count']} 条记录")
        
        # 总结
        print(f"\n✅ 数据库清空完成! ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")
        print("\n📈 删除统计:")
        total_deleted = 0
        for description, count in deleted_counts.items():
            print(f"   {description}: {count} 条")
            total_deleted += count
        print(f"   总计删除: {total_deleted} 条记录")
        
        session.close()
        return True
        
    except Exception as e:
        print(f"\n❌ 数据库清空失败: {str(e)}")
        if 'session' in locals():
            session.rollback()
            session.close()
        return False

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="Wind Whisper RAG System - 数据库清空工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python scripts/clear_database.py                    # 清空业务数据，保留用户
  python scripts/clear_database.py --include-users    # 清空所有数据，包括用户
  python scripts/clear_database.py --force            # 跳过确认，直接执行

注意事项:
  • 此操作不可逆，请谨慎使用
  • 建议在执行前备份重要数据
  • 生产环境请勿使用此脚本
        """
    )
    
    parser.add_argument(
        '--include-users',
        action='store_true',
        help='同时删除用户数据（默认保留用户账户）'
    )
    
    parser.add_argument(
        '--force',
        action='store_true',
        help='跳过确认提示，直接执行删除'
    )
    
    args = parser.parse_args()
    
    print("🌪️  Wind Whisper RAG System - 数据库清空工具")
    print("=" * 60)
    
    # 执行清空操作
    success = clear_database(
        include_users=args.include_users,
        force=args.force
    )
    
    if success:
        print("\n🎉 操作完成！数据库已成功清空。")
        sys.exit(0)
    else:
        print("\n💥 操作失败或被取消。")
        sys.exit(1)

if __name__ == "__main__":
    main()