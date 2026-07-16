"""
身份分流Prompt模块
根据用户身份（学生、教师、访客等）提供不同的系统提示词和回复策略
"""

import json
import logging
from enum import Enum
from typing import Dict, List, Optional, Any
from pathlib import Path

from src.utils.exceptions import DataLoadError, safe_execute

logger = logging.getLogger(__name__)


class UserRole(str, Enum):
    """用户身份枚举"""
    STUDENT = "student"           # 学生
    TEACHER = "teacher"           # 教师
    STAFF = "staff"               # 行政人员
    VISITOR = "visitor"           # 访客/考生
    PARENT = "parent"             # 家长
    ALUMNI = "alumni"             # 校友

    @classmethod
    def from_string(cls, role_str: str) -> "UserRole":
        """从字符串转换为角色枚举"""
        role_map = {
            "学生": cls.STUDENT,
            "student": cls.STUDENT,
            "教师": cls.TEACHER,
            "老师": cls.TEACHER,
            "teacher": cls.TEACHER,
            "行政": cls.STAFF,
            "行政人员": cls.STAFF,
            "staff": cls.STAFF,
            "访客": cls.VISITOR,
            "考生": cls.VISITOR,
            "visitor": cls.VISITOR,
            "家长": cls.PARENT,
            "parent": cls.PARENT,
            "校友": cls.ALUMNI,
            "alumni": cls.ALUMNI,
        }
        return role_map.get(role_str.lower(), cls.VISITOR)

    @property
    def display_name(self) -> str:
        """获取角色的中文显示名称"""
        names = {
            UserRole.STUDENT: "在校学生",
            UserRole.TEACHER: "教职员工",
            UserRole.STAFF: "行政人员",
            UserRole.VISITOR: "访客/考生",
            UserRole.PARENT: "学生家长",
            UserRole.ALUMNI: "校友",
        }
        return names.get(self, "访客")


# 基础系统提示词 - 所有身份共享
BASE_SYSTEM_PROMPT = """你是"小航助手"，郑州航空工业管理学院（ZUA）的智能校园助手。

【学校简介】
郑州航空工业管理学院是河南省唯一一所具有航空特色的全日制普通本科院校，坐落在河南省郑州市。
学校以航空为特色，管、工为主，文、理、经、法多学科协调发展。

【你的职责】
1. 回答关于郑州航院的各类问题，包括但不限于：校园生活、教学科研、招生就业、行政服务等
2. 提供准确、实用的校园信息服务
3. 帮助用户便捷地获取校园资源和服务信息

【回答原则】
- 始终保持友好、专业、耐心的态度
- 信息准确，不确定的内容请明确告知用户并建议通过官方渠道核实
- 保护隐私，不透露任何个人敏感信息
- 对于超出校园服务范围的问题，礼貌地说明你的服务范围
- 使用简洁清晰的中文回答，必要时使用分点说明

【联系方式】
如果遇到无法回答的问题，建议用户通过以下官方渠道咨询：
- 学校官网：http://www.zua.edu.cn
- 招生办电话：0371-61912556
- 校长办公室：0371-61912666
"""


