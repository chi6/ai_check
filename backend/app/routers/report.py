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
import matplotlib
import matplotlib.pyplot as plt
import base64
from jinja2 import Template

# 创建 fonts 目录，以便后续添加内嵌字体
fonts_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'fonts')
os.makedirs(fonts_dir, exist_ok=True)

router = APIRouter()

@router.get("/report/{task_id}")
async def get_report(
    task_id: str,
    format: str = "html",  # 支持 json, html, text
    template: str = "standard",  # 支持 standard, detailed, simple
    includeChart: bool = True,
    includeDetails: bool = True,
    includeOriginalText: bool = False,
    includeMetadata: bool = True,
    includeHeaderFooter: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取检测报告
    
    参数：
    - format: 报告格式（json, html, text）
    - template: 报告模板（standard, detailed, simple）
    - includeChart: 是否包含图表
    - includeDetails: 是否包含详细分析结果
    - includeOriginalText: 是否包含原始文本
    - includeMetadata: 是否包含元数据
    - includeHeaderFooter: 是否包含页眉页脚
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
    
    # 创建选项对象
    options = {
        "template": template,
        "includeChart": includeChart,
        "includeDetails": includeDetails,
        "includeOriginalText": includeOriginalText,
        "includeMetadata": includeMetadata,
        "includeHeaderFooter": includeHeaderFooter,
    }
    
    # 根据请求的格式生成报告
    if format.lower() == "json":
        return generate_json_report(task, paragraph_results, options)
    elif format.lower() == "html":
        return await generate_html_report(task, paragraph_results, options)
    elif format.lower() == "text":
        return await generate_text_report(task, paragraph_results, options)
    else:
        # 默认返回HTML格式
        return await generate_html_report(task, paragraph_results, options)

def generate_json_report(task, paragraph_results, options):
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

async def generate_html_report(task, paragraph_results, options):
    """生成HTML格式的报告，包含交互式图表和样式"""
    matplotlib.use('Agg')
    
    # 配置matplotlib以支持中文
    import matplotlib.font_manager as fm
    
    # 尝试设置中文字体
    try:
        # 检查系统字体
        system_fonts = fm.findSystemFonts()
        
        # 优先查找常见的中文字体
        chinese_fonts = ['SimHei', 'Microsoft YaHei', 'PingFang SC', 'Hiragino Sans GB', 'Heiti SC', 'STHeiti', 'SimSun']
        chinese_font_found = False
        
        # 设置中文字体
        for font_name in chinese_fonts:
            # 在字体路径中查找匹配的字体文件
            matching_fonts = [f for f in system_fonts if font_name.lower() in f.lower()]
            if matching_fonts:
                plt.rcParams['font.family'] = 'sans-serif'
                plt.rcParams['font.sans-serif'] = [font_name] + plt.rcParams['font.sans-serif']
                chinese_font_found = True
                print(f"使用中文字体: {font_name}")
                break
                
        # 如果找不到中文字体，使用内置的中文字体
        if not chinese_font_found:
            # 尝试使用 fonts_dir 中的字体
            noto_font_path = os.path.join(fonts_dir, 'NotoSansCJKsc-Regular.otf')
            if os.path.exists(noto_font_path):
                noto_font = fm.FontProperties(fname=noto_font_path)
                plt.rcParams['font.family'] = 'sans-serif'
                plt.rcParams['font.sans-serif'] = ['Noto Sans CJK SC'] + plt.rcParams['font.sans-serif']
                print(f"使用 Noto Sans CJK SC 字体")
            else:
                # 使用备选方案处理中文标签
                print("警告: 未找到支持中文的字体，将使用英文替代")
                plt.rcParams['axes.unicode_minus']=False  # 正确显示负号
    except Exception as e:
        print(f"设置中文字体时出现错误: {str(e)}")
    
    # 如果是从/html端点调用，设置标志
    if options.get("from_html_endpoint") is None:
        # 检查调用栈来确定是否直接从html端点调用
        import inspect
        caller_name = inspect.currentframe().f_back.f_code.co_name
        if caller_name == "get_html_report":
            options["from_html_endpoint"] = True
        else:
            options["from_html_endpoint"] = False
    
    # 准备数据
    ai_paragraphs = [p for p in paragraph_results if p.ai_generated]
    human_paragraphs = [p for p in paragraph_results if not p.ai_generated]
    
    ai_percentage = task.ai_generated_percentage
    human_percentage = 100 - ai_percentage
    
    # 创建图表（如果选项允许）
    pie_chart_base64 = None
    if options.get("includeChart", True):
        # 创建饼图
        plt.figure(figsize=(5, 5))
        
        # 解决中文标签问题 - 如果找不到中文字体，使用英文标签
        if chinese_font_found or os.path.exists(os.path.join(fonts_dir, 'NotoSansCJKsc-Regular.otf')):
            labels = ['AI生成内容', '人类撰写内容']
        else:
            labels = ['AI Generated', 'Human Written']
            
        plt.pie(
            [ai_percentage, human_percentage],
            labels=labels,
            colors=['#ff4d4f', '#52c41a'],
            autopct='%1.1f%%',
            startangle=90
        )
        plt.axis('equal')
        
        # 使用英文标题避免中文问题
        plt.title('AI Content Detection Results' if not chinese_font_found else 'AI内容检测结果')
        
        # 转换为base64编码以嵌入HTML
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=100)
        buffer.seek(0)
        pie_chart_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        plt.close()
    
    # 提取整体分析结果
    overall_analysis = None
    if task.overall_analysis_result:
        try:
            if isinstance(task.overall_analysis_result, str):
                overall_analysis = json.loads(task.overall_analysis_result)
            else:
                overall_analysis = task.overall_analysis_result
            
            # 兼容性处理：确保字段名一致性
            if overall_analysis:
                # 处理困惑度字段名不一致的情况
                if "avg_perplexity" in overall_analysis and "perplexity" not in overall_analysis:
                    overall_analysis["perplexity"] = overall_analysis["avg_perplexity"]
                elif "perplexity" not in overall_analysis:
                    # 如果两个字段都不存在，设置默认值
                    overall_analysis["perplexity"] = 0
        except:
            pass
    
    # 选择要显示的段落
    displayed_paragraphs = []
    if options.get("includeDetails", True):
        displayed_paragraphs = paragraph_results
    elif ai_paragraphs:
        # 如果不包含详细信息但有AI段落，至少显示部分AI段落
        displayed_paragraphs = ai_paragraphs[:min(5, len(ai_paragraphs))]
    
    # 读取HTML模板
    html_template = Template("""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AI内容检测报告</title>
        <style>
            body {
                font-family: 'Arial', sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
                background-color: #f5f5f5;
            }
            .header {
                text-align: center;
                padding: 20px 0;
                border-bottom: 2px solid #1890ff;
                margin-bottom: 30px;
                background-color: #fff;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            .report-title {
                color: #1890ff;
                margin: 0;
                font-size: 2.2em;
            }
            .metadata {
                display: flex;
                flex-wrap: wrap;
                justify-content: space-between;
                margin: 20px 0;
                background-color: #fff;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            .metadata-item {
                margin: 10px 0;
                flex: 1 0 30%;
                min-width: 200px;
            }
            .metadata-label {
                font-weight: bold;
                color: #1890ff;
            }
            .summary {
                display: flex;
                flex-wrap: wrap;
                margin: 30px 0;
            }
            .chart-container {
                flex: 1 0 300px;
                background-color: #fff;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                margin-right: 20px;
                margin-bottom: 20px;
            }
            .stats-container {
                flex: 1 0 300px;
                background-color: #fff;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                margin-bottom: 20px;
            }
            .paragraph {
                background-color: #fff;
                padding: 20px;
                margin: 20px 0;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                position: relative;
            }
            .paragraph-ai {
                border-left: 5px solid #ff4d4f;
            }
            .paragraph-human {
                border-left: 5px solid #52c41a;
            }
            .paragraph-tag {
                display: inline-block;
                padding: 5px 12px;
                border-radius: 15px;
                color: white;
                font-weight: bold;
                margin-right: 10px;
                font-size: 0.9em;
            }
            .paragraph-tag-ai {
                background-color: #ff4d4f;
            }
            .paragraph-tag-human {
                background-color: #52c41a;
            }
            .metrics {
                display: flex;
                flex-wrap: wrap;
                margin-top: 15px;
                border-top: 1px dashed #ddd;
                padding-top: 15px;
            }
            .metric {
                margin-right: 15px;
                margin-bottom: 5px;
                padding: 5px 10px;
                background-color: #f9f9f9;
                border-radius: 5px;
                font-size: 0.85em;
            }
            .reason {
                margin-top: 15px;
                padding: 10px;
                background-color: #f0f5ff;
                border-radius: 5px;
                border-left: 3px solid #1890ff;
            }
            .overall-metrics {
                display: flex;
                flex-wrap: wrap;
                margin: 20px 0;
                justify-content: space-between;
            }
            .metric-card {
                flex: 1 0 28%;
                min-width: 200px;
                margin: 10px;
                padding: 15px;
                background-color: #fff;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                text-align: center;
            }
            .metric-value {
                font-size: 1.8em;
                font-weight: bold;
                margin: 10px 0;
            }
            .ai-high {
                color: #ff4d4f;
            }
            .ai-medium {
                color: #faad14;
            }
            .ai-low {
                color: #52c41a;
            }
            .footer {
                text-align: center;
                margin-top: 50px;
                padding: 20px;
                border-top: 1px solid #ddd;
                color: #888;
                font-size: 0.9em;
            }
            section {
                margin-bottom: 40px;
            }
            h2 {
                color: #1890ff;
                padding-bottom: 10px;
                border-bottom: 1px solid #ddd;
            }
            .alert {
                padding: 15px;
                border-radius: 8px;
                margin: 20px 0;
                font-weight: bold;
            }
            .alert-high {
                background-color: #fff1f0;
                border: 1px solid #ffccc7;
                color: #cf1322;
            }
            .alert-low {
                background-color: #f6ffed;
                border: 1px solid #b7eb8f;
                color: #389e0d;
            }
            .warning-message {
                background-color: #fff2e8;
                border: 1px solid #ffbb96;
                color: #d4380d;
                padding: 10px 15px;
                margin: 15px 0;
                border-radius: 4px;
                font-weight: bold;
            }
            @media (max-width: 768px) {
                .metadata-item {
                    flex: 1 0 100%;
                }
                .chart-container, .stats-container {
                    flex: 1 0 100%;
                    margin-right: 0;
                }
            }
        </style>
    </head>
    <body>
        <div class="header">
            <h1 class="report-title">AI内容检测报告</h1>
            <p>全面分析文本中的人工智能生成内容</p>
        </div>
        
        {% if options.includeMetadata %}
        <div class="metadata">
            <div class="metadata-item">
                <div class="metadata-label">文件名</div>
                <div>{{ task.filename }}</div>
            </div>
            <div class="metadata-item">
                <div class="metadata-label">任务ID</div>
                <div>{{ task.id }}</div>
            </div>
            <div class="metadata-item">
                <div class="metadata-label">检测时间</div>
                <div>{{ task.created_at.strftime('%Y-%m-%d %H:%M:%S') }}</div>
            </div>
            <div class="metadata-item">
                <div class="metadata-label">AI生成内容比例</div>
                <div><strong style="color: {% if ai_percentage > 50 %}#ff4d4f{% else %}#1890ff{% endif %}">{{ ai_percentage|round(1) }}%</strong></div>
            </div>
        </div>
        {% endif %}
        
        <div class="alert {% if ai_percentage > 50 %}alert-high{% else %}alert-low{% endif %}">
            {% if ai_percentage > 50 %}
            检测结果: 文本中包含较高比例的AI生成内容 ({{ ai_percentage|round(1) }}%)
            {% else %}
            检测结果: 文本中AI生成内容比例较低 ({{ ai_percentage|round(1) }}%)
            {% endif %}
        </div>
        
        <section>
            <h2>检测结果概览</h2>
            
            <div class="summary">
                {% if pie_chart_base64 and options.includeChart %}
                <div class="chart-container">
                    <h3>内容分布</h3>
                    <img src="data:image/png;base64,{{ pie_chart_base64 }}" alt="AI内容分布图" style="max-width: 100%;">
                </div>
                {% endif %}
                
                <div class="stats-container">
                    <h3>检测统计</h3>
                    <div style="margin: 15px 0;">
                        <div style="margin-bottom: 10px;"><strong>总段落数:</strong> {{ paragraph_results|length }}</div>
                        <div style="margin-bottom: 10px;"><strong>AI生成段落:</strong> {{ ai_paragraphs|length }} ({{ (ai_paragraphs|length / paragraph_results|length * 100)|round(1) if paragraph_results else 0 }}%)</div>
                        <div style="margin-bottom: 10px;"><strong>人类撰写段落:</strong> {{ human_paragraphs|length }} ({{ (human_paragraphs|length / paragraph_results|length * 100)|round(1) if paragraph_results else 0 }}%)</div>
                    </div>
                </div>
            </div>
            
            {% if overall_analysis %}
            <h3>整体分析指标</h3>
            <div class="overall-metrics">
                <div class="metric-card">
                    <div>平均困惑度</div>
                    <div class="metric-value {% if overall_analysis.perplexity < 20 %}ai-high{% elif overall_analysis.perplexity < 30 %}ai-medium{% else %}ai-low{% endif %}">
                        {{ overall_analysis.perplexity|round(2) }}
                    </div>
                    <div>
                        {% if overall_analysis.perplexity < 20 %}
                        偏低（疑似AI生成）
                        {% elif overall_analysis.perplexity < 30 %}
                        中等
                        {% else %}
                        正常
                        {% endif %}
                    </div>
                </div>
                
                <div class="metric-card">
                    <div>风格一致性</div>
                    <div class="metric-value {% if overall_analysis.style_consistency > 0.95 %}ai-high{% elif overall_analysis.style_consistency > 0.9 %}ai-medium{% else %}ai-low{% endif %}">
                        {{ overall_analysis.style_consistency|round(3) }}
                    </div>
                    <div>
                        {% if overall_analysis.style_consistency > 0.95 %}
                        过高（疑似AI生成）
                        {% elif overall_analysis.style_consistency > 0.9 %}
                        较高
                        {% else %}
                        正常
                        {% endif %}
                    </div>
                </div>
                
                <div class="metric-card">
                    <div>AI生成可能性</div>
                    <div class="metric-value {% if "高" in overall_analysis.ai_likelihood %}ai-high{% elif "中" in overall_analysis.ai_likelihood %}ai-medium{% else %}ai-low{% endif %}">
                        {{ overall_analysis.ai_likelihood }}
                    </div>
                </div>
            </div>
            {% endif %}
        </section>
        
        {% if displayed_paragraphs and (options.includeDetails or displayed_paragraphs|length > 0) %}
        <section>
            <h2>段落详细分析</h2>
            {% for p in displayed_paragraphs %}
            <div class="paragraph {% if p.ai_generated %}paragraph-ai{% else %}paragraph-human{% endif %}">
                <span class="paragraph-tag {% if p.ai_generated %}paragraph-tag-ai{% else %}paragraph-tag-human{% endif %}">
                    {% if p.ai_generated %}AI生成{% else %}人类撰写{% endif %}
                </span>
                
                {% if p.ai_likelihood %}
                <span class="paragraph-tag" style="background-color: 
                    {% if 'high' in p.ai_likelihood or '高' in p.ai_likelihood %}#ff4d4f
                    {% elif 'medium' in p.ai_likelihood or '中' in p.ai_likelihood %}#faad14
                    {% else %}#52c41a{% endif %};">
                    AI可能性: {{ p.ai_likelihood }}
                </span>
                {% endif %}
                
                <div style="margin-top: 15px; margin-bottom: 15px;">
                    {{ p.paragraph }}
                </div>
                
                <div class="metrics">
                    {% if p.perplexity is not none %}
                    <div class="metric">
                        困惑度: <strong style="color: 
                        {% if p.perplexity < 20 %}#ff4d4f
                        {% elif p.perplexity < 30 %}#faad14
                        {% else %}#52c41a{% endif %};">
                        {{ p.perplexity|round(2) }}</strong>
                    </div>
                    {% endif %}
                    
                    {% if p.confidence is not none %}
                    <div class="metric">
                        置信度: {{ (p.confidence * 100)|round(1) if p.confidence else 'N/A' }}%
                    </div>
                    {% endif %}
                </div>
                
                {% if p.reason %}
                <div class="reason">
                    <strong>分析原因:</strong> {{ p.reason }}
                </div>
                {% endif %}
            </div>
            {% endfor %}
        </section>
        {% endif %}
        
        <section>
            <h2>AI内容检测原理</h2>
            <div class="paragraph">
                <h3>困惑度分析</h3>
                <p>困惑度(Perplexity)是衡量语言模型预测文本难度的指标。AI生成的文本通常具有较低的困惑度，
                因为语言模型生成的文本往往更加可预测。人类撰写的文本则更加多变和不可预测，困惑度较高。</p>
                
                <h3>风格一致性分析</h3>
                <p>对文本各部分的风格一致性进行评估。AI生成的文本风格通常非常一致，
                而人类撰写的文本则风格略有变化。风格一致性过高可能表明是AI生成的内容。</p>
                
                <h3>语义内容审查</h3>
                <p>使用大型语言模型对文本内容进行分析，识别常见的AI生成特征，如模板化表达、缺乏个人见解或创造性思考等。</p>
                
                <div style="background-color: #fffbe6; border: 1px solid #ffe58f; padding: 10px; border-radius: 5px; margin-top: 20px;">
                    <strong>注意:</strong> 检测结果供参考，不应作为唯一判断依据。技术在不断发展，检测方法也在持续改进。
                </div>
            </div>
        </section>
        
        {% if options.includeHeaderFooter %}
        <div class="footer">
            <p>AI内容检测报告 - 生成于 {{ now.strftime('%Y-%m-%d %H:%M:%S') }}</p>
            <p>© AI文本检测系统</p>
        </div>
        {% endif %}
        
        {% if options.from_html_endpoint %}
        <div style="background-color: #e6f7ff; border: 1px solid #91d5ff; color: #1890ff; padding: 10px 15px; margin: 15px 0; border-radius: 4px;">
            <p><strong>提示:</strong> 您正在查看HTML格式的报告。如需其他格式，请使用报告下载按钮。</p>
        </div>
        {% endif %}
    </body>
    </html>
    """)
    
    # 渲染HTML
    html_content = html_template.render(
        task=task,
        paragraph_results=paragraph_results,
        ai_paragraphs=ai_paragraphs,
        human_paragraphs=human_paragraphs,
        ai_percentage=ai_percentage,
        human_percentage=human_percentage,
        pie_chart_base64=pie_chart_base64,
        overall_analysis=overall_analysis,
        options=options,
        displayed_paragraphs=displayed_paragraphs,
        now=datetime.now()
    )
    
    # 准备响应
    return StreamingResponse(
        io.StringIO(html_content),
        media_type="text/html",
        headers={"Content-Disposition": f"attachment; filename=report_{task.id}.html"}
    )

