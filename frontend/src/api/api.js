import axios from 'axios';

// 创建axios实例
const api = axios.create({
  baseURL: '/api',  // 使用相对路径，这样会自动使用当前域名
  timeout: 50000, // 50秒超时
});

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// 响应拦截器
api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    // 处理401错误
    if (error.response && error.response.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
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
  
  // 获取用户使用情况
  getUsage: () => api.get('/user/usage'),
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

// 支付相关API
export const paymentApi = {
  // 获取所有订阅计划
  getPlans: () => api.get('/plans'),
  
  // 获取用户支付历史
  getPaymentHistory: () => api.get('/payments'),
  
  // 获取用户订阅
  getSubscriptions: () => api.get('/subscriptions'),
  
  // 获取特定计划的Stripe链接
  getPlanStripeLink: (planId) => api.get(`/plans/${planId}/stripe-link`),
  
  // 创建支付(购买计划)
  checkout: (planId, paymentMethod, paymentMethodId, returnUrl) => api.post('/checkout', {
    plan_id: planId,
    payment_method: paymentMethod,
    payment_method_id: paymentMethodId,
    return_url: returnUrl
  }),
  
  // 创建Stripe支付
  createStripePayment: (amount, currency, paymentMethodId, returnUrl) => api.post('/payments/stripe', {
    amount,
    currency,
    payment_method_id: paymentMethodId,
    return_url: returnUrl
  }),
  
  // 创建Stripe Checkout会话
  createStripeCheckout: (planId, successUrl, cancelUrl) => api.post('/payments/stripe/create-checkout', {
    plan_id: planId,
    success_url: successUrl,
    cancel_url: cancelUrl
  }),
  
  // 确认Stripe支付
  confirmStripePayment: (paymentId, paymentIntentId) => api.post(`/payments/stripe/${paymentId}/confirm`, {
    payment_intent_id: paymentIntentId
  }),

  // 获取支付状态
  getPaymentStatus: (paymentId) => api.get(`/payments/${paymentId}`),
  
  // 取消订阅
  cancelSubscription: (subscriptionId) => api.delete(`/subscriptions/${subscriptionId}`),
  
  // 支付宝公钥
  alipayPublicKey: 'MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAsex7bh615RWPLRxpbyZ8oo86ay/D0ZtB1NEBWG4MGpP7wPXTcl0435z1zxQzmpMhpKIw/F0r/4E4y77q348wAF7ED0jxfLChTwiSare1HiTJ1/kSX0nqOooRJr4hSnJyoGQVPjiKoP5H4salW8/lECtgEXl62kMfS4vUIivASTHuiHoT+uBmFdyJXo24KJ4ea80vB3ns7QGmQimIHzykICJg2iJj5sbBjpomHZVBAIgot51ScK376zr8951dIdxuQcx4jQTdEJUeAzRBKpDmiYEcLMDY35ykKYcz2X6qsmU2o/Rq77VT9VTkWTioqPqKed1conxtcSumhIikpMsRyQIDAQAB',
};

export default api; 