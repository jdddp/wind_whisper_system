#!/usr/bin/env python3

#===============================================================================
# Wind Whisper RAG System 管理员账户初始化脚本
#===============================================================================
#
# 功能描述:
#   用于Docker容器启动时自动初始化系统管理员账户
#   包含数据库连接检查、扩展安装、数据迁移和管理员创建
#
# 使用场景:
#   1. Docker容器首次启动时自动执行
#   2. 系统部署后的初始化配置
#   3. 开发环境的快速搭建
#
# 执行流程:
#   1. 等待数据库服务启动
#   2. 安装pgvector扩展
#   3. 运行数据库迁移
#   4. 创建默认管理员账户
#
# 默认管理员账户:
#   用户名: admin
#   密码: admin123
#   角色: ADMIN
#
# 安全提醒:
#   生产环境部署后请立即修改默认密码！
#
# 作者: Wind Whisper Team
# 版本: v1.0
# 更新: 2024-01-20
#===============================================================================

import os
import sys
import asyncio
import time
import subprocess
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
import uuid
from datetime import datetime

#===============================================================================
# 配置变量
#===============================================================================

# 项目路径配置
PROJECT_ROOT = '/app'
sys.path.append(PROJECT_ROOT)

# 数据库连接配置
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://postgres:postgres123@localhost:5432/wind_whisper_rag"
)

# 数据库连接参数
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres123")
DB_NAME = os.getenv("DB_NAME", "wind_whisper_rag")

# 重试配置
MAX_RETRIES = 30           # 最大重试次数
RETRY_INTERVAL = 2         # 重试间隔(秒)

# 默认管理员配置
DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "admin123"

# 导入项目模块
try:
    from models.user import User, UserRole
    from utils.auth import get_password_hash
except ImportError as e:
    print(f"❌ 导入模块失败: {e}")
    print("请确保在项目根目录下运行此脚本")
    sys.exit(1)

#===============================================================================
# 核心功能函数
#===============================================================================

def create_admin_user():
    """
    创建默认管理员账户
    
    功能说明:
        - 检查是否已存在管理员账户
        - 创建默认管理员账户(如果不存在)
        - 设置默认用户名和密码
        - 分配管理员权限
    
    返回值:
        bool: 创建成功返回True，失败返回False
    
    安全提醒:
        默认密码为admin123，生产环境请立即修改！
    """
    print("🔐 开始创建管理员账户...")
    
    try:
        # 创建数据库引擎和会话
        print(f"🔗 连接数据库: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'localhost'}")
        engine = create_engine(DATABASE_URL)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        with SessionLocal() as db:
            # 检查是否已存在管理员账户
            print(f"🔍 检查管理员账户: {DEFAULT_ADMIN_USERNAME}")
            existing_admin = db.query(User).filter(
                User.username == DEFAULT_ADMIN_USERNAME
            ).first()
            
            if existing_admin:
                print("✅ 管理员账户已存在，跳过创建")
                print(f"   账户ID: {existing_admin.user_id}")
                print(f"   用户名: {existing_admin.username}")
                print(f"   角色: {existing_admin.role.value}")
                print(f"   状态: {'激活' if existing_admin.is_active else '禁用'}")
                return True
            
            # 创建新的管理员账户
            print("🆕 创建新的管理员账户...")
            admin_user = User(
                user_id=uuid.uuid4(),
                username=DEFAULT_ADMIN_USERNAME,
                password_hash=get_password_hash(DEFAULT_ADMIN_PASSWORD),
                role=UserRole.ADMIN,
                is_active=True,
                created_at=datetime.utcnow()
            )
            
            # 保存到数据库
            db.add(admin_user)
            db.commit()
            
            print("✅ 管理员账户创建成功")
            print("="*50)
            print("📋 账户信息:")
            print(f"   账户ID: {admin_user.user_id}")
            print(f"   用户名: {admin_user.username}")
            print(f"   密码: {DEFAULT_ADMIN_PASSWORD}")
            print(f"   角色: {admin_user.role.value}")
            print(f"   创建时间: {admin_user.created_at}")
            print("="*50)
            print("⚠️  安全提醒: 请立即登录系统修改默认密码！")
            print("="*50)
            
            return True
            
    except IntegrityError as e:
        print(f"⚠️  管理员账户已存在: {e}")
        return True
    except Exception as e:
        print(f"❌ 创建管理员账户失败: {e}")
        print("🔧 故障排除建议:")
        print("   1. 检查数据库连接是否正常")
        print("   2. 确认数据库表是否已创建")
        print("   3. 验证数据库用户权限")
        print("   4. 检查环境变量配置")
        return False

