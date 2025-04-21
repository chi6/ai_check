from fastapi import APIRouter, File, UploadFile, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from ..schemas.models import UploadResponse, TaskStatus
from ..schemas.database_models import DetectionTask, User
from ..utils.database import get_db
from ..services.file_service import save_upload_file, validate_file
from ..services.auth import get_current_user
import uuid
import os

router = APIRouter()

@router.post("/upload", response_model=UploadResponse)
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    上传论文文件进行AI内容检测
    """
    # 验证文件
    if not validate_file(file):
        raise HTTPException(status_code=400, detail="不支持的文件格式，请上传PDF、DOCX或TXT文件")
    
    # 获取文件大小
    file.file.seek(0, os.SEEK_END)
    file_size = file.file.tell()
    file.file.seek(0)  # 重置文件指针
    
    # 检查文件大小限制 (50MB)
    if file_size > 50 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="文件大小超过限制（最大50MB）")
    
    # 创建检测任务
    task_id = str(uuid.uuid4())
    
    # 保存文件
    try:
        filename = await save_upload_file(task_id, file)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")
    
    # 保存任务信息到数据库 - 使用访客用户ID关联所有上传任务
    task = DetectionTask(
        id=task_id,
        filename=filename,
        file_size=file_size,
        status=TaskStatus.UPLOADED.value,
        owner_id=current_user.id  # 此处不需要修改，因为当前用户已经是访客用户
    )
    
    db.add(task)
    db.commit()
    db.refresh(task)
    
    # 添加异步处理任务
    # (此处将在detect路由中实现)
    
    return UploadResponse(
        task_id=task_id,
        status=TaskStatus.UPLOADED,
        filename=filename,
        file_size=file_size
    ) 