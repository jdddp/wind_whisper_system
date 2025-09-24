import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import text, and_
from typing import List, Dict, Any, Optional
import logging
from models import ExpertLog, LogChunk, Turbine
from models.expert_log import LogStatus
from schemas.rag import RAGSource
from .embedding_service import EmbeddingService
from .llm_service import LLMService

logger = logging.getLogger(__name__)

class RAGService:
    """RAG检索增强生成服务"""
    
    def __init__(self, db: Session):
        """
        初始化RAG服务
        Args:
            db: 数据库会话
        """
        self.db = db
        self.embedding_service = EmbeddingService()
        self.llm_service = LLMService()
        self.chunk_size = 500  # 文本分块大小
        self.chunk_overlap = 50  # 分块重叠大小
    
    def _split_text(self, text: str) -> List[str]:
        """
        将长文本分割成块
        Args:
            text: 原始文本
        Returns:
            文本块列表
        """
        if len(text) <= self.chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.chunk_size
            
            # 如果不是最后一块，尝试在句号或换行符处分割
            if end < len(text):
                # 寻找最近的句号或换行符
                for i in range(end, max(start + self.chunk_size - 100, start), -1):
                    if text[i] in ['。', '\n', '！', '？']:
                        end = i + 1
                        break
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            start = end - self.chunk_overlap
            if start >= len(text):
                break
        
        return chunks
    
    async def process_expert_log(self, log_id: int) -> Dict[str, Any]:
        """
        处理专家记录，生成嵌入向量和AI增强内容
        Args:
            log_id: 专家记录ID
        Returns:
            处理结果
        """
        try:
            # 获取专家记录
            log = self.db.query(ExpertLog).filter(ExpertLog.log_id == log_id).first()
            if not log:
                raise ValueError(f"Expert log {log_id} not found")
            
            # 删除旧的分块
            self.db.query(LogChunk).filter(LogChunk.log_id == log_id).delete()
            
            # 分割文本
            chunks = self._split_text(log.description_text)
            
            # 生成嵌入向量
            embeddings = self.embedding_service.encode(chunks)
            
            # 保存分块和嵌入向量
            chunk_count = 0
            for i, (chunk_text, embedding) in enumerate(zip(chunks, embeddings)):
                chunk = LogChunk(
                    log_id=log_id,
                    turbine_id=log.turbine_id,
                    chunk_text=chunk_text,
                    embedding=embedding.tolist(),  # 转换为列表存储
                    status_tag=log.status_tag.value,  # 添加状态标签
                    published_at=log.published_at  # 添加发布时间
                )
                self.db.add(chunk)
                chunk_count += 1
            
            # 生成AI增强内容
            turbine = self.db.query(Turbine).filter(Turbine.turbine_id == log.turbine_id).first()
            context = {
                "turbine_info": f"{turbine.farm_name} - {turbine.unit_id}" if turbine else ""
            }
            
            # 生成摘要
            ai_summary = await self.llm_service.generate_summary(log.description_text, context)
            
            # 生成结构化标签
            ai_tags = await self.llm_service.generate_tags(log.description_text, ai_summary)
            
            # 更新专家记录
            log.ai_summary = ai_summary
            log.ai_tags = ai_tags
            
            self.db.commit()
            
            return {
                "log_id": log_id,
                "chunks_created": chunk_count,
                "ai_summary": ai_summary,
                "ai_tags": ai_tags
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to process expert log {log_id}: {e}")
            raise e
    
    async def search_similar_chunks(
        self, 
        query: str, 
        turbine_id: Optional[int] = None, 
        max_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        搜索相似的文档块
        Args:
            query: 查询文本
            turbine_id: 风机ID（可选）
            max_results: 最大结果数
        Returns:
            相似文档块列表
        """
        try:
            # 生成查询向量
            query_embedding = self.embedding_service.encode(query)
            
            # 构建查询条件
            query_conditions = []
            if turbine_id:
                query_conditions.append(LogChunk.turbine_id == turbine_id)
            
            # 只搜索已发布的记录
            query_conditions.append(
                LogChunk.log_id.in_(
                    self.db.query(ExpertLog.log_id).filter(
                        ExpertLog.log_status == LogStatus.PUBLISHED
                    )
                )
            )
            
            # 使用PostgreSQL的向量相似度搜索
            # 注意：这里需要安装pgvector扩展
            similarity_query = text("""
                SELECT 
                    lc.chunk_id,
                    lc.log_id,
                    lc.turbine_id,
                    lc.chunk_text,
                    lc.chunk_index,
                    el.title,
                    el.published_at,
                    t.farm_name,
                    t.unit_id,
                    1 - (lc.embedding <=> :query_embedding) as similarity
                FROM log_chunks lc
                JOIN expert_logs el ON lc.log_id = el.log_id
                JOIN turbines t ON lc.turbine_id = t.turbine_id
                WHERE el.log_status = 'published'
                """ + (f" AND lc.turbine_id = {turbine_id}" if turbine_id else "") + """
                ORDER BY lc.embedding <=> :query_embedding
                LIMIT :max_results
            """)
            
            result = self.db.execute(
                similarity_query,
                {
                    "query_embedding": query_embedding.tolist(),
                    "max_results": max_results
                }
            )
            
            chunks = []
            for row in result:
                chunks.append({
                    "chunk_id": row.chunk_id,
                    "log_id": row.log_id,
                    "turbine_id": row.turbine_id,
                    "text": row.chunk_text,
                    "chunk_index": row.chunk_index,
                    "title": row.title,
                    "published_at": row.published_at.isoformat() if row.published_at else None,
                    "turbine_info": f"{row.farm_name} - {row.unit_id}",
                    "similarity": float(row.similarity)
                })
            
            return chunks
            
        except Exception as e:
            logger.error(f"Failed to search similar chunks: {e}")
            # 如果向量搜索失败，回退到文本搜索
            return await self._fallback_text_search(query, turbine_id, max_results)
    
    async def _fallback_text_search(
        self, 
        query: str, 
        turbine_id: Optional[int] = None, 
        max_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        回退的文本搜索方法
        """
        try:
            query_obj = self.db.query(
                LogChunk.chunk_id,
                LogChunk.log_id,
                LogChunk.turbine_id,
                LogChunk.chunk_text,
                LogChunk.chunk_index,
                ExpertLog.title,
                ExpertLog.published_at,
                Turbine.farm_name,
                Turbine.unit_id
            ).join(
                ExpertLog, LogChunk.log_id == ExpertLog.log_id
            ).join(
                Turbine, LogChunk.turbine_id == Turbine.turbine_id
            ).filter(
                ExpertLog.status == 'published'
            )
            
            if turbine_id:
                query_obj = query_obj.filter(LogChunk.turbine_id == turbine_id)
            
            # 简单的文本匹配
            query_obj = query_obj.filter(
                LogChunk.chunk_text.ilike(f"%{query}%")
            ).limit(max_results)
            
            chunks = []
            for row in query_obj.all():
                chunks.append({
                    "chunk_id": row.chunk_id,
                    "log_id": row.log_id,
                    "turbine_id": row.turbine_id,
                    "text": row.chunk_text,
                    "chunk_index": row.chunk_index,
                    "title": row.title,
                    "published_at": row.published_at.isoformat() if row.published_at else None,
                    "turbine_info": f"{row.farm_name} - {row.unit_id}",
                    "similarity": 0.5  # 默认相似度
                })
            
            return chunks
            
        except Exception as e:
            logger.error(f"Fallback text search failed: {e}")
            return []
    
    async def query(
        self, 
        question: str, 
        turbine_id: Optional[int] = None, 
        max_results: int = 5
    ) -> Dict[str, Any]:
        """
        RAG查询主方法
        Args:
            question: 用户问题
            turbine_id: 风机ID（可选）
            max_results: 最大检索结果数
        Returns:
            包含答案和来源的字典
        """
        try:
            # 检索相关文档块
            similar_chunks = await self.search_similar_chunks(
                question, turbine_id, max_results
            )
            
            # 生成答案
            answer = await self.llm_service.answer_question(question, similar_chunks)
            
            # 构建来源信息
            sources = []
            for chunk in similar_chunks:
                source = RAGSource(
                    log_id=chunk["log_id"],
                    chunk_text=chunk["text"],
                    similarity_score=chunk["similarity"],
                    turbine_info=chunk["turbine_info"],
                    published_at=chunk["published_at"]
                )
                sources.append(source)
            
            return {
                "answer": answer,
                "sources": sources
            }
            
        except Exception as e:
            logger.error(f"RAG query failed: {e}")
            return {
                "answer": f"抱歉，查询过程中出现错误：{str(e)}",
                "sources": []
            }
    
    async def reindex_all_documents(self) -> Dict[str, Any]:
        """
        重新索引所有已发布的文档
        Returns:
            处理结果统计
        """
        try:
            # 获取所有已发布的专家记录
            published_logs = self.db.query(ExpertLog).filter(
                ExpertLog.log_status == LogStatus.PUBLISHED
            ).all()
            
            total_chunks = 0
            processed_logs = 0
            
            for log in published_logs:
                try:
                    result = await self.process_expert_log(log.log_id)
                    total_chunks += result["chunks_created"]
                    processed_logs += 1
                    logger.info(f"Processed log {log.log_id}: {result['chunks_created']} chunks")
                except Exception as e:
                    logger.error(f"Failed to process log {log.log_id}: {e}")
                    continue
            
            return {
                "processed_logs": processed_logs,
                "total_chunks": total_chunks
            }
            
        except Exception as e:
            logger.error(f"Failed to reindex documents: {e}")
            raise e