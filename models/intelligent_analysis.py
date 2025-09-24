import uuid
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Integer, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .database import Base

class IntelligentAnalysis(Base):
    """智能分析结果表"""
    __tablename__ = "intelligent_analyses"

    analysis_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    turbine_id = Column(UUID(as_uuid=True), ForeignKey("turbines.turbine_id"), nullable=False)
    
    # 分析参数
    analysis_mode = Column(String(20), nullable=False)  # 'llm' 或 'basic'
    days_back = Column(Integer, nullable=False, default=30)  # 回溯天数
    
    # 分析结果
    summary = Column(Text, nullable=False)  # 分析总结
    analysis_data = Column(JSON)  # 原始分析数据（包含统计信息等）
    
    # 元数据
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关系
    turbine = relationship("Turbine", back_populates="intelligent_analyses")

    def to_dict(self):
        """转换为字典格式"""
        return {
            'analysis_id': str(self.analysis_id),
            'turbine_id': str(self.turbine_id),
            'analysis_mode': self.analysis_mode,
            'days_back': self.days_back,
            'summary': self.summary,
            'analysis_data': self.analysis_data,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }