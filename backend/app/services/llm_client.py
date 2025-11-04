import os
import uuid
import json
import time
import asyncio
import re
from volcenginesdkarkruntime import Ark
from concurrent.futures import ThreadPoolExecutor

class LlmClient:
    """
    LLM 客户端，用于与大语言模型服务通信
    """
    def __init__(self):
        self.endpoint_id = os.getenv('ENDPOINT_ID', 'ep-20250422142640-ksbch')  # 从环境变量获取模型 ID，默认使用提供的ID
        self.responses = {}  # 存储请求的响应
        self.client = Ark(
            base_url="https://ark.cn-beijing.volces.com/api/v3",
            api_key=os.environ.get("ARK_API_KEY", "f1298f35-98b3-4068-82b9-fd0bae492fc7"),
        )
        
    def query(self, system_message, user_message, request_id=None):
        """
        发送用户消息并获取响应
        
        Args:
            system_message: 系统消息内容
            user_message: 用户消息内容
            request_id: 请求ID，如果不提供将自动生成
            
        Returns:
            模型响应对象
        """
        if request_id is None:
            request_id = str(uuid.uuid4())
            
        try:
            completion = self.client.chat.completions.create(
                model=self.endpoint_id,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message},
                ],
            )
            # 存储响应
            self.responses[request_id] = completion
            return completion
        except Exception as e:
            print(f"调用LLM API时出错: {str(e)}")
            return None
    
    def _detect_text_type_simple(self, text: str) -> str:
        """简单检测文本类型"""
        academic_indicators = 0
        text_lower = text.lower()
        
        # 检测学术特征
        if any(word in text_lower for word in ['research', 'study', 'analysis', 'findings']):
            academic_indicators += 1
        if 'et al' in text_lower or re.search(r'\(\w+,?\s+\d{4}\)', text):
            academic_indicators += 1
        if any(word in text_lower for word in ['furthermore', 'moreover', 'consequently']):
            academic_indicators += 1
            
        return 'academic' if academic_indicators >= 2 else 'general'
    
    def _create_academic_prompt(self) -> str:
        """创建针对学术文本的检测提示词"""
        return """你是一个专业的AI生成内容检测专家，专门识别由GPT-4、Claude、ChatGPT等现代AI模型生成的学术文本。

🎯 针对学术文本，请重点关注以下AI生成特征：

1. **过度规范的结构特征**（关键！）：
   ❌ 平行结构使用过多（如：三个分号连接的平行子句）
   ❌ 冒号后跟多个分号的模式（冒号：A; B; and C）**← 这是最典型的AI特征！**
   ❌ 句子长度过于一致（变化很小）
   ❌ 每个观点都有完美的支撑和例证
   ❌ 逻辑链过于完整，没有跳跃或省略

2. **AI词汇使用特征**：
   ❌ 高频使用："exhibit", "characteristics", "significant", "crucial", "fundamental"
   ❌ 过度使用抽象名词化结构
   ❌ 缺乏领域特定的术语变体
   ❌ 修饰语过于规范（如总是"significant"而不是"considerable"或"notable"）

3. **引用和格式特征**：
   ❌ 引用格式过于完美统一
   ❌ 缺乏引用的自然变化（如有时用"et al."，有时列出所有作者）
   ❌ 引用位置过于规范（总是在句末）

4. **语义和逻辑特征**：
   ❌ 缺乏个人观点或批判性思考
   ❌ 观点表达过于中neutral和全面
   ❌ 没有"顺便提一下"或"值得注意的是"之类的补充
   ❌ 论述过于完整，没有"遗留问题"或"需要进一步研究"

5. **人类学术写作的特征**（AI通常缺乏）：
   ✅ 句子长度有自然变化（长短句交替）
   ✅ 偶尔出现非正式表达或口语化
   ✅ 引用方式有变化
   ✅ 某些观点可能阐述不够完整
   ✅ 可能有轻微的语法不规范

⚠️ **判断标准**（请严格执行）：
- 如果检测到"冒号+多个分号"模式，**必须判定为AI生成**（is_ai_generated: true）
- 如果检测到3个或以上显著AI特征，**应判定为AI生成**
- 如果同时出现多个AI词汇（exhibit, characteristics, significant等）且结构过于规范，**应判定为AI生成**
- 学术文本本身具有规范性，但AI文本会"过度规范"、"过于完美"，缺乏人类写作的自然变化
- **重要**：宁可误判为AI，也不要漏掉明显的AI特征
- **对于明显的AI模式（如完美的平行结构、AI高频词汇组合），即使只有1-2个特征也应判定为AI**

请返回JSON格式：
{
  "is_ai_generated": true/false,
  "confidence": 0-100,
  "reason": "详细分析，指出具体的AI特征或人类特征",
  "key_indicators": ["指标1", "指标2", ...]
}
        """
    
    def _create_general_prompt(self) -> str:
        """创建通用文本的检测提示词"""
        return """
        你是一个专业的AI生成内容检测器。你的任务是分析给定的文本段落，判断它是人类撰写还是AI生成的。
        请注意以下特征:
        1. 低困惑度和过于流畅的表达
        2. 词汇使用不自然，缺乏人类语言的变化性
        3. 句式结构重复，缺乏多样化表达
        4. 逻辑过于完美，缺乏人类思维的跳跃性
        
        请仅返回JSON格式，包含以下字段:
        {
          "is_ai_generated": true/false,
          "confidence": 0-100,
          "reason": "详细解释为什么你认为是人类或AI生成的文本"
        }
        """
    
    async def analyze_text(self, text, is_ai_generated=False, context=None):
        """
        异步分析文本是否为AI生成，并提供原因
        
        Args:
            text: 要分析的文本
            is_ai_generated: 是否已知是AI生成的内容
            context: 可选的上下文信息，包含其他评估指标的数据
            
        Returns:
            (bool, str): 返回判断结果和原因
        """
        # 检测文本类型，生成针对性的提示词
        text_type = self._detect_text_type_simple(text)
        
        if text_type == 'academic':
            system_prompt = self._create_academic_prompt()
        else:
            system_prompt = self._create_general_prompt()
        
        # 如果提供了指标数据，添加到系统提示中
        if context and isinstance(context, dict):
            metrics_info = []
            
            # AI评分（最重要的指标）
            if 'ai_score' in context:
                ai_score = context['ai_score']
                metrics_info.append(f"**AI评分: {ai_score}/100**")
                
                if ai_score >= 60:
                    metrics_info.append("  → 评分较高，强烈倾向于AI生成")
                elif ai_score >= 50:
                    metrics_info.append("  → 评分中等偏高，倾向于AI生成")
                elif ai_score >= 40:
                    metrics_info.append("  → 评分中等，可能是AI生成")
                else:
                    metrics_info.append("  → 评分较低，更可能是人类写作")
            
            # AI可能性评估
            if 'ai_likelihood' in context:
                metrics_info.append(f"初步判断: {context['ai_likelihood']}")
            
            # 关键指标
            if 'key_indicators' in context and context['key_indicators']:
                metrics_info.append("\n检测到的关键AI特征:")
                for indicator in context['key_indicators']:
                    metrics_info.append(f"  • {indicator}")
            
            # 困惑度
            if 'perplexity' in context:
                perplexity = context['perplexity']
                metrics_info.append(f"\n困惑度(Perplexity): {perplexity:.2f}")
                
                if perplexity < 20:
                    metrics_info.append("  → 困惑度非常低，支持AI生成判断")
                elif perplexity < 30:
                    metrics_info.append("  → 困惑度中等偏低，可能是AI生成")
                else:
                    metrics_info.append("  → 困惑度较高，更倾向于人类创作")
            
            if 'burstiness' in context:
                metrics_info.append(f"爆发度(Burstiness): {context['burstiness']:.2f} (值低表示可能是AI生成)")
            
            if metrics_info:
                metrics_text = "\n".join(metrics_info)
                guidance = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 **预计算的量化指标**
{metrics_text}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**判断指导**（重要，请严格遵守）：
- 如果AI评分≥40，**倾向于判定为AI生成**（is_ai_generated: true）
- 如果AI评分≥50且检测到关键AI特征，**必须判定为AI生成**
- 如果AI评分≥60，**强烈判定为AI生成**，除非有明确的人类写作证据
- 特别是如果检测到"冒号+多个分号"、"平行结构"、"子句级爆发度极低"，这些都是**强烈的AI信号**
- 请以量化指标为主要依据，文本主观感受为辅助参考
- **警告**：不要因为文本"读起来流畅"就判定为人类写作，AI生成的文本通常非常流畅！
""".format(metrics_text=metrics_text)
                system_prompt += guidance
        
        # 如果已知是AI生成的，添加这个信息到提示中
        if is_ai_generated:
            user_prompt = f"以下是一段AI生成的文本，请分析为什么它看起来像AI生成的:\n\n{text}"
        else:
            user_prompt = f"请分析以下文本段落是人类撰写还是AI生成的:\n\n{text}"
        
        try:
            # 使用异步方法调用模型
            response_text = await self.call_model(system_prompt, user_prompt)
            
            try:
                # 尝试解析JSON响应
                response_data = json.loads(response_text)
                is_ai = response_data.get("is_ai_generated", False)
                confidence = response_data.get("confidence", 50)
                reason = response_data.get("reason", "未提供原因")
                
                # 添加困惑度信息到原因中（如果有）
                if context and 'perplexity' in context:
                    perplexity = context['perplexity']
                    if perplexity < 20 and "困惑度" not in reason:
                        reason += f"（困惑度为{perplexity:.2f}，非常低，支持AI生成判断）"
                    elif perplexity > 35 and is_ai:
                        reason += f"（需注意，困惑度为{perplexity:.2f}，较高，与AI生成特征不完全一致）"
                
                return is_ai, reason
            except json.JSONDecodeError:
                # 如果无法解析完整JSON，使用简单的文本匹配
                is_ai = "is_ai_generated\": true" in response_text.lower() or "\"is_ai_generated\":true" in response_text.lower()
                
                # 提取reason部分 - 简化实现
                reason_start = response_text.find("\"reason\":")
                reason = "无法确定原因" if reason_start == -1 else response_text[reason_start+10:].split("\"")[1]
                
                # 添加困惑度信息（如果有）
                if context and 'perplexity' in context:
                    perplexity = context['perplexity']
                    reason += f"（困惑度：{perplexity:.2f}）"
                
                return is_ai, reason
                
        except Exception as e:
            print(f"分析文本时出错: {str(e)}")
            # 如果提供了困惑度，在错误时使用困惑度简单判断
            if context and 'perplexity' in context:
                perplexity = context['perplexity']
                is_ai_guess = perplexity < 20
                return is_ai_guess, f"LLM分析失败，基于困惑度({perplexity:.2f})推断: {str(e)}"
            return False, f"分析过程出错: {str(e)}"

    async def call_model(self, system_prompt, user_prompt):
        """
        异步调用大模型并返回JSON格式结果
        
        Args:
            system_prompt: 系统提示
            user_prompt: 用户提示
            
        Returns:
            str: 模型返回的JSON格式文本
        """
        # 在线程池中执行同步API调用
        with ThreadPoolExecutor() as executor:
            def _call_api():
                try:
                    completion = self.client.chat.completions.create(
                        model=self.endpoint_id,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                    )
                    return completion
                except Exception as e:
                    print(f"调用LLM API时出错: {str(e)}")
                    return None
            
            # 异步执行调用
            completion = await asyncio.get_event_loop().run_in_executor(executor, _call_api)
            
            if not completion:
                raise Exception("无法获取LLM响应")
                
            # 提取响应文本
            response_text = completion.choices[0].message.content
            
            # 尝试提取JSON部分
            try:
                # 尝试直接解析整个响应
                json.loads(response_text)
                return response_text
            except json.JSONDecodeError:
                # 尝试从响应中提取JSON字符串
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}') + 1
                
                if start_idx >= 0 and end_idx > start_idx:
                    json_str = response_text[start_idx:end_idx]
                    try:
                        # 验证提取的是有效JSON
                        json.loads(json_str)
                        return json_str
                    except:
                        pass
                
                # 如果无法提取JSON，返回原始响应
                return response_text

# 创建单例实例
llm_client = LlmClient() 