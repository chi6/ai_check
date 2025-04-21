from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from ..schemas.models import DetectionResult, TaskStatus, ParagraphAnalysis
from ..schemas.database_models import DetectionTask, ParagraphResult, User
from ..utils.database import get_db
from ..services.file_service import extract_text, clean_up_task_files
from ..services.ai_detection_service import detect_ai_content
from ..services.auth import get_current_user
from typing import List

router = APIRouter()

@router.get("/detect/{task_id}", response_model=DetectionResult)
async def get_detection_status(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取检测任务的状态及结果
    """
    # 查询任务
    task = db.query(DetectionTask).filter(DetectionTask.id == task_id).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="任务未找到")
    
    # 如果任务已完成，返回结果
    if task.status == TaskStatus.COMPLETED.value:
        # 获取段落分析结果
        paragraph_results = db.query(ParagraphResult).filter(
            ParagraphResult.task_id == task_id
        ).all()
        
        details = [
            ParagraphAnalysis(
                paragraph=p.paragraph,
                ai_generated=p.ai_generated,
                reason=p.reason
            ) for p in paragraph_results
        ]
        
        return DetectionResult(
            task_id=task_id,
            status=TaskStatus.COMPLETED,
            ai_generated_percentage=task.ai_generated_percentage,
            details=details
        )
    
    # 返回当前状态
    return DetectionResult(
        task_id=task_id,
        status=TaskStatus(task.status)
    )

@router.post("/detect/{task_id}/start")
async def start_detection(
    task_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    开始AI内容检测任务
    """
    # 查询任务
    task = db.query(DetectionTask).filter(DetectionTask.id == task_id).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="任务未找到")
    
    # 检查任务状态
    if task.status != TaskStatus.UPLOADED.value:
        raise HTTPException(status_code=400, detail="任务状态不正确，无法开始检测")
    
    # 更新任务状态
    task.status = TaskStatus.PROCESSING.value
    db.commit()
    
    # 添加后台任务执行检测
    background_tasks.add_task(
        perform_detection,
        task_id=task_id,
        filename=task.filename,
        db=db
    )
    
    return {"message": "检测任务已启动"}

@router.delete("/detect/{task_id}/cancel")
async def cancel_detection(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    取消正在进行的检测任务
    """
    # 查询任务
    task = db.query(DetectionTask).filter(DetectionTask.id == task_id).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="任务未找到")
    
    # 检查任务状态
    if task.status != TaskStatus.PROCESSING.value:
        raise HTTPException(status_code=400, detail="任务不在处理中，无法取消")
    
    # 更新任务状态
    task.status = TaskStatus.FAILED.value
    db.commit()
    
    # 清理任务文件
    clean_up_task_files(task_id)
    
    return {"message": "检测任务已取消"}

async def perform_detection(task_id: str, filename: str, db: Session):
    """
    执行AI内容检测的后台任务
    """
    try:
        # 获取任务
        task = db.query(DetectionTask).filter(DetectionTask.id == task_id).first()
        if not task or task.status != TaskStatus.PROCESSING.value:
            return
        
        # 提取文本
        text = extract_text(task_id, filename)
        if not text:
            raise Exception("无法从文件中提取文本")
        
        # 检测AI内容
        ai_percentage, paragraph_results = await detect_ai_content(text)
        
        # 保存结果到数据库
        # 更新任务
        task.ai_generated_percentage = ai_percentage
        task.status = TaskStatus.COMPLETED.value
        
        # 保存段落分析结果
        for result in paragraph_results:
            paragraph = ParagraphResult(
                task_id=task_id,
                paragraph=result.paragraph,
                ai_generated=result.ai_generated,
                reason=result.reason
            )
            db.add(paragraph)
        
        db.commit()
        
        # 检测完成后清理文件
        clean_up_task_files(task_id)
        
    except Exception as e:
        print(f"检测过程中出错: {str(e)}")
        
        # 更新任务状态为失败
        if task:
            task.status = TaskStatus.FAILED.value
            db.commit()
            
        # 清理文件
        clean_up_task_files(task_id) 