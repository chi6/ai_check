import React, { useState, useEffect, useRef } from 'react';
import { Modal, Radio, Space, Button, QRCode, message, Alert } from 'antd';
import { payApi, setLicenseToken, userApi } from '../api/api';

const PACKAGES = [
  { 
    packageType: 'detect_once', 
    name: '1次查重', 
    amount: 1.0,
    description: '单次文本查重检测(比淘宝便宜1元)'
  },
  { 
    packageType: 'ai_detect_once', 
    name: '1次AI查询+查重', 
    amount: 4.98,
    description: '单次AI检测+文本查重(比淘宝便宜5元)'
  },
  { 
    packageType: 'unlimited_1day', 
    name: '1天不限次', 
    amount: 19.98,
    description: '24小时内不限次数使用（查重+AI）(比淘宝便宜20元)',
    tag: '热门'
  },
  { 
    packageType: 'unlimited_1week', 
    name: '1周不限次', 
    amount: 39.98,
    description: '7天内不限次数使用（查重+AI）(比淘宝便宜40元)',
    tag: '超值'
  },
];

export default function TopupModal({ open, onClose, onSuccess }) {
  const [selected, setSelected] = useState(PACKAGES[0]);
  const [channel, setChannel] = useState('wechat');
  const [loading, setLoading] = useState(false);
  const [orderId, setOrderId] = useState(null);
  const [payUrl, setPayUrl] = useState(null);
  const [paymentSuccess, setPaymentSuccess] = useState(false);
  const [creditsInfo, setCreditsInfo] = useState(null);
  const timerRef = useRef(null);
  const isProcessingRef = useRef(false);

  useEffect(() => {
    async function poll() {
      if (!orderId || isProcessingRef.current) return;
      try {
        const res = await payApi.poll(orderId);
        if (res.status === 'PAID' && res.licenseToken) {
          // 标记正在处理，避免重复处理
          isProcessingRef.current = true;
          
          // 立即清除定时器
          if (timerRef.current) {
            clearInterval(timerRef.current);
            timerRef.current = null;
          }
          
          setLicenseToken(res.licenseToken);
          
          // 获取用户配额信息
          try {
            const userCredits = await userApi.getCredits();
            setCreditsInfo(userCredits);
            setPaymentSuccess(true);
            message.success('充值成功！');
            // 通知父组件刷新配额显示
            onSuccess?.();
          } catch (e) {
            message.success('充值成功');
            // 通知父组件刷新配额显示
            onSuccess?.();
            onClose?.();
          }
        }
      } catch (e) {}
    }
    
    if (open && orderId && !paymentSuccess && !isProcessingRef.current) {
      timerRef.current = setInterval(poll, 1500);
    }
    
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    };
  }, [open, orderId, paymentSuccess]);

  const onPay = async () => {
    setLoading(true);
    isProcessingRef.current = false; // 重置处理标记
    try {
      const deviceId = localStorage.getItem('deviceId') || '';
      const res = await payApi.createOrder({
        channel,
        packageType: selected.packageType,
        deviceId,
      });
      setOrderId(res.orderId);
      setPayUrl(res.qrcodeUrl || res.payUrl);
    } catch (e) {
      message.error('创建订单失败');
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setPaymentSuccess(false);
    setCreditsInfo(null);
    setOrderId(null);
    setPayUrl(null);
    isProcessingRef.current = false;
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    onClose?.();
  };

  return (
    <Modal 
      open={open} 
      onCancel={handleClose} 
      footer={paymentSuccess ? <Button type="primary" onClick={handleClose}>关闭</Button> : null} 
      title="充值"
    >
      <Space direction="vertical" style={{ width: '100%' }}>
        {paymentSuccess && creditsInfo ? (
          <div>
            <Alert
              message="充值成功！"
              description={
                <div>
                  <p><strong>当前剩余额度:</strong> {creditsInfo.totalCredits} 次</p>
                  <p>您可以在账户页面查看详细配额信息</p>
                </div>
              }
              type="success"
              showIcon
            />
          </div>
        ) : (
          <>
            <Radio.Group
              value={selected.packageType}
              onChange={(e) => setSelected(PACKAGES.find(p => p.packageType === e.target.value))}
            >
              <Space direction="vertical" style={{ width: '100%' }}>
                {PACKAGES.map(p => (
                  <Radio 
                    key={p.packageType} 
                    value={p.packageType}
                    style={{ width: '100%', padding: '8px' }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%' }}>
                      <div>
                        <strong>{p.name}</strong>
                        {p.tag && <span style={{ 
                          marginLeft: 8, 
                          padding: '2px 6px', 
                          background: '#ff4d4f', 
                          color: 'white', 
                          fontSize: '12px', 
                          borderRadius: '3px' 
                        }}>{p.tag}</span>}
                        <div style={{ fontSize: '12px', color: '#999', marginTop: '4px' }}>
                          {p.description}
                        </div>
                      </div>
                      <div style={{ fontSize: '16px', fontWeight: 'bold', color: '#ff4d4f', marginLeft: '16px' }}>
                        ￥{p.amount}
                      </div>
                    </div>
                  </Radio>
                ))}
              </Space>
            </Radio.Group>

            <Radio.Group value={channel} onChange={(e) => setChannel(e.target.value)}>
              <Radio.Button value="wechat">微信</Radio.Button>
              <Radio.Button value="alipay" disabled>支付宝（待开发）</Radio.Button>
            </Radio.Group>

            {!orderId && (
              <Button type="primary" onClick={onPay} loading={loading} block>
                去支付
              </Button>
            )}

            {orderId && payUrl && channel === 'wechat' && (
              <div style={{ textAlign: 'center' }}>
                {(() => {
                  const isAbsolute = payUrl.startsWith('weixin://') || payUrl.startsWith('http://') || payUrl.startsWith('https://');
                  const qrValue = isAbsolute ? payUrl : (window.location.origin + payUrl);
                  return <QRCode value={qrValue} size={200} />;
                })()}
                <div style={{ marginTop: 8 }}>请使用微信扫码支付</div>
              </div>
            )}

            {orderId && payUrl && channel === 'alipay' && (
              <Button type="primary" href={payUrl} target="_blank" block>
                前往支付宝支付
              </Button>
            )}
          </>
        )}
      </Space>
    </Modal>
  );
}


