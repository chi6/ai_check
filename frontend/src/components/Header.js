import React, { useState, useEffect } from 'react';
import { Layout, Menu, Button, Dropdown, message } from 'antd';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { UploadOutlined, HomeOutlined, HistoryOutlined, UserOutlined, LogoutOutlined } from '@ant-design/icons';
import { userApi } from '../api/api';

const { Header: AntHeader } = Layout;

const AppHeader = ({ token, currentUser, onLogout }) => {
  const [user, setUser] = useState(currentUser || {
    username: '访客用户',
    email: 'guest@example.com'
  });
  const location = useLocation();
  const navigate = useNavigate();

  // 移除获取用户信息的逻辑，始终使用访客用户
  const handleLogout = () => {
    onLogout();
    message.success('已切换访客');
    navigate('/dashboard');
  };

  const userMenu = (
    <Menu>
      <Menu.Item key="username" disabled>
        <UserOutlined /> {user?.username || '访客用户'}
      </Menu.Item>
      <Menu.Divider />
      <Menu.Item key="logout" onClick={handleLogout}>
        <LogoutOutlined /> 切换访客
      </Menu.Item>
    </Menu>
  );

  const getSelectedKeys = () => {
    const path = location.pathname;
    if (path.startsWith('/dashboard')) return ['dashboard'];
    if (path.startsWith('/upload')) return ['upload'];
    if (path.startsWith('/history')) return ['history'];
    return [];
  };

  return (
    <AntHeader style={{ position: 'fixed', zIndex: 1, width: '100%' }}>
      <div className="logo">AI论文检测工具</div>
      <Menu
        theme="dark"
        mode="horizontal"
        selectedKeys={getSelectedKeys()}
        style={{ lineHeight: '64px' }}
      >
        <Menu.Item key="dashboard" icon={<HomeOutlined />}>
          <Link to="/dashboard">首页</Link>
        </Menu.Item>
        <Menu.Item key="upload" icon={<UploadOutlined />}>
          <Link to="/upload">上传检测</Link>
        </Menu.Item>
        <Menu.Item key="history" icon={<HistoryOutlined />}>
          <Link to="/history">历史记录</Link>
        </Menu.Item>
      </Menu>
      <div style={{ float: 'right' }}>
        <Dropdown overlay={userMenu} placement="bottomRight">
          <Button type="text" style={{ color: 'white' }}>
            <UserOutlined /> {user?.username || '访客用户'} 
          </Button>
        </Dropdown>
      </div>
    </AntHeader>
  );
};

export default AppHeader; 