def wait_for_database():
    """
    等待数据库服务启动
    
    功能说明:
        - 循环检测数据库连接状态
        - 支持自定义重试次数和间隔
        - 适用于Docker容器启动场景
    
    返回值:
        bool: 数据库可用返回True，超时返回False
    
    配置参数:
        - MAX_RETRIES: 最大重试次数
        - RETRY_INTERVAL: 重试间隔(秒)
    """
    print("🔄 等待数据库服务启动...")
    print(f"📋 连接参数: {DB_HOST}:{DB_PORT}/{DB_NAME}")
    print(f"⏱️  最大等待时间: {MAX_RETRIES * RETRY_INTERVAL}秒")
    
    try:
        import psycopg2
    except ImportError:
        print("❌ 错误: 未安装psycopg2库")
        print("请运行: pip install psycopg2-binary")
        return False
    
    retry_count = 0
    
    while retry_count < MAX_RETRIES:
        try:
            # 尝试连接数据库
            print(f"🔗 尝试连接数据库... ({retry_count + 1}/{MAX_RETRIES})")
            
            conn = psycopg2.connect(
                host=DB_HOST,
                port=DB_PORT,
                user=DB_USER,
                password=DB_PASSWORD,
                database=DB_NAME,
                connect_timeout=5  # 5秒连接超时
            )
            
            # 测试数据库功能
            cursor = conn.cursor()
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            cursor.close()
            conn.close()
            
            print("✅ 数据库连接成功")
            print(f"📊 数据库版本: {version.split()[0]} {version.split()[1]}")
            return True
            
        except psycopg2.OperationalError as e:
            retry_count += 1
            if retry_count < MAX_RETRIES:
                print(f"⏳ 数据库未就绪，等待中... ({retry_count}/{MAX_RETRIES})")
                print(f"   错误信息: {str(e).strip()}")
                time.sleep(RETRY_INTERVAL)
            else:
                print(f"❌ 数据库连接超时: {e}")
        except Exception as e:
            print(f"❌ 数据库连接异常: {e}")
            return False
    
    print("❌ 数据库连接超时")
    print("🔧 故障排除建议:")
    print("   1. 检查数据库服务是否启动")
    print("   2. 验证数据库连接参数")
    print("   3. 检查网络连接")
    print("   4. 确认防火墙设置")
    return False

def install_pgvector_extension():
    """
    安装pgvector扩展
    
    功能说明:
        - 为数据库安装向量搜索扩展
        - 支持RAG系统的向量存储功能
        - 自动检查扩展是否已安装
    
    返回值:
        bool: 安装成功返回True，失败返回False
    
    依赖要求:
        - PostgreSQL数据库
        - pgvector扩展包
        - 数据库管理员权限
    """
    print("🧩 开始安装pgvector扩展...")
    
    try:
        # 检查psql命令是否可用
        result = subprocess.run(
            ["which", "psql"], 
            capture_output=True, 
            text=True
        )
        
        if result.returncode != 0:
            print("⚠️  警告: 未找到psql命令")
            print("尝试使用SQLAlchemy方式安装扩展...")
            return install_pgvector_via_sqlalchemy()
        
        print("🔧 使用psql命令安装pgvector扩展...")
        
        # 设置环境变量
        env = os.environ.copy()
        env["PGPASSWORD"] = DB_PASSWORD
        
        # 安装pgvector扩展
        result = subprocess.run([
            "psql", 
            "-h", DB_HOST,
            "-p", DB_PORT,
            "-U", DB_USER, 
            "-d", DB_NAME,
            "-c", "CREATE EXTENSION IF NOT EXISTS vector;"
        ], 
        env=env,
        capture_output=True,
        text=True,
        timeout=30
        )
        
        if result.returncode == 0:
            print("✅ pgvector扩展安装完成")
            
            # 验证扩展安装
            verify_result = subprocess.run([
                "psql", 
                "-h", DB_HOST,
                "-p", DB_PORT,
                "-U", DB_USER, 
                "-d", DB_NAME,
                "-c", "SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';"
            ], 
            env=env,
            capture_output=True,
            text=True
            )
            
            if verify_result.returncode == 0 and "vector" in verify_result.stdout:
                print("✅ pgvector扩展验证成功")
                return True
            else:
                print("⚠️  pgvector扩展验证失败")
                return False
        else:
            print(f"❌ pgvector扩展安装失败")
            print(f"   错误输出: {result.stderr.strip()}")
            print(f"   标准输出: {result.stdout.strip()}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ pgvector扩展安装超时")
        return False
    except Exception as e:
        print(f"❌ pgvector扩展安装异常: {e}")
        return False

def install_pgvector_via_sqlalchemy():
    """
    通过SQLAlchemy安装pgvector扩展
    
    备用方案，当psql命令不可用时使用
    """
    try:
        print("🔧 使用SQLAlchemy安装pgvector扩展...")
        
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            # 检查扩展是否已存在
            result = conn.execute(text(
                "SELECT 1 FROM pg_extension WHERE extname = 'vector'"
            ))
            
            if result.fetchone():
                print("✅ pgvector扩展已存在")
                return True
            
            # 安装扩展
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            conn.commit()
            
            print("✅ pgvector扩展安装完成")
            return True
            
    except Exception as e:
        print(f"❌ SQLAlchemy方式安装失败: {e}")
        print("🔧 故障排除建议:")
        print("   1. 确认数据库用户具有创建扩展权限")
        print("   2. 检查pgvector扩展包是否已安装")
        print("   3. 验证PostgreSQL版本兼容性")
        return False

