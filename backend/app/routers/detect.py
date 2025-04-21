from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from ..schemas.models import DetectionResult, TaskStatus, ParagraphAnalysis, DetailedAnalysisResult
from ..schemas.database_models import DetectionTask, ParagraphResult, User
from ..utils.database import get_db
from ..services.file_service import extract_text, clean_up_task_files
from ..services.ai_detection_service import detect_ai_content
from ..services.auth import get_current_user
from typing import List
from ..services.detection_metrics import detection_metrics
import json

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
        
        # 构建详细结果
        details = []
        for p in paragraph_results:
            # 解析JSON格式的指标数据
            metrics_data = {}
            if p.metrics_data:
                try:
                    metrics_data = json.loads(p.metrics_data)
                except Exception as e:
                    print(f"解析指标数据失败: {str(e)}")
            
            # 创建包含详细指标的段落分析对象
            details.append(ParagraphAnalysis(
                paragraph=p.paragraph,
                ai_generated=p.ai_generated,
                reason=p.reason,
                confidence=p.confidence,
                metrics=metrics_data
            ))
        
        # 解析整体分析数据
        overall_analysis = None
        if task.overall_perplexity or task.overall_burstiness or hasattr(task, 'overall_analysis_result'):
            try:
                # 尝试使用新格式（如果数据库已更新）
                if hasattr(task, 'overall_analysis_result') and task.overall_analysis_result:
                    # 解析JSON数据
                    analysis_data = json.loads(task.overall_analysis_result)
                    overall_analysis = DetailedAnalysisResult(
                        is_ai_generated=analysis_data.get("is_ai_generated"),
                        confidence=analysis_data.get("confidence"),
                        reason=analysis_data.get("reason"),
                        models_results=analysis_data.get("models_results"),
                        # 保持向后兼容
                        perplexity=task.overall_perplexity,
                        burstiness=task.overall_burstiness
                    )
                else:
                    # 旧格式
                    syntax_metrics = json.loads(task.overall_syntax_analysis) if task.overall_syntax_analysis else None
                    coherence_metrics = json.loads(task.overall_coherence_analysis) if task.overall_coherence_analysis else None
                    style_metrics = json.loads(task.overall_style_analysis) if task.overall_style_analysis else None
                    
                    overall_analysis = DetailedAnalysisResult(
                        perplexity=task.overall_perplexity,
                        burstiness=task.overall_burstiness,
                        syntax_metrics=syntax_metrics,
                        coherence_metrics=coherence_metrics,
                        style_metrics=style_metrics
                    )
            except Exception as e:
                print(f"解析整体分析数据失败: {str(e)}")
        
        return DetectionResult(
            task_id=task_id,
            status=TaskStatus.COMPLETED,
            ai_generated_percentage=task.ai_generated_percentage,
            details=details,
            overall_analysis=overall_analysis
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
        
        # 分析整体文本
        overall_analysis = await detection_metrics.analyze_text(text)
        
        # 保存结果到数据库
        # 更新任务
        task.ai_generated_percentage = ai_percentage
        task.status = TaskStatus.COMPLETED.value
        
        # 保存整体分析结果
        # 提取特征分析数据，如果有的话
        metrics_data = {}
        models_results = overall_analysis.get("models_results", {})
        if "特征分析" in models_results and "metrics" in models_results["特征分析"]:
            metrics_data = models_results["特征分析"]["metrics"]
        
        # 保存兼容性字段
        task.overall_perplexity = metrics_data.get("perplexity", 0.0)
        task.overall_burstiness = metrics_data.get("burstiness", 0.0)
        
        # 保存新字段
        task.overall_syntax_analysis = json.dumps(metrics_data.get("syntax_analysis", {}), ensure_ascii=False)
        task.overall_coherence_analysis = json.dumps({}, ensure_ascii=False)  # 不再使用
        task.overall_style_analysis = json.dumps(metrics_data.get("style_analysis", {}), ensure_ascii=False)
        
        # 添加新字段到任务表（如果数据库已更新）
        if hasattr(task, 'overall_analysis_result'):
            task.overall_analysis_result = json.dumps(overall_analysis, ensure_ascii=False)
        
        # 保存段落分析结果
        for result in paragraph_results:
            # 准备详细指标数据
            metrics_data = {}
            if hasattr(result, 'metrics') and result.metrics:
                metrics_data = result.metrics
            
            # 创建段落结果
            paragraph = ParagraphResult(
                task_id=task_id,
                paragraph=result.paragraph,
                ai_generated=result.ai_generated,
                reason=result.reason,
                confidence=result.confidence if hasattr(result, 'confidence') else None,
                perplexity=metrics_data.get('perplexity', 0.0) if metrics_data else None,
                burstiness=metrics_data.get('burstiness', 0.0) if metrics_data else None,
                metrics_data=json.dumps(metrics_data, ensure_ascii=False) if metrics_data else None
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