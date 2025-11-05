import httpx
import os
import re
import json
import asyncio
import numpy as np
from typing import List, Dict, Tuple, Any, Optional
from ..schemas.models import ParagraphAnalysis
from .llm_client import llm_client

# 导入NLP相关库
from nltk.tokenize import sent_tokenize
from transformers import GPT2LMHeadModel, GPT2Tokenizer
import torch
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

# 检查是否为离线模式
OFFLINE_MODE = os.environ.get("OFFLINE_MODE", "false").lower() == "true"
if OFFLINE_MODE:
    print("运行在离线模式，将只使用本地模型")

# ----------- 文本切分部分 -----------

def clean_text(text: str) -> str:
    """清理文本，统一换行符并减少连续空行"""
    text = re.sub(r'\r\n', '\n', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def paragraph_split(text: str, min_chars: int = 30) -> List[str]:
    """按段落分割文本，合并过短的段落"""
    raw_blocks = text.split('\n\n')
    processed = []
    buffer = ""
    for block in raw_blocks:
        block = block.strip()
        if len(block) < min_chars:
            buffer += " " + block
        else:
            if buffer:
                processed.append(buffer.strip())
                buffer = ""
            processed.append(block)
    if buffer:
        processed.append(buffer.strip())
    return processed

def safe_sent_tokenize(text: str) -> List[str]:
    """安全的句子分割：优先使用NLTK，失败时下载依赖或使用正则回退"""
    try:
        from nltk.tokenize import sent_tokenize as _sent_tokenize
        try:
            return _sent_tokenize(text)
        except LookupError:
            import nltk
            data_dir = os.environ.get("NLTK_DATA") or os.path.abspath("models/nltk_data")
            os.makedirs(data_dir, exist_ok=True)
            os.environ["NLTK_DATA"] = data_dir
            try:
                nltk.download("punkt", download_dir=data_dir, quiet=True)
            except Exception:
                pass
            try:
                nltk.download("punkt_tab", download_dir=data_dir, quiet=True)
            except Exception:
                pass
            try:
                return _sent_tokenize(text)
            except Exception:
                pass
    except Exception:
        pass
    # 正则回退（适用于中英混合常见终止符）
    pieces = re.split(r'(?<=[。！？!?\.])\s+', text)
    return [p.strip() for p in pieces if p.strip()]

def segment_sentences(blocks: List[str], max_chars: int = 300) -> List[str]:
    """将段落按句子分割，确保每个片段不超过最大字符数"""
    result = []
    for block in blocks:
        sentences = safe_sent_tokenize(block)
        segment = ""
        for sentence in sentences:
            if len(segment) + len(sentence) < max_chars:
                segment += " " + sentence
            else:
                result.append(segment.strip())
                segment = sentence
        if segment:
            result.append(segment.strip())
    return result

def smart_split(text: str, 
                min_chars: int = 30, 
                max_chars: int = 300,
                segment_level: str = "sentence") -> List[str]:
    """智能拆分文本，可以按段落或句子级别拆分"""
    text = clean_text(text)
    blocks = paragraph_split(text, min_chars=min_chars)
    if segment_level == "paragraph":
        return blocks
    elif segment_level == "sentence":
        return segment_sentences(blocks, max_chars=max_chars)
    else:
        raise ValueError("segment_level必须是'paragraph'或'sentence'")

def split_text_with_sliding_window(text: str, window_size: int = 500, step_size: int = 250) -> List[str]:
    """使用滑动窗口方法分割长文本"""
    if not text or len(text) <= window_size:
        return [text] if text else []
        
    segments = []
    start = 0
    text_length = len(text)
    
    while start < text_length:
        # 提取当前窗口
        end = min(start + window_size, text_length)
        current_segment = text[start:end]
        
        # 尝试在句子边界处分割
        if start > 0 and end < text_length:
            paragraph_end = current_segment.rfind('\n\n')
            if paragraph_end > window_size * 0.5:
                current_segment = current_segment[:paragraph_end].strip()
                end = start + paragraph_end
            else:
                sentence_end_matches = list(re.finditer(r'[.!?]\s', current_segment))
                if sentence_end_matches and sentence_end_matches[-1].end() > window_size * 0.7:
                    sentence_end = sentence_end_matches[-1].end()
                    current_segment = current_segment[:sentence_end].strip()
                    end = start + sentence_end
        
        if current_segment:
            segments.append(current_segment)
        
        start += step_size
        if text_length - start < window_size * 0.3:
            if start < text_length:
                segments.append(text[start:].strip())
            break
            
    return segments

# ----------- 新增：文本类型识别和结构分析 -----------

def detect_text_type(text: str) -> str:
    """
    识别文本类型（学术文本 vs 普通文本）
    学术文本需要使用不同的检测阈值和权重
    """
    academic_features = 0
    
    # 1. 检测引用格式 (Author et al., Year)
    if re.search(r'\([A-Z][a-z]+(?:\s+(?:&|et\s+al\.?))?\s*,?\s+\d{4}\)', text):
        academic_features += 1
    
    # 2. 检测学术词汇
    academic_words = ['research', 'study', 'analysis', 'methodology', 
                      'findings', 'results', 'literature', 'hypothesis',
                      'theoretical', 'empirical', 'framework']
    text_lower = text.lower()
    for word in academic_words:
        if word in text_lower:
            academic_features += 1
            break
    
    # 3. 检测正式过渡词
    formal_transitions = ['furthermore', 'moreover', 'consequently', 
                          'therefore', 'nevertheless', 'thus', 'hence']
    for transition in formal_transitions:
        if re.search(r'\b' + transition + r'\b', text, re.IGNORECASE):
            academic_features += 1
            break
    
    # 4. 检测图表引用
    if re.search(r'\b(Fig\.|Table|Figure|Section|Chapter)\s+\d+', text, re.IGNORECASE):
        academic_features += 1
    
    return 'academic' if academic_features >= 2 else 'general'

def split_into_clauses(sentence: str) -> List[str]:
    """
    将长句分割成子句（按分号、冒号分割）
    用于检测长句内部的结构一致性
    """
    clauses = []
    
    # 首先按分号分割
    parts = sentence.split(';')
    
    # 如果只有一个部分，尝试按冒号分割
    if len(parts) == 1 and ':' in sentence:
        colon_parts = sentence.split(':', 1)
        if len(colon_parts) == 2:
            # 冒号后的部分可能包含分号
            after_colon = colon_parts[1]
            if ';' in after_colon:
                parts = [colon_parts[0]] + after_colon.split(';')
            else:
                parts = colon_parts
    
    # 清理并过滤短子句
    for part in parts:
        part = part.strip()
        # 移除句末标点和引用
        part = re.sub(r'\([^)]+\d{4}\)\.?$', '', part)
        part = part.rstrip('.,;:!?')
        
        # 只保留足够长的子句（至少10个词）
        if len(part.split()) >= 10:
            clauses.append(part)
    
    return clauses

def compute_multi_level_burstiness(text: str) -> Dict[str, Any]:
    """
    多层次爆发度计算
    
    关键改进：不仅检测句子间的爆发度，还检测长句内部子句的爆发度
    这是区分AI生成学术文本和人类写作的关键指标
    
    Returns:
        Dict包含:
        - paragraph_burstiness: 段落级别爆发度（句子间）
        - min_clause_burstiness: 最小子句级别爆发度（长句内部）
        - has_long_sentences_with_clauses: 是否存在包含多个子句的长句
        - long_sentence_count: 长句数量
    """
    try:
        sentences = safe_sent_tokenize(text)
        
        # 1. 段落级别：句子间的爆发度
        sentence_lengths = [len(s.split()) for s in sentences]
        
        if len(sentence_lengths) >= 2:
            mean_len = np.mean(sentence_lengths)
            std_len = np.std(sentence_lengths)
            paragraph_burstiness = std_len / mean_len if mean_len > 0 else 0
        else:
            paragraph_burstiness = 0.5
        
        # 2. 子句级别：检测长句内部的结构一致性
        clause_burstiness_scores = []
        long_sentence_details = []
        
        for sentence in sentences:
            word_count = len(sentence.split())
            
            # 对于长句子（>35词），检查内部子句
            if word_count > 35:
                # 检查是否包含分号或冒号（表示有子句结构）
                if ';' in sentence or (': ' in sentence and ';' in sentence):
                    clauses = split_into_clauses(sentence)
                    
                    if len(clauses) >= 2:
                        clause_lengths = [len(c.split()) for c in clauses]
                        
                        # 计算子句长度的一致性
                        mean_clause_len = np.mean(clause_lengths)
                        std_clause_len = np.std(clause_lengths)
                        
                        if mean_clause_len > 0:
                            clause_burst = std_clause_len / mean_clause_len
                            clause_burstiness_scores.append(clause_burst)
                            
                            long_sentence_details.append({
                                'word_count': word_count,
                                'clause_count': len(clauses),
                                'clause_lengths': clause_lengths,
                                'clause_burstiness': clause_burst
                            })
                # 新增：对于没有分号但有多个逗号的长句，也检查子句结构
                elif sentence.count(',') >= 3:
                    # 按逗号分割，检查是否有重复的结构模式
                    comma_parts = sentence.split(',')
                    # 过滤掉太短的部分
                    valid_parts = [p.strip() for p in comma_parts if len(p.split()) >= 5]
                    
                    if len(valid_parts) >= 3:
                        part_lengths = [len(p.split()) for p in valid_parts]
                        mean_part_len = np.mean(part_lengths)
                        std_part_len = np.std(part_lengths)
                        
                        if mean_part_len > 0:
                            part_burst = std_part_len / mean_part_len
                            clause_burstiness_scores.append(part_burst)
                            
                            long_sentence_details.append({
                                'word_count': word_count,
                                'clause_count': len(valid_parts),
                                'clause_lengths': part_lengths,
                                'clause_burstiness': part_burst,
                                'type': 'comma_separated'
                            })
        
        # 3. 综合结果
        result = {
            'paragraph_burstiness': float(paragraph_burstiness),
            'sentence_lengths': sentence_lengths,
            'has_long_sentences_with_clauses': len(clause_burstiness_scores) > 0,
            'long_sentence_count': len(clause_burstiness_scores),
            'long_sentence_details': long_sentence_details
        }
        
        # 如果有子句爆发度，记录最小值（最低的爆发度最能体现AI特征）
        if clause_burstiness_scores:
            result['min_clause_burstiness'] = float(min(clause_burstiness_scores))
            result['avg_clause_burstiness'] = float(np.mean(clause_burstiness_scores))
        else:
            result['min_clause_burstiness'] = None
            result['avg_clause_burstiness'] = None
        
        return result
        
    except Exception as e:
        print(f"计算多层次爆发度时出错: {str(e)}")
        return {
            'paragraph_burstiness': 0.5,
            'min_clause_burstiness': None,
            'has_long_sentences_with_clauses': False,
            'long_sentence_count': 0,
            'sentence_lengths': []
        }

def detect_parallel_structures(text: str) -> Dict[str, Any]:
    """
    检测AI生成文本的典型平行结构
    
    AI生成的学术文本经常使用完美的平行结构：
    - 冒号 + 多个分号连接的子句
    - "A; B; and C" 模式
    - 重复的句式结构
    """
    results = {
        'parallel_structure_count': 0,
        'patterns_found': []
    }
    
    # 1. 检测：冒号 + 分号子句的模式（AI典型特征）
    if ':' in text:
        colon_parts = text.split(':')
        for part in colon_parts[1:]:  # 检查冒号后的内容
            semicolon_count = part.count(';')
            # 降低阈值：1个分号也算，因为"冒号: A; and B"也是典型AI模式
            if semicolon_count >= 2:
                results['parallel_structure_count'] += 3  # 增加权重
                results['patterns_found'].append('colon_with_multiple_semicolons')
            elif semicolon_count >= 1 and 'and' in part.lower():
                # 新增：检测"冒号: A; and B"模式
                results['parallel_structure_count'] += 2
                results['patterns_found'].append('colon_semicolon_and_pattern')
    
    # 2. 检测：三个或更多分号连接的平行句
    semicolon_sequences = re.findall(r'[^.!?;]+;[^.!?;]+;[^.!?;]+', text)
    if semicolon_sequences:
        results['parallel_structure_count'] += len(semicolon_sequences)
        results['patterns_found'].append('multiple_semicolon_sequence')
    
    # 3. 检测：分号 + and 模式（AI常用，即使只有一个）
    # 改进：单个 "; and they/it" 也算AI特征
    and_pattern_count = len(re.findall(r';\s*and\s+(?:they|it)\s+', text, re.IGNORECASE))
    if and_pattern_count >= 1:  # 从2改为1
        results['parallel_structure_count'] += and_pattern_count
        results['patterns_found'].append('semicolon_and_pattern')
    
    # 4. 检测：序列化列举（First, Second, Third等）- 新增
    ordinal_patterns = [
        r'\bFirst,.*?\bSecond,.*?\bThird,',  # First, ... Second, ... Third,
        r'\bFirstly,.*?\bSecondly,.*?\bThirdly,',  # Firstly, ... Secondly, ... Thirdly,
    ]
    
    for pattern in ordinal_patterns:
        matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
        if matches:
            results['parallel_structure_count'] += 2  # 权重较高
            results['patterns_found'].append('ordinal_enumeration')
            break
    
    # 5. 检测：重复的"The X Stage [动词] on"模式（新增） - AI学术文本常见
    stage_pattern = r'The\s+\w+\s+Stage\s+(focuses|centers|concentrates|emphasizes)\s+on'
    stage_matches = re.findall(stage_pattern, text, re.IGNORECASE)
    if len(stage_matches) >= 2:  # 至少出现2次
        results['parallel_structure_count'] += 2  # 权重较高
        results['patterns_found'].append('repeated_stage_pattern')
    
    # 6. 检测：平行的子句开头（相似的句式）
    sentences = safe_sent_tokenize(text)
    if len(sentences) >= 3:
        # 检查是否有3个或更多句子以相似方式开头
        sentence_starts = []
        for sent in sentences:
            words = sent.split()
            if len(words) >= 3:
                # 获取前3个词作为句子开头模式
                start_pattern = ' '.join(words[:3]).lower()
                sentence_starts.append(start_pattern)
        
        # 如果有重复的开头模式
        from collections import Counter
        start_counts = Counter(sentence_starts)
        for pattern, count in start_counts.items():
            if count >= 3:
                results['parallel_structure_count'] += 1
                results['patterns_found'].append('repeated_sentence_starts')
                break
    
    results['total_score'] = results['parallel_structure_count']
    
    return results

def detect_ai_vocabulary_enhanced(text: str) -> Dict[str, Any]:
    """
    增强版AI词汇检测
    检测AI生成文本中常见的词汇模式
    """
    import re  # 确保re模块在函数开始时导入
    
    words = text.split()
    text_lower = text.lower()
    total_words = len(words)
    
    results = {
        'high_freq_ai_words': [],
        'transition_words': [],
        'hedging_phrases': [],
        'total_ai_word_count': 0,
        'ai_vocabulary_density': 0
    }
    
    # 1. AI高频词汇（扩展列表）
    ai_words = [
        'exhibit', 'characteristics', 'significant', 'crucial',
        'essential', 'fundamental', 'comprehensive', 'substantial',
        'demonstrate', 'illustrate', 'emphasize', 'highlight',
        'indicates', 'suggests', 'reveals', 'demonstrates',
        # 新增常见AI词汇
        'represents', 'enhances', 'contributes', 'facilitates',
        'serves', 'focuses', 'ensures', 'enables', 'supports',
        'avoids', 'prevents', 'addresses', 'summarized',
        'identified', 'characterized', 'prioritized',
        # 新增：AI常用的描述性词汇
        'distinct', 'typical', 'various', 'numerous', 'multiple',
        'particular', 'specific', 'certain', 'notable', 'prominent'
    ]
    
    for word in words:
        word_clean = word.lower().strip('.,;:!?()')
        if word_clean in ai_words:
            results['high_freq_ai_words'].append(word_clean)
    
    # 2. 过渡词（AI常用）
    transition_words = [
        'moreover', 'furthermore', 'consequently', 'therefore',
        'meanwhile', 'nevertheless', 'thus', 'hence', 'accordingly'
    ]
    
    for word in words:
        word_clean = word.lower().strip('.,;:!?()')
        if word_clean in transition_words:
            results['transition_words'].append(word_clean)
    
    # 3. 套话短语
    hedging_phrases = [
        'it is important to note',
        'it is worth noting',
        'it should be emphasized',
        'it is necessary to',
        'it is crucial to understand'
    ]
    
    for phrase in hedging_phrases:
        if phrase in text_lower:
            results['hedging_phrases'].append(phrase)
    
    # 计算总数和密度
    results['total_ai_word_count'] = (
        len(results['high_freq_ai_words']) + 
        len(results['transition_words']) + 
        len(results['hedging_phrases'])
    )
    
    if total_words > 0:
        results['ai_vocabulary_density'] = results['total_ai_word_count'] / total_words
    
    # 4. 检测典型AI词汇组合（新增）
    results['ai_word_combinations'] = []
    
    # 常见的AI词汇组合模式 - 扩展更多典型组合
    ai_combinations = [
        ('exhibit', 'characteristics'),
        ('exhibit', 'distinct'),
        ('distinct', 'characteristics'),
        ('significant', 'impact'),
        ('crucial', 'role'),
        ('fundamental', 'importance'),
        ('demonstrates', 'effectiveness'),
        ('illustrates', 'significance'),
        ('highlights', 'importance'),
        ('emphasizes', 'necessity'),
        ('typical', 'characteristics'),
        ('various', 'aspects'),
        ('multiple', 'factors')
    ]
    
    # 使用更精确的模式匹配，检测词汇是否在相近位置出现（窗口大小：5个词）
    for word1, word2 in ai_combinations:
        # 使用正则表达式检测两个词在5个词的窗口内出现
        pattern = rf'\b{word1}\b(?:\s+\w+){{0,4}}\s+\b{word2}\b'
        if re.search(pattern, text_lower):
            results['ai_word_combinations'].append(f'{word1}_{word2}')
            results['total_ai_word_count'] += 5  # 组合权重提高（原来是2，现在是5）
    
    # 检测"it is necessary to"等套话（额外权重）
    if any(phrase in text_lower for phrase in ['it is necessary to', 'it is important to note', 'it should be emphasized']):
        results['total_ai_word_count'] += 3  # 套话权重很高
    
    # 5. 检测AI常用短语模式（增强版）
    ai_phrase_patterns = [
        # 原有模式
        r'\bserves as\b',  # "serves as"
        r'\bfocuses on\b',  # "focuses on"
        r'\brepresents the\b',  # "represents the"
        r'\benhances the\b',  # "enhances the"
        r'\bin terms of\b',  # "in terms of"
        r'\bfrom the perspective of\b',  # "from the perspective of"
        r'\bare summarized as follows\b',  # "are summarized as follows"
        r'\bis identified as\b',  # "is identified as"
        r'\bis characterized by\b',  # "is characterized by"
        r'\bmust be prioritized\b',  # "must be prioritized"
        # 新增：典型的 AI 描述性短语
        r'\bexhibit\s+(?:distinct|typical|various|certain|specific)\s+characteristics\b',  # "exhibit [形容词] characteristics"
        r'\bdemonstrate\s+(?:significant|considerable|substantial)\s+(?:impact|effect|influence)\b',  # "demonstrate [形容词] impact"
        r'\bplay\s+a\s+(?:crucial|vital|significant|key)\s+role\b',  # "play a [形容词] role"
        r'\bmake\s+it\s+(?:necessary|essential|crucial|important)\s+to\b',  # "make it [形容词] to"
        r'\bhas\s+been\s+(?:widely|extensively|commonly)\s+(?:recognized|acknowledged|accepted)\b',  # "has been [副词] recognized"
    ]
    
    ai_phrase_count = 0
    high_value_phrases = []  # 记录高价值短语
    
    for pattern in ai_phrase_patterns:
        matches = re.findall(pattern, text_lower)
        if matches:
            ai_phrase_count += len(matches)
            # 对于包含 "exhibit" 的短语，给予更高权重
            if 'exhibit' in pattern:
                high_value_phrases.extend(matches)
    
    if ai_phrase_count > 0:
        base_weight = ai_phrase_count * 2
        # 高价值短语额外加分
        bonus_weight = len(high_value_phrases) * 3
        results['total_ai_word_count'] += base_weight + bonus_weight
        results['ai_phrase_patterns'] = ai_phrase_count
        if high_value_phrases:
            results['high_value_ai_phrases'] = high_value_phrases
    
    return results

# ----------- 困惑度计算部分 -----------

# 初始化GPT-2模型，用于计算困惑度
_gpt2_model = None
_gpt2_tokenizer = None

def get_gpt2_model():
    """懒加载GPT-2模型"""
    global _gpt2_model, _gpt2_tokenizer
    if _gpt2_model is None:
        try:
            model_name = 'gpt2'
            # 设置超时和重试参数
            from transformers import logging
            logging.set_verbosity_error()  # 减少不必要的警告
            
            # 尝试从本地加载模型（如果之前已下载）
            import os
            local_model_path = os.environ.get("GPT2_MODEL_PATH", "models/gpt2")
            
            if os.path.exists(local_model_path) or OFFLINE_MODE:
                print(f"从本地加载GPT-2模型: {local_model_path}")
                try:
                    # 设置超时加载
                    _gpt2_model = GPT2LMHeadModel.from_pretrained(
                        local_model_path,
                        local_files_only=True,
                        revision=None
                    )
                    _gpt2_tokenizer = GPT2Tokenizer.from_pretrained(
                        local_model_path,
                        local_files_only=True,
                        revision=None
                    )
                except Exception as e:
                    if OFFLINE_MODE:
                        print(f"离线模式下无法加载本地GPT-2模型: {str(e)}")
                        raise  # 在离线模式下，如果本地加载失败，就抛出异常
                    else:
                        print(f"从本地加载GPT-2模型失败，尝试从Hugging Face下载: {str(e)}")
                        raise  # 让下面的代码处理重新下载
            
            if _gpt2_model is None and not OFFLINE_MODE:
                # 从Hugging Face下载，设置超时
                print("尝试从Hugging Face下载GPT-2模型...")
                os.environ['TRANSFORMERS_CACHE'] = os.environ.get('TRANSFORMERS_CACHE', 'models/')
                
                try:
                    _gpt2_model = GPT2LMHeadModel.from_pretrained(
                        model_name, 
                        revision=None, 
                        use_auth_token=None,
                        cache_dir='models/'
                    )
                    _gpt2_tokenizer = GPT2Tokenizer.from_pretrained(
                        model_name, 
                        revision=None,
                        use_auth_token=None,
                        cache_dir='models/'
                    )
                except Exception as e:
                    print(f"无法从Hugging Face下载GPT-2模型: {str(e)}")
                    # 在这种情况下，将返回None，compute_perplexity将使用备选方案
            
            if _gpt2_model is not None:
                _gpt2_model.eval()
                # 移至CPU以减少内存占用
                _gpt2_model = _gpt2_model.cpu()
        except Exception as e:
            print(f"无法加载GPT-2模型: {str(e)}")
            _gpt2_model = None
            _gpt2_tokenizer = None
            # 这里不创建备选方案，我们会在compute_perplexity中处理
    
    return _gpt2_model, _gpt2_tokenizer

def compute_perplexity(text: str) -> float:
    """计算文本的困惑度（perplexity）"""
    try:
        # 文本预处理：清理并检查文本内容
        if not text or len(text.strip()) < 5:  # 如果文本为空或非常短
            return 25.0  # 返回默认值
            
        # 限制文本长度，防止处理超长文本
        if len(text) > 10000:
            text = text[:10000]
            
        model, tokenizer = get_gpt2_model()
        
        # 如果模型加载失败，返回默认值
        if model is None or tokenizer is None:
            return 25.0  # 返回中等困惑度作为降级方案
            
        encodings = tokenizer(text, return_tensors='pt', truncation=True, max_length=512)
        
        # 检查编码是否为空或没有有效内容
        if 'input_ids' not in encodings or encodings['input_ids'].shape[1] == 0:
            return 25.0  # 返回默认值
            
        # 安全执行模型推理
        with torch.no_grad():
            try:
                outputs = model(**encodings, labels=encodings["input_ids"])
                loss = outputs.loss
                return torch.exp(loss).item()
            except IndexError:
                # 处理索引错误
                print("计算困惑度时出现索引错误，返回默认值")
                return 25.0
    except Exception as e:
        print(f"计算困惑度时出错: {str(e)}")
        return 25.0  # 返回中等困惑度作为降级方案

# ----------- 风格一致性检测 -----------

# 初始化句子编码模型
_embed_model = None

def get_embed_model():
    """懒加载句子编码模型"""
    global _embed_model
    if _embed_model is None:
        try:
            # 设置超时和重试参数
            from transformers import logging
            logging.set_verbosity_error()  # 减少不必要的警告
            
            # 尝试从本地加载模型（如果之前已下载）
            import os
            local_model_path = os.environ.get("SENTENCE_TRANSFORMER_PATH", "models/all-MiniLM-L6-v2")
            
            if os.path.exists(local_model_path) or OFFLINE_MODE:
                print(f"从本地加载模型: {local_model_path}")
                try:
                    _embed_model = SentenceTransformer(local_model_path)
                except Exception as e:
                    if OFFLINE_MODE:
                        print(f"离线模式下无法加载本地句子转换模型: {str(e)}")
                        # 在离线模式下使用备选模型
                        raise
                    else:
                        print(f"从本地加载模型失败，尝试从Hugging Face下载: {str(e)}")
                        raise  # 让下面的代码处理重新下载
            
            if _embed_model is None and not OFFLINE_MODE:
                # 从Hugging Face下载，设置超时
                print("尝试从Hugging Face下载模型...")
                os.environ['SENTENCE_TRANSFORMERS_HOME'] = os.environ.get('SENTENCE_TRANSFORMERS_HOME', 'models/')
                _embed_model = SentenceTransformer('all-MiniLM-L6-v2')
                # 成功下载后保存路径
                print(f"模型下载成功，保存在: {_embed_model.get_model_path()}")
        except Exception as e:
            print(f"无法加载SentenceTransformer模型: {str(e)}")
            # 创建一个简单的备选方案
            from sklearn.feature_extraction.text import TfidfVectorizer
            print("使用TF-IDF作为备选嵌入模型")
            
            # 创建一个简单的包装类，模拟SentenceTransformer的接口
            class TfidfEmbedder:
                def __init__(self):
                    self.vectorizer = TfidfVectorizer()
                    # 通过一个简单的文本初始化vectorizer
                    self.vectorizer.fit(["这是一个初始化文本，用于TF-IDF向量化器"])
                
                def encode(self, sentences):
                    # 确保sentences是列表
                    if isinstance(sentences, str):
                        sentences = [sentences]
                    # 转换并返回稀疏矩阵的密集表示
                    return self.vectorizer.transform(sentences).toarray()
            
            _embed_model = TfidfEmbedder()
    
    return _embed_model

def compute_style_consistency(segments: List[str]) -> float:
    """计算文本片段间的风格一致性"""
    try:
        # 如果只有一个片段，无法计算片段间的一致性
        if len(segments) < 2:
            # 返回中等值，而不是0，避免因为段落少而导致AI可能性被低估
            return 0.5
            
        embed_model = get_embed_model()
        embeddings = embed_model.encode(segments)
        similarities = []
        for i in range(len(embeddings) - 1):
            sim = cosine_similarity([embeddings[i]], [embeddings[i + 1]])[0][0]
            similarities.append(sim)
        
        # 当计算结果异常低时（低于0.1），可能是由于片段差异极大或计算问题
        # 返回一个最小合理值，避免完全否定AI可能性
        result = float(np.mean(similarities)) if similarities else 0.5
        return max(result, 0.1)  # 确保风格一致性至少有一个最小值
    except Exception as e:
        print(f"计算风格一致性时出错: {str(e)}")
        return 0.5  # 返回中等值作为降级方案

# ----------- AI评分整合 -----------

def estimate_ai_likelihood(perplexity: float, style: float, ai_percentage: float, segment_count: int) -> str:
    """
    [已弃用] 旧版AI可能性估计函数，保留用于兼容性
    请使用 estimate_ai_likelihood_v2 代替
    """
    # 调用新版本函数
    result = estimate_ai_likelihood_v2(
        text="",  # 旧版本不需要text参数
        perplexity=perplexity,
        burstiness_result=None,
        parallel_structures=None,
        ai_vocab_result=None,
        style=style,
        ai_percentage=ai_percentage,
        segment_count=segment_count,
        text_type='general'
    )
    return result['ai_likelihood']

def estimate_ai_likelihood_v2(
    text: str,
    perplexity: float,
    burstiness_result: Optional[Dict[str, Any]],
    parallel_structures: Optional[Dict[str, Any]],
    ai_vocab_result: Optional[Dict[str, Any]],
    style: float,
    ai_percentage: float,
    segment_count: int,
    text_type: str = 'general'
) -> Dict[str, Any]:
    """
    增强版AI可能性估计 v2.0
    
    关键改进：
    1. 多层次爆发度检测（段落级 + 子句级）
    2. 平行结构检测（AI学术文本的典型特征）
    3. AI词汇密度分析
    4. 文本类型自适应阈值
    5. 多维度加权评分系统
    
    Args:
        text: 原始文本（用于类型检测）
        perplexity: 困惑度
        burstiness_result: 多层次爆发度结果
        parallel_structures: 平行结构检测结果
        ai_vocab_result: AI词汇检测结果
        style: 风格一致性
        ai_percentage: LLM判断的AI比例
        segment_count: 段落数量
        text_type: 文本类型 ('academic' 或 'general')
    
    Returns:
        Dict包含:
        - ai_likelihood: 可能性描述
        - ai_score: 数值评分 (0-100)
        - confidence: 置信度
        - key_indicators: 关键指标列表
    """
    ai_score = 0
    indicators = []
    
    # 根据文本类型设置阈值
    if text_type == 'academic':
        thresholds = {
            'perplexity_high': 15,      # 学术文本困惑度通常较低
            'perplexity_medium': 25,
            'burstiness_low': 0.20,     # 学术文本阈值更严格
            'burstiness_medium': 0.30,
            'clause_burstiness_critical': 0.15,  # 子句爆发度阈值
            'parallel_weight_high': 35,  # 学术文本平行结构权重更高
            'parallel_weight_medium': 25,
            'vocab_density_threshold': 0.03
        }
    else:
        thresholds = {
            'perplexity_high': 20,
            'perplexity_medium': 30,
            'burstiness_low': 0.25,
            'burstiness_medium': 0.35,
            'clause_burstiness_critical': 0.20,
            'parallel_weight_high': 25,
            'parallel_weight_medium': 15,
            'vocab_density_threshold': 0.05
        }
    
    # 1. 困惑度评分 (最高25分)
    if perplexity < thresholds['perplexity_high']:
        ai_score += 25
        indicators.append(f"困惑度极低({perplexity:.2f})")
    elif perplexity < thresholds['perplexity_medium']:
        ai_score += 15
        indicators.append(f"困惑度偏低({perplexity:.2f})")
    elif perplexity < 35:
        ai_score += 5
    
    # 2. 多层次爆发度评分 (最高35分) - 最关键的指标！
    if burstiness_result:
        # 优先检查子句级别爆发度（针对长句内部结构）
        if burstiness_result.get('has_long_sentences_with_clauses'):
            min_clause_burst = burstiness_result.get('min_clause_burstiness')
            if min_clause_burst is not None:
                if min_clause_burst < thresholds['clause_burstiness_critical']:
                    ai_score += 35
                    indicators.append(f"子句级爆发度极低({min_clause_burst:.3f})，长句内部结构高度一致")
                elif min_clause_burst < thresholds['burstiness_low']:
                    ai_score += 30
                    indicators.append(f"子句级爆发度很低({min_clause_burst:.3f})")
                elif min_clause_burst < thresholds['burstiness_medium']:
                    ai_score += 20
                    indicators.append(f"子句级爆发度偏低({min_clause_burst:.3f})")
        
        # 如果没有子句级数据，使用段落级爆发度
        if ai_score < 20:  # 如果子句级没有贡献太多分数
            para_burst = burstiness_result.get('paragraph_burstiness', 0.5)
            if para_burst < thresholds['burstiness_low']:
                additional_score = min(25, 25 - (ai_score // 2))  # 避免重复计分
                ai_score += additional_score
                if additional_score > 0:
                    indicators.append(f"段落级爆发度低({para_burst:.3f})")
            elif para_burst < thresholds['burstiness_medium']:
                additional_score = min(15, 15 - (ai_score // 3))
                ai_score += additional_score
    
    # 3. 平行结构评分 (最高35分) - 学术AI文本的显著特征
    if parallel_structures:
        parallel_score = parallel_structures.get('total_score', 0)
        patterns = parallel_structures.get('patterns_found', [])
        
        if parallel_score >= 3:
            weight = thresholds['parallel_weight_high']
            ai_score += weight
            indicators.append(f"检测到显著的平行结构模式(得分:{parallel_score})")
            if 'colon_with_multiple_semicolons' in patterns:
                indicators.append("检测到AI典型模式：冒号+多个分号")
        elif parallel_score >= 2:
            weight = thresholds['parallel_weight_medium']
            ai_score += weight
            indicators.append(f"检测到平行结构(得分:{parallel_score})")
        elif parallel_score >= 1:
            ai_score += 15
            indicators.append("检测到轻微平行结构")
        
        # 额外检查特定模式（新增）
        if 'ordinal_enumeration' in patterns:
            ai_score += 10
            indicators.append("检测到序列化列举（First, Second, Third）")
        if 'semicolon_and_pattern' in patterns:
            ai_score += 10
            indicators.append("检测到分号+and平行结构")
        if 'repeated_stage_pattern' in patterns:
            ai_score += 10
            indicators.append("检测到重复句式：The X Stage [动词] on")
    
    # 4. AI词汇密度评分 (最高30分 - 提高权重)
    if ai_vocab_result:
        vocab_density = ai_vocab_result.get('ai_vocabulary_density', 0)
        vocab_count = ai_vocab_result.get('total_ai_word_count', 0)
        
        if vocab_density > thresholds['vocab_density_threshold'] * 2:
            ai_score += 15
            indicators.append(f"AI词汇密度高({vocab_density:.1%})")
        elif vocab_density > thresholds['vocab_density_threshold']:
            ai_score += 10
            indicators.append(f"AI词汇密度中等({vocab_density:.1%})")
        elif vocab_count >= 5:
            ai_score += 5
            indicators.append(f"AI词汇数量较多({vocab_count}个)")
        
        # 检测AI词汇组合 - 提高权重
        ai_combinations = ai_vocab_result.get('ai_word_combinations', [])
        if ai_combinations:
            combination_score = min(15, len(ai_combinations) * 8)  # 从5提高到8
            ai_score += combination_score
            # 列出检测到的组合
            combo_list = ', '.join(ai_combinations[:3])
            indicators.append(f"检测到AI典型词汇组合({len(ai_combinations)}个): {combo_list}")
        
        # 检测高价值AI短语（如 "exhibit distinct characteristics"）
        high_value_phrases = ai_vocab_result.get('high_value_ai_phrases', [])
        if high_value_phrases:
            ai_score += 20  # 高价值短语直接加20分！
            indicators.append(f"⚠️ 检测到AI高度典型短语: {', '.join(high_value_phrases[:2])}")
        
        # 检测AI短语模式
        ai_phrase_count = ai_vocab_result.get('ai_phrase_patterns', 0)
        if ai_phrase_count >= 3:
            ai_score += 15
            indicators.append(f"检测到大量AI短语模式({ai_phrase_count}个)")
        elif ai_phrase_count >= 1:
            ai_score += 10  # 从8提高到10
            indicators.append(f"检测到AI短语模式({ai_phrase_count}个)")
    
    # 5. 风格一致性评分 (最高10分) - 权重降低
    if segment_count >= 2:
        if style > 0.9:
            ai_score += 10
            indicators.append(f"风格一致性过高({style:.2f})")
        elif style > 0.85:
            ai_score += 5
    
    # 6. LLM判断评分 (最高10分)
    if ai_percentage > 80:
        ai_score += 10
        indicators.append(f"LLM判断AI比例高({ai_percentage:.0f}%)")
    elif ai_percentage > 60:
        ai_score += 5
    
    # 7. 完美引用格式检测 (学术文本额外10分)
    if text_type == 'academic' and text:
        # 检测完美引用格式
        perfect_citations = re.findall(r'\([A-Z][a-z]+\s+et\s+al\.,\s+\d{4}\)', text)
        if len(perfect_citations) >= 1:
            ai_score += 10
            indicators.append("引用格式过于完美")
    
    # 最终判断（进一步降低阈值，提高检测灵敏度）
    if ai_score >= 40:  # 从50进一步降到40
        likelihood = "高（AI生成可能性大）"
        confidence = "高"
    elif ai_score >= 30:  # 从35降到30
        likelihood = "中（可能为AI生成）"
        confidence = "中"
    else:
        likelihood = "低（更可能为人类写作）"
        confidence = "低"
    
    return {
        'ai_likelihood': likelihood,
        'ai_score': ai_score,
        'confidence': confidence,
        'key_indicators': indicators,
        'thresholds_used': text_type
    }

async def analyze_segment_comprehensive(segment: str) -> Dict[str, Any]:
    """综合分析文本片段，计算困惑度、AI评分和获取LLM评估"""
    print(f"分析段落: {segment}")
    if len(segment.strip()) < 20:  # 跳过过短的片段
        return {
            "paragraph": segment,
            "ai_generated": False,
            "reason": "文本片段过短，无法有效分析",
            "perplexity": 0,
            "is_ai_likelihood": "未知"
        }
    
    try:
        # 首先计算困惑度（带错误处理）
        try:
            perplexity = compute_perplexity(segment)
        except Exception as e:
            print(f"为段落计算困惑度时出错: {str(e)}")
            perplexity = 25.0  # 返回中等困惑度作为降级方案
        
        # 计算爆发度
        try:
            burstiness_result = compute_multi_level_burstiness(segment)
        except Exception as e:
            print(f"计算爆发度时出错: {str(e)}")
            burstiness_result = {'paragraph_burstiness': 0.5}
        
        # 检测平行结构
        try:
            parallel_structures = detect_parallel_structures(segment)
        except Exception as e:
            print(f"检测平行结构时出错: {str(e)}")
            parallel_structures = {'score': 0}
        
        # 检测AI词汇
        try:
            ai_vocab_result = detect_ai_vocabulary_enhanced(segment)
        except Exception as e:
            print(f"检测AI词汇时出错: {str(e)}")
            ai_vocab_result = {'density': 0}
        
        # 计算AI评分
        text_type = detect_text_type(segment)
        ai_score_result = estimate_ai_likelihood_v2(
            text=segment,
            perplexity=perplexity,
            burstiness_result=burstiness_result,
            parallel_structures=parallel_structures,
            ai_vocab_result=ai_vocab_result,
            style=1.0,
            ai_percentage=0,  # Changed from None to 0 for initial segment analysis
            segment_count=1,
            text_type=text_type
        )
        
        ai_score = ai_score_result['ai_score']
        ai_likelihood = ai_score_result['ai_likelihood']
        
        # 根据AI评分判断初步结果
        # 降低阈值：40分及以上倾向于判定为AI（原来是50分，太保守）
        initial_ai_judgment = ai_score >= 40
        
        # 将所有指标作为上下文传递给LLM进行分析
        context = {
            "perplexity": perplexity,
            "ai_score": ai_score,
            "ai_likelihood": ai_likelihood,
            "key_indicators": ai_score_result.get('key_indicators', []),
            "initial_judgment": initial_ai_judgment
        }
        
        # 使用LLM客户端分析文本，将所有指标作为上下文传入
        try:
            is_ai_generated, reason = await llm_client.analyze_text(segment, context=context)
        except Exception as e:
            print(f"调用LLM客户端分析文本时出错: {str(e)}")
            # 当LLM分析失败时，使用AI评分来进行基本判断
            is_ai_generated = initial_ai_judgment
            reason = f"LLM分析失败，基于AI评分({ai_score}/100)推断: {str(e)}"
        
        # 最终判断说明逻辑
        final_ai_likelihood = ai_likelihood
        
        # 如果LLM判断与AI评分有明显矛盾，以AI评分为准并调整
        # 降低阈值：40分就应该判定为AI（之前是50分，太保守导致漏检）
        if not is_ai_generated and ai_score >= 40:
            # LLM认为是人类但AI评分较高，强制判定为AI生成
            is_ai_generated = True
            if ai_score >= 60:
                final_ai_likelihood = "高（AI生成可能性大）"
            else:
                final_ai_likelihood = "中（可能为AI生成）"
            reason += f" [系统修正: AI评分{ai_score}/100较高，判定为AI生成]"
            print(f"⚠️ 修正判断：LLM认为是人类但AI评分{ai_score}≥40，强制判定为AI生成")
        elif is_ai_generated and ai_score < 25:
            # LLM认为是AI但评分很低，调整为人类创作
            is_ai_generated = False
            final_ai_likelihood = "低（更可能为人类写作）"
            reason += f" [系统修正: AI评分{ai_score}/100较低，判定为人类创作]"
            print(f"⚠️ 修正判断：LLM认为是AI但AI评分{ai_score}<30，调整为人类创作")
        
        return {
            "paragraph": segment,
            "ai_generated": is_ai_generated,
            "reason": reason,
            "perplexity": round(perplexity, 2),
            "is_ai_likelihood": final_ai_likelihood
        }
    except Exception as e:
        print(f"分析段落时出错: {str(e)}")
        return {
            "paragraph": segment,
            "ai_generated": False,
            "reason": f"分析出错: {str(e)}",
            "perplexity": 0,
            "is_ai_likelihood": "未知"
        }

async def detect_ai_content_comprehensive(text: str) -> Dict[str, Any]:
    """
    综合检测文本中的AI生成内容
    使用多种指标：困惑度、风格一致性、语言模型评估
    
    Returns:
        Dict: 包含AI生成内容的综合分析结果
    """
    try:
        # 使用智能拆分方式分割文本
        segments = smart_split(text, segment_level="sentence")
        print(f"分割后的片段数量: {len(segments)}")
        
        # 过滤掉太短的段落
        valid_segments = [segment for segment in segments if len(segment) >= 20]
        
        if not valid_segments:
            return {
                "ai_percentage": 0,
                "avg_perplexity": 0,
                "style_consistency": 0,
                "ai_likelihood": "未知",
                "segment_count": 0,
                "detailed_analysis": []
            }
        
        # 计算风格一致性（带错误处理）
        try:
            style_score = compute_style_consistency(valid_segments)
        except Exception as e:
            print(f"计算风格一致性失败: {str(e)}")
            style_score = 0.5  # 使用中等风格一致性作为降级方案
        
        # 创建并发任务分析每个段落
        tasks = [analyze_segment_comprehensive(segment) for segment in valid_segments]
        
        # 控制并发数
        MAX_CONCURRENCY = 2
        detailed_analysis = []
        ai_segments_count = 0
        perplexity_values = []
        
        # 分批处理任务
        for i in range(0, len(tasks), MAX_CONCURRENCY):
            batch = tasks[i:i+MAX_CONCURRENCY]
            batch_results = await asyncio.gather(*batch, return_exceptions=True)
            
            for result in batch_results:
                # 跳过异常
                if isinstance(result, Exception):
                    print(f"段落分析出现异常: {str(result)}")
                    continue
                    
                # 处理结果
                if result["ai_generated"]:
                    ai_segments_count += 1
                
                if result["perplexity"] > 0:
                    perplexity_values.append(result["perplexity"])
                
                # 添加到结果
                detailed_analysis.append(ParagraphAnalysis(
                    paragraph=result["paragraph"],
                    ai_generated=result["ai_generated"],
                    reason=result["reason"],
                    perplexity=result["perplexity"],
                    ai_likelihood=result["is_ai_likelihood"]
                ))
        
        # 计算AI生成内容百分比 - 增加安全检查，确保一定有有效值
        segment_count = len(detailed_analysis)
        # 确保分母不为零
        if segment_count > 0:
            ai_percentage = (ai_segments_count / segment_count) * 100
        else:
            ai_percentage = 0
            print("警告: 没有有效的段落分析结果")
        
        # 计算平均困惑度
        if perplexity_values:
            avg_perplexity = round(np.mean(perplexity_values), 2)
        else:
            avg_perplexity = 0
            print("警告: 没有有效的困惑度值")
        
        # 对于段落数量少的情况，进行特殊处理
        if segment_count <= 2:
            # 如果段落数量很少，LLM判断权重更高
            if ai_percentage > 90:  # 如果所有(或绝大多数)段落被判断为AI，强化AI判断
                # 确保困惑度值合理 - 不再强行调整数值，因为这可能与LLM判断不一致
                if avg_perplexity > 30:
                    print(f"注意: 全部段落被判为AI但困惑度较高({avg_perplexity})")
                
                # 风格一致性仍可适当调整，因为这不影响段落级判断
                if style_score < 0.8:
                    style_score = max(style_score, 0.85)  # 确保至少达到中等一致性
            elif ai_percentage == 0:  # 如果所有段落被判断为人类写作
                # 不再强行调整困惑度
                if avg_perplexity < 20:
                    print(f"注意: 全部段落被判为人类但困惑度非常低({avg_perplexity})")
        
        # ===== 新增：使用增强版检测方法 =====
        
        # 1. 识别文本类型
        text_type = detect_text_type(text)
        print(f"检测到文本类型: {text_type}")
        
        # 2. 多层次爆发度检测
        try:
            burstiness_result = compute_multi_level_burstiness(text)
            print(f"爆发度检测完成 - 段落级: {burstiness_result.get('paragraph_burstiness', 0):.3f}, "
                  f"子句级: {burstiness_result.get('min_clause_burstiness', 'N/A')}")
        except Exception as e:
            print(f"计算爆发度失败: {str(e)}")
            burstiness_result = None
        
        # 3. 平行结构检测
        try:
            parallel_structures = detect_parallel_structures(text)
            print(f"平行结构检测完成 - 得分: {parallel_structures.get('total_score', 0)}")
        except Exception as e:
            print(f"平行结构检测失败: {str(e)}")
            parallel_structures = None
        
        # 4. AI词汇检测
        try:
            ai_vocab_result = detect_ai_vocabulary_enhanced(text)
            print(f"AI词汇检测完成 - 密度: {ai_vocab_result.get('ai_vocabulary_density', 0):.1%}")
        except Exception as e:
            print(f"AI词汇检测失败: {str(e)}")
            ai_vocab_result = None
        
        # 5. 使用增强版判断逻辑
        ai_likelihood_result = estimate_ai_likelihood_v2(
            text=text,
            perplexity=avg_perplexity,
            burstiness_result=burstiness_result,
            parallel_structures=parallel_structures,
            ai_vocab_result=ai_vocab_result,
            style=style_score,
            ai_percentage=ai_percentage,
            segment_count=segment_count,
            text_type=text_type
        )
        
        print(f"最终AI评分: {ai_likelihood_result['ai_score']}/100")
        print(f"判断结果: {ai_likelihood_result['ai_likelihood']}")
        print(f"关键指标: {ai_likelihood_result['key_indicators']}")
        
        # ===== 二次检测：解决整体评分与段落百分比不一致的问题 =====
        overall_ai_score = ai_likelihood_result['ai_score']
        
        # 如果整体AI评分较高（≥60），但段落百分比较低，进行谨慎的二次检测
        # 提高触发阈值：从50提高到60，减少误判
        if overall_ai_score >= 60 and ai_percentage < 40:
            print(f"⚠️ 检测到不一致：整体AI评分{overall_ai_score}/100，但段落AI比例仅{ai_percentage:.1f}%")
            print(f"   启动二次检测：仅重新识别那些有明显AI特征但被漏判的段落")
            
            # 收集所有被判定为"人类"的段落，评估其AI倾向度
            human_segments = []
            for i, analysis in enumerate(detailed_analysis):
                if not analysis.ai_generated:
                    # 重新计算该段落的AI倾向度分数
                    segment_text = analysis.paragraph
                    
                    # 计算段落的多项指标
                    try:
                        seg_perplexity = calculate_perplexity_corrected(segment_text)
                    except:
                        seg_perplexity = 50
                    
                    try:
                        seg_burstiness = compute_multi_level_burstiness(segment_text)
                        burstiness_score = seg_burstiness.get('paragraph_burstiness', 0.5)
                    except:
                        burstiness_score = 0.5
                    
                    try:
                        seg_vocab = detect_ai_vocabulary_enhanced(segment_text)
                        vocab_density = seg_vocab.get('ai_vocabulary_density', 0)
                    except:
                        vocab_density = 0
                    
                    # 计算综合AI倾向度分数（分数越低，越像AI）
                    ai_tendency_score = (
                        seg_perplexity * 0.4 +  # 困惑度越低越像AI
                        burstiness_score * 40 +  # 爆发度越低越像AI
                        (1 - vocab_density) * 30  # AI词汇密度越高越像AI
                    )
                    
                    human_segments.append({
                        'index': i,
                        'analysis': analysis,
                        'ai_tendency_score': ai_tendency_score,
                        'perplexity': seg_perplexity,
                        'burstiness': burstiness_score,
                        'vocab_density': vocab_density
                    })
            
            if human_segments:
                # 按AI倾向度排序（分数越低，越像AI）
                human_segments.sort(key=lambda x: x['ai_tendency_score'])
                
                # 只重新识别那些真正有明显AI特征的段落，不按比例凑数
                # 设置严格的阈值标准
                reidentified_count = 0
                max_reidentify = max(3, int(segment_count * 0.15))  # 最多重新识别15%的段落
                
                for candidate in human_segments[:max_reidentify]:
                    idx = candidate['index']
                    old_analysis = candidate['analysis']
                    
                    # 严格的判定标准：必须满足多个条件才重新判定为AI
                    is_strong_ai = False
                    reasons = []
                    
                    # 条件1：极低困惑度（<25）
                    if candidate['perplexity'] < 25:
                        is_strong_ai = True
                        reasons.append(f"困惑度极低({candidate['perplexity']:.1f})")
                    
                    # 条件2：低困惑度 + 低爆发度
                    if candidate['perplexity'] < 35 and candidate['burstiness'] < 0.3:
                        is_strong_ai = True
                        reasons.append(f"困惑度低({candidate['perplexity']:.1f}) + 爆发度低({candidate['burstiness']:.3f})")
                    
                    # 条件3：高AI词汇密度 + 低困惑度
                    if candidate['vocab_density'] > 0.15 and candidate['perplexity'] < 40:
                        is_strong_ai = True
                        reasons.append(f"AI词汇密度高({candidate['vocab_density']:.1%}) + 困惑度低({candidate['perplexity']:.1f})")
                    
                    # 只有满足严格条件的段落才重新标记
                    if is_strong_ai:
                        # 更新判定结果
                        new_reason = (f"二次检测识别（整体评分{overall_ai_score}/100）："
                                    f"{'; '.join(reasons)}，综合判定为AI生成")
                        
                        # 确定AI可能性级别
                        if candidate['perplexity'] < 20:
                            new_likelihood = "极高（几乎确定为AI生成）"
                        elif candidate['perplexity'] < 30:
                            new_likelihood = "高（AI生成可能性大）"
                        else:
                            new_likelihood = "中（可能为AI生成）"
                        
                        # 创建新的分析结果
                        detailed_analysis[idx] = ParagraphAnalysis(
                            paragraph=old_analysis.paragraph,
                            ai_generated=True,  # 更新为AI生成
                            reason=new_reason,
                            perplexity=candidate['perplexity'],
                            ai_likelihood=new_likelihood
                        )
                        
                        reidentified_count += 1
                        print(f"   ✓ 重新识别段落 #{idx+1}: {old_analysis.paragraph[:50]}... -> AI生成 ({'; '.join(reasons)})")
                
                if reidentified_count > 0:
                    # 更新统计数据
                    ai_segments_count += reidentified_count
                    ai_percentage = (ai_segments_count / segment_count) * 100
                    
                    print(f"   二次检测完成：重新识别 {reidentified_count} 个有明显AI特征的段落")
                    print(f"   更新后AI百分比: {ai_percentage:.1f}%")
                    
                    # 更新判断结果说明
                    if 'key_indicators' in ai_likelihood_result:
                        ai_likelihood_result['key_indicators'].insert(0, 
                            f"通过二次检测重新识别了{reidentified_count}个具有明显AI特征的段落，AI比例从{(ai_segments_count-reidentified_count)/segment_count*100:.1f}%提升至{ai_percentage:.1f}%"
                        )
                else:
                    print(f"   二次检测完成：未发现明显被漏判的AI段落")
        
        # 返回最终分析结果（增强版）
        return {
            "ai_percentage": round(ai_percentage, 2),
            "avg_perplexity": avg_perplexity,
            "style_consistency": round(style_score, 3),
            "ai_likelihood": ai_likelihood_result['ai_likelihood'],
            "ai_score": ai_likelihood_result['ai_score'],  # 新增：数值评分
            "confidence": ai_likelihood_result['confidence'],  # 新增：置信度
            "key_indicators": ai_likelihood_result['key_indicators'],  # 新增：关键指标
            "text_type": text_type,  # 新增：文本类型
            "burstiness": burstiness_result,  # 新增：爆发度详情
            "parallel_structures": parallel_structures,  # 新增：平行结构详情
            "ai_vocabulary": ai_vocab_result,  # 新增：AI词汇详情
            "segment_count": segment_count,
            "detailed_analysis": detailed_analysis
        }
    except Exception as e:
        print(f"AI内容检测过程中出现严重错误: {str(e)}")
        # 返回一个最小有效结果，确保至少有ai_percentage为0
        return {
            "ai_percentage": 0,
            "avg_perplexity": 0,
            "style_consistency": 0,
            "ai_likelihood": f"检测失败: {str(e)}",
            "segment_count": 0,
            "detailed_analysis": []
        }

# 保留原有功能以兼容旧接口
async def analyze_segment(segment: str) -> Tuple[bool, str, str]:
    """分析单个文本段落（兼容旧接口）"""
    try:
        is_ai_generated, reason = await llm_client.analyze_text(segment)
        return is_ai_generated, reason, segment
    except Exception as e:
        print(f"分析段落时出错: {str(e)}")
        return False, f"分析出错: {str(e)}", segment

async def detect_ai_content(text: str, window_size: int = 500, step_size: int = 250) -> Tuple[float, List[ParagraphAnalysis]]:
    """检测文本中的AI生成内容（兼容旧接口）"""
    segments = smart_split(text, segment_level="sentence", max_chars=window_size)
    print(f"分割后的片段数量: {len(segments)}")
    
    results = []
    ai_segments_count = 0
    
    valid_segments = [segment for segment in segments if len(segment) >= 20]
    
    if not valid_segments:
        return 0, []
    
    tasks = [analyze_segment(segment) for segment in valid_segments]
    
    MAX_CONCURRENCY = 2
    
    for i in range(0, len(tasks), MAX_CONCURRENCY):
        batch = tasks[i:i+MAX_CONCURRENCY]
        batch_results = await asyncio.gather(*batch, return_exceptions=True)
        
        for result in batch_results:
            if isinstance(result, Exception):
                print(f"段落分析出现异常: {str(result)}")
                continue
                
            is_ai_generated, reason, segment = result
            
            if is_ai_generated:
                ai_segments_count += 1
            
            results.append(ParagraphAnalysis(
                paragraph=segment,
                ai_generated=is_ai_generated,
                reason=reason
            ))
    
    ai_percentage = (ai_segments_count / len(results)) * 100 if results else 0
    
    return ai_percentage, results 