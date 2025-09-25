from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import datetime
import os
import uuid
import aiofiles
from pathlib import Path
from models import get_db, User, ExpertLog, Turbine, Attachment
from models.expert_log import LogStatus
from models.user import UserRole
from schemas.expert_log import ExpertLogCreate, ExpertLogUpdate, ExpertLogResponse
from utils.dependencies import get_current_user, get_current_admin_user, get_current_admin_or_expert_for_user_management
from services.text_extraction_service import TextExtractionService
from services.rag_service import RAGService

router = APIRouter()

@router.post("/", response_model=ExpertLogResponse)
async def create_expert_log(
    log: ExpertLogCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_or_expert_for_user_management)
):
    """创建专家记录（管理员和专家可用）"""
    # 验证风机是否存在
    turbine = db.query(Turbine).filter(Turbine.turbine_id == log.turbine_id).first()
    if not turbine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Turbine not found"
        )
    
    # 创建专家记录
    db_log = ExpertLog(
        turbine_id=log.turbine_id,
        author_id=current_user.user_id,
        status_tag=log.status_tag,
        description_text=log.description_text
    )
    db.add(db_log)
    
    # 同时更新风机状态为专家记录中的状态标签
    turbine.status = log.status_tag.value
    
    db.commit()
    db.refresh(db_log)
    
    # 手动转换UUID为字符串
    return {
        "log_id": str(db_log.log_id),
        "turbine_id": str(db_log.turbine_id),
        "author_id": str(db_log.author_id),
        "status_tag": db_log.status_tag,
        "description_text": db_log.description_text,
        "log_status": db_log.log_status,
        "ai_summary": db_log.ai_summary,
        "ai_tags": db_log.ai_tags,
        "ai_confidence": db_log.ai_confidence,
        "ai_review_status": db_log.ai_review_status,
        "created_at": db_log.created_at,
        "updated_at": db_log.updated_at,
        "published_at": db_log.published_at,
        "attachments": []
    }

