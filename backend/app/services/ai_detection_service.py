import httpx
import os
import re
import json
from typing import List, Dict, Tuple, Any, Optional
from ..schemas.models import ParagraphAnalysis
from .llm_client import llm_client
from .detection_metrics import detection_metrics

def split_text_into_paragraphs(text: str, min_length: int = 100, max_length: int = 3000) -> List[str]:
    """
    将文本分割成段落
    
    增强的段落分割功能：
    1. 处理多种格式的段落分隔符
    2. 识别Markdown和HTML格式
    3. 保留段落原始格式
    4. 控制段落长度范围
    5. 优化语义完整性
    6. 识别代码块、列表等特殊结构
    7. 控制总段落数量，减少分段
    
    参数:
        text (str): 要分割的文本
        min_length (int): 段落最小长度
        max_length (int): 段落最大长度
        
    返回:
        List[str]: 分割后的段落列表
    """
    if not text or not text.strip():
        return []
        
    # 预处理：标准化换行符
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    
    # 首先识别和提取特殊文本块(代码块、列表等)
    special_blocks, remaining_text = _extract_special_blocks(text)
    
    # 处理剩余文本
    paragraphs = _process_regular_text(remaining_text)
    
    # 将特殊块重新插入到适当位置
    final_paragraphs = _merge_special_blocks_with_paragraphs(paragraphs, special_blocks)
    
    # 处理段落长度问题
    length_optimized_paragraphs = _optimize_paragraph_length(final_paragraphs, min_length, max_length)
    
    # 确保有合理数量的段落
    if not length_optimized_paragraphs:
        length_optimized_paragraphs = [text.strip()]
        
    return length_optimized_paragraphs

def _extract_special_blocks(text: str) -> Tuple[List[Dict[str, Any]], str]:
    """
    提取文本中的特殊块（代码块、列表等）
    返回特殊块列表和移除特殊块后的文本
    
    参数:
        text (str): 原始文本
    
    返回:
        Tuple[List[Dict], str]: 特殊块列表和剩余文本
    """
    special_blocks = []
    
    # 1. 提取代码块(Markdown格式: ```code```)
    code_block_pattern = r'```(?:[\w]*)\n([\s\S]*?)```'
    code_matches = list(re.finditer(code_block_pattern, text))
    
    for i, match in enumerate(code_matches):
        block_content = match.group(0)
        special_blocks.append({
            'type': 'code_block',
            'content': block_content,
            'start': match.start(),
            'end': match.end(),
            'index': i
        })
    
    # 2. 提取HTML代码块
    html_block_pattern = r'<(pre|code)(?:\s[^>]*)?>([\s\S]*?)<\/\1>'
    html_matches = list(re.finditer(html_block_pattern, text, re.IGNORECASE))
    
    for i, match in enumerate(html_matches):
        block_content = match.group(0)
        special_blocks.append({
            'type': 'html_code',
            'content': block_content,
            'start': match.start(),
            'end': match.end(),
            'index': i + len(code_matches)
        })
    
    # 3. 提取列表 (无序列表和有序列表)
    # 无序列表模式
    unordered_list_pattern = r'(?:^|\n)(?:\s*[-*+]\s+.+(?:\n|$))+' 
    unordered_matches = list(re.finditer(unordered_list_pattern, text))
    
    for i, match in enumerate(unordered_matches):
        block_content = match.group(0)
        special_blocks.append({
            'type': 'unordered_list',
            'content': block_content,
            'start': match.start(),
            'end': match.end(),
            'index': i + len(code_matches) + len(html_matches)
        })
    
    # 有序列表模式
    ordered_list_pattern = r'(?:^|\n)(?:\s*\d+\.\s+.+(?:\n|$))+'
    ordered_matches = list(re.finditer(ordered_list_pattern, text))
    
    for i, match in enumerate(ordered_matches):
        block_content = match.group(0)
        special_blocks.append({
            'type': 'ordered_list',
            'content': block_content,
            'start': match.start(),
            'end': match.end(),
            'index': i + len(code_matches) + len(html_matches) + len(unordered_matches)
        })
    
    # 4. 提取表格 (Markdown表格)
    table_pattern = r'(?:^|\n)(?:\|.+\|(?:\n|$))+(?:\|[-:\s|]+\|(?:\n|$))(?:\|.+\|(?:\n|$))+'
    table_matches = list(re.finditer(table_pattern, text))
    
    for i, match in enumerate(table_matches):
        block_content = match.group(0)
        special_blocks.append({
            'type': 'table',
            'content': block_content,
            'start': match.start(),
            'end': match.end(),
            'index': i + len(code_matches) + len(html_matches) + len(unordered_matches) + len(ordered_matches)
        })
    
    # 按位置排序所有特殊块
    special_blocks.sort(key=lambda x: x['start'])
    
    # 移除特殊块，保留其余文本
    if not special_blocks:
        return [], text
        
    remaining_text = ""
    last_end = 0
    
    for block in special_blocks:
        # 添加块之前的文本
        remaining_text += text[last_end:block['start']]
        # 添加一个占位符，以便后续处理
        remaining_text += f"\n[SPECIAL_BLOCK_{block['index']}]\n"
        last_end = block['end']
    
    # 添加最后一个块之后的文本
    remaining_text += text[last_end:]
    
    return special_blocks, remaining_text

