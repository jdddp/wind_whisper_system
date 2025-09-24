"""
Wind Whisper RAG System 统一配置文件
集中管理所有配置项，避免硬编码

配置优先级：
1. 环境变量 (最高优先级)
2. .env 文件
3. 默认值 (最低优先级)

使用方法：
    from config.settings import get_settings
    settings = get_settings()
    db_url = settings.database.url
"""
import os
from typing import Optional, List
try:
    from pydantic_settings import BaseSettings
    from pydantic import Field, field_validator
except ImportError:
    # 如果pydantic-settings不可用，尝试从pydantic导入（旧版本）
    try:
        from pydantic import BaseSettings, Field, field_validator
    except ImportError:
        raise ImportError("需要安装 pydantic-settings: pip install pydantic-settings")


class DatabaseSettings(BaseSettings):
    """
    数据库相关配置
    
    包含数据库连接、连接池、查询优化等设置
    """
    model_config = {"extra": "allow"}
    url: str = Field(
        default="postgresql://postgres:postgres123@localhost:5432/wind_whisper_rag",
        env="DATABASE_URL",
        description="数据库连接URL，格式：postgresql://用户名:密码@主机:端口/数据库名"
    )
    echo: bool = Field(
        default=False,
        env="DATABASE_ECHO",
        description="是否在控制台打印SQL语句，用于调试，生产环境建议设为False"
    )
    pool_size: int = Field(
        default=10,
        env="DATABASE_POOL_SIZE",
        description="数据库连接池初始大小，根据并发需求调整，一般10-20个连接"
    )
    max_overflow: int = Field(
        default=20,
        env="DATABASE_MAX_OVERFLOW",
        description="连接池最大溢出连接数，当连接池满时可额外创建的连接数"
    )


class ServerSettings(BaseSettings):
    """
    服务器运行配置
    
    控制FastAPI服务器的启动参数、性能设置等
    """
    model_config = {"extra": "allow"}
    host: str = Field(
        default="0.0.0.0",
        env="HOST",
        description="服务器监听地址，0.0.0.0表示监听所有网络接口，127.0.0.1仅本地访问"
    )
    port: int = Field(
        default=8000,
        env="PORT",
        description="服务器监听端口，范围1024-65535，确保端口未被占用"
    )
    debug: bool = Field(
        default=False,
        env="DEBUG",
        description="调试模式开关，True时显示详细错误信息，生产环境必须设为False"
    )
    reload: bool = Field(
        default=False,
        env="RELOAD",
        description="热重载开关，True时代码变更自动重启服务，仅开发环境使用"
    )
    workers: int = Field(
        default=1,
        env="WORKERS",
        description="工作进程数量，建议设为CPU核心数，单进程调试时设为1"
    )


class AIModelSettings(BaseSettings):
    """
    AI模型相关配置
    
    包含大语言模型(LLM)、嵌入模型(Embedding)的路径、参数设置
    """
    model_config = {"extra": "allow"}
    # ==================== LLM模型配置 ====================
    llm_model_name: str = Field(
        default="Qwen/Qwen2.5-0.5B-Instruct",
        env="LLM_MODEL_NAME",
        description="LLM模型名称，HuggingFace模型ID或本地路径标识"
    )
    llm_local_path: str = Field(
        default="/app/ai_models/Qwen2.5-0.5B-Instruct",
        env="LLM_LOCAL_PATH",
        description="LLM本地模型文件路径，优先使用本地模型以避免网络下载"
    )
    llm_max_length: int = Field(
        default=2048,
        env="LLM_MAX_LENGTH",
        description="LLM最大生成token数量，影响回答长度，范围512-4096"
    )
    llm_temperature: float = Field(
        default=0.7,
        env="LLM_TEMPERATURE",
        description="LLM生成温度，控制随机性，0.1-1.0，越高越随机，0.7适中"
    )
    llm_top_p: float = Field(
        default=0.9,
        env="LLM_TOP_P",
        description="LLM Top-p采样参数，控制词汇选择范围，0.1-1.0，0.9较好"
    )
    llm_device: Optional[str] = Field(
        default=None,
        env="LLM_DEVICE",
        description="LLM运行设备，auto自动选择/cuda使用GPU/cpu使用CPU，None为自动"
    )
    
    # ==================== 嵌入模型配置 ====================
    embedding_model_name: str = Field(
        default="BAAI/bge-m3",
        env="EMBEDDING_MODEL_NAME",
        description="嵌入模型名称，用于文本向量化，BGE-M3支持中英文"
    )
    embedding_local_path: str = Field(
        default="/app/ai_models/bge-m3",
        env="EMBEDDING_LOCAL_PATH",
        description="嵌入模型本地路径，优先使用本地模型文件"
    )
    embedding_device: Optional[str] = Field(
        default=None,
        env="EMBEDDING_DEVICE",
        description="嵌入模型运行设备，auto/cuda/cpu，None为自动选择"
    )
    embedding_batch_size: int = Field(
        default=32,
        env="EMBEDDING_BATCH_SIZE",
        description="嵌入模型批处理大小，影响处理速度和内存占用，8-64合适"
    )
    
    # ==================== 模型通用配置 ====================
    transformers_offline: bool = Field(
        default=True,
        env="TRANSFORMERS_OFFLINE",
        description="Transformers离线模式，True时不从网络下载模型，仅使用本地"
    )
    hf_hub_offline: bool = Field(
        default=True,
        env="HF_HUB_OFFLINE",
        description="HuggingFace Hub离线模式，True时禁用在线模型下载"
    )


