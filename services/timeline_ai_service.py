import re
import json
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
import logging

from models import ExpertLog, Turbine
from models.timeline import EventType, EventSeverity
from .llm_service import LLMService

logger = logging.getLogger(__name__)

class TimelineAIService:
    """时间线AI分析服务 - 从专家记录中提取时间和事件信息"""
    
    def __init__(self, db: Session):
        self.db = db
        self.llm_service = LLMService()
        
        # 时间模式匹配
        self.time_patterns = [
            # 绝对时间
            r'(\d{4})[年\-/](\d{1,2})[月\-/](\d{1,2})[日号]?\s*(\d{1,2})[时:](\d{1,2})',
            r'(\d{4})[年\-/](\d{1,2})[月\-/](\d{1,2})[日号]?',
            r'(\d{1,2})[月\-/](\d{1,2})[日号]?\s*(\d{1,2})[时:](\d{1,2})',
            r'(\d{1,2})[月\-/](\d{1,2})[日号]?',
            # 相对时间
            r'([昨前]天|今天|明天)',
            r'(\d+)天前',
            r'(\d+)小时前',
            r'上周|本周|下周',
            r'上月|本月|下月',
        ]
        
        # 事件类型关键词映射
        self.event_keywords = {
            EventType.MAINTENANCE: ['维护', '保养', '检修', '维修', '清洁', '润滑', '更换'],
            EventType.FAULT: ['故障', '异常', '报警', '错误', '失效', '损坏', '破损'],
            EventType.INSPECTION: ['检查', '巡检', '检测', '监测', '观察', '查看'],
            EventType.REPAIR: ['修理', '修复', '维修', '更换', '调整', '校准'],
            EventType.UPGRADE: ['升级', '改造', '更新', '优化', '改进'],
            EventType.MONITORING: ['监控', '监测', '数据', '参数', '指标', '状态']
        }
        
        # 严重程度关键词
        self.severity_keywords = {
            EventSeverity.CRITICAL: ['紧急', '严重', '危险', '停机', '故障', '失效'],
            EventSeverity.HIGH: ['重要', '异常', '警告', '超标', '偏差'],
            EventSeverity.MEDIUM: ['注意', '观察', '轻微', '一般'],
            EventSeverity.LOW: ['正常', '良好', '稳定', '常规']
        }

    async def extract_time_from_text(self, text: str, created_at: datetime) -> Optional[datetime]:
        """
        从文本中提取事件发生时间
        
        Args:
            text: 文本内容
            created_at: 记录创建时间（作为参考）
            
        Returns:
            提取的时间，如果无法提取则返回None
        """
        try:
            # 首先尝试使用AI提取时间
            ai_time = await self._ai_extract_time(text, created_at)
            if ai_time:
                return ai_time
            
            # 回退到规则匹配
            return self._rule_based_time_extraction(text, created_at)
            
        except Exception as e:
            logger.error(f"Error extracting time from text: {e}")
            return None

    async def _ai_extract_time(self, text: str, created_at: datetime) -> Optional[datetime]:
        """使用AI提取时间"""
        if not self.llm_service.generator:
            return None
            
        try:
            prompt = f"""请从以下风机监测记录中提取事件发生的具体时间。

记录创建时间：{created_at.strftime('%Y-%m-%d %H:%M:%S')}

记录内容：
{text}

请分析文本中的时间信息，返回JSON格式：
{{
    "event_time": "YYYY-MM-DD HH:MM:SS",
    "confidence": 0.8,
    "time_source": "文本中明确提到的时间"
}}

如果无法确定具体时间，请返回：
{{
    "event_time": null,
    "confidence": 0.0,
    "time_source": "无法确定"
}}

JSON结果："""

            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.llm_service.generator(
                    prompt,
                    max_length=len(prompt.split()) + 100,
                    num_return_sequences=1,
                    temperature=0.1,
                    do_sample=True,
                    pad_token_id=self.llm_service.tokenizer.eos_token_id
                )
            )
            
            generated_text = response[0]['generated_text']
            result_text = generated_text[len(prompt):].strip()
            
            # 解析JSON结果
            result = json.loads(result_text)
            
            if result.get('event_time') and result.get('confidence', 0) > 0.5:
                return datetime.fromisoformat(result['event_time'])
                
        except Exception as e:
            logger.warning(f"AI time extraction failed: {e}")
            
        return None

    def _rule_based_time_extraction(self, text: str, created_at: datetime) -> Optional[datetime]:
        """基于规则的时间提取"""
        try:
            # 尝试匹配各种时间模式
            for pattern in self.time_patterns:
                matches = re.findall(pattern, text)
                if matches:
                    return self._parse_time_match(matches[0], created_at)
            
            # 如果没有找到明确时间，返回创建时间
            return created_at
            
        except Exception as e:
            logger.error(f"Rule-based time extraction failed: {e}")
            return created_at

    def _parse_time_match(self, match: tuple, reference_time: datetime) -> datetime:
        """解析时间匹配结果"""
        try:
            if len(match) == 5:  # 完整日期时间
                year, month, day, hour, minute = match
                return datetime(int(year), int(month), int(day), int(hour), int(minute))
            elif len(match) == 3:  # 年月日
                year, month, day = match
                return datetime(int(year), int(month), int(day))
            elif len(match) == 4:  # 月日时分
                month, day, hour, minute = match
                return datetime(reference_time.year, int(month), int(day), int(hour), int(minute))
            elif len(match) == 2:  # 月日
                month, day = match
                return datetime(reference_time.year, int(month), int(day))
            else:
                # 相对时间处理
                relative_time = match[0] if isinstance(match, tuple) else match
                return self._parse_relative_time(relative_time, reference_time)
                
        except Exception as e:
            logger.error(f"Error parsing time match: {e}")
            return reference_time

    def _parse_relative_time(self, relative_str: str, reference_time: datetime) -> datetime:
        """解析相对时间"""
        if '昨天' in relative_str:
            return reference_time - timedelta(days=1)
        elif '前天' in relative_str:
            return reference_time - timedelta(days=2)
        elif '今天' in relative_str:
            return reference_time
        elif '明天' in relative_str:
            return reference_time + timedelta(days=1)
        elif '天前' in relative_str:
            days = int(re.findall(r'(\d+)天前', relative_str)[0])
            return reference_time - timedelta(days=days)
        elif '小时前' in relative_str:
            hours = int(re.findall(r'(\d+)小时前', relative_str)[0])
            return reference_time - timedelta(hours=hours)
        elif '上周' in relative_str:
            return reference_time - timedelta(weeks=1)
        elif '下周' in relative_str:
            return reference_time + timedelta(weeks=1)
        elif '上月' in relative_str:
            return reference_time - timedelta(days=30)
        elif '下月' in relative_str:
            return reference_time + timedelta(days=30)
        else:
            return reference_time

    def classify_event_type(self, text: str) -> EventType:
        """分类事件类型"""
        text_lower = text.lower()
        
        # 统计各类型关键词出现次数
        type_scores = {}
        for event_type, keywords in self.event_keywords.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            if score > 0:
                type_scores[event_type] = score
        
        # 返回得分最高的类型
        if type_scores:
            return max(type_scores, key=type_scores.get)
        else:
            return EventType.OTHER

    def classify_event_severity(self, text: str) -> EventSeverity:
        """分类事件严重程度"""
        text_lower = text.lower()
        
        # 按严重程度优先级检查
        for severity, keywords in self.severity_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                return severity
        
        return EventSeverity.LOW

    async def analyze_expert_log(self, log: ExpertLog) -> Dict[str, Any]:
        """
        分析专家记录，提取时间线相关信息
        
        Args:
            log: 专家记录对象
            
        Returns:
            分析结果字典
        """
        try:
            # 提取事件时间
            event_time = await self.extract_time_from_text(
                log.description_text, 
                log.created_at
            )
            
            # 分类事件类型和严重程度
            event_type = self.classify_event_type(log.description_text)
            event_severity = self.classify_event_severity(log.description_text)
            
            # 生成AI摘要和关键点
            title, summary, key_points, confidence = await self._generate_event_summary(
                log.description_text, 
                event_type, 
                event_severity
            )
            
            return {
                'event_time': event_time,
                'event_type': event_type,
                'event_severity': event_severity,
                'title': title,
                'summary': summary,
                'key_points': key_points,
                'confidence_score': confidence,
                'source_log_id': str(log.log_id)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing expert log {log.log_id}: {e}")
            return {
                'event_time': log.created_at,
                'event_type': EventType.OTHER,
                'event_severity': EventSeverity.LOW,
                'title': log.title or '未知事件',
                'summary': log.description_text[:200] + '...' if len(log.description_text) > 200 else log.description_text,
                'key_points': [],
                'confidence_score': 0.3,
                'source_log_id': str(log.log_id)
            }

    async def _generate_event_summary(
        self, 
        text: str, 
        event_type: EventType, 
        event_severity: EventSeverity
    ) -> Tuple[str, str, List[str], float]:
        """生成事件摘要和关键点"""
        if not self.llm_service.generator:
            return (
                f"{event_type.value}事件",
                text[:200] + '...' if len(text) > 200 else text,
                [],
                0.3
            )
        
        try:
            prompt = f"""请分析以下风机监测记录，生成结构化的事件信息：

事件类型：{event_type.value}
严重程度：{event_severity.value}

记录内容：
{text}

请生成JSON格式的结果：
{{
    "title": "简洁的事件标题（不超过50字）",
    "summary": "事件摘要（不超过200字）",
    "key_points": ["关键点1", "关键点2", "关键点3"],
    "confidence": 0.8
}}

JSON结果："""

            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.llm_service.generator(
                    prompt,
                    max_length=len(prompt.split()) + 200,
                    num_return_sequences=1,
                    temperature=0.2,
                    do_sample=True,
                    pad_token_id=self.llm_service.tokenizer.eos_token_id
                )
            )
            
            generated_text = response[0]['generated_text']
            result_text = generated_text[len(prompt):].strip()
            
            # 解析JSON结果
            result = json.loads(result_text)
            
            return (
                result.get('title', f"{event_type.value}事件"),
                result.get('summary', text[:200] + '...' if len(text) > 200 else text),
                result.get('key_points', []),
                result.get('confidence', 0.5)
            )
            
        except Exception as e:
            logger.warning(f"AI summary generation failed: {e}")
            return (
                f"{event_type.value}事件",
                text[:200] + '...' if len(text) > 200 else text,
                [],
                0.3
            )

    async def generate_timeline_for_turbine(self, turbine_id: str) -> List[Dict[str, Any]]:
        """
        为指定风机生成时间线事件
        
        Args:
            turbine_id: 风机ID
            
        Returns:
            时间线事件列表
        """
        try:
            # 获取该风机的所有已发布专家记录
            logs = self.db.query(ExpertLog).filter(
                ExpertLog.turbine_id == turbine_id,
                ExpertLog.log_status == 'published'
            ).order_by(ExpertLog.created_at.desc()).all()
            
            if not logs:
                return []
            
            # 分析每条记录
            timeline_events = []
            for log in logs:
                event_data = await self.analyze_expert_log(log)
                timeline_events.append(event_data)
            
            # 按事件时间排序
            timeline_events.sort(key=lambda x: x['event_time'], reverse=True)
            
            return timeline_events
            
        except Exception as e:
            logger.error(f"Error generating timeline for turbine {turbine_id}: {e}")
            return []