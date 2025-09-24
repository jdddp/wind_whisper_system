import uuid
import enum
from sqlalchemy import Column, String, Text, DateTime, Enum, ForeignKey, JSON, Numeric, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .database import Base

class EventType(str, enum.Enum):
    """事件类型枚举"""
    NORMAL = "NORMAL"              # 正常事件
    ALARM = "ALARM"                # 告警事件
    WATCH = "WATCH"                # 观察事件
    MAINTENANCE = "MAINTENANCE"     # 维护事件
    FAULT = "FAULT"                # 故障事件
    INSPECTION = "INSPECTION"       # 检查事件
    REPAIR = "REPAIR"              # 修理事件
    UPGRADE = "UPGRADE"            # 升级事件
    MONITORING = "MONITORING"       # 监控事件
    UNKNOWN = "UNKNOWN"            # 未知事件
    OTHER = "OTHER"                # 其他事件

class EventSeverity(str, enum.Enum):
    """事件严重程度"""
    NORMAL = "NORMAL"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class TimelineEvent(Base):
    """风机时间线事件表"""
    __tablename__ = "timeline_events"

    event_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    turbine_id = Column(UUID(as_uuid=True), ForeignKey("turbines.turbine_id"), nullable=False)
    
    # 事件基本信息
    event_time = Column(DateTime(timezone=True), nullable=False)  # AI提取的事件发生时间
    event_type = Column(Enum(EventType), nullable=False)
    event_severity = Column(Enum(EventSeverity), default=EventSeverity.LOW)
    
    # AI生成的内容
    title = Column(String(200), nullable=False)  # AI生成的事件标题
    summary = Column(Text, nullable=False)       # AI生成的事件摘要
    key_points = Column(JSON)                    # 关键要点列表
    
    # 元数据
    confidence_score = Column(Numeric(3, 2))     # AI分析的置信度 0-1
    is_verified = Column(Boolean, default=False) # 是否经过人工验证
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 关系
    turbine = relationship("Turbine", back_populates="timeline_events")
    source_logs = relationship("TimelineSourceLog", back_populates="timeline_event", cascade="all, delete-orphan")

class TimelineSourceLog(Base):
    """时间线事件与源专家记录的关联表"""
    __tablename__ = "timeline_source_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), ForeignKey("timeline_events.event_id"), nullable=False)
    log_id = Column(UUID(as_uuid=True), ForeignKey("expert_logs.log_id"), nullable=False)
    
    # 关联权重（表示该专家记录对此时间线事件的贡献度）
    relevance_score = Column(Numeric(3, 2), default=1.0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 关系
    timeline_event = relationship("TimelineEvent", back_populates="source_logs")
    expert_log = relationship("ExpertLog")