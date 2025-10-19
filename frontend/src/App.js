import React, { useState, useEffect, useRef, useCallback } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Layout, ConfigProvider, theme, Row, Col, App as AntdApp } from 'antd';
import Dashboard from './pages/Dashboard';
import Upload from './pages/Upload';
import Result from './pages/Result';
import History from './pages/History';
import Login from './pages/Login';
import Register from './pages/Register';
import Account from './pages/Account';
import Header from './components/Header';
import { userApi } from './api/api';
import './App.css';

const { Content, Footer } = Layout;

function App() {
  const [token, setToken] = useState(localStorage.getItem('token') || null);
  const [currentUser, setCurrentUser] = useState(null);
  const quotaBadgeRef = useRef(null);

  useEffect(() => {
    // 保存token到本地存储
    if (token) {
      localStorage.setItem('token', token);
      // 自动获取用户信息
      const fetchUserInfo = async () => {
        try {
          const userInfo = await userApi.getCurrentUser();
          setCurrentUser(userInfo);
        } catch (error) {
          console.error('获取用户信息失败:', error);
          // 如果token无效，清除token
          if (error.response?.status === 401) {
            setToken(null);
            setCurrentUser(null);
            localStorage.removeItem('token');
          }
        }
      };
      fetchUserInfo();
    } else {
      localStorage.removeItem('token');
      setCurrentUser(null);
    }
  }, [token]);

  const handleLogout = () => {
    setToken(null);
    setCurrentUser(null);
    localStorage.removeItem('token');
  };

  // 刷新配额显示的函数，供子组件调用
  const refreshQuota = useCallback(() => {
    if (quotaBadgeRef.current) {
      quotaBadgeRef.current.refresh();
    }
  }, []);

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
              quotaBadgeRef={quotaBadgeRef}
            />
            <Content className="responsive-content">
              <Row justify="center">
                <Col xs={24} sm={24} md={22} lg={20} xl={18}>
                  <div className="site-layout-content">
                    <Routes>
                      <Route path="/login" element={<Login setToken={setToken} setCurrentUser={setCurrentUser} />} />
                      <Route path="/register" element={<Register setToken={setToken} setCurrentUser={setCurrentUser} />} />
                      <Route path="/dashboard" element={<Dashboard />} />
                      <Route path="/upload" element={<Upload refreshQuota={refreshQuota} />} />
                      <Route path="/result/:taskId" element={<Result refreshQuota={refreshQuota} />} />
                      <Route path="/history" element={<History />} />
                      <Route path="/account" element={<Account />} />
                      <Route path="/" element={<Navigate to="/dashboard" />} />
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