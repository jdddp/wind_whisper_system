from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import time
import os
from models import get_db, User
from schemas.rag import RAGQuery, RAGResponse, RAGSource
from services.rag_service import RAGService
from services.simple_rag_service import SimpleRAGService
from utils.dependencies import get_current_user

router = APIRouter()

@router.post("/query", response_model=RAGResponse)
async def rag_query(
    query: RAGQuery,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """智能RAG问答查询 - 基于语义理解的查询路由"""
    start_time = time.time()
    
    try:
        # 使用简化的RAG服务
        simple_rag_service = SimpleRAGService(db)
        result = await simple_rag_service.query(
            question=query.question,
            max_results=query.max_results
        )
        
        query_time = time.time() - start_time
        
        return RAGResponse(
            answer=result["answer"],
            sources=result.get("sources", []),
            query_time=query_time,
            query_type=result.get("query_type", "document_search"),
            metadata=result.get("data", {})
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG query failed: {str(e)}")

@router.post("/reindex")
async def reindex_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """重新索引所有文档（管理员功能）"""
    if current_user.role.value != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        rag_service = RAGService(db)
        result = await rag_service.reindex_all_documents()
        return {"message": f"Reindexed {result['processed_logs']} logs with {result['total_chunks']} chunks"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reindexing failed: {str(e)}")