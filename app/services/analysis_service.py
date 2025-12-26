from datetime import datetime, timezone
from app.schemas import (
    AnalyzeResponse, RepoInfo, FileContent, HealthCheck, Report, Issue,
    Severity, IssueCategory
)
from app.services.github_service import GitHubService
from app.services.llm_service import LLMService
from app.services.linter_service import LinterService

class AnalysisService:
    def __init__(self):
        self.github_service = GitHubService()
        self.llm_service = LLMService()
        self.linter_service = LinterService()

    async def analyze_repo(self, url: str) -> AnalyzeResponse:
        # 1. 解析 URL & 获取元数据 & 获取文件 (保持不变)
        owner, repo = self.github_service.parse_github_url(url)
        repo_meta = await self.github_service.get_repo_metadata(owner, repo)
        files_data = await self.github_service.fetch_repo_files(owner, repo)
        
        # 4. 构建 RepoInfo (保持不变)
        repo_info = RepoInfo(
            owner=repo_meta["owner"]["login"],
            repo=repo_meta["name"],
            default_branch=repo_meta["default_branch"],
            url=repo_meta["html_url"]
        )
        
        # 5. 构建 Files 响应 (保持不变)
        files_response = {}
        for key, data in files_data.items():
            if data:
                files_response[key] = FileContent(path=data["path"], content=data["content"])
            else:
                files_response[key] = FileContent(path=f"{key.upper()}.md", content=None)

        # 6. 执行 Health Check (保持不变)
        health_check = HealthCheck(
            has_readme=files_data.get("readme") is not None,
            has_contributing=files_data.get("contributing") is not None,
            has_license=files_data.get("license") is not None,
            has_code_of_conduct=files_data.get("code_of_conduct") is not None,
            has_security_policy=files_data.get("security") is not None,
            has_changelog=files_data.get("changelog") is not None
        )

        # ---------------------------------------------------------
        # 核心修改区域开始
        # ---------------------------------------------------------

        # 7. 调用 LLM 并处理 Issue
        llm_report = await self.llm_service.analyze_documentation_completeness(files_data)
        
        # [修改 1] 获取 LLM 的 issues 并转换为对象
        completeness_issues = self._convert_issues(llm_report.get("issues", []))
        
        # [修改 2] 补充 Health Check 发现的缺失文件问题
        # 注意：这可能会增加新的扣分项
        completeness_issues = self._add_health_check_issues(completeness_issues, health_check)
        
        # [修改 3] 【关键修复】手动计算 LLM 得分 (满分 70)
        # 我们不再信任 llm_report["overall_score"]，因为 LLM 算术很差
        llm_max_score = 70
        llm_deductions = sum(issue.score_deduction for issue in completeness_issues)
        llm_final_score = max(0, llm_max_score - llm_deductions)

        # 8. 运行 Linter 服务 (满分 30)
        all_linter_issues = []
        for key, file_obj in files_data.items():
            if file_obj and file_obj["content"] and file_obj["path"].endswith(".md"):
                result = self.linter_service.lint_file(file_obj["content"], file_obj["path"])
                all_linter_issues.extend(result["issues"])

        # [修改 4] 手动计算 Linter 得分，修复 MD040 硬编码问题
        score_breakdown = {
            "structure": 10,
            "syntax": 10,
            "code": 5,
            "links": 5
        }
        
        syntax_deductions = 0
        md013_deductions = 0
        
        for issue in all_linter_issues:
            deduction = issue.score_deduction
            
            if issue.id in ["MD001", "MD041"]:
                score_breakdown["structure"] -= deduction
            elif issue.id == "MD040":
                # [修复] 使用真实的 deduction (3.0)，不再硬编码 0.5
                score_breakdown["code"] -= deduction
            elif issue.id in ["MD042", "MD043"]:
                score_breakdown["links"] -= deduction
            elif issue.id == "MD013":
                md013_deductions += deduction
            else:
                syntax_deductions += deduction

        # 计算 Syntax 最终扣分 (行长问题封顶)
        syntax_loss = syntax_deductions + min(5, md013_deductions)
        score_breakdown["syntax"] -= syntax_loss

        linter_final_score = (
            max(0, score_breakdown["structure"]) +
            max(0, score_breakdown["syntax"]) +
            max(0, score_breakdown["code"]) +
            max(0, score_breakdown["links"])
        )

        # ---------------------------------------------------------
        # 核心修改区域结束
        # ---------------------------------------------------------

        # 9. 合并所有 issues
        all_issues = completeness_issues + all_linter_issues

        # 10. 计算最终总分
        final_score = llm_final_score + linter_final_score
        # 双重保险，防止溢出
        final_score = max(0, min(100, final_score))

        return AnalyzeResponse(
            repo_info=repo_info,
            files=files_response,
            health_check=health_check,
            report=Report(
                overall_score=int(final_score),
                timestamp=datetime.now(timezone.utc).isoformat(),
                issues=all_issues
            )
        )

    def _convert_issues(self, raw_issues: list) -> list[Issue]:
        """将 LLM 返回的 issues 转换为 Schema 定义的 Issue 对象"""
        issues = []
        for raw in raw_issues:
            severity_map = {
                "high": Severity.HIGH,
                "medium": Severity.MEDIUM,
                "low": Severity.LOW,
                "critical": Severity.CRITICAL
            }
            severity = severity_map.get(raw.get("severity", "medium"), Severity.MEDIUM)
            
            issues.append(Issue(
                id=raw.get("id", "unknown_issue"),
                category=IssueCategory.COMPLETENESS,
                file=raw.get("file", "README.md"),
                severity=severity,
                description=raw.get("description", ""),
                suggestion=raw.get("suggestion", ""),
                line_number=raw.get("line_number"),
                # 确保这里转为 float，防止之前的验证错误
                score_deduction=float(raw.get("score_deduction", 0))
            ))
        return issues

    def _add_health_check_issues(self, issues: list[Issue], health_check: HealthCheck) -> list[Issue]:
        existing_ids = {issue.id for issue in issues}
        
        missing_file_issues = [
            {
                "check": not health_check.has_security_policy,
                "id": "missing_security",
                "file": "SECURITY.md",
                "severity": Severity.MEDIUM,
                "description": "缺失安全策略文件",
                "suggestion": "建议添加 SECURITY.md 说明漏洞上报流程",
                "score_deduction": 5
            },
            {
                "check": not health_check.has_changelog,
                "id": "missing_changelog",
                "file": "CHANGELOG.md",
                "severity": Severity.LOW,
                "description": "缺失变更日志文件",
                "suggestion": "建议添加 CHANGELOG.md 或使用 GitHub Releases",
                "score_deduction": 5
            }
        ]
        
        for item in missing_file_issues:
            if item["check"] and item["id"] not in existing_ids:
                issues.append(Issue(
                    id=item["id"],
                    category=IssueCategory.COMPLETENESS,
                    file=item["file"],
                    severity=item["severity"],
                    description=item["description"],
                    suggestion=item["suggestion"],
                    score_deduction=float(item["score_deduction"])
                ))
        return issues