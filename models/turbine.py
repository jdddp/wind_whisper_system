import uuid
from sqlalchemy import Column, String, Date, DateTime, JSON, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .database import Base

class Turbine(Base):
    __tablename__ = "turbines"

    turbine_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    farm_name = Column(String(100), nullable=False)
    unit_id = Column(String(50), nullable=False)
    model = Column(String(100))
    owner_company = Column(String(100))
    install_date = Column(Date)
    status = Column(String(20), default='Normal')  # Normal, Watch, Alarm, Maintenance, Unknown
    metadata_json = Column(JSON)  # 经纬度、额定功率等扩展信息
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 关系
    expert_logs = relationship("ExpertLog", back_populates="turbine", cascade="all, delete-orphan")
    timeline_events = relationship("TimelineEvent", back_populates="turbine", cascade="all, delete-orphan")
    intelligent_analyses = relationship("IntelligentAnalysis", back_populates="turbine", cascade="all, delete-orphan")

    # 唯一约束
    __table_args__ = (
        UniqueConstraint('farm_name', 'unit_id', name='uq_farm_unit'),
    )