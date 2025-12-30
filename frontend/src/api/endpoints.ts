import apiClient from './client';
import { AnalyzeResponse, AuthResponse, UserInfo } from '../types';

export const analyzeRepo = async (url: string): Promise<AnalyzeResponse> => {
  const response = await apiClient.post<AnalyzeResponse>('/analyze', { url });
  return response.data;
};

export const getLoginUrl = async (): Promise<{ login_url: string }> => {
  const response = await apiClient.get('/auth/login');
  return response.data;
};

export const exchangeToken = async (code: string): Promise<AuthResponse> => {
  const response = await apiClient.get('/auth/callback', { params: { code } });
  return response.data;
};

export const getUserInfo = async (): Promise<UserInfo> => {
  const response = await apiClient.get('/user/me');
  return response.data;
};

export const generateFix = async (
  owner: string,
  repo: string,
  filePath: string,
  originalContent: string,
  issueId: string
): Promise<{ fixed_content: string }> => {
  const response = await apiClient.post('/fix/generate', {
    repo_owner: owner,
    repo_name: repo,
    file_path: filePath,
    original_content: originalContent,
    issue_id: issueId,
    // 因为后端标记为必填，所以我们可以传一个空字符串或者默认提示
    custom_instruction: "Fix the issue based on standard guidelines." 
  },
  {
    // 2. [新增] 请求配置 (Config) - Axios 的第三个参数
    // 设置超时时间为 300,000 毫秒 (即 5 分钟)
    // LLM 有时候真的很慢，给足时间防止断开
    timeout: 300000 
  });
  return response.data;
}

export const createPR = async (
  targetOwner: string,
  targetRepo: string,
  filePath: string,
  finalContent: string,
  commitMessage: string = "docs: fix issues via oss-doclinter", // 提供默认值
  prTitle: string = "Docs: Automated fixes" // 提供默认值
): Promise<{ pr_url: string }> => {
  // 注意：OpenAPI文档中路径写的是 /api/v1/，但根据你的设计文档可能是 /pr/create
  // 如果后端报错404，请尝试改为 '/pr/create'
  // 这里暂时根据之前的上下文假设路径是 /pr/create，因为422说明路径是对的，参数是错的
  const response = await apiClient.post('/pr/create', { 
    target_owner: targetOwner,
    target_repo: targetRepo,
    file_path: filePath,
    final_content: finalContent,
    commit_message: commitMessage,
    pr_title: prTitle
  });
  return response.data;
};

export const generateIssue = async (
  repoOwner: string,
  repoName: string,
  filePath: string,
  issueId: string,
  issueDescription: string,
  originalContent: string
): Promise<{ title: string; body: string }> => {
  const response = await apiClient.post(
    '/issue/generate', // 对应 API 路径
    {
      repo_owner: repoOwner,
      repo_name: repoName,
      file_path: filePath,
      issue_id: issueId,
      issue_description: issueDescription,
      original_content: originalContent,
    },
    {
      timeout: 120000 // 生成文本可能较慢，设置 2 分钟超时
    }
  );
  return response.data;
};

// 新增：提交 Issue
export const createIssue = async (
  targetOwner: string,
  targetRepo: string,
  title: string,
  body: string
): Promise<{ issue_url: string; status: string }> => {
  const response = await apiClient.post('/issue/create', {
    target_owner: targetOwner,
    target_repo: targetRepo,
    title: title,
    body: body,
  });
  return response.data;
};
