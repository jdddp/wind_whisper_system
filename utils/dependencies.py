from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from models import get_db, User
from models.user import UserRole
from .auth import verify_token

security = HTTPBearer()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """获取当前用户"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    payload = verify_token(credentials.credentials)
    if payload is None:
        raise credentials_exception
    
    username: str = payload.get("sub")
    if username is None:
        raise credentials_exception
    
    user = db.query(User).filter(User.username == username).first()
    if user is None or not user.is_active:
        raise credentials_exception
    
    return user

def get_current_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """获取当前管理员用户"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user

def get_current_expert_or_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """获取当前专家或管理员用户"""
    if current_user.role not in [UserRole.EXPERT, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Expert or admin permissions required"
        )
    return current_user

def get_current_admin_or_expert_for_user_management(current_user: User = Depends(get_current_user)) -> User:
    """获取有用户管理权限的用户（管理员可管理所有用户，专家可管理普通用户）"""
    if current_user.role not in [UserRole.ADMIN, UserRole.EXPERT]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User management permissions required"
        )
    return current_user

def check_user_management_permission(current_user: User, target_role: UserRole) -> bool:
    """检查用户管理权限"""
    if current_user.role == UserRole.ADMIN:
        return True  # 管理员可以管理所有用户
    elif current_user.role == UserRole.EXPERT:
        return target_role == UserRole.READER  # 专家只能管理普通用户
    return False