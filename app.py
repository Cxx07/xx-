"""
郑州航院校园助手 - Streamlit 主应用
这是应用的入口文件，负责整合所有功能模块
"""

import os
import sys
import logging
from pathlib import Path
from typing import List, Dict, Optional

import streamlit as st

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.api.silicon_flow import SiliconFlowClient, DEFAULT_MODEL
from src.prompts.identity_router import IdentityRouter, UserRole
from src.utils.exceptions import (
    APIError,
    DataLoadError,
    format_error_for_user,
    safe_execute
)
from src.pages.yellow_pages import render_yellow_pages_page

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 页面配置
st.set_page_config(
    page_title="小航助手 - 郑州航院校园助手",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ==================== 会话状态初始化 ====================
def init_session_state() -> None:
    """初始化会话状态"""
    if "api_key" not in st.session_state:
        st.session_state.api_key = os.environ.get("SILICONFLOW_API_KEY", "")
    
    if "current_role" not in st.session_state:
        st.session_state.current_role = UserRole.VISITOR
    
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "identity_router" not in st.session_state:
        st.session_state.identity_router = IdentityRouter()
    
    if "selected_model" not in st.session_state:
        st.session_state.selected_model = DEFAULT_MODEL
    
    if "temperature" not in st.session_state:
        st.session_state.temperature = 0.7


init_session_state()


# ==================== 侧边栏配置 ====================
def render_sidebar() -> None:
    """渲染侧边栏"""
    with st.sidebar:
        # Logo和标题
        st.markdown("## ✈️ 小航助手")
        st.markdown("**郑州航空工业管理学院** 校园智能助手")
        st.markdown("---")
        
        # API配置
        st.subheader("🔧 API配置")
        api_key = st.text_input(
            "硅基流动 API Key",
            value=st.session_state.api_key,
            type="password",
            placeholder="请输入您的API密钥...",
            help="在 https://cloud.siliconflow.cn 获取您的API密钥"
        )
        if api_key != st.session_state.api_key:
            st.session_state.api_key = api_key
        
        # 模型选择
        model_options = [
            "Qwen/Qwen2.5-7B-Instruct",
            "Qwen/Qwen2.5-72B-Instruct",
            "THUDM/glm-4-9b-chat",
            "meta-llama/Llama-3.1-8B-Instruct",
        ]
        st.session_state.selected_model = st.selectbox(
            "🤖 选择模型",
            options=model_options,
            index=0,
            help="不同模型的性能和响应速度不同"
        )
        
        # 温度参数
        st.session_state.temperature = st.slider(
            "🌡️ 创意程度",
            min_value=0.0,
            max_value=2.0,
            value=0.7,
            step=0.1,
            help="值越高回答越有创意，值越低回答越确定"
        )
        
        st.markdown("---")
        
        # 身份选择
        st.subheader("👤 我的身份")
        roles = IdentityRouter.get_all_roles()
        role_labels = [r["label"] for r in roles]
        role_values = [r["value"] for r in roles]
        
        current_idx = role_values.index(st.session_state.current_role.value) \
            if st.session_state.current_role.value in role_values else 3
        
        selected_role_label = st.selectbox(
            "选择您的身份",
            options=role_labels,
            index=current_idx,
            help="选择身份后，小航将为您提供更个性化的服务"
        )
        
        selected_idx = role_labels.index(selected_role_label)
        selected_role = UserRole(role_values[selected_idx])
        
        if selected_role != st.session_state.current_role:
            st.session_state.current_role = selected_role
            st.session_state.identity_router.set_role(selected_role)
            st.success(f"✨ 已切换为「{selected_role.display_name}」身份")
        
        st.markdown("---")
        
        # 清空对话
        if st.button("🗑️ 清空对话历史", use_container_width=True):
            st.session_state.messages = []
            st.success("对话历史已清空")
        
        # 关于信息
        st.markdown("---")
        st.caption(
            "📚 版本 1.0.0\n\n"
            "💬 如有问题或建议，欢迎反馈！"
        )


# ==================== AI 对话页面 ====================
def get_api_client() -> Optional[SiliconFlowClient]:
    """获取API客户端实例"""
    if not st.session_state.api_key:
        return None
    
    try:
        return SiliconFlowClient(
            api_key=st.session_state.api_key,
            model=st.session_state.selected_model
        )
    except APIError:
        return None


@safe_execute(default_return="抱歉，处理您的请求时出现了错误，请稍后再试。")
def process_user_message(user_input: str) -> str:
    """
    处理用户消息并返回AI回复
    
    Args:
        user_input: 用户输入文本
    
    Returns:
        AI回复文本
    """
    client = get_api_client()
    
    if client is None:
        return (
            "⚠️ **请先配置API密钥**\n\n"
            "请在左侧侧边栏输入您的硅基流动 API Key，然后再开始对话。\n\n"
            "如果还没有API密钥，可以访问 [硅基流动](https://cloud.siliconflow.cn) 免费注册获取。"
        )
    
    # 自动检测身份（如果用户消息中有明显线索）
    router = st.session_state.identity_router
    detected_role = router.detect_role_from_message(user_input)
    
    if detected_role != st.session_state.current_role and detected_role != UserRole.VISITOR:
        # 只在检测到非访客身份且与当前不同时提示
        pass
    
    # 构建消息
    router.set_role(st.session_state.current_role)
    messages = router.build_messages(
        user_message=user_input,
        history=st.session_state.messages
    )
    
    # 调用API
    try:
        with st.spinner("🤔 小航正在思考..."):
            response = client.chat_completion(
                messages=messages,
                temperature=st.session_state.temperature,
                max_tokens=2048
            )
            return response or "抱歉，我暂时无法回答这个问题。"
    except APIError as e:
        error_title, error_detail = format_error_for_user(e)
        return f"**{error_title}**\n\n{error_detail}"


def render_chat_page() -> None:
    """渲染AI对话页面"""
    # 页面标题
    col1, col2 = st.columns([1, 4])
    with col1:
        st.markdown("# ✈️")
    with col2:
        st.title("小航助手")
        st.caption(f"当前身份：**{st.session_state.current_role.display_name}** | 模型：{st.session_state.selected_model.split('/')[-1]}")
    
    st.markdown("---")
    
    # 欢迎信息
    if not st.session_state.messages:
        welcome_messages = {
            UserRole.STUDENT: "🎓 同学你好！我是小航助手，有什么可以帮你的吗？选课、考试、校园生活，尽管问我~",
            UserRole.TEACHER: "👨‍🏫 老师您好！我是小航助手，可以帮您查询教学、科研、人事等相关信息。",
            UserRole.STAFF: "💼 您好！我是小航助手，办公事务、行政流程方面的问题都可以问我。",
            UserRole.VISITOR: "👋 您好！欢迎了解郑州航院！我是小航助手，招生、专业、校园等问题都可以问我~",
            UserRole.PARENT: "👨‍👩‍👧 家长您好！我是小航助手，可以为您介绍学校的培养模式、校园生活等信息。",
            UserRole.ALUMNI: "🎊 校友您好！欢迎回家！我是小航助手，校友会、学校发展等信息都可以为您提供。",
        }
        welcome = welcome_messages.get(st.session_state.current_role, "👋 您好！我是小航助手，有什么可以帮您的吗？")
        
        with st.chat_message("assistant", avatar="✈️"):
            st.markdown(welcome)
        
        # 快捷问题建议
        st.markdown("#### 💡 您可以这样问我：")
        suggestions = _get_role_suggestions(st.session_state.current_role)
        
        sug_cols = st.columns(2)
        for i, sug in enumerate(suggestions):
            with sug_cols[i % 2]:
                if st.button(f"❓ {sug}", key=f"sug_{i}", use_container_width=True):
                    st.session_state.messages.append({"role": "user", "content": sug})
                    st.rerun()
    
    # 显示对话历史
    for msg in st.session_state.messages:
        avatar = "👤" if msg["role"] == "user" else "✈️"
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])
    
    # 用户输入
    user_input = st.chat_input("请输入您的问题...")
    
    if user_input:
        # 显示用户消息
        with st.chat_message("user", avatar="👤"):
            st.markdown(user_input)
        
        # 添加到历史
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        # 获取AI回复
        response = process_user_message(user_input)
        
        # 显示AI回复
        with st.chat_message("assistant", avatar="✈️"):
            st.markdown(response)
        
        # 添加到历史
        st.session_state.messages.append({"role": "assistant", "content": response})


