import React, { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Card, Typography, Spin, Result, Button, message } from 'antd';
import { CheckCircleOutlined, CloseCircleOutlined } from '@ant-design/icons';
import { paymentApi } from '../api/api';

const { Title, Text } = Typography;

const PaymentStatus = () => {
  const [status, setStatus] = useState('processing');
  const [loading, setLoading] = useState(true);
  const [paymentDetails, setPaymentDetails] = useState(null);
  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    const processPayment = async () => {
      try {
        const params = new URLSearchParams(location.search);
        if (params.get('success') === 'true') {
          setStatus('success');
          setPaymentDetails({
            plan_id: params.get('plan_id'),
            timestamp: new Date().toISOString()
          });
        } else if (params.get('canceled') === 'true') {
          setStatus('failed');
        } else {
          setStatus('failed');
        }
      } catch (error) {
        setStatus('failed');
      } finally {
        setLoading(false);
      }
    };

    processPayment();
  }, [location]);

  const handleBackToDashboard = () => {
    navigate('/dashboard');
  };

  if (loading) {
    return (
      <div style={{ padding: '50px', textAlign: 'center' }}>
        <Spin size="large" />
        <Title level={3}>正在处理支付结果...</Title>
      </div>
    );
  }

  return (
    <div style={{ padding: '50px' }}>
      <Card>
        {status === 'success' ? (
          <Result
            status="success"
            icon={<CheckCircleOutlined />}
            title="支付成功！"
            subTitle="您的支付已经完成，感谢您的购买"
            extra={[
              <Button type="primary" key="dashboard" onClick={handleBackToDashboard}>
                返回控制台
              </Button>
            ]}
          />
        ) : (
          <Result
            status="error"
            icon={<CloseCircleOutlined />}
            title="支付处理失败"
            subTitle="很抱歉，您的支付未能成功处理，请稍后重试"
            extra={[
              <Button type="primary" key="dashboard" onClick={handleBackToDashboard}>
                返回控制台
              </Button>
            ]}
          />
        )}
      </Card>
    </div>
  );
};

export default PaymentStatus; 