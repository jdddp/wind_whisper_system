"""
权限控制工具模块
"""
from functools import wraps
from typing import List, Optional, Callable, Any
from fastapi import HTTPException, status, Depends
from models.user import User, UserRole
from utils.dependencies import get_current_user


class PermissionChecker:
    """权限检查器"""
    
    @staticmethod
    def require_roles(allowed_roles: List[UserRole]):
        """
        装饰器：要求用户具有指定角色之一
        
        Args:
            allowed_roles: 允许的角色列表
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # 从依赖注入中获取当前用户
                current_user = None
                for key, value in kwargs.items():
                    if isinstance(value, User):
                        current_user = value
                        break
                
                if not current_user:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Authentication required"
                    )
                
                if current_user.role not in allowed_roles:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Insufficient permissions"
                    )
                
                return await func(*args, **kwargs)
            return wrapper
        return decorator
    
    @staticmethod
    def require_admin():
        """装饰器：要求管理员权限"""
        return PermissionChecker.require_roles([UserRole.ADMIN])
    
    @staticmethod
    def require_admin_or_expert():
        """装饰器：要求管理员或专家权限"""
        return PermissionChecker.require_roles([UserRole.ADMIN, UserRole.EXPERT])
    
    @staticmethod
    def can_manage_user(manager: User, target_role: UserRole) -> bool:
        """
        检查用户是否可以管理指定角色的用户
        
        Args:
            manager: 管理者用户
            target_role: 目标用户角色
            
        Returns:
            bool: 是否有权限管理
        """
        if manager.role == UserRole.ADMIN:
            return True
        elif manager.role == UserRole.EXPERT:
            return target_role == UserRole.READER
        return False
    
    @staticmethod
    def can_create_content(user: User) -> bool:
        """
        检查用户是否可以创建内容（风机、专家记录、时间线事件等）
        
        Args:
            user: 用户对象
            
        Returns:
            bool: 是否有权限创建内容
        """
        return user.role in [UserRole.ADMIN, UserRole.EXPERT]
    
    @staticmethod
    def can_delete_content(user: User, content_type: str = None) -> bool:
        """
        检查用户是否可以删除内容
        
        Args:
            user: 用户对象
            content_type: 内容类型（可选）
            
        Returns:
            bool: 是否有权限删除内容
        """
        # 只有管理员可以删除内容
        return user.role == UserRole.ADMIN
    
    @staticmethod
    def can_access_management_features(user: User) -> bool:
        """
        检查用户是否可以访问管理功能
        
        Args:
            user: 用户对象
            
        Returns:
            bool: 是否有权限访问管理功能
        """
        return user.role in [UserRole.ADMIN, UserRole.EXPERT]


def require_permission(permission_check: Callable[[User], bool]):
    """
    通用权限检查装饰器
    
    Args:
        permission_check: 权限检查函数，接收User对象，返回bool
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 从依赖注入中获取当前用户
            current_user = None
            for key, value in kwargs.items():
                if isinstance(value, User):
                    current_user = value
                    break
            
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            if not permission_check(current_user):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


# 常用权限检查函数
def require_content_creation_permission():
    """要求内容创建权限"""
    return require_permission(PermissionChecker.can_create_content)


def require_content_deletion_permission():
    """要求内容删除权限"""
    return require_permission(PermissionChecker.can_delete_content)


def require_management_access():
    """要求管理功能访问权限"""
    return require_permission(PermissionChecker.can_access_management_features)