def _get_role_suggestions(role: UserRole) -> List[str]:
    """根据用户角色获取建议问题"""
    suggestions_map = {
        UserRole.STUDENT: [
            "图书馆怎么借书？自习室在哪里？",
            "怎么查成绩？绩点怎么算？",
            "奖学金有哪些？怎么申请？",
            "校园卡丢了怎么办？",
        ],
        UserRole.TEACHER: [
            "怎么录入学生成绩？",
            "科研项目怎么申报？",
            "职称评审需要什么条件？",
            "教务系统怎么用？",
        ],
        UserRole.STAFF: [
            "财务报销流程是什么？",
            "OA系统怎么登录？",
            "会议室怎么预约？",
            "采购流程怎么走？",
        ],
        UserRole.VISITOR: [
            "学校有哪些优势专业？",
            "去年的录取分数线是多少？",
            "学费标准是多少？",
            "宿舍条件怎么样？",
        ],
        UserRole.PARENT: [
            "学校的就业情况怎么样？",
            "孩子的成绩怎么查询？",
            "校园安全管理如何？",
            "奖助学金政策是怎样的？",
        ],
        UserRole.ALUMNI: [
            "怎么加入校友会？",
            "学校最近有什么变化？",
            "返校日是什么时候？",
            "怎么办理学历证明？",
        ],
    }
    return suggestions_map.get(role, suggestions_map[UserRole.VISITOR])


# ==================== 主函数 ====================
def main() -> None:
    """主函数"""
    try:
        # 渲染侧边栏
        render_sidebar()
        
        # 主内容区 - 页面切换
        tab1, tab2 = st.tabs(["💬 智能对话", "📞 电话黄页"])
        
        with tab1:
            render_chat_page()
        
        with tab2:
            data_path = project_root / "data" / "yellow_pages.json"
            render_yellow_pages_page(str(data_path))
    
    except Exception as e:
        logger.exception("应用运行时发生错误")
        error_title, error_detail = format_error_for_user(e)
        st.error(f"**{error_title}**\n\n{error_detail}")


if __name__ == "__main__":
    main()
