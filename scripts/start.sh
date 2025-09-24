#!/bin/bash

#===============================================================================
# Wind Whisper RAG System 开发环境启动脚本
#===============================================================================
#
# 功能描述:
#   用于开发环境下启动Wind Whisper RAG系统
#   自动检查环境依赖、配置数据库、安装依赖并启动服务
#
# 使用方法:
#   ./scripts/start.sh [选项]
#
# 选项:
#   --dev          开发模式启动 (默认)
#   --prod         生产模式启动
#   --debug        调试模式启动
#   --no-deps      跳过依赖安装
#   --no-db-check  跳过数据库检查
#   --help         显示帮助信息
#
# 前置条件:
#   1. Python 3.8+ 已安装
#   2. PostgreSQL 数据库已配置
#   3. .env 文件已正确配置
#   4. 建议在虚拟环境中运行
#
# 作者: Wind Whisper Team
# 版本: v1.0
# 更新: 2024-01-20
#===============================================================================

# 启用严格模式：遇到错误立即退出
set -e

#===============================================================================
# 配置变量
#===============================================================================

# 脚本配置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_PATH="$PROJECT_ROOT/venv"

# 运行模式配置
RUN_MODE="dev"              # 运行模式: dev/prod/debug
SKIP_DEPS=false            # 是否跳过依赖安装
SKIP_DB_CHECK=false        # 是否跳过数据库检查
SHOW_HELP=false            # 是否显示帮助

# 服务配置
DEFAULT_HOST="0.0.0.0"     # 默认主机地址
DEFAULT_PORT=8000          # 默认端口
RELOAD_MODE=true           # 是否启用热重载

#===============================================================================
# 参数解析
#===============================================================================

while [[ $# -gt 0 ]]; do
    case $1 in
        --dev)
            RUN_MODE="dev"
            RELOAD_MODE=true
            shift
            ;;
        --prod)
            RUN_MODE="prod"
            RELOAD_MODE=false
            shift
            ;;
        --debug)
            RUN_MODE="debug"
            RELOAD_MODE=true
            shift
            ;;
        --no-deps)
            SKIP_DEPS=true
            shift
            ;;
        --no-db-check)
            SKIP_DB_CHECK=true
            shift
            ;;
        --help)
            SHOW_HELP=true
            shift
            ;;
        *)
            echo "未知参数: $1"
            echo "使用 --help 查看帮助信息"
            exit 1
            ;;
    esac
done

#===============================================================================
# 帮助信息
#===============================================================================

if [ "$SHOW_HELP" = true ]; then
    echo "Wind Whisper RAG System 启动脚本"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  --dev          开发模式启动 (默认，启用热重载)"
    echo "  --prod         生产模式启动 (禁用热重载)"
    echo "  --debug        调试模式启动 (详细日志输出)"
    echo "  --no-deps      跳过依赖安装检查"
    echo "  --no-db-check  跳过数据库连接检查"
    echo "  --help         显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0                    # 开发模式启动"
    echo "  $0 --prod            # 生产模式启动"
    echo "  $0 --debug --no-deps # 调试模式，跳过依赖检查"
    echo ""
    exit 0
fi

#===============================================================================
# 启动信息显示
#===============================================================================

echo "==============================================================================="
echo "🚀 Wind Whisper RAG System 启动脚本"
echo "==============================================================================="
echo ""
echo "📋 启动配置:"
echo "   运行模式:     $RUN_MODE"
echo "   项目目录:     $PROJECT_ROOT"
echo "   热重载:       $([ "$RELOAD_MODE" = true ] && echo "启用" || echo "禁用")"
echo "   跳过依赖:     $([ "$SKIP_DEPS" = true ] && echo "是" || echo "否")"
echo "   跳过数据库:   $([ "$SKIP_DB_CHECK" = true ] && echo "是" || echo "否")"
echo ""

# 切换到项目根目录
cd "$PROJECT_ROOT"

#===============================================================================
# 环境检查阶段
#===============================================================================

