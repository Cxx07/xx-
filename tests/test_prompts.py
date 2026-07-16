"""
Prompt 模块单元测试
测试身份分流和 Prompt 路由功能
"""

import sys
import pytest
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.prompts.identity_router import (
    IdentityRouter,
    UserRole,
    BASE_SYSTEM_PROMPT,
    ROLE_SPECIFIC_PROMPTS
)
from src.utils.exceptions import DataLoadError


class TestUserRole:
    """UserRole 枚举测试类"""

    def test_all_roles_exist(self):
        """测试所有角色是否存在"""
        expected_roles = [
            UserRole.STUDENT,
            UserRole.TEACHER,
            UserRole.STAFF,
            UserRole.VISITOR,
            UserRole.PARENT,
            UserRole.ALUMNI
        ]
        for role in expected_roles:
            assert role in UserRole

    def test_from_string_chinese(self):
        """测试从中文字符串转换角色"""
        assert UserRole.from_string("学生") == UserRole.STUDENT
        assert UserRole.from_string("教师") == UserRole.TEACHER
        assert UserRole.from_string("老师") == UserRole.TEACHER
        assert UserRole.from_string("行政") == UserRole.STAFF
        assert UserRole.from_string("考生") == UserRole.VISITOR
        assert UserRole.from_string("访客") == UserRole.VISITOR
        assert UserRole.from_string("家长") == UserRole.PARENT
        assert UserRole.from_string("校友") == UserRole.ALUMNI

    def test_from_string_english(self):
        """测试从英文字符串转换角色"""
        assert UserRole.from_string("student") == UserRole.STUDENT
        assert UserRole.from_string("teacher") == UserRole.TEACHER
        assert UserRole.from_string("staff") == UserRole.STAFF
        assert UserRole.from_string("visitor") == UserRole.VISITOR
        assert UserRole.from_string("parent") == UserRole.PARENT
        assert UserRole.from_string("alumni") == UserRole.ALUMNI

    def test_from_string_unknown(self):
        """测试未知字符串默认返回访客"""
        assert UserRole.from_string("unknown") == UserRole.VISITOR
        assert UserRole.from_string("") == UserRole.VISITOR

    def test_display_name(self):
        """测试角色显示名称"""
        assert UserRole.STUDENT.display_name == "在校学生"
        assert UserRole.TEACHER.display_name == "教职员工"
        assert UserRole.STAFF.display_name == "行政人员"
        assert UserRole.VISITOR.display_name == "访客/考生"
        assert UserRole.PARENT.display_name == "学生家长"
        assert UserRole.ALUMNI.display_name == "校友"


