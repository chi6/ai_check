import axios from 'axios';

// 创建axios实例
const api = axios.create({
  // 生产环境可通过环境变量覆盖，例如：REACT_APP_API_BASE_URL=https://vibe-checker.com/api
  baseURL: process.env.REACT_APP_API_BASE_URL || '/api',
  timeout: 50000, // 50秒超时
});

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    const path = (config.url || '').toString();
    const userToken = localStorage.getItem('token');
    const licenseToken = localStorage.getItem('licenseToken');
    // 针对用量/许可证接口使用licenseToken，其余接口沿用用户token
    if (path.startsWith('/usage') || path.startsWith('/license')) {
      if (licenseToken) {
        config.headers.Authorization = `Bearer ${licenseToken}`;
      }
    } else if (userToken) {
      config.headers.Authorization = `Bearer ${userToken}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// 响应拦截器
api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    // 不再跳转到 /login，交由调用方自行处理（例如弹窗或提示）
    return Promise.reject(error);
  }
);

// 用户相关API
export const userApi = {
  // 用户注册
  register: (userData) => api.post('/user/register', userData),
  
  // 用户登录
  login: (email, password) => api.post('/user/token', 
    new URLSearchParams({
      'username': email,
      'password': password,
    }),
    {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      }
    }
  ),
  
  // 获取当前用户信息
  getCurrentUser: () => api.get('/user/me'),
  
  // 获取用户任务列表
  getTasks: () => api.get('/user/tasks'),
  
  // 获取用户配额信息
  getCredits: () => api.get('/user/credits'),
};

// 文件上传相关API
export const uploadApi = {
  // 上传文件
  uploadFile: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    
    return api.post('/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });
  },
};

// 检测相关API
export const detectApi = {
  // 获取检测状态
  getDetectionStatus: (taskId) => {
    if (!taskId || typeof taskId !== 'string') {
      console.error('Invalid task ID for getDetectionStatus:', taskId);
      throw new Error('Invalid task ID');
    }
    return api.get(`/detect/${taskId}`);
  },
  
  // 开始检测
  startDetection: (taskId) => {
    if (!taskId || typeof taskId !== 'string') {
      console.error('Invalid task ID for startDetection:', taskId);
      throw new Error('Invalid task ID');
    }
    return api.post(`/detect/${taskId}/start`);
  },
  
  // 取消检测
  cancelDetection: (taskId) => {
    if (!taskId || typeof taskId !== 'string') {
      console.error('Invalid task ID for cancelDetection:', taskId);
      throw new Error('Invalid task ID');
    }
    return api.delete(`/detect/${taskId}/cancel`);
  },
};

// 报告相关API
export const reportApi = {
  // 获取JSON格式报告
  getJsonReport: (taskId) => api.get(`/report/${taskId}?format=json`),
  
  // 获取HTML格式报告(返回blob)
  getHtmlReport: (taskId, options = {}) => {
    const params = new URLSearchParams({
      format: 'html',
      ...options
    });
    return api.get(`/report/${taskId}?${params.toString()}`, {
      responseType: 'blob'
    });
  },
  
  // 获取纯文本格式报告(返回blob)
  getTextReport: (taskId, options = {}) => {
    const params = new URLSearchParams({
      format: 'text',
      ...options
    });
    return api.get(`/report/${taskId}?${params.toString()}`, {
      responseType: 'blob'
    });
  },
  
  // 注意: PDF格式功能已从后端移除
};

export default api; 

// 支付与配额相关API
export const payApi = {
  createOrder: ({ channel, packageType, deviceId, credits, amount }) =>
    api.post('/pay/create_order', { channel, packageType, deviceId, credits, amount }),
  poll: (orderId) => api.post('/pay/poll', { orderId }),
};

export const licenseApi = {
  get: () => api.get('/license'),
};

export const usageApi = {
  consume: (units, reason) => api.post('/usage/consume', { units, reason }),
};

export function setLicenseToken(token) {
  if (token && typeof token === 'string') {
    localStorage.setItem('licenseToken', token);
  }
}

export function getLicenseToken() {
  return localStorage.getItem('licenseToken');
}