class RAGSettings(BaseSettings):
    """
    RAG检索增强生成配置
    
    控制文档处理、向量检索、上下文构建等核心参数
    """
    model_config = {"extra": "allow"}
    chunk_size: int = Field(
        default=500,
        env="RAG_CHUNK_SIZE",
        description="文档分块大小(字符数)，影响检索精度，200-1000合适，500为平衡值"
    )
    chunk_overlap: int = Field(
        default=50,
        env="RAG_CHUNK_OVERLAP",
        description="文档分块重叠字符数，保持上下文连贯性，通常为chunk_size的10%"
    )
    top_k: int = Field(
        default=5,
        env="RAG_TOP_K",
        description="检索返回的相关文档数量，3-10合适，越多上下文越丰富但可能引入噪音"
    )
    similarity_threshold: float = Field(
        default=0.7,
        env="RAG_SIMILARITY_THRESHOLD",
        description="相似度阈值，0-1之间，高于此值的文档才会被使用，0.6-0.8合适"
    )
    max_context_length: int = Field(
        default=4000,
        env="RAG_MAX_CONTEXT_LENGTH",
        description="最大上下文长度(字符数)，限制输入LLM的文本总量，需小于模型最大长度"
    )


class SecuritySettings(BaseSettings):
    """
    安全认证配置
    
    JWT令牌、密钥管理、会话控制等安全相关设置
    """
    model_config = {"extra": "allow"}
    secret_key: str = Field(
        default="your-secret-key-here-change-in-production",
        env="SECRET_KEY",
        description="应用密钥，用于JWT签名和加密，生产环境必须使用强随机字符串(32+字符)"
    )
    algorithm: str = Field(
        default="HS256",
        env="JWT_ALGORITHM",
        description="JWT加密算法，HS256为对称加密，RS256为非对称加密，推荐HS256"
    )
    access_token_expire_minutes: int = Field(
        default=30,
        env="ACCESS_TOKEN_EXPIRE_MINUTES",
        description="访问令牌过期时间(分钟)，15-60分钟合适，过短影响体验，过长有安全风险"
    )
    refresh_token_expire_days: int = Field(
        default=7,
        env="REFRESH_TOKEN_EXPIRE_DAYS",
        description="刷新令牌过期时间(天)，7-30天合适，用于自动续期访问令牌"
    )


class FileStorageSettings(BaseSettings):
    """
    文件存储配置
    
    管理文件上传、存储路径、大小限制等文件处理相关设置
    """
    model_config = {
        "extra": "allow",
        "env_parse_none_str": "None",
        "env_parse_enums": False
    }
    upload_dir: str = Field(
        default="./uploads",
        env="UPLOAD_DIR",
        description="文件上传存储目录，相对路径基于项目根目录，确保目录有写权限"
    )
    max_file_size: int = Field(
        default=10 * 1024 * 1024,  # 10MB
        env="MAX_FILE_SIZE",
        description="单个文件最大大小(字节)，10MB=10485760字节，根据服务器性能调整"
    )
    allowed_extensions_str: str = Field(
        default=".txt,.pdf,.docx,.md",
        description="允许上传的文件扩展名列表（逗号分隔）",
        env="ALLOWED_EXTENSIONS"
    )
    
    @property
    def allowed_extensions(self) -> List[str]:
        """获取允许的文件扩展名列表"""
        return [ext.strip() for ext in self.allowed_extensions_str.split(',') if ext.strip()]  # 默认值


