import React, { useState, useEffect } from 'react';
import { Form, Input, Select, Button, Radio, Card, message, Spin, Tabs, Row, Col, Typography, Tag, Alert, Space } from 'antd';
import { CreditCardOutlined, WechatOutlined, AlipayOutlined, SafetyCertificateOutlined, CalendarOutlined, LinkOutlined } from '@ant-design/icons';
import { paymentApi } from '../../api/api';

const { Option } = Select;
const { Title, Text, Paragraph } = Typography;
const { TabPane } = Tabs;

const PaymentForm = ({ onSuccess }) => {
  const [form] = Form.useForm();
  const [paymentMethod, setPaymentMethod] = useState('stripe');
  const [loading, setLoading] = useState(false);
  const [qrCodeUrl, setQrCodeUrl] = useState('');
  const [plans, setPlans] = useState([]);
  const [selectedPlan, setSelectedPlan] = useState(null);
  const [plansLoading, setPlansLoading] = useState(true);
  const [stripeLink, setStripeLink] = useState('');
  const [error, setError] = useState('');
  const [availablePlans, setAvailablePlans] = useState([]);
  const [officialPlans, setOfficialPlans] = useState([]);

  // 获取订阅计划
  useEffect(() => {
    const fetchAvailablePlans = async () => {
      setPlansLoading(true);
      try {
        // 尝试从API获取计划
        let plansData = [];
        try {
          const response = await paymentApi.getPlans();
          plansData = response.data || [];
          console.log('从API获取的计划:', plansData);
        } catch (apiError) {
          console.error('获取计划失败，使用预设数据:', apiError);
          // 使用预设数据
          plansData = [];
        }
        
        // 设置API获取的计划为可用计划
        setAvailablePlans(plansData);
        
        // 设置正式订阅计划
        setOfficialPlans([
          {
            id: 'single_use_official',
            name: '单次使用',
            description: '充值1美元获取1次检测机会',
            plan_type: 'single_use',
            price: 1.0,
            currency: 'USD',
            duration_days: 0,
            is_active: true,
            stripe_link: 'https://buy.stripe.com/bIYcPz53W8aM0JaaEF',
            usage_credits: 1
          },
          {
            id: 'ten_use_official',
            name: '十次使用',
            description: '充值5美元获取10次检测机会',
            plan_type: 'single_use',
            price: 5.0,
            currency: 'USD',
            duration_days: 0,
            is_active: true,
            stripe_link: 'https://buy.stripe.com/eVabLv2VO62EbnO5kk',
            usage_credits: 10
          },
          {
            id: 'hundred_use_official',
            name: '百次使用',
            description: '充值10美元获取100次检测机会',
            plan_type: 'single_use',
            price: 10.0,
            currency: 'USD',
            duration_days: 0,
            is_active: true,
            stripe_link: 'https://buy.stripe.com/4gw8zjdAsdv63VmcMO',
            usage_credits: 100
          }
        ]);
      } catch (error) {
        console.error('获取订阅计划失败:', error);
      } finally {
        setPlansLoading(false);
      }
    };

    fetchAvailablePlans();
  }, []);

  // 处理支付方式变更
  const handlePaymentMethodChange = (e) => {
    setPaymentMethod(e.target.value);
  };

  // 处理计划选择
  const handlePlanSelect = async (plan) => {
    console.log('选择计划(完整对象):', JSON.stringify(plan, null, 2));
    console.log('选择计划:', plan.name);
    console.log('计划ID:', plan.id);
    console.log('计划类型:', plan.plan_type);
    console.log('使用次数:', plan.usage_credits, '类型:', typeof plan.usage_credits);
    console.log('是否10次计划:', plan.name.includes('10') || plan.name.includes('十次') || (plan.usage_credits && Number(plan.usage_credits) === 10));
    
    setSelectedPlan(plan);
    form.setFieldsValue({
      amount: plan.price,
      currency: plan.currency,
      description: plan.description || plan.name
    });
    
    // 手动设置链接 - 直接使用硬编码链接而不是计算
    let directLink;
    if (plan.name.includes('10') || plan.name.includes('十次') || (plan.usage_credits && Number(plan.usage_credits) === 10)) {
      directLink = 'https://buy.stripe.com/eVabLv2VO62EbnO5kk'; // 5美元10次链接
      console.log('检测到10次使用计划，直接设置链接为:', directLink);
    } else if (plan.plan_type === 'daily') {
      directLink = 'https://buy.stripe.com/4gw8zjdAsdv63VmcMO'; // 日套餐
      console.log('检测到日套餐计划，直接设置链接为:', directLink);
    } else {
      directLink = 'https://buy.stripe.com/bIYcPz53W8aM0JaaEF'; // 单次使用
      console.log('默认使用单次使用链接:', directLink);
    }
    
    // 直接设置链接
    setStripeLink(directLink);
    console.log('设置的最终链接:', directLink);
    
    // 如果计划中有stripe_link，记录到控制台
    if (plan.stripe_link) {
      console.log('计划中存在链接(仅记录不使用):', plan.stripe_link);
    }
    
    // 不再尝试从API获取
  };

  // 获取Stripe支付链接
  const getStripePaymentLink = (planType, usageCredits) => {
    console.log('DEBUG - 获取支付链接:', planType, usageCredits, typeof usageCredits, 'plan:', selectedPlan?.name);
    
    // 添加直接调试输出，显示使用的链接
    const TEN_TIMES_LINK = 'https://buy.stripe.com/eVabLv2VO62EbnO5kk'; // 十次使用 - 5美元
    const ONE_TIME_LINK = 'https://buy.stripe.com/bIYcPz53W8aM0JaaEF'; // 单次使用 - 1美元
    const HUNDRED_TIMES_LINK = 'https://buy.stripe.com/4gw8zjdAsdv63VmcMO'; // 百次使用 - 10美元
    
    // 如果是单次使用计划，检查多种可能的值
    if (planType === 'single_use') {
      // 使用多种检测方式确保能识别计划
      if (usageCredits) {
        const creditsNum = Number(usageCredits);
        // 直接检查计划名称中是否包含特定字符
        const planName = selectedPlan?.name || '';
        
        console.log('计划名称:', planName);
        console.log('使用次数转换为数字:', creditsNum);
        
        // 检查是否是100次使用计划
        if (creditsNum === 100 || 
            planName.includes('100') || 
            planName.includes('百次')) {
          console.log('DEBUG - 检测到100次使用计划，返回链接:', HUNDRED_TIMES_LINK);
          return HUNDRED_TIMES_LINK;
        } 
        // 检查是否是10次使用计划
        else if (creditsNum === 10 || 
            planName.includes('10') || 
            planName.includes('十次')) {
          console.log('DEBUG - 检测到10次使用计划，返回链接:', TEN_TIMES_LINK);
          return TEN_TIMES_LINK;
        }
      }
      
      console.log('DEBUG - 返回单次使用链接:', ONE_TIME_LINK);
      return ONE_TIME_LINK;
    }
    
    console.log('DEBUG - 未匹配任何计划类型，返回默认链接:', ONE_TIME_LINK);
    return ONE_TIME_LINK; // 默认使用单次使用链接
  };

  // 提交表单
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!selectedPlan) {
      setError('请选择一个订阅计划');
      return;
    }
    
    // 添加调试日志
    console.log('提交支付表单，选中计划:', selectedPlan);
    
    // 设置加载状态
    setLoading(true);
    setError('');
    
    try {
      // 获取当前域名作为回调URL基础
      const baseUrl = window.location.origin;
      
      // 设置成功和取消URL
      const successUrl = `${baseUrl}/payment/status?success=true&plan_id=${selectedPlan.id}`;
      const cancelUrl = `${baseUrl}/payment/status?canceled=true`;
      
      console.log('发送创建Checkout会话请求，plan_id:', selectedPlan.id);
      console.log('成功回调URL:', successUrl);
      console.log('取消回调URL:', cancelUrl);
      
      // 通过API创建Checkout会话
      const result = await paymentApi.createStripeCheckout(
        selectedPlan.id, 
        successUrl, 
        cancelUrl
      );
      
      if (result && result.checkout_url) {
        console.log('创建Checkout会话成功，重定向到:', result.checkout_url);
        // 重定向到Checkout页面
        window.location.href = result.checkout_url;
      } else {
        throw new Error('创建Checkout会话失败：没有返回有效URL');
      }
    } catch (error) {
      console.error('创建Checkout会话失败:', error);
      let errorMsg = '请稍后再试';
      
      // 尝试从响应中获取更详细的错误信息
      if (error.response && error.response.data) {
        const responseData = error.response.data;
        if (responseData.detail) {
          errorMsg = responseData.detail;
        }
      } else if (error.message) {
        errorMsg = error.message;
      }
      
      setError(`支付初始化失败: ${errorMsg}`);
      message.error(`支付初始化失败: ${errorMsg}`);
    } finally {
      setLoading(false);
    }
  };

  // 渲染订阅计划卡片
  const renderPlanCard = (plan, isOfficial = false) => {
    const isSelected = selectedPlan && selectedPlan.id === plan.id;
    
    return (
      <div 
        key={plan.id}
        className={`plan-card ${isSelected ? 'selected-plan' : ''} ${isOfficial ? 'official-plan' : ''}`}
        onClick={() => handlePlanSelect(plan)}
      >
        <h4>{plan.name}</h4>
        <div className="price">
          <span className="currency">{plan.currency === 'USD' ? '$' : plan.currency}</span>
          <span className="amount">{plan.price}</span>
        </div>
        <p className="description">{plan.description}</p>
        <div className="plan-details">
          {plan.plan_type === 'single_use' && plan.usage_credits && (
            <p className="usage-credits">包含 {plan.usage_credits} 次检测</p>
          )}
          {plan.plan_type === 'daily' && (
            <p className="daily-plan">每日无限制使用</p>
          )}
        </div>
        {isSelected && (
          <div className="selected-marker">已选择</div>
        )}
      </div>
    );
  };

  // 添加一个调试信息组件
  const renderDebugInfo = () => {
    return (
      <div className="debug-info" style={{ 
        padding: '10px', 
        margin: '10px 0', 
        border: '1px dashed #ccc',
        background: '#f9f9f9',
        fontSize: '12px',
        fontFamily: 'monospace'
      }}>
        <h4>调试信息</h4>
        <div>
          <h5>可用计划：</h5>
          <pre>{JSON.stringify(availablePlans, null, 2)}</pre>
        </div>
        <div>
          <h5>正式计划：</h5>
          <pre>{JSON.stringify(officialPlans, null, 2)}</pre>
        </div>
        <div>
          <h5>当前选中计划：</h5>
          <pre>{JSON.stringify(selectedPlan, null, 2)}</pre>
        </div>
      </div>
    );
  };

  // 设置一个调试模式标志
  const debug = false; // 设置为true时显示调试信息

  // 添加基本的CSS样式
  const styles = `
    .payment-form-container {
      max-width: 100%;
      margin: 0 auto;
      padding: 20px;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    }
    
    .payment-form-container h2 {
      font-size: 24px;
      margin-bottom: 20px;
      text-align: center;
    }
    
    .payment-form {
      display: flex;
      flex-direction: column;
      gap: 20px;
    }
    
    .payment-plans {
      display: flex;
      flex-direction: column;
      gap: 30px;
    }
    
    .plans-section h3, .official-plans-section h3 {
      font-size: 18px;
      margin-bottom: 15px;
    }
    
    .plan-cards {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
      gap: 15px;
    }
    
    .plan-card {
      border: 1px solid #e8e8e8;
      border-radius: 8px;
      padding: 15px;
      transition: all 0.3s ease;
      cursor: pointer;
      position: relative;
      overflow: hidden;
    }
    
    .plan-card:hover {
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    }
    
    .plan-card.selected-plan {
      border-color: #1890ff;
      background-color: rgba(24, 144, 255, 0.05);
    }
    
    .plan-card.official-plan {
      border-style: solid;
      opacity: 1;
    }
    
    .plan-card h4 {
      margin-top: 0;
      font-size: 18px;
      margin-bottom: 10px;
    }
    
    .plan-card .price {
      font-size: 22px;
      font-weight: bold;
      margin: 10px 0;
      color: #1890ff;
    }
    
    .plan-card .price .currency {
      font-size: 16px;
      margin-right: 2px;
    }
    
    .plan-card .description {
      margin-bottom: 10px;
      color: #666;
    }
    
    .plan-card .plan-details {
      margin-top: 10px;
    }
    
    .plan-card .plan-details p {
      margin: 5px 0;
      font-size: 14px;
      color: #333;
    }
    
    .plan-card .selected-marker {
      position: absolute;
      top: 0;
      right: 0;
      background-color: #1890ff;
      color: white;
      padding: 5px 10px;
      font-size: 12px;
      transform: translate(30%, -30%) rotate(45deg);
      transform-origin: bottom left;
      width: 100px;
      text-align: center;
      box-shadow: 0 1px 4px rgba(0, 0, 0, 0.2);
    }
    
    .submit-section {
      margin-top: 20px;
      text-align: center;
    }
    
    .payment-submit-button {
      background-color: #1890ff;
      color: white;
      border: none;
      padding: 10px 20px;
      font-size: 16px;
      border-radius: 4px;
      cursor: pointer;
      transition: background-color 0.3s;
      min-width: 200px;
    }
    
    .payment-submit-button:hover {
      background-color: #40a9ff;
    }
    
    .payment-submit-button:disabled {
      background-color: #d9d9d9;
      cursor: not-allowed;
    }
    
    .error-message {
      color: #ff4d4f;
      padding: 10px;
      margin-bottom: 15px;
      background-color: #fff2f0;
      border: 1px solid #ffccc7;
      border-radius: 4px;
    }
    
    .loading-plans {
      padding: 20px;
      text-align: center;
      color: #666;
    }
    
    .qr-code-section {
      margin-top: 30px;
      text-align: center;
    }
    
    .qr-code-section h3 {
      margin-bottom: 15px;
    }
    
    .qr-code-section img {
      max-width: 200px;
      border: 1px solid #e8e8e8;
      padding: 10px;
      border-radius: 4px;
    }
    
    .usage-credits {
      color: #1890ff !important;
      font-weight: bold;
    }
    
    .daily-plan {
      color: #52c41a !important;
      font-weight: bold;
    }
  `;

  return (
    <div className="payment-form-container">
      <style>{styles}</style>
      {error && <div className="error-message">{error}</div>}

      <form onSubmit={handleSubmit} className="payment-form">
        <div className="payment-plans">
          <div className="official-plans-section">
            <h3>正式订阅计划</h3>
            <div className="plan-cards">
              {officialPlans.map(plan => renderPlanCard(plan, true))}
            </div>
          </div>
        </div>

        <div className="submit-section">
          <button 
            type="submit" 
            className="payment-submit-button"
            disabled={!selectedPlan || loading}
          >
            {loading ? '处理中...' : '现在订阅'}
          </button>
        </div>
      </form>
      
      {qrCodeUrl && (
        <div className="qr-code-section">
          <h3>扫描二维码进行支付</h3>
          <img src={qrCodeUrl} alt="支付二维码" />
        </div>
      )}

      {debug && renderDebugInfo()}
    </div>
  );
};

export default PaymentForm; 