class TestIdentityRouter:
    """IdentityRouter 测试类"""

    def test_init_default_role(self):
        """测试初始化默认角色"""
        router = IdentityRouter()
        assert router.get_role() == UserRole.VISITOR

    def test_set_role(self):
        """测试设置角色"""
        router = IdentityRouter()
        router.set_role(UserRole.STUDENT)
        assert router.get_role() == UserRole.STUDENT

        router.set_role(UserRole.TEACHER)
        assert router.get_role() == UserRole.TEACHER

    def test_get_system_prompt_student(self):
        """测试获取学生身份的系统提示词"""
        router = IdentityRouter()
        prompt = router.get_system_prompt(UserRole.STUDENT)
        
        assert BASE_SYSTEM_PROMPT in prompt
        assert "学生" in prompt
        assert "学业" in prompt

    def test_get_system_prompt_teacher(self):
        """测试获取教师身份的系统提示词"""
        router = IdentityRouter()
        prompt = router.get_system_prompt(UserRole.TEACHER)
        
        assert BASE_SYSTEM_PROMPT in prompt
        assert "教师" in prompt
        assert "教学" in prompt

    def test_get_system_prompt_visitor(self):
        """测试获取访客身份的系统提示词"""
        router = IdentityRouter()
        prompt = router.get_system_prompt(UserRole.VISITOR)
        
        assert BASE_SYSTEM_PROMPT in prompt
        assert "招生" in prompt

    def test_get_system_prompt_default(self):
        """测试获取当前角色的系统提示词"""
        router = IdentityRouter()
        router.set_role(UserRole.PARENT)
        prompt = router.get_system_prompt()
        
        assert BASE_SYSTEM_PROMPT in prompt
        assert "家长" in prompt

    def test_build_messages_with_history(self):
        """测试构建带历史记录的消息"""
        router = IdentityRouter()
        router.set_role(UserRole.STUDENT)
        
        history = [
            {"role": "user", "content": "图书馆怎么借书？"},
            {"role": "assistant", "content": "借书流程是..."}
        ]
        
        messages = router.build_messages(
            user_message="自习室在哪里？",
            history=history
        )
        
        # 验证消息结构
        assert len(messages) == 4  # system + 2 history + user
        assert messages[0]["role"] == "system"
        assert messages[1]["content"] == "图书馆怎么借书？"
        assert messages[2]["content"] == "借书流程是..."
        assert messages[3]["content"] == "自习室在哪里？"

    def test_build_messages_without_history(self):
        """测试构建不带历史记录的消息"""
        router = IdentityRouter()
        messages = router.build_messages(user_message="你好")
        
        assert len(messages) == 2  # system + user
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "你好"

    def test_build_messages_with_specific_role(self):
        """测试使用指定角色构建消息"""
        router = IdentityRouter()
        messages = router.build_messages(
            user_message="分数线是多少？",
            role=UserRole.VISITOR
        )
        
        assert len(messages) == 2
        # 系统提示词应该包含访客相关内容
        assert "招生" in messages[0]["content"]

    def test_detect_role_student_message(self):
        """测试识别学生消息"""
        router = IdentityRouter()
        role = router.detect_role_from_message("选课系统怎么用？我想查成绩")
        assert role == UserRole.STUDENT

    def test_detect_role_teacher_message(self):
        """测试识别教师消息"""
        router = IdentityRouter()
        role = router.detect_role_from_message("科研项目怎么申报？我想评职称")
        assert role == UserRole.TEACHER

    def test_detect_role_visitor_message(self):
        """测试识别访客消息"""
        router = IdentityRouter()
        role = router.detect_role_from_message("录取分数线是多少？我想报考")
        assert role == UserRole.VISITOR

    def test_detect_role_parent_message(self):
        """测试识别家长消息"""
        router = IdentityRouter()
        role = router.detect_role_from_message("我是家长，孩子的成绩怎么查？")
        assert role == UserRole.PARENT

    def test_detect_role_alumni_message(self):
        """测试识别校友消息"""
        router = IdentityRouter()
        role = router.detect_role_from_message("我是校友，想了解校友会的活动")
        assert role == UserRole.ALUMNI

    def test_detect_role_generic_message(self):
        """测试通用消息默认返回访客"""
        router = IdentityRouter()
        role = router.detect_role_from_message("你好")
        assert role == UserRole.VISITOR

    def test_get_all_roles(self):
        """测试获取所有角色列表"""
        roles = IdentityRouter.get_all_roles()
        
        assert len(roles) == 6
        
        # 验证结构
        for role in roles:
            assert "value" in role
            assert "label" in role
        
        # 验证包含学生角色
        values = [r["value"] for r in roles]
        assert "student" in values
        assert "teacher" in values
        assert "visitor" in values


class TestBasePrompts:
    """基础 Prompt 测试"""

    def test_base_prompt_contains_school_info(self):
        """测试基础提示词包含学校信息"""
        assert "郑州航空工业管理学院" in BASE_SYSTEM_PROMPT
        assert "ZUA" in BASE_SYSTEM_PROMPT

    def test_role_prompts_coverage(self):
        """测试所有角色都有对应的提示词"""
        for role in UserRole:
            assert role in ROLE_SPECIFIC_PROMPTS
            assert len(ROLE_SPECIFIC_PROMPTS[role]) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
