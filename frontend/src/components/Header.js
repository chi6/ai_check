import React, { useState, useEffect } from 'react';
import { Layout, Menu, Button, Dropdown, message, Drawer, Space } from 'antd';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { 
  UploadOutlined, 
  HomeOutlined, 
  HistoryOutlined, 
  UserOutlined, 
  LogoutOutlined,
  MenuOutlined,
  LoginOutlined
} from '@ant-design/icons';
import '../styles/Header.css';

const { Header: AntHeader } = Layout;

const AppHeader = ({ token, currentUser, onLogout }) => {
  const [drawerVisible, setDrawerVisible] = useState(false);
  const [isMobile, setIsMobile] = useState(window.innerWidth < 768);
  const location = useLocation();
  const navigate = useNavigate();

  // 监听窗口大小变化
  useEffect(() => {
    const handleResize = () => {
      setIsMobile(window.innerWidth < 768);
    };

    window.addEventListener('resize', handleResize);
    return () => {
      window.removeEventListener('resize', handleResize);
    };
  }, []);

  const handleLogout = () => {
    onLogout();
    message.success('退出登录成功');
    navigate('/login');
    setDrawerVisible(false);
  };

  const userMenu = currentUser ? [
    {
      key: 'username',
      disabled: true,
      label: (
        <>
          <UserOutlined /> {currentUser.username}
        </>
      )
    },
    {
      type: 'divider'
    },
    {
      key: 'logout',
      onClick: handleLogout,
      label: (
        <>
          <LogoutOutlined /> 退出登录
        </>
      )
    }
  ] : [];

  const getSelectedKeys = () => {
    const path = location.pathname;
    if (path.startsWith('/dashboard')) return ['dashboard'];
    if (path.startsWith('/upload')) return ['upload'];
    if (path.startsWith('/history')) return ['history'];
    return [];
  };

  const menuItems = [
    {
      key: "dashboard",
      icon: <HomeOutlined />,
      label: <Link to="/dashboard">首页</Link>
    },
    {
      key: "upload",
      icon: <UploadOutlined />,
      label: <Link to="/upload">上传检测</Link>
    },
    {
      key: "history",
      icon: <HistoryOutlined />,
      label: <Link to="/history">历史记录</Link>
    }
  ];

  const handleMenuClick = (e) => {
    if (isMobile) {
      setDrawerVisible(false);
    }
  };

  const renderUserSection = () => {
    if (token && currentUser) {
      return (
        <Dropdown menu={{ items: userMenu }} placement="bottomRight">
          <Button type="text" style={{ color: 'white' }}>
            <UserOutlined /> {currentUser.username}
          </Button>
        </Dropdown>
      );
    } else {
      return (
        <Space>
          <Button type="primary" onClick={() => navigate('/login')}>
            <LoginOutlined /> 登录
          </Button>
          <Button onClick={() => navigate('/register')}>
            注册
          </Button>
        </Space>
      );
    }
  };

  const renderMobileUserSection = () => {
    if (token && currentUser) {
      return (
        <div style={{ padding: '16px 0', borderTop: '1px solid #f0f0f0', marginTop: '16px' }}>
          <Space direction="vertical" style={{ width: '100%' }}>
            <div>
              <UserOutlined /> {currentUser.username}
            </div>
            <Button type="primary" danger onClick={handleLogout} block>
              <LogoutOutlined /> 退出登录
            </Button>
          </Space>
        </div>
      );
    } else {
      return (
        <div style={{ padding: '16px 0', borderTop: '1px solid #f0f0f0', marginTop: '16px' }}>
          <Space direction="vertical" style={{ width: '100%' }}>
            <Button type="primary" onClick={() => { navigate('/login'); setDrawerVisible(false); }} block>
              <LoginOutlined /> 登录
            </Button>
            <Button onClick={() => { navigate('/register'); setDrawerVisible(false); }} block>
              注册
            </Button>
          </Space>
        </div>
      );
    }
  };

  return (
    <AntHeader className="app-header">
      <div className="header-container">
        <div className="logo-section">
          <div className="logo">AI论文检测工具</div>
          {isMobile && (
            <Button 
              type="text" 
              icon={<MenuOutlined />} 
              onClick={() => setDrawerVisible(true)}
              className="menu-button"
            />
          )}
        </div>
        
        {!isMobile && (
          <>
            <Menu
              theme="dark"
              mode="horizontal"
              selectedKeys={getSelectedKeys()}
              className="desktop-menu"
              items={menuItems}
              onClick={handleMenuClick}
            />
            <div className="user-section">
              {renderUserSection()}
            </div>
          </>
        )}

        <Drawer
          title="菜单"
          placement="left"
          closable={true}
          onClose={() => setDrawerVisible(false)}
          open={drawerVisible}
          width={250}
        >
          <Menu
            mode="vertical"
            selectedKeys={getSelectedKeys()}
            items={menuItems}
            onClick={handleMenuClick}
            style={{ border: 'none' }}
          />
          {renderMobileUserSection()}
        </Drawer>
      </div>
    </AntHeader>
  );
};

export default AppHeader; 