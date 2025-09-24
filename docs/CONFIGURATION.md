# Wind Whisper RAG System 配置指南

<!-- 系统配置管理文档 -->
**版本**: v1.0  
**更新日期**: 2024年1月  
**维护者**: 系统配置团队

## 📋 概述

Wind Whisper RAG System 采用现代化的配置管理方案，基于 **Pydantic Settings** 实现类型安全的配置管理。所有配置项都集中在 `config/settings.py` 文件中，支持多种配置来源和灵活的配置覆盖机制。

### 🎯 配置管理特性

- **类型安全**: 基于Pydantic的自动类型验证和转换
- **环境感知**: 支持开发、测试、生产环境的配置隔离
- **多源配置**: 支持环境变量、.env文件、默认值的优先级覆盖
- **实时验证**: 启动时自动验证配置的完整性和有效性
- **文档化**: 每个配置项都有详细的说明和使用示例
- **热重载**: 开发模式下支持配置的动态重载

### 🔧 配置架构设计

```python
# 配置管理架构
Settings (主配置类)
├── DatabaseSettings     # 数据库相关配置
├── ServerSettings       # 服务器运行配置
├── AIModelSettings      # AI模型配置
├── RAGSettings          # RAG系统配置
├── SecuritySettings     # 安全认证配置
├── FileStorageSettings  # 文件存储配置
├── LoggingSettings      # 日志系统配置
└── TestSettings         # 测试环境配置
```

## 📁 配置文件结构

### 主配置文件
- **`config/settings.py`** - 统一配置管理中心，定义所有配置类和验证逻辑
- **`.env`** - 环境变量配置文件，存储敏感信息和环境特定配置
- **`.env.example`** - 配置模板文件，提供所有可配置项的示例
- **`config/database.py`** - 数据库连接和会话管理
- **`config/__init__.py`** - 配置模块初始化

### 配置文件层次结构
```
config/
├── settings.py          # 主配置文件 (核心)
├── database.py          # 数据库配置
├── __init__.py          # 模块初始化
└── logging_config.py    # 日志配置 (可选)

.env                     # 环境变量文件
.env.example            # 配置模板
.env.local              # 本地开发配置 (可选)
.env.production         # 生产环境配置 (可选)
```

## 🔧 详细配置模块

### 1. 数据库配置 (DatabaseSettings)

**用途**: 管理PostgreSQL数据库连接、连接池、查询优化等设置

```bash
# 基础连接配置
DATABASE_URL=postgresql://postgres:postgres123@localhost:5432/wind_whisper_rag
DATABASE_ECHO=false                    # 是否打印SQL语句 (开发时可设为true)

# 连接池配置 (性能优化)
DATABASE_POOL_SIZE=10                  # 连接池大小 (建议: 10-20)
DATABASE_MAX_OVERFLOW=20               # 最大溢出连接数 (建议: pool_size的2倍)
DATABASE_POOL_TIMEOUT=30               # 获取连接超时时间 (秒)
DATABASE_POOL_RECYCLE=3600            # 连接回收时间 (秒)

# 查询优化配置
DATABASE_QUERY_TIMEOUT=30              # 查询超时时间 (秒)
DATABASE_STATEMENT_TIMEOUT=60          # 语句执行超时 (秒)
```

**配置说明**:
- `DATABASE_URL`: 完整的数据库连接字符串，格式为 `postgresql://用户名:密码@主机:端口/数据库名`
- `DATABASE_ECHO`: 开发环境建议设为 `true` 以便调试SQL，生产环境设为 `false`
- `DATABASE_POOL_SIZE`: 根据并发用户数调整，一般设置为CPU核心数的2-4倍
- `DATABASE_MAX_OVERFLOW`: 处理突发流量，建议设为pool_size的1-2倍

### 2. 服务器配置 (ServerSettings)

**用途**: 控制FastAPI应用服务器的运行参数和性能设置