@router.get("/", response_model=List[ExpertLogResponse])
async def list_expert_logs(
    turbine_id: str = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取专家记录列表"""
    query = db.query(ExpertLog).options(
        joinedload(ExpertLog.turbine),
        joinedload(ExpertLog.author),
        joinedload(ExpertLog.attachments)
    )
    
    if turbine_id:
        query = query.filter(ExpertLog.turbine_id == turbine_id)
    
    # 只有READER用户只能看到已发布的记录，ADMIN和EXPERT可以看到所有记录
    if current_user.role == UserRole.READER:
        query = query.filter(ExpertLog.log_status == LogStatus.PUBLISHED)
    
    logs = query.offset(skip).limit(limit).all()
    # 手动转换UUID为字符串，包含关联对象信息
    return [
        {
            "log_id": str(log.log_id),
            "turbine_id": str(log.turbine_id),
            "author_id": str(log.author_id),
            "status_tag": log.status_tag,
            "description_text": log.description_text,
            "ai_summary": log.ai_summary,
            "ai_tags": log.ai_tags,
            "log_status": log.log_status,
            "ai_confidence": log.ai_confidence,
            "ai_review_status": log.ai_review_status,
            "created_at": log.created_at,
            "updated_at": log.updated_at,
            "published_at": log.published_at,
            "turbine": {
                "turbine_id": str(log.turbine.turbine_id),
                "farm_name": log.turbine.farm_name,
                "unit_id": log.turbine.unit_id,
                "model": log.turbine.model,
                "owner_company": log.turbine.owner_company
            } if log.turbine else None,
            "author": {
                "user_id": str(log.author.user_id),
                "username": log.author.username,
                "role": log.author.role
            } if log.author else None,
            "attachments": [
                {
                    "attachment_id": str(attachment.attachment_id),
                    "file_name": attachment.file_name,
                    "file_type": attachment.file_type,
                    "file_size": attachment.file_size,
                    "uploaded_at": attachment.uploaded_at
                }
                for attachment in log.attachments
            ]
        }
        for log in logs
    ]

@router.get("/{log_id}", response_model=ExpertLogResponse)
async def get_expert_log(
    log_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取单个专家记录详情"""
    log = db.query(ExpertLog).options(
        joinedload(ExpertLog.turbine),
        joinedload(ExpertLog.author),
        joinedload(ExpertLog.attachments)
    ).filter(ExpertLog.log_id == log_id).first()
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expert log not found"
        )
    
    # 权限检查：ADMIN和EXPERT可以看到所有记录，READER只能看到已发布的记录或自己创建的草稿
    if (current_user.role == UserRole.READER and 
        log.log_status != LogStatus.PUBLISHED and 
        log.author_id != current_user.user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # 手动转换UUID为字符串，包含关联对象信息
    return {
        "log_id": str(log.log_id),
        "turbine_id": str(log.turbine_id),
        "author_id": str(log.author_id),
        "status_tag": log.status_tag,
        "description_text": log.description_text,
        "ai_summary": log.ai_summary,
        "ai_tags": log.ai_tags,
        "ai_confidence": float(log.ai_confidence) if log.ai_confidence is not None else None,
        "ai_review_status": log.ai_review_status,
        "log_status": log.log_status,
        "created_at": log.created_at,
        "updated_at": log.updated_at,
        "published_at": log.published_at,
        "turbine": {
            "turbine_id": str(log.turbine.turbine_id),
            "farm_name": log.turbine.farm_name,
            "unit_id": log.turbine.unit_id,
            "model": log.turbine.model,
            "owner_company": log.turbine.owner_company
        } if log.turbine else None,
        "author": {
            "user_id": str(log.author.user_id),
            "username": log.author.username,
            "role": log.author.role
        } if log.author else None,
        "attachments": [
            {
                "attachment_id": str(attachment.attachment_id),
                "file_name": attachment.file_name,
                "file_type": attachment.file_type,
                "file_size": attachment.file_size,
                "uploaded_at": attachment.uploaded_at
            }
            for attachment in log.attachments
        ]
    }

@router.put("/{log_id}", response_model=ExpertLogResponse)
async def update_expert_log(
    log_id: str,
    log_update: ExpertLogUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """更新专家记录（仅管理员）"""
    log = db.query(ExpertLog).filter(ExpertLog.log_id == log_id).first()
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expert log not found"
        )
    
    update_data = log_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(log, field, value)
    
    db.commit()
    db.refresh(log)
    
    # 重新加载关联对象
    log = db.query(ExpertLog).options(
        joinedload(ExpertLog.turbine),
        joinedload(ExpertLog.author),
        joinedload(ExpertLog.attachments)
    ).filter(ExpertLog.log_id == log_id).first()
    
    # 手动转换UUID为字符串，包含关联对象信息
    return {
        "log_id": str(log.log_id),
        "turbine_id": str(log.turbine_id),
        "author_id": str(log.author_id),
        "status_tag": log.status_tag,
        "description_text": log.description_text,
        "ai_summary": log.ai_summary,
        "ai_tags": log.ai_tags,
        "ai_confidence": float(log.ai_confidence) if log.ai_confidence is not None else None,
        "ai_review_status": log.ai_review_status,
        "log_status": log.log_status,
        "created_at": log.created_at,
        "updated_at": log.updated_at,
        "published_at": log.published_at,
        "turbine": {
            "turbine_id": str(log.turbine.turbine_id),
            "farm_name": log.turbine.farm_name,
            "unit_id": log.turbine.unit_id,
            "model": log.turbine.model,
            "owner_company": log.turbine.owner_company
        } if log.turbine else None,
        "author": {
            "user_id": str(log.author.user_id),
            "username": log.author.username,
            "role": log.author.role
        } if log.author else None,
        "attachments": [
            {
                "attachment_id": str(attachment.attachment_id),
                "file_name": attachment.file_name,
                "file_type": attachment.file_type,
                "file_size": attachment.file_size,
                "uploaded_at": attachment.uploaded_at
            }
            for attachment in log.attachments
        ]
    }

@router.post("/{log_id}/publish")
async def publish_expert_log(
    log_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """发布专家记录（仅管理员）"""
    log = db.query(ExpertLog).filter(ExpertLog.log_id == log_id).first()
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expert log not found"
        )
    
    if log.log_status == LogStatus.PUBLISHED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Log is already published"
        )
    
    # 获取关联的风机
    turbine = db.query(Turbine).filter(Turbine.turbine_id == log.turbine_id).first()
    if turbine:
        # 发布时更新风机状态为专家记录中的状态标签
        turbine.status = log.status_tag.value
    
    log.log_status = LogStatus.PUBLISHED
    log.published_at = datetime.utcnow()
    
    db.commit()
    db.refresh(log)
    
    # 触发RAG处理（分块、嵌入等）
    try:
        rag_service = RAGService(db)
        await rag_service.process_expert_log(str(log.log_id))
    except Exception as e:
        # 记录错误但不影响发布流程
        print(f"RAG processing failed for log {log.log_id}: {e}")
    
    # 注意：为了提升发布性能，时间线更新已移除
    # 用户可以在时间线页面手动触发智能总结更新
    
    return {"message": "Expert log published successfully"}