def _process_regular_text(text: str) -> List[str]:
    """
    处理普通文本（非特殊块）
    使用多种方法分隔段落
    
    参数:
        text (str): 文本内容
        
    返回:
        List[str]: 段落列表
    """
    # 尝试多种分隔模式
    # 1. 常规多行分隔(两个或更多换行符)
    paragraphs = [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]
    
    # 如果只有一个段落，尝试使用单个换行符分割，但需要更谨慎
    if len(paragraphs) <= 1 and len(text) > 500 and '\n' in text:
        # 对于长文本中的单个换行，可能表示段落分隔
        potential_paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
        # 只有当分割后的段落数适中且长度合理时才采用这种分割
        if 3 <= len(potential_paragraphs) <= 20 and all(len(p) > 30 for p in potential_paragraphs):
            paragraphs = potential_paragraphs
    
    # 识别Markdown/HTML格式的标题作为段落开始
    if len(paragraphs) == 1 and (re.search(r'#+\s', text) or re.search(r'<h[1-6]>', text, re.IGNORECASE)):
        # Markdown 标题分割
        md_paragraphs = re.split(r'(^|\n)#+\s', text)
        if len(md_paragraphs) > 1:
            # 第一个元素可能是标题前的内容
            processed_paragraphs = []
            for i, p in enumerate(md_paragraphs):
                if i == 0 and p.strip():
                    processed_paragraphs.append(p.strip())
                elif i > 0:
                    # 重新添加标题标记
                    match = re.search(r'#+\s', md_paragraphs[i-1])
                    if match and i < len(md_paragraphs):
                        header = match.group(0)
                        processed_paragraphs.append(f"{header}{p.strip()}")
            paragraphs = [p for p in processed_paragraphs if p.strip()]
        
        # HTML 标题分割
        if len(paragraphs) <= 1:
            html_paragraphs = re.split(r'<h[1-6]>', text, flags=re.IGNORECASE)
            if len(html_paragraphs) > 1:
                # 处理HTML标题
                paragraphs = [p.strip() for p in html_paragraphs if p.strip()]
                
    return paragraphs

