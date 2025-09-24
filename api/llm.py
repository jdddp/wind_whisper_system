from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from services.llm_service import LLMService
from utils.dependencies import get_current_user
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# 全局LLM服务实例
llm_service = None

class GenerateRequest(BaseModel):
    prompt: str
    max_tokens: Optional[int] = 500

class GenerateResponse(BaseModel):
    content: str
    success: bool
    error: Optional[str] = None

@router.on_event("startup")
async def startup_llm_service():
    """启动时初始化LLM服务"""
    global llm_service
    try:
        logger.info("Initializing LLM service...")
        llm_service = LLMService()
        logger.info(f"LLM service initialized. Available: {llm_service.is_available}")
    except Exception as e:
        logger.error(f"Failed to initialize LLM service: {e}")

@router.post("/generate", response_model=GenerateResponse)
async def generate_text(
    request: GenerateRequest,
    current_user = Depends(get_current_user)
):
    """生成文本响应"""
    global llm_service
    
    if llm_service is None:
        try:
            llm_service = LLMService()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"LLM service initialization failed: {str(e)}")
    
    if not llm_service.is_available:
        raise HTTPException(status_code=503, detail="LLM service is not available")
    
    try:
        result = await llm_service.generate_response(request.prompt, request.max_tokens)
        return GenerateResponse(**result)
    except Exception as e:
        logger.error(f"Error generating text: {e}")
        raise HTTPException(status_code=500, detail=f"Text generation failed: {str(e)}")

@router.get("/status")
async def get_llm_status(current_user = Depends(get_current_user)):
    """获取LLM服务状态"""
    global llm_service
    
    if llm_service is None:
        return {
            "available": False,
            "model": None,
            "device": None,
            "error": "LLM service not initialized"
        }
    
    return {
        "available": llm_service.is_available,
        "model": getattr(llm_service, 'model_name', None),
        "device": getattr(llm_service, 'device', None),
        "generator_loaded": llm_service.generator is not None
    }