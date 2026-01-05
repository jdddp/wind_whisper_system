import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from datetime import datetime, timedelta

from models import Turbine, ExpertLog, LogChunk
from models.expert_log import LogStatus

logger = logging.getLogger(__name__)

class MultiTurbineAggregator:
    """多风机数据聚合服务 - 支持遍历和分析多台风机数据"""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def aggregate_turbine_data(
        self, 
        question: str, 
        turbine_filters: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        聚合多台风机的数据，支持横向对比分析
        
        Args:
            question: 用户问题
            turbine_filters: 风机过滤条件
            
        Returns:
            聚合的风机数据
        """
        try:
            # 获取相关风机
            turbines = await self._get_relevant_turbines(question, turbine_filters)
            
            if not turbines:
                return {
                    "turbines": [],
                    "summary": "未找到符合条件的风机",
                    "aggregated_data": {}
                }
            
            # 聚合各种数据
            aggregated_data = {
                "turbine_count": len(turbines),
                "status_distribution": await self._get_status_distribution(turbines),
                "farm_distribution": await self._get_farm_distribution(turbines),
                "recent_issues": await self._get_recent_issues(turbines),
                "maintenance_summary": await self._get_maintenance_summary(turbines),
                "performance_insights": await self._get_performance_insights(turbines)
            }
            
            # 生成聚合摘要
            summary = await self._generate_aggregation_summary(question, turbines, aggregated_data)
            
            return {
                "turbines": [self._format_turbine_info(t) for t in turbines],
                "summary": summary,
                "aggregated_data": aggregated_data
            }
            
        except Exception as e:
            logger.error(f"Error aggregating turbine data: {e}")
            return {
                "turbines": [],
                "summary": f"数据聚合出现错误：{str(e)}",
                "aggregated_data": {}
            }
    
    async def _get_relevant_turbines(
        self, 
        question: str, 
        filters: Dict[str, Any] = None
    ) -> List[Turbine]:
        """获取相关的风机列表"""
        try:
            query = self.db.query(Turbine)
            
            # 应用过滤条件
            if filters:
                if "status" in filters:
                    if isinstance(filters["status"], list):
                        query = query.filter(Turbine.status.in_(filters["status"]))
                    else:
                        query = query.filter(Turbine.status == filters["status"])
                
                if "farm_name" in filters:
                    query = query.filter(Turbine.farm_name.ilike(f"%{filters['farm_name']}%"))
                
                if "model" in filters:
                    query = query.filter(Turbine.model.ilike(f"%{filters['model']}%"))
            
            # 基于问题内容进行智能过滤
            if "故障" in question or "异常" in question:
                query = query.filter(Turbine.status.in_(["Fault", "Error", "Watch"]))
            elif "正常" in question:
                query = query.filter(Turbine.status == "NORMAL")
            elif "维护" in question:
                query = query.filter(Turbine.status.in_(["MAINTENANCE", "WATCH"]))
            
            # 限制结果数量，避免处理过多数据
            turbines = query.limit(50).all()
            
            return turbines
            
        except Exception as e:
            logger.error(f"Error getting relevant turbines: {e}")
            return []
    
    async def _get_status_distribution(self, turbines: List[Turbine]) -> Dict[str, int]:
        """获取状态分布统计"""
        status_count = {}
        for turbine in turbines:
            status = turbine.status
            status_count[status] = status_count.get(status, 0) + 1
        return status_count
    
    async def _get_farm_distribution(self, turbines: List[Turbine]) -> Dict[str, int]:
        """获取风场分布统计"""
        farm_count = {}
        for turbine in turbines:
            farm = turbine.farm_name
            farm_count[farm] = farm_count.get(farm, 0) + 1
        return farm_count
    
    async def _get_recent_issues(self, turbines: List[Turbine]) -> List[Dict[str, Any]]:
        """获取最近的问题记录"""
        try:
            turbine_ids = [t.turbine_id for t in turbines]
            
            # 获取最近7天的问题记录
            recent_date = datetime.now() - timedelta(days=7)
            
            recent_logs = self.db.query(ExpertLog).filter(
                ExpertLog.turbine_id.in_(turbine_ids),
                ExpertLog.log_status == LogStatus.PUBLISHED,
                ExpertLog.published_at >= recent_date
            ).order_by(ExpertLog.published_at.desc()).limit(10).all()
            
            issues = []
            for log in recent_logs:
                # 找到对应的风机信息
                turbine = next((t for t in turbines if t.turbine_id == log.turbine_id), None)
                if turbine:
                    issues.append({
                        "log_id": log.log_id,
                        "title": log.title,
                        "turbine_info": f"{turbine.farm_name}-{turbine.unit_id}",
                        "published_at": log.published_at.isoformat() if log.published_at else None,
                        "description": log.description_text[:100] + "..." if len(log.description_text) > 100 else log.description_text
                    })
            
            return issues
            
        except Exception as e:
            logger.error(f"Error getting recent issues: {e}")
            return []
    
    async def _get_maintenance_summary(self, turbines: List[Turbine]) -> Dict[str, Any]:
        """获取维护摘要"""
        try:
            turbine_ids = [t.turbine_id for t in turbines]
            
            # 统计维护相关的记录
            maintenance_logs = self.db.query(ExpertLog).filter(
                ExpertLog.turbine_id.in_(turbine_ids),
                ExpertLog.log_status == LogStatus.PUBLISHED,
                or_(
                    ExpertLog.title.ilike("%维护%"),
                    ExpertLog.title.ilike("%检修%"),
                    ExpertLog.title.ilike("%保养%"),
                    ExpertLog.description_text.ilike("%维护%")
                )
            ).count()
            
            # 统计需要维护的风机
            maintenance_needed = len([t for t in turbines if t.status in ["MAINTENANCE", "WATCH"]])
            
            return {
                "total_maintenance_logs": maintenance_logs,
                "turbines_needing_maintenance": maintenance_needed,
                "maintenance_rate": round(maintenance_needed / len(turbines) * 100, 2) if turbines else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting maintenance summary: {e}")
            return {}
    
    async def _get_performance_insights(self, turbines: List[Turbine]) -> Dict[str, Any]:
        """获取性能洞察"""
        try:
            # 统计各种状态的风机
            normal_count = len([t for t in turbines if t.status == "Normal"])
            fault_count = len([t for t in turbines if t.status in ["Fault", "Error"]])
            watch_count = len([t for t in turbines if t.status == "Watch"])
            
            total_count = len(turbines)
            
            insights = {
                "health_score": round((normal_count / total_count * 100), 2) if total_count > 0 else 0,
                "fault_rate": round((fault_count / total_count * 100), 2) if total_count > 0 else 0,
                "watch_rate": round((watch_count / total_count * 100), 2) if total_count > 0 else 0,
                "total_turbines": total_count
            }
            
            # 添加性能评级
            health_score = insights["health_score"]
            if health_score >= 90:
                insights["performance_grade"] = "优秀"
            elif health_score >= 80:
                insights["performance_grade"] = "良好"
            elif health_score >= 70:
                insights["performance_grade"] = "一般"
            else:
                insights["performance_grade"] = "需要关注"
            
            return insights
            
        except Exception as e:
            logger.error(f"Error getting performance insights: {e}")
            return {}
    
    async def _generate_aggregation_summary(
        self, 
        question: str, 
        turbines: List[Turbine], 
        aggregated_data: Dict[str, Any]
    ) -> str:
        """生成聚合数据摘要"""
        try:
            summary_parts = []
            
            # 基本统计
            turbine_count = len(turbines)
            summary_parts.append(f"共分析了{turbine_count}台风机")
            
            # 状态分布
            status_dist = aggregated_data.get("status_distribution", {})
            if status_dist:
                status_summary = []
                for status, count in status_dist.items():
                    status_summary.append(f"{status}状态{count}台")
                summary_parts.append("状态分布：" + "、".join(status_summary))
            
            # 风场分布
            farm_dist = aggregated_data.get("farm_distribution", {})
            if farm_dist:
                farm_count = len(farm_dist)
                summary_parts.append(f"涉及{farm_count}个风场")
            
            # 性能洞察
            performance = aggregated_data.get("performance_insights", {})
            if performance:
                health_score = performance.get("health_score", 0)
                grade = performance.get("performance_grade", "未知")
                summary_parts.append(f"整体健康度{health_score}%，评级：{grade}")
            
            # 最近问题
            recent_issues = aggregated_data.get("recent_issues", [])
            if recent_issues:
                summary_parts.append(f"最近7天内有{len(recent_issues)}条问题记录")
            
            return "；".join(summary_parts) + "。"
            
        except Exception as e:
            logger.error(f"Error generating aggregation summary: {e}")
            return f"生成摘要时出现错误：{str(e)}"
    
    def _format_turbine_info(self, turbine: Turbine) -> Dict[str, Any]:
        """格式化风机信息"""
        return {
            "turbine_id": turbine.turbine_id,
            "farm_name": turbine.farm_name,
            "unit_id": turbine.unit_id,
            "status": turbine.status,
            "model": turbine.model,
            "updated_at": turbine.updated_at.isoformat() if turbine.updated_at else None
        }