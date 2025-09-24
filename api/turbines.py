from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from models import get_db, User, Turbine
from schemas.turbine import TurbineCreate, TurbineUpdate, TurbineResponse
from utils.dependencies import get_current_user, get_current_admin_user

router = APIRouter()

@router.post("/", response_model=TurbineResponse)
async def create_turbine(
    turbine: TurbineCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """创建风机（仅管理员）"""
    # 检查是否已存在相同的风机
    existing = db.query(Turbine).filter(
        Turbine.farm_name == turbine.farm_name,
        Turbine.unit_id == turbine.unit_id
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Turbine with this farm_name and unit_id already exists"
        )
    
    db_turbine = Turbine(**turbine.dict())
    db.add(db_turbine)
    db.commit()
    db.refresh(db_turbine)
    
    # 手动转换UUID为字符串
    response_data = {
        "turbine_id": str(db_turbine.turbine_id),
        "farm_name": db_turbine.farm_name,
        "unit_id": db_turbine.unit_id,
        "model": db_turbine.model,
        "owner_company": db_turbine.owner_company,
        "install_date": db_turbine.install_date,
        "status": db_turbine.status,
        "metadata_json": db_turbine.metadata_json,
        "created_at": db_turbine.created_at,
        "updated_at": db_turbine.updated_at
    }
    
    return response_data

@router.get("/", response_model=List[TurbineResponse])
async def list_turbines(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取风机列表"""
    turbines = db.query(Turbine).offset(skip).limit(limit).all()
    
    # 手动转换UUID为字符串
    result = []
    for turbine in turbines:
        result.append({
            "turbine_id": str(turbine.turbine_id),
            "farm_name": turbine.farm_name,
            "unit_id": turbine.unit_id,
            "model": turbine.model,
            "owner_company": turbine.owner_company,
            "install_date": turbine.install_date,
            "status": turbine.status,
            "metadata_json": turbine.metadata_json,
            "created_at": turbine.created_at,
            "updated_at": turbine.updated_at
        })
    
    return result

@router.get("/{turbine_id}", response_model=TurbineResponse)
async def get_turbine(
    turbine_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取单个风机详情"""
    turbine = db.query(Turbine).filter(Turbine.turbine_id == turbine_id).first()
    if not turbine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Turbine not found"
        )
    
    # 手动转换UUID为字符串
    return {
        "turbine_id": str(turbine.turbine_id),
        "farm_name": turbine.farm_name,
        "unit_id": turbine.unit_id,
        "model": turbine.model,
        "owner_company": turbine.owner_company,
        "install_date": turbine.install_date,
        "status": turbine.status,
        "metadata_json": turbine.metadata_json,
        "created_at": turbine.created_at,
        "updated_at": turbine.updated_at
    }

@router.put("/{turbine_id}", response_model=TurbineResponse)
async def update_turbine(
    turbine_id: str,
    turbine_update: TurbineUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """更新风机信息（仅管理员）"""
    turbine = db.query(Turbine).filter(Turbine.turbine_id == turbine_id).first()
    if not turbine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Turbine not found"
        )
    
    update_data = turbine_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(turbine, field, value)
    
    db.commit()
    db.refresh(turbine)
    
    # 手动转换UUID为字符串
    response_data = {
        "turbine_id": str(turbine.turbine_id),
        "farm_name": turbine.farm_name,
        "unit_id": turbine.unit_id,
        "model": turbine.model,
        "owner_company": turbine.owner_company,
        "install_date": turbine.install_date,
        "status": turbine.status,
        "metadata_json": turbine.metadata_json,
        "created_at": turbine.created_at,
        "updated_at": turbine.updated_at
    }
    
    return response_data

@router.delete("/{turbine_id}")
async def delete_turbine(
    turbine_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """删除风机（仅管理员）"""
    turbine = db.query(Turbine).filter(Turbine.turbine_id == turbine_id).first()
    if not turbine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Turbine not found"
        )
    
    db.delete(turbine)
    db.commit()
    
    return {"message": "Turbine deleted successfully"}