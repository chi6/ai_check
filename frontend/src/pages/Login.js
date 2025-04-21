import React, { useState } from 'react';
import { Form, Input, Button, Card, message, Typography } from 'antd';
import { UserOutlined, LockOutlined } from '@ant-design/icons';
import { Link, useNavigate } from 'react-router-dom';
import { userApi } from '../api/api';

const { Title } = Typography;

const Login = ({ setToken, setCurrentUser }) => {
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const onFinish = async (values) => {
    try {
      setLoading(true);
      // 调用登录API
      const response = await userApi.login(values.email, values.password);
      
      // 保存token和用户信息
      setToken(response.access_token);
      
      // 获取用户信息
      const userInfo = await userApi.getCurrentUser();
      setCurrentUser(userInfo);
      
      message.success('登录成功！');
      navigate('/dashboard');
    } catch (error) {
      console.error('登录失败:', error);
      message.error('登录失败: ' + (error.response?.data?.detail || '请检查邮箱和密码'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-form">
      <Card className="auth-card">
        <Title level={2} style={{ textAlign: 'center', marginBottom: 30 }}>
          登录账户
        </Title>
        <Form
          name="login_form"
          initialValues={{ remember: true }}
          onFinish={onFinish}
          size="large"
          layout="vertical"
        >
          <Form.Item
            name="email"
            rules={[
              { required: true, message: '请输入邮箱!' },
              { type: 'email', message: '请输入有效的邮箱地址!' }
            ]}
          >
            <Input prefix={<UserOutlined />} placeholder="邮箱" />
          </Form.Item>
          
          <Form.Item
            name="password"
            rules={[{ required: true, message: '请输入密码!' }]}
          >
            <Input.Password prefix={<LockOutlined />} placeholder="密码" />
          </Form.Item>
          
          <Form.Item style={{ marginBottom: 10 }}>
            <Button type="primary" htmlType="submit" style={{ width: '100%' }} loading={loading}>
              登录
            </Button>
          </Form.Item>
          
          <div style={{ textAlign: 'center' }}>
            还没有账号? <Link to="/register">立即注册</Link>
          </div>
        </Form>
      </Card>
    </div>
  );
};

export default Login; 