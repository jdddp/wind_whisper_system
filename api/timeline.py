from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid
import logging

from models import get_db, TimelineEvent, TimelineSourceLog, ExpertLog, Turbine, Attachment
from models.enums import TurbineStatus
from schemas.timeline import (
    TimelineEventResponse, 
    TimelineEventCreate, 
    TimelineEventUpdate,
    TimelineGenerateRequest,
    TimelineGenerateResponse
)
from services.timeline_ai_service import TimelineAIService
from services.intelligent_summary_service import IntelligentSummaryService
from services.turbine_status_service import update_turbine_status_from_timeline, batch_update_all_turbine_status
from utils.dependencies import get_current_user, get_current_admin_user, get_current_admin_or_expert_for_user_management

logger = logging.getLogger(__name__)
router = APIRouter(tags=["timeline"])

@router.get("/", response_model=List[TimelineEventResponse])
async def get_all_timeline_events(
    limit: Optional[int] = 100,
    offset: Optional[int] = 0,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    获取所有时间线事件
    """
    try:
        events = db.query(TimelineEvent).order_by(
            TimelineEvent.event_time.desc()
        ).offset(offset).limit(limit).all()
        
        result = []
        for event in events:
            # 获取源记录信息
            source_logs = []
            for source in event.source_logs:
                expert_log = db.query(ExpertLog).filter(ExpertLog.log_id == source.log_id).first()
                if expert_log:
                    # 获取该专家记录的附件信息
                    attachments = db.query(Attachment).filter(Attachment.log_id == source.log_id).all()
                    attachment_list = [
                        {
                            "attachment_id": str(attachment.attachment_id),
                            "file_name": attachment.file_name,
                            "file_type": attachment.file_type,
                            "file_size": attachment.file_size,
                            "uploaded_at": attachment.uploaded_at.isoformat() if attachment.uploaded_at else None
                        }
                        for attachment in attachments
                    ]
                    
                    source_logs.append({
                        "log_id": str(source.log_id),
                        "relevance_score": float(source.relevance_score),
                        "title": expert_log.description_text,
                        "created_at": source.created_at,
                        "attachments": attachment_list
                    })
            
            result.append(TimelineEventResponse(
                event_id=str(event.event_id),
                turbine_id=str(event.turbine_id),
                event_time=event.event_time,
                event_severity=event.event_severity,
                title=event.title,
                summary=event.summary,
                detail=event.detail,
                key_points=event.key_points or [],
                confidence_score=float(event.confidence_score) if event.confidence_score else None,
                is_verified=event.is_verified,
                created_at=event.created_at,
                updated_at=event.updated_at,
                source_logs=source_logs
            ))
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting timeline events: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取时间线事件失败: {str(e)}"
        )

@router.post("/generate", response_model=TimelineGenerateResponse)
async def generate_timeline(
    request: TimelineGenerateRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_or_expert_for_user_management)
):
    """
    为指定风机生成AI时间线（管理员和专家可用）
    """
    try:
        # 验证风机是否存在
        turbine = db.query(Turbine).filter(Turbine.turbine_id == request.turbine_id).first()
        if not turbine:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="风机不存在"
            )
        
        # 初始化AI服务
        ai_service = TimelineAIService(db)
        
        # 如果强制重新生成，删除现有时间线事件
        if request.force_regenerate:
            db.query(TimelineEvent).filter(
                TimelineEvent.turbine_id == request.turbine_id
            ).delete()
            db.commit()
        
        # 生成时间线事件
        timeline_data = await ai_service.generate_timeline_for_turbine(request.turbine_id)
        
        events_generated = 0
        events_updated = 0
        
        for event_data in timeline_data:
            # 检查是否已存在相似的事件
            existing_event = db.query(TimelineEvent).filter(
                TimelineEvent.turbine_id == request.turbine_id,
                TimelineEvent.event_time == event_data['event_time'],
                TimelineEvent.event_severity == event_data['event_severity']
            ).first()
            
            if existing_event and not request.force_regenerate:
                # 更新现有事件
                existing_event.title = event_data['title']
                existing_event.summary = event_data['summary']
                existing_event.key_points = event_data['key_points']
                existing_event.confidence_score = event_data['confidence_score']
                existing_event.event_severity = event_data['event_severity']
                events_updated += 1
            else:
                # 创建新事件
                new_event = TimelineEvent(
                    turbine_id=request.turbine_id,
                    event_time=event_data['event_time'],
                    event_severity=event_data['event_severity'],
                    title=event_data['title'],
                    summary=event_data['summary'],
                    key_points=event_data['key_points'],
                    confidence_score=event_data['confidence_score']
                )
                db.add(new_event)
                db.flush()  # 获取event_id
                
                # 创建源记录关联
                source_log = TimelineSourceLog(
                    event_id=new_event.event_id,
                    log_id=event_data['source_log_id'],
                    relevance_score=1.0
                )
                db.add(source_log)
                events_generated += 1
        
        db.commit()
        
        # 获取总事件数
        total_events = db.query(TimelineEvent).filter(
            TimelineEvent.turbine_id == request.turbine_id
        ).count()
        
        return TimelineGenerateResponse(
            turbine_id=request.turbine_id,
            events_generated=events_generated,
            events_updated=events_updated,
            total_events=total_events,
            message=f"成功生成 {events_generated} 个新事件，更新 {events_updated} 个事件"
        )
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error generating timeline: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"生成时间线失败: {str(e)}"
        )

@router.get("/turbine/{turbine_id}")
async def get_turbine_timeline(
    turbine_id: str,
    limit: Optional[int] = 50,
    offset: Optional[int] = 0,
    include_drafts: Optional[bool] = True,  # 默认包含草稿，便于开发和测试
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    获取指定风机的时间线事件（从timeline_events表获取）
    """
    try:
        # 将字符串转换为UUID进行查询
        try:
            turbine_uuid = uuid.UUID(turbine_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="无效的风机ID格式"
            )
        
        # 验证风机是否存在
        turbine = db.query(Turbine).filter(Turbine.turbine_id == turbine_uuid).first()
        if not turbine:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="风机不存在"
            )
        
        # 从timeline_events表查询时间线事件
        events = db.query(TimelineEvent).filter(
            TimelineEvent.turbine_id == turbine_uuid
        ).order_by(TimelineEvent.event_time.desc()).offset(offset).limit(limit).all()
        
        # 转换为响应格式
        result = []
        for event in events:
            # 获取源记录信息
            source_logs = []
            for source in event.source_logs:
                expert_log = db.query(ExpertLog).filter(ExpertLog.log_id == source.log_id).first()
                if expert_log:
                    # 获取该专家记录的附件信息
                    attachments = db.query(Attachment).filter(Attachment.log_id == source.log_id).all()
                    attachment_list = [
                        {
                            "attachment_id": str(attachment.attachment_id),
                            "file_name": attachment.file_name,
                            "file_type": attachment.file_type,
                            "file_size": attachment.file_size,
                            "uploaded_at": attachment.uploaded_at.isoformat() if attachment.uploaded_at else None
                        }
                        for attachment in attachments
                    ]
                    
                    source_logs.append({
                        "log_id": str(source.log_id),
                        "relevance_score": float(source.relevance_score),
                        "title": expert_log.description_text,
                        "created_at": source.created_at,
                        "attachments": attachment_list
                    })
            
            timeline_event = {
                "event_id": str(event.event_id),
                "turbine_id": str(event.turbine_id),
                "event_time": event.event_time,
                "event_severity": event.event_severity,
                "title": event.title,
                "summary": event.summary,
                "detail": event.detail,
                "key_points": event.key_points or [],
                "confidence_score": float(event.confidence_score) if event.confidence_score else None,
                "is_verified": event.is_verified,
                "created_at": event.created_at,
                "updated_at": event.updated_at,
                "source_logs": source_logs
            }
            result.append(timeline_event)
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting turbine timeline: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取时间线失败: {str(e)}"
        )

