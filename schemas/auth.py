from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, Union, Any
from datetime import datetime
from uuid import UUID
from models.user import UserRole

class Token(BaseModel):
    access_token: str
    token_type: str

class UserLogin(BaseModel):
    username: str
    password: str

class UserCreate(BaseModel):
    username: str
    password: str
    role: UserRole = UserRole.READER

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    user_id: str
    username: str
    role: UserRole
    is_active: bool
    created_at: datetime
    
    @classmethod
    def from_orm_user(cls, user: Any) -> 'UserResponse':
        """从User ORM对象创建UserResponse"""
        return cls(
            user_id=str(user.user_id),
            username=user.username,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at
        )