# 各身份专属提示词
ROLE_SPECIFIC_PROMPTS: Dict[UserRole, str] = {
    UserRole.STUDENT: """
【学生专属服务】
你正在为郑州航院的在校学生提供服务，请重点关注以下内容：

1. 学业相关：
   - 课程安排、选课系统、学分要求
   - 图书馆资源使用、自习室信息
   - 考试安排、成绩查询、绩点计算
   - 转专业、辅修、考研信息
   - 奖学金、助学金评定政策

2. 校园生活：
   - 宿舍管理、水电充值、报修流程
   - 食堂分布、校园卡使用
   - 校园班车、校历时间
   - 社团活动、学生会、校园赛事
   - 医务室、心理咨询服务

3. 就业发展：
   - 招聘会信息、实习机会
   - 就业指导、简历修改建议
   - 创新创业支持

【回答风格】
- 像热心的学长/学姐一样亲切
- 提供具体的操作步骤和注意事项
- 适当给予鼓励和建议
""",

    UserRole.TEACHER: """
【教师专属服务】
你正在为郑州航院的教职员工提供服务，请重点关注以下内容：

1. 教学事务：
   - 教务系统使用、排课调课
   - 学生成绩录入、教学评价
   - 课程建设、教材选用
   - 教学改革、质量工程

2. 科研事务：
   - 科研项目申报、经费管理
   - 论文发表、专利申请
   - 学术交流、会议信息
   - 科研平台、实验室使用

3. 人事行政：
   - 职称评审、岗位聘任
   - 培训进修、考核评优
   - 薪酬福利、社保公积金
   - 工会活动、教职工服务

【回答风格】
- 专业、严谨、高效
- 提供准确的政策依据和办事流程
- 注意区分公开信息和内部信息
""",

    UserRole.STAFF: """
【行政人员专属服务】
你正在为郑州航院的行政人员提供服务，请重点关注以下内容：

1. 办公事务：
   - OA系统使用、公文流转
   - 会议安排、用车预约
   - 印章使用、证明开具
   - 资产管理、采购流程

2. 人事财务：
   - 财务报销、预算管理
   - 考勤管理、请假制度
   - 办公设备、后勤保障

3. 对外联络：
   - 接待流程、会议服务
   - 合作交流、校地对接

【回答风格】
- 高效、规范、条理清晰
- 提供标准化的办事指南
""",

    UserRole.VISITOR: """
【访客/考生专属服务】
你正在为访客或考生提供服务，请重点关注以下内容：

1. 招生咨询：
   - 学校概况、专业介绍
   - 招生计划、录取分数线
   - 报考指南、志愿填报建议
   - 艺术类、空乘类专业招生
   - 中外合作办学项目

2. 校园参观：
   - 校园地图、交通指引
   - 开放日安排、预约参观
   - 周边住宿、餐饮信息

3. 常见问题：
   - 学费标准、奖助学金政策
   - 住宿条件、食堂情况
   - 就业情况、考研升学率
   - 转专业政策、辅修制度

【回答风格】
- 热情、详细、有吸引力
- 充分展示学校的优势和特色
- 鼓励报考，积极引导
""",

    UserRole.PARENT: """
【家长专属服务】
你正在为学生家长提供服务，请重点关注以下内容：

1. 学生培养：
   - 专业前景、就业方向
   - 学风建设、考研情况
   - 国际化交流、联合培养
   - 奖助学金体系

2. 校园生活：
   - 住宿条件、安全管理
   - 饮食卫生、医疗保障
   - 心理健康、辅导员制度
   - 校园文化、社会实践

3. 家校沟通：
   - 成绩查询、学业预警
   - 家长接待日、家长会
   - 辅导员联系方式

【回答风格】
- 亲切、诚恳、让人放心
- 重点回应家长关心的安全和发展问题
- 体现学校的人文关怀和管理规范
""",

    UserRole.ALUMNI: """
【校友专属服务】
你正在为郑州航院校友提供服务，请重点关注以下内容：

1. 校友联络：
   - 校友会组织、地方分会
   - 校友活动、返校日安排
   - 校友通讯录更新

2. 学校发展：
   - 学校最新动态、建设成就
   - 校友捐赠、基金会
   - 校企合作、产学研对接

3. 校友服务：
   - 学历证明、成绩单办理
   - 继续教育、在职深造
   - 就业推荐、创业支持

【回答风格】
- 亲切、温暖、有归属感
- 唤起校友的美好回忆
- 鼓励校友常回家看看
"""
}


