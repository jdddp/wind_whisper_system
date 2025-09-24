import uuid
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from .database import Base

class LogChunk(Base):
    __tablename__ = "log_chunks"

    chunk_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    log_id = Column(UUID(as_uuid=True), ForeignKey("expert_logs.log_id"), nullable=False)
    turbine_id = Column(UUID(as_uuid=True), ForeignKey("turbines.turbine_id"), nullable=False)  # 冗余字段，便于查询
    
    chunk_text = Column(Text, nullable=False)
    embedding = Column(Vector(1024))  # bge-m3 维度
    
    # 冗余字段，便于检索时过滤
    status_tag = Column(String(20))
    published_at = Column(DateTime(timezone=True))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 关系
    expert_log = relationship("ExpertLog", back_populates="chunks")
    turbine = relationship("Turbine")