echo "🔍 检查运行环境..."

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到 python3"
    echo "请安装 Python 3.8 或更高版本"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo "✅ Python 版本: $PYTHON_VERSION"

# 检查Python版本
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)
if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 8 ]); then
    echo "❌ 错误: Python 版本过低，需要 3.8 或更高版本"
    exit 1
fi

# 检查虚拟环境
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "⚠️  警告: 当前未在虚拟环境中运行"
    echo ""
    echo "建议操作:"
    echo "   创建虚拟环境: python3 -m venv venv"
    echo "   激活虚拟环境: source venv/bin/activate"
    echo "   然后重新运行此脚本"
    echo ""
    
    # 检查是否存在虚拟环境目录
    if [ -d "$VENV_PATH" ]; then
        echo "发现虚拟环境目录: $VENV_PATH"
        echo "可以运行: source venv/bin/activate"
    fi
    echo ""
else
    echo "✅ 虚拟环境: $VIRTUAL_ENV"
fi

#===============================================================================
# 环境配置检查
#===============================================================================

echo ""
echo "⚙️  检查环境配置..."

# 检查.env文件
if [ ! -f ".env" ]; then
    echo "⚠️  警告: 未找到 .env 文件"
    
    if [ -f ".env.example" ]; then
        echo "📋 发现示例配置文件，正在复制..."
        cp .env.example .env
        echo "✅ 已创建 .env 文件"
        echo ""
        echo "🔧 请编辑 .env 文件配置以下信息:"
        echo "   - 数据库连接信息 (DATABASE_URL)"
        echo "   - JWT密钥 (JWT_SECRET_KEY)"
        echo "   - AI模型配置 (OPENAI_API_KEY等)"
        echo "   - 其他必要的环境变量"
        echo ""
        echo "配置完成后请重新运行此脚本"
        exit 1
    else
        echo "❌ 错误: 未找到 .env.example 文件"
        echo "请手动创建 .env 文件并配置必要的环境变量"
        echo ""
        echo "必需的环境变量:"
        echo "   DATABASE_URL=postgresql://user:password@localhost:5432/dbname"
        echo "   JWT_SECRET_KEY=your-secret-key"
        echo "   OPENAI_API_KEY=your-openai-key"
        exit 1
    fi
else
    echo "✅ 找到 .env 配置文件"
fi

# 验证关键环境变量
echo "🔍 验证环境变量配置..."
source .env 2>/dev/null || true

MISSING_VARS=()
if [ -z "$DATABASE_URL" ]; then
    MISSING_VARS+=("DATABASE_URL")
fi
if [ -z "$JWT_SECRET_KEY" ]; then
    MISSING_VARS+=("JWT_SECRET_KEY")
fi

