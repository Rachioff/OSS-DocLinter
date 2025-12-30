import React, { useEffect, useRef } from 'react'; // 1. 引入 useRef
import { useNavigate, useSearchParams } from 'react-router-dom';
import { message, Spin } from 'antd';
import { exchangeToken } from '../api/endpoints';

const Callback: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const code = searchParams.get('code');
  
  // 2. 创建一个 ref 来记录是否已经调用过 API
  // useRef 的值在组件重新渲染时会保持不变
  const hasCalled = useRef(false);

  useEffect(() => {
    const handleCallback = async () => {
      // 3. 如果没有 code，直接返回
      if (!code) {
        // 防止没有 code 时也跳转导致的用户体验问题，可以加个判断
        // 如果是纯粹的无参数访问，可能需要重定向回首页
        if (!hasCalled.current) {
             message.error('未获取到授权码');
             navigate('/');
        }
        return;
      }

      // 4. [关键步骤] 检查是否已经调用过
      if (hasCalled.current) return;
      hasCalled.current = true; // 标记为已调用

      try {
        const data = await exchangeToken(code);
        localStorage.setItem('access_token', data.access_token);
        message.success('登录成功');
        // 建议：可以使用 replace: true 防止用户点浏览器后退按钮回到 callback 页面再次触发流程
        navigate('/', { replace: true }); 
      } catch (error) {
        console.error(error);
        // 这里不需要 hasCalled.current = false，因为 code 已经脏了，重试也没用
        message.error('登录失败，请重试');
        navigate('/', { replace: true });
      }
    };

    handleCallback();
  }, [code, navigate]);

  return (
    <div style={{ textAlign: 'center', padding: '100px' }}>
      <Spin size="large" tip="正在处理登录..." />
    </div>
  );
};

export default Callback;