from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import io
import json
import os
from datetime import datetime
from ..schemas.database_models import DetectionTask, ParagraphResult, User
from ..utils.database import get_db
from ..services.auth import get_current_user
from ..schemas.models import TaskStatus
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib
import numpy as np
from matplotlib.font_manager import FontProperties, findfont

# 创建 fonts 目录，以便后续添加内嵌字体
fonts_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'fonts')
os.makedirs(fonts_dir, exist_ok=True)

router = APIRouter()

@router.get("/report/{task_id}")
async def get_report(
    task_id: str,
    format: str = "pdf",  # 支持 pdf 或 json
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取检测报告
    """
    # 查询任务
    task = db.query(DetectionTask).filter(DetectionTask.id == task_id).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="任务未找到")
    
    # 已移除权限检查，允许任何用户访问任何任务的报告
    
    # 检查任务状态
    if task.status != TaskStatus.COMPLETED.value:
        raise HTTPException(status_code=400, detail="任务尚未完成，无法生成报告")
    
    # 获取段落分析结果
    paragraph_results = db.query(ParagraphResult).filter(
        ParagraphResult.task_id == task_id
    ).all()
    
    # 根据请求的格式生成报告
    if format.lower() == "json":
        return generate_json_report(task, paragraph_results)
    else:  # PDF默认
        return await generate_pdf_report(task, paragraph_results)

def generate_json_report(task, paragraph_results):
    """生成JSON格式的报告"""
    ai_paragraphs = [p for p in paragraph_results if p.ai_generated]
    human_paragraphs = [p for p in paragraph_results if not p.ai_generated]
    
    report = {
        "task_id": task.id,
        "filename": task.filename,
        "report_date": datetime.now().isoformat(),
        "summary": {
            "ai_generated_percentage": task.ai_generated_percentage,
            "ai_paragraphs_count": len(ai_paragraphs),
            "human_paragraphs_count": len(human_paragraphs),
            "total_paragraphs_count": len(paragraph_results)
        },
        "details": [
            {
                "paragraph": p.paragraph,
                "ai_generated": p.ai_generated,
                "reason": p.reason
            } for p in paragraph_results
        ]
    }
    
    return report

async def generate_pdf_report(task, paragraph_results):
    """生成PDF格式的报告，包含美观的排版和视觉元素"""
    buffer = io.BytesIO()
    
    # 尝试获取支持中文的字体
    try:
        chinese_font_path = findfont(FontProperties(family='Arial Unicode MS'))
        chinese_font = FontProperties(fname=chinese_font_path)
    except Exception as e:
        print(f"获取字体时出错: {str(e)}")
        # 尝试其他可能支持中文的系统字体
        potential_chinese_fonts = ['SimHei', 'Microsoft YaHei', 'SimSun', 'Arial Unicode MS', 'Heiti SC', 'PingFang SC']
        chinese_font = None
        
        for font_name in potential_chinese_fonts:
            try:
                font_path = findfont(FontProperties(family=font_name))
                chinese_font = FontProperties(fname=font_path)
                break
            except Exception:
                continue
                
        if chinese_font is None:
            chinese_font = FontProperties()
    
    # 定义颜色方案
    primary_color = '#3366cc'  # 主色调：深蓝色
    secondary_color = '#f0f5ff'  # 次色调：浅蓝色
    accent_color = '#ff6633'  # 强调色：橙色
    text_color = '#333333'  # 文本颜色：深灰色
    
    # AI和人类内容的颜色
    ai_color = '#cc0000'  # AI内容：红色
    human_color = '#006600'  # 人类内容：绿色
    
    # 创建PDF文档
    with PdfPages(buffer) as pdf:
        # 配置matplotlib以支持中文
        plt.rcParams['pdf.fonttype'] = 42
        
        # 创建报告标题页
        plt.figure(figsize=(8.5, 11))
        plt.axis('off')
        
        # 添加页面装饰元素 - 顶部横幅
        plt.axhspan(0.95, 1.0, facecolor=primary_color, alpha=0.8)
        plt.axhspan(0.94, 0.95, facecolor=accent_color, alpha=0.9)
        
        # 添加底部装饰
        plt.axhspan(0.0, 0.05, facecolor=primary_color, alpha=0.2)
        
        # 添加报告标题 - 使用更加突出的样式
        plt.text(0.5, 0.92, f"AI文本检测报告", fontsize=24, fontproperties=chinese_font, 
                weight='bold', ha='center', color=primary_color)
        
        # 添加一条分隔线
        plt.axhline(y=0.88, xmin=0.1, xmax=0.9, color=primary_color, alpha=0.4, linewidth=2)
        
        # 创建一个信息框
        info_box = plt.Rectangle((0.1, 0.6), 0.8, 0.25, fill=True, 
                              facecolor=secondary_color, edgecolor=primary_color, 
                              linewidth=1.5, alpha=0.3)
        plt.gca().add_patch(info_box)
        
        # 添加报告基本信息 - 改进版式和颜色
        plt.text(0.15, 0.82, f"文件名:", fontsize=14, fontproperties=chinese_font, 
                weight='bold', color=primary_color)
        plt.text(0.35, 0.82, f"{task.filename}", fontsize=14, fontproperties=chinese_font, 
                color=text_color)
        
        plt.text(0.15, 0.77, f"检测日期:", fontsize=14, fontproperties=chinese_font, 
                weight='bold', color=primary_color)
        plt.text(0.35, 0.77, f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", fontsize=14, 
                fontproperties=chinese_font, color=text_color)
        
        plt.text(0.15, 0.72, f"任务ID:", fontsize=14, fontproperties=chinese_font, 
                weight='bold', color=primary_color)
        plt.text(0.35, 0.72, f"{task.id}", fontsize=14, fontproperties=chinese_font, 
                color=text_color)
        
        plt.text(0.15, 0.67, f"AI生成内容比例:", fontsize=14, fontproperties=chinese_font, 
                weight='bold', color=primary_color)
        plt.text(0.35, 0.67, f"{task.ai_generated_percentage}%", fontsize=14, 
                fontproperties=chinese_font, color=accent_color, weight='bold')
        
        # 添加AI/人类内容的图例
        legend_y = 0.5
        # AI内容图例
        plt.scatter([0.2], [legend_y], color=ai_color, s=100)
        plt.text(0.23, legend_y, "AI生成内容", va='center', fontsize=12, 
                fontproperties=chinese_font, color=ai_color)
        # 人类内容图例
        plt.scatter([0.2], [legend_y-0.05], color=human_color, s=100)
        plt.text(0.23, legend_y-0.05, "人类撰写内容", va='center', fontsize=12, 
                fontproperties=chinese_font, color=human_color)
        
        # 添加页脚
        plt.text(0.5, 0.03, "AI文本检测报告系统", fontsize=10, fontproperties=chinese_font, 
                ha='center', color=primary_color)
        plt.text(0.5, 0.01, f"生成时间: {datetime.now().strftime('%Y-%m-%d')}", 
                fontsize=8, ha='center', color=text_color)
        
        # 保存标题页
        pdf.savefig()
        plt.close()
        
        # 按顺序排列所有段落
        all_paragraphs = sorted(paragraph_results, key=lambda p: p.id)
        
        # 创建内容页
        plt.figure(figsize=(8.5, 11))
        plt.axis('off')
        
        # 添加页面装饰元素 - 顶部横幅
        plt.axhspan(0.95, 1.0, facecolor=primary_color, alpha=0.8)
        plt.axhspan(0.94, 0.95, facecolor=accent_color, alpha=0.9)
        
        # 添加底部装饰
        plt.axhspan(0.0, 0.05, facecolor=primary_color, alpha=0.2)
        
        # 页面标题 - 更美观的样式
        plt.text(0.5, 0.92, "文章内容分析", fontsize=20, fontproperties=chinese_font, 
                weight='bold', ha='center', color=primary_color)
        
        # 添加一条分隔线
        plt.axhline(y=0.9, xmin=0.05, xmax=0.95, color=primary_color, alpha=0.4, linewidth=2)
        
        # 添加说明
        content_y = 0.87
        plt.text(0.05, content_y, "以下是文章各段落内容及分析:", fontsize=12, 
                fontproperties=chinese_font, color=text_color)
        content_y -= 0.03
        
        # 显示所有段落的文本内容
        for i, p in enumerate(all_paragraphs):
            # 如果当前页面空间不足，创建新页面
            if content_y < 0.1:
                # 添加页脚
                plt.text(0.5, 0.03, "AI文本检测报告系统", fontsize=10, fontproperties=chinese_font, 
                        ha='center', color=primary_color)
                plt.text(0.5, 0.01, f"第 {pdf.get_pagecount()+1} 页", 
                        fontsize=8, ha='center', color=text_color)
                
                pdf.savefig()
                plt.close()
                plt.figure(figsize=(8.5, 11))
                plt.axis('off')
                
                # 添加页面装饰元素 - 顶部横幅
                plt.axhspan(0.95, 1.0, facecolor=primary_color, alpha=0.8)
                plt.axhspan(0.94, 0.95, facecolor=accent_color, alpha=0.9)
                
                # 添加底部装饰
                plt.axhspan(0.0, 0.05, facecolor=primary_color, alpha=0.2)
                
                content_y = 0.92
                
                # 添加继续标记
                plt.text(0.5, 0.92, f"文章内容分析 (续)", fontsize=18, fontproperties=chinese_font, 
                        weight='bold', ha='center', color=primary_color)
                plt.axhline(y=0.9, xmin=0.05, xmax=0.95, color=primary_color, alpha=0.4, linewidth=2)
                content_y = 0.87
            
            # 确定段落的颜色
            para_color = ai_color if p.ai_generated else human_color
            status_text = "AI生成" if p.ai_generated else "人类撰写"
            
            # 为段落标题创建一个带颜色的背景框
            header_height = 0.035
            header_rect = plt.Rectangle((0.05, content_y - header_height + 0.005), 0.9, header_height, 
                                   fill=True, facecolor=secondary_color, edgecolor=para_color, 
                                   linewidth=1.5, alpha=0.3)
            plt.gca().add_patch(header_rect)
            
            # 显示段落编号和AI生成状态 - 增加颜色区分
            plt.text(0.07, content_y - 0.025, f"段落 {i+1}", fontsize=12, weight='bold', 
                   fontproperties=chinese_font, color=text_color, va='center')
            plt.text(0.2, content_y - 0.025, f"({status_text})", fontsize=12, weight='bold', 
                   fontproperties=chinese_font, color=para_color, va='center')
            
            content_y -= header_height + 0.01
            
            # 为段落内容创建一个轻微背景
            # 估算段落内容的行数
            paragraph_text = p.paragraph
            lines = paragraph_text.split('\n')
            estimated_lines = 0
            for line in lines:
                estimated_lines += max(1, len(line) // 100 + (1 if len(line) % 100 > 0 else 0))
            
            content_height = estimated_lines * 0.035 + 0.01
            
            # 创建一个适应内容的背景框，给予轻微的颜色区分
            content_rect = plt.Rectangle((0.07, content_y - content_height), 0.86, content_height + 0.005, 
                                    fill=True, facecolor='white', edgecolor=para_color, 
                                    linewidth=1, alpha=0.2)
            plt.gca().add_patch(content_rect)
            
            # 显示段落内容 - 增大字体并扩宽显示区域
            for line in lines:
                # 增大每行字符数到100个
                while line:
                    display_line = line[:100]
                    line = line[100:]
                    
                    # 如果当前页面空间不足，创建新页面
                    if content_y < 0.1:
                        # 添加页脚
                        plt.text(0.5, 0.03, "AI文本检测报告系统", fontsize=10, fontproperties=chinese_font, 
                                ha='center', color=primary_color)
                        plt.text(0.5, 0.01, f"第 {pdf.get_pagecount()+1} 页", 
                                fontsize=8, ha='center', color=text_color)
                        
                        pdf.savefig()
                        plt.close()
                        plt.figure(figsize=(8.5, 11))
                        plt.axis('off')
                        
                        # 添加页面装饰元素 - 顶部横幅
                        plt.axhspan(0.95, 1.0, facecolor=primary_color, alpha=0.8)
                        plt.axhspan(0.94, 0.95, facecolor=accent_color, alpha=0.9)
                        
                        # 添加底部装饰
                        plt.axhspan(0.0, 0.05, facecolor=primary_color, alpha=0.2)
                        
                        # 添加继续标记
                        plt.text(0.5, 0.92, f"文章内容分析 (续)", fontsize=18, fontproperties=chinese_font, 
                                weight='bold', ha='center', color=primary_color)
                        plt.axhline(y=0.9, xmin=0.05, xmax=0.95, color=primary_color, alpha=0.4, linewidth=2)
                        content_y = 0.87
                        
                        # 重新绘制段落标题
                        header_rect = plt.Rectangle((0.05, content_y - header_height + 0.005), 0.9, header_height, 
                                               fill=True, facecolor=secondary_color, edgecolor=para_color, 
                                               linewidth=1.5, alpha=0.3)
                        plt.gca().add_patch(header_rect)
                        
                        plt.text(0.07, content_y - 0.025, f"段落 {i+1} (续)", fontsize=12, weight='bold', 
                               fontproperties=chinese_font, color=text_color, va='center')
                        plt.text(0.25, content_y - 0.025, f"({status_text})", fontsize=12, weight='bold', 
                               fontproperties=chinese_font, color=para_color, va='center')
                        
                        content_y -= header_height + 0.01
                        
                        # 创建新的背景框
                        remaining_lines = 0
                        if line:  # 如果当前行还有剩余内容
                            remaining_lines += max(1, len(line) // 100 + (1 if len(line) % 100 > 0 else 0))
                        # 计算剩余行数
                        for next_line in lines[lines.index(paragraph_text.split('\n')[lines.index(line) if line else 0])+1:]:
                            remaining_lines += max(1, len(next_line) // 100 + (1 if len(next_line) % 100 > 0 else 0))
                        
                        new_content_height = remaining_lines * 0.035 + 0.01
                        content_rect = plt.Rectangle((0.07, content_y - new_content_height), 0.86, new_content_height + 0.005, 
                                                fill=True, facecolor='white', edgecolor=para_color, 
                                                linewidth=1, alpha=0.2)
                        plt.gca().add_patch(content_rect)
                    
                    # 增大字体，优化行间距
                    plt.text(0.08, content_y, display_line, fontsize=11, fontproperties=chinese_font, 
                           color=text_color)
                    content_y -= 0.035
            
            # 显示分析原因（如果有）
            if p.reason:
                # 添加一定的间距
                content_y -= 0.01
                
                # 为分析原因创建一个背景框
                reason_height = 0.08
                reason_rect = plt.Rectangle((0.07, content_y - reason_height + 0.01), 0.86, reason_height, 
                                       fill=True, facecolor=secondary_color, edgecolor=para_color, 
                                       linewidth=1, alpha=0.15)
                plt.gca().add_patch(reason_rect)
                
                # 添加原因标题
                plt.text(0.08, content_y - 0.02, "分析原因:", fontsize=10, weight='bold',
                       fontproperties=chinese_font, color=para_color)
                
                # 添加原因内容
                plt.text(0.2, content_y - 0.02, f"{p.reason}", fontsize=10,
                       fontproperties=chinese_font, color=text_color)
                
                content_y -= reason_height + 0.02
            else:
                content_y -= 0.03
            
            # 添加段落之间的间距
            content_y -= 0.03
        
        # 添加页脚
        plt.text(0.5, 0.03, "AI文本检测报告系统", fontsize=10, fontproperties=chinese_font, 
                ha='center', color=primary_color)
        plt.text(0.5, 0.01, f"第 {pdf.get_pagecount()+1} 页", 
                fontsize=8, ha='center', color=text_color)
        
        # 保存最后一页
        pdf.savefig()
        plt.close()
    
    # 准备响应
    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=report_{task.id}.pdf"}
    ) 