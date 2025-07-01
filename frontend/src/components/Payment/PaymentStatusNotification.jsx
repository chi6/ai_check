import React from 'react';
import { Alert, Result, Button, Card, Typography, Space, Divider } from 'antd';
import { 
  CheckCircleOutlined, 
  CloseCircleOutlined, 
  LoadingOutlined, 
  ExclamationCircleOutlined,
  ReloadOutlined,
  HomeOutlined
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';

const { Title, Text, Paragraph } = Typography;

const PaymentStatusNotification = ({ 
  status, 
  message, 
  paymentDetails, 
  onRetry, 
  onClose 
}) => {
  const navigate = useNavigate();

  const getStatusConfig = () => {
    switch (status) {
      case 'success':
        return {
          icon: <CheckCircleOutlined style={{ color: '#52c41a' }} />,
          title: '支付成功！',
          type: 'success',
          description: '您的支付已成功完成，检测次数已添加到您的账户中。',
          showActions: true
        };
      case 'failed':
        return {
          icon: <CloseCircleOutlined style={{ color: '#ff4d4f' }} />,
          title: '支付失败',
          type: 'error',
          description: '支付处理失败，请重试或联系客服。',
          showActions: true
        };
      case 'processing':
        return {
          icon: <LoadingOutlined style={{ color: '#1890ff' }} />,
          title: '支付处理中...',
          type: 'info',
          description: '正在处理您的支付，请稍候...',
          showActions: false
        };
      case 'canceled':
        return {
          icon: <ExclamationCircleOutlined style={{ color: '#faad14' }} />,
          title: '支付已取消',
          type: 'warning',
          description: '您已取消支付，如需继续请重新选择支付方式。',
          showActions: true
        };
      case 'pending':
        return {
          icon: <LoadingOutlined style={{ color: '#faad14' }} />,
          title: '支付待处理',
          type: 'warning',
          description: '支付正在处理中，我们会在处理完成后通知您。',
          showActions: true
        };
      default:
        return {
          icon: <ExclamationCircleOutlined style={{ color: '#d9d9d9' }} />,
          title: '未知状态',
          type: 'info',
          description: '支付状态未知，请联系客服确认。',
          showActions: true
        };
    }
  };

  const config = getStatusConfig();

  const handleGoHome = () => {
    navigate('/dashboard');
  };

  const handleRetry = () => {
    if (onRetry) {
      onRetry();
    } else {
      navigate('/payment');
    }
  };

  const renderPaymentDetails = () => {
    if (!paymentDetails) return null;

    return (
      <Card size="small" style={{ marginTop: 16 }}>
        <Title level={5}>支付详情</Title>
        <div style={{ fontSize: '14px' }}>
          {paymentDetails.planName && (
            <div style={{ marginBottom: 8 }}>
              <Text strong>订阅计划：</Text>
              <Text>{paymentDetails.planName}</Text>
            </div>
          )}
          {paymentDetails.amount && (
            <div style={{ marginBottom: 8 }}>
              <Text strong>支付金额：</Text>
              <Text>${paymentDetails.amount} {paymentDetails.currency || 'USD'}</Text>
            </div>
          )}
          {paymentDetails.paymentId && (
            <div style={{ marginBottom: 8 }}>
              <Text strong>支付ID：</Text>
              <Text code>{paymentDetails.paymentId}</Text>
            </div>
          )}
          {paymentDetails.usageCredits && (
            <div style={{ marginBottom: 8 }}>
              <Text strong>获得检测次数：</Text>
              <Text style={{ color: '#52c41a', fontWeight: 'bold' }}>
                {paymentDetails.usageCredits} 次
              </Text>
            </div>
          )}
          {paymentDetails.timestamp && (
            <div style={{ marginBottom: 8 }}>
              <Text strong>处理时间：</Text>
              <Text>{new Date(paymentDetails.timestamp).toLocaleString()}</Text>
            </div>
          )}
        </div>
      </Card>
    );
  };

  const renderActions = () => {
    if (!config.showActions) return null;

    return (
      <Space size="middle" style={{ marginTop: 24 }}>
        <Button 
          type="primary" 
          icon={<HomeOutlined />}
          onClick={handleGoHome}
        >
          返回首页
        </Button>
        {(status === 'failed' || status === 'canceled') && (
          <Button 
            icon={<ReloadOutlined />}
            onClick={handleRetry}
          >
            重试支付
          </Button>
        )}
        {onClose && (
          <Button onClick={onClose}>
            关闭
          </Button>
        )}
      </Space>
    );
  };

  return (
    <div style={{ padding: '20px', maxWidth: '600px', margin: '0 auto' }}>
      <Result
        icon={config.icon}
        title={config.title}
        subTitle={
          <div>
            <Paragraph>{config.description}</Paragraph>
            {message && (
              <Alert 
                message={message} 
                type={config.type} 
                showIcon={false}
                style={{ marginTop: 16 }}
              />
            )}
          </div>
        }
        extra={renderActions()}
      />
      
      {renderPaymentDetails()}
      
      {status === 'processing' && (
        <div style={{ textAlign: 'center', marginTop: 20 }}>
          <Text type="secondary">
            支付处理通常需要几分钟时间，请耐心等待...
          </Text>
        </div>
      )}
    </div>
  );
};

export default PaymentStatusNotification; 