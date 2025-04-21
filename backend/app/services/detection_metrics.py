import numpy as np
import os
import json
import asyncio
from typing import List, Dict, Tuple, Any, Optional
from concurrent.futures import ThreadPoolExecutor
from volcenginesdkarkruntime import Ark
import logging
import re
import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
from .llm_client import llm_client

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("detection_metrics")

def _convert_numpy_types(obj, depth=0):
    """
    将NumPy类型转换为Python原生类型，以便JSON序列化
    
    参数:
        obj: 要转换的对象
        depth: 当前递归深度，用于防止无限递归
        
    返回:
        转换后的对象
    """
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

class VolcenginePrompt:
    """火山引擎大模型不同角度的分析提示"""
    def __init__(self, name: str, system_prompt: str, user_prompt_template: str):
        self.name = name
        self.system_prompt = system_prompt
        self.user_prompt_template = user_prompt_template
    
    def get_user_prompt(self, text: str) -> str:
        """根据模板生成用户提示"""
        return self.user_prompt_template.format(text=text)

class DetectionMetrics:
    """
    多角度AI文本检测指标计算
    使用同一个火山引擎大模型，但从不同角度设计prompt进行分析
    """
    def __init__(self):
        # 使用共享的llm_client替代直接实例化火山引擎客户端
        # 不再需要以下代码
        # self.endpoint_id = os.getenv('ENDPOINT_ID', 'ep-20241229201843-lbwqd')
        # api_key = os.environ.get("ARK_API_KEY", "f1298f35-98b3-4068-82b9-fd0bae492fc7")
        # self.client = Ark(
        #     base_url="https://ark.cn-beijing.volces.com/api/v3",
        #     api_key=api_key,
        # )
        
        # 定义多个不同角度的提示
        self.prompts = [
            # 语言特征角度
            VolcenginePrompt(
                name="语言特征分析",
                system_prompt="""
                你是一个专业的AI生成内容检测器，专注于分析语言特征。你的任务是分析给定文本段落的语言特征，判断它是人类撰写还是AI生成的。
                
                请从以下几个方面分析:
                1. 词汇多样性和丰富度：AI常使用相似词汇和表达
                2. 句式结构变化：人类通常有更多样的句式结构
                3. 标点符号和过渡词使用：AI可能有特定模式
                4. 语言措辞的不自然之处：寻找AI生成文本的特征词
                
                只返回JSON格式，包含以下字段:
                {
                  "is_ai_generated": true/false,
                  "confidence": 0-100,
                  "reason": "详细分析原因",
                  "language_features": "发现的语言特征"
                }
                """,
                user_prompt_template="请从语言特征角度分析这段文本是人类撰写还是AI生成的:\n\n{text}"
            ),
            
            # 思维模式角度
            VolcenginePrompt(
                name="思维模式分析",
                system_prompt="""
                你是一个专业的AI生成内容检测器，专注于分析思维模式。你的任务是分析给定文本段落的思维和逻辑模式，判断它是人类撰写还是AI生成的。
                
                请从以下几个方面分析:
                1. 思维跳跃性：人类思维通常更有跳跃性和不连贯处
                2. 逻辑结构：AI生成内容的逻辑往往过于完美和系统化
                3. 创造性思维与见解：寻找独特的见解和创新思维
                4. 前后矛盾或模棱两可：人类写作中可能存在的特点
                
                只返回JSON格式，包含以下字段:
                {
                  "is_ai_generated": true/false,
                  "confidence": 0-100,
                  "reason": "详细分析原因",
                  "thinking_patterns": "发现的思维模式特征"
                }
                """,
                user_prompt_template="请从思维模式和逻辑结构角度分析这段文本是人类撰写还是AI生成的:\n\n{text}"
            ),
            
            # 情感表达角度
            VolcenginePrompt(
                name="情感表达分析",
                system_prompt="""
                你是一个专业的AI生成内容检测器，专注于分析情感表达。你的任务是分析给定文本段落的情感和主观表达，判断它是人类撰写还是AI生成的。
                
                请从以下几个方面分析:
                1. 情感表达的真实性：AI生成的情感可能显得平淡或不自然
                2. 情感变化与深度：人类表达的情感通常有深度和复杂性
                3. 主观观点与个人色彩：检查文本中个人主观表达的自然程度
                4. 幽默感与讽刺：这些常是AI难以自然表达的
                
                只返回JSON格式，包含以下字段:
                {
                  "is_ai_generated": true/false,
                  "confidence": 0-100,
                  "reason": "详细分析原因",
                  "emotion_analysis": "发现的情感表达特征"
                }
                """,
                user_prompt_template="请从情感表达和主观性角度分析这段文本是人类撰写还是AI生成的:\n\n{text}"
            ),
            
            # 风格一致性角度
            VolcenginePrompt(
                name="风格一致性分析",
                system_prompt="""
                你是一个专业的AI生成内容检测器，专注于分析风格一致性。你的任务是分析给定文本段落的写作风格一致性，判断它是人类撰写还是AI生成的。
                
                请从以下几个方面分析:
                1. 风格突变：人类写作可能有风格突变，AI通常保持一致
                2. 语气变化：检查文本中语气的自然变化程度
                3. 格式统一性：AI常保持过度一致的格式模式
                4. 措辞习惯：个人写作习惯与固定模式的区别
                
                只返回JSON格式，包含以下字段:
                {
                  "is_ai_generated": true/false,
                  "confidence": 0-100,
                  "reason": "详细分析原因",
                  "style_analysis": "发现的风格特征"
                }
                """,
                user_prompt_template="请从风格一致性和写作习惯角度分析这段文本是人类撰写还是AI生成的:\n\n{text}"
            ),
        ]
        
        # 添加一个基础文本特征分析器
        self.metrics_analyzer = MetricsAnalyzer()
    
    async def _call_volcengine_model(self, prompt: VolcenginePrompt, text: str) -> Dict[str, Any]:
        """调用火山引擎模型，使用指定的prompt进行分析"""
        try:
            user_prompt = prompt.get_user_prompt(text)
            
            async def call_model():
                # 使用llm_client而不是直接调用self.client
                llm_response = await llm_client.call_model(
                    system_prompt=prompt.system_prompt,
                    user_prompt=user_prompt
                )
                return llm_response
            
            # 重试机制
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response_text = await call_model()
                    # 解析JSON响应
                    try:
                        result = json.loads(response_text)
                        
                        # 验证必要字段
                        if "is_ai_generated" not in result or "confidence" not in result:
                            logger.warning(f"模型返回结果缺少必要字段: {response_text}")
                            result = {
                                "is_ai_generated": None,
                                "confidence": 0,
                                "reason": f"无效响应格式: {response_text[:100]}..."
                            }
                        
                        # 格式化响应
                        return _convert_numpy_types({
                            "model": prompt.name,
                            "result": result
                        })
                        
                    except json.JSONDecodeError:
                        logger.warning(f"模型返回非JSON格式: {response_text}")
                        # 尝试提取结果
                        ai_result = "AI" in response_text.upper() and "生成" in response_text
                        human_result = "人类" in response_text or "人工" in response_text
                        
                        # 根据文本内容进行判断
                        if ai_result and not human_result:
                            is_ai = True
                            confidence = 80
                        elif human_result and not ai_result:
                            is_ai = False
                            confidence = 80
                        else:
                            # 无法确定
                            is_ai = None
                            confidence = 0
                        
                        return _convert_numpy_types({
                            "model": prompt.name,
                            "result": {
                                "is_ai_generated": is_ai,
                                "confidence": confidence,
                                "reason": f"非JSON响应: {response_text[:100]}..."
                            }
                        })
                        
                except Exception as e:
                    logger.error(f"调用模型时出错 (尝试 {attempt+1}/{max_retries}): {str(e)}")
                    if attempt == max_retries - 1:  # 最后一次尝试
                        raise
                    # 等待一段时间后重试
                    await asyncio.sleep(2 ** attempt)  # 指数退避
            
        except Exception as e:
            logger.error(f"调用火山引擎API时出错: {str(e)}")
            return _convert_numpy_types({
                "model": prompt.name,
                "result": {
                    "is_ai_generated": None,
                    "confidence": 0,
                    "reason": f"API调用失败: {str(e)}"
                }
            })
    
    async def analyze_text(self, text: str) -> Dict[str, Any]:
        """
        综合分析文本，通过多个prompt角度调用火山引擎大模型
        """
        # 并行调用所有prompt
        tasks = [self._call_volcengine_model(prompt, text) for prompt in self.prompts]
        
        # 添加基础特征分析
        features_result = await asyncio.get_event_loop().run_in_executor(
            ThreadPoolExecutor(), 
            lambda: self.metrics_analyzer.analyze_text(text)
        )
        
        # 收集所有结果
        llm_results = await asyncio.gather(*tasks)
        results = llm_results + [features_result]
        
        # 合并所有角度的结果
        models_results = {result["model"]: result["result"] for result in results}
        
        # 计算综合判断
        total_weight = 0
        weighted_score = 0
        ai_votes = 0
        human_votes = 0
        
        # 为不同角度设置权重
        weights = {
            "语言特征分析": 0.25,
            "思维模式分析": 0.25,
            "情感表达分析": 0.20,
            "风格一致性分析": 0.20,
            "特征分析": 0.10
        }
        
        # 计算各角度权重得分
        for model_name, result in models_results.items():
            weight = weights.get(model_name, 0.1)
            
            if result["is_ai_generated"] is not None:
                if result["is_ai_generated"]:
                    ai_votes += weight
                else:
                    human_votes += weight
                
                weighted_score += weight * result["confidence"]
                total_weight += weight
        
        # 防止除零错误
        if total_weight == 0:
            return _convert_numpy_types({
                "is_ai_generated": None,
                "confidence": 0,
                "models_results": models_results,
                "reason": "所有分析角度都未能给出有效判断"
            })
        
        # 计算综合得分
        final_confidence = weighted_score / total_weight
        is_ai_generated = ai_votes > human_votes
        
        # 生成综合原因
        reason_parts = []
        
        # 主要判断依据
        if is_ai_generated:
            reason_parts.append(f"该文本可能是AI生成，综合置信度: {final_confidence:.2f}%。")
        else:
            reason_parts.append(f"该文本可能是人类撰写，综合置信度: {(100-final_confidence):.2f}%。")
        
        # 各角度分析结果
        reason_parts.append("各角度分析结果:")
        for model_name, result in models_results.items():
            if result["is_ai_generated"] is not None:
                judgment = "AI生成" if result["is_ai_generated"] else "人类撰写"
                reason_parts.append(f"- {model_name}: {judgment} (置信度: {result['confidence']:.2f}%)")
                if "reason" in result and result["reason"]:
                    reason = result["reason"]
                    if len(reason) > 100:
                        reason = reason[:100] + "..."
                    reason_parts.append(f"  理由: {reason}")
        
        # 总结特征分析结果
        if "特征分析" in models_results and "metrics" in models_results["特征分析"]:
            metrics = models_results["特征分析"]["metrics"]
            reason_parts.append("文本特征分析:")
            
            if "burstiness" in metrics:
                burstiness = metrics["burstiness"]
                reason_parts.append(f"- 爆发度: {burstiness:.2f} ({'低' if burstiness < 0.5 else '高'})")
            
            if "syntax_analysis" in metrics:
                syntax = metrics["syntax_analysis"]
                reason_parts.append(f"- 句式重复度: {syntax['repetition_score']:.2f} ({'高' if syntax['is_suspicious'] else '正常'})")
            
            if "style_analysis" in metrics:
                style = metrics["style_analysis"]
                reason_parts.append(f"- 风格一致性: 方差{style['style_variance']:.2f} ({'过于一致' if style['is_suspicious'] else '自然变化'})")
        
        result = {
            "is_ai_generated": is_ai_generated,
            "confidence": final_confidence,
            "models_results": models_results,
            "reason": "\n".join(reason_parts)
        }
        
        # 在返回前转换NumPy类型
        return _convert_numpy_types(result)