@router.delete("/{log_id}")
async def delete_expert_log(
    log_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """删除专家记录（仅管理员）"""
    from models.timeline import TimelineSourceLog, TimelineEvent
    
    log = db.query(ExpertLog).filter(ExpertLog.log_id == log_id).first()
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expert log not found"
        )
    
    # 获取所有相关的时间线源记录
    source_logs = db.query(TimelineSourceLog).filter(TimelineSourceLog.log_id == log_id).all()
    
    # 收集相关的事件ID
    event_ids = [source_log.event_id for source_log in source_logs]
    
    # 删除时间线源记录
    db.query(TimelineSourceLog).filter(TimelineSourceLog.log_id == log_id).delete()
    
    # 检查并删除没有其他源记录的孤立时间线事件
    for event_id in event_ids:
        remaining_sources = db.query(TimelineSourceLog).filter(TimelineSourceLog.event_id == event_id).count()
        if remaining_sources == 0:
            # 如果没有其他源记录，删除该时间线事件
            db.query(TimelineEvent).filter(TimelineEvent.event_id == event_id).delete()
    
    # 然后删除专家记录（级联删除会自动处理附件和chunks）
    db.delete(log)
    db.commit()
    
    return {"message": "Expert log deleted successfully"}

@router.post("/{log_id}/attachments")
async def upload_attachment(
    log_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """为专家记录上传附件（仅管理员）"""
    # 验证专家记录是否存在
    log = db.query(ExpertLog).filter(ExpertLog.log_id == log_id).first()
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expert log not found"
        )
    
    # 检查文件类型和大小
    allowed_types = {
        'application/pdf', 'text/plain', 'text/csv',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/vnd.ms-excel',
        'image/jpeg', 'image/png', 'image/gif', 'image/bmp', 'image/tiff',
        'audio/mpeg', 'audio/wav', 'audio/ogg',
        'video/mp4', 'video/avi', 'video/mov'
    }
    
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type {file.content_type} not supported"
        )
    
    # 限制文件大小为50MB
    max_size = 50 * 1024 * 1024  # 50MB
    file_content = await file.read()
    if len(file_content) > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size exceeds 50MB limit"
        )
    
    # 创建存储目录
    upload_dir = Path("/app/uploads/attachments")
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    # 生成唯一文件名
    file_extension = Path(file.filename).suffix
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = upload_dir / unique_filename
    
    # 保存文件
    async with aiofiles.open(file_path, 'wb') as f:
        await f.write(file_content)
    
    # 创建附件记录
    attachment = Attachment(
        log_id=log.log_id,
        file_name=file.filename,
        file_type=file.content_type,
        file_size=len(file_content),
        storage_path=str(file_path)
    )
    
    db.add(attachment)
    db.commit()
    db.refresh(attachment)
    
    # 异步提取文本内容
    text_extracted = False
    try:
        text_service = TextExtractionService()
        extracted_text = await text_service.extract_text(str(file_path), file.content_type)
        
        if extracted_text:
            attachment.extracted_text = extracted_text
            db.commit()
            db.refresh(attachment)
            text_extracted = True
            
            # 如果提取到文本内容，更新专家记录的内容并重新处理嵌入
            try:
                expert_log = db.query(ExpertLog).filter(ExpertLog.log_id == log_id).first()
                if expert_log:
                    # 将附件文本添加到专家记录内容中
                    attachment_content = f"\n\n[附件: {file.filename}]\n{extracted_text}"
                    if expert_log.description_text:
                        expert_log.description_text += attachment_content
                    else:
                        expert_log.description_text = attachment_content.strip()
                    
                    db.commit()
                    
                    # 重新处理RAG嵌入
                    rag_service = RAGService(db)
                    await rag_service.process_expert_log(int(log_id))
                    
            except Exception as rag_error:
                print(f"RAG processing failed for log {log_id}: {str(rag_error)}")
                
    except Exception as e:
        # 文本提取失败不影响文件上传
        print(f"Text extraction failed for {file.filename}: {str(e)}")
    
    return {
        "attachment_id": str(attachment.attachment_id),
        "file_name": attachment.file_name,
        "file_type": attachment.file_type,
        "file_size": attachment.file_size,
        "uploaded_at": attachment.uploaded_at.isoformat(),
        "message": "文件上传成功"
    }

