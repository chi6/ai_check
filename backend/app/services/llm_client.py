import os
import uuid
import json
import time
import asyncio
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
        system_prompt = """
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
        
        # 如果提供了指标数据，添加到系统提示中
        if context and isinstance(context, dict):
            metrics_info = []
            if 'perplexity' in context:
                metrics_info.append(f"计算出的困惑度(Perplexity): {context['perplexity']:.2f} (值低表示可能是AI生成)")
            if 'burstiness' in context:
                metrics_info.append(f"计算出的爆发度(Burstiness): {context['burstiness']:.2f} (值低表示可能是AI生成)")
            
            if metrics_info:
                metrics_text = "\n".join(metrics_info)
                system_prompt += f"\n\n我们已经预先计算了一些指标数据，请将其纳入你的考虑：\n{metrics_text}"
        
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
                
                return is_ai, reason
            except json.JSONDecodeError:
                # 如果无法解析完整JSON，使用简单的文本匹配
                is_ai = "is_ai_generated\": true" in response_text.lower() or "\"is_ai_generated\":true" in response_text.lower()
                
                # 提取reason部分 - 简化实现
                reason_start = response_text.find("\"reason\":")
                reason = "无法确定原因" if reason_start == -1 else response_text[reason_start+10:].split("\"")[1]
                
                return is_ai, reason
                
        except Exception as e:
            print(f"分析文本时出错: {str(e)}")
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