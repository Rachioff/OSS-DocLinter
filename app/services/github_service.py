import httpx
import os
import re
from fastapi import HTTPException
import asyncio

class GitHubService:
    def __init__(self):
        self.token = os.getenv("GITHUB_TOKEN")
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
        }
        if self.token:
            self.headers["Authorization"] = f"Bearer {self.token}"

    @staticmethod
    def parse_github_url(url: str) -> tuple[str, str]:
        clean_url = url.removesuffix(".git")
        
        clean_url = clean_url.rstrip("/")
        
        pattern = r"github\.com/([^/]+)/([^/]+)"
        match = re.search(pattern, clean_url)
        
        if not match:
            raise HTTPException(status_code=400, detail="Invalid GitHub URL format")
        
        return match.group(1), match.group(2)
    
    async def get_repo_metadata(self, owner: str, repo: str) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"https://api.github.com/repos/{owner}/{repo}",
                headers=self.headers
            )

            if resp.status_code == 404:
                raise HTTPException(status_code=404, detail="Repository not found")
            elif resp.status_code != 200:
                raise HTTPException(status_code=resp.status_code, detail="GitHub API error")
            
            return resp.json()
        
    async def _fetch_single_file(self, client: httpx.AsyncClient, owner: str, repo: str, path: str) -> dict | None:
        url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
        try:
            resp = await client.get(url, headers=self.headers)
            if resp.status_code == 200:
                data = resp.json()
                download_url = data.get("download_url")
                if download_url:
                    content_resp = await client.get(download_url)
                    return {"path": path, "content": content_resp.text}
        except Exception:
            return None
    
    async def fetch_repo_files(self, owner: str, repo: str) -> dict:
        # 1. 扩展搜索路径：增加 .github 目录，这是现代开源项目的标准
        targets = {
            "readme": ["README.md", "readme.md", "README.rst", "README.txt"],
            "contributing": [".github/CONTRIBUTING.md", "CONTRIBUTING.md", "docs/CONTRIBUTING.md"],
            "license": ["LICENSE", "LICENSE.txt", "COPYING"],
            "code_of_conduct": [".github/CODE_OF_CONDUCT.md", "CODE_OF_CONDUCT.md"],
            "security": [".github/SECURITY.md", "SECURITY.md"],
            "changelog": ["CHANGELOG.md", "HISTORY.md", "RELEASES.md"]
        }

        results = {}

        # 2. 使用更长的超时时间，防止网络波动
        async with httpx.AsyncClient(timeout=15.0) as client:
            tasks = []
            target_keys = []

            for key, paths in targets.items():
                for path in paths:
                    tasks.append(self._fetch_single_file(client, owner, repo, path))
                    target_keys.append((key, path))

            # 并发获取所有文件
            responses = await asyncio.gather(*tasks, return_exceptions=True)

            found_files = {key: [] for key in targets}

            for i, resp in enumerate(responses):
                # 忽略异常，只处理成功的响应
                if isinstance(resp, dict):
                    key, _ = target_keys[i]
                    found_files[key].append(resp)

            # 选取第一个找到的文件
            for key, files in found_files.items():
                if files:
                    results[key] = files[0]
                else:
                    results[key] = None
            
            # 3. 安全地检查 GitHub Releases (即便失败也不会影响 README)
            # 只有当没找到 CHANGELOG 文件时才检查，节省请求资源
            if results["changelog"] is None:
                try:
                    has_releases = await self._check_github_releases(client, owner, repo)
                    if has_releases:
                        results["changelog"] = {
                            "path": "GitHub Releases",
                            "content": "This project uses GitHub Releases feature for changelog."
                        }
                except Exception as e:
                    print(f"Warning: Failed to check releases: {e}")
                    # 忽略错误，不要让它导致函数崩溃
                    pass
            
        return results

    async def _check_github_releases(self, client: httpx.AsyncClient, owner: str, repo: str) -> bool:
        """检查仓库是否有 GitHub Release 记录"""
        # 务必加上 https://
        url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
        try:
            resp = await client.get(url, headers=self.headers)
            return resp.status_code == 200
        except Exception:
            return False
        
    async def create_issue(self, token: str, owner: str, repo: str, title: str, body: str) -> str:
        """
        使用 httpx 异步创建 Issue
        :param token: 用户的 OAuth Access Token (必须具备 public_repo 权限)
        """
        url = f"https://api.github.com/repos/{owner}/{repo}/issues"
        
        # 这里必须使用用户传进来的 token，而不是 self.default_headers
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"Bearer {token}" 
        }
        
        payload = {
            "title": title,
            "body": body
        }

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(url, headers=headers, json=payload)
                
                if resp.status_code == 201:
                    data = resp.json()
                    return data["html_url"] # 返回 Issue 的网页链接
                elif resp.status_code == 403:
                     # 常见错误：Token 没权限 或 频率限制
                    raise HTTPException(status_code=403, detail="GitHub API permission denied. Check token scope.")
                elif resp.status_code == 404:
                    raise HTTPException(status_code=404, detail="Target repository not found.")
                else:
                    raise HTTPException(
                        status_code=resp.status_code, 
                        detail=f"GitHub API Error: {resp.text}"
                    )
            except httpx.RequestError as e:
                raise HTTPException(status_code=500, detail=f"Network error when connecting to GitHub: {str(e)}")
