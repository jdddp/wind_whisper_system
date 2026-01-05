import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from datetime import datetime, timedelta

from models import Turbine, ExpertLog, LogChunk
from models.expert_log import LogStatus
from .query_intent_service import QueryIntentService

logger = logging.getLogger(__name__)

class SmartQueryHandler:
    """智能数据库查询处理器 - 基于语义理解"""
    
    def __init__(self, db: Session, model_path: str = "ai_models/Qwen2-1.5B-Instruct"):
        self.db = db
        self.intent_service = QueryIntentService(model_path)
        
    async def execute_query(self, question: str) -> Dict[str, Any]:
        """执行智能查询"""
        try:
            # 分析查询意图
            intent_analysis = self.intent_service.analyze_query_intent(question)
            
            intent = intent_analysis["intent"]
            entities = intent_analysis["entities"]
            confidence = intent_analysis["confidence"]
            
            logger.info(f"Query intent: {intent}, confidence: {confidence}")
            
            # 根据意图路由到相应的处理方法
            if intent == "count_query":
                return await self._handle_count_query(question, entities, intent_analysis)
            elif intent == "status_query":
                return await self._handle_status_query(question, entities, intent_analysis)
            elif intent == "list_query":
                return await self._handle_list_query(question, entities, intent_analysis)
            elif intent == "specific_info_query":
                return await self._handle_specific_info_query(question, entities, intent_analysis)
            elif intent == "time_related_query":
                return await self._handle_time_related_query(question, entities, intent_analysis)
            elif intent == "technical_query":
                return await self._handle_technical_query(question, entities, intent_analysis)
            else:
                return await self._handle_unknown_query(question, intent_analysis)
                
        except Exception as e:
            logger.error(f"Error executing smart query: {e}")
            return {
                "answer": f"查询处理出现错误：{str(e)}",
                "query_type": "error",
                "confidence": 0.0
            }
    
    async def _handle_count_query(self, question: str, entities: Dict, intent_analysis: Dict) -> Dict[str, Any]:
        """处理数量查询"""
        try:
            # 判断查询的是什么数量
            if any(keyword in question.lower() for keyword in ["风机", "机组"]):
                return await self._count_turbines(entities)
            elif any(keyword in question.lower() for keyword in ["风场", "场站"]):
                return await self._count_farms(entities)
            elif any(keyword in question.lower() for keyword in ["记录", "日志"]):
                return await self._count_logs(entities)
            else:
                # 默认查询风机数量
                return await self._count_turbines(entities)
                
        except Exception as e:
            logger.error(f"Error handling count query: {e}")
            return {"answer": f"统计查询出现错误：{str(e)}"}
    
    async def _handle_status_query(self, question: str, entities: Dict, intent_analysis: Dict) -> Dict[str, Any]:
        """处理状态查询"""
        try:
            query = self.db.query(
                Turbine.farm_name,
                Turbine.unit_id,
                Turbine.status,
                Turbine.model,
                Turbine.updated_at
            )
            
            # 应用过滤条件
            query = self._apply_entity_filters(query, entities)
            
            turbines = query.all()
            
            if not turbines:
                return {"answer": "未找到符合条件的风机。"}
            
            # 根据查询的具体内容生成回答
            return self._format_status_response(question, turbines, entities)
            
        except Exception as e:
            logger.error(f"Error handling status query: {e}")
            return {"answer": f"状态查询出现错误：{str(e)}"}
    
    async def _handle_specific_info_query(self, question: str, entities: Dict, intent_analysis: Dict) -> Dict[str, Any]:
        """处理具体信息查询"""
        try:
            # 这是关键改进：处理"处于XX状态的风机叫什么"这类问题
            query = self.db.query(
                Turbine.farm_name,
                Turbine.unit_id,
                Turbine.status,
                Turbine.model,
                Turbine.turbine_id
            )
            
            # 应用过滤条件
            query = self._apply_entity_filters(query, entities)
            
            turbines = query.all()
            
            if not turbines:
                return {"answer": "未找到符合条件的风机。"}
            
            # 生成具体信息回答
            return self._format_specific_info_response(question, turbines, entities)
            
        except Exception as e:
            logger.error(f"Error handling specific info query: {e}")
            return {"answer": f"信息查询出现错误：{str(e)}"}
    
    async def _handle_list_query(self, question: str, entities: Dict, intent_analysis: Dict) -> Dict[str, Any]:
        """处理列表查询"""
        try:
            if any(keyword in question.lower() for keyword in ["风场", "场站"]):
                return await self._list_farms(entities)
            elif any(keyword in question.lower() for keyword in ["型号", "机型"]):
                return await self._list_models(entities)
            else:
                return await self._list_turbines(entities)
                
        except Exception as e:
            logger.error(f"Error handling list query: {e}")
            return {"answer": f"列表查询出现错误：{str(e)}"}
    
    async def _handle_time_related_query(self, question: str, entities: Dict, intent_analysis: Dict) -> Dict[str, Any]:
        """处理时间相关查询"""
        try:
            return await self._query_recent_logs(entities)
        except Exception as e:
            logger.error(f"Error handling time related query: {e}")
            return {"answer": f"时间查询出现错误：{str(e)}"}
    
    async def _handle_technical_query(self, question: str, entities: Dict, intent_analysis: Dict) -> Dict[str, Any]:
        """处理技术查询 - 增强的知识抽取和语义理解"""
        try:
            # 首先尝试从数据库中获取相关的风机数据作为上下文
            context_data = await self._extract_contextual_data(question, entities)
            
            # 如果找到相关的风机数据，增强查询上下文
            if context_data:
                enhanced_question = self._enhance_question_with_context(question, context_data)
                return {
                    "answer": None,  # 表示需要转发给RAG系统
                    "query_type": "technical_enhanced",
                    "should_forward_to_rag": True,
                    "intent_analysis": intent_analysis,
                    "enhanced_question": enhanced_question,
                    "context_data": context_data
                }
            else:
                # 没有找到相关数据，直接转发
                return {
                    "answer": None,
                    "query_type": "technical",
                    "should_forward_to_rag": True,
                    "intent_analysis": intent_analysis
                }
                
        except Exception as e:
            logger.error(f"Error handling technical query: {e}")
            return {
                "answer": None,
                "query_type": "technical",
                "should_forward_to_rag": True,
                "intent_analysis": intent_analysis
            }
    
    async def _handle_unknown_query(self, question: str, intent_analysis: Dict) -> Dict[str, Any]:
        """处理未知查询"""
        suggestions = self.intent_service.get_query_suggestions("count_query")[:3]
        suggestion_text = "、".join(suggestions)
        
        return {
            "answer": f"抱歉，我无法理解您的问题。您可以尝试询问：{suggestion_text}",
            "query_type": "unknown",
            "confidence": intent_analysis["confidence"],
            "suggestions": suggestions
        }
    
    async def _extract_contextual_data(self, question: str, entities: Dict) -> Dict[str, Any]:
        """从数据库中提取与问题相关的上下文数据"""
        try:
            context_data = {}
            
            # 提取相关风机信息
            turbine_query = self.db.query(Turbine)
            
            # 如果实体中包含状态信息，过滤相关风机
            if "status" in entities:
                status = entities["status"]
                if status == "watch":
                    turbine_query = turbine_query.filter(Turbine.status == "Watch")
                elif status == "fault":
                    turbine_query = turbine_query.filter(Turbine.status.in_(["Fault", "Error"]))
                elif status == "normal":
                    turbine_query = turbine_query.filter(Turbine.status == "Normal")
            
            # 如果实体中包含风场信息，过滤相关风机
            if "farm_name" in entities:
                turbine_query = turbine_query.filter(Turbine.farm_name.ilike(f"%{entities['farm_name']}%"))
            
            # 获取相关风机
            turbines = turbine_query.limit(10).all()
            
            if turbines:
                context_data["turbines"] = []
                for turbine in turbines:
                    context_data["turbines"].append({
                        "turbine_id": turbine.turbine_id,
                        "farm_name": turbine.farm_name,
                        "unit_id": turbine.unit_id,
                        "status": turbine.status,
                        "model": turbine.model
                    })
            
            # 提取相关的专家日志（最近的记录）
            if turbines:
                turbine_ids = [t.turbine_id for t in turbines]
                recent_logs = self.db.query(ExpertLog).filter(
                    ExpertLog.turbine_id.in_(turbine_ids),
                    ExpertLog.log_status == LogStatus.PUBLISHED
                ).order_by(ExpertLog.published_at.desc()).limit(5).all()
                
                if recent_logs:
                    context_data["recent_logs"] = []
                    for log in recent_logs:
                        context_data["recent_logs"].append({
                            "log_id": log.log_id,
                            "title": log.title,
                            "description": log.description_text[:200] + "..." if len(log.description_text) > 200 else log.description_text,
                            "turbine_id": log.turbine_id,
                            "published_at": log.published_at.isoformat() if log.published_at else None
                        })
            
            return context_data
            
        except Exception as e:
            logger.error(f"Error extracting contextual data: {e}")
            return {}
    
    def _enhance_question_with_context(self, question: str, context_data: Dict) -> str:
        """使用上下文数据增强问题"""
        try:
            enhanced_parts = [f"用户问题：{question}"]
            
            # 添加相关风机信息
            if "turbines" in context_data and context_data["turbines"]:
                turbine_info = []
                for turbine in context_data["turbines"][:3]:  # 最多显示3台风机
                    turbine_info.append(f"{turbine['farm_name']}-{turbine['unit_id']}({turbine['status']})")
                enhanced_parts.append(f"相关风机：{', '.join(turbine_info)}")
            
            # 添加最近的日志信息
            if "recent_logs" in context_data and context_data["recent_logs"]:
                enhanced_parts.append("最近相关记录：")
                for log in context_data["recent_logs"][:2]:  # 最多显示2条记录
                    enhanced_parts.append(f"- {log['title']}: {log['description']}")
            
            return "\n".join(enhanced_parts)
            
        except Exception as e:
            logger.error(f"Error enhancing question with context: {e}")
            return question
    
    def _apply_entity_filters(self, query, entities: Dict):
        """应用实体过滤条件"""
        # 状态过滤
        if "status" in entities:
            status_map = {
                "watch": "WATCH",
                "normal": "NORMAL", 
                "fault": "FAULT",
                "maintenance": "MAINTENANCE"
            }
            status = status_map.get(entities["status"], entities["status"])
            query = query.filter(Turbine.status == status)
        
        # 风场过滤
        if "farm_name" in entities:
            query = query.filter(Turbine.farm_name.ilike(f"%{entities['farm_name']}%"))
        
        # 具体风机过滤
        if "turbine_farm" in entities and "turbine_unit" in entities:
            query = query.filter(
                and_(
                    Turbine.farm_name.ilike(f"%{entities['turbine_farm']}%"),
                    Turbine.unit_id.ilike(f"%{entities['turbine_unit']}%")
                )
            )
        
        return query
    
    def _format_status_response(self, question: str, turbines: List, entities: Dict) -> Dict[str, Any]:
        """格式化状态查询响应"""
        if len(turbines) == 1:
            turbine = turbines[0]
            answer = f"{turbine.farm_name} {turbine.unit_id} 当前状态：{turbine.status}"
            if turbine.model:
                answer += f"，型号：{turbine.model}"
        else:
            # 按状态分组
            status_groups = {}
            for turbine in turbines:
                status = turbine.status
                if status not in status_groups:
                    status_groups[status] = []
                status_groups[status].append(turbine)
            
            answer_parts = [f"共找到 {len(turbines)} 台风机，按状态分布："]
            for status, turbine_list in status_groups.items():
                answer_parts.append(f"- {status}: {len(turbine_list)}台")
            
            answer = "\n".join(answer_parts)
        
        return {
            "answer": answer,
            "query_type": "status",
            "data": {
                "turbine_count": len(turbines),
                "turbines": [{"farm": t.farm_name, "unit": t.unit_id, "status": t.status} for t in turbines]
            }
        }
    
    def _format_specific_info_response(self, question: str, turbines: List, entities: Dict) -> Dict[str, Any]:
        """格式化具体信息查询响应"""
        if "叫什么" in question or "名字" in question or "名称" in question:
            # 用户询问名称
            if len(turbines) == 1:
                turbine = turbines[0]
                answer = f"这台风机是 {turbine.farm_name} {turbine.unit_id}"
                if turbine.model:
                    answer += f"，型号：{turbine.model}"
            else:
                answer_parts = [f"符合条件的风机有 {len(turbines)} 台："]
                for i, turbine in enumerate(turbines[:10], 1):  # 最多显示10台
                    answer_parts.append(f"{i}. {turbine.farm_name} {turbine.unit_id}")
                if len(turbines) > 10:
                    answer_parts.append(f"... 还有{len(turbines) - 10}台")
                answer = "\n".join(answer_parts)
        else:
            # 其他具体信息查询
            answer_parts = []
            for turbine in turbines[:5]:  # 最多显示5台详细信息
                info = f"{turbine.farm_name} {turbine.unit_id}："
                details = []
                if turbine.status:
                    details.append(f"状态 {turbine.status}")
                if turbine.model:
                    details.append(f"型号 {turbine.model}")
                info += "、".join(details)
                answer_parts.append(info)
            
            if len(turbines) > 5:
                answer_parts.append(f"... 还有{len(turbines) - 5}台风机")
            
            answer = "\n".join(answer_parts)
        
        return {
            "answer": answer,
            "query_type": "specific_info",
            "data": {
                "turbine_count": len(turbines),
                "turbines": [{"farm": t.farm_name, "unit": t.unit_id, "status": t.status, "model": t.model} for t in turbines]
            }
        }
    
    async def _count_turbines(self, entities: Dict) -> Dict[str, Any]:
        """统计风机数量"""
        query = self.db.query(Turbine)
        query = self._apply_entity_filters(query, entities)
        
        total_count = query.count()
        
        # 按状态统计
        status_query = self.db.query(
            Turbine.status,
            func.count(Turbine.turbine_id).label('count')
        )
        status_query = self._apply_entity_filters(status_query, entities)
        status_stats = status_query.group_by(Turbine.status).all()
        
        answer_parts = [f"系统中共有 {total_count} 台风机。"]
        
        if status_stats and len(status_stats) > 1:
            answer_parts.append("按状态分布：")
            for status, count in status_stats:
                answer_parts.append(f"- {status}: {count}台")
        
        return {
            "answer": "\n".join(answer_parts),
            "query_type": "count",
            "data": {
                "total_count": total_count,
                "status_distribution": {status: count for status, count in status_stats}
            }
        }
    
    async def _count_farms(self, entities: Dict) -> Dict[str, Any]:
        """统计风场数量"""
        farms = self.db.query(func.distinct(Turbine.farm_name)).all()
        farm_count = len(farms)
        
        return {
            "answer": f"系统中共有 {farm_count} 个风场。",
            "query_type": "count",
            "data": {"farm_count": farm_count}
        }
    
    async def _list_turbines(self, entities: Dict) -> Dict[str, Any]:
        """列出风机"""
        query = self.db.query(Turbine.farm_name, Turbine.unit_id, Turbine.status, Turbine.model)
        query = self._apply_entity_filters(query, entities)
        
        turbines = query.limit(20).all()  # 限制显示数量
        
        if not turbines:
            return {"answer": "未找到符合条件的风机。"}
        
        answer_parts = [f"找到 {len(turbines)} 台风机："]
        for i, turbine in enumerate(turbines, 1):
            answer_parts.append(f"{i}. {turbine.farm_name} {turbine.unit_id} ({turbine.status})")
        
        return {
            "answer": "\n".join(answer_parts),
            "query_type": "list",
            "data": {"turbines": [dict(t._asdict()) for t in turbines]}
        }
    
    async def _list_farms(self, entities: Dict) -> Dict[str, Any]:
        """列出风场"""
        farms = self.db.query(
            Turbine.farm_name,
            func.count(Turbine.turbine_id).label('turbine_count')
        ).group_by(Turbine.farm_name).all()
        
        answer_parts = [f"系统中共有 {len(farms)} 个风场："]
        for i, farm in enumerate(farms, 1):
            answer_parts.append(f"{i}. {farm.farm_name} - {farm.turbine_count}台风机")
        
        return {
            "answer": "\n".join(answer_parts),
            "query_type": "list",
            "data": {"farms": [dict(f._asdict()) for f in farms]}
        }
    
    async def _query_recent_logs(self, entities: Dict) -> Dict[str, Any]:
        """查询最近记录"""
        time_period = entities.get("time_period", "recent")
        
        # 根据时间周期设置过滤条件
        now = datetime.now()
        if time_period == "today":
            start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif time_period == "yesterday":
            start_time = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
        elif time_period == "this_week":
            start_time = now - timedelta(days=now.weekday())
        else:  # recent
            start_time = now - timedelta(days=7)
        
        query = self.db.query(
            ExpertLog.title,
            ExpertLog.created_at,
            Turbine.farm_name,
            Turbine.unit_id
        ).join(Turbine, ExpertLog.turbine_id == Turbine.turbine_id)
        
        query = query.filter(ExpertLog.created_at >= start_time)
        logs = query.order_by(ExpertLog.created_at.desc()).limit(10).all()
        
        if not logs:
            return {"answer": f"未找到{time_period}的记录。"}
        
        answer_parts = [f"找到 {len(logs)} 条记录："]
        for i, log in enumerate(logs, 1):
            answer_parts.append(
                f"{i}. {log.farm_name} {log.unit_id} - {log.title} "
                f"({log.created_at.strftime('%m-%d %H:%M')})"
            )
        
        return {
            "answer": "\n".join(answer_parts),
            "query_type": "time_related",
            "data": {"logs": [dict(l._asdict()) for l in logs]}
        }