def _merge_special_blocks_with_paragraphs(paragraphs: List[str], special_blocks: List[Dict[str, Any]]) -> List[str]:
    """
    将特殊块与段落合并
    替换占位符为实际特殊块内容
    
    参数:
        paragraphs (List[str]): 段落列表
        special_blocks (List[Dict]): 特殊块信息
        
    返回:
        List[str]: 合并后的段落列表
    """
    if not special_blocks:
        return paragraphs
        
    # 创建块索引映射，以便快速查找
    blocks_map = {f"[SPECIAL_BLOCK_{block['index']}]": block for block in special_blocks}
    
    merged_paragraphs = []
    
    for paragraph in paragraphs:
        # 检查段落中是否包含特殊块占位符
        has_placeholder = False
        
        for placeholder in blocks_map.keys():
            if placeholder in paragraph:
                has_placeholder = True
                # 替换占位符为块内容
                parts = paragraph.split(placeholder)
                
                for i, part in enumerate(parts):
                    if part.strip():
                        merged_paragraphs.append(part.strip())
                    
                    # 在每个部分之后添加块内容，最后一部分除外
                    if i < len(parts) - 1:
                        block = blocks_map[placeholder]
                        merged_paragraphs.append(block['content'])
                
                break
        
        # 如果没有占位符，直接添加段落
        if not has_placeholder:
            merged_paragraphs.append(paragraph)
    
    return merged_paragraphs

def _optimize_paragraph_length(paragraphs: List[str], min_length: int, max_length: int) -> List[str]:
    """
    优化段落长度
    - 合并过短段落
    - 分割过长段落
    - 确保段落总数不超过10个
    
    参数:
        paragraphs (List[str]): 原始段落列表
        min_length (int): 最小段落长度
        max_length (int): 最大段落长度
        
    返回:
        List[str]: 优化后的段落列表
    """
    if not paragraphs:
        return []
        
    final_paragraphs = []
    current_para = ""
    
    for paragraph in paragraphs:
        if not paragraph.strip():
            continue
            
        # 检查段落类型，特殊块不作处理
        is_special_block = any([
            paragraph.startswith('```') and paragraph.endswith('```'),
            paragraph.startswith('<pre') or paragraph.startswith('<code'),
            re.match(r'^\s*[-*+]\s', paragraph) is not None,
            re.match(r'^\s*\d+\.\s', paragraph) is not None,
            '|---|' in paragraph or '|---:' in paragraph
        ])
        
        if is_special_block:
            # 如果当前有累积的文本，先添加到结果中
            if current_para:
                final_paragraphs.append(current_para)
                current_para = ""
            # 然后添加特殊块
            final_paragraphs.append(paragraph)
            continue
        
        # 处理常规段落
        if len(paragraph) > max_length:
            # 处理过长段落之前，先保存当前累积的段落
            if current_para:
                final_paragraphs.append(current_para)
                current_para = ""
                
            # 尝试在句子边界分割过长段落
            sentences = _split_into_sentences(paragraph)
            temp_para = ""
            
            for sentence in sentences:
                # 如果添加这个句子会导致段落过长，则保存当前段落并开始新段落
                if len(temp_para) + len(sentence) > max_length and len(temp_para) >= min_length:
                    final_paragraphs.append(temp_para.strip())
                    temp_para = sentence
                else:
                    # 否则继续添加到当前段落
                    if temp_para and not temp_para.endswith(' '):
                        temp_para += ' '
                    temp_para += sentence
            
            # 添加最后一个段落或合并到当前累积段落
            if temp_para:
                if current_para and len(current_para) + len(temp_para) <= max_length:
                    current_para = current_para + "\n\n" + temp_para if current_para else temp_para
                else:
                    if current_para:
                        final_paragraphs.append(current_para)
                    current_para = temp_para
        
        # 处理短段落 - 更积极地合并
        elif not current_para or len(current_para) + len(paragraph) <= max_length:
            # 合并到当前段落
            if current_para:
                current_para += "\n\n" + paragraph
            else:
                current_para = paragraph
        else:
            # 当前段落已经足够长，保存并开始新段落
            final_paragraphs.append(current_para)
            current_para = paragraph
    
    # 添加剩余段落
    if current_para:
        final_paragraphs.append(current_para)
    
    # 如果段落数量仍然过多，进行进一步合并
    if len(final_paragraphs) > 10:
        # 基于段落长度进一步合并
        short_paragraphs = []
        other_paragraphs = []
        
        # 分离短段落和其他段落
        for p in final_paragraphs:
            if len(p) < min_length * 2 and not any([
                p.startswith('```') and p.endswith('```'),
                p.startswith('<pre') or p.startswith('<code'),
                re.match(r'^\s*[-*+]\s', p) is not None,
                re.match(r'^\s*\d+\.\s', p) is not None,
                '|---|' in p or '|---:' in p
            ]):
                short_paragraphs.append(p)
            else:
                other_paragraphs.append(p)
        
        # 尝试合并相邻的短段落
        merged_short = []
        i = 0
        while i < len(short_paragraphs):
            if i + 1 < len(short_paragraphs) and len(short_paragraphs[i]) + len(short_paragraphs[i+1]) <= max_length:
                merged_short.append(f"{short_paragraphs[i]}\n\n{short_paragraphs[i+1]}")
                i += 2
            else:
                merged_short.append(short_paragraphs[i])
                i += 1
        
        # 合并结果
        final_paragraphs = other_paragraphs + merged_short
        
        # 如果仍然超过10个段落，使用更激进的方法合并
        if len(final_paragraphs) > 10:
            return _further_optimize_paragraphs(final_paragraphs, 10, 0)
    
    return final_paragraphs

