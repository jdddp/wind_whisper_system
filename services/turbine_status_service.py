"""
风机状态服务
负责根据最新时间线事件更新风机状态
"""

from sqlalchemy.orm import Session
from models import Turbine, TimelineEvent
from models.enums import TurbineStatus
import logging

logger = logging.getLogger(__name__)

def update_turbine_status_from_timeline(db: Session, turbine_id: str) -> bool:
    """
    根据最新的时间线事件更新风机状态
    
    Args:
        db: 数据库会话
        turbine_id: 风机ID
        
    Returns:
        bool: 是否成功更新
    """
    try:
        # 获取风机
        turbine = db.query(Turbine).filter(Turbine.turbine_id == turbine_id).first()
        if not turbine:
            logger.warning(f"风机 {turbine_id} 不存在")
            return False
        
        # 获取该风机最新的时间线事件
        latest_event = db.query(TimelineEvent).filter(
            TimelineEvent.turbine_id == turbine_id
        ).order_by(TimelineEvent.event_time.desc()).first()
        
        if not latest_event:
            logger.info(f"风机 {turbine_id} 没有时间线事件，保持当前状态")
            return True
        
        # 将事件严重程度映射到风机状态
        # TurbineStatus 枚举值直接对应状态标签
        new_status = latest_event.event_severity.value
        
        # 更新风机状态
        old_status = turbine.status
        turbine.status = new_status
        
        db.commit()
        
        logger.info(f"风机 {turbine_id} 状态从 {old_status} 更新为 {new_status}，基于时间线事件 {latest_event.event_id}")
        return True
        
    except Exception as e:
        db.rollback()
        logger.error(f"更新风机 {turbine_id} 状态失败: {e}")
        return False

def batch_update_all_turbine_status(db: Session) -> dict:
    """
    批量更新所有风机状态
    
    Args:
        db: 数据库会话
        
    Returns:
        dict: 更新结果统计
    """
    try:
        # 获取所有风机
        turbines = db.query(Turbine).all()
        
        success_count = 0
        failed_count = 0
        updated_turbines = []
        
        for turbine in turbines:
            if update_turbine_status_from_timeline(db, str(turbine.turbine_id)):
                success_count += 1
                updated_turbines.append(str(turbine.turbine_id))
            else:
                failed_count += 1
        
        logger.info(f"批量更新风机状态完成: 成功 {success_count}, 失败 {failed_count}")
        
        return {
            "success_count": success_count,
            "failed_count": failed_count,
            "updated_turbines": updated_turbines,
            "total_turbines": len(turbines)
        }
        
    except Exception as e:
        logger.error(f"批量更新风机状态失败: {e}")
        return {
            "success_count": 0,
            "failed_count": 0,
            "updated_turbines": [],
            "total_turbines": 0,
            "error": str(e)
        }