@router.get("/{event_id}", response_model=TimelineEventResponse)
async def get_timeline_event(
    event_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    获取指定时间线事件详情
    """
    try:
        event = db.query(TimelineEvent).filter(TimelineEvent.event_id == event_id).first()
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="时间线事件不存在"
            )
        
        # 获取源记录信息
        source_logs = []
        for source in event.source_logs:
            expert_log = db.query(ExpertLog).filter(ExpertLog.log_id == source.log_id).first()
            if expert_log:
                # 获取该专家记录的附件信息
                attachments = db.query(Attachment).filter(Attachment.log_id == source.log_id).all()
                attachment_list = [
                    {
                        "attachment_id": str(attachment.attachment_id),
                        "file_name": attachment.file_name,
                        "file_type": attachment.file_type,
                        "file_size": attachment.file_size,
                        "uploaded_at": attachment.uploaded_at.isoformat() if attachment.uploaded_at else None
                    }
                    for attachment in attachments
                ]
                
                source_logs.append({
                    "log_id": str(source.log_id),
                    "relevance_score": float(source.relevance_score),
                    "title": expert_log.description_text,
                    "created_at": source.created_at,
                    "attachments": attachment_list
                })
        
        return TimelineEventResponse(
            event_id=str(event.event_id),
            turbine_id=str(event.turbine_id),
            event_time=event.event_time,
            event_severity=event.event_severity,
            title=event.title,
            summary=event.summary,
            detail=event.detail,
            key_points=event.key_points or [],
            confidence_score=float(event.confidence_score) if event.confidence_score else None,
            is_verified=event.is_verified,
            created_at=event.created_at,
            updated_at=event.updated_at,
            source_logs=source_logs
        )
        
    except Exception as e:
        logger.error(f"Error getting timeline event: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取事件详情失败: {str(e)}"
        )

@router.put("/{event_id}", response_model=TimelineEventResponse)
async def update_timeline_event(
    event_id: str,
    event_update: TimelineEventUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    更新时间线事件
    """
    try:
        event = db.query(TimelineEvent).filter(TimelineEvent.event_id == event_id).first()
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="时间线事件不存在"
            )
        
        # 更新字段
        update_data = event_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(event, field, value)
        
        db.commit()
        db.refresh(event)
        
        # 更新风机状态基于最新时间线事件
        update_turbine_status_from_timeline(db, str(event.turbine_id))
        
        # 获取源记录信息
        source_logs = []
        for source in event.source_logs:
            expert_log = db.query(ExpertLog).filter(ExpertLog.log_id == source.log_id).first()
            if expert_log:
                source_logs.append({
                    "log_id": str(source.log_id),
                    "relevance_score": float(source.relevance_score),
                    "title": expert_log.description_text,
                    "created_at": source.created_at
                })
        
        return TimelineEventResponse(
            event_id=str(event.event_id),
            turbine_id=str(event.turbine_id),
            event_time=event.event_time,
            event_severity=event.event_severity,
            title=event.title,
            summary=event.summary,
            detail=event.detail,
            key_points=event.key_points or [],
            confidence_score=float(event.confidence_score) if event.confidence_score else None,
            is_verified=event.is_verified,
            created_at=event.created_at,
            updated_at=event.updated_at,
            source_logs=source_logs
        )
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating timeline event: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新事件失败: {str(e)}"
        )