def run_database_migration():
    """
    运行数据库迁移
    
    功能说明:
        - 执行Alembic数据库迁移脚本
        - 创建或更新数据库表结构
        - 确保数据库架构与代码模型同步
    
    返回值:
        bool: 迁移成功返回True，失败返回False
    
    依赖要求:
        - Alembic迁移工具
        - 正确的迁移脚本配置
        - 数据库连接权限
    """
    print("🔄 开始数据库迁移...")
    
    try:
        # 检查alembic命令是否可用
        result = subprocess.run(
            ["which", "alembic"], 
            capture_output=True, 
            text=True
        )
        
        if result.returncode != 0:
            print("⚠️  警告: 未找到alembic命令")
            print("跳过数据库迁移，使用基础表创建")
            return True
        
        print("🔧 使用Alembic执行数据库迁移...")
        
        # 检查迁移配置文件
        alembic_ini_path = os.path.join(PROJECT_ROOT, "alembic.ini")
        if not os.path.exists(alembic_ini_path):
            print(f"⚠️  警告: 未找到alembic配置文件: {alembic_ini_path}")
            print("跳过数据库迁移")
            return True
        
        # 运行alembic迁移
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=60  # 60秒超时
        )
        
        if result.returncode == 0:
            print("✅ 数据库迁移完成")
            if result.stdout.strip():
                print(f"   迁移输出: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ 数据库迁移失败")
            print(f"   错误输出: {result.stderr.strip()}")
            if result.stdout.strip():
                print(f"   标准输出: {result.stdout.strip()}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ 数据库迁移超时")
        return False
    except Exception as e:
        print(f"❌ 数据库迁移异常: {e}")
        print("🔧 故障排除建议:")
        print("   1. 检查alembic配置文件")
        print("   2. 验证数据库连接")
        print("   3. 确认迁移脚本完整性")
        return False

#===============================================================================
# 主程序入口
#===============================================================================

def main():
    """
    主函数 - 系统初始化流程控制
    
    执行流程:
        1. 等待数据库服务启动
        2. 安装pgvector扩展
        3. 运行数据库迁移
        4. 创建默认管理员账户
    
    退出码:
        0: 初始化成功
        1: 初始化失败
    """
    print("="*80)
    print("🚀 Wind Whisper RAG System 初始化程序")
    print("="*80)
    print("")
    print("📋 初始化流程:")
    print("   1. 等待数据库服务启动")
    print("   2. 安装pgvector扩展")
    print("   3. 运行数据库迁移")
    print("   4. 创建默认管理员账户")
    print("")
    print("⏱️  开始时间:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("="*80)
    
    start_time = time.time()
    
    try:
        # 第一步：等待数据库启动
        print("\n🔄 步骤 1/4: 等待数据库服务启动")
        if not wait_for_database():
            print("❌ 数据库连接失败，初始化中止")
            sys.exit(1)
        
        # 第二步：安装pgvector扩展
        print("\n🔄 步骤 2/4: 安装pgvector扩展")
        if not install_pgvector_extension():
            print("❌ pgvector扩展安装失败，初始化中止")
            sys.exit(1)
        
        # 第三步：运行数据库迁移
        print("\n🔄 步骤 3/4: 运行数据库迁移")
        if not run_database_migration():
            print("❌ 数据库迁移失败，初始化中止")
            sys.exit(1)
        
        # 第四步：创建管理员账户
        print("\n🔄 步骤 4/4: 创建管理员账户")
        if not create_admin_user():
            print("❌ 管理员账户创建失败，初始化中止")
            sys.exit(1)
        
        # 初始化完成
        end_time = time.time()
        duration = end_time - start_time
        
        print("\n" + "="*80)
        print("🎉 Wind Whisper RAG System 初始化完成！")
        print("="*80)
        print(f"⏱️  总耗时: {duration:.2f}秒")
        print(f"🕐 完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("")
        print("📋 系统信息:")
        print(f"   数据库: {DB_HOST}:{DB_PORT}/{DB_NAME}")
        print(f"   管理员: {DEFAULT_ADMIN_USERNAME}")
        print(f"   默认密码: {DEFAULT_ADMIN_PASSWORD}")
        print("")
        print("🔐 安全提醒:")
        print("   请立即登录系统修改默认管理员密码！")
        print("   建议启用双因素认证增强安全性")
        print("")
        print("🌐 下一步:")
        print("   1. 访问系统管理界面")
        print("   2. 修改默认密码")
        print("   3. 配置系统参数")
        print("   4. 上传知识库文档")
        print("="*80)
        
        sys.exit(0)
        
    except KeyboardInterrupt:
        print("\n❌ 用户中断初始化过程")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 初始化过程发生异常: {e}")
        print("🔧 请检查系统配置和日志信息")
        sys.exit(1)

if __name__ == "__main__":
    main()