class LoggingSettings(BaseSettings):
    """
    日志系统配置
    
    控制日志级别、文件路径、轮转策略等日志管理设置
    """
    model_config = {"extra": "allow"}
    log_level: str = Field(
        default="INFO",
        env="LOG_LEVEL",
        description="日志级别，DEBUG/INFO/WARNING/ERROR/CRITICAL，开发用DEBUG，生产用INFO"
    )
    log_file: str = Field(
        default="./logs/app.log",
        env="LOG_FILE",
        description="日志文件存储路径，相对路径基于项目根目录，确保logs目录存在"
    )
    log_rotation: str = Field(
        default="1 day",
        env="LOG_ROTATION",
        description="日志文件轮转周期，支持'1 day'/'1 week'/'100 MB'等格式"
    )
    log_retention: str = Field(
        default="30 days",
        env="LOG_RETENTION",
        description="日志文件保留时间，超过此时间的日志文件将被自动删除"
    )


class TestSettings(BaseSettings):
    """
    测试环境配置
    
    单元测试、集成测试相关的数据库和环境设置
    """
    model_config = {"extra": "allow"}
    base_url: str = Field(
        default="http://localhost:8003",
        env="TEST_BASE_URL",
        description="测试基础URL"
    )
    timeout: int = Field(
        default=30,
        env="TEST_TIMEOUT",
        description="测试超时时间(秒)"
    )
    test_db_url: str = Field(
        default="postgresql://postgres:postgres123@localhost:5432/wind_whisper_rag_test",
        env="TEST_DATABASE_URL",
        description="测试数据库URL"
    )
    test_mode: bool = Field(
        default=False,
        env="TEST_MODE",
        description="测试模式开关，True时启用测试配置，禁用某些生产功能如邮件发送"
    )


class AppInfo(BaseSettings):
    """
    应用基本信息配置
    
    应用名称、版本、描述等元数据信息
    """
    model_config = {"extra": "allow"}
    name: str = Field(
        default="Wind Whisper RAG System",
        env="APP_NAME",
        description="应用名称，显示在API文档、日志、错误信息中"
    )
    version: str = Field(
        default="1.0.0",
        env="APP_VERSION",
        description="应用版本号，遵循语义化版本规范(major.minor.patch)"
    )
    description: str = Field(
        default="基于RAG的智能问答系统",
        env="APP_DESCRIPTION",
        description="应用功能描述，显示在API文档首页和系统介绍中"
    )


class Settings(BaseSettings):
    """
    主配置类 - 系统核心配置管理
    
    整合所有子配置模块，提供统一的配置访问接口
    支持环境变量覆盖，自动加载.env文件
    """
    model_config = {
        "extra": "allow",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False
    }
    
    # 各模块配置
    app_info: AppInfo = AppInfo()
    database: DatabaseSettings = DatabaseSettings()
    server: ServerSettings = ServerSettings()
    ai_model: AIModelSettings = AIModelSettings()
    rag: RAGSettings = RAGSettings()
    security: SecuritySettings = SecuritySettings()
    file_storage: FileStorageSettings = FileStorageSettings()
    logging: LoggingSettings = LoggingSettings()
    test: TestSettings = TestSettings()


# 全局配置实例
settings = Settings()


def get_settings() -> Settings:
    """获取配置实例"""
    return settings


def reload_settings():
    """重新加载配置"""
    global settings
    settings = Settings()
    return settings


# ==================== 便捷访问函数 ====================
# 提供快速访问常用配置的函数，简化代码调用

def get_database_url() -> str:
    """
    获取数据库连接URL
    
    Returns:
        str: 完整的数据库连接字符串，包含用户名、密码、主机、端口、数据库名
    """
    return settings.database.url


def get_server_config() -> dict:
    """
    获取服务器运行配置字典
    
    Returns:
        dict: 包含host、port、debug、reload、workers的服务器配置
        用于uvicorn.run()等服务器启动函数
    """
    return {
        "host": settings.server.host,
        "port": settings.server.port,
        "debug": settings.server.debug,
        "reload": settings.server.reload,
        "workers": settings.server.workers
    }


def get_ai_model_config() -> dict:
    """
    获取AI模型配置字典
    
    Returns:
        dict: 包含LLM和嵌入模型的名称、路径、离线模式等配置
        用于初始化LLMService和EmbeddingService
    """
    return {
        "llm_model_name": settings.ai_model.llm_model_name,
        "llm_local_path": settings.ai_model.llm_local_path,
        "embedding_model_name": settings.ai_model.embedding_model_name,
        "embedding_local_path": settings.ai_model.embedding_local_path,
        "transformers_offline": settings.ai_model.transformers_offline,
        "hf_hub_offline": settings.ai_model.hf_hub_offline
    }


def is_production() -> bool:
    """判断是否为生产环境"""
    return not settings.server.debug


def setup_environment():
    """设置环境变量"""
    if settings.ai_model.transformers_offline:
        os.environ['TRANSFORMERS_OFFLINE'] = '1'
    if settings.ai_model.hf_hub_offline:
        os.environ['HF_HUB_OFFLINE'] = '1'