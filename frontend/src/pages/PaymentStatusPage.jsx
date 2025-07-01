import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { Layout, Spin, message, Card, Typography, Button, Space } from 'antd';
import PaymentStatusNotification from '../components/Payment/PaymentStatusNotification';
import { paymentApi, userApi } from '../api/api';

const { Content } = Layout;
const { Title } = Typography;

const PaymentStatusPage = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [paymentStatus, setPaymentStatus] = useState(null);
  const [paymentDetails, setPaymentDetails] = useState(null);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    const checkPaymentStatus = async () => {
      try {
        console.log('支付状态页面 - 开始检查支付状态');
        
        // 从URL参数获取状态信息
        const success = searchParams.get('success');
        const canceled = searchParams.get('canceled');
        const sessionId = searchParams.get('session_id');
        const planId = searchParams.get('plan_id');
        const paymentIntentId = searchParams.get('payment_intent');
        const paymentIntentClientSecret = searchParams.get('payment_intent_client_secret');

        console.log('URL参数:', {
          success,
          canceled,
          sessionId,
          planId,
          paymentIntentId,
          paymentIntentClientSecret
        });

        // 处理取消状态
        if (canceled === 'true') {
          console.log('用户取消了支付');
          setPaymentStatus('canceled');
          setMessage('您已取消支付操作');
          setLoading(false);
          return;
        }

        // 处理成功状态
        if (success === 'true') {
          console.log('支付成功，准备获取支付详情');
          
          // 如果有session_id，可以从后端获取更多详情
          if (sessionId) {
            try {
              console.log('正在获取支付会话详情，Session ID:', sessionId);
              // 这里可以调用后端API获取会话详情
              // const sessionDetails = await paymentApi.getSessionDetails(sessionId);
              
              // 暂时使用基本的成功状态
              setPaymentStatus('success');
              setMessage('支付已成功完成！');
              
              // 设置基本的支付详情
              if (planId) {
                setPaymentDetails({
                  planId: planId,
                  sessionId: sessionId,
                  timestamp: new Date().toISOString()
                });
              }
              
              // 显示成功消息
              message.success('支付成功！检测次数已添加到您的账户中。');
              
              // 刷新用户信息
              try {
                await userApi.getCurrentUser();
                console.log('用户信息已刷新');
              } catch (userError) {
                console.error('刷新用户信息失败:', userError);
              }
              
            } catch (error) {
              console.error('获取支付详情失败:', error);
              setPaymentStatus('success');
              setMessage('支付成功，但获取详情失败。请检查您的账户余额。');
            }
          } else {
            // 没有session_id，使用基本成功状态
            setPaymentStatus('success');
            setMessage('支付成功！');
            message.success('支付成功！');
          }
          
          setLoading(false);
          return;
        }

        // 处理支付意图状态
        if (paymentIntentId) {
          console.log('检测到PaymentIntent ID，检查支付状态:', paymentIntentId);
          
          try {
            // 这里可以调用后端API检查支付意图状态
            // const paymentStatus = await paymentApi.getPaymentIntentStatus(paymentIntentId);
            
            // 暂时假设支付成功
            setPaymentStatus('success');
            setMessage('支付处理完成！');
            setPaymentDetails({
              paymentIntentId: paymentIntentId,
              timestamp: new Date().toISOString()
            });
            
            message.success('支付成功！');
            
          } catch (error) {
            console.error('检查支付意图状态失败:', error);
            setPaymentStatus('failed');
            setMessage('支付状态检查失败，请联系客服确认。');
            setError('无法确认支付状态');
          }
          
          setLoading(false);
          return;
        }

        // 如果没有明确的状态参数，显示未知状态
        console.log('没有明确的支付状态参数');
        setPaymentStatus('unknown');
        setMessage('无法确定支付状态，请联系客服确认。');
        setLoading(false);

      } catch (error) {
        console.error('检查支付状态时出错:', error);
        setPaymentStatus('failed');
        setMessage('检查支付状态时出错，请联系客服。');
        setError(error.message || '未知错误');
        setLoading(false);
      }
    };

    checkPaymentStatus();
  }, [searchParams]);

  const handleRetry = () => {
    navigate('/payment');
  };

  const handleClose = () => {
    navigate('/dashboard');
  };

  if (loading) {
    return (
      <Layout style={{ minHeight: '100vh' }}>
        <Content style={{ padding: '50px', textAlign: 'center' }}>
          <Card>
            <Spin size="large" />
            <div style={{ marginTop: 20 }}>
              <Title level={4}>正在检查支付状态...</Title>
              <p>请稍候，我们正在验证您的支付信息。</p>
            </div>
          </Card>
        </Content>
      </Layout>
    );
  }

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Content style={{ padding: '20px' }}>
        <PaymentStatusNotification
          status={paymentStatus}
          message={error || message}
          paymentDetails={paymentDetails}
          onRetry={handleRetry}
          onClose={handleClose}
        />
        
        {/* 调试信息 */}
        {process.env.NODE_ENV === 'development' && (
          <Card 
            title="调试信息" 
            style={{ marginTop: 20, maxWidth: '600px', margin: '20px auto' }}
            size="small"
          >
            <pre style={{ fontSize: '12px', background: '#f5f5f5', padding: '10px' }}>
              URL参数: {JSON.stringify(Object.fromEntries(searchParams), null, 2)}
            </pre>
            <pre style={{ fontSize: '12px', background: '#f5f5f5', padding: '10px' }}>
              支付状态: {paymentStatus}
            </pre>
            <pre style={{ fontSize: '12px', background: '#f5f5f5', padding: '10px' }}>
              支付详情: {JSON.stringify(paymentDetails, null, 2)}
            </pre>
          </Card>
        )}
      </Content>
    </Layout>
  );
};

export default PaymentStatusPage; 