def _split_into_sentences(text: str) -> List[str]:
    """
    将文本分割成句子。
    保留句子的标点符号。
    """
    # 常见的中英文句子结束标记
    # 处理常见的中英文句子结束标点
    pattern = r'(?<=[。！？\.!?])\s+'
    sentences = re.split(pattern, text)
    
    # 恢复句子结束标记可能被意外分割的情况
    result = []
    current = ""
    for s in sentences:
        if not s.strip():
            continue
            
        # 检查是否以句号等结束
        if re.search(r'[。！？\.!?]$', s):
            current += s
            result.append(current)
            current = ""
        else:
            # 可能是被错误分割的句子
            if current:
                current += " " + s
            else:
                current = s
    
    # 添加最后一个未完成的句子
    if current:
        result.append(current)
        
    # 如果没有成功分割，则返回原始文本作为一个句子
    if not result:
        return [text]
        
    return result

def optimize_paragraphs_for_ai_detection(paragraphs: List[str]) -> List[str]:
    """
    为AI检测优化段落分割
    
    1. 合并相似主题的相邻段落
    2. 分离明显不同主题的段落
    3. 考虑语言模式的连贯性
    4. 控制段落总数不超过10个
    
    参数:
        paragraphs (List[str]): 初始分割的段落
        
    返回:
        List[str]: 优化后的段落
    """
    if not paragraphs or len(paragraphs) <= 1:
        return paragraphs
    
    # 如果段落总数已经小于等于10，不需要特别优化
    if len(paragraphs) <= 10:
        return paragraphs
        
    # 第一轮优化：合并高度相似的段落
    optimized = []
    current_paragraph = paragraphs[0]
    
    for i in range(1, len(paragraphs)):
        next_paragraph = paragraphs[i]
        
        # 特殊块不合并
        is_current_special = any([
            current_paragraph.startswith('```') and current_paragraph.endswith('```'),
            current_paragraph.startswith('<pre') or current_paragraph.startswith('<code'),
            re.match(r'^\s*[-*+]\s', current_paragraph) is not None,
            re.match(r'^\s*\d+\.\s', current_paragraph) is not None,
            '|---|' in current_paragraph or '|---:' in current_paragraph
        ])
        
        is_next_special = any([
            next_paragraph.startswith('```') and next_paragraph.endswith('```'),
            next_paragraph.startswith('<pre') or next_paragraph.startswith('<code'),
            re.match(r'^\s*[-*+]\s', next_paragraph) is not None,
            re.match(r'^\s*\d+\.\s', next_paragraph) is not None,
            '|---|' in next_paragraph or '|---:' in next_paragraph
        ])
        
        if is_current_special or is_next_special:
            optimized.append(current_paragraph)
            current_paragraph = next_paragraph
            continue
        
        # 检测段落间的连贯性
        is_coherent = _check_paragraph_coherence(current_paragraph, next_paragraph)
        
        # 提高合并倾向: 增加段落长度阈值，提高合并可能性
        # 如果段落之间连贯且合并后不会太长，则合并
        if is_coherent and len(current_paragraph) + len(next_paragraph) < 3000:  # 增加长度阈值
            current_paragraph = f"{current_paragraph}\n\n{next_paragraph}"
        else:
            # 否则保存当前段落并开始新段落
            optimized.append(current_paragraph)
            current_paragraph = next_paragraph
    
    # 添加最后一个段落
    if current_paragraph:
        optimized.append(current_paragraph)
    
    # 如果第一轮优化后段落数仍然大于10，继续合并
    if len(optimized) > 10:
        # 第二轮优化：基于段落长度合并较短的段落
        return _further_optimize_paragraphs(optimized, max_paragraphs=10)
        
    return optimized

