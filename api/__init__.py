from fastapi import APIRouter
from .auth import router as auth_router
from .turbines import router as turbines_router
from .expert_logs import router as expert_logs_router
from .rag import router as rag_router
from .dashboard import router as dashboard_router
from .timeline import router as timeline_router
from .llm import router as llm_router

api_router = APIRouter(prefix="/api")

api_router.include_router(auth_router, prefix="/auth", tags=["认证"])
api_router.include_router(turbines_router, prefix="/turbines", tags=["风机管理"])
api_router.include_router(expert_logs_router, prefix="/expert-logs", tags=["专家记录"])
api_router.include_router(rag_router, prefix="/rag", tags=["RAG问答"])
api_router.include_router(dashboard_router, prefix="/dashboard", tags=["驾驶舱"])
api_router.include_router(timeline_router, prefix="/timeline", tags=["时间线"])
api_router.include_router(llm_router, prefix="/llm", tags=["LLM服务"])