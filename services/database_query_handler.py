import re
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, text, and_, or_
from datetime import datetime, timedelta
import logging

from models import Turbine, ExpertLog, LogChunk
from models.expert_log import LogStatus

logger = logging.getLogger(__name__)

class DatabaseQueryHandler:
    """数据库查询处理器 - 处理各种统计和查询需求"""
    
    def __init__(self, db: Session):
        self.db = db
        
        # 查询模式定义
        self.query_patterns = {
            # 数量统计类
            'count_turbines': [
                r'有几台风机', r'风机数量', r'多少台风机', r'风机总数',
                r'总共.*风机', r'风机.*多少', r'几个风机', r'风机.*台数'
            ],
            'count_farms': [
                r'有几个风场', r'风场数量', r'多少个风场', r'风场总数'
            ],
            'count_logs': [
                r'有多少.*记录', r'记录数量', r'日志.*多少', r'专家.*记录.*数'
            ],
            
            # 状态查询类
            'turbine_status': [
                r'风机状态', r'风机.*状态', r'状态.*风机',
                r'正常.*风机', r'异常.*风机', r'故障.*风机', r'维护.*风机'
            ],
            
            # 信息列表类
            'list_farms': [
                r'有哪些风场', r'风场名称', r'风场列表', r'所有风场'
            ],
            'list_models': [
                r'有哪些型号', r'风机型号', r'型号.*风机', r'机型.*列表'
            ],
            'list_turbines': [
                r'有哪些风机', r'风机列表', r'所有风机', r'风机.*清单'
            ],
            
            # 时间相关查询
            'recent_logs': [
                r'最近.*记录', r'近期.*日志', r'最新.*记录', r'今天.*记录'
            ],
            'maintenance_history': [
                r'维护.*历史', r'维修.*记录', r'保养.*记录', r'检修.*历史'
            ],
            
            # 特定风机查询
            'specific_turbine': [
                r'(\w+)\s*(\w+)\s*风机', r'(\w+)\s*(\w+)\s*机组',
                r'风机\s*(\w+)\s*(\w+)', r'机组\s*(\w+)\s*(\w+)'
            ]
        }
    
    def classify_query(self, question: str) -> Tuple[str, Dict[str, Any]]:
        """分类查询并提取参数"""
        question_lower = question.lower()
        
        # 提取时间参数
        time_params = self._extract_time_params(question)
        
        # 提取风机/风场参数
        entity_params = self._extract_entity_params(question)
        
        # 匹配查询类型
        for query_type, patterns in self.query_patterns.items():
            for pattern in patterns:
                if re.search(pattern, question_lower):
                    return query_type, {
                        'time_params': time_params,
                        'entity_params': entity_params,
                        'original_question': question
                    }
        
        return 'unknown', {'original_question': question}
    
    def _extract_time_params(self, question: str) -> Dict[str, Any]:
        """提取时间参数"""
        time_params = {}
        
        # 今天、昨天、本周等
        if re.search(r'今天|今日', question):
            time_params['period'] = 'today'
        elif re.search(r'昨天|昨日', question):
            time_params['period'] = 'yesterday'
        elif re.search(r'本周|这周', question):
            time_params['period'] = 'this_week'
        elif re.search(r'上周|上星期', question):
            time_params['period'] = 'last_week'
        elif re.search(r'本月|这个月', question):
            time_params['period'] = 'this_month'
        elif re.search(r'上月|上个月', question):
            time_params['period'] = 'last_month'
        
        # 最近N天
        recent_match = re.search(r'最近(\d+)天', question)
        if recent_match:
            time_params['recent_days'] = int(recent_match.group(1))
        
        return time_params
    
    def _extract_entity_params(self, question: str) -> Dict[str, Any]:
        """提取实体参数（风场、风机等）"""
        entity_params = {}
        
        # 提取风场名称
        farm_match = re.search(r'(\w+)风场', question)
        if farm_match:
            entity_params['farm_name'] = farm_match.group(1)
        
        # 提取风机编号
        turbine_match = re.search(r'(\w+)\s*(\w+)\s*[风机|机组]', question)
        if turbine_match:
            entity_params['turbine_farm'] = turbine_match.group(1)
            entity_params['turbine_unit'] = turbine_match.group(2)
        
        return entity_params
    
    def _get_time_filter(self, time_params: Dict[str, Any]):
        """根据时间参数生成过滤条件"""
        if not time_params:
            return None
        
        now = datetime.now()
        
        if time_params.get('period') == 'today':
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            return ExpertLog.created_at >= start_date
        elif time_params.get('period') == 'yesterday':
            yesterday = now - timedelta(days=1)
            start_date = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            return and_(ExpertLog.created_at >= start_date, ExpertLog.created_at < end_date)
        elif time_params.get('period') == 'this_week':
            days_since_monday = now.weekday()
            start_date = (now - timedelta(days=days_since_monday)).replace(hour=0, minute=0, second=0, microsecond=0)
            return ExpertLog.created_at >= start_date
        elif time_params.get('recent_days'):
            days = time_params['recent_days']
            start_date = now - timedelta(days=days)
            return ExpertLog.created_at >= start_date
        
        return None
    
    async def handle_count_turbines(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理风机数量查询"""
        try:
            entity_params = params.get('entity_params', {})
            
            query = self.db.query(Turbine)
            
            # 如果指定了风场
            if entity_params.get('farm_name'):
                query = query.filter(Turbine.farm_name.ilike(f"%{entity_params['farm_name']}%"))
            
            total_count = query.count()
            
            # 按状态统计
            status_stats = query.with_entities(
                Turbine.status,
                func.count(Turbine.turbine_id).label('count')
            ).group_by(Turbine.status).all()
            
            # 构建回答
            if entity_params.get('farm_name'):
                answer = f"{entity_params['farm_name']}风场共有 {total_count} 台风机。\n\n"
            else:
                answer = f"系统中共有 {total_count} 台风机。\n\n"
            
            if status_stats:
                answer += "按状态分布：\n"
                for status, count in status_stats:
                    answer += f"- {status}: {count}台\n"
            
            return {
                "answer": answer.strip(),
                "data": {
                    "total_count": total_count,
                    "status_distribution": dict(status_stats)
                }
            }
            
        except Exception as e:
            logger.error(f"Error handling turbine count query: {e}")
            return {"answer": f"查询风机数量时出现错误：{str(e)}"}
    
    async def handle_turbine_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理风机状态查询"""
        try:
            entity_params = params.get('entity_params', {})
            
            query = self.db.query(
                Turbine.farm_name,
                Turbine.unit_id,
                Turbine.status,
                Turbine.model,
                Turbine.updated_at
            )
            
            # 如果指定了风场
            if entity_params.get('farm_name'):
                query = query.filter(Turbine.farm_name.ilike(f"%{entity_params['farm_name']}%"))
            
            # 如果指定了具体风机
            if entity_params.get('turbine_farm') and entity_params.get('turbine_unit'):
                query = query.filter(
                    and_(
                        Turbine.farm_name.ilike(f"%{entity_params['turbine_farm']}%"),
                        Turbine.unit_id.ilike(f"%{entity_params['turbine_unit']}%")
                    )
                )
            
            turbines = query.all()
            
            if not turbines:
                return {"answer": "未找到符合条件的风机。"}
            
            # 按状态分组
            status_groups = {}
            for turbine in turbines:
                status = turbine.status
                if status not in status_groups:
                    status_groups[status] = []
                status_groups[status].append(turbine)
            
            # 构建回答
            answer_parts = []
            
            if len(turbines) == 1:
                turbine = turbines[0]
                answer_parts.append(f"{turbine.farm_name} {turbine.unit_id} 当前状态：{turbine.status}")
                if turbine.model:
                    answer_parts.append(f"型号：{turbine.model}")
                if turbine.updated_at:
                    answer_parts.append(f"最后更新：{turbine.updated_at.strftime('%Y-%m-%d %H:%M:%S')}")
            else:
                answer_parts.append(f"共找到 {len(turbines)} 台风机，状态分布如下：\n")
                
                for status, turbine_list in status_groups.items():
                    answer_parts.append(f"\n{status} ({len(turbine_list)}台):")
                    for turbine in turbine_list[:5]:  # 最多显示5台
                        answer_parts.append(f"  - {turbine.farm_name} {turbine.unit_id}")
                    if len(turbine_list) > 5:
                        answer_parts.append(f"  - 还有{len(turbine_list) - 5}台...")
            
            return {
                "answer": "\n".join(answer_parts),
                "data": {
                    "turbine_count": len(turbines),
                    "status_groups": {k: len(v) for k, v in status_groups.items()}
                }
            }
            
        except Exception as e:
            logger.error(f"Error handling turbine status query: {e}")
            return {"answer": f"查询风机状态时出现错误：{str(e)}"}
    
    async def handle_list_farms(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理风场列表查询"""
        try:
            farms = self.db.query(
                Turbine.farm_name,
                func.count(Turbine.turbine_id).label('turbine_count'),
                func.count(func.distinct(Turbine.model)).label('model_count')
            ).group_by(Turbine.farm_name).all()
            
            if not farms:
                return {"answer": "系统中暂无风场数据。"}
            
            answer_parts = [f"系统中共有 {len(farms)} 个风场：\n"]
            
            for i, farm in enumerate(farms, 1):
                answer_parts.append(
                    f"{i}. {farm.farm_name} - {farm.turbine_count}台风机，{farm.model_count}种型号"
                )
            
            return {
                "answer": "\n".join(answer_parts),
                "data": {
                    "farm_count": len(farms),
                    "farms": [dict(farm._asdict()) for farm in farms]
                }
            }
            
        except Exception as e:
            logger.error(f"Error handling farm list query: {e}")
            return {"answer": f"查询风场列表时出现错误：{str(e)}"}
    
    async def handle_recent_logs(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理最近记录查询"""
        try:
            time_params = params.get('time_params', {})
            entity_params = params.get('entity_params', {})
            
            query = self.db.query(
                ExpertLog.log_id,
                ExpertLog.title,
                ExpertLog.created_at,
                ExpertLog.log_status,
                Turbine.farm_name,
                Turbine.unit_id
            ).join(Turbine, ExpertLog.turbine_id == Turbine.turbine_id)
            
            # 应用时间过滤
            time_filter = self._get_time_filter(time_params)
            if time_filter is not None:
                query = query.filter(time_filter)
            else:
                # 默认最近7天
                week_ago = datetime.now() - timedelta(days=7)
                query = query.filter(ExpertLog.created_at >= week_ago)
            
            # 应用实体过滤
            if entity_params.get('farm_name'):
                query = query.filter(Turbine.farm_name.ilike(f"%{entity_params['farm_name']}%"))
            
            logs = query.order_by(ExpertLog.created_at.desc()).limit(10).all()
            
            if not logs:
                return {"answer": "未找到符合条件的记录。"}
            
            answer_parts = [f"找到 {len(logs)} 条最近的记录：\n"]
            
            for i, log in enumerate(logs, 1):
                status_text = "已发布" if log.log_status == LogStatus.PUBLISHED else "草稿"
                answer_parts.append(
                    f"{i}. {log.farm_name} {log.unit_id} - {log.title} "
                    f"({log.created_at.strftime('%m-%d %H:%M')}, {status_text})"
                )
            
            return {
                "answer": "\n".join(answer_parts),
                "data": {
                    "log_count": len(logs),
                    "logs": [dict(log._asdict()) for log in logs]
                }
            }
            
        except Exception as e:
            logger.error(f"Error handling recent logs query: {e}")
            return {"answer": f"查询最近记录时出现错误：{str(e)}"}
    
    async def execute_query(self, question: str) -> Dict[str, Any]:
        """执行查询"""
        query_type, params = self.classify_query(question)
        
        if query_type == 'count_turbines':
            return await self.handle_count_turbines(params)
        elif query_type == 'turbine_status':
            return await self.handle_turbine_status(params)
        elif query_type == 'list_farms':
            return await self.handle_list_farms(params)
        elif query_type == 'recent_logs':
            return await self.handle_recent_logs(params)
        else:
            return {
                "answer": "抱歉，我无法理解这个查询。请尝试询问风机数量、状态、风场信息等。",
                "query_type": query_type
            }