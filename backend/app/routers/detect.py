from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from ..schemas.models import DetectionResult, TaskStatus, ParagraphAnalysis, DetailedAnalysisResult
from ..schemas.database_models import DetectionTask, ParagraphResult, User
from ..utils.database import get_db, SessionLocal
from ..services.file_service import extract_text, clean_up_task_files, UPLOAD_DIR
from ..services.ai_detection_service import detect_ai_content, detect_ai_content_comprehensive
from ..services.auth import get_current_user
from typing import List, Dict, Any
import json
import asyncio
import os

router = APIRouter()

@router.get("/detect/{task_id}", response_model=DetectionResult)
async def get_detection_status(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取AI检测任务状态和结果"""
    # 查询任务
    task = db.query(DetectionTask).filter(
        DetectionTask.id == task_id,
        DetectionTask.owner_id == current_user.id
    ).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="检测任务不存在")
    
    # 如果任务已完成，返回结果
    if task.status == TaskStatus.COMPLETED.value:
        # 获取段落分析结果
        paragraph_results = db.query(ParagraphResult).filter(
            ParagraphResult.task_id == task_id
        ).all()
        
        # 构建详细结果
        details = []
        for p in paragraph_results:
            # 创建包含详细指标的段落分析对象
            additional_metrics = {}
            if p.metrics_data:
                try:
                    additional_metrics = json.loads(p.metrics_data)
                except:
                    pass
                    
            details.append(ParagraphAnalysis(
                paragraph=p.paragraph,
                ai_generated=p.ai_generated,
                reason=p.reason,
                confidence=p.confidence if p.confidence else None,
                perplexity=p.perplexity if p.perplexity else None,
                ai_likelihood=p.ai_likelihood if p.ai_likelihood else None,
                additional_metrics=additional_metrics
            ))
        
        # 解析整体分析数据
        overall_analysis = None
        if task.overall_analysis_result:
            try:
                overall_analysis = json.loads(task.overall_analysis_result)
                # 确保有段落数量信息
                if "segment_count" not in overall_analysis:
                    overall_analysis["segment_count"] = len(details)
                
                # 处理困惑度字段名不一致的情况
                if "avg_perplexity" in overall_analysis and "perplexity" not in overall_analysis:
                    overall_analysis["perplexity"] = overall_analysis["avg_perplexity"]
                elif "perplexity" not in overall_analysis:
                    overall_analysis["perplexity"] = 0
                
                # 确保ai_percentage字段存在并与数据库一致
                if "ai_percentage" not in overall_analysis or overall_analysis["ai_percentage"] is None:
                    # 如果overall_analysis中没有ai_percentage字段，使用数据库中保存的值
                    overall_analysis["ai_percentage"] = task.ai_generated_percentage
                elif task.ai_generated_percentage is not None and task.ai_generated_percentage != overall_analysis["ai_percentage"]:
                    # 如果数据库和overall_analysis中的值不一致，优先使用数据库中保存的值
                    print(f"警告: ai_percentage不一致，数据库:{task.ai_generated_percentage}，overall_analysis:{overall_analysis['ai_percentage']}")
                    overall_analysis["ai_percentage"] = task.ai_generated_percentage
            except Exception as e:
                print(f"解析整体分析数据时出错: {str(e)}")
                # 创建最小的overall_analysis
                overall_analysis = {
                    "ai_percentage": task.ai_generated_percentage,
                    "perplexity": task.overall_perplexity if task.overall_perplexity else 0,
                    "segment_count": len(details),
                    "ai_likelihood": "未知（解析错误）"
                }
        else:
            # 如果没有整体分析数据，创建一个包含基本信息的分析结果
            overall_analysis = {
                "ai_percentage": task.ai_generated_percentage,
                "perplexity": task.overall_perplexity if task.overall_perplexity else 0,
                "segment_count": len(details),
                "ai_likelihood": "未知（无分析数据）"
            }
        
        return {
            "task_id": task.id,
            "status": task.status,
            "filename": task.filename,
            "ai_generated_percentage": task.ai_generated_percentage,
            "details": details,
            "overall_analysis": overall_analysis,
            "created_at": task.created_at,
            "updated_at": task.updated_at
        }
    
    # 如果任务仍在处理中
    return {
        "task_id": task.id,
        "status": task.status,
        "filename": task.filename,
        "ai_generated_percentage": None,
        "details": [],
        "overall_analysis": None,
        "created_at": task.created_at,
        "updated_at": task.updated_at
    }

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
        perform_detection_wrapper,
        task_id=task_id,
        filename=task.filename
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

def perform_detection_wrapper(task_id: str, filename: str):
    """
    后台任务包装器，调用异步检测函数
    """
    # 创建事件循环
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # 执行异步任务
    try:
        loop.run_until_complete(perform_detection(task_id, filename))
    finally:
        loop.close()

async def perform_detection(task_id: str, filename: str):
    """执行AI内容检测的后台任务"""
    db = SessionLocal()
    
    try:
        # 获取任务
        task = db.query(DetectionTask).filter(DetectionTask.id == task_id).first()
        if not task:
            print(f"任务 {task_id} 不存在")
            return
        
        # 更新任务状态为处理中
        task.status = TaskStatus.PROCESSING.value
        db.commit()
        
        # 读取文件内容
        file_path = os.path.join(UPLOAD_DIR, task_id, filename)
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 调用AI检测服务进行综合分析
        detection_result = await detect_ai_content_comprehensive(content)
        
        # 确保ai_percentage有值且在0-100之间
        ai_percentage = detection_result.get("ai_percentage", 0)
        if ai_percentage is None:
            print("警告: AI百分比为None，设置为0")
            ai_percentage = 0
        # 确保ai_percentage在有效范围内
        ai_percentage = max(0, min(100, ai_percentage))
        
        # 更新任务状态和结果
        task.status = TaskStatus.COMPLETED.value
        task.ai_generated_percentage = ai_percentage
        
        # 确保avg_perplexity有值
        avg_perplexity = detection_result.get("avg_perplexity", 0)
        if avg_perplexity is None:
            print("警告: 平均困惑度为None，设置为0")
            avg_perplexity = 0
        task.overall_perplexity = avg_perplexity
        
        # 构建整体分析结果
        overall_analysis = {
            "ai_percentage": ai_percentage,
            "perplexity": avg_perplexity,
            "style_consistency": detection_result.get("style_consistency", 0) or 0,
            "ai_likelihood": detection_result.get("ai_likelihood", "未知") or "未知",
            "segment_count": detection_result.get("segment_count", len(detection_result.get("detailed_analysis", [])))
        }
        
        # 将整体分析保存到数据库
        task.overall_analysis_result = json.dumps(overall_analysis)
        
        # 保存段落分析结果
        for result in detection_result.get("detailed_analysis", []):
            # 准备额外的指标数据
            metrics_data = {}
            if hasattr(result, 'additional_metrics') and result.additional_metrics:
                metrics_data = result.additional_metrics
            
            # 创建段落结果
            paragraph = ParagraphResult(
                task_id=task_id,
                paragraph=result.paragraph,
                ai_generated=result.ai_generated,
                reason=result.reason,
                confidence=result.confidence if hasattr(result, 'confidence') else None,
                perplexity=result.perplexity if hasattr(result, 'perplexity') else None,
                ai_likelihood=result.ai_likelihood if hasattr(result, 'ai_likelihood') else None,
                metrics_data=json.dumps(metrics_data) if metrics_data else None
            )
            db.add(paragraph)
        
        db.commit()
        print(f"任务 {task_id} 检测完成，AI生成内容百分比: {ai_percentage}%")
        
        # 检测完成后清理文件
        clean_up_task_files(task_id)
        
    except Exception as e:
        print(f"检测过程中出错: {str(e)}")
        
        # 更新任务状态为失败
        try:
            task = db.query(DetectionTask).filter(DetectionTask.id == task_id).first()
            if task:
                task.status = TaskStatus.FAILED.value
                db.commit()
        except Exception as inner_e:
            print(f"更新任务状态时出错: {str(inner_e)}")
            
        # 清理文件
        clean_up_task_files(task_id)
    finally:
        # 确保关闭数据库会话
        db.close() 