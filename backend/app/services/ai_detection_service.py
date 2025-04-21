import httpx
import os
import re
import json
from typing import List, Dict, Tuple
from ..schemas.models import ParagraphAnalysis
from .llm_client import llm_client

# 假设我们使用一个AI API服务进行检测
# 正式环境中，替换为实际的API密钥和端点
API_KEY = os.getenv("AI_DETECTION_API_KEY", "your_api_key_here")
API_ENDPOINT = os.getenv("AI_DETECTION_API_ENDPOINT", "https://api.example.com/detect")

def split_text_into_paragraphs(text: str) -> List[str]:
    """
    将文本分割成段落
    """
    # 使用换行符分割文本，并过滤掉空段落
    paragraphs = [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]
    return paragraphs

async def detect_ai_content(text: str) -> Tuple[float, List[ParagraphAnalysis]]:
    """
    检测文本中的AI生成内容
    返回AI生成内容的百分比和详细分析
    """
    # 将文本分割成段落
    paragraphs = split_text_into_paragraphs(text)
    print(f"分割后的段落数量: {len(paragraphs)}")
    print(f"段落示例: {paragraphs[:5]}")
    # 存储分析结果
    results = []
    ai_paragraphs_count = 0
    
    # 使用LLM客户端进行AI检测
    for paragraph in paragraphs:
        if len(paragraph) < 20:  # 段落太短不作检测
            continue
            
        try:
            # 使用LLM客户端分析文本
            is_ai_generated, reason = llm_client.analyze_text(paragraph)
            
            # 处理结果
            if is_ai_generated:
                ai_paragraphs_count += 1
            
            # 添加到结果
            results.append(ParagraphAnalysis(
                paragraph=paragraph,
                ai_generated=is_ai_generated,
                reason=reason
            ))
            
        except Exception as e:
            print(f"AI检测过程中出错: {str(e)}")
    
    # 计算AI生成内容百分比
    ai_percentage = (ai_paragraphs_count / len(results)) * 100 if results else 0
    
    return ai_percentage, results 