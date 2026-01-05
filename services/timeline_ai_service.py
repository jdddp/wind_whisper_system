import re
import json
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
import logging

from models import ExpertLog, Turbine
from models.enums import TurbineStatus
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
        
        # 事件状态关键词（与专家记录状态标签一致）
        self.severity_keywords = {
            TurbineStatus.ALARM: ['告警', '报警', '紧急', '严重', '危险', '停机', '故障', '失效', '异常'],
            TurbineStatus.WATCH: ['观察', '注意', '监控', '轻微', '偏差', '超标', '警告'],
            TurbineStatus.MAINTENANCE: ['维护', '保养', '检修', '维修', '清洁', '润滑', '更换', '修理'],
            TurbineStatus.NORMAL: ['正常', '良好', '稳定', '常规', '运行', '正常运行'],
            TurbineStatus.UNKNOWN: ['未知', '不明', '待确认']
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



    def classify_event_severity(self, text: str) -> TurbineStatus:
        """分类事件严重程度"""
        text_lower = text.lower()
        
        # 按严重程度优先级检查
        for severity, keywords in self.severity_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                return severity
        
        return TurbineStatus.NORMAL

    async def analyze_expert_log(self, log: ExpertLog) -> Dict[str, Any]:
        """
        分析专家记录，提取时间线相关信息
        
        Args:
            log: 专家记录对象
            
        Returns:
            分析结果字典
        """
        try:
            # 合并专家记录描述和附件内容
            full_content = log.description_text
            if hasattr(log, 'attachments') and log.attachments:
                for attachment in log.attachments:
                    if attachment.extracted_text:
                        full_content += f"\n\n附件内容：{attachment.extracted_text}"
            
            # 提取事件时间（使用完整内容）
            event_time = await self.extract_time_from_text(
                full_content, 
                log.created_at
            )
            
            # 分类事件严重程度（使用完整内容）
            event_severity = self.classify_event_severity(full_content)
            
            # 生成AI摘要、详细内容和关键点（使用完整内容）
            title, summary, detail, key_points, confidence = await self._generate_event_summary(
                full_content, 
                event_severity
            )
            
            return {
                'event_time': event_time,
                'event_severity': event_severity,
                'title': title,
                'summary': summary,
                'detail': detail,
                'key_points': key_points,
                'confidence_score': confidence,
                'source_log_id': str(log.log_id)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing expert log {log.log_id}: {e}")
            return {
                'event_time': log.created_at,
                'event_severity': TurbineStatus.NORMAL,
                'title': log.title or '未知事件',
                'summary': log.description_text,  # 保持完整文本，不截断
                'key_points': [],
                'confidence_score': 0.3,
                'source_log_id': str(log.log_id)
            }

    async def _generate_event_summary(
        self, 
        text: str, 
        event_severity: TurbineStatus
    ) -> Tuple[str, str, str, List[str], float]:
        """生成事件摘要、详细内容和关键点"""
        if not self.llm_service.generator:
            return (
                f"{event_severity.value}状态事件",
                text,  # 保持完整文本，不截断
                text,  # 详细内容使用原始文本
                [],
                0.3
            )
        
        try:
            # 限制输入文本长度，避免超出模型处理能力
            max_input_length = 1500  # 限制输入文本最大长度
            truncated_text = text[:max_input_length]
            
            prompt = f"""
    你是一个专业的技术文档分析助手。请阅读以下风机叶片技术文档，严格按照要求生成 JSON。

    要求：
    - 只输出合法 JSON，不要输出其他文字
    - JSON 必须以 {{ 开始，以 }} 结束
    - 字段说明：
    - title: 简短标题
    - summary: 简要摘要（≤50字，关注叶片状态）
    - detail: 详细说明（100-200字，关注叶片状态）
    - key_points: 要点列表
    - confidence: 置信度 (0~1)

    现在请处理以下文档：
    <doc>
    {truncated_text}
    </doc>
    """

            logger.info(f"发送给AI模型的prompt长度: {len(prompt)} 字符")
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.llm_service.generator(
                    prompt,
                    max_new_tokens=256,  # 减少新生成的token数量
                    num_return_sequences=1,
                    temperature=0.4,  # 降低温度，增加确定性
                    do_sample=True,
                    pad_token_id=self.llm_service.tokenizer.eos_token_id,
                    eos_token_id=self.llm_service.tokenizer.eos_token_id,
                    repetition_penalty=1.1,  # 增加重复惩罚
                    top_p=0.95,  # 添加top_p采样
                    top_k=0,   # 添加top_k采样
                    return_full_text=False
                )
            )
            
            generated_text = response[0]['generated_text']
            logger.info("generated_text")            
            logger.info(generated_text)
            
            match = re.search(r"```json\s*([\s\S]*?)```", generated_text)
            # # 尝试多种方式提取JSON
            if match:
                json_str = match.group(1).strip()
                try:
                    result = json.loads(json_str)
                except json.JSONDecodeError:
                    result = {'title': 'json还原失败，手动抽取', 'summary': '', 'detail':generated_text, 'key_points': [], 'confidence': 0.98}
            else:
                result = {'title': 'json还原失败，手动抽取', 'summary': '', 'detail':generated_text, 'key_points': [], 'confidence': 0.98}
            return (
                result.get('title', f"{event_severity.value}状态事件"),
                result.get('summary', '提取失败'),  # 保持完整文本，不截断
                result.get('detail', generated_text),  # 详细内容
                result.get('key_points', []),
                result.get('confidence', 0.5)
            )
            
        except Exception as e:
            logger.warning(f"AI summary generation failed: {e}")
            # 使用备用方案
            return self._generate_fallback_summary(text, event_severity)
    
    def _extract_json_from_text(self, result_text: str, original_text: str, event_severity: TurbineStatus) -> Optional[Dict[str, Any]]:
        match = re.search(r"\{.*\}", result_text, re.DOTALL)
        if match:
            json_str = match.group(0)
            try:
                return json.loads(json_str)  # 转成 Python dict
            except json.JSONDecodeError:
                # 如果不完整，可以尝试自动补齐
                return {'title': 'json还原失败，手动抽取', 'summary': '', 'detail':original_text, 'key_points': [], 'confidence': 0.98}
        else:
            return {'title': 'json还原失败，手动抽取', 'summary': '', 'detail':original_text, 'key_points': [], 'confidence': 0.98}
    def _generate_fallback_summary(self, text: str, event_severity: TurbineStatus) -> Tuple[str, str, str, List[str], float]:
        """备用摘要生成方法 - 基于规则的简单摘要"""
        try:
            # 生成标题
            title = f"{event_severity.value}状态事件"
            if "叶片" in text:
                title = f"叶片{event_severity.value}事件"
            elif "齿轮箱" in text:
                title = f"齿轮箱{event_severity.value}事件"
            elif "发电机" in text:
                title = f"发电机{event_severity.value}事件"
            elif "变桨" in text:
                title = f"变桨系统{event_severity.value}事件"
            
            # 生成摘要（前100字符）
            summary = text[:100] + "..." if len(text) > 100 else text
            
            # 生成详细信息（前500字符）
            detail = text[:500] + "..." if len(text) > 500 else text
            
            # 提取关键点
            key_points = []
            keywords = ["报警", "故障", "维修", "检查", "异常", "损伤", "修复", "更换"]
            for keyword in keywords:
                if keyword in text:
                    # 找到包含关键词的句子
                    sentences = text.split('。')
                    for sentence in sentences:
                        if keyword in sentence and len(sentence.strip()) > 0:
                            key_points.append(sentence.strip()[:50])
                            break
                if len(key_points) >= 3:
                    break
            
            if not key_points:
                key_points = ["设备状态异常", "需要关注监控", "建议及时处理"]
            
            logger.info(f"使用备用方案生成摘要: {title}")
            
            return (title, summary, detail, key_points, 0.5)
            
        except Exception as e:
            logger.error(f"备用摘要生成也失败: {str(e)}")
            # 最后的兜底方案
            return (
                f"{event_severity.value}状态事件",
                text[:100] + "..." if len(text) > 100 else text,
                text,
                ["设备异常", "需要关注"],
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
            # 获取该风机的所有已发布专家记录（包含附件）
            from sqlalchemy.orm import joinedload
            logs = self.db.query(ExpertLog).options(
                joinedload(ExpertLog.attachments)
            ).filter(
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