@router.delete("/{event_id}")
async def delete_timeline_event(
    event_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    删除时间线事件（仅管理员可用）
    """
    try:
        event = db.query(TimelineEvent).filter(TimelineEvent.event_id == event_id).first()
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="时间线事件不存在"
            )
        
        turbine_id = str(event.turbine_id)
        db.delete(event)
        db.commit()
        
        # 删除事件后更新风机状态基于剩余的最新时间线事件
        update_turbine_status_from_timeline(db, turbine_id)
        
        return {"message": "时间线事件已删除"}
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting timeline event: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除事件失败: {str(e)}"
        )

@router.post("/update-from-log/{log_id}")
async def update_timeline_from_log(
    log_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    从专家记录更新时间线（用于专家记录发布后自动触发）
    """
    try:
        # 获取专家记录
        expert_log = db.query(ExpertLog).filter(ExpertLog.log_id == log_id).first()
        if not expert_log:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="专家记录不存在"
            )
        
        # 初始化AI服务
        ai_service = TimelineAIService(db)
        
        # 分析专家记录
        event_data = await ai_service.analyze_expert_log(expert_log)
        
        # 检查是否已存在相似事件
        existing_event = db.query(TimelineEvent).filter(
            TimelineEvent.turbine_id == expert_log.turbine_id,
            TimelineEvent.event_time == event_data['event_time'],
            TimelineEvent.event_severity == event_data['event_severity']
        ).first()
        
        if existing_event:
            # 更新现有事件
            existing_event.title = event_data['title']
            existing_event.summary = event_data['summary']
            existing_event.detail = event_data.get('detail')
            existing_event.key_points = event_data['key_points']
            existing_event.confidence_score = event_data['confidence_score']
            existing_event.event_severity = event_data['event_severity']
            
            # 添加源记录关联（如果不存在）
            existing_source = db.query(TimelineSourceLog).filter(
                TimelineSourceLog.event_id == existing_event.event_id,
                TimelineSourceLog.log_id == log_id
            ).first()
            
            if not existing_source:
                source_log = TimelineSourceLog(
                    event_id=existing_event.event_id,
                    log_id=log_id,
                    relevance_score=1.0
                )
                db.add(source_log)
            
            message = "已更新现有时间线事件"
        else:
            # 创建新事件
            new_event = TimelineEvent(
                turbine_id=expert_log.turbine_id,
                event_time=event_data['event_time'],
                event_severity=event_data['event_severity'],
                title=event_data['title'],
                summary=event_data['summary'],
                detail=event_data.get('detail'),
                key_points=event_data['key_points'],
                confidence_score=event_data['confidence_score']
            )
            db.add(new_event)
            db.flush()  # 获取event_id
            
            # 创建源记录关联
            source_log = TimelineSourceLog(
                event_id=new_event.event_id,
                log_id=log_id,
                relevance_score=1.0
            )
            db.add(source_log)
            
            message = "已创建新的时间线事件"
        
        db.commit()
        
        return {"message": message}
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating timeline from log: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新时间线失败: {str(e)}"
        )

