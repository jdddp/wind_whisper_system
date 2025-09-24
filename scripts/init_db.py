#!/usr/bin/env python3
"""
Wind Whisper RAG System - 数据库初始化脚本
===========================================

功能描述:
    完整的数据库初始化脚本，用于从零开始创建和配置数据库环境
    
主要功能:
    1. 创建数据库表结构
    2. 启用pgvector扩展
    3. 创建默认管理员用户
    4. 初始化示例风机数据
    5. 设置数据库索引和约束

使用场景:
    - 首次部署系统时的数据库初始化
    - 开发环境的数据库重置
    - 测试环境的数据准备
    - 数据库结构更新和迁移

执行方式:
    python scripts/init_db.py

前置条件:
    - PostgreSQL数据库服务已启动
    - 数据库连接参数正确配置
    - 具有数据库创建和修改权限
    - Python环境已安装必要依赖

注意事项:
    - 该脚本会删除现有数据，请谨慎使用
    - 建议在生产环境使用前进行充分测试
    - 确保数据库备份策略已就绪

作者: Wind Whisper Team
版本: 2.0.0
更新时间: 2024-01-20
许可证: MIT License
"""

import sys
import os
from pathlib import Path
import logging

#===============================================================================
# 项目路径配置
#===============================================================================

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

#===============================================================================
# 依赖导入
#===============================================================================

from sqlalchemy import text
from models import engine, Base, get_db
from models.user import User, UserRole
from models.turbine import Turbine
from utils.auth import get_password_hash

#===============================================================================
# 日志配置
#===============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('init_db.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

#===============================================================================
# 核心功能函数
#===============================================================================

