import React, { useState, useEffect } from 'react';
import { 
  Form, Button, Card, message, Spin, Row, Col, Typography, 
  Badge, Space, Tag, Alert, Divider, Radio, Tooltip
} from 'antd';
import { 
  CreditCardOutlined, DollarOutlined, StarOutlined, 
  CrownOutlined, CheckOutlined, FireOutlined,
  SafetyCertificateOutlined, ThunderboltOutlined
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { paymentApi } from '../../api/api';

const { Title, Text, Paragraph } = Typography;

const PaymentForm = ({ onSuccess }) => {
  const { t } = useTranslation();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [selectedPlan, setSelectedPlan] = useState(null);
  const [error, setError] = useState('');
  const [officialPlans, setOfficialPlans] = useState([]);

  useEffect(() => {
    // 设置正式订阅计划
    setOfficialPlans([
      {
        id: 'single_use_official',
        name: t('payment.plans.singleUse.name'),
        description: t('payment.plans.singleUse.description'),
        plan_type: 'single_use',
        price: 1.0,
        currency: 'USD',
        duration_days: 0,
        is_active: true,
        stripe_link: 'https://buy.stripe.com/bIYcPz53W8aM0JaaEF',
        usage_credits: 1,
        tag: t('payment.plans.singleUse.tag'),
        tagColor: 'blue',
        icon: <DollarOutlined />,
        features: t('payment.plans.singleUse.features', { returnObjects: true })
      },
      {
        id: 'ten_use_official',
        name: t('payment.plans.tenUse.name'),
        description: t('payment.plans.tenUse.description'),
        plan_type: 'single_use',
        price: 5.0,
        currency: 'USD',
        duration_days: 0,
        is_active: true,
        stripe_link: 'https://buy.stripe.com/eVabLv2VO62EbnO5kk',
        usage_credits: 10,
        tag: t('payment.plans.tenUse.tag'),
        tagColor: 'green',
        icon: <StarOutlined />,
        features: t('payment.plans.tenUse.features', { returnObjects: true }),
        discount: t('payment.plans.tenUse.discount'),
        popular: true,
        popularText: t('payment.plans.tenUse.popular')
      },
      {
        id: 'hundred_use_official',
        name: t('payment.plans.hundredUse.name'),
        description: t('payment.plans.hundredUse.description'),
        plan_type: 'single_use',
        price: 10.0,
        currency: 'USD',
        duration_days: 0,
        is_active: true,
        stripe_link: 'https://buy.stripe.com/4gw8zjdAsdv63VmcMO',
        usage_credits: 100,
        tag: t('payment.plans.hundredUse.tag'),
        tagColor: 'purple',
        icon: <CrownOutlined />,
        features: t('payment.plans.hundredUse.features', { returnObjects: true }),
        discount: t('payment.plans.hundredUse.discount')
      }
    ]);
  }, [t]);

  // 处理计划选择
  const handlePlanSelect = (plan) => {
    console.log('选择计划:', plan);
    setSelectedPlan(plan);
    setError('');
  };

  // 提交表单
  const handleSubmit = async () => {
    if (!selectedPlan) {
      const errorMsg = t('payment.errors.selectPlanRequired');
      setError(errorMsg);
      message.warning(errorMsg);
      return;
    }
    
    setLoading(true);
    setError('');
    
    try {
      const baseUrl = window.location.origin;
      const successUrl = `${baseUrl}/payment/status?success=true&plan_id=${selectedPlan.id}`;
      const cancelUrl = `${baseUrl}/payment/status?canceled=true`;
      
      console.log('创建Checkout会话，计划:', selectedPlan.id);
      
      const result = await paymentApi.createStripeCheckout(
        selectedPlan.id, 
        successUrl, 
        cancelUrl
      );
      
      if (result && result.checkout_url) {
        console.log('重定向到Stripe Checkout:', result.checkout_url);
        window.location.href = result.checkout_url;
      } else {
        throw new Error(t('payment.errors.paymentInitFailed'));
      }
    } catch (error) {
      console.error('支付初始化失败:', error);
      const errorMsg = error.response?.data?.detail || error.message || t('payment.errors.paymentInitFailed');
      setError(errorMsg);
      message.error(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  // 渲染计划卡片
  const renderPlanCard = (plan) => {
    const isSelected = selectedPlan && selectedPlan.id === plan.id;
    const pricePerUnit = plan.price / plan.usage_credits;
    
    return (
      <Col xs={24} sm={12} lg={8} key={plan.id}>
        <Card
          className={`plan-card ${isSelected ? 'selected' : ''} ${plan.popular ? 'popular' : ''}`}
          hoverable
          onClick={() => handlePlanSelect(plan)}
          style={{
            height: '100%',
            border: isSelected ? '2px solid #1890ff' : '1px solid #d9d9d9',
            borderRadius: '12px',
            position: 'relative',
            cursor: 'pointer',
            transition: 'all 0.3s ease'
          }}
          bodyStyle={{ padding: '24px' }}
        >
          {/* 热门标签 */}
          {plan.popular && (
            <div 
              style={{
                position: 'absolute',
                top: '-8px',
                right: '16px',
                background: 'linear-gradient(135deg, #ff6b6b, #ee5a24)',
                color: 'white',
                padding: '4px 12px',
                borderRadius: '12px',
                fontSize: '12px',
                fontWeight: 'bold',
                boxShadow: '0 2px 8px rgba(238, 90, 36, 0.3)'
              }}
            >
              <FireOutlined style={{ marginRight: 4 }} />
              {plan.popularText}
            </div>
          )}
          
          {/* 折扣标签 */}
          {plan.discount && (
            <Badge.Ribbon 
              text={plan.discount} 
              color="red"
              style={{ top: '16px', right: '-8px' }}
            />
          )}

          <div style={{ textAlign: 'center' }}>
            {/* 图标 */}
            <div 
              style={{
                width: '56px',
                height: '56px',
                borderRadius: '50%',
                background: isSelected ? '#1890ff' : '#f0f0f0',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                margin: '0 auto 16px',
                fontSize: '24px',
                color: isSelected ? 'white' : '#666',
                transition: 'all 0.3s ease'
              }}
            >
              {plan.icon}
            </div>

            {/* 标题 */}
            <Title level={4} style={{ margin: '0 0 8px', fontSize: '18px' }}>
              {plan.name}
            </Title>

            {/* 标签 */}
            <Tag color={plan.tagColor} style={{ marginBottom: '16px' }}>
              {plan.tag}
            </Tag>

            {/* 价格 */}
            <div style={{ marginBottom: '16px' }}>
              <div style={{ fontSize: '32px', fontWeight: 'bold', color: '#1890ff' }}>
                ${plan.price}
              </div>
              <Text type="secondary">
                {t('payment.plans.timesDetection', { count: plan.usage_credits })} • {t('payment.plans.pricePerUnit', { price: pricePerUnit.toFixed(2) })}
              </Text>
            </div>

            {/* 描述 */}
            <Paragraph type="secondary" style={{ fontSize: '14px', marginBottom: '16px' }}>
              {plan.description}
            </Paragraph>

            {/* 功能列表 */}
            <div style={{ textAlign: 'left', marginBottom: '16px' }}>
              {plan.features.map((feature, index) => (
                <div key={index} style={{ marginBottom: '8px' }}>
                  <CheckOutlined style={{ color: '#52c41a', marginRight: '8px' }} />
                  <Text style={{ fontSize: '14px' }}>{feature}</Text>
                </div>
              ))}
            </div>

            {/* 选择状态 */}
            {isSelected && (
              <div 
                style={{
                  position: 'absolute',
                  top: '12px',
                  left: '12px',
                  width: '24px',
                  height: '24px',
                  borderRadius: '50%',
                  background: '#1890ff',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: 'white',
                  fontSize: '12px'
                }}
              >
                <CheckOutlined />
              </div>
            )}
          </div>
        </Card>
      </Col>
    );
  };

  return (
    <div style={{ maxWidth: '100%' }}>
      {/* 错误提示 */}
      {error && (
        <Alert
          type="error"
          message={t('payment.errors.paymentError')}
          description={error}
          showIcon
          closable
          style={{ marginBottom: 24 }}
          onClose={() => setError('')}
        />
      )}

      {/* 计划选择标题 */}
      <div style={{ textAlign: 'center', marginBottom: 32 }}>
        <Title level={3} style={{ marginBottom: 8 }}>
          {t('payment.plans.selectTitle')}
        </Title>
        <Paragraph type="secondary">
          {t('payment.plans.selectSubtitle')}
        </Paragraph>
      </div>

      {/* 计划卡片 */}
      <Row gutter={[24, 24]} style={{ marginBottom: 32 }}>
        {officialPlans.map(plan => renderPlanCard(plan))}
      </Row>

      {/* 选中计划摘要 */}
      {selectedPlan && (
        <Card 
          style={{ 
            marginBottom: 24,
            background: 'linear-gradient(135deg, #e6f7ff 0%, #f0f9ff 100%)',
            border: '1px solid #1890ff'
          }}
        >
          <Row align="middle" gutter={16}>
            <Col flex="1">
              <Space>
                <div 
                  style={{
                    width: '40px',
                    height: '40px',
                    borderRadius: '50%',
                    background: '#1890ff',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: 'white'
                  }}
                >
                  {selectedPlan.icon}
                </div>
                <div>
                  <Title level={5} style={{ margin: 0, color: '#1890ff' }}>
                    {t('payment.selectedPlan.title', { planName: selectedPlan.name })}
                  </Title>
                  <Text type="secondary">
                    {t('payment.selectedPlan.subtitle', { 
                      price: selectedPlan.price, 
                      count: selectedPlan.usage_credits 
                    })}
                  </Text>
                </div>
              </Space>
            </Col>
            <Col>
              <Button 
                type="link" 
                onClick={() => setSelectedPlan(null)}
                style={{ color: '#666' }}
              >
                {t('payment.selectedPlan.reselect')}
              </Button>
            </Col>
          </Row>
        </Card>
      )}

      {/* 支付按钮 */}
      <div style={{ textAlign: 'center', marginBottom: 24 }}>
        <Button
          type="primary"
          size="large"
          icon={<CreditCardOutlined />}
          loading={loading}
          disabled={!selectedPlan}
          onClick={handleSubmit}
          style={{
            height: '48px',
            padding: '0 48px',
            fontSize: '16px',
            borderRadius: '24px',
            background: selectedPlan ? 'linear-gradient(135deg, #1890ff 0%, #52c41a 100%)' : undefined,
            border: 'none',
            boxShadow: selectedPlan ? '0 4px 15px rgba(24, 144, 255, 0.3)' : undefined
          }}
        >
          {loading 
            ? t('payment.paymentButton.processing') 
            : selectedPlan 
              ? t('payment.paymentButton.payNow', { amount: selectedPlan.price })
              : t('payment.paymentButton.selectPlan')
          }
        </Button>
      </div>

      {/* 安全保障信息 */}
      <Card size="small" style={{ background: '#f9f9f9' }}>
        <Row gutter={[16, 16]} align="middle">
          <Col xs={24} sm={12}>
            <Space>
              <SafetyCertificateOutlined style={{ color: '#52c41a', fontSize: '18px' }} />
              <div>
                <Text strong style={{ fontSize: '14px' }}>{t('payment.security.safePayment')}</Text>
                <br />
                <Text type="secondary" style={{ fontSize: '12px' }}>
                  {t('payment.security.safePaymentDesc')}
                </Text>
              </div>
            </Space>
          </Col>
          <Col xs={24} sm={12}>
            <Space>
              <ThunderboltOutlined style={{ color: '#faad14', fontSize: '18px' }} />
              <div>
                <Text strong style={{ fontSize: '14px' }}>{t('payment.security.instantActivation')}</Text>
                <br />
                <Text type="secondary" style={{ fontSize: '12px' }}>
                  {t('payment.security.instantActivationDesc')}
                </Text>
              </div>
            </Space>
          </Col>
        </Row>
      </Card>
    </div>
  );
};

export default PaymentForm; 