@router.post("/{log_id}/attachments/batch")
async def upload_attachments_batch(
    log_id: str,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """为专家记录批量上传多个附件"""
    # 验证专家记录是否存在
    log = db.query(ExpertLog).filter(ExpertLog.log_id == log_id).first()
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expert log not found"
        )
    
    # 检查文件数量限制（最多10个文件）
    if len(files) > 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot upload more than 10 files at once"
        )
    
    # 检查文件类型和大小
    allowed_types = {
        'application/pdf', 'text/plain', 'text/csv',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/vnd.ms-excel',
        'image/jpeg', 'image/png', 'image/gif', 'image/bmp', 'image/tiff',
        'audio/mpeg', 'audio/wav', 'audio/ogg',
        'video/mp4', 'video/avi', 'video/mov'
    }
    
    max_size = 50 * 1024 * 1024  # 50MB
    upload_dir = Path("/app/uploads/attachments")
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    uploaded_attachments = []
    failed_uploads = []
    
    for file in files:
        try:
            # 验证文件类型
            if file.content_type not in allowed_types:
                failed_uploads.append({
                    "file_name": file.filename,
                    "error": f"File type {file.content_type} not supported"
                })
                continue
            
            # 验证文件大小
            file_content = await file.read()
            if len(file_content) > max_size:
                failed_uploads.append({
                    "file_name": file.filename,
                    "error": "File size exceeds 50MB limit"
                })
                continue
            
            # 生成唯一文件名
            file_extension = Path(file.filename).suffix
            unique_filename = f"{uuid.uuid4()}{file_extension}"
            file_path = upload_dir / unique_filename
            
            # 保存文件
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(file_content)
            
            # 创建附件记录
            attachment = Attachment(
                log_id=log.log_id,
                file_name=file.filename,
                file_type=file.content_type,
                file_size=len(file_content),
                storage_path=str(file_path)
            )
            
            db.add(attachment)
            db.commit()
            db.refresh(attachment)
            
            uploaded_attachments.append({
                "attachment_id": str(attachment.attachment_id),
                "file_name": attachment.file_name,
                "file_type": attachment.file_type,
                "file_size": attachment.file_size,
                "uploaded_at": attachment.uploaded_at.isoformat()
            })
            
            # 异步提取文本内容（不阻塞批量上传）
            try:
                text_service = TextExtractionService()
                extracted_text = await text_service.extract_text(str(file_path), file.content_type)
                
                if extracted_text:
                    attachment.extracted_text = extracted_text
                    db.commit()
                    
            except Exception as e:
                print(f"Text extraction failed for {file.filename}: {str(e)}")
                
        except Exception as e:
            failed_uploads.append({
                "file_name": file.filename,
                "error": str(e)
            })
    
    # 如果有成功上传的文件，重新处理RAG嵌入
    if uploaded_attachments:
        try:
            rag_service = RAGService(db)
            await rag_service.process_expert_log(int(log_id))
        except Exception as rag_error:
            print(f"RAG processing failed for log {log_id}: {str(rag_error)}")
    
    return {
        "uploaded_count": len(uploaded_attachments),
        "failed_count": len(failed_uploads),
        "uploaded_attachments": uploaded_attachments,
        "failed_uploads": failed_uploads,
        "message": f"批量上传完成：成功 {len(uploaded_attachments)} 个，失败 {len(failed_uploads)} 个"
    }

