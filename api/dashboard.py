from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from models import get_db, User, Turbine, ExpertLog
from models.enums import TurbineStatus, LogStatus
from utils.dependencies import get_current_user

router = APIRouter()

@router.get("/stats")
async def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取驾驶舱统计数据"""
    
    # 总风机数
    total_turbines = db.query(Turbine).count()
    
    # 按状态统计风机（基于风机表的状态字段）
    status_stats = {}
    
    # 初始化状态统计
    for status in TurbineStatus:
        status_stats[status.value] = 0
    
    # 直接从风机表统计状态
    turbine_status_counts = db.query(
        Turbine.status,
        func.count(Turbine.turbine_id).label('count')
    ).group_by(Turbine.status).all()
    
    for status, count in turbine_status_counts:
        if status in status_stats:
            status_stats[status] = count
        else:
            # 如果状态不在预定义列表中，归类为Unknown
            status_stats[TurbineStatus.UNKNOWN.value] += count
    
    # 获取不同状态的机组列表
    def get_turbines_by_status(status):
        turbines_query = db.query(Turbine).filter(Turbine.status == status).all()
        turbines = []
        
        for turbine in turbines_query:
            # 获取该风机最新的专家记录（用于显示描述信息）
            latest_log = db.query(ExpertLog).filter(
                ExpertLog.turbine_id == turbine.turbine_id,
                ExpertLog.log_status == LogStatus.PUBLISHED
            ).order_by(ExpertLog.published_at.desc()).first()
            
            turbines.append({
                "turbine_id": str(turbine.turbine_id),
                "farm_name": turbine.farm_name,
                "unit_id": turbine.unit_id,
                "owner_company": turbine.owner_company,
                "status": turbine.status,
                "latest_time": latest_log.published_at.isoformat() if latest_log and latest_log.published_at else turbine.updated_at.isoformat() if turbine.updated_at else None,
                "description": latest_log.ai_summary or (latest_log.description_text[:100] + "..." if latest_log and len(latest_log.description_text) > 100 else latest_log.description_text) if latest_log else "无专家记录描述"
            })
        
        return turbines[:20]  # 最多返回20个机组

    # 获取各状态机组
    alarm_turbines = get_turbines_by_status(TurbineStatus.ALARM.value)
    watch_turbines = get_turbines_by_status(TurbineStatus.WATCH.value)
    maintenance_turbines = get_turbines_by_status(TurbineStatus.MAINTENANCE.value)

    return {
        "status_distribution": status_stats,
        "alarm_turbines": alarm_turbines,
        "watch_turbines": watch_turbines,
        "maintenance_turbines": maintenance_turbines
    }

@router.get("/recent-activities")
async def get_recent_activities(
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取最近活动"""
    
    recent_logs = db.query(ExpertLog).filter(
        ExpertLog.log_status == LogStatus.PUBLISHED
    ).order_by(
        ExpertLog.published_at.desc()
    ).limit(limit).all()
    
    activities = []
    for log in recent_logs:
        turbine = db.query(Turbine).filter(Turbine.turbine_id == log.turbine_id).first()
        if turbine:
            activities.append({
                "log_id": str(log.log_id),
                "title": log.ai_summary or log.description_text[:50] + "..." if len(log.description_text) > 50 else log.description_text,
                "turbine_info": f"{turbine.farm_name} - {turbine.unit_id}",
                "status": log.status_tag.value,
                "created_at": log.published_at.isoformat() if log.published_at else None
            })
    
    return {"activities": activities}