class MetricsAnalyzer:
    """基础文本特征分析器"""
    def __init__(self):
        self.name = "特征分析"
    
    def calculate_burstiness(self, text: str) -> float:
        """
        计算文本的爆发度(Burstiness)
        爆发度低表示句子长度和句式变化小，更可能是AI生成
        """
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            nltk.download('punkt')
        
        # 将文本分割成句子
        sentences = sent_tokenize(text)
        if len(sentences) <= 1:
            return 0.0  # 只有一个句子无法计算爆发度
        
        # 计算每个句子的长度(词数)
        sentence_lengths = [len(word_tokenize(sent)) for sent in sentences]
        
        # 计算标准差和平均值
        std_deviation = np.std(sentence_lengths)
        mean_length = np.mean(sentence_lengths)
        
        # 计算爆发度: 标准差/平均值
        if mean_length == 0:
            return 0.0
        
        burstiness = std_deviation / mean_length
        return burstiness
    
    def analyze_syntax_patterns(self, text: str) -> Dict[str, Any]:
        """
        语法模式识别
        识别文本中的句法结构模式，高频模式可能表示AI生成
        """
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            nltk.download('punkt')
        
        # 将文本分割成句子
        sentences = sent_tokenize(text)
        if len(sentences) <= 1:
            return {
                "repetition_score": 0.0,
                "pattern_types": 0,
                "is_suspicious": False
            }
        
        # 提取每个句子的前3个词作为模式
        starting_patterns = []
        for sent in sentences:
            words = word_tokenize(sent)
            pattern = " ".join(words[:min(3, len(words))]).lower()
            starting_patterns.append(pattern)
        
        # 计算模式的频率
        pattern_counts = {}
        for pattern in starting_patterns:
            if pattern in pattern_counts:
                pattern_counts[pattern] += 1
            else:
                pattern_counts[pattern] = 1
        
        # 计算重复模式的比例
        repeated_patterns = sum(1 for count in pattern_counts.values() if count > 1)
        pattern_types = len(pattern_counts)
        
        # 句型重复度评分
        repetition_score = repeated_patterns / len(sentences) if sentences else 0.0
        
        return {
            "repetition_score": repetition_score,
            "pattern_types": pattern_types,
            "is_suspicious": repetition_score > 0.3  # 超过30%的句子使用重复模式视为可疑
        }
    
    def analyze_style_consistency(self, text: str) -> Dict[str, Any]:
        """
        风格一致性检测
        分析文本风格特征的一致性
        """
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            nltk.download('punkt')
        
        # 将文本分割成段落
        paragraphs = re.split(r'\n\s*\n', text)
        paragraphs = [p for p in paragraphs if p.strip()]
        
        if len(paragraphs) <= 1:
            return {
                "style_variance": 0.0,
                "is_suspicious": False
            }
        
        # 计算每个段落的风格特征
        features = []
        for para in paragraphs:
            # 1. 平均句长
            sentences = sent_tokenize(para)
            if not sentences:
                continue
                
            words = word_tokenize(para)
            avg_sent_len = len(words) / len(sentences)
            
            # 2. 平均词长
            avg_word_len = sum(len(word) for word in words) / len(words) if words else 0
            
            # 3. 标点符号频率
            punctuation_count = sum(1 for char in para if char in ",.;:!?()[]{}\"'")
            punct_ratio = punctuation_count / len(para) if para else 0
            
            # 将特征添加到列表
            features.append([avg_sent_len, avg_word_len, punct_ratio])
        
        if not features:
            return {
                "style_variance": 0.0,
                "is_suspicious": False
            }
        
        # 计算特征的方差
        features_array = np.array(features)
        style_variance = np.mean(np.var(features_array, axis=0))
        
        # 风格过于一致（方差小）可能表明AI生成
        is_suspicious = style_variance < 0.1
        
        return {
            "style_variance": float(style_variance),
            "is_suspicious": is_suspicious
        }
    
    def analyze_text(self, text: str) -> Dict[str, Any]:
        """执行文本特征分析"""
        burstiness = self.calculate_burstiness(text)
        syntax_analysis = self.analyze_syntax_patterns(text)
        style_analysis = self.analyze_style_consistency(text)
        
        # 综合评分
        ai_score = 0.0
        count = 0
        
        # 爆发度贡献 - 爆发度低表示可能是AI (满分20分)
        if burstiness < 0.5:
            ai_score += 20 * (1 - (burstiness / 0.5))
            count += 1
        
        # 句法模式贡献 (满分20分)
        if syntax_analysis["is_suspicious"]:
            ai_score += 20 * syntax_analysis["repetition_score"]
            count += 1
        
        # 风格一致性贡献 (满分20分)
        if style_analysis["is_suspicious"]:
            ai_score += 20 * (1 - style_analysis["style_variance"] * 10)
            count += 1
        
        # 平均分计算
        final_score = ai_score / count if count > 0 else 0
        
        # 判断是否为AI生成
        is_ai_generated = final_score > 60
        confidence = final_score
        
        result = {
            "model": self.name,
            "result": {
                "is_ai_generated": is_ai_generated,
                "confidence": confidence,
                "reason": f"特征分析: 爆发度={burstiness:.2f}, 句式重复={syntax_analysis['repetition_score']:.2f}, 风格方差={style_analysis['style_variance']:.2f}",
                "metrics": {
                    "burstiness": burstiness,
                    "syntax_analysis": syntax_analysis,
                    "style_analysis": style_analysis
                }
            }
        }
        
        # 在返回前转换NumPy类型
        return _convert_numpy_types(result)

# 创建单例实例
detection_metrics = DetectionMetrics() 