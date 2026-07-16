# ✈️ 小航助手 - 郑州航院校园助手

> 一个基于 Streamlit 和大语言模型的郑州航空工业管理学院智能校园助手

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

## 📋 项目简介

小航助手是为郑州航空工业管理学院（ZUA）师生打造的智能校园助手。项目基于 Streamlit 构建 Web 界面，通过调用硅基流动（SiliconFlow）的大语言模型 API，为用户提供智能化的校园信息咨询服务。

### ✨ 主要功能

- **💬 智能对话**：基于大语言模型的自然语言问答，支持多种身份的个性化服务
- **👤 身份分流**：针对学生、教师、行政人员、访客/考生、家长、校友等不同身份提供定制化回答
- **📞 电话黄页**：校园各部门、学院、服务机构的联系方式查询，支持分类筛选和关键词搜索
- **🔧 异常处理**：完善的异常捕获和用户友好的错误提示
- **⚙️ 灵活配置**：支持多模型选择、温度参数调节、API密钥配置

## 🏗️ 项目结构

```
xiaohang_helper/
├── src/                          # 源代码目录
│   ├── __init__.py
│   ├── app.py                    # Streamlit 主应用入口
│   ├── api/                      # API 调用模块
│   │   ├── __init__.py
│   │   └── silicon_flow.py       # 硅基流动 API 封装
│   ├── prompts/                  # Prompt 模板模块
│   │   ├── __init__.py
│   │   └── identity_router.py    # 身份分流 Prompt 路由器
│   ├── utils/                    # 工具模块
│   │   ├── __init__.py
│   │   └── exceptions.py         # 异常捕获与处理
│   └── pages/                    # 页面模块
│       ├── __init__.py
│       └── yellow_pages.py       # 电话黄页页面
├── data/                         # 数据目录
│   ├── yellow_pages.json         # 电话黄页数据
│   └── custom_prompts.json       # 自定义 Prompt 模板
├── tests/                        # 测试目录
│   ├── __init__.py
│   ├── test_api.py               # API 模块测试
│   └── test_prompts.py           # Prompt 模块测试
├── requirements.txt              # Python 依赖
├── .gitignore                    # Git 忽略配置
└── README.md                     # 项目说明文档
```

## 🚀 快速开始

### 环境要求

- Python 3.9 或更高版本
- 有效的硅基流动 API Key（在 [硅基流动官网](https://cloud.siliconflow.cn) 免费注册获取）

### 安装步骤

1. **克隆或下载项目**

```bash
cd xiaohang_helper
```

2. **创建虚拟环境（推荐）**

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

3. **安装依赖**

```bash
pip install -r requirements.txt
```

4. **配置 API Key（可选）**

可以通过环境变量设置 API Key，也可以在应用启动后在侧边栏输入：

```bash
# Windows
set SILICONFLOW_API_KEY=your_api_key_here

# macOS / Linux
export SILICONFLOW_API_KEY=your_api_key_here
```

5. **启动应用**

```bash
cd xiaohang_helper
streamlit run src/app.py
```

应用将在浏览器中自动打开，默认地址为 `http://localhost:8501`

## 📖 使用指南

### 智能对话

1. 在左侧侧边栏输入您的硅基流动 API Key
2. 选择您的身份（学生、教师、访客等），小航将为您提供更个性化的服务
3. 在底部输入框中输入问题，按回车发送
4. 小航会根据您的身份和问题给出相应的回答

### 电话黄页

1. 点击顶部的「📞 电话黄页」标签
2. 在搜索框输入关键词（部门名称、电话、地址等）
3. 或使用分类筛选器浏览特定类别的联系方式
4. 点击电话号码可直接拨打（需设备支持）

### 身份说明

| 身份 | 适用人群 | 服务重点 |
|------|---------|---------|
| 在校学生 | 在读本科生、研究生 | 学业、校园生活、就业发展 |
| 教职员工 | 教师、科研人员 | 教学、科研、人事行政 |
| 行政人员 | 机关处室工作人员 | 办公事务、财务、后勤 |
| 访客/考生 | 考生、社会访客 | 招生咨询、校园参观、报考指南 |
| 学生家长 | 在读学生家长 | 培养模式、校园生活、家校沟通 |
| 校友 | 已毕业校友 | 校友会、学校发展、校友服务 |

## 🧪 运行测试

项目包含单元测试，使用 pytest 运行：

```bash
# 运行所有测试
pytest

# 运行测试并显示覆盖率
pytest --cov=src

# 运行特定测试文件
pytest tests/test_api.py
```

## 🔧 自定义配置

### 添加自定义黄页数据

编辑 `data/yellow_pages.json` 文件，按以下格式添加条目：

```json
{
  "name": "部门名称",
  "department": "上级部门",
  "category": "分类",
  "phone": ["电话号码1", "电话号码2"],
  "address": "地址",
  "email": "邮箱",
  "description": "描述说明"
}
```

### 自定义 Prompt 模板

编辑 `data/custom_prompts.json` 文件，为不同身份设置自定义的系统提示词。

## 📝 开发说明

### 核心模块说明

| 模块 | 文件 | 功能 |
|------|------|------|
| API 客户端 | `src/api/silicon_flow.py` | 封装硅基流动 API 调用，支持聊天补全、模型列表等 |
| 身份路由 | `src/prompts/identity_router.py` | 根据用户身份构建不同的系统提示词，支持自动身份识别 |
| 异常处理 | `src/utils/exceptions.py` | 统一的异常类、错误处理装饰器、用户友好的错误格式化 |
| 电话黄页 | `src/pages/yellow_pages.py` | 黄页数据加载、搜索、分类筛选和页面渲染 |

### 扩展建议

- 添加更多校园服务功能（如课表查询、成绩查询等，需对接学校API）
- 支持多轮对话的上下文管理
- 添加用户反馈和问题上报功能
- 集成更多AI模型提供商
- 添加语音输入和输出功能

## ⚠️ 注意事项

1. **API 安全**：请勿将您的 API Key 提交到公共代码仓库
2. **数据准确性**：电话黄页数据仅供参考，如有变动请以学校官方公布为准
3. **使用限额**：请注意您的 API 调用额度，避免超出配额
4. **内容审核**：AI 生成的内容可能存在不准确的情况，请核实重要信息

## 📄 许可证

本项目采用 MIT 许可证，详见 [LICENSE](LICENSE) 文件。

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📮 联系方式

如有问题或建议，欢迎通过以下方式联系：

- 提交 GitHub Issue
- 发送邮件至项目维护者

---

**郑州航空工业管理学院** - Zhengzhou University of Aeronautics

> 本项目为非官方校园助手，仅供学习和参考使用。