```bash
# 网络配置
HOST=0.0.0.0                          # 监听地址 (0.0.0.0表示所有接口)
PORT=8000                              # 监听端口 (1024-65535)

# 运行模式配置
DEBUG=false                            # 调试模式 (生产环境必须为false)
RELOAD=false                           # 代码热重载 (仅开发环境使用)
WORKERS=1                              # 工作进程数 (生产环境建议设为CPU核心数)

# 性能配置
MAX_CONNECTIONS=1000                   # 最大并发连接数
KEEPALIVE_TIMEOUT=5                    # Keep-Alive超时时间 (秒)
REQUEST_TIMEOUT=30                     # 请求超时时间 (秒)

# 安全配置
ALLOWED_HOSTS=["localhost", "127.0.0.1"]  # 允许的主机名列表
CORS_ORIGINS=["http://localhost:3000"]     # CORS允许的源
```

**环境建议**:
- **开发环境**: `DEBUG=true`, `RELOAD=true`, `WORKERS=1`
- **测试环境**: `DEBUG=false`, `RELOAD=false`, `WORKERS=2`
- **生产环境**: `DEBUG=false`, `RELOAD=false`, `WORKERS=4-8`

### 3. AI模型配置 (AIModelSettings)

**用途**: 管理大语言模型(LLM)和嵌入模型的配置，支持本地和云端模型

```bash
# === LLM大语言模型配置 ===
LLM_MODEL_NAME=Qwen/Qwen2.5-0.5B-Instruct    # 模型标识符
LLM_LOCAL_PATH=/app/ai_models/Qwen2.5-0.5B-Instruct  # 本地模型路径
LLM_MAX_LENGTH=2048                           # 最大输入长度 (tokens)
LLM_TEMPERATURE=0.7                           # 生成温度 (0.0-2.0, 越高越随机)
LLM_TOP_P=0.9                                # 核采样参数 (0.0-1.0)
LLM_TOP_K=50                                 # Top-K采样参数
LLM_REPETITION_PENALTY=1.1                   # 重复惩罚系数
LLM_DEVICE=auto                              # 设备选择 (auto/cpu/cuda)

# === 嵌入模型配置 ===
EMBEDDING_MODEL_NAME=BAAI/bge-m3             # 嵌入模型名称
EMBEDDING_LOCAL_PATH=/app/ai_models/bge-m3   # 本地模型路径
EMBEDDING_BATCH_SIZE=32                      # 批处理大小 (根据显存调整)
EMBEDDING_MAX_LENGTH=512                     # 最大输入长度
EMBEDDING_DEVICE=auto                        # 设备选择
EMBEDDING_NORMALIZE=true                     # 是否归一化向量

# === 模型通用配置 ===
TRANSFORMERS_OFFLINE=true                    # 离线模式 (不从HuggingFace下载)
HF_HUB_OFFLINE=true                         # HuggingFace Hub离线模式
MODEL_CACHE_DIR=/app/ai_models              # 模型缓存目录
TORCH_HOME=/app/ai_models/.torch            # PyTorch缓存目录

# === OpenAI API配置 (可选) ===
OPENAI_API_KEY=sk-your-api-key-here         # OpenAI API密钥
OPENAI_BASE_URL=https://api.openai.com/v1   # API基础URL
OPENAI_MODEL=gpt-3.5-turbo                  # 使用的模型
OPENAI_TIMEOUT=30                           # 请求超时时间
```

**模型选择建议**:
- **轻量级部署**: Qwen2.5-0.5B (512MB显存)
- **平衡性能**: Qwen2.5-1.5B (1.5GB显存)
- **高性能**: Qwen2.5-7B (14GB显存)
- **嵌入模型**: BGE-M3 (多语言支持) 或 BGE-Large-ZH (中文优化)

### 4. RAG配置 (RAGSettings)

**用途**: 控制检索增强生成(RAG)系统的核心参数，影响检索质量和生成效果

