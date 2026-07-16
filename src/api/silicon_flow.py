"""
硅基流动 (SiliconFlow) API 调用模块
封装与硅基流动大语言模型服务的交互
"""

import json
import time
import logging
from typing import List, Dict, Optional, Any, Generator

import requests

from src.utils.exceptions import (
    APIError,
    safe_execute,
    handle_api_error
)

logger = logging.getLogger(__name__)

# 硅基流动API基础地址
BASE_URL = "https://api.siliconflow.cn/v1"

# 默认模型配置
DEFAULT_MODEL = "Qwen/Qwen2.5-7B-Instruct"
DEFAULT_MAX_TOKENS = 2048
DEFAULT_TEMPERATURE = 0.7
DEFAULT_TIMEOUT = 60


class SiliconFlowClient:
    """硅基流动API客户端"""

    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_MODEL,
        base_url: str = BASE_URL,
        timeout: int = DEFAULT_TIMEOUT
    ):
        """
        初始化API客户端
        
        Args:
            api_key: 硅基流动API密钥
            model: 使用的模型名称
            base_url: API基础地址
            timeout: 请求超时时间（秒）
        """
        if not api_key:
            raise APIError("API密钥不能为空，请在设置中配置您的硅基流动API密钥")
        
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()
        self._setup_headers()

    def _setup_headers(self) -> None:
        """设置请求头"""
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        })

    @safe_execute(default_return=None, reraise=True)
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        stream: bool = False,
        **kwargs
    ) -> Optional[str]:
        """
        发送聊天补全请求
        
        Args:
            messages: 消息列表，格式为 [{"role": "user", "content": "..."}, ...]
            temperature: 采样温度 (0.0-2.0)
            max_tokens: 最大生成token数
            stream: 是否启用流式输出
            **kwargs: 其他传递给API的参数
        
        Returns:
            模型生成的回复文本
        
        Raises:
            APIError: API调用失败时抛出
        """
        url = f"{self.base_url}/chat/completions"
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
            **kwargs
        }

        logger.info(f"发送API请求: model={self.model}, messages_count={len(messages)}")
        start_time = time.time()

        try:
            response = self.session.post(
                url,
                json=payload,
                timeout=self.timeout
            )
            
            elapsed = time.time() - start_time
            logger.info(f"API响应: status={response.status_code}, elapsed={elapsed:.2f}s")

            # 处理错误状态码
            handle_api_error(response.status_code, response.text)

            # 解析响应
            result = response.json()
            
            if stream:
                return self._handle_stream_response(result)
            
            return self._extract_content(result)

        except requests.Timeout:
            raise APIError(
                message="请求超时",
                details=f"API请求在 {self.timeout} 秒内未响应"
            )
        except requests.ConnectionError:
            raise APIError(
                message="网络连接失败",
                details="无法连接到硅基流动API服务，请检查网络连接"
            )
        except json.JSONDecodeError as e:
            raise APIError(
                message="响应解析失败",
                details=f"无法解析API响应: {str(e)}"
            )

    def _extract_content(self, response_data: Dict[str, Any]) -> str:
        """
        从API响应中提取生成的文本内容
        
        Args:
            response_data: API响应的JSON数据
        
        Returns:
            提取的文本内容
        """
        try:
            choices = response_data.get("choices", [])
            if not choices:
                raise APIError(
                    message="API响应中没有生成内容",
                    details=json.dumps(response_data, ensure_ascii=False)[:500]
                )
            
            message = choices[0].get("message", {})
            content = message.get("content", "")
            
            if not content:
                logger.warning("API返回的内容为空")
            
            return content

        except (KeyError, IndexError) as e:
            raise APIError(
                message="响应格式错误",
                details=f"无法从响应中提取内容: {str(e)}"
            )

    def _handle_stream_response(self, response_data: Dict[str, Any]) -> str:
        """
        处理流式响应（简化版本，收集所有内容）
        
        Args:
            response_data: 流式响应数据
        
        Returns:
            合并后的文本内容
        """
        # 对于非流式的stream=True情况（实际实现中应处理SSE）
        return self._extract_content(response_data)

    @safe_execute(default_return=[])
    def list_models(self) -> List[Dict[str, Any]]:
        """
        获取可用模型列表
        
        Returns:
            模型信息列表
        """
        url = f"{self.base_url}/models"
        
        try:
            response = self.session.get(url, timeout=self.timeout)
            handle_api_error(response.status_code, response.text)
            
            data = response.json()
            return data.get("data", [])
        except Exception as e:
            logger.error(f"获取模型列表失败: {e}")
            return []

    def validate_api_key(self) -> bool:
        """
        验证API密钥是否有效
        
        Returns:
            True表示有效，False表示无效
        """
        try:
            models = self.list_models()
            return len(models) > 0
        except APIError:
            return False
        except Exception:
            return False

    def get_usage_info(self, response_data: Dict[str, Any]) -> Dict[str, int]:
        """
        从响应中提取token使用信息
        
        Args:
            response_data: API响应数据
        
        Returns:
            包含prompt_tokens, completion_tokens, total_tokens的字典
        """
        usage = response_data.get("usage", {})
        return {
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0)
        }


# 便捷函数
@safe_execute(default_return="抱歉，我暂时无法回答您的问题，请稍后再试。")
def quick_chat(
    api_key: str,
    user_message: str,
    system_prompt: Optional[str] = None,
    model: str = DEFAULT_MODEL,
    **kwargs
) -> str:
    """
    便捷的单轮对话函数
    
    Args:
        api_key: API密钥
        user_message: 用户消息
        system_prompt: 系统提示词（可选）
        model: 模型名称
        **kwargs: 其他参数
    
    Returns:
        模型回复
    """
    client = SiliconFlowClient(api_key=api_key, model=model)
    
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_message})
    
    return client.chat_completion(messages, **kwargs) or "抱歉，我暂时无法回答您的问题。"
