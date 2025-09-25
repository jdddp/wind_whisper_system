from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional
from models import get_db, User
from models.user import UserRole
from schemas.auth import Token, UserLogin, UserCreate, UserResponse, UserUpdate, UserListResponse
from utils.auth import verify_password, get_password_hash, create_access_token
from utils.dependencies import (
    get_current_user, 
    get_current_admin_user, 
    get_current_admin_or_expert_for_user_management,
    check_user_management_permission
)

router = APIRouter()

@router.post("/login", response_model=Token)
async def login(user_login: UserLogin, db: Session = Depends(get_db)):
    """用户登录"""
    user = db.query(User).filter(User.username == user_login.username).first()
    if not user or not verify_password(user_login.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/register", response_model=UserResponse)
async def register(
    user_create: UserCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_or_expert_for_user_management)
):
    """用户注册（管理员和专家可用）"""
    # 检查权限：专家只能创建普通用户
    if not check_user_management_permission(current_user, user_create.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to create user with this role"
        )
    
    # 检查用户名是否已存在
    if db.query(User).filter(User.username == user_create.username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # 创建新用户
    hashed_password = get_password_hash(user_create.password)
    db_user = User(
        username=user_create.username,
        password_hash=hashed_password,
        role=user_create.role
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return UserResponse.from_orm_user(db_user)

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """获取当前用户信息"""
    return UserResponse.from_orm_user(current_user)

@router.get("/users", response_model=UserListResponse)
async def get_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    role: Optional[UserRole] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_or_expert_for_user_management)
):
    """获取用户列表（管理员和专家可用）"""
    query = db.query(User)
    
    # 专家只能查看普通用户
    if current_user.role == UserRole.EXPERT:
        query = query.filter(User.role == UserRole.READER)
    elif role:
        query = query.filter(User.role == role)
    
    total = query.count()
    users = query.offset((page - 1) * page_size).limit(page_size).all()
    
    return UserListResponse(
        users=[UserResponse.from_orm_user(user) for user in users],
        total=total,
        page=page,
        page_size=page_size
    )

@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_or_expert_for_user_management)
):
    """获取指定用户信息"""
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # 专家只能查看普通用户
    if current_user.role == UserRole.EXPERT and user.role != UserRole.READER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to view this user"
        )
    
    return UserResponse.from_orm_user(user)

@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_or_expert_for_user_management)
):
    """更新用户信息"""
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # 专家只能管理普通用户
    if current_user.role == UserRole.EXPERT and user.role != UserRole.READER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to update this user"
        )
    
    # 检查角色更新权限
    if user_update.role and not check_user_management_permission(current_user, user_update.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to assign this role"
        )
    
    # 更新用户信息
    if user_update.username:
        # 检查用户名是否已存在
        existing_user = db.query(User).filter(
            User.username == user_update.username,
            User.user_id != user_id
        ).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exists"
            )
        user.username = user_update.username
    
    if user_update.password:
        user.password_hash = get_password_hash(user_update.password)
    
    if user_update.role:
        user.role = user_update.role
    
    if user_update.is_active is not None:
        user.is_active = user_update.is_active
    
    db.commit()
    db.refresh(user)
    
    return UserResponse.from_orm_user(user)

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_or_expert_for_user_management)
):
    """删除用户"""
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # 不能删除自己
    if user.user_id == current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete yourself"
        )
    
    # 专家只能删除普通用户
    if current_user.role == UserRole.EXPERT and user.role != UserRole.READER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to delete this user"
        )
    
    db.delete(user)
    db.commit()
    
    return {"message": "User deleted successfully"}