def _further_optimize_paragraphs(paragraphs: List[str], max_paragraphs: int = 10, depth: int = 0) -> List[str]:
    """
    进一步合并段落，确保总段落数不超过指定值
    
    参数:
        paragraphs (List[str]): 初步优化后的段落
        max_paragraphs (int): 最大段落数量
        depth (int): 递归深度，用于防止无限递归
        
    返回:
        List[str]: 进一步优化后的段落
    """
    # 设定最大递归深度，防止堆栈溢出
    MAX_RECURSION_DEPTH = 10
    if depth >= MAX_RECURSION_DEPTH:
        print(f"警告：达到最大递归深度 {MAX_RECURSION_DEPTH}，强制返回当前段落")
        # 如果仍然超出限制，直接截取前max_paragraphs个段落
        return paragraphs[:max_paragraphs] if len(paragraphs) > max_paragraphs else paragraphs
    
    if len(paragraphs) <= max_paragraphs:
        return paragraphs
    
    # 计算需要合并的段落数
    merge_count = len(paragraphs) - max_paragraphs
    
    # 根据段落长度排序，优先合并较短的段落
    paragraph_lengths = [(i, len(p)) for i, p in enumerate(paragraphs)]
    paragraph_lengths.sort(key=lambda x: x[1])  # 按长度排序
    
    # 找出最短的几个段落的索引
    short_indices = [idx for idx, _ in paragraph_lengths[:merge_count+1]]
    short_indices.sort()  # 按原始顺序排序
    
    # 合并相邻的较短段落
    result = []
    i = 0
    while i < len(paragraphs):
        if i in short_indices and i+1 < len(paragraphs) and i+1 in short_indices:
            # 合并当前段落和下一个段落
            merged = f"{paragraphs[i]}\n\n{paragraphs[i+1]}"
            result.append(merged)
            i += 2  # 跳过已合并的段落
            # 从短段落列表中移除已处理的索引
            if i < len(paragraphs) and i in short_indices:
                short_indices.remove(i)
        else:
            result.append(paragraphs[i])
            i += 1
    
    # 如果结果长度没有减少，强制合并段落
    if len(result) >= len(paragraphs):
        result = _force_merge_paragraphs(paragraphs, max_paragraphs)
        return result
    
    # 如果结果仍然超过最大段落数，递归调用继续合并，但增加深度计数
    if len(result) > max_paragraphs:
        return _further_optimize_paragraphs(result, max_paragraphs, depth + 1)
    
    return result

def _force_merge_paragraphs(paragraphs: List[str], max_paragraphs: int) -> List[str]:
    """
    强制合并段落，确保返回不超过max_paragraphs数量的段落
    
    参数:
        paragraphs (List[str]): 段落列表
        max_paragraphs (int): 最大段落数量
        
    返回:
        List[str]: 合并后的段落列表
    """
    if len(paragraphs) <= max_paragraphs:
        return paragraphs
    
    # 计算每个组应该包含的原始段落数
    group_size = len(paragraphs) // max_paragraphs
    remainder = len(paragraphs) % max_paragraphs
    
    result = []
    start_idx = 0
    
    # 将段落分组合并
    for i in range(max_paragraphs):
        # 当前组的大小，前remainder个组各多分配1个段落
        current_group_size = group_size + (1 if i < remainder else 0)
        end_idx = start_idx + current_group_size
        
        # 合并当前组的段落
        group_paragraphs = paragraphs[start_idx:end_idx]
        merged_paragraph = "\n\n".join(group_paragraphs)
        result.append(merged_paragraph)
        
        start_idx = end_idx
    
    return result

