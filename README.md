# OSS-Linter (Open Source Documentation Linter)

[![Python](https://img.shields.io/badge/Python-3.12%2B-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.95%2B-009688)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

**OSS-Linter** 是一个智能化的开源项目文档评估与修复平台，是一个Web应用形式的软件。它利用 **LLM (大语言模型)** 和 **静态分析工具 (Linters)**，自动检测 GitHub 仓库中的文档（如 README, Contributing, License 等）的完整性与规范性，并提供一键式的自动化修复和 Issue 提交功能。

## ✨ 核心特性

- **🔍 多维文档分析**：原子化并行运行 LLM 语义分析与 Markdown Linter 语法检查。
- **🤖 AI 驱动修复**：基于分析报告，利用 LLM 生成符合上下文的文档修复建议。
- **⚡️ 自动化 PR 流程**：用户确认修改后，系统自动执行 Fork -> Branch -> Commit -> Pull Request 全流程。
- **📝 智能 Issue 生成**：(新功能) 对于无需直接修改代码的问题，自动撰写语气礼貌、格式规范的 Issue 草稿并提交到原仓库。
- **🚀 全异步架构**：基于 FastAPI + httpx 构建，确保高并发下的极速响应。

## 🛠 技术栈

- **后端框架**: [FastAPI](https://fastapi.tiangolo.com/)
- **网络请求**: [httpx](https://www.python-httpx.org/) (全异步处理)
- **AI 服务**: OpenAI API / LangChain
- **认证服务**: GitHub OAuth 2.0 + JWT
- **部署**: Docker / Uvicorn

## 📂 项目结构

```
app
├── routers/          # API 路由层
│   ├── analysis.py   # 文档抓取与分析
│   ├── auth.py       # GitHub OAuth 认证
│   ├── issue.py      # Issue 生成与提交
│   └── remediation.py# PR 修复流程
├── services/         # 业务逻辑层
│   ├── analysis_service.py
│   ├── auth_service.py
│   ├── github_service.py # 基于 httpx 的 GitHub API 封装
│   ├── issue_service.py
│   └── llm_service.py    # LLM 交互封装
├── schemas.py        # Pydantic 数据模型
├── config.py         # 环境变量配置
└── main.py           # 应用入口
```

## 🚀 快速开始

> 本项目应当是一个Web应用，目前尚未进行部署，故若想本地运行可以参照以下步骤，将来等有财力酌情进行部署

**前置要求**

- Python 3.12+
- 一个 GitHub OAuth App (获取 Client ID 和 Secret)
- OpenAI API Key (或其他 LLM 密钥)

**安装步骤**

> 本项目推荐您使用uv作为项目包管理工具

1.  克隆仓库
    ```bash
    git clone https://github.com/your-username/oss-linter.git
    cd oss-linter
    ```
2.  创建虚拟环境并安装依赖
    ```bash
    python -m venv venv
    source venv/bin/activate  # Windows 使用 `venv\Scripts\activate`
    pip install -r requirements.txt
    ```
3.  配置环境变量 复制 `.env.example` 为 `.env` 并填入以下信息：
    ```ini
    # App Config
    APP_ENV=development

    # GitHub OAuth
    GITHUB_CLIENT_ID=your_client_id
    GITHUB_CLIENT_SECRET=your_client_secret

    # GitHub Token (用于后端只读分析，防止速率限制)
    GITHUB_TOKEN=your_personal_access_token

    # LLM
    OPENAI_API_KEY=sk-xxxx
    ```
4.  启动服务
    ```bash
    uvicorn app.main:app --reload
    ```

## 🤝 贡献

我们非常欢迎社区贡献！请查阅 CONTRIBUTING.md 了解详细的开发规范和提交流程。

## 📄 许可证

本项目采用 `MIT License` 开源。