```bash
# === 文档分块配置 ===
RAG_CHUNK_SIZE=500                          # 文档分块大小 (字符数)
RAG_CHUNK_OVERLAP=50                        # 分块重叠大小 (字符数)
RAG_MIN_CHUNK_SIZE=100                      # 最小分块大小
RAG_MAX_CHUNK_SIZE=1000                     # 最大分块大小

# === 检索配置 ===
RAG_TOP_K=5                                 # 检索返回的文档数量
RAG_SIMILARITY_THRESHOLD=0.7                # 相似度阈值 (0.0-1.0)
RAG_RERANK_TOP_K=10                        # 重排序前的候选数量
RAG_ENABLE_RERANK=true                     # 是否启用重排序

# === 上下文配置 ===
RAG_MAX_CONTEXT_LENGTH=4000                # 最大上下文长度 (字符数)
RAG_CONTEXT_OVERLAP_RATIO=0.1              # 上下文重叠比例
RAG_ENABLE_CONTEXT_COMPRESSION=true        # 是否启用上下文压缩

# === 检索策略配置 ===
RAG_SEARCH_TYPE=hybrid                     # 检索类型 (semantic/keyword/hybrid)
RAG_KEYWORD_WEIGHT=0.3                     # 关键词检索权重 (hybrid模式)
RAG_SEMANTIC_WEIGHT=0.7                    # 语义检索权重 (hybrid模式)

# === 缓存配置 ===
RAG_ENABLE_CACHE=true                      # 是否启用检索缓存
RAG_CACHE_TTL=3600                         # 缓存过期时间 (秒)
RAG_CACHE_MAX_SIZE=1000                    # 缓存最大条目数
```

**参数调优建议**:
- **高精度场景**: `CHUNK_SIZE=300`, `TOP_K=3`, `THRESHOLD=0.8`
- **高召回场景**: `CHUNK_SIZE=800`, `TOP_K=10`, `THRESHOLD=0.6`
- **平衡场景**: `CHUNK_SIZE=500`, `TOP_K=5`, `THRESHOLD=0.7`

### 5. 安全配置 (SecuritySettings)

**用途**: 管理身份认证、授权和数据安全相关配置

```bash
# === JWT认证配置 ===
SECRET_KEY=wind-whisper-secret-key-2024     # JWT签名密钥 (生产环境必须更换)
JWT_ALGORITHM=HS256                         # JWT签名算法
ACCESS_TOKEN_EXPIRE_MINUTES=30              # 访问令牌过期时间 (分钟)
REFRESH_TOKEN_EXPIRE_DAYS=7                 # 刷新令牌过期时间 (天)

# === 密码安全配置 ===
PASSWORD_MIN_LENGTH=8                       # 密码最小长度
PASSWORD_REQUIRE_UPPERCASE=true             # 是否要求大写字母
PASSWORD_REQUIRE_LOWERCASE=true             # 是否要求小写字母
PASSWORD_REQUIRE_NUMBERS=true               # 是否要求数字
PASSWORD_REQUIRE_SPECIAL=true               # 是否要求特殊字符
PASSWORD_HASH_ROUNDS=12                     # bcrypt哈希轮数

# === 会话安全配置 ===
SESSION_TIMEOUT=1800                        # 会话超时时间 (秒)
MAX_LOGIN_ATTEMPTS=5                        # 最大登录尝试次数
LOGIN_LOCKOUT_DURATION=900                  # 登录锁定时间 (秒)
ENABLE_2FA=false                            # 是否启用双因子认证

# === API安全配置 ===
API_RATE_LIMIT=100                          # API速率限制 (请求/分钟)
API_RATE_LIMIT_WINDOW=60                    # 速率限制窗口 (秒)
ENABLE_API_KEY_AUTH=false                   # 是否启用API密钥认证
API_KEY_HEADER=X-API-Key                    # API密钥请求头名称

# === CORS安全配置 ===
CORS_ALLOW_ORIGINS=["http://localhost:3000"] # 允许的跨域源
CORS_ALLOW_METHODS=["GET", "POST", "PUT", "DELETE"] # 允许的HTTP方法
CORS_ALLOW_HEADERS=["*"]                    # 允许的请求头
CORS_ALLOW_CREDENTIALS=true                 # 是否允许携带凭证
```

