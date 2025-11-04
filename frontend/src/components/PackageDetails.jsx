import React from 'react';
import { Card, Tag, Badge, Space, Empty, Typography } from 'antd';
import { 
  FireOutlined, 
  ClockCircleOutlined, 
  CheckCircleOutlined,
  ThunderboltOutlined,
  TrophyOutlined
} from '@ant-design/icons';

const { Text } = Typography;

// 套餐类型映射
const PACKAGE_TYPE_MAP = {
  'detect_once': {
    name: '1次查重',
    icon: <CheckCircleOutlined />,
    color: 'blue'
  },
  'ai_single_check': {
    name: '1次AI智能查重',
    icon: <ThunderboltOutlined />,
    color: 'green'
  },
  'ai_detect_once': {
    name: '1次AI深度查询+查重',
    icon: <ThunderboltOutlined />,
    color: 'purple'
  },
  'unlimited_1day': {
    name: '1天不限次',
    icon: <FireOutlined />,
    color: 'gold'
  },
  'unlimited_1week': {
    name: '1周不限次',
    icon: <FireOutlined />,
    color: 'red'
  }
};

const PackageDetails = ({ licenses }) => {
  if (!licenses || licenses.length === 0) {
    return (
      <Empty 
        image={Empty.PRESENTED_IMAGE_SIMPLE}
        description="暂无有效套餐"
        style={{ padding: '40px 0' }}
      />
    );
  }

  // 格式化到期时间
  const formatExpireTime = (isoString) => {
    if (!isoString) return null;
    const date = new Date(isoString);
    const now = new Date();
    const diffMs = date - now;
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffHours / 24);
    
    if (diffDays > 0) {
      return {
        text: `${diffDays}天后到期`,
        status: diffDays > 7 ? 'success' : (diffDays > 1 ? 'warning' : 'error')
      };
    } else if (diffHours > 0) {
      return {
        text: `${diffHours}小时后到期`,
        status: 'error'
      };
    } else {
      return {
        text: '即将到期',
        status: 'error'
      };
    }
  };

  return (
    <div style={{ marginTop: 16 }}>
      <Text strong style={{ fontSize: '14px', marginBottom: 12, display: 'block' }}>
        <TrophyOutlined style={{ marginRight: 8 }} />
        我的套餐详情
      </Text>
      <Space direction="vertical" style={{ width: '100%' }} size="small">
        {licenses.map((license, index) => {
          const packageInfo = PACKAGE_TYPE_MAP[license.packageType] || {
            name: '未知套餐',
            icon: <CheckCircleOutlined />,
            color: 'default'
          };
          
          const expireInfo = license.exp ? formatExpireTime(license.exp) : null;
          const isUnlimited = license.unlimited;

          return (
            <Badge.Ribbon 
              key={license.id} 
              text={isUnlimited ? '不限次数' : null}
              color={isUnlimited ? 'gold' : null}
            >
              <Card 
                size="small" 
                style={{ 
                  borderLeft: `3px solid ${
                    isUnlimited ? '#faad14' : 
                    license.creditsRemaining > 5 ? '#52c41a' : 
                    license.creditsRemaining > 0 ? '#fa8c16' : '#ff4d4f'
                  }`
                }}
              >
                <Space direction="vertical" style={{ width: '100%' }} size="small">
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Space>
                      <span style={{ color: packageInfo.color, fontSize: '16px' }}>
                        {packageInfo.icon}
                      </span>
                      <Text strong>{packageInfo.name}</Text>
                      {license.packageType && (
                        <Tag color={packageInfo.color} style={{ margin: 0 }}>
                          {packageInfo.name}
                        </Tag>
                      )}
                    </Space>
                    <div style={{ textAlign: 'right' }}>
                      {isUnlimited ? (
                        <Tag icon={<FireOutlined />} color="gold">
                          无限次数
                        </Tag>
                      ) : (
                        <Text strong style={{ 
                          fontSize: '16px',
                          color: license.creditsRemaining > 5 ? '#52c41a' : 
                                 license.creditsRemaining > 0 ? '#fa8c16' : '#ff4d4f'
                        }}>
                          {license.creditsRemaining} 次
                        </Text>
                      )}
                    </div>
                  </div>
                  
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px' }}>
                    <Text type="secondary">
                      <ClockCircleOutlined style={{ marginRight: 4 }} />
                      {expireInfo ? (
                        <span style={{ 
                          color: expireInfo.status === 'success' ? '#52c41a' :
                                 expireInfo.status === 'warning' ? '#fa8c16' : '#ff4d4f'
                        }}>
                          {expireInfo.text}
                        </span>
                      ) : (
                        '永久有效'
                      )}
                    </Text>
                    {license.createdAt && (
                      <Text type="secondary">
                        购买于: {new Date(license.createdAt).toLocaleDateString('zh-CN')}
                      </Text>
                    )}
                  </div>
                </Space>
              </Card>
            </Badge.Ribbon>
          );
        })}
      </Space>
    </div>
  );
};

export default PackageDetails;

