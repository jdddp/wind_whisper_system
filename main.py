from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import os
import logging
import traceback
from api import api_router
from models import engine, Base

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="Wind Whisper RAG System",
    description="风机专家知识RAG系统",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境中应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局异常处理器
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理器"""
    logger.error(f"Global exception on {request.method} {request.url}: {str(exc)}")
    logger.error(f"Exception type: {type(exc).__name__}")
    logger.error(f"Traceback: {traceback.format_exc()}")
    
    # 如果是HTTPException，保持原有行为
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail}
        )
    
    # 其他异常返回500
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error": str(exc),
            "type": type(exc).__name__
        }
    )

# 包含API路由
app.include_router(api_router)

# 静态文件服务
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    logger.info("Starting Wind Whisper RAG System...")
    
    # 创建数据库表
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        raise e

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件"""
    logger.info("Shutting down Wind Whisper RAG System...")

@app.get("/")
async def root():
    """根路径，返回前端页面"""
    if os.path.exists("static/index.html"):
        return FileResponse("static/index.html")
    else:
        return {
            "message": "Wind Whisper RAG System API",
            "docs": "/api/docs",
            "version": "1.0.0"
        }

@app.get("/test-login")
async def test_login():
    """返回登录测试页面"""
    try:
        return FileResponse("test_login.html")
    except Exception as e:
        logger.error(f"Error serving test_login.html: {e}")
        raise HTTPException(status_code=404, detail="Test login page not found")

@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "service": "Wind Whisper RAG System",
        "version": "1.0.0"
    }

if __name__ == "__main__":
    import uvicorn
    from config.settings import get_settings, setup_environment
    
    # 设置环境变量
    setup_environment()
    
    # 获取配置
    settings = get_settings()
    server_config = settings.server
    
    uvicorn.run(
        "main:app",
        host=server_config.host,
        port=server_config.port,
        reload=server_config.reload,
        log_level=settings.logging.log_level.lower()
    )