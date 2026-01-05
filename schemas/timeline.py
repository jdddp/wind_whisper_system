from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from models.enums import TurbineStatus

class TimelineSourceLogResponse(BaseModel):
    """时间线源记录响应"""
    log_id: str
    relevance_score: float
    title: Optional[str] = None  # 专家记录的标题或摘要
    created_at: datetime

    class Config:
        from_attributes = True

class TimelineEventResponse(BaseModel):
    """时间线事件响应"""
    event_id: str
    turbine_id: str
    event_time: datetime
    event_severity: TurbineStatus
    title: str
    summary: str
    detail: Optional[str] = None
    key_points: Optional[List[str]] = None
    confidence_score: Optional[float] = None
    is_verified: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    source_logs: List[TimelineSourceLogResponse] = []

    class Config:
        from_attributes = True

class TimelineEventCreate(BaseModel):
    """创建时间线事件"""
    turbine_id: str
    event_time: datetime
    event_severity: TurbineStatus
    title: str
    summary: str
    detail: Optional[str] = None
    key_points: Optional[List[str]] = None
    confidence_score: Optional[float] = None
    source_log_ids: List[str] = []

class TimelineEventUpdate(BaseModel):
    """更新时间线事件"""
    event_time: Optional[datetime] = None
    event_severity: Optional[TurbineStatus] = None
    title: Optional[str] = None
    summary: Optional[str] = None
    detail: Optional[str] = None
    key_points: Optional[List[str]] = None
    confidence_score: Optional[float] = None
    is_verified: Optional[bool] = None

class TimelineGenerateRequest(BaseModel):
    """生成时间线请求"""
    turbine_id: str
    force_regenerate: bool = False  # 是否强制重新生成

class TimelineGenerateResponse(BaseModel):
    """生成时间线响应"""
    turbine_id: str
    events_generated: int
    events_updated: int
    total_events: int
    message: str