def _check_paragraph_coherence(para1: str, para2: str) -> bool:
    """
    检查两个段落之间的连贯性
    使用简单的启发式方法判断段落是否应该合并
    
    参数:
        para1 (str): 第一个段落
        para2 (str): 第二个段落
        
    返回:
        bool: 如果段落连贯应合并，则返回True
    """
    # 如果其中一个段落是标题格式，不合并
    if re.match(r'^#+\s', para2) or re.match(r'^<h[1-6]>', para2, re.IGNORECASE):
        return False
        
    # 检查段落间的关键词重叠
    para1_words = set(re.findall(r'\w+', para1.lower()))
    para2_words = set(re.findall(r'\w+', para2.lower()))
    
    # 计算词汇重叠率
    overlap = len(para1_words.intersection(para2_words))
    
    if len(para1_words) == 0 or len(para2_words) == 0:
        return False
        
    overlap_ratio = overlap / min(len(para1_words), len(para2_words))
    
    # 降低连贯性阈值，使段落更容易合并
    return overlap_ratio > 0.15  # 从0.2降低到0.15

def _convert_numpy_types(obj, depth=0):
    """
    将NumPy类型转换为Python原生类型，以便JSON序列化
    
    参数:
        obj: 要转换的对象
        depth: 当前递归深度，用于防止无限递归
        
    返回:
        转换后的对象
    """
    import numpy as np
    
    # 防止递归过深导致堆栈溢出
    MAX_RECURSION_DEPTH = 20
    if depth >= MAX_RECURSION_DEPTH:
        # 如果递归太深，直接尝试转换为字符串
        try:
            if isinstance(obj, dict):
                return {k: str(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [str(item) for item in obj]
            else:
                return str(obj)
        except:
            return "数据结构过于复杂，无法转换"
    
    if isinstance(obj, (np.integer, np.int_, np.intc, np.intp, np.int8,
                        np.int16, np.int32, np.int64, np.uint8,
                        np.uint16, np.uint32, np.uint64)):
        return int(obj)
    elif isinstance(obj, (np.float_, np.float16, np.float32, np.float64)):
        return float(obj)
    elif isinstance(obj, np.bool_):  # 单独处理np.bool_类型
        return bool(obj)
    elif isinstance(obj, (bool)):  # 保持原始Python布尔值
        return obj
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {k: _convert_numpy_types(v, depth+1) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_convert_numpy_types(item, depth+1) for item in obj]
    elif obj is None or isinstance(obj, (str, int, float)):  # 明确处理基本类型
        return obj
    else:  # 处理其他可能的NumPy类型
        try:
            return obj.item() if hasattr(obj, 'item') else obj
        except:
            return str(obj)  # 最后的防御：转为字符串

async def detect_ai_content(text: str, max_paragraphs: int = 10) -> Tuple[float, List[ParagraphAnalysis]]:
    """
    检测文本中的AI生成内容
    返回AI生成内容的百分比和详细分析
    使用多个大模型和综合指标进行评估
    
    参数:
        text (str): 要分析的文本
        max_paragraphs (int): 最大段落数量，默认为10个
    """
    # 将文本分割成段落
    paragraphs = split_text_into_paragraphs(text)
    print(f"初始段落分割数量: {len(paragraphs)}")
    
    # 优化段落分割以提高AI检测精度
    optimized_paragraphs = optimize_paragraphs_for_ai_detection(paragraphs)
    
    # 确保段落数量不超过限制
    if len(optimized_paragraphs) > max_paragraphs:
        print(f"段落数量({len(optimized_paragraphs)})超过限制({max_paragraphs})，进行强制合并")
        optimized_paragraphs = _further_optimize_paragraphs(optimized_paragraphs, max_paragraphs)
    
    print(f"优化后段落数量: {len(optimized_paragraphs)}")
    print(f"段落示例: {optimized_paragraphs[:2] if len(optimized_paragraphs) >= 2 else optimized_paragraphs}")
    
    # 存储分析结果
    results = []
    ai_paragraphs_count = 0
    
    # 分析整篇文章
    try:
        overall_analysis = await detection_metrics.analyze_text(text)
        # 确保整体分析结果中的NumPy类型被转换
        overall_analysis = _convert_numpy_types(overall_analysis)
        print(f"整体分析结果: {overall_analysis['is_ai_generated']}, 置信度: {overall_analysis['confidence']:.2f}%")
    except Exception as e:
        print(f"整体分析出错: {str(e)}")
        overall_analysis = {"is_ai_generated": None, "confidence": 0, "reason": f"分析错误: {str(e)}"}
    
    # 逐段分析
    for paragraph in optimized_paragraphs:
        if len(paragraph) < 20:  # 段落太短不作检测
            continue
            
        try:
            # 使用多模型分析文本
            metrics_result = await detection_metrics.analyze_text(paragraph)
            
            # 转换NumPy类型
            metrics_result = _convert_numpy_types(metrics_result)
            
            # 提取结果
            is_ai_generated = metrics_result["is_ai_generated"]
            confidence = metrics_result["confidence"]
            reason = metrics_result["reason"]
            
            # 额外权重因素: 如果整体分析有较高置信度，影响段落判断
            if overall_analysis["is_ai_generated"] is not None and overall_analysis["confidence"] > 70:
                # 如果整体判定是AI生成且当前段落置信度不高，提高AI可能性
                if overall_analysis["is_ai_generated"] and confidence < 60:
                    is_ai_generated = True
                    reason = f"整体分析影响: 整篇文章很可能是AI生成，此段落也被视为AI生成\n\n{reason}"
            
            # 处理结果
            if is_ai_generated:
                ai_paragraphs_count += 1
            
            # 准备指标数据
            models_results = metrics_result.get("models_results", {})
            metrics_data = {}
            
            # 如果有特征分析结果，提取其中的指标
            if "特征分析" in models_results and "metrics" in models_results["特征分析"]:
                metrics_data = models_results["特征分析"]["metrics"]
            
            # 转换指标数据 - 确保所有NumPy类型都被转换
            metrics_data = _convert_numpy_types(metrics_data)
            
            # 添加详细指标到结果
            results.append(ParagraphAnalysis(
                paragraph=paragraph,
                ai_generated=bool(is_ai_generated),  # 确保是Python原生bool类型
                reason=str(reason),  # 确保是字符串类型
                metrics=metrics_data,
                confidence=float(confidence)  # 确保是Python原生float类型
            ))
            
        except Exception as e:
            print(f"AI检测过程中出错: {str(e)}")
            # 如果出错，尝试使用LLM备用方法
            try:
                is_ai_generated, reason = llm_client.analyze_text(paragraph)
                
                if is_ai_generated:
                    ai_paragraphs_count += 1
                
                results.append(ParagraphAnalysis(
                    paragraph=paragraph,
                    ai_generated=bool(is_ai_generated),  # 确保是Python原生bool类型
                    reason=f"[备用检测] {reason}"
                ))
            except Exception as e2:
                print(f"备用检测也失败: {str(e2)}")
    
    # 计算AI生成内容百分比
    ai_percentage = (ai_paragraphs_count / len(results)) * 100 if results else 0
    
    # 确保返回的是Python内置类型
    ai_percentage = float(ai_percentage)
    
    # 整体分析影响最终结果
    if overall_analysis["is_ai_generated"] and overall_analysis["confidence"] > 80:
        # 如果整体分析有高度置信度，提高AI百分比
        ai_percentage = min(100, ai_percentage * 1.2)
        
        # 添加整体分析结果到第一段
        if results:
            results[0].reason = f"整体分析: {overall_analysis['reason'][:200]}...\n\n{results[0].reason}"
    
    return ai_percentage, results 