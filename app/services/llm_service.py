import os
import httpx
from typing import Dict, List, Optional
from fastapi import HTTPException
import json

class LLMService:
    def __init__(self):
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        if not self.api_key:
            raise ValueError("DEEPSEEK_API_KEY environment variable is required")
        
        self.base_url = "https://api.deepseek.com/v1"
        self.model = "deepseek-chat"  # 或使用 deepseek-coder 针对代码文档
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    async def analyze_documentation_completeness(
        self, 
        files: Dict[str, Optional[Dict]]
    ) -> Dict:
        """
        分析文档完整性并打分
        
        Args:
            files: 从 GitHubService.fetch_repo_files() 获取的文件字典
        
        Returns:
            包含总分和详细问题的报告
        """
        # 准备文档内容
        readme_content = files.get("readme", {}).get("content", "") if files.get("readme") else ""
        contributing_content = files.get("contributing", {}).get("content", "") if files.get("contributing") else ""
        code_of_conduct_content = files.get("code_of_conduct", {}).get("content", "") if files.get("code_of_conduct") else ""
        license_content = files.get("license", {}).get("content", "") if files.get("license") else ""
        
        # 构建评测prompt
        prompt = self._build_completeness_prompt(
            readme_content,
            contributing_content,
            code_of_conduct_content,
            license_content
        )
        
        # 调用DeepSeek API
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json={
                        "model": self.model,
                        "messages": [
                            {
                                "role": "system",
                                "content": "你是一个专业的开源项目文档评审专家，精通开源社区最佳实践。"
                            },
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        "temperature": 0.3,  # 降低随机性，提高一致性
                        "response_format": {"type": "json_object"}
                    }
                )
                
                if response.status_code != 200:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"DeepSeek API error: {response.text}"
                    )
                
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                
                # 解析JSON响应
                analysis = json.loads(content)
                
                # 转换为标准报告格式
                return self._format_report(analysis, files)
                
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="LLM request timeout")
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=500, detail=f"Failed to parse LLM response: {str(e)}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"LLM analysis failed: {str(e)}")
    
    def _build_completeness_prompt(
        self,
        readme: str,
        contributing: str,
        code_of_conduct: str,
        license_info: str
    ) -> str:
        """构建完整性评测的Prompt"""
        
        return f"""请对以下开源项目文档进行完整性评测。
        
                **评分核心原则（Modern Open Source Standards）：**
                1. **安装指导**：如果项目提供了 `pip install` 或 `npm install` 等标准包管理器命令，**无需**要求源码安装指南，该项应得满分。
                2. **外部链接有效**：如果文档包含指向官方网站（如 readthedocs, vercel）的链接，视为内容完整，**不扣分**。
                3. **Release 即日志**：如果 CHANGELOG 部分的内容是 "This project uses GitHub Releases feature"，视为满分。
                4. **非侵入式贡献**：如果 CONTRIBUTING 文件仅包含指向外部贡献指南的链接，视为满分。
                5. **行为准则灵活性**：如果 CODE_OF_CONDUCT 文件仅包含指向外部行为准则的链接，视为满分。
                6. **评分灵活性**：如果某个文件缺失，但其他文档中已经涵盖了该部分内容，视为满分。

                **总分70分，维度如下：**

                1. **安装与依赖 (20分)**
                - 是否提供了一键安装命令(有则满分，不强制要求系统依赖说明，除非是二进制工具)？如果是Web应用等其他不需要安装等情况则此项目满分

                2. **快速上手 (20分)**
                - 是否有 Hello World 级别的最小示例？(有代码块即可)

                3. **贡献指南 (20分)**
                - 是否有 CONTRIBUTING 文件或相关链接？
                - 是否提及开发环境或测试命令？(外部链接有效)

                4. **行为准则 (5分)**
                - 是否有 CODE_OF_CONDUCT？如果没有，是否在其他文档中提及社区行为准则？如果其他文档发现了类似说明且完善，可以视为满分。如果只有代码风格等内容可以酌情给部分分数。

                5. **许可证 (5分)**
                - 是否有 LICENSE？

                ---

                **待评测文档：**

                ### README.md

                {readme if readme else "[文件不存在]"}

                ### CONTRIBUTING.md

                {contributing if contributing else "[文件不存在]"}

                ### CODE_OF_CONDUCT.md

                {code_of_conduct if code_of_conduct else "[文件不存在]"}

                ### LICENSE

                {license_info if license_info else "[文件不存在]"}

                ---


                ---

                **输出要求：**
                请以JSON格式返回评测结果，结构如下：

                ```json
                {{
                "overall_score": 65,
                "dimensions": [
                    {{
                    "name": "installation_guide",
                    "score": 15,
                    "max_score": 20,
                    "issues": [
                        {{
                        "id": "missing_install_command",
                        "severity": "high",
                        "description": "未提供具体的安装命令",
                        "suggestion": "建议添加 `pip install package-name` 等安装指令",
                        "file": "README.md"
                        }}
                    ]
                    }},
                    {{
                    "name": "quick_start",
                    "score": 18,
                    "max_score": 20,
                    "issues": [
                        {{
                        "id": "example_not_runnable",
                        "severity": "medium",
                        "description": "示例代码缺少import语句",
                        "suggestion": "建议补充完整的import声明",
                        "file": "README.md"
                        }}
                    ]
                    }},
                    {{
                    "name": "contributing_guide",
                    "score": 0,
                    "max_score": 20,
                    "issues": [
                        {{
                        "id": "missing_contributing",
                        "severity": "high",
                        "description": "缺失CONTRIBUTING.md文件",
                        "suggestion": "建议创建贡献指南，说明PR流程和开发规范",
                        "file": "CONTRIBUTING.md"
                        }}
                    ]
                    }},
                    {{
                    "name": "code_of_conduct",
                    "score": 5,
                    "max_score": 5,
                    "issues": []
                    }},
                    {{
                    "name": "license",
                    "score": 5,
                    "max_score": 5,
                    "issues": []
                    }}
                ]
                }}

                注意：

                - 每个维度必须给出具体扣分理由

                - issue的id使用snake_case命名

                - severity只能是：high/medium/low

                - 如果某个文件不存在，这是最高优先级的问题

                - 评分要客观严格，参考顶级开源项目标准
                """
    
    def _format_report(self, analysis: Dict, files: Dict) -> Dict: 
        issues = [] 
        overall_score = analysis.get("overall_score", 0)
        for dimension in analysis.get("dimensions", []): 
            for issue in dimension.get("issues", []): 
                issues.append({ "id": issue.get("id"),
                                "category": "completeness", 
                                "file": issue.get("file"), 
                                "severity": issue.get("severity"), 
                                "description": issue.get("description"), 
                                "suggestion": issue.get("suggestion"), 
                                "score_deduction": dimension.get("max_score", 0) - dimension.get("score", 0) })
        return { "overall_score": overall_score, "issues": issues, "raw_analysis": analysis }
    
    async def generate_fix(
        self,
        original_content: str,
        issue_id: str,
        issue_description: str,
        custom_instruction: Optional[str] = None
    ) -> str:
        """
        根据问题生成修复后的完整文档
        """
        prompt = self._build_fix_prompt(
            original_content,
            issue_id,
            issue_description,
            custom_instruction
        )
        
        try:
            # [修改 1] 增加超时时间，长文档生成非常耗时，60s 往往不够
            async with httpx.AsyncClient(timeout=180.0) as client:
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json={
                        "model": self.model,
                        "messages": [
                            {
                                "role": "system",
                                "content": "你是一个专业的开源项目文档专家。你的任务是根据用户提供的问题，修复并完善文档。请直接返回修复后的完整 Markdown 文档，不要添加任何解释或代码块标记。除了问题描述以外的其他任何地方都不要改动。"
                            },
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        "temperature": 0.1, # [建议] 降低温度，对于长文档重写，稳定性比创造性更重要
                        "max_tokens": 8192  # [修改 2] 显式增加最大输出 Token 限制，防止输出被截断
                    }
                )
                
                if resp.status_code != 200:
                    # 增加更详细的错误日志
                    raise HTTPException(status_code=502, detail=f"LLM API error: {resp.text}")
                
                data = resp.json()
                
                # 检查 finish_reason，如果不是 stop，说明还是被截断了
                finish_reason = data["choices"][0]["finish_reason"]
                if finish_reason == "length":
                    # 如果依然因为长度被截断，抛出特定错误提示前端
                    raise HTTPException(status_code=400, detail="文档过长，超出了模型单次生成的最大限制，建议分段处理。")

                fixed_content = data["choices"][0]["message"]["content"]
                
                # 清理可能的 Markdown 代码块包裹
                fixed_content = self._clean_markdown_wrapper(fixed_content)
                
                return fixed_content
                
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="LLM request timeout (generation took too long)")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"LLM error: {str(e)}")

    def _build_fix_prompt(
        self,
        original_content: str,
        issue_id: str,
        issue_description: str,
        custom_instruction: Optional[str]
    ) -> str:
        """构建修复文档的 Prompt"""
        prompt = f"""请修复以下文档中的问题。

        ## 问题信息
        - 问题ID: {issue_id}
        - 问题描述: {issue_description}

        ## 原始文档内容
        ```markdown
        {original_content}
        ```
        ## 修复要求
        1. 保持原有内容的风格和格式

        2. 只针对上述问题进行修复或补充

        3. 返回修复后的完整文档"""

        if custom_instruction:
            prompt += f"\n## 用户额外要求\n{custom_instruction}\n"
        
        return prompt
    
    def _clean_markdown_wrapper(self, content: str) -> str:
        """清理可能的 Markdown 代码块包裹"""
        if content.startswith("```markdown") and content.endswith("```"):
            return "\n".join(content.split("\n")[1:-1]).strip()
        return content.strip()
    
    async def generate_issue_content(self, file_path: str, issue_desc: str, context: str) -> dict:
        """
        生成 Issue 的标题和正文
        """
        system_prompt = """
        You are an incredibly helpful open-source contributor assistant. 
        Your goal is to write a polite, clear, and constructive GitHub Issue report based on a documentation problem.
        The output must be in JSON format with keys: "title" and "body".
        The "body" should be in Markdown format.
        """
        
        user_prompt = f"""
        I found a problem in the file `{file_path}`.
        The specific issue is: "{issue_desc}".
        
        Here is a snippet of the file content for context:
        {context[:2000]} # 截取部分内容避免 token 溢出
        
        Please generate:
        1. A concise Title.
        2. A Body that describes the problem and politely asks for a fix or clarification.
        """

        # 模拟调用 LLM (请替换为实际的 OpenAI/LangChain 调用)
        # response = await openai.ChatCompletion.create(...)
        
        # 模拟返回
        return {
            "title": f"Docs: Improvement needed for {file_path}",
            "body": f"## Problem Description\n\nI noticed that in `{file_path}`, {issue_desc}.\n\n## Context\nIt would be great to improve this to help new users."
        }
    
    

