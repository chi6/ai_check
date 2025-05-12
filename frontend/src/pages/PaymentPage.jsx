import React, { useState, useEffect } from 'react';
import { Tabs, Row, Col, message, Typography, Card, Spin } from 'antd';
import PaymentForm from '../components/Payment/PaymentForm';
import PaymentHistory from '../components/Payment/PaymentHistory';
import SubscriptionManager from '../components/Payment/SubscriptionManager';
import { userApi } from '../api/api';

const { TabPane } = Tabs;
const { Title, Paragraph, Text } = Typography;

const PaymentPage = () => {
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
      message.error('获取用户使用情况失败');
    } finally {
      setLoading(false);
    }
  };
  
  // 支付成功后的回调
  const handlePaymentSuccess = (paymentData) => {
    message.success('支付请求已提交');
    setActiveKey('history'); // 切换到支付历史记录标签页
    
    // 刷新用户使用情况
    fetchUserUsage();
  };
  
  // 渲染用户使用情况摘要
  const renderUsageSummary = () => {
    if (loading) {
      return <Spin size="small" />;
    }
    
    if (!userUsage) {
      return <Text type="danger">无法获取使用情况</Text>;
    }
    
    return (
      <Card className="usage-summary-card" style={{ marginBottom: 24 }}>
        <Title level={5}>您的使用情况</Title>
        
        {userUsage.active_subscription ? (
          <div>
            <Paragraph>
              <Text strong>当前计划: </Text> 
              <Text type="success">{userUsage.active_subscription.plan_name}</Text>
            </Paragraph>
            <Paragraph>
              <Text strong>到期时间: </Text> 
              <Text>{new Date(userUsage.active_subscription.end_time).toLocaleDateString('zh-CN')}</Text>
            </Paragraph>
            <Paragraph>
              <Text type="success">您可以无限次使用检测服务！</Text>
            </Paragraph>
          </div>
        ) : (
          <div>
            <Paragraph>
              <Text strong>剩余免费次数: </Text> 
              <Text type={userUsage.remaining_free_usage > 0 ? "success" : "danger"}>
                {userUsage.remaining_free_usage}
              </Text>
            </Paragraph>
            <Paragraph>
              {userUsage.can_use ? 
                <Text type="success">您目前可以使用检测服务</Text> : 
                <Text type="warning">{userUsage.reason}</Text>
              }
            </Paragraph>
          </div>
        )}
      </Card>
    );
  };
  
  return (
    <div className="payment-page-container">
      <Title level={2}>充值与订阅管理</Title>
      <Paragraph>购买检测次数或订阅计划，享受无限使用权限</Paragraph>
      
      {renderUsageSummary()}
      
      <Card>
        <Tabs activeKey={activeKey} onChange={setActiveKey} type="card">
          <TabPane tab="充值/订阅" key="payment">
            <Row gutter={[24, 24]}>
              <Col xs={24} lg={16}>
                <PaymentForm onSuccess={handlePaymentSuccess} />
              </Col>
              <Col xs={24} lg={8}>
                <Card className="payment-info-card" title="付款说明">
                  <Paragraph>我们支持以下支付方式:</Paragraph>
                  <ul>
                    <li><Text strong>信用卡支付 (Stripe)</Text> - 适用于国际用户</li>
                    <li><Text strong>微信支付</Text> - 适用于中国大陆用户</li>
                    <li><Text strong>支付宝</Text> - 适用于中国大陆用户</li>
                  </ul>
                  <Title level={5}>计划说明</Title>
                  <ul>
                    <li><Text strong>单次使用</Text>: 每次1美元，适合临时使用</li>
                    <li><Text strong>十次使用</Text>: 5美元购买10次检测，适合定期使用</li>
                    <li><Text strong>百次使用</Text>: 10美元购买100次检测，适合频繁使用</li>
                  </ul>
                  <Paragraph type="secondary" style={{ marginTop: 16 }}>
                    所有支付信息将被安全加密处理。如有问题，请联系客服。
                  </Paragraph>
                </Card>
              </Col>
            </Row>
          </TabPane>
          
          <TabPane tab="支付记录" key="history">
            <PaymentHistory />
          </TabPane>
          
          <TabPane tab="我的订阅" key="subscription">
            <SubscriptionManager />
          </TabPane>
        </Tabs>
      </Card>
    </div>
  );
};

export default PaymentPage; 