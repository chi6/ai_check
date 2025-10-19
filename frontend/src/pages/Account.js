import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Statistic, Descriptions, Button, Spin, message, Space, Typography } from 'antd';
import { UserOutlined, CreditCardOutlined, CalendarOutlined, MailOutlined, TrophyOutlined } from '@ant-design/icons';
import { userApi } from '../api/api';
import TopupModal from '../components/TopupModal';

const { Title } = Typography;

const Account = () => {
  const [userInfo, setUserInfo] = useState(null);
  const [credits, setCredits] = useState(null);
  const [loading, setLoading] = useState(true);
  const [topupVisible, setTopupVisible] = useState(false);

  const fetchUserData = async () => {
    try {
      setLoading(true);
      const [userResponse, creditsResponse] = await Promise.all([
        userApi.getCurrentUser(),
        userApi.getCredits()
      ]);
      setUserInfo(userResponse);
      setCredits(creditsResponse);
    } catch (error) {
      console.error('获取用户信息失败:', error);
      message.error('加载用户信息失败，请稍后重试');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUserData();
  }, []);

  const handleTopupSuccess = () => {
    // 充值成功后刷新配额
    fetchUserData();
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '100px 0' }}>
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div style={{ padding: '24px' }}>
      <Title level={2}>账户信息</Title>
      
      <Row gutter={[16, 16]}>
        {/* 用户基本信息卡片 */}
        <Col xs={24} lg={12}>
          <Card
            title={
              <Space>
                <UserOutlined />
                <span>个人信息</span>
              </Space>
            }
            bordered={false}
          >
            <Descriptions column={1} bordered>
              <Descriptions.Item label={<><UserOutlined /> 用户名</>}>
                {userInfo?.username || '-'}
              </Descriptions.Item>
              <Descriptions.Item label={<><MailOutlined /> 邮箱</>}>
                {userInfo?.email || '-'}
              </Descriptions.Item>
              <Descriptions.Item label={<><CalendarOutlined /> 注册时间</>}>
                {userInfo?.created_at 
                  ? new Date(userInfo.created_at).toLocaleString('zh-CN') 
                  : '-'}
              </Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>

        {/* 配额信息卡片 */}
        <Col xs={24} lg={12}>
          <Card
            title={
              <Space>
                <CreditCardOutlined />
                <span>配额信息</span>
              </Space>
            }
            bordered={false}
            extra={
              <Button 
                type="primary" 
                onClick={() => setTopupVisible(true)}
              >
                充值
              </Button>
            }
          >
            <Statistic
              title={
                <Space>
                  <TrophyOutlined />
                  <span>剩余额度</span>
                </Space>
              }
              value={credits?.totalCredits || 0}
              suffix="次"
              valueStyle={{ color: '#3f8600' }}
              style={{ marginBottom: 24 }}
            />
            
            {credits?.licenses && credits.licenses.length > 0 && (
              <div>
                <div style={{ marginBottom: 8, fontWeight: 500 }}>许可证列表：</div>
                {credits.licenses.map((license, index) => (
                  <Card 
                    key={license.id} 
                    size="small" 
                    style={{ marginBottom: 8 }}
                  >
                    <Row justify="space-between" align="middle">
                      <Col>
                        <div>许可证 #{index + 1}</div>
                        <div style={{ fontSize: '12px', color: '#666' }}>
                          剩余: {license.creditsRemaining} 次
                        </div>
                      </Col>
                      <Col>
                        {license.exp ? (
                          <div style={{ fontSize: '12px', color: '#999' }}>
                            到期: {new Date(license.exp).toLocaleDateString('zh-CN')}
                          </div>
                        ) : (
                          <div style={{ fontSize: '12px', color: '#999' }}>
                            永久有效
                          </div>
                        )}
                      </Col>
                    </Row>
                  </Card>
                ))}
              </div>
            )}

            {(!credits?.licenses || credits.licenses.length === 0) && (
              <div style={{ 
                padding: '20px', 
                textAlign: 'center', 
                color: '#999',
                background: '#fafafa',
                borderRadius: '4px'
              }}>
                暂无有效许可证，请充值后使用
              </div>
            )}
          </Card>
        </Col>
      </Row>

      {/* 使用说明 */}
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col span={24}>
          <Card
            title="使用说明"
            bordered={false}
          >
            <ul style={{ paddingLeft: 20, lineHeight: '2em' }}>
              <li>每次检测文档将消耗 1 个额度</li>
              <li>额度可通过充值获得，充值后立即生效</li>
              <li>已购买的额度将永久保存在您的账户中</li>
              <li>如有任何问题，请联系客服支持</li>
            </ul>
          </Card>
        </Col>
      </Row>

      <TopupModal 
        open={topupVisible} 
        onClose={() => setTopupVisible(false)} 
        onSuccess={handleTopupSuccess}
      />
    </div>
  );
};

export default Account;

