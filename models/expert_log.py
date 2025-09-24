import uuid
import enum
from sqlalchemy import Column, String, Text, DateTime, Enum, ForeignKey, JSON, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .database import Base

class StatusTag(str, enum.Enum):
    NORMAL = "Normal"
    WATCH = "Watch"
    ALARM = "Alarm"
    MAINTENANCE = "Maintenance"
    UNKNOWN = "Unknown"

class LogStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"

class AIReviewStatus(str, enum.Enum):
    UNREVIEWED = "unreviewed"
    APPROVED = "approved"
    REJECTED = "rejected"

class ExpertLog(Base):
    __tablename__ = "expert_logs"

    log_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    turbine_id = Column(UUID(as_uuid=True), ForeignKey("turbines.turbine_id"), nullable=False)
    author_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    
    status_tag = Column(Enum(StatusTag), nullable=False, default=StatusTag.UNKNOWN)
    description_text = Column(Text, nullable=False)
    log_status = Column(Enum(LogStatus), nullable=False, default=LogStatus.DRAFT)
    
    # AI增强字段
    ai_summary = Column(Text)  # 约束式摘要
    ai_tags = Column(JSON)     # 结构化标签
    ai_confidence = Column(Numeric(3, 2))  # 0~1 可信度
    ai_review_status = Column(Enum(AIReviewStatus), default=AIReviewStatus.UNREVIEWED)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    published_at = Column(DateTime(timezone=True))

    # 关系
    turbine = relationship("Turbine", back_populates="expert_logs")
    author = relationship("User")
    attachments = relationship("Attachment", back_populates="expert_log", cascade="all, delete-orphan")
    chunks = relationship("LogChunk", back_populates="expert_log", cascade="all, delete-orphan")