def create_tables():
    """
    创建数据库表结构
    
    功能说明:
        - 使用SQLAlchemy ORM创建所有数据库表
        - 基于models目录中定义的数据模型
        - 自动处理表之间的外键关系
        - 支持幂等操作（重复执行安全）
    
    返回值:
        bool: 创建成功返回True，失败返回False
    
    涉及表:
        - users: 用户账户表
        - turbines: 风机设备表
        - documents: 文档管理表
        - knowledge_base: 知识库表
        - chat_sessions: 对话会话表
        - chat_messages: 对话消息表
    """
    print("🔄 开始创建数据库表结构...")
    
    try:
        # 显示将要创建的表
        tables_to_create = list(Base.metadata.tables.keys())
        print(f"📋 将创建 {len(tables_to_create)} 个数据表:")
        for table_name in tables_to_create:
            print(f"   - {table_name}")
        
        logger.info("开始创建数据库表...")
        
        # 创建所有表
        Base.metadata.create_all(bind=engine)
        
        # 验证表创建结果
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """))
            created_tables = [row[0] for row in result.fetchall()]
        
        print(f"✅ 数据库表创建完成，共创建 {len(created_tables)} 个表")
        for table_name in created_tables:
            print(f"   ✓ {table_name}")
        
        logger.info("数据库表创建完成")
        return True
        
    except Exception as e:
        print(f"❌ 创建数据库表失败: {e}")
        logger.error(f"创建数据库表失败: {e}")
        print("🔧 故障排除建议:")
        print("   1. 检查数据库连接权限")
        print("   2. 验证数据模型定义")
        print("   3. 确认数据库版本兼容性")
        return False

def enable_pgvector():
    """
    启用pgvector扩展
    
    功能说明:
        - 安装PostgreSQL的vector扩展
        - 支持向量相似度搜索功能
        - 为RAG系统提供向量存储能力
        - 启用向量索引和查询优化
    
    返回值:
        bool: 启用成功返回True，失败返回False
    
    依赖要求:
        - PostgreSQL 11+
        - pgvector扩展已安装
        - 数据库超级用户权限
    """
    print("🔄 启用pgvector扩展...")
    
    try:
        logger.info("启用pgvector扩展...")
        
        with engine.connect() as conn:
            # 检查扩展是否已安装
            result = conn.execute(text("""
                SELECT EXISTS(
                    SELECT 1 FROM pg_extension 
                    WHERE extname = 'vector'
                )
            """))
            
            extension_exists = result.scalar()
            
            if extension_exists:
                print("✅ pgvector扩展已存在")
                logger.info("pgvector扩展已存在")
            else:
                # 创建扩展
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                conn.commit()
                print("✅ pgvector扩展启用成功")
                logger.info("pgvector扩展启用成功")
            
            # 验证扩展功能
            conn.execute(text("SELECT vector_dims(ARRAY[1,2,3]::vector)"))
            print("✅ pgvector扩展功能验证通过")
            
        return True
        
    except Exception as e:
        print(f"❌ 启用pgvector扩展失败: {e}")
        logger.error(f"启用pgvector扩展失败: {e}")
        print("🔧 故障排除建议:")
        print("   1. 确认pgvector扩展已安装")
        print("   2. 检查数据库超级用户权限")
        print("   3. 验证PostgreSQL版本兼容性")
        print("   4. 参考pgvector官方安装文档")
        return False

def create_admin_user():
    """
    创建默认管理员用户
    
    功能说明:
        - 创建系统默认管理员账户
        - 设置超级用户权限
        - 配置默认密码（需要首次登录修改）
        - 支持幂等操作（避免重复创建）
    
    返回值:
        bool: 创建成功返回True，失败返回False
    
    默认账户信息:
        - 用户名: admin
        - 密码: admin123
        - 邮箱: admin@example.com
        - 权限: 超级管理员
    
    安全提醒:
        请在首次登录后立即修改默认密码！
    """
    print("🔄 创建默认管理员用户...")
    
    db = None
    try:
        logger.info("创建管理员用户...")
        
        # 获取数据库会话
        db = next(get_db())
        
        # 检查是否已存在管理员用户
        existing_user = db.query(User).filter(User.username == "admin").first()
        if existing_user:
            print(f"✅ 管理员用户 'admin' 已存在")
            print(f"   用户ID: {existing_user.id}")
            print(f"   权限: {existing_user.role}")
            logger.info("管理员用户已存在，跳过创建")
            return True
        
        # 创建管理员用户
        print(f"🔧 创建新的管理员用户: admin")
        
        hashed_password = get_password_hash("admin123")
        admin_user = User(
            username="admin",
            password_hash=hashed_password,
            role=UserRole.ADMIN
        )
        
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        
        print("✅ 管理员用户创建成功")
        print(f"   用户ID: {admin_user.id}")
        print(f"   用户名: {admin_user.username}")
        print(f"   权限: {admin_user.role}")
        print(f"   默认密码: admin123")
        print("")
        print("🔐 安全提醒:")
        print("   请立即登录系统修改默认密码！")
        print("   建议启用双因素认证增强安全性")
        
        logger.info("管理员用户创建成功")
        return True
        
    except Exception as e:
        print(f"❌ 创建管理员用户失败: {e}")
        logger.error(f"创建管理员用户失败: {e}")
        print("🔧 故障排除建议:")
        print("   1. 检查用户表是否已创建")
        print("   2. 验证密码哈希函数")
        print("   3. 确认数据库写入权限")
        if db:
            db.rollback()
        return False
    finally:
        if db:
            db.close()

def create_sample_turbines():
    """
    创建示例风机数据
    
    功能说明:
        - 创建多个示例风机设备记录
        - 包含不同品牌和型号的风机
        - 设置不同的地理位置和状态
        - 为系统演示和测试提供基础数据
    
    返回值:
        bool: 创建成功返回True，失败返回False
    
    示例数据包含:
        - 4台不同品牌的风机设备
        - 分布在海上和陆上风电场
        - 多种运行状态（运行中、维护中）
        - 完整的设备参数信息
    """
    print("🔄 创建示例风机数据...")
    
    db = None
    try:
        # 获取数据库会话
        db = next(get_db())
        
        # 检查是否已有风机数据
        existing_count = db.query(Turbine).count()
        if existing_count > 0:
            print(f"✅ 已存在 {existing_count} 台风机，跳过示例数据创建")
            logger.info(f"Found {existing_count} existing turbines, skipping sample data creation")
            return True
        
        logger.info("Creating sample turbines...")
        
        # 创建示例风机数据
        sample_turbines = [
            {
                "farm_name": "海上风电场A",
                "unit_id": "A01",
                "model": "GE 3.6-130",
                "capacity": 3.6,
                "installation_date": "2022-01-15",
                "status": "active"
            },
            {
                "farm_name": "海上风电场A", 
                "unit_id": "A02",
                "model": "GE 3.6-130",
                "capacity": 3.6,
                "installation_date": "2022-01-20",
                "status": "active"
            },
            {
                "farm_name": "陆上风电场B",
                "unit_id": "B01", 
                "model": "Vestas V120-2.2",
                "capacity": 2.2,
                "installation_date": "2021-08-10",
                "status": "active"
            },
            {
                "farm_name": "陆上风电场B",
                "unit_id": "B02",
                "model": "Vestas V120-2.2", 
                "capacity": 2.2,
                "installation_date": "2021-08-15",
                "status": "maintenance"
            }
        ]
        
        print(f"📋 将创建 {len(sample_turbines)} 台示例风机:")
        
        for turbine_data in sample_turbines:
            turbine = Turbine(**turbine_data)
            db.add(turbine)
            print(f"   + {turbine_data['unit_id']} ({turbine_data['model']}) - {turbine_data['status']}")
        
        db.commit()
        
        # 验证创建结果
        created_count = db.query(Turbine).count()
        print(f"✅ 示例风机数据创建完成，共创建 {created_count} 台风机")
        
        logger.info(f"Created {len(sample_turbines)} sample turbines")
        return True
        
    except Exception as e:
        print(f"❌ 创建示例风机数据失败: {e}")
        logger.error(f"Failed to create sample turbines: {e}")
        print("🔧 故障排除建议:")
        print("   1. 检查风机表是否已创建")
        print("   2. 验证数据模型定义")
        print("   3. 确认数据库写入权限")
        if db:
            db.rollback()
        return False
    finally:
        if db:
            db.close()

def main():
    """
    主函数 - 数据库初始化流程控制
    
    执行流程:
        1. 创建数据库表结构
        2. 启用pgvector扩展
        3. 创建默认管理员用户
        4. 创建示例风机数据
    
    退出码:
        0: 初始化成功
        1: 初始化失败
    """
    print("="*80)
    print("🚀 Wind Whisper RAG System 数据库初始化")
    print("="*80)
    print("")
    print("📋 初始化流程:")
    print("   1. 创建数据库表结构")
    print("   2. 启用pgvector扩展")
    print("   3. 创建默认管理员用户")
    print("   4. 创建示例风机数据")
    print("")
    print("="*80)
    
    try:
        logger.info("Starting database initialization...")
        
        # 第一步：创建数据库表
        print("\n🔄 步骤 1/4: 创建数据库表结构")
        if not create_tables():
            print("❌ 数据库表创建失败，初始化中止")
            return False
        
        # 第二步：启用pgvector扩展
        print("\n🔄 步骤 2/4: 启用pgvector扩展")
        if not enable_pgvector():
            print("❌ pgvector扩展启用失败，初始化中止")
            return False
        
        # 第三步：创建管理员用户
        print("\n🔄 步骤 3/4: 创建默认管理员用户")
        if not create_admin_user():
            print("❌ 管理员用户创建失败，初始化中止")
            return False
        
        # 第四步：创建示例数据
        print("\n🔄 步骤 4/4: 创建示例风机数据")
        if not create_sample_turbines():
            print("❌ 示例数据创建失败，初始化中止")
            return False
        
        # 初始化完成
        print("\n" + "="*80)
        print("🎉 数据库初始化完成！")
        print("="*80)
        print("")
        print("📋 初始化结果:")
        print("   ✅ 数据库表结构已创建")
        print("   ✅ pgvector扩展已启用")
        print("   ✅ 管理员用户已创建")
        print("   ✅ 示例数据已创建")
        print("")
        print("🔐 默认管理员账户:")
        print("   用户名: admin")
        print("   密码: admin123")
        print("")
        print("⚠️  安全提醒:")
        print("   请立即登录系统修改默认管理员密码！")
        print("")
        print("🌐 下一步:")
        print("   1. 启动应用服务")
        print("   2. 访问管理界面")
        print("   3. 修改默认密码")
        print("   4. 配置系统参数")
        print("="*80)
        
        logger.info("Database initialization completed successfully!")
        return True
        
    except KeyboardInterrupt:
        print("\n❌ 用户中断初始化过程")
        return False
    except Exception as e:
        print(f"\n❌ 数据库初始化失败: {e}")
        logger.error(f"Database initialization failed: {e}")
        print("🔧 请检查系统配置和日志信息")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)