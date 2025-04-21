import { message, notification } from 'antd';
import { 
  CheckCircleOutlined, 
  ExclamationCircleOutlined, 
  InfoCircleOutlined, 
  CloseCircleOutlined 
} from '@ant-design/icons';

// 注意：为避免 antd 的 message 静态方法警告，
// 应该在应用根组件中使用 message.App 组件包装整个应用

// 成功提示
export const showSuccess = (content, duration = 3) => {
  message.success({
    content,
    duration,
    style: {
      marginTop: '20px',
    },
  });
};

// 警告提示
export const showWarning = (content, duration = 3) => {
  message.warning({
    content,
    duration,
    style: {
      marginTop: '20px',
    },
  });
};

// 错误提示
export const showError = (content, duration = 4) => {
  message.error({
    content,
    duration,
    style: {
      marginTop: '20px',
    },
  });
};

// 信息提示
export const showInfo = (content, duration = 3) => {
  message.info({
    content,
    duration,
    style: {
      marginTop: '20px',
    },
  });
};

// 成功通知
export const notifySuccess = (message, description, duration = 4.5) => {
  notification.success({
    message,
    description,
    icon: <CheckCircleOutlined style={{ color: '#52c41a' }} />,
    duration,
    placement: 'topRight',
  });
};

// 错误通知
export const notifyError = (message, description, duration = 6) => {
  notification.error({
    message,
    description,
    icon: <CloseCircleOutlined style={{ color: '#ff4d4f' }} />,
    duration,
    placement: 'topRight',
  });
};

// 警告通知
export const notifyWarning = (message, description, duration = 4.5) => {
  notification.warning({
    message,
    description,
    icon: <ExclamationCircleOutlined style={{ color: '#faad14' }} />,
    duration,
    placement: 'topRight',
  });
};

// 信息通知
export const notifyInfo = (message, description, duration = 4.5) => {
  notification.info({
    message,
    description,
    icon: <InfoCircleOutlined style={{ color: '#1890ff' }} />,
    duration,
    placement: 'topRight',
  });
};

// 处理API错误
export const handleApiError = (error, fallbackMessage = '操作失败，请稍后重试') => {
  console.error('API错误:', error);
  
  let errorMsg = fallbackMessage;
  
  if (error.response) {
    // 服务器返回的错误信息
    if (error.response.data && error.response.data.detail) {
      errorMsg = error.response.data.detail;
    } else if (error.response.data && error.response.data.message) {
      errorMsg = error.response.data.message;
    } else if (error.response.status === 401) {
      errorMsg = '未授权，请重新登录';
    } else if (error.response.status === 403) {
      errorMsg = '权限不足，无法执行此操作';
    } else if (error.response.status === 404) {
      errorMsg = '请求的资源不存在';
    } else if (error.response.status === 500) {
      errorMsg = '服务器错误，请稍后重试';
    }
  } else if (error.request) {
    // 请求发送但没有收到响应
    errorMsg = '网络连接异常，请检查您的网络';
  } else {
    // 请求设置出错
    errorMsg = error.message || fallbackMessage;
  }
  
  showError(errorMsg);
  return errorMsg;
}; 