**安全最佳实践**:
1. **生产环境必须更换SECRET_KEY**: 使用 `openssl rand -hex 32` 生成
2. **启用HTTPS**: 生产环境必须使用SSL/TLS加密
3. **定期轮换密钥**: 建议每3-6个月更换一次JWT密钥
4. **最小权限原则**: 用户只分配必要的权限
5. **监控异常登录**: 记录和监控失败的登录尝试

### 6. 文件存储配置 (FileStorageSettings)

**用途**: 管理文件上传、存储和访问相关配置

```bash
# === 基础存储配置 ===
UPLOAD_FOLDER=uploads                        # 上传文件存储目录
STATIC_FOLDER=static                         # 静态文件目录
TEMP_FOLDER=temp                            # 临时文件目录
BACKUP_FOLDER=backups                       # 备份文件目录

# === 文件大小限制 ===
MAX_CONTENT_LENGTH=16777216                 # 最大文件大小 (16MB)
MAX_FILE_COUNT=100                          # 单次上传最大文件数量
CHUNK_SIZE=8192                             # 文件读取块大小 (字节)

# === 文件类型配置 ===
ALLOWED_EXTENSIONS=pdf,txt,docx,md,xlsx,pptx,csv,json,xml  # 允许的文件扩展名
ALLOWED_MIME_TYPES=application/pdf,text/plain,application/vnd.openxmlformats-officedocument.wordprocessingml.document  # 允许的MIME类型
FORBIDDEN_EXTENSIONS=exe,bat,sh,cmd,scr     # 禁止的文件扩展名

# === 存储策略配置 ===
STORAGE_TYPE=local                          # 存储类型 (local/s3/oss/minio)
ENABLE_FILE_COMPRESSION=true                # 是否启用文件压缩
COMPRESSION_LEVEL=6                         # 压缩级别 (1-9)
ENABLE_FILE_ENCRYPTION=false               # 是否启用文件加密

# === 文件清理配置 ===
AUTO_CLEANUP_ENABLED=true                  # 是否启用自动清理
TEMP_FILE_TTL=3600                         # 临时文件生存时间 (秒)
ORPHAN_FILE_TTL=86400                      # 孤儿文件生存时间 (秒)
CLEANUP_SCHEDULE=0 2 * * *                 # 清理任务调度 (cron表达式)

# === 云存储配置 (可选) ===
AWS_ACCESS_KEY_ID=your-access-key           # AWS访问密钥
AWS_SECRET_ACCESS_KEY=your-secret-key       # AWS秘密密钥
AWS_BUCKET_NAME=wind-whisper-bucket         # S3存储桶名称
AWS_REGION=us-east-1                        # AWS区域
```

**存储最佳实践**:
- **本地存储**: 适合小规模部署，注意磁盘空间监控
- **云存储**: 适合生产环境，提供高可用性和扩展性
- **文件验证**: 上传前进行病毒扫描和内容验证
- **访问控制**: 实施细粒度的文件访问权限控制

### 7. 日志配置 (LoggingSettings)

**用途**: 控制应用程序日志记录的详细程度和存储方式