class IdentityRouter:
    """身份分流路由器"""

    def __init__(self, prompt_data_path: Optional[str] = None):
        """
        初始化身份分流路由器
        
        Args:
            prompt_data_path: 自定义Prompt数据文件路径（可选）
        """
        self.role_prompts = ROLE_SPECIFIC_PROMPTS.copy()
        self.current_role: UserRole = UserRole.VISITOR
        
        # 如果提供了自定义数据文件，尝试加载
        if prompt_data_path:
            self._load_custom_prompts(prompt_data_path)

    @safe_execute(default_return=None, reraise=True)
    def _load_custom_prompts(self, file_path: str) -> None:
        """
        从JSON文件加载自定义Prompt
        
        Args:
            file_path: JSON文件路径
        """
        path = Path(file_path)
        if not path.exists():
            raise DataLoadError(f"Prompt数据文件不存在", file_path=str(path))
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for role_str, prompt in data.items():
                try:
                    role = UserRole.from_string(role_str)
                    self.role_prompts[role] = prompt
                except ValueError:
                    logger.warning(f"跳过未知的角色: {role_str}")
            
            logger.info(f"已从 {file_path} 加载自定义Prompt")
        except json.JSONDecodeError as e:
            raise DataLoadError(f"Prompt数据文件格式错误: {e}", file_path=str(path))

    def set_role(self, role: UserRole) -> None:
        """
        设置当前用户角色
        
        Args:
            role: 用户角色
        """
        self.current_role = role
        logger.info(f"用户角色已设置为: {role.display_name}")

    def get_role(self) -> UserRole:
        """获取当前用户角色"""
        return self.current_role

    def get_system_prompt(self, role: Optional[UserRole] = None) -> str:
        """
        获取指定角色的完整系统提示词
        
        Args:
            role: 用户角色，默认为当前角色
        
        Returns:
            完整的系统提示词
        """
        target_role = role or self.current_role
        specific_prompt = self.role_prompts.get(target_role, "")
        
        return BASE_SYSTEM_PROMPT + specific_prompt

    def build_messages(
        self,
        user_message: str,
        history: Optional[List[Dict[str, str]]] = None,
        role: Optional[UserRole] = None
    ) -> List[Dict[str, str]]:
        """
        构建发送给API的消息列表
        
        Args:
            user_message: 当前用户消息
            history: 历史对话记录
            role: 用户角色，默认为当前角色
        
        Returns:
            消息列表，格式为 [{"role": "system", "content": "..."}, ...]
        """
        messages = []
        
        # 添加系统提示词
        system_prompt = self.get_system_prompt(role)
        messages.append({"role": "system", "content": system_prompt})
        
        # 添加历史记录
        if history:
            messages.extend(history)
        
        # 添加当前用户消息
        messages.append({"role": "user", "content": user_message})
        
        return messages

    def detect_role_from_message(self, message: str) -> UserRole:
        """
        尝试从用户消息中自动识别角色
        
        Args:
            message: 用户消息文本
        
        Returns:
            识别出的用户角色
        """
        message_lower = message.lower()
        
        # 关键词匹配
        role_keywords = {
            UserRole.STUDENT: ["学生", "同学", "选课", "考试", "绩点", "宿舍", "学分", "课程", "考研", "奖学金"],
            UserRole.TEACHER: ["老师", "教师", "教授", "科研", "项目", "职称", "教学", "论文", "课题"],
            UserRole.STAFF: ["行政", "办公", "报销", "oa", "公文", "会议", "采购", "资产"],
            UserRole.VISITOR: ["考生", "报考", "录取", "分数线", "招生", "专业", "志愿", "参观"],
            UserRole.PARENT: ["家长", "父母", "孩子", "儿子", "女儿", "小孩", "放心"],
            UserRole.ALUMNI: ["校友", "毕业", "母校", "校友会", "返校", "捐赠"],
        }
        
        best_role = UserRole.VISITOR
        max_matches = 0
        
        for role, keywords in role_keywords.items():
            matches = sum(1 for kw in keywords if kw in message_lower)
            if matches > max_matches:
                max_matches = matches
                best_role = role
        
        if max_matches > 0:
            logger.info(f"从消息中识别出角色: {best_role.display_name} (匹配关键词数: {max_matches})")
        else:
            logger.info("未能从消息中识别角色，使用默认访客身份")
        
        return best_role

    @staticmethod
    def get_all_roles() -> List[Dict[str, str]]:
        """
        获取所有可用角色及其显示名称
        
        Returns:
            角色信息列表
        """
        return [
            {"value": role.value, "label": role.display_name}
            for role in UserRole
        ]
