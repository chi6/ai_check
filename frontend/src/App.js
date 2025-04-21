import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Layout, ConfigProvider, theme } from 'antd';
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import Upload from './pages/Upload';
import Result from './pages/Result';
import History from './pages/History';
import Header from './components/Header';
import './App.css';

const { Content, Footer } = Layout;

function App() {
  // 设置默认令牌值为一个假的值，这样所有认证检查都会通过
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

  return (
    <ConfigProvider
      theme={{
        algorithm: theme.defaultAlgorithm,
        token: {
          colorPrimary: '#1890ff',
        },
      }}
    >
      <Router>
        <Layout className="layout" style={{ minHeight: '100vh' }}>
          <Header 
            token={token} 
            currentUser={currentUser} 
            onLogout={handleLogout} 
          />
          <Content style={{ padding: '0 50px', marginTop: 64 }}>
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
          </Content>
          <Footer style={{ textAlign: 'center' }}>
            AI论文检测工具 ©{new Date().getFullYear()} 版权所有
          </Footer>
        </Layout>
      </Router>
    </ConfigProvider>
  );
}

export default App; 