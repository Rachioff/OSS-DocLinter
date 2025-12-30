import React, { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
// [新增] 引入 Tabs 和 Input
import { Card, Button, Typography, Space, message, Spin, Modal, Result, Tabs, Input } from 'antd';
import { ArrowLeftOutlined, GithubOutlined, EditOutlined, DiffOutlined } from '@ant-design/icons';
import ReactDiffViewer, { DiffMethod } from 'react-diff-viewer-continued';
import { generateFix, createPR } from '../api/endpoints';
import { Issue, RepoInfo, AnalyzeResponse } from '../types';
import Alert from 'antd/es/alert/Alert';

const { Title, Paragraph, Text } = Typography;
const { TextArea } = Input; // [新增] 获取 TextArea 组件

const FixPreview: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  
  const state = location.state as { 
    issue: Issue; 
    fileContent: string; 
    repoInfo: RepoInfo;
    dashboardData: AnalyzeResponse;
  } | null;

  const { issue, fileContent, repoInfo, dashboardData } = state || {};

  const [fixedContent, setFixedContent] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [activeTab, setActiveTab] = useState<string>('diff');

  useEffect(() => {
    if (!issue || !fileContent || !repoInfo) {
        setLoading(false);
        return;
    }

    const fetchFix = async () => {
      try {
        const res = await generateFix(
            repoInfo.owner,
            repoInfo.repo,
            issue.file,
            issue.id,
            fileContent
        );
        setFixedContent(res.fixed_content);
      } catch (error) {
        console.error(error);
        message.error('生成修复内容失败，请检查控制台网络请求详情');
      } finally {
        setLoading(false);
      }
    };

    fetchFix();
  }, [issue, fileContent, repoInfo]);

  const handleCreatePR = async () => {
    if (!issue || !repoInfo || !fixedContent) {
        message.error("缺少必要信息，无法提交PR");
        return;
    }

    setSubmitting(true);
    try {
        // 路径清洗：移除开头的 ./ 或 /
        const cleanFilePath = issue.file.replace(/^(\.\/|\/)/, '');

        const res = await createPR(
            repoInfo.owner,
            repoInfo.repo,
            cleanFilePath,
            fixedContent, // 这里使用的是 state 中的内容，因此包含了用户的编辑
            `docs: fix ${issue.category} issue in ${cleanFilePath}`,
            `Docs: Fix ${issue.category} issues in ${cleanFilePath}`
        );
        
        Modal.success({
            title: 'PR 创建成功',
            content: (
                <div>
                    <p>已成功为您创建 Pull Request！</p>
                    <a href={res.pr_url} target="_blank" rel="noopener noreferrer">点击查看 PR</a>
                </div>
            ),
            onOk: () => navigate('/dashboard', { state: { data: dashboardData } }),
        });
    } catch (error) {
        console.error(error);
        message.error('创建 PR 失败。这可能是因为目标分支已存在或权限不足。');
    } finally {
        setSubmitting(false);
    }
  };

  if (!issue || !fileContent || !repoInfo) {
      return (
          <Result
            status="500"
            title="会话已过期"
            subTitle="无法获取修复上下文。请返回仪表盘重新选择修复。"
            extra={<Button type="primary" onClick={() => navigate('/')}>回到首页</Button>}
          />
      );
  }

  if (loading) {
      return (
          <div style={{ textAlign: 'center', padding: '100px' }}>
              <Spin size="large" tip="正在生成修复方案..." />
          </div>
      );
  }

  // [新增] 定义 Tabs 的内容
  const items = [
    {
      key: 'diff',
      label: (
        <span>
          <DiffOutlined />
          改动对比 (Preview)
        </span>
      ),
      children: (
        <div style={{ maxHeight: '600px', overflow: 'auto', border: '1px solid #e8e8e8', borderRadius: '4px' }}>
            <ReactDiffViewer 
                // 处理缺失文件的情况，左侧显示为空
                oldValue={fileContent === "当前仓库内无此文件" ? "" : fileContent} 
                newValue={fixedContent} 
                splitView={true}
                compareMethod={DiffMethod.WORDS}
                leftTitle="当前内容"
                rightTitle="修复后内容 (最终提交版)"
            />
        </div>
      ),
    },
    {
      key: 'edit',
      label: (
        <span>
          <EditOutlined />
          手动编辑 (Edit)
        </span>
      ),
      children: (
        <div>
            <Alert 
                message="您可以在下方直接修改修复后的代码，修改结果将实时反映在“改动对比”中，并作为最终 PR 提交内容。" 
                type="info" 
                showIcon 
                style={{ marginBottom: 16 }} 
            />
            <TextArea 
                value={fixedContent}
                onChange={(e) => setFixedContent(e.target.value)} // [关键] 绑定输入事件
                placeholder="在此处编辑代码..."
                autoSize={{ minRows: 15, maxRows: 30 }}
                style={{ 
                    fontFamily: 'Consolas, "Courier New", monospace', // 使用等宽字体
                    fontSize: '14px',
                    backgroundColor: '#fafafa',
                    color: '#24292e'
                }}
            />
        </div>
      ),
    },
  ];

  return (
    <div className="fade-in">
      <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(-1)} style={{ marginBottom: 16 }}>
        返回报告
      </Button>

      <Card 
        title={`修复预览: ${issue.file}`} 
        extra={
          <Button type="primary" icon={<GithubOutlined />} loading={submitting} onClick={handleCreatePR}>
              提交 PR
          </Button>
        }
      >
        <Space direction="vertical" style={{ width: '100%', marginBottom: 16 }}>
            <Paragraph>
                针对问题 <Text code>{issue.description}</Text> 的修复方案。
            </Paragraph>
        </Space>
        
        {/* [新增] 使用 Tabs 替换直接渲染 */}
        <Tabs 
            defaultActiveKey="diff" 
            activeKey={activeTab}
            onChange={setActiveTab}
            items={items} 
            type="card"
        />
      </Card>
    </div>
  );
};

export default FixPreview;