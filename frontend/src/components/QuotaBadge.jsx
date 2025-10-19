import React, { useEffect, useState, useImperativeHandle, forwardRef } from 'react';
import { Button, Space, Tag } from 'antd';
import { WalletOutlined } from '@ant-design/icons';
import { userApi } from '../api/api';

const QuotaBadge = forwardRef(({ onTopup }, ref) => {
  const [remaining, setRemaining] = useState(0);
  const [loading, setLoading] = useState(true);

  const refresh = async () => {
    setLoading(true);
    try {
      const res = await userApi.getCredits();
      setRemaining(res.totalCredits || 0);
    } catch (e) {
      console.error('获取配额失败:', e);
      setRemaining(0);
    } finally {
      setLoading(false);
    }
  };

  // 暴露 refresh 方法给父组件
  useImperativeHandle(ref, () => ({
    refresh
  }));

  useEffect(() => {
    refresh();
  }, []);

  const danger = remaining <= 0;
  const warning = remaining > 0 && remaining <= 10;
  
  // 决定Tag的颜色
  let color = 'green';
  if (danger) color = 'red';
  else if (warning) color = 'orange';
  
  return (
    <Space size="small">
      <Tag 
        icon={<WalletOutlined />} 
        color={color}
        style={{ 
          fontSize: '14px', 
          padding: '4px 12px',
          margin: 0,
          fontWeight: 500
        }}
      >
        {loading ? '加载中...' : `${remaining} 次`}
      </Tag>
      <Button 
        size="small" 
        onClick={onTopup} 
        type={danger ? 'primary' : 'default'} 
        danger={danger}
      >
        充值
      </Button>
    </Space>
  );
});

QuotaBadge.displayName = 'QuotaBadge';

export default QuotaBadge;