```bash
# === 基础日志配置 ===
LOG_LEVEL=INFO                              # 日志级别 (DEBUG/INFO/WARNING/ERROR/CRITICAL)
LOG_FORMAT=%(asctime)s - %(name)s - %(levelname)s - %(message)s  # 日志格式
LOG_DATE_FORMAT=%Y-%m-%d %H:%M:%S          # 时间格式

# === 文件日志配置 ===
LOG_FILE=logs/app.log                       # 主日志文件路径
LOG_MAX_BYTES=10485760                      # 单个日志文件最大大小 (10MB)
LOG_BACKUP_COUNT=5                          # 保留的日志文件数量
LOG_ENCODING=utf-8                          # 日志文件编码

# === 分类日志配置 ===
ACCESS_LOG_FILE=logs/access.log             # 访问日志文件
ERROR_LOG_FILE=logs/error.log               # 错误日志文件
SECURITY_LOG_FILE=logs/security.log         # 安全日志文件
PERFORMANCE_LOG_FILE=logs/performance.log   # 性能日志文件

# === 日志输出配置 ===
LOG_TO_CONSOLE=true                         # 是否输出到控制台
LOG_TO_FILE=true                           # 是否输出到文件
LOG_TO_SYSLOG=false                        # 是否输出到系统日志
SYSLOG_ADDRESS=localhost:514               # Syslog服务器地址

# === 结构化日志配置 ===
ENABLE_JSON_LOGGING=false                  # 是否启用JSON格式日志
LOG_CORRELATION_ID=true                    # 是否添加关联ID
LOG_REQUEST_ID=true                        # 是否记录请求ID
LOG_USER_ID=true                           # 是否记录用户ID

# === 日志过滤配置 ===
LOG_EXCLUDE_PATHS=["/health", "/metrics"]  # 排除的路径
LOG_EXCLUDE_USERS=["system", "monitor"]    # 排除的用户
LOG_SENSITIVE_FIELDS=["password", "token"] # 敏感字段 (将被脱敏)

# === 日志监控配置 ===
LOG_METRICS_ENABLED=true                   # 是否启用日志指标
LOG_ALERT_ERROR_THRESHOLD=10               # 错误日志告警阈值 (每分钟)
LOG_ALERT_WARNING_THRESHOLD=50             # 警告日志告警阈值 (每分钟)
```

**日志级别说明**:
- **DEBUG**: 详细的调试信息 (开发环境)
- **INFO**: 一般信息 (生产环境推荐)
- **WARNING**: 警告信息
- **ERROR**: 错误信息
- **CRITICAL**: 严重错误信息

### 8. 测试配置 (TestSettings)

**用途**: 管理测试环境的配置，确保测试与生产环境隔离

```bash
# === 基础测试配置 ===
TESTING=false                               # 是否为测试模式
TEST_ENV=unittest                           # 测试环境类型 (unittest/integration/e2e)
TEST_PARALLEL=true                          # 是否并行执行测试

# === 测试数据库配置 ===
TEST_DATABASE_URL=sqlite:///test.db         # 测试数据库连接URL
TEST_DB_ISOLATION=true                      # 是否启用数据库隔离
TEST_DB_RESET_BETWEEN_TESTS=true           # 测试间是否重置数据库
TEST_DB_SEED_DATA=true                     # 是否加载种子数据

# === 测试文件配置 ===
TEST_UPLOAD_FOLDER=test_uploads             # 测试文件上传目录
TEST_TEMP_FOLDER=test_temp                  # 测试临时文件目录
TEST_CLEANUP_FILES=true                     # 测试后是否清理文件

# === 模拟服务配置 ===
MOCK_AI_SERVICES=true                       # 是否模拟AI服务
MOCK_EXTERNAL_APIS=true                     # 是否模拟外部API
MOCK_EMAIL_SERVICE=true                     # 是否模拟邮件服务
MOCK_FILE_STORAGE=true                      # 是否模拟文件存储

# === 测试覆盖率配置 ===
COVERAGE_ENABLED=true                       # 是否启用覆盖率统计
COVERAGE_MIN_THRESHOLD=80                   # 最小覆盖率阈值 (%)
COVERAGE_REPORT_FORMAT=html,xml,term        # 覆盖率报告格式
COVERAGE_EXCLUDE_PATTERNS=["*/tests/*", "*/migrations/*"]  # 排除的文件模式

# === 性能测试配置 ===
PERFORMANCE_TEST_ENABLED=false             # 是否启用性能测试
LOAD_TEST_CONCURRENT_USERS=10              # 负载测试并发用户数
LOAD_TEST_DURATION=60                      # 负载测试持续时间 (秒)
RESPONSE_TIME_THRESHOLD=1000               # 响应时间阈值 (毫秒)

# === 测试报告配置 ===
TEST_REPORT_FORMAT=junit                    # 测试报告格式 (junit/html/json)
TEST_REPORT_OUTPUT=test_reports             # 测试报告输出目录
TEST_SCREENSHOTS_ON_FAILURE=true           # 失败时是否截图 (UI测试)
```

