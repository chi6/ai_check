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

def segment_sentences(blocks: List[str], max_chars: int = 300) -> List[str]:
    """将段落按句子分割，确保每个片段不超过最大字符数"""
    result = []
    for block in blocks:
        sentences = sent_tokenize(block)
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
    根据困惑度、风格一致性、AI内容比例和段落数量估计AI生成可能性
    
    添加了特殊情况处理：
    - 当段落数量少时，减少对风格一致性的依赖
    - 当AI比例高时，提高AI生成可能性
    """
    # 当段落数量少于2时，风格一致性参数不可靠，完全忽略风格一致性
    if segment_count < 2:
        if perplexity < 20:
            return "高（AI生成可能性大）"
        elif perplexity < 30:
            # 当段落少且困惑度中等时，AI比例权重很高
            if ai_percentage > 50:
                return "高（AI生成可能性大）"
            elif ai_percentage > 0:  # 只要有任何被标记为AI的段落
                return "中（可能为AI生成）"
            else:
                return "低（更可能为人类写作）"
        else:
            # 对于高困惑度的情况，只有当AI比例很高时才认为可能是AI
            if ai_percentage > 80:
                return "中（可能为AI生成）"
            else:
                return "低（更可能为人类写作）"
    
    # 当风格一致性异常低(接近0)但困惑度明显为AI特征时，仍可能是AI生成
    if style < 0.2 and perplexity < 20:
        if ai_percentage > 50:
            return "高（AI生成可能性大）" 
        else:
            return "中（可能为AI生成）"
    
    # 当AI比例特别高时，即使其他指标一般，也提高AI可能性
    if ai_percentage > 75:
        if perplexity < 30:
            return "高（AI生成可能性大）"
        else:
            return "中（可能为AI生成）"
    
    # 标准判断逻辑（原有逻辑，但放宽了风格一致性要求）
    if perplexity < 20 and style > 0.85:
        return "高（AI生成可能性大）"
    elif perplexity < 30 and style > 0.75:
        return "中（可能为AI生成）"
    else:
        # 如果困惑度和风格一致性不明显，但AI百分比较高，仍可能是AI
        if ai_percentage > 50 and perplexity < 35:
            return "中（可能为AI生成）"
        else:
            return "低（更可能为人类写作）"

async def analyze_segment_comprehensive(segment: str) -> Dict[str, Any]:
    """综合分析文本片段，计算困惑度和获取LLM评估"""
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
        
        # 根据困惑度推断初步AI可能性
        if perplexity < 20:
            ai_likelihood = "高（AI生成可能性大）"
            initial_ai_judgment = True
        elif perplexity < 30:
            ai_likelihood = "中（可能为AI生成）"
            initial_ai_judgment = perplexity < 25  # 25作为中等值的分界点
        else:
            ai_likelihood = "低（更可能为人类写作）"
            initial_ai_judgment = False
        
        # 将困惑度和初步判断作为上下文传递给LLM进行分析
        context = {
            "perplexity": perplexity,
            "initial_likelihood": ai_likelihood,
            "initial_judgment": initial_ai_judgment
        }
        
        # 使用LLM客户端分析文本，将困惑度作为上下文传入
        try:
            is_ai_generated, reason = await llm_client.analyze_text(segment, context=context)
        except Exception as e:
            print(f"调用LLM客户端分析文本时出错: {str(e)}")
            # 当LLM分析失败时，使用困惑度来进行基本判断
            is_ai_generated = initial_ai_judgment
            reason = f"LLM分析失败，基于困惑度({perplexity:.2f})推断: {str(e)}"
        
        # 最终判断说明逻辑（修改为根据LLM判断调整AI可能性）
        final_ai_likelihood = ai_likelihood  # 先使用初步判断作为默认值
        
        # 当LLM判断与困惑度计算结果矛盾时
        if is_ai_generated and "低（更可能为人类写作）" in ai_likelihood:
            # LLM认为是AI但困惑度高，调整ai_likelihood
            final_ai_likelihood = "中（可能为AI生成）"  # 修改为中等可能性
            if "困惑度" not in reason:
                reason += f"（注意：LLM判断为AI生成，但困惑度为{perplexity:.2f}，较高）"
        elif not is_ai_generated and "高（AI生成可能性大）" in ai_likelihood:
            # LLM认为是人类但困惑度低，调整ai_likelihood
            final_ai_likelihood = "中（可能为AI生成）"  # 修改为中等可能性
            if "困惑度" not in reason:
                reason += f"（注意：LLM判断为人类创作，但困惑度为{perplexity:.2f}，非常低）"
        
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
        
        # 估计整体AI生成可能性
        ai_likelihood = estimate_ai_likelihood(avg_perplexity, style_score, ai_percentage, segment_count)
        
        # 返回最终分析结果
        return {
            "ai_percentage": round(ai_percentage, 2),
            "avg_perplexity": avg_perplexity,
            "style_consistency": round(style_score, 3),
            "ai_likelihood": ai_likelihood,
            "segment_count": segment_count,  # 添加段落数量信息
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