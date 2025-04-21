import os
import uuid
import time
from volcenginesdkarkruntime import Ark

class LlmClient:
    """
    LLM 客户端，用于与大语言模型服务通信
    """
    def __init__(self):
        self.endpoint_id = os.getenv('ENDPOINT_ID', 'ep-20241229201843-lbwqd')  # 从环境变量获取模型 ID，默认使用提供的ID
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
    
    def analyze_text(self, text, is_ai_generated=False, context=None):
        """
        分析文本是否为AI生成，并提供原因
        
        Args:
            text: 要分析的文本
            is_ai_generated: 是否已知是AI生成的内容
            context: 可选的上下文信息
            
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
        
        # 如果已知是AI生成的，添加这个信息到提示中
        if is_ai_generated:
            user_prompt = f"以下是一段AI生成的文本，请分析为什么它看起来像AI生成的:\n\n{text}"
        else:
            user_prompt = f"请分析以下文本段落是人类撰写还是AI生成的:\n\n{text}"
            
        # 发送请求
        request_id = str(uuid.uuid4())
        completion = self.query(system_prompt, user_prompt, request_id)
        
        if completion:
            try:
                # 尝试从响应中提取结果
                response_text = completion.choices[0].message.content
                
                # 这里需要解析JSON响应，但为简化代码暂不实现
                # 在实际应用中，应该使用json.loads解析响应
                
                # 简单模拟：如果响应中包含"is_ai_generated": true
                is_ai = "is_ai_generated\": true" in response_text.lower() or "\"is_ai_generated\":true" in response_text.lower()
                
                # 提取reason部分 - 简化实现
                reason_start = response_text.find("\"reason\":")
                reason = "无法确定原因" if reason_start == -1 else response_text[reason_start+10:].split("\"")[1]
                
                return is_ai, reason
            except Exception as e:
                print(f"解析LLM响应时出错: {str(e)}")
                return None, f"分析过程出错: {str(e)}"
        
        return None, "无法获取LLM响应"

# 创建单例实例
llm_client = LlmClient() 