async def generate_text_report(task, paragraph_results, options):
    """
    生成纯文本格式的检测报告
    
    参数:
        task: 任务信息
        paragraph_results: 段落分析结果
        options: 报告选项
    
    返回:
        StreamingResponse: 包含纯文本报告的响应
    """
    # 准备AI和人类段落
    ai_paragraphs = [p for p in paragraph_results if p.ai_generated]
    human_paragraphs = [p for p in paragraph_results if not p.ai_generated]
    
    # 计算AI生成内容的比例
    total_paragraphs = len(paragraph_results)
    ai_percentage = len(ai_paragraphs) / total_paragraphs * 100 if total_paragraphs > 0 else 0
    human_percentage = 100 - ai_percentage
    
    # 解析整体分析结果
    overall_analysis = None
    if task.overall_analysis_result:
        try:
            if isinstance(task.overall_analysis_result, str):
                overall_analysis = json.loads(task.overall_analysis_result)
            else:
                overall_analysis = task.overall_analysis_result
                
            # 兼容性处理：确保字段名一致性
            if overall_analysis:
                # 处理困惑度字段名不一致的情况
                if "avg_perplexity" in overall_analysis and "perplexity" not in overall_analysis:
                    overall_analysis["perplexity"] = overall_analysis["avg_perplexity"]
                elif "perplexity" not in overall_analysis:
                    # 如果两个字段都不存在，设置默认值
                    overall_analysis["perplexity"] = 0
        except:
            pass
    
    # 创建纯文本报告
    report_lines = []
    
    # 报告标题
    report_lines.append("=" * 80)
    report_lines.append(" " * 30 + "AI内容检测报告")
    report_lines.append("=" * 80)
    report_lines.append("")
    
    # 基本信息
    if options.get("includeMetadata", True):
        report_lines.append("任务ID: " + str(task.id))
        report_lines.append("创建时间: " + task.created_at.strftime("%Y-%m-%d %H:%M:%S") if task.created_at else "未知")
        report_lines.append("文件名: " + (task.filename or "未命名"))
        report_lines.append("")
        report_lines.append("-" * 80)
        report_lines.append("")
    
    # 总体结果
    report_lines.append("检测总结:")
    report_lines.append("-" * 20)
    report_lines.append(f"分析段落总数: {total_paragraphs}个")
    report_lines.append(f"AI生成内容: {len(ai_paragraphs)}个段落 ({ai_percentage:.1f}%)")
    report_lines.append(f"人类撰写内容: {len(human_paragraphs)}个段落 ({human_percentage:.1f}%)")
    report_lines.append("")
    
    # 显示整体分析指标
    if overall_analysis:
        report_lines.append("整体分析指标:")
        report_lines.append("-" * 20)
        
        # 困惑度
        if "perplexity" in overall_analysis:
            perplexity = overall_analysis["perplexity"]
            perplexity_rating = "低(AI特征)" if perplexity < 20 else "中等" if perplexity < 30 else "高(人类特征)"
            report_lines.append(f"困惑度: {perplexity:.2f} - {perplexity_rating}")
        
        # 风格一致性
        if "style_consistency" in overall_analysis:
            consistency = overall_analysis["style_consistency"]
            consistency_rating = "高(AI特征)" if consistency > 0.95 else "中等" if consistency > 0.85 else "低(人类特征)"
            report_lines.append(f"风格一致性: {consistency:.2f} - {consistency_rating}")
        
        # AI可能性
        if "ai_likelihood" in overall_analysis:
            likelihood = overall_analysis["ai_likelihood"]
            report_lines.append(f"AI可能性: {likelihood}")
        
        report_lines.append("")
    
    # 结论评估
    report_lines.append("结论评估:")
    report_lines.append("-" * 20)
    if ai_percentage > 75:
        report_lines.append("本文内容主要由AI生成（>75%）。")
        report_lines.append("建议: 此内容可能需要进一步审查，确认是否符合使用AI内容的相关政策。")
    elif ai_percentage > 50:
        report_lines.append("本文包含大量AI生成内容（50-75%）。")
        report_lines.append("建议: 考虑修改或重写部分内容，增加原创性。")
    elif ai_percentage > 25:
        report_lines.append("本文包含部分AI生成内容（25-50%）。")
        report_lines.append("建议: 可能需要标注AI辅助生成的部分。")
    elif ai_percentage > 0:
        report_lines.append("本文主要由人类撰写，包含少量AI生成内容（<25%）。")
        report_lines.append("建议: 可以考虑保留大部分内容，仅审查标记为AI生成的段落。")
    else:
        report_lines.append("未检测到明显的AI生成内容。")
        report_lines.append("建议: 内容可能完全由人类撰写，符合原创要求。")
    
    report_lines.append("")
    report_lines.append("-" * 80)
    report_lines.append("")
    
    # 详细段落分析
    if options.get("includeDetails", True):
        report_lines.append("详细段落分析:")
        report_lines.append("=" * 20)
        report_lines.append("")
        
        # 按ID排序段落
        sorted_paragraphs = sorted(paragraph_results, key=lambda p: getattr(p, 'id', ''))
        
        for i, para in enumerate(sorted_paragraphs):
            is_ai = para.ai_generated
            report_lines.append(f"段落 {i+1}: {'AI生成' if is_ai else '人类撰写'}")
            report_lines.append("-" * 40)
            
            # 显示困惑度和AI可能性
            metrics = []
            if hasattr(para, 'perplexity') and para.perplexity is not None:
                metrics.append(f"困惑度: {para.perplexity:.2f}")
            if hasattr(para, 'ai_likelihood') and para.ai_likelihood:
                metrics.append(f"AI可能性: {para.ai_likelihood}")
            
            if metrics:
                report_lines.append("指标: " + ", ".join(metrics))
            
            # 显示段落内容
            if options.get("includeOriginalText", False):
                report_lines.append("")
                report_lines.append("内容:")
                # 分行显示段落
                for line in para.paragraph.split('\n'):
                    report_lines.append(line)
            
            # 显示分析原因
            if hasattr(para, 'reason') and para.reason:
                report_lines.append("")
                report_lines.append("分析原因:")
                report_lines.append(para.reason)
            
            report_lines.append("")
    
    # 检测方法说明
    report_lines.append("AI内容检测原理:")
    report_lines.append("=" * 20)
    report_lines.append("")
    report_lines.append("困惑度分析:")
    report_lines.append("  困惑度(Perplexity)是衡量语言模型预测文本难度的指标。AI生成的文本通常具有较低的困惑度，")
    report_lines.append("  因为语言模型生成的文本往往更加可预测。人类撰写的文本则更加多变和不可预测，困惑度较高。")
    report_lines.append("")
    
    report_lines.append("风格一致性分析:")
    report_lines.append("  对文本各部分的风格一致性进行评估。AI生成的文本风格通常非常一致，")
    report_lines.append("  而人类撰写的文本则风格略有变化。风格一致性过高可能表明是AI生成的内容。")
    report_lines.append("")
    
    report_lines.append("语义内容审查:")
    report_lines.append("  使用大型语言模型对文本内容进行分析，识别常见的AI生成特征，")
    report_lines.append("  如模板化表达、缺乏个人见解或创造性思考等。")
    report_lines.append("")
    
    report_lines.append("注意：检测结果供参考，不应作为唯一判断依据。技术在不断发展，检测方法也在持续改进。")
    
    # 准备响应
    text_content = "\n".join(report_lines)
    
    return StreamingResponse(
        io.StringIO(text_content),
        media_type="text/plain",
        headers={"Content-Disposition": f"attachment; filename=report_{task.id}.txt"}
    )

@router.get("/report/{task_id}/html")
async def get_html_report(
    task_id: str,
    template: str = "standard",  # 支持 standard, detailed, simple
    includeChart: bool = True,
    includeDetails: bool = True,
    includeOriginalText: bool = False,
    includeMetadata: bool = True,
    includeHeaderFooter: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    直接获取HTML格式的检测报告
    """
    # 查询任务
    task = db.query(DetectionTask).filter(DetectionTask.id == task_id).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="任务未找到")
    
    # 检查任务状态
    if task.status != TaskStatus.COMPLETED.value:
        raise HTTPException(status_code=400, detail="任务尚未完成，无法生成报告")
    
    # 获取段落分析结果
    paragraph_results = db.query(ParagraphResult).filter(
        ParagraphResult.task_id == task_id
    ).all()
    
    # 创建选项对象
    options = {
        "template": template,
        "includeChart": includeChart,
        "includeDetails": includeDetails,
        "includeOriginalText": includeOriginalText,
        "includeMetadata": includeMetadata,
        "includeHeaderFooter": includeHeaderFooter,
        "from_html_endpoint": True  # 表明这是直接从HTML端点调用的
    }
    
    return await generate_html_report(task, paragraph_results, options) 