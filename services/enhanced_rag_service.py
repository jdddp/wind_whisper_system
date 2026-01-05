import re
import json
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, text
import logging

from models import ExpertLog, Turbine, LogChunk
from models.expert_log import LogStatus
from .rag_service import RAGService
from .llm_service import LLMService
from .smart_query_handler import SmartQueryHandler
from .multi_turbine_aggregator import MultiTurbineAggregator

logger = logging.getLogger(__name__)

class EnhancedRAGService(RAGService):
    """增强的RAG服务 - 支持数据库直接查询和统计分析"""
    
    def __init__(self, db: Session, model_path: str = "ai_models/Qwen2-1.5B-Instruct"):
        super().__init__(db)
        self.smart_query_handler = SmartQueryHandler(db, model_path)
        self.multi_turbine_aggregator = MultiTurbineAggregator(db)
    

    
    async def query(self, question: str, turbine_id: Optional[str] = None, limit: int = 5) -> Dict[str, Any]:
        """增强的查询方法 - 基于智能语义理解"""
        try:
            # 使用智能查询处理器
            smart_result = await self.smart_query_handler.execute_query(question)
            
            # 检查是否需要转发给RAG系统
            if smart_result.get("should_forward_to_rag", False):
                # 技术类问题转发给RAG系统
                query_text = question
                enhanced_metadata = {}
                
                # 如果是增强的技术查询，使用增强的问题文本
                if smart_result.get("query_type") == "technical_enhanced":
                    enhanced_question = smart_result.get("enhanced_question", question)
                    context_data = smart_result.get("context_data", {})
                    
                    # 使用增强的问题进行RAG查询
                    query_text = enhanced_question
                    enhanced_metadata = {
                        "original_question": question,
                        "enhanced_question": enhanced_question,
                        "context_data": context_data
                    }
                
                # 执行RAG查询
                rag_result = await self._enhanced_rag_query(query_text, turbine_id, limit, enhanced_metadata)
                
                return {
                    "answer": rag_result.get("answer", "未找到相关信息"),
                    "sources": rag_result.get("sources", []),
                    "query_type": smart_result.get("query_type", "technical"),
                    "metadata": {
                        "intent_analysis": smart_result.get("intent_analysis", {}),
                        "forwarded_to_rag": True,
                        **enhanced_metadata
                    }
                }
            else:
                # 直接返回智能查询结果
                return {
                    "answer": smart_result.get("answer", "未找到相关信息"),
                    "sources": [],
                    "query_type": smart_result.get("query_type", "smart_query"),
                    "metadata": smart_result.get("data", {})
                }
                
        except Exception as e:
            logger.error(f"Enhanced RAG query error: {e}")
            return {
                "answer": f"查询出现错误：{str(e)}",
                "sources": [],
                "query_type": "error",
                "metadata": {}
            }
    
    async def enhanced_query(self, question: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """增强查询方法 - 支持多种查询类型的智能路由和多风机数据聚合"""
        try:
            # 检查是否需要多风机数据聚合
            multi_turbine_keywords = ['所有风机', '全部风机', '各个风机', '多台风机', '整体', '总体', '对比', '分布']
            needs_aggregation = any(keyword in question for keyword in multi_turbine_keywords)
            
            # 如果需要多风机聚合，先获取聚合数据
            aggregated_data = None
            if needs_aggregation:
                # 从问题中提取过滤条件
                turbine_filters = self._extract_turbine_filters(question)
                aggregated_data = await self.multi_turbine_aggregator.aggregate_turbine_data(
                    question, turbine_filters
                )
            
            # 查询分类
            if any(keyword in question.lower() for keyword in ['多少', '数量', '统计', '总共']):
                query_type = "count"
            elif any(keyword in question.lower() for keyword in ['状态', '情况', '运行']):
                query_type = "status"
            elif any(keyword in question.lower() for keyword in ['故障', '异常', '问题', '错误']):
                query_type = "fault"
            elif any(keyword in question.lower() for keyword in ['维护', '检修', '保养']):
                query_type = "maintenance"
            else:
                query_type = "general"
            
            # 根据查询类型选择处理方式
            if query_type in ["count", "status", "fault", "maintenance"]:
                # 使用智能查询处理器
                result = await self.smart_query_handler.execute_query(question)
                
                # 如果智能查询处理器返回了增强的技术查询，使用增强的RAG
                if result.get("query_type") == "enhanced_technical":
                    enhanced_question = result.get("enhanced_question", question)
                    context_data = result.get("context_data", {})
                    
                    # 如果有聚合数据，将其添加到上下文中
                    if aggregated_data:
                        context_data["aggregated_turbine_data"] = aggregated_data
                    
                    # 生成增强的元数据
                    enhanced_metadata = {
                        "original_question": question,
                        "enhanced_question": enhanced_question,
                        "context_data": context_data,
                        "enhancement_type": "technical_context",
                        "has_aggregation": needs_aggregation
                    }
                    
                    # 使用增强的RAG查询
                    rag_result = await self._enhanced_rag_query(enhanced_question, context_data)
                    rag_result["query_type"] = "enhanced_technical"
                    rag_result["metadata"] = enhanced_metadata
                    
                    return rag_result
                else:
                    # 如果有聚合数据，增强返回结果
                    if aggregated_data:
                        result["aggregated_data"] = aggregated_data
                        result["enhanced_with_aggregation"] = True
                    return result
            else:
                # 使用传统RAG，但如果有聚合数据则增强上下文
                enhanced_context = context or {}
                if aggregated_data:
                    enhanced_context["aggregated_turbine_data"] = aggregated_data
                
                rag_result = await super().query(question, enhanced_context)
                
                # 如果有聚合数据，增强答案
                if aggregated_data:
                    rag_result = await self._enhance_answer_with_aggregation(
                        rag_result, aggregated_data, question
                    )
                
                return rag_result
                
        except Exception as e:
            logger.error(f"Error in enhanced query: {e}")
            return {
                "answer": f"查询处理出现错误：{str(e)}",
                "sources": [],
                "query_type": "error"
            }
    
    async def _enhanced_rag_query(
        self, 
        query_text: str, 
        turbine_id: Optional[str] = None, 
        limit: int = 5,
        enhanced_metadata: Dict = None
    ) -> Dict[str, Any]:
        """增强的RAG查询方法，支持上下文感知的文档检索"""
        try:
            # 使用父类的查询方法进行文档检索
            base_result = await super().query(query_text, turbine_id, limit)
            
            # 如果有增强的元数据，进一步优化结果
            if enhanced_metadata and enhanced_metadata.get("context_data"):
                context_data = enhanced_metadata["context_data"]
                
                # 基于上下文数据过滤和重新排序结果
                enhanced_sources = self._rerank_sources_with_context(
                    base_result.get("sources", []), 
                    context_data
                )
                
                # 生成更好的答案
                enhanced_answer = await self._generate_contextual_answer(
                    enhanced_metadata.get("original_question", query_text),
                    enhanced_sources,
                    context_data
                )
                
                return {
                    "answer": enhanced_answer,
                    "sources": enhanced_sources,
                    "enhanced": True
                }
            
            return base_result
            
        except Exception as e:
            logger.error(f"Enhanced RAG query failed: {e}")
            return {
                "answer": f"增强查询过程中出现错误：{str(e)}",
                "sources": [],
                "enhanced": False
            }
    
    def _rerank_sources_with_context(self, sources: List, context_data: Dict) -> List:
        """基于上下文数据重新排序来源"""
        try:
            if not sources or not context_data:
                return sources
            
            # 获取相关的风机ID
            relevant_turbine_ids = set()
            if "turbines" in context_data:
                relevant_turbine_ids = {t["turbine_id"] for t in context_data["turbines"]}
            
            # 重新排序：优先显示相关风机的记录
            reranked_sources = []
            other_sources = []
            
            for source in sources:
                # 检查来源是否与上下文中的风机相关
                if hasattr(source, 'turbine_id') and source.turbine_id in relevant_turbine_ids:
                    reranked_sources.append(source)
                else:
                    other_sources.append(source)
            
            # 合并结果：相关的在前，其他的在后
            return reranked_sources + other_sources
            
        except Exception as e:
            logger.error(f"Error reranking sources: {e}")
            return sources
    
    async def _generate_contextual_answer(
        self, 
        original_question: str, 
        sources: List, 
        context_data: Dict
    ) -> str:
        """生成基于上下文的答案"""
        try:
            # 构建增强的上下文信息
            context_chunks = []
            
            # 添加来源信息
            for source in sources:
                if hasattr(source, 'chunk_text'):
                    context_chunks.append({
                        'content': source.chunk_text,
                        'source': f"{source.turbine_info} - {getattr(source, 'published_at', '未知时间')}"
                    })
            
            # 添加上下文数据中的风机信息
            if "turbines" in context_data:
                turbine_context = "相关风机状态：\n"
                for turbine in context_data["turbines"][:3]:
                    turbine_context += f"- {turbine['farm_name']}-{turbine['unit_id']}: {turbine['status']}\n"
                
                context_chunks.append({
                    'content': turbine_context,
                    'source': '当前风机状态'
                })
            
            # 使用LLM服务生成答案
            answer = await self.llm_service.answer_question(original_question, context_chunks)
            
            return answer
            
        except Exception as e:
            logger.error(f"Error generating contextual answer: {e}")
            return answer
    
    def _extract_turbine_filters(self, question: str) -> Dict[str, Any]:
        """从问题中提取风机过滤条件"""
        filters = {}
        
        # 状态过滤
        if "故障" in question or "异常" in question:
            filters["status"] = ["Fault", "Error"]
        elif "正常" in question:
            filters["status"] = "NORMAL"
        elif "维护" in question:
            filters["status"] = ["MAINTENANCE", "WATCH"]
        
        # 风场过滤 (简单的关键词匹配)
        farm_keywords = ["风场", "风电场"]
        for keyword in farm_keywords:
            if keyword in question:
                # 尝试提取风场名称 (这里可以根据实际情况优化)
                words = question.split()
                for i, word in enumerate(words):
                    if keyword in word and i > 0:
                        potential_farm = words[i-1]
                        if len(potential_farm) > 1:
                            filters["farm_name"] = potential_farm
                        break
        
        return filters
    
    async def _enhance_answer_with_aggregation(
        self, 
        rag_result: Dict[str, Any], 
        aggregated_data: Dict[str, Any], 
        question: str
    ) -> Dict[str, Any]:
        """使用聚合数据增强RAG答案"""
        try:
            original_answer = rag_result.get("answer", "")
            
            # 构建聚合数据摘要
            aggregation_summary = aggregated_data.get("summary", "")
            turbine_count = aggregated_data.get("aggregated_data", {}).get("turbine_count", 0)
            
            # 构建增强的prompt
            enhancement_prompt = f"""
基于以下信息，请增强和完善回答：

原始问题：{question}
原始回答：{original_answer}

多风机聚合数据摘要：{aggregation_summary}
涉及风机数量：{turbine_count}台

请结合聚合数据，提供更全面、准确的回答。要求：
1. 保持原始回答的核心内容
2. 融入多风机的整体情况
3. 提供数据支撑的洞察
4. 保持专业性和准确性
"""
            
            # 使用LLM增强答案
            enhanced_answer = await self.llm_service.generate_response(enhancement_prompt)
            
            # 更新结果
            rag_result["answer"] = enhanced_answer
            rag_result["aggregated_data"] = aggregated_data
            rag_result["enhanced_with_aggregation"] = True
            
            return rag_result
            
        except Exception as e:
            logger.error(f"Error enhancing answer with aggregation: {e}")
            # 如果增强失败，返回原始结果但添加聚合数据
            rag_result["aggregated_data"] = aggregated_data
            rag_result["enhancement_error"] = str(e)
            return rag_result