import React, { useState, useEffect } from 'react';
import { 
  Tabs, Row, Col, message, Typography, Card, Spin, Button, 
  Statistic, Badge, Divider, Space, Alert, Progress, Tag,
  Timeline, Avatar, Tooltip
} from 'antd';
import { 
  CreditCardOutlined, HistoryOutlined, UserOutlined,
  TrophyOutlined, GiftOutlined, SafetyCertificateOutlined,
  CheckCircleOutlined, ClockCircleOutlined, DollarOutlined,
  StarOutlined, CrownOutlined, ShoppingOutlined
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import PaymentForm from '../components/Payment/PaymentForm';
import PaymentHistory from '../components/Payment/PaymentHistory';
import SubscriptionManager from '../components/Payment/SubscriptionManager';
import LanguageSwitch from '../components/LanguageSwitch';
import { userApi } from '../api/api';
import './PaymentPage.css';

const { TabPane } = Tabs;
const { Title, Text, Paragraph } = Typography;

const PaymentPage = () => {
  const { t } = useTranslation();
  const [activeKey, setActiveKey] = useState('payment');
  const [userUsage, setUserUsage] = useState(null);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    fetchUserUsage();
  }, []);

  // 获取用户使用情况
  const fetchUserUsage = async () => {
    try {
      setLoading(true);
      const usageData = await userApi.getUsage();
      setUserUsage(usageData);
    } catch (error) {
      console.error('获取用户使用情况失败:', error);
      message.error(t('payment.errors.cannotGetUsage'));
    } finally {
      setLoading(false);
    }
  };
  
  // 支付成功后的回调
  const handlePaymentSuccess = (paymentData) => {
    message.success(t('common.success'));
    setActiveKey('history'); // 切换到支付历史记录标签页
    
    // 刷新用户使用情况
    fetchUserUsage();
  };

  // 计算使用进度
  const getUsageProgress = () => {
    if (!userUsage || userUsage.active_subscription) return 100;
    const total = userUsage.free_usage_limit || 10;
    const used = total - (userUsage.remaining_free_usage || 0);
    return Math.round((used / total) * 100);
  };

  // 获取用户等级
  const getUserLevel = () => {
    if (!userUsage) return { 
      level: t('payment.userStatus.freeUser'), 
      color: '#8c8c8c', 
      icon: <UserOutlined /> 
    };
    
    if (userUsage.active_subscription) {
      return { 
        level: t('payment.userStatus.premiumUser'), 
        color: '#52c41a', 
        icon: <CrownOutlined />,
        badge: true 
      };
    }
    
    const remaining = userUsage.remaining_free_usage || 0;
    if (remaining > 5) {
      return { 
        level: t('payment.userStatus.freeUser'), 
        color: '#1890ff', 
        icon: <UserOutlined /> 
      };
    } else if (remaining > 0) {
      return { 
        level: t('payment.userStatus.limitedUser'), 
        color: '#faad14', 
        icon: <ClockCircleOutlined /> 
      };
    } else {
      return { 
        level: t('payment.userStatus.expiredUser'), 
        color: '#f5222d', 
        icon: <ClockCircleOutlined /> 
      };
    }
  };
  
  // 渲染美化的用户状态卡片
  const renderUserStatusCard = () => {
    if (loading) {
      return (
        <Card className="user-status-card">
          <Spin size="large" />
        </Card>
      );
    }
    
    if (!userUsage) {
      return (
        <Alert 
          type="error" 
          message={t('payment.errors.cannotGetUsage')} 
          showIcon 
          style={{ marginBottom: 24 }}
        />
      );
    }

    const userLevel = getUserLevel();
    const progress = getUsageProgress();

    return (
      <Card 
        className="user-status-card"
        style={{ 
          marginBottom: 24,
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          color: 'white',
          border: 'none'
        }}
      >
        <Row gutter={[24, 16]} align="middle">
          <Col xs={24} sm={12} md={8}>
            <Space direction="vertical" size="small">
              <Space>
                <Avatar 
                  size={40} 
                  style={{ backgroundColor: userLevel.color }}
                  icon={userLevel.icon}
                />
                <div>
                  <Text style={{ color: 'white', fontSize: '16px', fontWeight: 'bold' }}>
                    用户状态
                  </Text>
                  <br />
                  <Badge 
                    status={userLevel.badge ? "processing" : "default"}
                    text={
                      <Text style={{ color: 'white' }}>
                        {userLevel.level} 用户
                      </Text>
                    }
                  />
                </div>
              </Space>
            </Space>
          </Col>
          
          <Col xs={24} sm={12} md={8}>
            {userUsage.active_subscription ? (
              <div>
                <Statistic
                  title={<Text style={{ color: 'rgba(255,255,255,0.8)' }}>当前计划</Text>}
                  value={userUsage.active_subscription.plan_name}
                  valueStyle={{ color: 'white', fontSize: '18px' }}
                  prefix={<TrophyOutlined />}
                />
                <Text style={{ color: 'rgba(255,255,255,0.8)' }}>
                  到期: {new Date(userUsage.active_subscription.end_time).toLocaleDateString('zh-CN')}
                </Text>
              </div>
            ) : (
              <div>
                <Statistic
                  title={<Text style={{ color: 'rgba(255,255,255,0.8)' }}>剩余次数</Text>}
                  value={userUsage.remaining_free_usage || 0}
                  valueStyle={{ 
                    color: userUsage.remaining_free_usage > 0 ? '#52c41a' : '#ff4d4f',
                    fontSize: '24px'
                  }}
                  prefix={<GiftOutlined />}
                />
                <Progress 
                  percent={progress} 
                  size="small" 
                  strokeColor="#52c41a"
                  trailColor="rgba(255,255,255,0.3)"
                />
              </div>
            )}
          </Col>
          
          <Col xs={24} sm={24} md={8}>
            <Space direction="vertical" size="small" style={{ width: '100%' }}>
              {userUsage.active_subscription ? (
                <Tag color="green" style={{ fontSize: '14px', padding: '4px 12px' }}>
                  <CheckCircleOutlined /> 无限使用权限
                </Tag>
              ) : userUsage.can_use ? (
                <Tag color="blue" style={{ fontSize: '14px', padding: '4px 12px' }}>
                  <CheckCircleOutlined /> 可以使用
                </Tag>
              ) : (
                <Tag color="orange" style={{ fontSize: '14px', padding: '4px 12px' }}>
                  <ClockCircleOutlined /> 需要充值
                </Tag>
              )}
              
              {!userUsage.active_subscription && (
                <Button 
                  type="primary" 
                  ghost 
                  size="small"
                  onClick={() => setActiveKey('payment')}
                  style={{ width: '100%' }}
                >
                  立即充值
                </Button>
              )}
            </Space>
          </Col>
        </Row>
      </Card>
    );
  };

  // 渲染快速充值卡片
  const renderQuickTopupCards = () => (
    <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
      <Col xs={24} sm={8}>
        <Card 
          hoverable
          className="quick-topup-card"
          onClick={() => setActiveKey('payment')}
          style={{ textAlign: 'center', cursor: 'pointer' }}
        >
          <Space direction="vertical">
            <Avatar size={48} style={{ backgroundColor: '#1890ff' }}>
              <DollarOutlined />
            </Avatar>
            <Title level={4} style={{ margin: 0 }}>单次使用</Title>
            <Text type="secondary">$1.00 / 1次检测</Text>
            <Tag color="blue">最受欢迎</Tag>
          </Space>
        </Card>
      </Col>
      
      <Col xs={24} sm={8}>
        <Card 
          hoverable
          className="quick-topup-card"
          onClick={() => setActiveKey('payment')}
          style={{ textAlign: 'center', cursor: 'pointer' }}
        >
          <Space direction="vertical">
            <Avatar size={48} style={{ backgroundColor: '#52c41a' }}>
              <StarOutlined />
            </Avatar>
            <Title level={4} style={{ margin: 0 }}>十次套餐</Title>
            <Text type="secondary">$5.00 / 10次检测</Text>
            <Tag color="green">超值优惠</Tag>
          </Space>
        </Card>
      </Col>
      
      <Col xs={24} sm={8}>
        <Card 
          hoverable
          className="quick-topup-card"
          onClick={() => setActiveKey('payment')}
          style={{ textAlign: 'center', cursor: 'pointer' }}
        >
          <Space direction="vertical">
            <Avatar size={48} style={{ backgroundColor: '#722ed1' }}>
              <CrownOutlined />
            </Avatar>
            <Title level={4} style={{ margin: 0 }}>百次套餐</Title>
            <Text type="secondary">$10.00 / 100次检测</Text>
            <Tag color="purple">企业首选</Tag>
          </Space>
        </Card>
      </Col>
    </Row>
  );

  // 渲染功能特色
  const renderFeatures = () => (
    <Card style={{ marginBottom: 24 }}>
      <Title level={4}>为什么选择我们？</Title>
      <Row gutter={[24, 16]}>
        <Col xs={24} sm={12} md={6}>
          <Space direction="vertical" align="center" style={{ width: '100%' }}>
            <Avatar size={40} style={{ backgroundColor: '#52c41a' }}>
              <SafetyCertificateOutlined />
            </Avatar>
            <Text strong>安全可靠</Text>
            <Text type="secondary" style={{ textAlign: 'center' }}>
              银行级别加密，保护您的支付信息
            </Text>
          </Space>
        </Col>
        
        <Col xs={24} sm={12} md={6}>
          <Space direction="vertical" align="center" style={{ width: '100%' }}>
            <Avatar size={40} style={{ backgroundColor: '#1890ff' }}>
              <CheckCircleOutlined />
            </Avatar>
            <Text strong>即时到账</Text>
            <Text type="secondary" style={{ textAlign: 'center' }}>
              支付完成后立即生效，无需等待
            </Text>
          </Space>
        </Col>
        
        <Col xs={24} sm={12} md={6}>
          <Space direction="vertical" align="center" style={{ width: '100%' }}>
            <Avatar size={40} style={{ backgroundColor: '#722ed1' }}>
              <TrophyOutlined />
            </Avatar>
            <Text strong>精准检测</Text>
            <Text type="secondary" style={{ textAlign: 'center' }}>
              AI驱动的高精度内容检测技术
            </Text>
          </Space>
        </Col>
        
        <Col xs={24} sm={12} md={6}>
          <Space direction="vertical" align="center" style={{ width: '100%' }}>
            <Avatar size={40} style={{ backgroundColor: '#faad14' }}>
              <GiftOutlined />
            </Avatar>
            <Text strong>优惠套餐</Text>
            <Text type="secondary" style={{ textAlign: 'center' }}>
              批量购买享受更多优惠折扣
            </Text>
          </Space>
        </Col>
      </Row>
    </Card>
  );
  
  return (
    <div className="payment-page-container" style={{ padding: '24px', background: '#f5f5f5', minHeight: '100vh' }}>
      <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
        {/* 页面标题 */}
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <Title level={1} style={{ marginBottom: 8 }}>
            充值与订阅中心
          </Title>
          <Paragraph style={{ fontSize: '16px', color: '#666' }}>
            选择适合您的套餐，享受专业的AI内容检测服务
          </Paragraph>
        </div>

        {/* 用户状态卡片 */}
        {renderUserStatusCard()}

        {/* 快速充值卡片 */}
        {renderQuickTopupCards()}

        {/* 功能特色 */}
        {renderFeatures()}

        {/* 主要内容标签页 */}
        <Card>
          <Tabs 
            activeKey={activeKey} 
            onChange={setActiveKey} 
            type="card"
            size="large"
            items={[
              {
                key: 'payment',
                label: (
                  <Space>
                    <CreditCardOutlined />
                    充值/订阅
                  </Space>
                ),
                children: (
                  <Row gutter={[24, 24]}>
                    <Col xs={24} lg={16}>
                      <PaymentForm onSuccess={handlePaymentSuccess} />
                    </Col>
                    <Col xs={24} lg={8}>
                      <Card title="💡 支付帮助" size="small">
                        <Timeline
                          size="small"
                          items={[
                            {
                              color: 'blue',
                              children: (
                                <div>
                                  <Text strong>选择套餐</Text>
                                  <br />
                                  <Text type="secondary">根据使用频率选择合适的套餐</Text>
                                </div>
                              )
                            },
                            {
                              color: 'green',
                              children: (
                                <div>
                                  <Text strong>安全支付</Text>
                                  <br />
                                  <Text type="secondary">支持信用卡、微信、支付宝</Text>
                                </div>
                              )
                            },
                            {
                              color: 'purple',
                              children: (
                                <div>
                                  <Text strong>即时生效</Text>
                                  <br />
                                  <Text type="secondary">支付完成后立即可用</Text>
                                </div>
                              )
                            }
                          ]}
                        />
                        
                        <Divider />
                        
                        <Title level={5}>🎁 优惠说明</Title>
                        <ul style={{ paddingLeft: 16, color: '#666' }}>
                          <li>单次购买：适合偶尔使用</li>
                          <li>十次套餐：节省50%费用</li>
                          <li>百次套餐：节省90%费用</li>
                        </ul>
                        
                        <Alert
                          type="info"
                          message="安全保障"
                          description="所有支付信息均采用SSL加密传输，您的信息安全有保障。"
                          showIcon
                          style={{ marginTop: 16 }}
                        />
                      </Card>
                    </Col>
                  </Row>
                )
              },
              {
                key: 'history',
                label: (
                  <Space>
                    <HistoryOutlined />
                    支付记录
                  </Space>
                ),
                children: <PaymentHistory />
              },
              {
                key: 'subscription',
                                 label: (
                   <Space>
                     <ShoppingOutlined />
                     我的订阅
                   </Space>
                 ),
                children: <SubscriptionManager />
              }
            ]}
          />
        </Card>
        
        {/* 底部信息 */}
        <div style={{ textAlign: 'center', marginTop: 32, color: '#999' }}>
          <Text type="secondary">
            如有任何支付问题，请联系我们的客服团队 | 
            <a href="mailto:support@vibe-checker.com" style={{ marginLeft: 8 }}>
              support@vibe-checker.com
            </a>
          </Text>
        </div>
      </div>
    </div>
  );
};

export default PaymentPage; 