@router.post("/turbine/{turbine_id}/batch-update")
async def batch_update_turbine_timeline(
    turbine_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    批量更新指定风机的时间线（从所有已发布的专家记录）
    """
    try:
        # 验证风机是否存在
        turbine = db.query(Turbine).filter(Turbine.turbine_id == turbine_id).first()
        if not turbine:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="风机不存在"
            )
        
        # 获取该风机的所有已发布专家记录
        expert_logs = db.query(ExpertLog).filter(
            ExpertLog.turbine_id == turbine_id
        ).all()
        
        if not expert_logs:
            return {"message": "该风机没有专家记录"}
        
        # 初始化AI服务
        ai_service = TimelineAIService(db)
        
        # 生成时间线
        timeline_data = await ai_service.generate_timeline_for_turbine(turbine_id)
        
        # 清除现有时间线事件
        db.query(TimelineEvent).filter(TimelineEvent.turbine_id == turbine_id).delete()
        
        # 创建新的时间线事件
        events_created = 0
        for event_data in timeline_data:
            event = TimelineEvent(
                turbine_id=turbine_id,
                event_time=event_data['event_time'],
                event_severity=event_data['event_severity'],
                title=event_data['title'],
                summary=event_data['summary'],
                key_points=event_data['key_points'],
                confidence_score=event_data['confidence_score']
            )
            db.add(event)
            db.flush()
            
            # 创建源记录关联
            if 'source_log_id' in event_data:
                source_log = TimelineSourceLog(
                    event_id=event.event_id,
                    log_id=event_data['source_log_id'],
                    relevance_score=1.0
                )
                db.add(source_log)
            
            events_created += 1
        
        db.commit()
        
        return {
            "message": f"成功为风机 {turbine_id} 批量更新时间线",
            "events_created": events_created,
            "expert_logs_processed": len(expert_logs)
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error batch updating timeline: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"批量更新时间线失败: {str(e)}"
        )

@router.post("/batch-update-all")
async def batch_update_all_timelines(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    批量更新所有风机的时间线（仅管理员可用）
    """
    try:
        # 获取所有有专家记录的风机
        turbines_with_logs = db.query(Turbine.turbine_id).join(
            ExpertLog, Turbine.turbine_id == ExpertLog.turbine_id
        ).distinct().all()
        
        if not turbines_with_logs:
            return {"message": "没有找到有专家记录的风机"}
        
        ai_service = TimelineAIService(db)
        results = []
        
        for (turbine_id,) in turbines_with_logs:
            try:
                # 生成时间线
                timeline_data = await ai_service.generate_timeline_for_turbine(turbine_id)
                
                # 清除现有时间线事件
                db.query(TimelineEvent).filter(TimelineEvent.turbine_id == turbine_id).delete()
                
                # 创建新的时间线事件
                events_created = 0
                for event_data in timeline_data:
                    event = TimelineEvent(
                        turbine_id=turbine_id,
                        event_time=event_data['event_time'],
                        event_severity=event_data['event_severity'],
                        title=event_data['title'],
                        summary=event_data['summary'],
                        key_points=event_data['key_points'],
                        confidence_score=event_data['confidence_score']
                    )
                    db.add(event)
                    db.flush()
                    
                    # 创建源记录关联
                    if 'source_log_id' in event_data:
                        source_log = TimelineSourceLog(
                            event_id=event.event_id,
                            log_id=event_data['source_log_id'],
                            relevance_score=1.0
                        )
                        db.add(source_log)
                    
                    events_created += 1
                
                db.commit()
                
                results.append({
                    "turbine_id": turbine_id,
                    "status": "success",
                    "events_created": events_created
                })
                
            except Exception as e:
                db.rollback()
                results.append({
                    "turbine_id": turbine_id,
                    "status": "failed",
                    "error": str(e)
                })
        
        successful_updates = len([r for r in results if r["status"] == "success"])
        failed_updates = len([r for r in results if r["status"] == "failed"])
        
        return {
            "message": f"批量更新完成: {successful_updates} 个成功, {failed_updates} 个失败",
            "results": results,
            "summary": {
                "total_turbines": len(turbines_with_logs),
                "successful": successful_updates,
                "failed": failed_updates
            }
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error batch updating all timelines: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"批量更新所有时间线失败: {str(e)}"
        )

# ==================== 智能总结功能 ====================

@router.post("/turbine/{turbine_id}/intelligent-summary")
async def generate_intelligent_summary(
    turbine_id: str,
    days_back: int = 30,
    analysis_mode: str = "llm",
    force_regenerate: bool = False,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    为指定风机生成智能总结
    
    Args:
        turbine_id: 风机ID
        days_back: 回溯天数，默认30天
        analysis_mode: 分析模式，"llm"使用大模型分析，"basic"使用基本统计
        force_regenerate: 是否强制重新生成，默认False
    """
    try:
        # 验证分析模式参数
        if analysis_mode not in ["llm", "basic"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="分析模式必须是 'llm' 或 'basic'"
            )
        
        # 验证风机是否存在
        turbine = db.query(Turbine).filter(Turbine.turbine_id == turbine_id).first()
        if not turbine:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="风机不存在"
            )
        
        # 初始化智能总结服务
        summary_service = IntelligentSummaryService(db)
        
        # 生成智能总结 - 支持不同分析模式和数据库存储
        result = await summary_service.generate_turbine_summary(
            turbine_id=turbine_id, 
            days_back=days_back,
            analysis_mode=analysis_mode,
            force_regenerate=force_regenerate
        )
        
        # 返回完整的分析结果
        return {
            "success": True,
            "data": result,
            "turbine_id": turbine_id
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error generating intelligent summary for turbine {turbine_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"生成智能总结失败: {str(e)}"
        )

@router.get("/turbine/{turbine_id}/intelligent-summary")
async def get_saved_intelligent_summary(
    turbine_id: str,
    analysis_mode: str = "llm",
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    获取已保存的智能分析结果
    
    Args:
        turbine_id: 风机ID
        analysis_mode: 分析模式，"llm"使用大模型分析，"basic"使用基本统计
    """
    try:
        # 验证分析模式参数
        if analysis_mode not in ["llm", "basic"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="分析模式必须是 'llm' 或 'basic'"
            )
        
        # 验证风机是否存在
        turbine = db.query(Turbine).filter(Turbine.turbine_id == turbine_id).first()
        if not turbine:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="风机不存在"
            )
        
        # 初始化智能总结服务
        summary_service = IntelligentSummaryService(db)
        
        # 获取已保存的分析结果
        saved_analysis = await summary_service.get_saved_analysis(turbine_id, analysis_mode)
        
        if not saved_analysis:
            return {
                "success": False,
                "message": "未找到已保存的分析结果",
                "turbine_id": turbine_id
            }
        
        # 返回保存的分析结果
        return {
            "success": True,
            "data": {
                "summary": saved_analysis.summary,
                "analysis_data": saved_analysis.analysis_data,
                "analysis_mode": saved_analysis.analysis_mode,
                "days_back": saved_analysis.days_back,
                "created_at": saved_analysis.created_at.isoformat(),
                "updated_at": saved_analysis.updated_at.isoformat() if saved_analysis.updated_at else None,
                "is_cached": True
            },
            "turbine_id": turbine_id
        }
        
    except Exception as e:
        logger.error(f"Error retrieving saved intelligent summary for turbine {turbine_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取智能总结失败: {str(e)}"
        )

@router.get("/turbine/{turbine_id}/summary-status")
async def get_summary_status(
    turbine_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    获取风机智能总结状态信息
    
    Args:
        turbine_id: 风机ID
    """
    try:
        # 验证风机是否存在
        turbine = db.query(Turbine).filter(Turbine.turbine_id == turbine_id).first()
        if not turbine:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="风机不存在"
            )
        
        # 获取专家记录统计
        from datetime import datetime, timedelta
        from sqlalchemy import and_
        
        cutoff_date = datetime.utcnow() - timedelta(days=30)
        recent_logs_count = db.query(ExpertLog).filter(
            and_(
                ExpertLog.turbine_id == turbine_id,
                ExpertLog.log_status == 'published',
                ExpertLog.created_at >= cutoff_date
            )
        ).count()
        
        total_logs_count = db.query(ExpertLog).filter(
            and_(
                ExpertLog.turbine_id == turbine_id,
                ExpertLog.log_status == 'published'
            )
        ).count()
        
        return {
            "turbine_id": turbine_id,
            "turbine_name": turbine.unit_id,
            "recent_logs_count": recent_logs_count,
            "total_logs_count": total_logs_count,
            "has_data": recent_logs_count > 0,
            "summary_available": recent_logs_count > 0
        }
        
    except Exception as e:
        logger.error(f"Error getting summary status for turbine {turbine_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取总结状态失败: {str(e)}"
        )

# ==================== 时间线编辑功能 ====================

@router.post("/batch-edit")
async def batch_edit_timeline_events(
    event_updates: List[dict],
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    批量编辑时间线事件
    
    Args:
        event_updates: 事件更新列表，每个元素包含event_id和要更新的字段
    """
    try:
        updated_events = []
        failed_updates = []
        
        for update_data in event_updates:
            try:
                event_id = update_data.get('event_id')
                if not event_id:
                    failed_updates.append({
                        "event_id": None,
                        "error": "缺少event_id"
                    })
                    continue
                
                event = db.query(TimelineEvent).filter(TimelineEvent.event_id == event_id).first()
                if not event:
                    failed_updates.append({
                        "event_id": event_id,
                        "error": "事件不存在"
                    })
                    continue
                
                # 更新字段
                for field, value in update_data.items():
                    if field != 'event_id' and hasattr(event, field):
                        setattr(event, field, value)
                
                updated_events.append(event_id)
                
            except Exception as e:
                failed_updates.append({
                    "event_id": update_data.get('event_id'),
                    "error": str(e)
                })
        
        db.commit()
        
        return {
            "message": f"批量编辑完成: {len(updated_events)} 个成功, {len(failed_updates)} 个失败",
            "updated_events": updated_events,
            "failed_updates": failed_updates
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error batch editing timeline events: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"批量编辑失败: {str(e)}"
        )

@router.post("/batch-verify")
async def batch_verify_timeline_events(
    event_ids: List[str],
    is_verified: bool = True,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    批量验证/取消验证时间线事件
    
    Args:
        event_ids: 事件ID列表
        is_verified: 是否验证，默认True
    """
    try:
        updated_count = 0
        failed_updates = []
        
        for event_id in event_ids:
            try:
                event = db.query(TimelineEvent).filter(TimelineEvent.event_id == event_id).first()
                if not event:
                    failed_updates.append({
                        "event_id": event_id,
                        "error": "事件不存在"
                    })
                    continue
                
                event.is_verified = is_verified
                updated_count += 1
                
            except Exception as e:
                failed_updates.append({
                    "event_id": event_id,
                    "error": str(e)
                })
        
        db.commit()
        
        action = "验证" if is_verified else "取消验证"
        return {
            "message": f"批量{action}完成: {updated_count} 个成功, {len(failed_updates)} 个失败",
            "updated_count": updated_count,
            "failed_updates": failed_updates
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error batch verifying timeline events: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"批量验证失败: {str(e)}"
        )

@router.post("/batch-delete")
async def batch_delete_timeline_events(
    event_ids: List[str],
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    批量删除时间线事件
    
    Args:
        event_ids: 事件ID列表
    """
    try:
        deleted_count = 0
        failed_deletes = []
        
        for event_id in event_ids:
            try:
                event = db.query(TimelineEvent).filter(TimelineEvent.event_id == event_id).first()
                if not event:
                    failed_deletes.append({
                        "event_id": event_id,
                        "error": "事件不存在"
                    })
                    continue
                
                db.delete(event)
                deleted_count += 1
                
            except Exception as e:
                failed_deletes.append({
                    "event_id": event_id,
                    "error": str(e)
                })
        
        db.commit()
        
        return {
            "message": f"批量删除完成: {deleted_count} 个成功, {len(failed_deletes)} 个失败",
            "deleted_count": deleted_count,
            "failed_deletes": failed_deletes
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error batch deleting timeline events: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"批量删除失败: {str(e)}"
        )

@router.post("/create")
async def create_timeline_event(
    event_data: TimelineEventCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_or_expert_for_user_management)
):
    """
    创建新的时间线事件（管理员和专家可用）
    """
    try:
        # 验证风机是否存在
        turbine = db.query(Turbine).filter(Turbine.turbine_id == event_data.turbine_id).first()
        if not turbine:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="风机不存在"
            )
        
        # 检查专家记录一对一关系：如果有source_log_ids，确保每个专家记录只能关联一个时间线事件
        for log_id in event_data.source_log_ids:
            # 查找该专家记录是否已经关联了其他时间线事件
            existing_source = db.query(TimelineSourceLog).filter(
                TimelineSourceLog.log_id == log_id
            ).first()
            
            if existing_source:
                # 删除旧的时间线事件及其关联
                old_event = db.query(TimelineEvent).filter(
                    TimelineEvent.event_id == existing_source.event_id
                ).first()
                
                if old_event:
                    # 删除所有相关的源记录关联
                    db.query(TimelineSourceLog).filter(
                        TimelineSourceLog.event_id == old_event.event_id
                    ).delete()
                    
                    # 删除旧的时间线事件
                    db.delete(old_event)
                    logger.info(f"删除专家记录 {log_id} 的旧时间线事件 {old_event.event_id}")
        
        # 创建新事件
        new_event = TimelineEvent(
            turbine_id=event_data.turbine_id,
            event_time=event_data.event_time,
            event_severity=event_data.event_severity,
            title=event_data.title,
            summary=event_data.summary,
            detail=event_data.detail,
            key_points=event_data.key_points,
            confidence_score=event_data.confidence_score,
            is_verified=False  # 新创建的事件默认未验证
        )
        
        db.add(new_event)
        db.flush()  # 获取event_id
        
        # 创建源记录关联
        for log_id in event_data.source_log_ids:
            source_log = TimelineSourceLog(
                event_id=new_event.event_id,
                log_id=log_id,
                relevance_score=1.0
            )
            db.add(source_log)
        
        db.commit()
        db.refresh(new_event)
        
        # 更新风机状态基于最新时间线事件
        update_turbine_status_from_timeline(db, str(new_event.turbine_id))
        
        # 获取源记录信息
        source_logs = []
        for source in new_event.source_logs:
            expert_log = db.query(ExpertLog).filter(ExpertLog.log_id == source.log_id).first()
            if expert_log:
                source_logs.append({
                    "log_id": str(source.log_id),
                    "relevance_score": float(source.relevance_score),
                    "title": expert_log.description_text,
                    "created_at": source.created_at
                })
        
        return TimelineEventResponse(
            event_id=str(new_event.event_id),
            turbine_id=str(new_event.turbine_id),
            event_time=new_event.event_time,
            event_severity=new_event.event_severity,
            title=new_event.title,
            summary=new_event.summary,
            detail=new_event.detail,
            key_points=new_event.key_points or [],
            confidence_score=float(new_event.confidence_score) if new_event.confidence_score else None,
            is_verified=new_event.is_verified,
            created_at=new_event.created_at,
            updated_at=new_event.updated_at,
            source_logs=source_logs
        )
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating timeline event: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建事件失败: {str(e)}"
        )

