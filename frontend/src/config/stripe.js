// Stripe配置
export const STRIPE_CONFIG = {
  // Stripe Publishable Key (前端使用)
  publishableKey: 'pk_live_51RKWOaKXvLtctMCt32h7z0v9UF6oK3QtL12fn3He1eeTsZjD7u3waOkDlgXx7uKXa9YcHF7cmoZV5GDqBKYE4gjT00DSpU6hW5',
  
  // Stripe配置选项
  options: {
    // 设置支持的支付方式
    paymentMethods: ['card'],
    
    // 设置外观主题
    appearance: {
      theme: 'stripe',
      variables: {
        colorPrimary: '#1890ff',
        colorBackground: '#ffffff',
        colorText: '#424770',
        colorDanger: '#df1b41',
        fontFamily: 'Ideal Sans, system-ui, sans-serif',
        spacingUnit: '2px',
        borderRadius: '4px',
      }
    },
    
    // 设置支持的货币
    currency: 'usd',
    
    // 设置地区
    locale: 'zh-CN'
  }
};

// 验证Stripe配置
export const validateStripeConfig = () => {
  if (!STRIPE_CONFIG.publishableKey) {
    console.error('Stripe publishable key 未配置');
    return false;
  }
  
  if (!STRIPE_CONFIG.publishableKey.startsWith('pk_')) {
    console.error('Stripe publishable key 格式错误');
    return false;
  }
  
  return true;
};

// 获取Stripe实例
let stripeInstance = null;

export const getStripeInstance = async () => {
  if (!validateStripeConfig()) {
    throw new Error('Stripe配置无效');
  }
  
  if (!stripeInstance) {
    try {
      // 动态导入Stripe
      const { loadStripe } = await import('@stripe/stripe-js');
      stripeInstance = await loadStripe(STRIPE_CONFIG.publishableKey);
      
      if (!stripeInstance) {
        throw new Error('无法加载Stripe');
      }
      
      console.log('Stripe实例创建成功');
    } catch (error) {
      console.error('创建Stripe实例失败:', error);
      throw error;
    }
  }
  
  return stripeInstance;
};

// 重置Stripe实例（用于测试或配置更改）
export const resetStripeInstance = () => {
  stripeInstance = null;
};

export default STRIPE_CONFIG; 