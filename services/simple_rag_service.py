import logging
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import text
from models import ExpertLog, Turbine, LogChunk
from .embedding_service import EmbeddingService
from .llm_service import LLMService

logger = logging.getLogger(__name__)

class SimpleRAGService:
    """简化的RAG服务 - 直接基于数据库检索和大模型回答"""
    
    def __init__(self, db: Session):
        self.db = db
        self.embedding_service = EmbeddingService()
        self.llm_service = LLMService()
    
    async def query(self, question: str, max_results: int = 5) -> Dict[str, Any]:
        """
        简单直接的RAG查询
        1. 从数据库检索相关文档
        2. 大模型基于检索内容生成回答
        """
        try:
            # 1. 检索相关文档
            relevant_docs = await self._search_relevant_documents(question, max_results)
            
            # 2. 如果没有找到相关文档，返回默认回答
            if not relevant_docs:
                return {
                    "answer": "抱歉，没有找到相关的风机数据来回答您的问题。",
                    "sources": [],
                    "query_time": 0,
                    "query_type": "document_search",
                    "metadata": {}
                }
            
            # 3. 大模型基于检索内容生成回答
            answer = await self._generate_answer(question, relevant_docs)
            
            # 格式化sources以符合RAGSource schema
            formatted_sources = []
            for doc in relevant_docs:
                formatted_sources.append({
                    "log_id": str(doc.get("log_id", "")),  # 确保转换为字符串
                    "chunk_text": doc["content"],
                    "similarity_score": 1.0 - doc.get("distance", 0.0),  # 转换距离为相似度
                    "turbine_info": doc.get("turbine_name", "未知风机"),
                    "published_at": ""  # 暂时为空，后续可以从数据库获取
                })
            
            return {
                "answer": answer,
                "sources": formatted_sources,
                "query_time": 0,
                "query_type": "document_search",
                "metadata": {
                    "total_docs_found": len(relevant_docs),
                    "search_method": "vector_similarity"
                }
            }
            
        except Exception as e:
            logger.error(f"RAG查询错误: {e}")
            return {
                "answer": f"查询过程中出现错误：{str(e)}",
                "sources": [],
                "query_time": 0,
                "query_type": "document_search",
                "metadata": {"error": str(e)}
            }
    
    async def _search_relevant_documents(self, question: str, max_results: int) -> List[Dict]:
        """从数据库检索相关文档"""
        try:
            # 生成查询向量
            query_embedding = await self.embedding_service.get_embedding(question)
            
            # 使用向量相似度搜索
            sql = text("""
                SELECT 
                    lc.chunk_id,
                    lc.chunk_text as content,
                    lc.log_id,
                    CONCAT(t.farm_name, '-', t.unit_id) as turbine_name,
                    (lc.embedding <=> :query_embedding) as distance
                FROM log_chunks lc
                JOIN expert_logs el ON lc.log_id = el.log_id
                LEFT JOIN turbines t ON el.turbine_id = t.turbine_id
                WHERE lc.embedding IS NOT NULL
                ORDER BY lc.embedding <=> :query_embedding
                LIMIT :limit
            """)
            
            result = self.db.execute(sql, {
                "query_embedding": str(query_embedding),
                "limit": max_results
            })
            
            docs = []
            for row in result:
                docs.append({
                    "content": row.content,
                    "log_id": row.log_id,
                    "turbine_name": row.turbine_name or "未知风机",
                    "distance": row.distance
                })
            
            return docs
            
        except Exception as e:
            logger.error(f"文档检索错误: {e}")
            # 如果向量搜索失败，使用简单的文本搜索
            return await self._fallback_text_search(question, max_results)
    
    async def _fallback_text_search(self, question: str, max_results: int) -> List[Dict]:
        """备用的文本搜索"""
        try:
            # 提取关键词
            keywords = question.replace("？", "").replace("?", "").split()
            
            # 构建LIKE查询
            conditions = []
            params = {"limit": max_results}
            
            for i, keyword in enumerate(keywords[:3]):  # 最多使用3个关键词
                conditions.append(f"(lc.text LIKE :keyword_{i} OR el.title LIKE :keyword_{i})")
                params[f"keyword_{i}"] = f"%{keyword}%"
            
            if not conditions:
                return []
            
            sql = text(f"""
                SELECT 
                    lc.id,
                    lc.text as content,
                    lc.log_id,
                    el.title,
                    t.name as turbine_name
                FROM log_chunks lc
                JOIN expert_logs el ON lc.log_id = el.id
                LEFT JOIN turbines t ON el.turbine_id = t.id
                WHERE {' OR '.join(conditions)}
                LIMIT :limit
            """)
            
            result = self.db.execute(sql, params)
            
            docs = []
            for row in result:
                docs.append({
                    "content": row.content,
                    "log_id": row.log_id,
                    "title": row.title,
                    "turbine_name": row.turbine_name or "未知风机"
                })
            
            return docs
            
        except Exception as e:
            logger.error(f"备用文本搜索错误: {e}")
            return []
    
    async def _generate_answer(self, question: str, relevant_docs: List[Dict]) -> str:
        """基于检索到的文档生成回答"""
        try:
            # 构建上下文
            context = "\n\n".join([
                f"【{doc['turbine_name']} - {doc.get('title', '专家日志')}】\n{doc['content']}"
                for doc in relevant_docs
            ])
            
            # 构建提示词
            prompt = f"""基于以下风机相关信息，回答用户的问题。请用专业但易懂的语言回答。

相关信息：
{context}

用户问题：{question}

请基于上述信息回答问题，如果信息不足以回答问题，请说明需要更多信息。"""

            # 调用大模型生成回答
            response = await self.llm_service.generate_response(prompt)
            # 从响应字典中提取content字段
            if isinstance(response, dict):
                return response.get("content", "生成回答失败")
            else:
                return str(response)
            
        except Exception as e:
            logger.error(f"答案生成错误: {e}")
            return f"抱歉，在生成回答时出现错误：{str(e)}"