@router.post("/batch-update-turbine-status")
async def batch_update_turbine_status(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    批量更新所有风机状态基于最新时间线事件（仅管理员可用）
    """
    try:
        result = batch_update_all_turbine_status(db)
        
        return {
            "message": "批量更新风机状态完成",
            "result": result
        }
        
    except Exception as e:
        logger.error(f"Error batch updating turbine status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"批量更新风机状态失败: {str(e)}"
        )

# ==================== AI内容生成功能 ====================

@router.post("/generate-ai-content")
async def generate_ai_content_for_event(
    request: dict,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_or_expert_for_user_management)
):
    """
    为时间线事件生成AI内容（摘要和详细内容）
    
    Args:
        request: 包含以下字段的字典
            - turbine_id: 风机ID
            - content: 提取的内容文本
            - title: 事件标题（可选）
    """
    try:
        # 验证请求参数
        turbine_id = request.get('turbine_id')
        content = request.get('content', '').strip()
        title = request.get('title', '')
        
        if not turbine_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="缺少风机ID"
            )
        
        if not content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="缺少内容文本"
            )
        
        # 验证风机是否存在
        turbine = db.query(Turbine).filter(Turbine.turbine_id == turbine_id).first()
        if not turbine:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="风机不存在"
            )
        
        # 初始化AI服务
        ai_service = TimelineAIService(db)
        
        # 分类事件严重程度
        event_severity = ai_service.classify_event_severity(content)
        
        # 生成AI摘要、详细内容和关键点
        ai_title, summary, detail, key_points, confidence = await ai_service._generate_event_summary(
            content, 
            event_severity
        )
        
        # 如果没有提供标题，使用AI生成的标题
        if not title.strip():
            title = ai_title
        
        return {
            "success": True,
            "data": {
                "title": title,
                "summary": summary,
                "detail": detail,
                "key_points": key_points,
                "event_severity": event_severity.value,
                "confidence_score": confidence
            },
            "message": "AI内容生成成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating AI content: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI内容生成失败: {str(e)}"
        )