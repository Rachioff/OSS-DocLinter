import httpx
import time
import base64
import asyncio
from typing import Optional
from fastapi import HTTPException
from app.services.llm_service import LLMService

class RemediationService:
    def __init__(self, github_token: str):
        self.github_token = github_token
        self.llm_service = LLMService()
        self.headers = {
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github.v3+json"
        }

    async def generate_fix(
        self,
        original_content: str,
        issue_id: str,
        custom_instruction: Optional[str] = None
    ) -> str:
        """
        生成修复后的文档
        """
        # issue_id 到描述的映射 (简化版，后续可以从数据库获取)
        issue_descriptions = {
            "missing_readme": "文档缺失 README 文件",
            "missing_install": "缺失安装指南",
            "missing_usage": "缺失使用说明",
            "missing_contributing": "缺失贡献指南",
            "missing_license": "缺失许可证信息",
            "missing_security": "缺失安全策略",
            "missing_changelog": "缺失变更日志",
        }
        
        description = issue_descriptions.get(issue_id, f"文档问题: {issue_id}")
        
        return await self.llm_service.generate_fix(
            original_content=original_content,
            issue_id=issue_id,
            issue_description=description,
            custom_instruction=custom_instruction
        )
    
    async def create_pull_request(
        self,
        target_owner: str,
        target_repo: str,
        file_path: str,
        final_content: str,
        commit_message: str,
        pr_title: str
    ) -> dict:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # 1. 获取当前用户信息
            user_resp = await client.get(
                "https://api.github.com/user",
                headers=self.headers
            )
            if user_resp.status_code != 200:
                raise HTTPException(status_code=401, detail="Invalid GitHub token")
            
            current_user = user_resp.json()["login"]
            
            # 【修复逻辑 1】判断是否是同一个仓库
            is_own_repo = (current_user == target_owner)

            # 2. Fork 仓库 (如果是自己修自己的仓库，不需要 Fork)
            if not is_own_repo:
                fork_resp = await client.post(
                    f"https://api.github.com/repos/{target_owner}/{target_repo}/forks",
                    headers=self.headers
                )
                if fork_resp.status_code not in [200, 202]:
                    raise HTTPException(status_code=400, detail="Failed to fork repository")
                # 等待 fork 完成
                await asyncio.sleep(2)
            
            # 3. 获取目标仓库的默认分支 (API调用保持不变)
            repo_resp = await client.get(
                f"https://api.github.com/repos/{target_owner}/{target_repo}",
                headers=self.headers
            )
            default_branch = repo_resp.json()["default_branch"]
            
            # 4. 获取 Base SHA
            # 注意：如果是同源，直接去目标仓库拿；如果是 Fork，通常也是基于目标仓库的最新状态
            # 这里为了简单，我们始终基于 current_user 的仓库状态进行操作（假设 Fork 已同步）
            ref_resp = await client.get(
                f"https://api.github.com/repos/{current_user}/{target_repo}/git/refs/heads/{default_branch}",
                headers=self.headers
            )
            if ref_resp.status_code != 200:
                # 尝试从 target_owner 拿（针对未同步的 Fork 或 同源情况）
                ref_resp = await client.get(
                    f"https://api.github.com/repos/{target_owner}/{target_repo}/git/refs/heads/{default_branch}",
                    headers=self.headers
                )
            
            if ref_resp.status_code != 200:
                 raise HTTPException(status_code=400, detail="Failed to get branch reference")

            base_sha = ref_resp.json()["object"]["sha"]
            
            # 5. 创建新分支
            # 【修复逻辑 2】更改分支前缀，避免与名为 'docs' 的既有分支冲突
            # 这里的命名改为 'oss-linter/fix-...' 
            branch_name = f"oss-linter/fix-{int(time.time())}"
            
            create_branch_resp = await client.post(
                f"https://api.github.com/repos/{current_user}/{target_repo}/git/refs",
                headers=self.headers,
                json={
                    "ref": f"refs/heads/{branch_name}",
                    "sha": base_sha
                }
            )
            
            if create_branch_resp.status_code != 201:
                # 增加错误详情返回，方便调试
                error_msg = create_branch_resp.json().get("message", "Unknown error")
                raise HTTPException(status_code=400, detail=f"Failed to create branch: {error_msg}")
            
            # 6. 获取文件当前 SHA (保持不变)
            file_sha = None
            file_resp = await client.get(
                f"https://api.github.com/repos/{current_user}/{target_repo}/contents/{file_path}?ref={branch_name}",
                headers=self.headers
            )
            if file_resp.status_code == 200:
                file_sha = file_resp.json()["sha"]
            
            # 7. 创建或更新文件 (保持不变)
            content_base64 = base64.b64encode(final_content.encode()).decode()
            update_payload = {
                "message": commit_message,
                "content": content_base64,
                "branch": branch_name
            }
            if file_sha:
                update_payload["sha"] = file_sha
            
            update_resp = await client.put(
                f"https://api.github.com/repos/{current_user}/{target_repo}/contents/{file_path}",
                headers=self.headers,
                json=update_payload
            )
            
            if update_resp.status_code not in [200, 201]:
                raise HTTPException(status_code=400, detail="Failed to update file")
            
            # 8. 创建 Pull Request
            # 【修复逻辑 3】同源仓库时，head 仅传 branch_name
            pr_head = f"{current_user}:{branch_name}"
            if is_own_repo:
                pr_head = branch_name

            pr_resp = await client.post(
                f"https://api.github.com/repos/{target_owner}/{target_repo}/pulls",
                headers=self.headers,
                json={
                    "title": pr_title,
                    "head": pr_head,
                    "base": default_branch,
                    "body": "This PR was automatically generated by OSS-DocLinter to improve documentation quality."
                }
            )
            
            if pr_resp.status_code != 201:
                error_msg = pr_resp.json().get("message", "Unknown error")
                # 这里经常报 "Validation Failed" 如果没有差异的话
                raise HTTPException(status_code=400, detail=f"Failed to create PR: {error_msg}")
            
            pr_data = pr_resp.json()
            
            return {
                "pr_url": pr_data["html_url"],
                "status": "success",
                "message": "Pull Request created successfully"
            }