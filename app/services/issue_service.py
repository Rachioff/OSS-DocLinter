# services/issue_service.py

from app.services.llm_service import LLMService
from app.services.github_service import GitHubService
from app.schemas import IssueGenerateRequest, IssueCreateRequest
from fastapi import HTTPException

class IssueService:
    def __init__(self):
        self.llm_service = LLMService()
        self.github_service = GitHubService()

    async def generate_draft(self, request: IssueGenerateRequest) -> dict:
        """
        业务逻辑：调用 LLM 生成 Issue 草稿
        """
        # 这里复用 llm_service 的能力
        # 假设 llm_service 中有一个 helper 方法处理 prompt
        draft = await self.llm_service.generate_issue_content(
            file_path=request.file_path,
            issue_desc=request.issue_description,
            context=request.original_content
        )
        return draft

    async def submit_issue(self, request: IssueCreateRequest, user_token: str) -> dict:
        """
        业务逻辑：将用户确认的内容提交给 GitHub
        """
        # 1. 简单的参数校验
        if not request.title.strip() or not request.body.strip():
            raise HTTPException(status_code=400, detail="Title and Body cannot be empty")

        # 2. 调用 GitHubService (只使用 httpx)
        issue_url = await self.github_service.create_issue(
            token=user_token,
            owner=request.target_owner,
            repo=request.target_repo,
            title=request.title,
            body=request.body
        )

        return {
            "issue_url": issue_url,
            "status": "success"
        }