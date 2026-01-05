from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime
from models.enums import TurbineStatus, LogStatus, AIReviewStatus
from models.user import UserRole

class ExpertLogCreate(BaseModel):
    turbine_id: str
    status_tag: TurbineStatus
    description_text: str

class ExpertLogUpdate(BaseModel):
    status_tag: Optional[TurbineStatus] = None
    description_text: Optional[str] = None
    ai_summary: Optional[str] = None
    ai_tags: Optional[Dict[str, Any]] = None
    ai_review_status: Optional[AIReviewStatus] = None

class AttachmentResponse(BaseModel):
    attachment_id: str
    file_name: str
    file_type: Optional[str]
    file_size: Optional[int]
    uploaded_at: datetime

    class Config:
        from_attributes = True

class TurbineResponse(BaseModel):
    turbine_id: str
    farm_name: str
    unit_id: str
    model: Optional[str]
    owner_company: Optional[str]

    class Config:
        from_attributes = True

class AuthorResponse(BaseModel):
    user_id: str
    username: str
    role: UserRole

    class Config:
        from_attributes = True

class ExpertLogResponse(BaseModel):
    log_id: str
    turbine_id: str
    author_id: str
    status_tag: TurbineStatus
    description_text: str
    log_status: LogStatus
    ai_summary: Optional[str]
    ai_tags: Optional[Dict[str, Any]]
    ai_confidence: Optional[float]
    ai_review_status: AIReviewStatus
    created_at: datetime
    updated_at: Optional[datetime]
    published_at: Optional[datetime]
    attachments: List[AttachmentResponse] = []
    turbine: Optional[TurbineResponse] = None
    author: Optional[AuthorResponse] = None

    class Config:
        from_attributes = True