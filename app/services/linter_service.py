import re
from typing import List, Dict, Tuple
from app.schemas import Issue, IssueCategory, Severity

class LinterService:
    def __init__(self):
        # 定义各维度满分
        self.max_scores = {
            "syntax": 10,    # Markdown语法正确性 (含行长、空格等)
            "structure": 10, # 标题层级与结构
            "code": 5,       # 代码块语言标识
            "links": 5       # 链接有效性 (语法层面)
        }
        self.total_max_score = sum(self.max_scores.values()) # 30分

    def lint_file(self, content: str, file_path: str) -> Dict:
        """
        对单个文件进行格式检查，返回各维度得分情况
        """
        lines = content.split('\n')
        all_issues = []
        
        # --- 1. 运行规则检查 ---
        
        # [Structure] 10分
        structure_issues = []
        structure_issues.extend(self._check_heading_increment(lines, file_path))
        if "readme" in file_path.lower():
            structure_issues.extend(self._check_first_line_h1(lines, file_path))
            
        # [Syntax] 10分
        syntax_issues = []
        syntax_issues.extend(self._check_trailing_spaces(lines, file_path))
        
        # [Code] 5分
        code_issues = self._check_code_block_language(lines, file_path)
        
        # [Links] 5分
        link_issues = self._check_link_syntax(content, lines, file_path) # 链接通常需要跨行匹配或全文匹配，但在行级处理更简单

        # --- 2. 计算各维度得分 (Bucket Scoring) ---
        
        # 计算 Structure 得分
        structure_deduction = sum(i.score_deduction for i in structure_issues)
        structure_score = max(0, self.max_scores["structure"] - structure_deduction)
        
        # 计算 Syntax 得分 (特殊处理：MD013 行长问题单独设置封顶，避免扣光)
        syntax_deduction = 0
        md013_deduction = 0
        for issue in syntax_issues:
            if issue.id == "MD013":
                md013_deduction += issue.score_deduction
            else:
                syntax_deduction += issue.score_deduction
        
        # 行长问题最多扣 5 分 (即保留一半语法分给其他规范)
        syntax_deduction = sum(i.score_deduction for i in syntax_issues)
        syntax_score = max(0, self.max_scores["syntax"] - syntax_deduction)
        
        # 计算 Code 得分
        code_deduction = sum(i.score_deduction for i in code_issues)
        code_score = max(0, self.max_scores["code"] - code_deduction)
        
        # 计算 Links 得分
        link_deduction = sum(i.score_deduction for i in link_issues)
        link_score = max(0, self.max_scores["links"] - link_deduction)

        # 汇总
        all_issues.extend(structure_issues)
        all_issues.extend(syntax_issues)
        all_issues.extend(code_issues)
        all_issues.extend(link_issues)

        total_score = structure_score + syntax_score + code_score + link_score

        return {
            "score": total_score, # 0 - 30
            "breakdown": {
                "structure": structure_score,
                "syntax": syntax_score,
                "code": code_score,
                "links": link_score
            },
            "issues": all_issues
        }

    # --- 规则实现 ---

    def _check_heading_increment(self, lines: List[str], file_path: str) -> List[Issue]:
        issues = []
        last_level = 0 # 初始视为 0
        heading_pattern = re.compile(r'^(#+)\s+(.*)')
        in_code_block = False
        
        for idx, line in enumerate(lines):
            if line.strip().startswith('```'):
                in_code_block = not in_code_block
                continue
            if in_code_block:
                continue

            match = heading_pattern.match(line)
            if match:
                current_level = len(match.group(1))
                
                # [新增逻辑] 如果是第一个标题，且不是 H1，我们允许它是 H1 或 H2 (有些项目用 H2 做子版块)
                if last_level == 0:
                    if current_level > 2: # 如果上来就是 H3/H4，那确实有问题
                         issues.append(Issue(
                            id="MD001",
                            category=IssueCategory.FORMAT,
                            file=file_path,
                            severity=Severity.LOW,
                            description=f"首个标题层级过深: H{current_level}",
                            suggestion="建议文档从 H1 或 H2 开始",
                            line_number=idx + 1,
                            score_deduction=3 
                        ))
                    last_level = current_level
                    continue

                if current_level > last_level + 1:
                    issues.append(Issue(
                        id="MD001",
                        category=IssueCategory.FORMAT,
                        file=file_path,
                        severity=Severity.LOW,
                        description=f"标题层级跳跃: H{last_level} -> H{current_level}",
                        suggestion=f"建议调整为 H{last_level + 1}",
                        line_number=idx + 1,
                        score_deduction=3 
                    ))
                last_level = current_level
        return issues

    def _check_first_line_h1(self, lines: List[str], file_path: str) -> List[Issue]:
        # 允许文件开头有 Frontmatter (--- ... ---)
        start_index = 0
        if len(lines) > 0 and lines[0].strip() == "---":
            for i in range(1, len(lines)):
                if lines[i].strip() == "---":
                    start_index = i + 1
                    break
        
        # 从正文开始寻找第一个非空行
        for i in range(start_index, len(lines)):
            line = lines[i].strip()
            if not line:
                continue
            
            # [新增] 如果行是以 HTML 标签 (<div, <img) 或 图片/链接徽章 ([![) 开头，跳过
            if line.startswith("<") or line.startswith("[!") or line.startswith("["):
                continue
            
            # 找到的第一个“正文文本行”必须是标题
            if not line.startswith("# "):
                return [Issue(
                    id="MD041",
                    category=IssueCategory.FORMAT,
                    file=file_path,
                    severity=Severity.MEDIUM,
                    description="首个文本内容非一级标题",
                    suggestion="建议在文档开头（徽章或图片下方）添加 '# 项目名称'",
                    line_number=i + 1,
                    score_deduction=5
                )]
            # 如果找到了 #，则通过，停止检查
            break
            
        return []

    def _check_trailing_spaces(self, lines: List[str], file_path: str) -> List[Issue]:
        error_lines = []
        for idx, line in enumerate(lines):
            if len(line) > 0 and line.rstrip() != line:
                error_lines.append(str(idx + 1))
        
        if error_lines:
            # 如果错误行数太多，只显示前5个，避免描述过长
            display_lines = error_lines[:5]
            suffix = "..." if len(error_lines) > 5 else ""
            line_str = ", ".join(display_lines) + suffix
            
            # 无论有多少行，只生成 1 个 Issue，扣 2 分 (Syntax总分10分)
            return [Issue(
                id="MD009",
                category=IssueCategory.FORMAT,
                file=file_path,
                severity=Severity.LOW,
                description=f"发现 {len(error_lines)} 处行尾包含多余空格",
                suggestion=f"建议配置编辑器自动删除行尾空格 (涉及行: {line_str})",
                line_number=int(error_lines[0]), # 定位到第一个错误
                score_deduction=2.0 
            )]
        return []

    def _check_line_length(self, lines: List[str], file_path: str, limit: int) -> List[Issue]:
        issues = []
        for idx, line in enumerate(lines):
            # 排除 URL 和 表格行 (简单的管道符判断)
            if len(line) > limit and "http" not in line and "|" not in line:
                issues.append(Issue(
                    id="MD013",
                    category=IssueCategory.FORMAT,
                    file=file_path,
                    severity=Severity.LOW,
                    description=f"行长超过 {limit} 字符",
                    suggestion="建议适当换行",
                    line_number=idx + 1,
                    score_deduction=0.2 # 大幅降低扣分，依赖总分封顶机制
                ))
        return issues

    def _check_code_block_language(self, lines: List[str], file_path: str) -> List[Issue]:
        error_lines = []
        in_code_block = False  # [新增] 状态标记：当前是否在代码块内部
        
        for idx, line in enumerate(lines):
            stripped = line.strip()
            
            # 检测是否是代码块的分隔符 (以 ``` 开头)
            if stripped.startswith("```"):
                # 情况 A: 当前不在代码块内 -> 这是【开始标签】
                if not in_code_block:
                    # 获取 ``` 后面的内容
                    # lstrip("`") 会去掉开头的 ```，剩下的就是语言标识
                    lang_identifier = stripped.lstrip("`").strip()
                    
                    # 如果剩下的内容为空，说明没写语言
                    if not lang_identifier:
                        error_lines.append(str(idx + 1))
                    
                    # 标记进入代码块状态
                    in_code_block = True
                
                # 情况 B: 当前已在代码块内 -> 这是【结束标签】
                else:
                    # 结束标签肯定是 ```，不需要检查语言，直接退出状态
                    in_code_block = False
        
        if error_lines:
            count = len(error_lines)
            display_lines = error_lines[:5]
            suffix = "..." if count > 5 else ""
            line_str = ", ".join(display_lines) + suffix
            
            return [Issue(
                id="MD040",
                category=IssueCategory.FORMAT,
                file=file_path,
                severity=Severity.LOW,
                description=f"发现 {count} 个代码块未指定语言标识",
                suggestion=f"建议为代码块添加语言标识（如 python, bash），以便正确高亮。涉及行: {line_str}",
                line_number=int(error_lines[0]),
                score_deduction=3.0 
            )]
        return []

    def _check_link_syntax(self, content: str, lines: List[str], file_path: str) -> List[Issue]:
        issues = []
        # 简单正则匹配空链接: [text]() 或 [](url)
        # 注意：这里只做基本的语法空值检查，不发网络请求
        empty_link_pattern = re.compile(r'\[([^\]]*)\]\(\s*\)')
        missing_text_pattern = re.compile(r'\[\s*\]\(([^)]+)\)')
        
        for idx, line in enumerate(lines):
            if empty_link_pattern.search(line):
                issues.append(Issue(
                    id="MD042",
                    category=IssueCategory.FORMAT,
                    file=file_path,
                    severity=Severity.MEDIUM,
                    description="存在空链接地址",
                    suggestion="请补充链接 URL",
                    line_number=idx + 1,
                    score_deduction=2
                ))
            elif missing_text_pattern.search(line):
                # 图片链接 ![alt](url) 是允许 alt 为空的，这里要排除图片
                if "!" not in line: 
                    issues.append(Issue(
                        id="MD043", # 自定义ID
                        category=IssueCategory.FORMAT,
                        file=file_path,
                        severity=Severity.LOW,
                        description="链接缺少描述文本",
                        suggestion="请补充链接描述文本",
                        line_number=idx + 1,
                        score_deduction=1
                    ))
        return issues