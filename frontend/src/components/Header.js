import React, { useState, useEffect, useRef } from 'react';
import { Layout, Menu, Button, Dropdown, message, Drawer, Space } from 'antd';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { 
  UploadOutlined, 
  HomeOutlined, 
  HistoryOutlined, 
  UserOutlined, 
  LogoutOutlined,
  MenuOutlined
} from '@ant-design/icons';
import '../styles/Header.css';
import QuotaBadge from './QuotaBadge';
import TopupModal from './TopupModal';

const { Header: AntHeader } = Layout;

const AppHeader = ({ token, currentUser, onLogout, quotaBadgeRef }) => {
  const [drawerVisible, setDrawerVisible] = useState(false);
  const [topupVisible, setTopupVisible] = useState(false);
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
    message.success('已退出登录');
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
      key: 'account',
      onClick: () => {
        navigate('/account');
        setDrawerVisible(false);
      },
      label: (
        <>
          <UserOutlined /> 账户信息
        </>
      )
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
    if (path.startsWith('/account')) return ['account'];
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
    },
    {
      key: "account",
      icon: <UserOutlined />,
      label: <Link to="/account">账户信息</Link>
    }
  ];

  const handleMenuClick = (e) => {
    if (isMobile) {
      setDrawerVisible(false);
    }
  };

  const handleTopupSuccess = () => {
    // 充值成功后刷新配额显示
    if (quotaBadgeRef.current) {
      quotaBadgeRef.current.refresh();
    }
  };

  // 检查是否为登录或注册页面
  const isAuthPage = location.pathname === '/login' || location.pathname === '/register';
  
  // 如果是登录/注册页面，不显示Header
  if (isAuthPage) {
    return null;
  }

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
            <div className="user-section" style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              {token && <QuotaBadge ref={quotaBadgeRef} onTopup={() => setTopupVisible(true)} />}
              {currentUser ? (
                <Dropdown menu={{ items: userMenu }} placement="bottomRight">
                  <Button type="text" style={{ color: 'white' }}>
                    <UserOutlined /> {currentUser.username}
                  </Button>
                </Dropdown>
              ) : (
                <Button type="primary" onClick={() => navigate('/login')}>
                  登录
                </Button>
              )}
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
          <div style={{ padding: '16px 0', borderTop: '1px solid #f0f0f0', marginTop: '16px' }}>
            <Space direction="vertical" style={{ width: '100%' }}>
              {currentUser ? (
                <>
                  <div>
                    <UserOutlined /> {currentUser.username}
                  </div>
                  <Button type="primary" danger onClick={handleLogout} block>
                    <LogoutOutlined /> 退出登录
                  </Button>
                </>
              ) : (
                <Button type="primary" onClick={() => navigate('/login')} block>
                  登录
                </Button>
              )}
            </Space>
          </div>
        </Drawer>
      </div>
      <TopupModal 
        open={topupVisible} 
        onClose={() => setTopupVisible(false)} 
        onSuccess={handleTopupSuccess}
      />
    </AntHeader>
  );
};

export default AppHeader; 