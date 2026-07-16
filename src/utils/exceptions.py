"""
异常捕获与处理模块
提供统一的异常处理机制，确保应用稳定运行
"""

import logging
import traceback
from functools import wraps
from typing import Callable, Any, Optional, Tuple

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class APIError(Exception):
    """API调用异常"""
    def __init__(self, message: str, status_code: Optional[int] = None, details: Optional[str] = None):
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(self.message)

    def __str__(self) -> str:
        base = f"API错误: {self.message}"
        if self.status_code:
            base += f" (状态码: {self.status_code})"
        if self.details:
            base += f"\n详细信息: {self.details}"
        return base


class AuthenticationError(APIError):
    """认证错误（如API Key无效）"""
    pass


class RateLimitError(APIError):
    """速率限制错误"""
    pass


class DataLoadError(Exception):
    """数据加载异常"""
    def __init__(self, message: str, file_path: Optional[str] = None):
        self.message = message
        self.file_path = file_path
        super().__init__(self.message)

    def __str__(self) -> str:
        base = f"数据加载错误: {self.message}"
        if self.file_path:
            base += f" (文件: {self.file_path})"
        return base


class ConfigurationError(Exception):
    """配置错误"""
    def __init__(self, message: str = "配置错误"):
        self.message = message
        super().__init__(self.message)

    def __str__(self) -> str:
        return f"配置错误: {self.message}"


def safe_execute(default_return: Any = None, 
                  error_message: str = "操作执行失败",
                  reraise: bool = False) -> Callable:
    """
    安全执行装饰器，捕获并处理函数中的异常
    
    Args:
        default_return: 异常时返回的默认值
        error_message: 错误提示信息
        reraise: 是否重新抛出异常
    
    Returns:
        装饰后的函数
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except APIError as e:
                logger.error(f"API错误 [{func.__name__}]: {e}")
                if reraise:
                    raise
                return default_return
            except DataLoadError as e:
                logger.error(f"数据加载错误 [{func.__name__}]: {e}")
                if reraise:
                    raise
                return default_return
            except Exception as e:
                error_detail = traceback.format_exc()
                logger.error(f"未预期的错误 [{func.__name__}]: {e}\n{error_detail}")
                if reraise:
                    raise
                return default_return
        return wrapper
    return decorator


def handle_api_error(response_status: int, response_text: str) -> None:
    """
    根据API响应状态码抛出相应异常
    
    Args:
        response_status: HTTP响应状态码
        response_text: 响应文本内容
    
    Raises:
        AuthenticationError: 认证失败
        RateLimitError: 速率限制
        APIError: 其他API错误
    """
    if response_status == 401:
        raise AuthenticationError(
            message="API密钥无效或已过期",
            status_code=response_status,
            details=response_text
        )
    elif response_status == 429:
        raise RateLimitError(
            message="请求过于频繁，请稍后再试",
            status_code=response_status,
            details=response_text
        )
    elif response_status >= 400:
        raise APIError(
            message=f"API请求失败 (状态码: {response_status})",
            status_code=response_status,
            details=response_text[:500]  # 限制详情长度
        )


def format_error_for_user(error: Exception) -> Tuple[str, str]:
    """
    将异常格式化为用户友好的提示信息
    
    Args:
        error: 异常对象
    
    Returns:
        (错误标题, 错误详情) 元组
    """
    if isinstance(error, AuthenticationError):
        return "🔐 认证失败", "请检查您的API密钥是否正确配置。可以在侧边栏的设置中重新输入API密钥。"
    elif isinstance(error, RateLimitError):
        return "⏳ 请求过于频繁", "API调用频率已达上限，请等待一段时间后再尝试。"
    elif isinstance(error, APIError):
        return "⚠️ 服务调用失败", f"无法连接到AI服务：{error.message}"
    elif isinstance(error, DataLoadError):
        return "📂 数据加载失败", f"无法加载数据文件：{error.message}"
    elif isinstance(error, ConfigurationError):
        return "⚙️ 配置错误", f"配置项缺失或无效：{error.message}"
    else:
        return "❌ 发生错误", f"程序运行时出现未预期的错误：{str(error)}"
