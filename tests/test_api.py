"""
API 模块单元测试
测试硅基流动 API 客户端的各项功能
"""

import sys
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.api.silicon_flow import (
    SiliconFlowClient,
    quick_chat,
    DEFAULT_MODEL,
    BASE_URL
)
from src.utils.exceptions import APIError, AuthenticationError, RateLimitError


class TestSiliconFlowClient:
    """SiliconFlowClient 测试类"""

    def test_init_with_valid_api_key(self):
        """测试使用有效 API Key 初始化客户端"""
        client = SiliconFlowClient(api_key="test-api-key-123")
        assert client.api_key == "test-api-key-123"
        assert client.model == DEFAULT_MODEL
        assert client.base_url == BASE_URL
        assert client.timeout == 60

    def test_init_with_custom_model(self):
        """测试使用自定义模型初始化"""
        client = SiliconFlowClient(
            api_key="test-key",
            model="custom-model"
        )
        assert client.model == "custom-model"

    def test_init_with_empty_api_key(self):
        """测试使用空 API Key 初始化应抛出异常"""
        with pytest.raises(APIError, match="API密钥不能为空"):
            SiliconFlowClient(api_key="")

    def test_init_with_none_api_key(self):
        """测试使用 None API Key 初始化应抛出异常"""
        with pytest.raises(APIError):
            SiliconFlowClient(api_key=None)

    def test_headers_setup(self):
        """测试请求头是否正确设置"""
        client = SiliconFlowClient(api_key="test-key")
        headers = client.session.headers
        assert headers["Authorization"] == "Bearer test-key"
        assert headers["Content-Type"] == "application/json"

    def test_extract_content_success(self):
        """测试从成功响应中提取内容"""
        client = SiliconFlowClient(api_key="test-key")
        mock_response = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "这是测试回复"
                    }
                }
            ]
        }
        content = client._extract_content(mock_response)
        assert content == "这是测试回复"

    def test_extract_content_empty_choices(self):
        """测试空 choices 应抛出异常"""
        client = SiliconFlowClient(api_key="test-key")
        with pytest.raises(APIError, match="没有生成内容"):
            client._extract_content({"choices": []})

    def test_extract_content_missing_content(self):
        """测试缺失 content 字段"""
        client = SiliconFlowClient(api_key="test-key")
        mock_response = {
            "choices": [{"message": {"role": "assistant"}}]
        }
        content = client._extract_content(mock_response)
        assert content == ""

    def test_get_usage_info(self):
        """测试获取 token 使用信息"""
        client = SiliconFlowClient(api_key="test-key")
        mock_response = {
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150
            }
        }
        usage = client.get_usage_info(mock_response)
        assert usage["prompt_tokens"] == 100
        assert usage["completion_tokens"] == 50
        assert usage["total_tokens"] == 150

    def test_get_usage_info_empty(self):
        """测试获取空的 token 使用信息"""
        client = SiliconFlowClient(api_key="test-key")
        usage = client.get_usage_info({})
        assert usage["prompt_tokens"] == 0
        assert usage["completion_tokens"] == 0
        assert usage["total_tokens"] == 0

    @patch('src.api.silicon_flow.requests.Session.post')
    def test_chat_completion_success(self, mock_post):
        """测试聊天补全成功"""
        # 模拟响应
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '{"choices": [{"message": {"content": "你好！"}}]}'
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "你好！"}}]
        }
        mock_post.return_value = mock_response

        client = SiliconFlowClient(api_key="test-key")
        messages = [{"role": "user", "content": "你好"}]
        result = client.chat_completion(messages)

        assert result == "你好！"
        mock_post.assert_called_once()

    @patch('src.api.silicon_flow.requests.Session.get')
    def test_list_models_success(self, mock_get):
        """测试获取模型列表成功"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {"id": "model1", "name": "Model 1"},
                {"id": "model2", "name": "Model 2"}
            ]
        }
        mock_get.return_value = mock_response

        client = SiliconFlowClient(api_key="test-key")
        models = client.list_models()

        assert len(models) == 2
        assert models[0]["id"] == "model1"

    def test_validate_api_key_with_empty_key(self):
        """测试空 API Key 的验证"""
        with pytest.raises(APIError):
            client = SiliconFlowClient(api_key="")

    @patch('src.api.silicon_flow.requests.Session.get')
    def test_validate_api_key_success(self, mock_get):
        """测试 API Key 验证成功"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": [{"id": "model1"}]}
        mock_get.return_value = mock_response

        client = SiliconFlowClient(api_key="valid-key")
        assert client.validate_api_key() is True

    @patch('src.api.silicon_flow.requests.Session.get')
    def test_validate_api_key_failure(self, mock_get):
        """测试 API Key 验证失败"""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_get.return_value = mock_response

        client = SiliconFlowClient(api_key="invalid-key")
        assert client.validate_api_key() is False


class TestQuickChat:
    """quick_chat 便捷函数测试"""

    @patch('src.api.silicon_flow.SiliconFlowClient.chat_completion')
    def test_quick_chat_with_system_prompt(self, mock_chat):
        """测试带系统提示词的快速聊天"""
        mock_chat.return_value = "测试回复"

        result = quick_chat(
            api_key="test-key",
            user_message="你好",
            system_prompt="你是助手"
        )

        assert result == "测试回复"
        mock_chat.assert_called_once()

    @patch('src.api.silicon_flow.SiliconFlowClient.chat_completion')
    def test_quick_chat_without_system_prompt(self, mock_chat):
        """测试不带系统提示词的快速聊天"""
        mock_chat.return_value = "回复"

        result = quick_chat(
            api_key="test-key",
            user_message="你好"
        )

        assert result == "回复"

    def test_quick_chat_with_empty_key(self):
        """测试空 API Key 的快速聊天"""
        result = quick_chat(api_key="", user_message="你好")
        assert "抱歉" in result or "无法" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