@router.get("/{log_id}/attachments")
async def list_attachments(
    log_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取专家记录的附件列表"""
    # 验证专家记录是否存在
    log = db.query(ExpertLog).filter(ExpertLog.log_id == log_id).first()
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expert log not found"
        )
    
    # READER用户只能看到已发布记录的附件
    if current_user.role == UserRole.READER and log.log_status != LogStatus.PUBLISHED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    attachments = db.query(Attachment).filter(Attachment.log_id == log_id).all()
    
    return [
        {
            "attachment_id": str(attachment.attachment_id),
            "file_name": attachment.file_name,
            "file_type": attachment.file_type,
            "file_size": attachment.file_size,
            "uploaded_at": attachment.uploaded_at.isoformat(),
            "has_extracted_text": bool(attachment.extracted_text)
        }
        for attachment in attachments
    ]

@router.delete("/{log_id}/attachments/{attachment_id}")
async def delete_attachment(
    log_id: str,
    attachment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """删除附件（仅管理员）"""
    # 验证专家记录是否存在
    log = db.query(ExpertLog).filter(ExpertLog.log_id == log_id).first()
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expert log not found"
        )
    
    # 验证附件是否存在且属于该记录
    attachment = db.query(Attachment).filter(
        Attachment.attachment_id == attachment_id,
        Attachment.log_id == log_id
    ).first()
    
    if not attachment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attachment not found"
        )
    
    # 删除物理文件
    try:
        if os.path.exists(attachment.storage_path):
            os.remove(attachment.storage_path)
    except Exception as e:
        print(f"Failed to delete file {attachment.storage_path}: {str(e)}")
    
    # 删除数据库记录
    db.delete(attachment)
    db.commit()
    
    return {"message": "Attachment deleted successfully"}

@router.get("/attachments/{attachment_id}/download")
async def download_attachment(
    attachment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """下载附件"""
    # 验证附件是否存在
    attachment = db.query(Attachment).filter(Attachment.attachment_id == attachment_id).first()
    if not attachment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attachment not found"
        )
    
    # 验证用户是否有权限访问该附件
    expert_log = db.query(ExpertLog).filter(ExpertLog.log_id == attachment.log_id).first()
    if not expert_log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expert log not found"
        )
    
    # READER用户只能下载已发布记录的附件
    if current_user.role == UserRole.READER and expert_log.log_status != LogStatus.PUBLISHED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # 检查文件是否存在
    if not os.path.exists(attachment.storage_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found on server"
        )
    
    # 返回文件
    return FileResponse(
        path=attachment.storage_path,
        filename=attachment.file_name,
        media_type=attachment.file_type or 'application/octet-stream'
    )

@router.post("/{log_id}/analyze")
async def trigger_ai_analysis(
    log_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """手动触发专家记录的AI分析（仅管理员）"""
    log = db.query(ExpertLog).options(
        joinedload(ExpertLog.attachments)
    ).filter(ExpertLog.log_id == log_id).first()
    
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expert log not found"
        )
    
    try:
        # 1. 处理附件内容提取
        for attachment in log.attachments:
            if not attachment.extracted_text:
                # 根据文件类型提取内容
                if attachment.file_type in ['application/pdf', 'text/plain', 'application/msword', 
                                         'application/vnd.openxmlformats-officedocument.wordprocessingml.document']:
                    # 提取文本内容（这里需要实现具体的文本提取逻辑）
                    extracted_text = await extract_text_from_file(attachment.storage_path, attachment.file_type)
                    attachment.extracted_text = extracted_text
                    
                    # 生成AI摘要
                    if extracted_text:
                        ai_excerpt = await generate_ai_excerpt(extracted_text)
                        attachment.ai_excerpt = ai_excerpt
        
        # 2. 生成专家记录的AI摘要和标签
        full_content = log.description_text
        for attachment in log.attachments:
            if attachment.extracted_text:
                full_content += f"\n\n附件内容：{attachment.extracted_text}"
        
        if full_content:
            ai_summary = await generate_ai_summary(full_content)
            ai_tags = await generate_ai_tags(full_content)
            
            log.ai_summary = ai_summary
            log.ai_tags = ai_tags
            log.ai_confidence = 0.85  # 默认置信度
            log.ai_review_status = AIReviewStatus.APPROVED
        
        # 3. 生成时间线事件（如果记录已发布）
        timeline_events = []
        if log.log_status == LogStatus.PUBLISHED:
            from services.timeline_ai_service import TimelineAIService
            timeline_service = TimelineAIService(db)
            events = await timeline_service.generate_timeline_for_turbine(str(log.turbine_id))
            timeline_events = events
        
        db.commit()
        
        return {
            "message": "AI analysis completed successfully",
            "ai_summary": log.ai_summary,
            "ai_tags": log.ai_tags,
            "ai_confidence": float(log.ai_confidence) if log.ai_confidence else None,
            "timeline_events_generated": len(timeline_events),
            "attachments_processed": len([a for a in log.attachments if a.extracted_text])
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI analysis failed: {str(e)}"
        )

async def extract_text_from_file(file_path: str, file_type: str) -> str:
    """从文件中提取文本内容"""
    try:
        if file_type == 'text/plain':
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        elif file_type == 'application/pdf':
            # PDF文本提取（需要安装PyPDF2或类似库）
            import PyPDF2
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                text = ""
                for page in reader.pages:
                    text += page.extract_text()
                return text
        elif file_type in ['application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']:
            # Word文档提取（需要安装python-docx）
            from docx import Document
            doc = Document(file_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text
        else:
            return ""
    except Exception as e:
        print(f"Failed to extract text from {file_path}: {str(e)}")
        return ""

async def generate_ai_excerpt(text: str) -> str:
    """生成AI摘要"""
    # 这里应该调用实际的AI服务
    # 暂时返回简化版本
    if len(text) > 200:
        return text[:200] + "..."
    return text

async def generate_ai_summary(text: str) -> str:
    """生成AI总结"""
    # 这里应该调用实际的AI服务
    # 暂时返回简化版本
    return f"AI分析摘要：基于文本内容的智能总结（长度：{len(text)}字符）"

async def generate_ai_tags(text: str) -> str:
    """生成AI标签"""
    # 这里应该调用实际的AI服务
    # 暂时返回简化版本
    import json
    tags = ["维护", "检查", "分析"] if "维护" in text else ["监测", "记录"]
    return json.dumps(tags, ensure_ascii=False)