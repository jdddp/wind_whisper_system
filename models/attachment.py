import uuid
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, BigInteger
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .database import Base

class Attachment(Base):
    __tablename__ = "attachments"

    attachment_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    log_id = Column(UUID(as_uuid=True), ForeignKey("expert_logs.log_id"), nullable=False)
    
    file_name = Column(String(255), nullable=False)
    file_type = Column(String(100))  # MIME type
    file_size = Column(BigInteger)   # 文件大小（字节）
    storage_path = Column(Text, nullable=False)  # 本地存储路径
    
    # 文本提取相关
    extracted_text = Column(Text)    # OCR/ASR/解析后的文本
    ai_excerpt = Column(Text)        # 附件级要点摘录
    
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())

    # 关系
    expert_log = relationship("ExpertLog", back_populates="attachments")