**测试环境最佳实践**:
1. **数据隔离**: 使用独立的测试数据库
2. **环境一致性**: 测试环境尽可能接近生产环境
3. **自动化清理**: 测试后自动清理临时数据和文件
4. **并行执行**: 提高测试执行效率
5. **覆盖率监控**: 确保代码覆盖率达到要求

## 使用方法

### 1. 在代码中使用配置

```python
from config.settings import get_settings

# 获取配置实例
settings = get_settings()

# 访问配置
database_url = settings.database.url
server_port = settings.server.port
llm_model = settings.ai_model.llm_model_name
```

### 2. 便捷访问函数

```python
from config.settings import get_database_url, get_server_config, get_ai_model_config

# 获取数据库URL
db_url = get_database_url()

# 获取服务器配置
server_config = get_server_config()

# 获取AI模型配置
ai_config = get_ai_model_config()
```

### 3. 环境变量设置

```bash
# 设置环境变量
export DATABASE_URL="postgresql://user:pass@localhost:5432/db"
export PORT=8080
export DEBUG=true

# 或者在.env文件中设置
echo "PORT=8080" >> .env
```

## 配置优先级

1. 环境变量 (最高优先级)
2. `.env` 文件
3. 默认值 (最低优先级)

## 开发环境配置

### 1. 复制配置模板
```bash
cp .env.example .env
```

### 2. 修改配置
编辑 `.env` 文件，根据需要修改配置项。

### 3. 开发模式配置
```bash
# 开启调试模式
DEBUG=true
RELOAD=true
LOG_LEVEL=DEBUG

# 使用本地数据库
DATABASE_URL=postgresql://postgres:password@localhost:5432/wind_whisper_rag_dev
```

## 生产环境配置

### 1. 安全配置
```bash
# 生成强密钥
SECRET_KEY=$(openssl rand -hex 32)

# 关闭调试模式
DEBUG=false
RELOAD=false
LOG_LEVEL=INFO
```

### 2. 性能配置
```bash
# 增加工作进程
WORKERS=4

# 优化数据库连接池
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=40
```

### 3. AI模型配置
```bash
# 使用GPU
LLM_DEVICE=cuda
EMBEDDING_DEVICE=cuda

# 优化批处理
EMBEDDING_BATCH_SIZE=64
```

## Docker环境配置

### 1. 环境变量传递
```bash
# 通过-e参数传递
docker run -e PORT=8080 -e DEBUG=false wind-whisper-rag

# 通过--env-file传递
docker run --env-file .env wind-whisper-rag
```

### 2. Docker Compose配置
```yaml
services:
  app:
    environment:
      - PORT=8000
      - DEBUG=false
      - DATABASE_URL=postgresql://postgres:password@db:5432/wind_whisper_rag
    env_file:
      - .env
```

## 配置验证

系统启动时会自动验证配置的有效性：

1. **必需配置检查** - 确保关键配置项已设置
2. **类型验证** - 确保配置值类型正确
3. **范围检查** - 确保数值在合理范围内
4. **依赖检查** - 确保相关配置的一致性

## 故障排除

### 1. 配置加载失败
```bash
# 检查.env文件格式
cat .env | grep -v '^#' | grep '='

# 检查环境变量
env | grep -E '(DATABASE|PORT|SECRET)'
```

### 2. 模型路径问题
```bash
# 检查模型文件是否存在
ls -la /app/ai_models/

# 检查权限
ls -la /app/ai_models/Qwen2.5-0.5B-Instruct/
```

### 3. 数据库连接问题
```bash
# 测试数据库连接
psql $DATABASE_URL -c "SELECT 1;"
```

## 最佳实践

1. **不要在代码中硬编码配置值**
2. **使用环境变量覆盖开发配置**
3. **定期更新密钥和敏感配置**
4. **在生产环境中使用强密钥**
5. **根据硬件资源调整性能配置**
6. **使用配置验证确保系统稳定性**

## 配置迁移

从旧版本迁移到新配置系统：

1. **备份现有配置**
2. **使用新的配置文件格式**
3. **更新代码中的配置访问方式**
4. **测试配置加载和功能**
5. **清理旧的硬编码配置**