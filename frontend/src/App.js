import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Layout, ConfigProvider, theme, Row, Col, App as AntdApp } from 'antd';
import Dashboard from './pages/Dashboard';
import Upload from './pages/Upload';
import Result from './pages/Result';
import History from './pages/History';
import Header from './components/Header';
import './App.css';

const { Content, Footer } = Layout;

function App() {
  // 设置默认令牌值为一个假的值，这样所有认证检查都会通过
  // eslint-disable-next-line no-unused-vars
  const [token, setToken] = useState('dummy-token');
  const [currentUser, setCurrentUser] = useState({
    id: 'guest-user',
    username: '访客用户',
    email: 'guest@example.com'
  });

  useEffect(() => {
    // 保存token到本地存储
    localStorage.setItem('token', token);
  }, [token]);

  const handleLogout = () => {
    // 登出后仍然保持相同的访客状态
    setCurrentUser({
      id: 'guest-user',
      username: '访客用户',
      email: 'guest@example.com'
    });
  };

  // 创建一个符合学术/教育领域特点的主题
  const customTheme = {
    algorithm: theme.defaultAlgorithm,
    token: {
      // 使用更柔和的蓝色作为主色调，适合学术领域
      colorPrimary: '#2b6cb0',  // 较深的蓝色
      colorSuccess: '#38a169',  // 柔和的绿色
      colorWarning: '#d69e2e',  // 柔和的黄色
      colorError: '#e53e3e',    // 柔和的红色
      colorInfo: '#3182ce',     // 中等蓝色
      
      // 圆角设置
      borderRadius: 4,
      
      // 字体设置
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
      
      // 其他颜色
      colorTextBase: '#333333',
      colorBgBase: '#ffffff',
      
      // 派生颜色
      colorLink: '#2b6cb0',
      colorLinkHover: '#4299e1',
    },
    components: {
      Button: {
        controlHeight: 36,
        borderRadius: 4,
      },
      Card: {
        colorBorderSecondary: '#e2e8f0',
        boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)',
      },
      Typography: {
        fontWeightStrong: 600,
      },
    },
  };

  return (
    <ConfigProvider theme={customTheme}>
      <AntdApp>
        <Router>
          <Layout className="layout" style={{ minHeight: '100vh' }}>
            <Header 
              token={token} 
              currentUser={currentUser} 
              onLogout={handleLogout} 
            />
            <Content className="responsive-content">
              <Row justify="center">
                <Col xs={24} sm={24} md={22} lg={20} xl={18}>
                  <div className="site-layout-content">
                    <Routes>
                      {/* 默认重定向到仪表盘，跳过登录页面 */}
                      <Route path="/login" element={<Navigate to="/dashboard" />} />
                      <Route path="/register" element={<Navigate to="/dashboard" />} />
                      <Route path="/dashboard" element={<Dashboard />} />
                      <Route path="/upload" element={<Upload />} />
                      <Route path="/result/:taskId" element={<Result />} />
                      <Route path="/history" element={<History />} />
                      <Route path="*" element={<Navigate to="/dashboard" />} />
                    </Routes>
                  </div>
                </Col>
              </Row>
            </Content>
            <Footer style={{ textAlign: 'center' }}>
              AI论文检测工具 ©{new Date().getFullYear()} 版权所有
            </Footer>
          </Layout>
        </Router>
      </AntdApp>
    </ConfigProvider>
  );
}

export default App; 