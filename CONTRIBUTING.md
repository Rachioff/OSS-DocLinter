# 贡献指南

感谢你对 OSS-Linter 感兴趣！🎉

OSS-Linter 是一个旨在改善开源文档质量的工具。为了保证代码质量和开发效率，请在提交代码前仔细阅读以下指南。

## 🌟 开发原则

1. **全异步 (Async First)**:
   本项目使用 `FastAPI` 和 `httpx`。所有的 I/O 操作（包括网络请求、数据库查询）**必须**使用 `async/await` 语法。
   - 🚫 **禁止**: 使用同步的 `requests` 库或同步的 `PyGithub` 方法（除非在线程池中运行）。
   - ✅ **推荐**: 使用 `app/services/github_service.py` 中封装好的异步方法。

2. **原子化服务**:
   服务层 (`services/`) 应保持无状态。分析 (`Analysis`) 和 修复 (`Remediation`) 应当解耦，通过前端传递上下文信息。

3. **路由规范**:
   - `main.py` 统一管理 API 版本前缀（如 `/api/v1`）。
   - 各个 `router` 文件中定义的 `prefix` 仅包含业务模块名（如 `/issue`，而不是 `/api/v1/issue`），避免路径重复。

## 🛠 开发环境搭建

请参考 [README.md](./README.md) 中的安装步骤。我们建议使用 VS Code 并安装 Python 和 Pylance 插件以获得最佳体验。

## 🔄 工作流 (Workflow)

1. **Fork** 本仓库到你的 GitHub 账号。
2. **Clone** 你的 Fork 到本地。
3. 创建一个新的分支进行开发：
   ```bash
   git checkout -b feat/add-new-linter-rule
   ```
4. 提交你的修改。请遵循 `Conventional Commits` 规范：
- feat: 新功能
- fix: 修复 Bug
- docs: 文档修改
- refactor: 代码重构
- chore: 构建过程或辅助工具的变动

*示例*: `feat: add support for GitLab repository analysis`

5. 推送分支并提交 `Pull Request`。

## 📐 代码风格
- **格式化**: 我们使用 `black` 进行代码格式化。

- **类型提示**: 所有函数参数和返回值必须包含 Python Type Hints。

```Python
# Good
async def get_repo(owner: str, repo: str) -> dict:
    ...
```
Schema: 数据交互必须通过 `schemas.py` 中的 `Pydantic` 模型进行定义。

## 🧪 测试
在提交 PR 之前，请确保你的代码没有破坏现有功能。 （目前测试框架正在建设中，请暂时确保手动测试 API 能够通过 swagger UI 正常调用）

## 🐛 发现 Bug？
如果你发现了 Bug，请通过 GitHub Issues 提交报告。提交时请包含：

完整的报错堆栈信息 (Traceback)。

复现步骤。

相关的 Request/Response 数据（请注意隐去 Token 等敏感信息）。

感谢你的贡献，让我们一起把开源文档变得更好！ 🚀
