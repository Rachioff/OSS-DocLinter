// pages/IssuePreview.tsx
import React, { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Card, Button, Input, Form, message, Spin, Modal, Result, Space } from 'antd';
import { ArrowLeftOutlined, GithubOutlined, CheckCircleOutlined } from '@ant-design/icons';
import { generateIssue, createIssue } from '../api/endpoints';
import { Issue, RepoInfo, AnalyzeResponse } from '../types';

const { TextArea } = Input;

const IssuePreview: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  
  // 获取传递过来的状态
  const state = location.state as { 
    issue: Issue; 
    fileContent: string; 
    repoInfo: RepoInfo; 
    dashboardData: AnalyzeResponse 
  } | null;

  const { issue, fileContent, repoInfo, dashboardData } = state || {};

  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [form] = Form.useForm();

  // 页面加载时自动调用 LLM 生成 Issue
  useEffect(() => {
    if (!issue || !fileContent || !repoInfo) {
        setLoading(false);
        return;
    }

    const fetchIssueDraft = async () => {
      try {
        const res = await generateIssue(
            repoInfo.owner,
            repoInfo.repo,
            issue.file,
            issue.id,
            issue.description,
            fileContent
        );
        // 将生成的内容填入表单
        form.setFieldsValue({
            title: res.title,
            body: res.body
        });
      } catch (error) {
        console.error(error);
        message.error('生成 Issue 草稿失败');
      } finally {
        setLoading(false);
      }
    };

    fetchIssueDraft();
  }, [issue, fileContent, repoInfo, form]);

  const handleSubmit = async (values: { title: string; body: string }) => {
      if (!repoInfo) return;
      
      setSubmitting(true);
      try {
          const res = await createIssue(
              repoInfo.owner,
              repoInfo.repo,
              values.title,
              values.body
          );
          
          Modal.success({
              title: 'Issue 提交成功',
              icon: <CheckCircleOutlined style={{ color: '#52c41a' }} />,
              content: (
                  <div>
                      <p>Issue 已成功提交到 GitHub 仓库。</p>
                      <a href={res.issue_url} target="_blank" rel="noopener noreferrer">点击查看 Issue</a>
                  </div>
              ),
              onOk: () => navigate('/dashboard', { state: { data: dashboardData } }),
          });
      } catch (error) {
          console.error(error);
          message.error('提交 Issue 失败');
      } finally {
          setSubmitting(false);
      }
  };

  // 异常处理：状态丢失
  if (!issue || !fileContent || !repoInfo) {
      return (
          <Result
            status="500"
            title="数据丢失"
            subTitle="无法获取上下文信息，请从仪表盘重新操作。"
            extra={<Button type="primary" onClick={() => navigate('/')}>返回首页</Button>}
          />
      );
  }

  if (loading) {
      return (
          <div style={{ textAlign: 'center', padding: '100px' }}>
              <Spin size="large" tip="正在通过 LLM 撰写 Issue 草稿..." />
          </div>
      );
  }

  return (
    <div className="fade-in">
      <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(-1)} style={{ marginBottom: 16 }}>
        返回报告
      </Button>

      <Card title="提交 Issue 预览" style={{ maxWidth: 800, margin: '0 auto' }}>
        <Form
            form={form}
            layout="vertical"
            onFinish={handleSubmit}
            initialValues={{ title: '', body: '' }}
        >
            <Form.Item
                label="标题 (Title)"
                name="title"
                rules={[{ required: true, message: '请输入 Issue 标题' }]}
            >
                <Input placeholder="Issue 标题" size="large" />
            </Form.Item>

            <Form.Item
                label="内容 (Body - Markdown)"
                name="body"
                rules={[{ required: true, message: '请输入 Issue 内容' }]}
            >
                <TextArea 
                    rows={12} 
                    placeholder="在此编辑 Issue 详细描述..." 
                    style={{ fontFamily: 'monospace' }}
                />
            </Form.Item>

            <Form.Item>
                <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
                    <Button onClick={() => navigate(-1)}>取消</Button>
                    <Button 
                        type="primary" 
                        htmlType="submit" 
                        icon={<GithubOutlined />} 
                        loading={submitting}
                    >
                        提交 Issue
                    </Button>
                </Space>
            </Form.Item>
        </Form>
      </Card>
    </div>
  );
};

export default IssuePreview;