if [ ${#MISSING_VARS[@]} -gt 0 ]; then
    echo "❌ 错误: 缺少必需的环境变量:"
    for var in "${MISSING_VARS[@]}"; do
        echo "   - $var"
    done
    echo ""
    echo "请在 .env 文件中配置这些变量"
    exit 1
fi

echo "✅ 环境变量配置完整"

#===============================================================================
# 依赖安装阶段
#===============================================================================

if [ "$SKIP_DEPS" = false ]; then
    echo ""
    echo "📦 安装Python依赖..."
    
    # 检查requirements.txt文件
    if [ ! -f "requirements.txt" ]; then
        echo "❌ 错误: 未找到 requirements.txt 文件"
        exit 1
    fi
    
    # 升级pip
    echo "🔄 升级pip..."
    python3 -m pip install --upgrade pip
    
    # 安装依赖
    echo "📥 安装项目依赖..."
    pip install -r requirements.txt
    
    echo "✅ 依赖安装完成"
else
    echo ""
    echo "⏭️  跳过依赖安装 (--no-deps)"
fi

#===============================================================================
# 数据库检查阶段
#===============================================================================

if [ "$SKIP_DB_CHECK" = false ]; then
    echo ""
    echo "🗄️  检查数据库连接..."
    
    # 数据库连接测试
    python3 -c "
import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

try:
    # 获取数据库URL
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print('❌ 错误: 未找到 DATABASE_URL 环境变量')
        sys.exit(1)
    
    print(f'🔗 连接数据库: {db_url.split(\"@\")[1] if \"@\" in db_url else \"localhost\"}')
    
    # 创建数据库引擎
    engine = create_engine(db_url)
    
    # 测试连接
    with engine.connect() as connection:
        result = connection.execute(text('SELECT version()'))
        version = result.fetchone()[0]
        print(f'✅ 数据库连接成功')
        print(f'📊 数据库版本: {version.split()[0]} {version.split()[1]}')
        
except ImportError as e:
    print(f'❌ 错误: 缺少必需的Python包: {e}')
    print('请运行: pip install -r requirements.txt')
    sys.exit(1)
except Exception as e:
    print(f'❌ 数据库连接失败: {e}')
    print('')
    print('🔧 故障排除建议:')
    print('   1. 检查数据库服务是否运行')
    print('   2. 验证 .env 文件中的 DATABASE_URL 配置')
    print('   3. 确认数据库用户权限')
    print('   4. 检查网络连接和防火墙设置')
    sys.exit(1)
"
    
    echo "✅ 数据库连接验证通过"
else
    echo ""
    echo "⏭️  跳过数据库检查 (--no-db-check)"
fi

#===============================================================================
# 数据库初始化阶段
#===============================================================================

echo ""
echo "🏗️  初始化数据库..."

# 检查初始化脚本
if [ ! -f "scripts/init_db.py" ]; then
    echo "⚠️  警告: 未找到数据库初始化脚本"
    echo "跳过数据库初始化"
else
    echo "🔄 运行数据库初始化脚本..."
    python3 scripts/init_db.py
    
    if [ $? -eq 0 ]; then
        echo "✅ 数据库初始化完成"
    else
        echo "❌ 数据库初始化失败"
        echo "请检查数据库配置和权限"
        exit 1
    fi
fi

#===============================================================================
# 应用启动阶段
#===============================================================================

echo ""
echo "🚀 启动应用服务..."

# 根据运行模式设置启动参数
case $RUN_MODE in
    "dev")
        echo "🔧 开发模式启动 (启用热重载和调试)"
        UVICORN_ARGS="--reload --log-level debug"
        ;;
    "prod")
        echo "🏭 生产模式启动"
        UVICORN_ARGS="--log-level info"
        ;;
    "debug")
        echo "🐛 调试模式启动 (详细日志)"
        UVICORN_ARGS="--reload --log-level debug --access-log"
        ;;
    *)
        echo "⚠️  未知运行模式: $RUN_MODE，使用默认配置"
        UVICORN_ARGS="--reload"
        ;;
esac

# 获取配置的主机和端口
HOST=${HOST:-$DEFAULT_HOST}
PORT=${PORT:-$DEFAULT_PORT}

echo ""
echo "📋 启动参数:"
echo "   主机地址:     $HOST"
echo "   端口:         $PORT"
echo "   运行模式:     $RUN_MODE"
echo "   额外参数:     $UVICORN_ARGS"
echo ""

echo "==============================================================================="
echo "🎉 启动 Wind Whisper RAG System"
echo "==============================================================================="
echo ""
echo "🌐 访问地址:"
echo "   本地访问:     http://localhost:$PORT"
echo "   网络访问:     http://$HOST:$PORT"
echo "   API文档:      http://localhost:$PORT/docs"
echo "   健康检查:     http://localhost:$PORT/health"
echo ""
echo "💡 提示:"
echo "   - 按 Ctrl+C 停止服务"
echo "   - 开发模式下代码修改会自动重载"
echo "   - 查看日志了解运行状态"
echo ""

# 启动应用
python3 -m uvicorn app.main:app --host "$HOST" --port "$PORT" $UVICORN_ARGS