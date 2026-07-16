"""
异常处理模块单元测试
测试各类异常和工具函数
"""

import sys
import pytest
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.utils.exceptions import (
    APIError,
    AuthenticationError,
    RateLimitError,
    DataLoadError,
    ConfigurationError,
    safe_execute,
    handle_api_error,
    format_error_for_user
)


class TestAPIError:
    """APIError 异常测试类"""

    def test_api_error_message(self):
        """测试 API 错误消息"""
        error = APIError(message="测试错误")
        assert "测试错误" in str(error)

    def test_api_error_with_status_code(self):
        """测试带状态码的 API 错误"""
        error = APIError(message="请求失败", status_code=500)
        error_str = str(error)
        assert "请求失败" in error_str
        assert "500" in error_str

    def test_api_error_with_details(self):
        """测试带详情的 API 错误"""
        error = APIError(message="错误", details="详细错误信息")
        error_str = str(error)
        assert "错误" in error_str
        assert "详细错误信息" in error_str


class TestSpecificAPIErrors:
    """特定 API 错误子类测试"""

    def test_authentication_error_is_api_error(self):
        """测试认证错误是 API 错误的子类"""
        error = AuthenticationError(message="认证失败")
        assert isinstance(error, APIError)

    def test_rate_limit_error_is_api_error(self):
        """测试速率限制错误是 API 错误的子类"""
        error = RateLimitError(message="请求过于频繁")
        assert isinstance(error, APIError)


class TestDataLoadError:
    """DataLoadError 异常测试类"""

    def test_data_load_error_message(self):
        """测试数据加载错误消息"""
        error = DataLoadError(message="加载失败")
        assert "加载失败" in str(error)

    def test_data_load_error_with_file_path(self):
        """测试带文件路径的数据加载错误"""
        error = DataLoadError(message="文件不存在", file_path="/path/to/file.json")
        error_str = str(error)
        assert "文件不存在" in error_str
        assert "/path/to/file.json" in error_str


class TestHandleApiError:
    """handle_api_error 函数测试"""

    def test_handle_401_error(self):
        """测试处理 401 认证错误"""
        with pytest.raises(AuthenticationError, match="API密钥无效"):
            handle_api_error(401, "Unauthorized")

    def test_handle_429_error(self):
        """测试处理 429 速率限制错误"""
        with pytest.raises(RateLimitError, match="请求过于频繁"):
            handle_api_error(429, "Rate limit exceeded")

    def test_handle_500_error(self):
        """测试处理 500 服务器错误"""
        with pytest.raises(APIError, match="API请求失败"):
            handle_api_error(500, "Internal Server Error")

    def test_handle_404_error(self):
        """测试处理 404 错误"""
        with pytest.raises(APIError):
            handle_api_error(404, "Not Found")

    def test_handle_200_no_error(self):
        """测试 200 状态码不抛出异常"""
        handle_api_error(200, "OK")  # 不应抛出异常


class TestFormatErrorForUser:
    """format_error_for_user 函数测试"""

    def test_format_authentication_error(self):
        """测试格式化认证错误"""
        error = AuthenticationError(message="密钥无效")
        title, detail = format_error_for_user(error)
        assert "认证" in title or "🔐" in title
        assert "API密钥" in detail

    def test_format_rate_limit_error(self):
        """测试格式化速率限制错误"""
        error = RateLimitError(message="频繁")
        title, detail = format_error_for_user(error)
        assert "频繁" in title or "⏳" in title

    def test_format_api_error(self):
        """测试格式化通用 API 错误"""
        error = APIError(message="连接失败")
        title, detail = format_error_for_user(error)
        assert "服务" in title or "⚠️" in title

    def test_format_data_load_error(self):
        """测试格式化数据加载错误"""
        error = DataLoadError(message="文件损坏")
        title, detail = format_error_for_user(error)
        assert "数据" in title or "📂" in title

    def test_format_configuration_error(self):
        """测试格式化配置错误"""
        error = ConfigurationError("缺少配置项")
        title, detail = format_error_for_user(error)
        assert "配置" in title or "⚙️" in title

    def test_format_generic_error(self):
        """测试格式化通用错误"""
        error = Exception("未知错误")
        title, detail = format_error_for_user(error)
        assert "错误" in title or "❌" in title


class TestSafeExecute:
    """safe_execute 装饰器测试"""

    def test_safe_execute_no_error(self):
        """测试正常执行无错误"""
        @safe_execute(default_return="默认值")
        def normal_func():
            return "成功"
        
        assert normal_func() == "成功"

    def test_safe_execute_with_api_error(self):
        """测试捕获 API 错误"""
        @safe_execute(default_return="默认值")
        def error_func():
            raise APIError(message="API错误")
        
        assert error_func() == "默认值"

    def test_safe_execute_with_data_error(self):
        """测试捕获数据加载错误"""
        @safe_execute(default_return=[])
        def error_func():
            raise DataLoadError(message="加载错误")
        
        assert error_func() == []

    def test_safe_execute_with_generic_error(self):
        """测试捕获通用异常"""
        @safe_execute(default_return=None)
        def error_func():
            raise ValueError("值错误")
        
        assert error_func() is None

    def test_safe_execute_with_reraise(self):
        """测试重新抛出异常"""
        @safe_execute(default_return="默认", reraise=True)
        def error_func():
            raise APIError(message="错误")
        
        with pytest.raises(APIError):
            error_func()

    def test_safe_execute_preserves_function_name(self):
        """测试装饰器保留函数名"""
        @safe_execute(default_return=None)
        def my_special_function():
            pass
        
        assert my_special_function.__name__ == "my_special_function"

    def test_safe_execute_with_arguments(self):
        """测试带参数的函数"""
        @safe_execute(default_return=0)
        def add(a, b):
            return a + b
        
        assert add(2, 3) == 5
        assert add(a=10, b=20) == 30


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
