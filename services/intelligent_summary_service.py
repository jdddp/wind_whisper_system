"""
智能总结服务 - 基于大模型的风机专家记录智能总结
"""

import logging
import re
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_

from models import ExpertLog, Turbine, IntelligentAnalysis
from models.timeline import TimelineEvent, TimelineSourceLog, EventType, EventSeverity
from services.llm_service import LLMService

logger = logging.getLogger(__name__)

class IntelligentSummaryService:
    """智能总结服务 - 为风机生成基于专家记录的智能总结"""
    
    def __init__(self, db: Session):
        self.db = db
        self.llm_service = LLMService()
    
    async def generate_turbine_summary(
        self, 
        turbine_id: str, 
        days_back: int = 30, 
        analysis_mode: str = "llm",
        force_regenerate: bool = False
    ) -> Dict[str, Any]:
        """
        为指定风机生成智能总结
        
        Args:
            turbine_id: 风机ID
            days_back: 回溯天数，默认30天
            analysis_mode: 分析模式，"llm"使用大模型分析，"basic"使用基本统计
            force_regenerate: 是否强制重新生成，默认False
            
        Returns:
            包含智能总结和元数据的字典
        """
        try:
            # 获取风机信息
            turbine = self.db.query(Turbine).filter(Turbine.turbine_id == turbine_id).first()
            if not turbine:
                raise ValueError(f"风机 {turbine_id} 不存在")
            
            # 如果不强制重新生成，先检查是否有现有的分析结果
            if not force_regenerate:
                existing_analysis = await self.get_saved_analysis(turbine_id, analysis_mode)
                if existing_analysis:
                    return {
                        "summary": existing_analysis.summary,
                        "analysis_data": existing_analysis.analysis_data,
                        "analysis_mode": existing_analysis.analysis_mode,
                        "days_back": existing_analysis.days_back,
                        "created_at": existing_analysis.created_at.isoformat(),
                        "is_cached": True
                    }
            
            # 获取指定时间范围内的数据
            cutoff_date = datetime.utcnow() - timedelta(days=days_back)
            
            # 获取专家记录
            expert_logs = self.db.query(ExpertLog).filter(
                and_(
                    ExpertLog.turbine_id == turbine_id,
                    ExpertLog.log_status == 'published',
                    ExpertLog.created_at >= cutoff_date
                )
            ).order_by(desc(ExpertLog.created_at)).all()
            
            # 获取时间线事件
            timeline_events = self.db.query(TimelineEvent).filter(
                and_(
                    TimelineEvent.turbine_id == turbine_id,
                    TimelineEvent.event_time >= cutoff_date
                )
            ).order_by(desc(TimelineEvent.event_time)).all()
            
            # 如果没有任何数据
            if not expert_logs and not timeline_events:
                summary_text = f"风机{turbine.unit_id}在最近{days_back}天内暂无专家记录和时间线事件数据。设备当前状态为{turbine.status}，建议持续关注设备运行状况。"
                analysis_data = {
                    "expert_logs_count": 0,
                    "timeline_events_count": 0,
                    "data_available": False
                }
            else:
                # 根据分析模式选择不同的处理方式
                if analysis_mode == "llm":
                    # 使用大模型生成自然语言总结
                    summary_text = await self._generate_llm_summary(
                        turbine, expert_logs, timeline_events, days_back
                    )
                else:
                    # 使用基本统计方法
                    summary_text = self._generate_basic_statistical_summary(
                        turbine, expert_logs, timeline_events, days_back
                    )
                
                # 构建分析数据
                analysis_data = {
                    "expert_logs_count": len(expert_logs),
                    "timeline_events_count": len(timeline_events),
                    "data_available": True,
                    "cutoff_date": cutoff_date.isoformat()
                }
            
            # 保存分析结果到数据库
            await self.save_analysis_result(
                turbine_id=turbine_id,
                analysis_mode=analysis_mode,
                days_back=days_back,
                summary=summary_text,
                analysis_data=analysis_data
            )
            
            return {
                "summary": summary_text,
                "analysis_data": analysis_data,
                "analysis_mode": analysis_mode,
                "days_back": days_back,
                "created_at": datetime.utcnow().isoformat(),
                "is_cached": False
            }
            
        except Exception as e:
            logger.error(f"Error generating turbine summary for {turbine_id}: {e}")
            # 返回基础错误信息
            return {
                "summary": f"生成智能总结时发生错误，请稍后重试。错误信息：{str(e)}",
                "analysis_data": {"error": str(e)},
                "analysis_mode": analysis_mode,
                "days_back": days_back,
                "created_at": datetime.utcnow().isoformat(),
                "is_cached": False
            }
    
    async def _generate_llm_summary(
        self, 
        turbine: Turbine, 
        expert_logs: List[ExpertLog], 
        timeline_events: List[TimelineEvent], 
        days_back: int
    ) -> str:
        """
        使用大模型生成自然语言总结
        """
        try:
            logger.info(f"开始使用大模型生成智能总结，风机ID: {turbine.turbine_id}")
            
            # 重新初始化LLM服务以确保可用性
            if not hasattr(self, 'llm_service') or self.llm_service is None:
                logger.info("重新初始化LLM服务")
                self.llm_service = LLMService()
            
            if not self.llm_service.is_available:
                logger.warning("LLM服务不可用，使用基本统计方法")
                return self._generate_basic_statistical_summary(turbine, expert_logs, timeline_events, days_back)
            
            # 提取内容中的时间信息
            content_time_info = self._extract_content_time_info(expert_logs, timeline_events)
            
            # 构建自然语言提示词
            prompt = self._build_natural_summary_prompt(
                turbine, expert_logs, timeline_events, days_back, content_time_info
            )
            
            response = await self.llm_service.generate_response(
                prompt=prompt,
                max_tokens=600
            )
            
            if response and len(response.strip()) > 50:
                # 清理和格式化响应
                cleaned_response = self._clean_llm_response(response)
                return cleaned_response
            else:
                logger.warning("LLM响应质量不佳，使用基本统计方法")
                return self._generate_basic_statistical_summary(turbine, expert_logs, timeline_events, days_back)
                
        except Exception as e:
            logger.error(f"Error generating LLM summary: {e}")
            return self._generate_basic_statistical_summary(turbine, expert_logs, timeline_events, days_back)
    
    def _extract_content_time_info(
        self, 
        expert_logs: List[ExpertLog], 
        timeline_events: List[TimelineEvent]
    ) -> Dict[str, List[str]]:
        """
        从内容中提取时间信息，而非记录时间
        """
        time_patterns = [
            r'\d{1,2}月\d{1,2}日',  # 7月15日
            r'\d{4}年\d{1,2}月\d{1,2}日',  # 2024年7月15日
            r'\d{1,2}-\d{1,2}',  # 7-15
            r'\d{4}-\d{1,2}-\d{1,2}',  # 2024-07-15
            r'昨天|今天|前天|上周|本周|上月|本月',  # 相对时间
            r'\d{1,2}:\d{2}',  # 14:30
            r'上午|下午|晚上|凌晨',  # 时间段
        ]
        
        content_times = {
            'expert_logs': [],
            'timeline_events': []
        }
        
        # 从专家记录中提取时间信息
        for log in expert_logs:
            if hasattr(log, 'description_text') and log.description_text:
                for pattern in time_patterns:
                    matches = re.findall(pattern, log.description_text)
                    content_times['expert_logs'].extend(matches)
        
        # 从时间线事件中提取时间信息
        for event in timeline_events:
            if hasattr(event, 'description') and event.description:
                for pattern in time_patterns:
                    matches = re.findall(pattern, event.description)
                    content_times['timeline_events'].extend(matches)
        
        return content_times
    
    def _build_natural_summary_prompt(
        self, 
        turbine: Turbine, 
        expert_logs: List[ExpertLog], 
        timeline_events: List[TimelineEvent], 
        days_back: int,
        content_time_info: Dict[str, List[str]]
    ) -> str:
        """
        构建自然语言总结的提示词
        """
        # 准备专家记录内容
        expert_content = []
        for log in expert_logs[:10]:  # 最多取10条
            if hasattr(log, 'description_text') and log.description_text:
                status_tag = log.status_tag.value if hasattr(log, 'status_tag') and log.status_tag else "未知"
                expert_content.append(f"[{status_tag}] {log.description_text}")
        
        # 准备时间线事件内容
        timeline_content = []
        for event in timeline_events[:10]:  # 最多取10条
            if hasattr(event, 'description') and event.description:
                event_type = event.event_type.value if hasattr(event, 'event_type') and event.event_type else "未知"
                timeline_content.append(f"[{event_type}] {event.description}")
        
        prompt = f"""请为风机{turbine.unit_id}（位于{turbine.location}，型号{turbine.model}）生成一段自然流畅的运维总结。

要求：
1. 用自然语言描述，不要使用格式化的标题和列表
2. 重点关注内容中提到的具体时间信息，而不是记录的创建时间
3. 如果内容中提到具体的技术现象（如"断续声纹"等），必须在总结中体现
4. 语言要专业但易懂，适合运维人员阅读
5. 总结应该是连贯的段落，不超过300字

最近{days_back}天的专家记录：
{chr(10).join(expert_content) if expert_content else "无专家记录"}

最近{days_back}天的时间线事件：
{chr(10).join(timeline_content) if timeline_content else "无时间线事件"}

内容中提到的时间信息：
{', '.join(set(content_time_info['expert_logs'] + content_time_info['timeline_events'])) if any(content_time_info.values()) else "无特定时间信息"}

请生成一段连贯的总结："""
        
        return prompt
    
    def _clean_llm_response(self, response: str) -> str:
        """
        清理和格式化LLM响应
        """
        # 移除多余的格式化标记
        cleaned = response.strip()
        
        # 移除markdown标题标记
        cleaned = re.sub(r'^#+\s*', '', cleaned, flags=re.MULTILINE)
        
        # 移除多余的换行
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        
        # 移除列表标记，转换为自然语言
        cleaned = re.sub(r'^\s*[-*•]\s*', '', cleaned, flags=re.MULTILINE)
        
        return cleaned.strip()
    
    def _generate_basic_statistical_summary(
        self, 
        turbine: Turbine, 
        expert_logs: List[ExpertLog], 
        timeline_events: List[TimelineEvent], 
        days_back: int
    ) -> str:
        """
        生成基本统计总结
        """
        summary_parts = []
        
        # 基本信息
        summary_parts.append(f"风机{turbine.unit_id}位于{turbine.farm_name}，型号为{turbine.model}。")
        
        # 专家记录统计
        if expert_logs:
            # 统计状态标签
            status_counts = {}
            content_keywords = {}
            
            for log in expert_logs:
                if hasattr(log, 'status_tag') and log.status_tag:
                    status = log.status_tag.value
                    status_counts[status] = status_counts.get(status, 0) + 1
                
                if hasattr(log, 'description_text') and log.description_text:
                    # 简单的关键词提取
                    text = log.description_text
                    for keyword in ['声纹', '振动', '温度', '压力', '断续', '异常', '正常']:
                        if keyword in text:
                            content_keywords[keyword] = content_keywords.get(keyword, 0) + 1
            
            summary_parts.append(f"最近{days_back}天共有{len(expert_logs)}条专家记录。")
            
            if status_counts:
                status_desc = "、".join([f"{k}状态{v}次" for k, v in status_counts.items()])
                summary_parts.append(f"记录状态分布：{status_desc}。")
            
            if content_keywords:
                keyword_desc = "、".join([f"{k}相关{v}次" for k, v in content_keywords.items()])
                summary_parts.append(f"主要关注点包括：{keyword_desc}。")
            
            # 最新记录
            latest_log = expert_logs[0]
            if hasattr(latest_log, 'description_text') and latest_log.description_text:
                summary_parts.append(f"最新记录显示：{latest_log.description_text}")
        
        # 时间线事件统计
        if timeline_events:
            event_types = {}
            for event in timeline_events:
                if hasattr(event, 'event_type') and event.event_type:
                    event_type = event.event_type.value
                    event_types[event_type] = event_types.get(event_type, 0) + 1
            
            summary_parts.append(f"同期发生{len(timeline_events)}个时间线事件。")
            
            if event_types:
                event_desc = "、".join([f"{k}类事件{v}个" for k, v in event_types.items()])
                summary_parts.append(f"事件类型分布：{event_desc}。")
        
        if not expert_logs and not timeline_events:
            summary_parts.append(f"最近{days_back}天内暂无专家记录和时间线事件。")
        
        return " ".join(summary_parts)

    async def _generate_comprehensive_summary(
        self, 
        turbine: Turbine, 
        expert_logs: List[ExpertLog], 
        timeline_events: List[TimelineEvent], 
        days_back: int
    ) -> str:
        """
        基于实际数据生成智能总结，严格避免自由发挥
        """
        try:
            logger.info(f"开始生成智能总结，风机ID: {turbine.turbine_id}, 专家记录数: {len(expert_logs)}, 时间线事件数: {len(timeline_events)}")
            
            # 第一步：提取和整理实际数据
            data_summary = self._extract_factual_data(expert_logs, timeline_events, turbine, days_back)
            
            # 第二步：基于实际数据生成总结
            intelligent_summary = await self._generate_data_driven_summary(data_summary)
            
            logger.info(f"智能总结生成成功，长度: {len(intelligent_summary)}")
            return intelligent_summary
            
        except Exception as e:
            logger.error(f"Error generating comprehensive summary: {e}")
            logger.warning("使用基础总结作为降级方案")
            # 返回基础总结
            return self._generate_basic_text_summary(turbine, expert_logs, timeline_events, days_back)
    
    def _extract_factual_data(
        self, 
        expert_logs: List[ExpertLog], 
        timeline_events: List[TimelineEvent], 
        turbine: Turbine, 
        days_back: int
    ) -> Dict[str, Any]:
        """
        提取实际的事实数据，不进行任何推测或分析
        """
        # 统计专家记录的详细信息
        expert_stats = {
            "total_logs": len(expert_logs),
            "log_types": {},
            "recent_logs": [],
            "time_distribution": {},
            "content_keywords": {}
        }
        
        for log in expert_logs:
            # 统计日志类型（使用status_tag作为类型）
            log_type = log.status_tag.value if log.status_tag else "未分类"
            expert_stats["log_types"][log_type] = expert_stats["log_types"].get(log_type, 0) + 1
            
            # 统计时间分布（按日期）
            date_key = log.created_at.strftime("%Y-%m-%d")
            expert_stats["time_distribution"][date_key] = expert_stats["time_distribution"].get(date_key, 0) + 1
            
            # 提取内容关键词（简单统计）
            content = log.description_text.lower() if log.description_text else ""
            keywords = ["故障", "维修", "检查", "更换", "异常", "正常", "停机", "运行", "声纹", "断续", "振动", "温度"]
            for keyword in keywords:
                if keyword in content:
                    expert_stats["content_keywords"][keyword] = expert_stats["content_keywords"].get(keyword, 0) + 1
            
            # 收集最近的日志内容（原文）
            expert_stats["recent_logs"].append({
                "date": log.created_at.strftime("%Y-%m-%d %H:%M"),
                "type": log_type,
                "content": log.description_text[:200] + "..." if log.description_text and len(log.description_text) > 200 else (log.description_text or "无内容")
            })
        
        # 统计时间线事件的详细信息
        timeline_stats = {
            "total_events": len(timeline_events),
            "event_types": {},
            "recent_events": [],
            "time_distribution": {},
            "severity_distribution": {}
        }
        
        for event in timeline_events:
            # 统计事件类型
            event_type = event.event_type or "未分类"
            timeline_stats["event_types"][event_type] = timeline_stats["event_types"].get(event_type, 0) + 1
            
            # 统计时间分布（按日期）
            date_key = event.event_time.strftime("%Y-%m-%d")
            timeline_stats["time_distribution"][date_key] = timeline_stats["time_distribution"].get(date_key, 0) + 1
            
            # 统计严重程度分布
            severity = getattr(event, 'event_severity', None) or "未知"
            timeline_stats["severity_distribution"][str(severity)] = timeline_stats["severity_distribution"].get(str(severity), 0) + 1
            
            # 收集最近的事件内容（原文）- 使用title和summary字段
            event_description = event.title or event.summary or "无描述"
            timeline_stats["recent_events"].append({
                "date": event.event_time.strftime("%Y-%m-%d %H:%M"),
                "type": event_type,
                "severity": str(severity),
                "title": event.title or "无标题",
                "summary": event.summary or "无摘要",
                "description": event_description[:200] + "..." if len(event_description) > 200 else event_description
            })
        
        # 风机基本信息
        turbine_info = {
            "id": str(turbine.turbine_id),
            "name": turbine.unit_id,
            "location": turbine.farm_name,
            "model": turbine.model or "未知型号"
        }
        
        # 数据活跃度统计
        activity_stats = {
            "most_active_date_expert": max(expert_stats["time_distribution"].items(), key=lambda x: x[1]) if expert_stats["time_distribution"] else ("无数据", 0),
            "most_active_date_timeline": max(timeline_stats["time_distribution"].items(), key=lambda x: x[1]) if timeline_stats["time_distribution"] else ("无数据", 0),
            "total_activity_days": len(set(list(expert_stats["time_distribution"].keys()) + list(timeline_stats["time_distribution"].keys())))
        }
        
        return {
             "turbine_info": turbine_info,
             "expert_stats": expert_stats,
             "timeline_stats": timeline_stats,
             "activity_stats": activity_stats,
             "analysis_period": f"最近{days_back}天",
             "summary_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
         }
    
    async def _generate_data_driven_summary(self, data_summary: Dict[str, Any]) -> str:
        """
        基于提取的实际数据生成总结，严格禁止自由发挥
        """
        # 重新初始化LLM服务以确保可用性
        try:
            if not hasattr(self, 'llm_service') or self.llm_service is None:
                logger.info("重新初始化LLM服务")
                self.llm_service = LLMService()
            
            logger.info(f"LLM服务可用性: {self.llm_service.is_available}")
            logger.info(f"LLM generator状态: {self.llm_service.generator is not None}")
            
            if not self.llm_service.is_available:
                logger.warning("LLM服务不可用，使用fallback方法")
                return self._generate_fallback_summary(data_summary)
        except Exception as e:
            logger.error(f"检查LLM服务时出错: {e}")
            return self._generate_fallback_summary(data_summary)
        
        # 构建严格的提示词，只允许基于提供的数据进行总结
        prompt = f"""请基于以下实际数据生成风机运维总结报告。

重要要求：
1. 只能使用下面提供的实际数据
2. 不得添加任何未在数据中明确提及的信息
3. 不得进行推测、猜测或基于常识的分析
4. 如果数据不足，请明确说明"数据不足"
5. 严格按照数据内容进行客观描述
6. **必须引用具体的事实内容**，特别是时间线事件中的具体描述信息
7. 如果时间线事件中包含具体的技术描述（如"断续声纹"等），必须在总结中明确提及

实际数据：
风机信息：
- 风机ID：{data_summary['turbine_info']['id']}
- 风机名称：{data_summary['turbine_info']['name']}
- 位置：{data_summary['turbine_info']['location']}
- 型号：{data_summary['turbine_info']['model']}

专家记录统计（{data_summary['analysis_period']}）：
- 总记录数：{data_summary['expert_stats']['total_logs']}条
- 记录类型分布：{data_summary['expert_stats']['log_types']}
- 时间分布：{data_summary['expert_stats']['time_distribution']}
- 内容关键词统计：{data_summary['expert_stats']['content_keywords']}

最近专家记录内容：
{self._format_recent_logs(data_summary['expert_stats']['recent_logs'])}

时间线事件统计（{data_summary['analysis_period']}）：
- 总事件数：{data_summary['timeline_stats']['total_events']}条
- 事件类型分布：{data_summary['timeline_stats']['event_types']}
- 时间分布：{data_summary['timeline_stats']['time_distribution']}
- 严重程度分布：{data_summary['timeline_stats']['severity_distribution']}

最近时间线事件内容：
{self._format_recent_events(data_summary['timeline_stats']['recent_events'])}

活跃度统计：
- 专家记录最活跃日期：{data_summary['activity_stats']['most_active_date_expert'][0]}（{data_summary['activity_stats']['most_active_date_expert'][1]}条）
- 时间线事件最活跃日期：{data_summary['activity_stats']['most_active_date_timeline'][0]}（{data_summary['activity_stats']['most_active_date_timeline'][1]}条）
- 总活跃天数：{data_summary['activity_stats']['total_activity_days']}天

请生成一份客观的总结报告，只描述上述数据中的实际内容，不要添加任何推测或建议。"""

        try:
            response = await self.llm_service.generate_response(
                prompt=prompt,
                max_tokens=800
            )
            
            if response and len(response.strip()) > 50:
                return f"## 风机运维数据总结\n\n{response.strip()}\n\n---\n*总结时间：{data_summary['summary_time']}*"
            else:
                return self._generate_fallback_summary(data_summary)
                
        except Exception as e:
            logger.error(f"Error generating data-driven summary: {e}")
            return self._generate_fallback_summary(data_summary)
    
    def _format_recent_logs(self, recent_logs: List[Dict]) -> str:
        """格式化最近的专家记录"""
        if not recent_logs:
            return "无专家记录"
        
        formatted = []
        for log in recent_logs[:5]:  # 只显示最近5条
            formatted.append(f"- {log['date']} [{log['type']}] {log['content']}")
        
        return "\n".join(formatted)
    
    def _format_recent_events(self, recent_events: List[Dict]) -> str:
        """格式化最近的时间线事件"""
        if not recent_events:
            return "无时间线事件"
        
        formatted = []
        for event in recent_events[:5]:  # 只显示最近5条
            # 包含title和summary的具体信息
            title = event.get('title', '无标题')
            summary = event.get('summary', '无摘要')
            event_info = f"- {event['date']} [{event['type']}] {title}"
            if summary and summary != '无摘要':
                event_info += f" - {summary}"
            formatted.append(event_info)
        
        return "\n".join(formatted)
    
    def _generate_fallback_summary(self, data_summary: Dict[str, Any]) -> str:
        """当AI不可用时的备用总结"""
        turbine_info = data_summary['turbine_info']
        expert_stats = data_summary['expert_stats']
        timeline_stats = data_summary['timeline_stats']
        activity_stats = data_summary['activity_stats']
        
        summary = f"""## 风机运维数据总结

### 风机基本信息
- 风机名称：{turbine_info['name']}
- 风机位置：{turbine_info['location']}
- 风机型号：{turbine_info['model']}

### 数据统计（{data_summary['analysis_period']}）
- 专家记录：共{expert_stats['total_logs']}条
- 时间线事件：共{timeline_stats['total_events']}条
- 总活跃天数：{activity_stats['total_activity_days']}天

### 专家记录详细统计
#### 类型分布
{self._format_type_distribution(expert_stats['log_types'])}

#### 时间分布
{self._format_type_distribution(expert_stats['time_distribution'])}

#### 内容关键词统计
{self._format_type_distribution(expert_stats['content_keywords'])}

### 时间线事件详细统计
#### 类型分布
{self._format_type_distribution(timeline_stats['event_types'])}

#### 时间分布
{self._format_type_distribution(timeline_stats['time_distribution'])}

#### 严重程度分布
{self._format_type_distribution(timeline_stats['severity_distribution'])}

### 活跃度分析
- 专家记录最活跃日期：{activity_stats['most_active_date_expert'][0]}（{activity_stats['most_active_date_expert'][1]}条）
- 时间线事件最活跃日期：{activity_stats['most_active_date_timeline'][0]}（{activity_stats['most_active_date_timeline'][1]}条）

### 最近专家记录
{self._format_recent_logs(expert_stats['recent_logs'])}

### 最近时间线事件
{self._format_recent_events(timeline_stats['recent_events'])}

---
*总结时间：{data_summary['summary_time']}*
*注：本总结基于实际数据生成，未进行任何推测或分析*"""
        
        return summary
    
    def _format_type_distribution(self, type_dist: Dict[str, int]) -> str:
        """格式化类型分布"""
        if not type_dist:
            return "无数据"
        
        formatted = []
        for type_name, count in type_dist.items():
            formatted.append(f"- {type_name}：{count}条")
        
        return "\n".join(formatted)
    
    # 旧的语义分析方法已被删除，现在使用基于事实数据的方法
    
    async def _analyze_timeline_events_semantically(self, timeline_events: List[TimelineEvent]) -> Dict[str, Any]:
        """语义分析时间线事件，识别事件模式和关联性"""
        if not timeline_events:
            return {"event_patterns": [], "critical_sequences": [], "impact_analysis": [], "summary": "暂无时间线事件"}
        
        # 准备时间线事件文本
        event_texts = []
        for i, event in enumerate(timeline_events[:20]):  # 分析最多20条
            severity_text = event.severity.value if event.severity else "未知"
            event_type_text = event.event_type.value if event.event_type else "未知"
            event_texts.append(f"事件{i+1}: [{event.event_time.strftime('%Y-%m-%d %H:%M')}] [{severity_text}] [{event_type_text}] {event.description}")
        
        prompt = f"""
请对以下风机时间线事件进行深度语义分析，识别事件模式和关联性：

时间线事件：
{chr(10).join(event_texts)}

请分析并返回JSON格式结果：
{{
    "event_patterns": ["事件模式1", "事件模式2"],
    "critical_sequences": ["关键事件序列1", "关键事件序列2"],
    "impact_analysis": ["影响分析1", "影响分析2"],
    "frequency_analysis": "频率分析描述",
    "escalation_trends": "升级趋势分析",
    "root_cause_indicators": ["根因指标1", "根因指标2"],
    "summary": "时间线事件总体分析摘要"
}}

要求：
1. 识别事件发生的模式和规律
2. 分析关键事件序列和因果关系
3. 评估事件对设备运行的影响
4. 识别可能的根本原因指标
5. 分析事件频率和严重程度趋势

JSON结果："""

        try:
            ai_response = await self.llm_service.generate_response(prompt, max_tokens=600)
            content = ai_response.get('content', '{}')
            
            # 尝试解析JSON
            import json
            try:
                result = json.loads(content)
                return result
            except json.JSONDecodeError:
                # 如果JSON解析失败，返回基础分析
                return {
                    "event_patterns": ["数据解析异常"],
                    "critical_sequences": ["无法识别事件序列"],
                    "impact_analysis": ["影响分析受限"],
                    "frequency_analysis": "频率分析失败",
                    "escalation_trends": "趋势分析受限",
                    "root_cause_indicators": ["根因分析失败"],
                    "summary": f"共有{len(timeline_events)}个时间线事件，但语义分析遇到技术问题"
                }
        except Exception as e:
            logger.error(f"Error in semantic analysis of timeline events: {e}")
            return {
                "event_patterns": ["分析异常"],
                "critical_sequences": ["系统分析错误"],
                "impact_analysis": ["影响评估失败"],
                "frequency_analysis": "分析失败",
                "escalation_trends": "趋势分析失败",
                "root_cause_indicators": ["根因分析失败"],
                "summary": f"共有{len(timeline_events)}个时间线事件，但分析过程出现错误"
            }
    
    async def _perform_comprehensive_analysis(
        self, 
        turbine: Turbine, 
        expert_analysis: Dict[str, Any], 
        timeline_analysis: Dict[str, Any], 
        days_back: int
    ) -> Dict[str, Any]:
        """综合分析专家记录和时间线事件，识别关联性和整体趋势"""
        
        prompt = f"""
请基于以下分析结果，进行综合分析和关联性识别：

【风机基本信息】
- 风机编号：{turbine.unit_id}
- 当前状态：{turbine.status}
- 分析时间段：最近{days_back}天

【专家记录分析结果】
- 识别模式：{expert_analysis.get('patterns', [])}
- 关键问题：{expert_analysis.get('key_issues', [])}
- 维护洞察：{expert_analysis.get('maintenance_insights', [])}
- 趋势分析：{expert_analysis.get('trend_analysis', '')}
- 严重程度评估：{expert_analysis.get('severity_assessment', '')}

【时间线事件分析结果】
- 事件模式：{timeline_analysis.get('event_patterns', [])}
- 关键序列：{timeline_analysis.get('critical_sequences', [])}
- 影响分析：{timeline_analysis.get('impact_analysis', [])}
- 频率分析：{timeline_analysis.get('frequency_analysis', '')}
- 升级趋势：{timeline_analysis.get('escalation_trends', '')}

请进行综合分析并返回JSON格式结果：
{{
    "correlation_insights": ["关联洞察1", "关联洞察2"],
    "overall_health_status": "设备整体健康状态评估",
    "risk_assessment": "风险评估描述",
    "predictive_indicators": ["预测指标1", "预测指标2"],
    "intervention_priorities": ["干预优先级1", "干预优先级2"],
    "performance_trends": "性能趋势分析",
    "summary": "综合分析总结"
}}

要求：
1. 识别专家记录和时间线事件之间的关联性
2. 评估设备的整体健康状态
3. 进行风险评估和预测
4. 确定干预和维护的优先级
5. 分析性能趋势

JSON结果："""

        try:
            ai_response = await self.llm_service.generate_response(prompt, max_tokens=600)
            content = ai_response.get('content', '{}')
            
            # 尝试解析JSON
            import json
            try:
                result = json.loads(content)
                return result
            except json.JSONDecodeError:
                # 如果JSON解析失败，返回基础分析
                return {
                    "correlation_insights": ["数据关联分析受限"],
                    "overall_health_status": "健康状态评估需要人工判断",
                    "risk_assessment": "风险评估受限",
                    "predictive_indicators": ["预测分析失败"],
                    "intervention_priorities": ["建议人工制定优先级"],
                    "performance_trends": "性能趋势分析受限",
                    "summary": "综合分析遇到技术问题，建议人工复核"
                }
        except Exception as e:
            logger.error(f"Error in comprehensive analysis: {e}")
            return {
                "correlation_insights": ["分析系统异常"],
                "overall_health_status": "无法评估",
                "risk_assessment": "风险评估失败",
                "predictive_indicators": ["预测功能异常"],
                "intervention_priorities": ["优先级确定失败"],
                "performance_trends": "趋势分析失败",
                "summary": "综合分析过程出现错误"
            }
    
    async def _generate_final_intelligent_summary(
        self, 
        turbine: Turbine, 
        expert_analysis: Dict[str, Any], 
        timeline_analysis: Dict[str, Any], 
        comprehensive_analysis: Dict[str, Any], 
        days_back: int
    ) -> str:
        """生成最终的智能总结报告"""
        
        prompt = f"""
请基于以下深度分析结果，生成一份专业的风机智能总结报告：

【风机基本信息】
- 风机编号：{turbine.unit_id}
- 当前状态：{turbine.status}
- 分析时间段：最近{days_back}天

【专家记录深度分析】
{expert_analysis.get('summary', '')}
关键问题：{expert_analysis.get('key_issues', [])}
维护洞察：{expert_analysis.get('maintenance_insights', [])}

【时间线事件深度分析】
{timeline_analysis.get('summary', '')}
事件模式：{timeline_analysis.get('event_patterns', [])}
关键序列：{timeline_analysis.get('critical_sequences', [])}

【综合分析结果】
整体健康状态：{comprehensive_analysis.get('overall_health_status', '')}
风险评估：{comprehensive_analysis.get('risk_assessment', '')}
关联洞察：{comprehensive_analysis.get('correlation_insights', [])}
干预优先级：{comprehensive_analysis.get('intervention_priorities', [])}

请生成一份400-500字的专业智能总结报告，要求：
1. 开头简要概述设备状态和分析时间段
2. 详细分析发现的关键问题和模式
3. 评估设备健康状态和风险等级
4. 提供具体的维护建议和干预措施
5. 预测可能的发展趋势
6. 语言专业但易懂，适合技术人员和管理人员阅读
7. 结构清晰，逻辑连贯

智能总结报告："""

        try:
            ai_response = await self.llm_service.generate_response(prompt, max_tokens=700)
            summary_text = ai_response.get('content', '生成智能总结失败')
            
            # 如果生成的内容太短，添加基础信息
            if len(summary_text) < 100:
                summary_text = f"风机{turbine.unit_id}在最近{days_back}天内的智能分析报告：\n\n" + summary_text + f"\n\n设备当前状态：{turbine.status}。建议持续关注设备运行状况并定期进行专业维护。"
            
            return summary_text
            
        except Exception as e:
            logger.error(f"Error generating final intelligent summary: {e}")
            return f"风机{turbine.unit_id}在最近{days_back}天内的智能分析遇到技术问题。设备当前状态为{turbine.status}。建议进行人工检查和分析，确保设备正常运行。"
    
    def _generate_basic_text_summary(
        self, 
        turbine: Turbine, 
        expert_logs: List[ExpertLog], 
        timeline_events: List[TimelineEvent], 
        days_back: int
    ) -> str:
        """
        生成基础文字总结（当AI总结失败时的降级方案）
        """
        summary_parts = []
        high_severity_count = 0  # 初始化变量
        
        # 基本信息
        summary_parts.append(f"风机{turbine.unit_id}在最近{days_back}天内")
        
        # 专家记录统计
        if expert_logs:
            summary_parts.append(f"共有{len(expert_logs)}条专家记录")
        
        # 时间线事件统计
        if timeline_events:
            summary_parts.append(f"产生了{len(timeline_events)}个时间线事件")
            
            # 分析严重程度
            high_severity_count = sum(1 for event in timeline_events 
                                    if event.severity and event.severity.value in ['Critical', 'High'])
            if high_severity_count > 0:
                summary_parts.append(f"其中{high_severity_count}个为高严重程度事件")
        
        # 当前状态
        summary_parts.append(f"设备当前状态为{turbine.status}")
        
        # 添加具体的时间线事件信息
        if timeline_events:
            recent_events = timeline_events[:3]  # 取最近3个事件
            event_details = []
            for event in recent_events:
                title = event.title or "未知事件"
                summary = event.summary or ""
                if summary:
                    event_detail = f"{title}({summary})"
                else:
                    event_detail = title
                event_details.append(event_detail)
            
            if event_details:
                summary_parts.append(f"最近的事件包括：{', '.join(event_details)}")
        
        # 建议
        if not expert_logs and not timeline_events:
            summary_parts.append("建议持续关注设备运行状况")
        elif high_severity_count > 0:
            summary_parts.append("建议重点关注高严重程度事件并及时处理")
        else:
            summary_parts.append("建议继续保持当前运维水平")
        
        return "，".join(summary_parts) + "。"
    
    async def _analyze_expert_logs(self, logs: List[ExpertLog], turbine: Turbine) -> Dict[str, Any]:
        """分析专家记录，提取关键信息"""
        
        # 统计分析
        total_logs = len(logs)
        status_distribution = {}
        maintenance_count = 0
        fault_count = 0
        inspection_count = 0
        
        # 关键词统计
        maintenance_keywords = ['维护', '保养', '检修', '维修', '清洁', '润滑', '更换']
        fault_keywords = ['故障', '异常', '报警', '错误', '失效', '损坏', '破损']
        inspection_keywords = ['检查', '巡检', '检测', '监测', '观察', '查看']
        
        for log in logs:
            # 状态分布
            status = log.status_tag.value if log.status_tag else '未知'
            status_distribution[status] = status_distribution.get(status, 0) + 1
            
            # 事件类型分析
            text = log.description_text.lower()
            if any(keyword in text for keyword in maintenance_keywords):
                maintenance_count += 1
            if any(keyword in text for keyword in fault_keywords):
                fault_count += 1
            if any(keyword in text for keyword in inspection_keywords):
                inspection_count += 1
        
        return {
            'total_logs': total_logs,
            'status_distribution': status_distribution,
            'maintenance_count': maintenance_count,
            'fault_count': fault_count,
            'inspection_count': inspection_count,
            'most_common_status': max(status_distribution.items(), key=lambda x: x[1])[0] if status_distribution else '未知'
        }
    
    async def _generate_ai_summary(
        self, 
        logs: List[ExpertLog], 
        turbine: Turbine, 
        analysis: Dict[str, Any],
        days_back: int
    ) -> Dict[str, Any]:
        """使用大模型生成智能总结"""
        
        # 准备专家记录文本
        log_texts = []
        for i, log in enumerate(logs[:10]):  # 限制最多10条记录避免token过多
            log_texts.append(f"{i+1}. [{log.created_at.strftime('%Y-%m-%d %H:%M')}] {log.description_text}")
        
        # 构建提示词 - 要求生成一段连贯的文字描述
        prompt = f"""
请基于以下风机专家记录数据，生成一段连贯的智能分析文字描述：

风机信息：
- 风机编号：{turbine.unit_id}
- 风机ID：{turbine.turbine_id}
- 当前状态：{turbine.status}
- 分析时间段：最近{days_back}天

统计数据：
- 总记录数：{analysis['total_logs']}
- 维护类记录：{analysis['maintenance_count']}
- 故障类记录：{analysis['fault_count']}
- 检查类记录：{analysis['inspection_count']}
- 状态分布：{analysis['status_distribution']}
- 最常见状态：{analysis['most_common_status']}

专家记录详情（最近10条）：
{chr(10).join(log_texts)}

请生成一段200-300字的连贯文字描述，包含以下要素：
1. 风机基本运行状况
2. 主要问题和趋势分析
3. 关键统计数据
4. 专家建议

要求：
- 用一段连贯的文字描述，不要分点列举
- 语言专业、简洁、易懂
- 重点突出关键问题和建议
- 适合在前端界面直接显示
"""

        try:
            # 调用大模型生成总结
            ai_response = await self.llm_service.generate_response(prompt)
            
            # 解析AI响应 - 直接返回大模型生成的连贯文字描述
            summary_text = ai_response.get('content', '生成总结失败')
            
            return {
                'turbine_id': turbine.turbine_id,
                'turbine_name': turbine.unit_id,
                'summary_period': f"最近{days_back}天",
                'total_records': analysis['total_logs'],
                'analysis_text': summary_text,  # 大模型生成的完整分析文字
                'statistics': {
                    'maintenance_count': analysis['maintenance_count'],
                    'fault_count': analysis['fault_count'],
                    'inspection_count': analysis['inspection_count'],
                    'status_distribution': analysis['status_distribution']
                },
                'generated_at': datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Error generating AI summary: {e}")
            # 降级到基础总结
            return self._generate_basic_summary(logs, turbine, analysis, days_back)
    
    def _extract_key_insights(self, summary_text: str, analysis: Dict[str, Any]) -> List[str]:
        """从AI总结中提取关键洞察"""
        insights = []
        
        # 基于统计数据生成洞察
        if analysis['fault_count'] > 0:
            insights.append(f"发现{analysis['fault_count']}次故障相关记录，需要重点关注")
        
        if analysis['maintenance_count'] > analysis['total_logs'] * 0.5:
            insights.append("维护活动频繁，设备保养状况良好")
        
        if analysis['most_common_status'] in ['故障', '异常']:
            insights.append(f"设备状态主要为{analysis['most_common_status']}，建议加强监控")
        
        # 如果AI总结中包含特定关键词，提取相关洞察
        if '趋势' in summary_text:
            insights.append("设备运行趋势需要持续关注")
        
        return insights[:5]  # 最多5个洞察
    
    def _extract_recommendations(self, summary_text: str, analysis: Dict[str, Any]) -> List[str]:
        """从AI总结中提取建议"""
        recommendations = []
        
        # 基于统计数据生成建议
        if analysis['fault_count'] > 2:
            recommendations.append("建议增加故障预防性维护频次")
        
        if analysis['inspection_count'] < analysis['total_logs'] * 0.3:
            recommendations.append("建议增加日常巡检频率")
        
        if analysis['maintenance_count'] == 0:
            recommendations.append("建议制定定期维护计划")
        
        # 通用建议
        recommendations.append("持续监控设备运行参数")
        recommendations.append("及时处理异常状况")
        
        return recommendations[:5]  # 最多5条建议
    
    def _analyze_status_trend(self, logs: List[ExpertLog]) -> str:
        """分析状态趋势"""
        if len(logs) < 2:
            return "数据不足，无法分析趋势"
        
        # 简化的趋势分析
        recent_logs = logs[:5]  # 最近5条
        older_logs = logs[5:10] if len(logs) > 5 else []
        
        recent_fault_count = sum(1 for log in recent_logs if '故障' in log.description_text or '异常' in log.description_text)
        older_fault_count = sum(1 for log in older_logs if '故障' in log.description_text or '异常' in log.description_text) if older_logs else 0
        
        if recent_fault_count > older_fault_count:
            return "故障趋势上升，需要关注"
        elif recent_fault_count < older_fault_count:
            return "故障趋势下降，状况改善"
        else:
            return "状态相对稳定"
    
    def _generate_basic_summary(
        self, 
        logs: List[ExpertLog], 
        turbine: Turbine, 
        analysis: Dict[str, Any],
        days_back: int
    ) -> Dict[str, Any]:
        """生成基础总结（当AI总结失败时的降级方案）"""
        
        summary = f"风机{turbine.unit_id}在最近{days_back}天内共有{analysis['total_logs']}条专家记录。"
        
        if analysis['fault_count'] > 0:
            summary += f"其中故障相关记录{analysis['fault_count']}条，"
        if analysis['maintenance_count'] > 0:
            summary += f"维护相关记录{analysis['maintenance_count']}条，"
        if analysis['inspection_count'] > 0:
            summary += f"检查相关记录{analysis['inspection_count']}条。"
        
        summary += f"设备当前主要状态为{analysis['most_common_status']}。"
        
        return {
            'turbine_id': turbine.turbine_id,
            'turbine_name': turbine.unit_id,
            'summary_period': f"最近{days_back}天",
            'total_records': analysis['total_logs'],
            'analysis_text': summary,  # 基础总结的文字描述
            'statistics': {
                'maintenance_count': analysis['maintenance_count'],
                'fault_count': analysis['fault_count'],
                'inspection_count': analysis['inspection_count'],
                'status_distribution': analysis['status_distribution']
            },
            'generated_at': datetime.utcnow()
        }
    
    async def save_analysis_result(
        self, 
        turbine_id: str, 
        analysis_mode: str, 
        days_back: int, 
        summary: str, 
        analysis_data: Dict[str, Any]
    ) -> None:
        """保存智能分析结果到数据库"""
        try:
            # 删除该风机和分析模式的旧分析结果（实现覆盖机制）
            existing_analysis = self.db.query(IntelligentAnalysis).filter(
                and_(
                    IntelligentAnalysis.turbine_id == turbine_id,
                    IntelligentAnalysis.analysis_mode == analysis_mode
                )
            ).first()
            
            if existing_analysis:
                # 更新现有记录
                existing_analysis.days_back = days_back
                existing_analysis.summary = summary
                existing_analysis.analysis_data = analysis_data
                existing_analysis.updated_at = datetime.utcnow()
            else:
                # 创建新记录
                new_analysis = IntelligentAnalysis(
                    turbine_id=turbine_id,
                    analysis_mode=analysis_mode,
                    days_back=days_back,
                    summary=summary,
                    analysis_data=analysis_data
                )
                self.db.add(new_analysis)
            
            self.db.commit()
            logger.info(f"Saved analysis result for turbine {turbine_id} with mode {analysis_mode}")
            
        except Exception as e:
            logger.error(f"Error saving analysis result: {e}")
            self.db.rollback()
            raise
    
    async def get_saved_analysis(self, turbine_id: str, analysis_mode: str) -> Optional[IntelligentAnalysis]:
        """获取保存的智能分析结果"""
        try:
            analysis = self.db.query(IntelligentAnalysis).filter(
                and_(
                    IntelligentAnalysis.turbine_id == turbine_id,
                    IntelligentAnalysis.analysis_mode == analysis_mode
                )
            ).first()
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error retrieving saved analysis: {e}")
            return None
    
    async def delete_analysis_result(self, turbine_id: str, analysis_mode: str = None) -> bool:
        """删除智能分析结果"""
        try:
            query = self.db.query(IntelligentAnalysis).filter(
                IntelligentAnalysis.turbine_id == turbine_id
            )
            
            if analysis_mode:
                query = query.filter(IntelligentAnalysis.analysis_mode == analysis_mode)
            
            deleted_count = query.delete()
            self.db.commit()
            
            logger.info(f"Deleted {deleted_count} analysis results for turbine {turbine_id}")
            return deleted_count > 0
            
        except Exception as e:
            logger.error(f"Error deleting analysis result: {e}")
            self.db.rollback()
            return False