# 支付系统实现文档

本文档详细描述了AI论文检测系统中支付功能的实现和使用方法。

## 支持的支付方式

系统目前支持以下三种支付方式：

1. **Stripe支付**：适用于国际用户，支持信用卡支付
2. **微信支付**：适用于中国大陆用户，支持扫码支付
3. **支付宝**：适用于中国大陆用户，支持网页和移动端支付

## 系统架构

支付系统采用模块化设计，主要包括以下组件：

1. **支付服务模块**（`payment_service.py`）：处理各种支付方式的具体实现
2. **API路由**（`user.py`中的支付相关路由）：提供支付相关的HTTP接口
3. **数据模型**：定义支付和订阅相关的数据结构
4. **前端集成**：提供用户友好的支付界面

## 配置说明

系统需要在`.env`文件中配置以下支付相关的环境变量：

```
# Stripe支付配置
STRIPE_API_KEY=your_stripe_api_key
STRIPE_WEBHOOK_SECRET=your_stripe_webhook_secret

# 微信支付配置
WECHAT_PAY_APPID=your_wechat_pay_appid
WECHAT_PAY_MCH_ID=your_wechat_pay_mch_id
WECHAT_PAY_API_KEY=your_wechat_pay_api_key
WECHAT_PAY_NOTIFY_URL=https://your-domain.com/api/payments/wechat/notify

# 支付宝配置
ALIPAY_APPID=your_alipay_appid
ALIPAY_PRIVATE_KEY=your_alipay_private_key
ALIPAY_PUBLIC_KEY=your_alipay_public_key
ALIPAY_NOTIFY_URL=https://your-domain.com/api/payments/alipay/notify
```

请确保这些配置保密且正确设置。

## API接口说明

### Stripe支付

#### 创建Stripe支付

```
POST /api/payments/stripe
```

**请求参数**：
```json
{
  "amount": 99.99,
  "currency": "usd",
  "payment_method_id": "pm_card_visa",
  "return_url": "http://localhost:3000/payment/result"
}
```

**响应**：
```json
{
  "payment_id": "9f7c5e7a-8b3d-4f1a-9e6d-1a2b3c4d5e6f",
  "status": "requires_action",
  "client_secret": "pi_3NjqxvAAuYT8V1Rg1h2j3k4l_secret_5m6n7o8p9q0r",
  "next_action": {}
}
```

#### 确认Stripe支付

```
POST /api/payments/stripe/{payment_id}/confirm
```

**请求参数**：
```json
{
  "payment_intent_id": "pi_3NjqxvAAuYT8V1Rg1h2j3k4l"
}
```

**响应**：
```json
{
  "status": "completed"
}
```

### 微信支付

#### 创建微信支付

```
POST /api/payments/wechat
```

**请求参数**：
```json
{
  "amount": 99.99,
  "product_description": "AI论文检测高级会员"
}
```

**响应**：
```json
{
  "payment_id": "9f7c5e7a-8b3d-4f1a-9e6d-1a2b3c4d5e6f",
  "status": "pending",
  "wechat_trade_no": "wx_1637829536_9f7c5e7a",
  "qr_code_url": "weixin://wxpay/bizpayurl?pr=xhd8976tre"
}
```

#### 微信支付通知处理

```
POST /api/payments/wechat/notify
```

此接口由微信支付服务器调用，用于通知支付结果。

### 支付宝支付

#### 创建支付宝支付

```
POST /api/payments/alipay
```

**请求参数**：
```json
{
  "amount": 99.99,
  "product_description": "AI论文检测高级会员",
  "return_url": "http://localhost:3000/payment/result"
}
```

**响应**：
```json
{
  "payment_id": "9f7c5e7a-8b3d-4f1a-9e6d-1a2b3c4d5e6f",
  "status": "pending",
  "alipay_trade_no": "ali_1637829536_9f7c5e7a",
  "pay_url": "https://openapi.alipay.com/gateway.do?..."
}
```

#### 支付宝支付通知处理

```
POST /api/payments/alipay/notify
```

此接口由支付宝服务器调用，用于通知支付结果。

### 订阅管理

#### 创建订阅

```
POST /api/subscriptions
```

**请求参数**：
```json
{
  "plan_id": "premium_monthly",
  "payment_method": "stripe",
  "payment_method_id": "pm_card_visa"
}
```

**响应**：
```json
{
  "subscription_id": "9f7c5e7a-8b3d-4f1a-9e6d-1a2b3c4d5e6f",
  "status": "active",
  "current_period_end": "2023-12-31T23:59:59Z"
}
```

#### 取消订阅

```
DELETE /api/subscriptions/{subscription_id}
```

**响应**：
```json
{
  "status": "canceled",
  "message": "订阅已成功取消"
}
```

#### 获取用户支付记录

```
GET /api/payments
```

**响应**：
```json
[
  {
    "id": "9f7c5e7a-8b3d-4f1a-9e6d-1a2b3c4d5e6f",
    "amount": 99.99,
    "currency": "usd",
    "status": "completed",
    "created_at": "2023-11-25T10:30:00Z",
    "payment_method": "stripe",
    "stripe_payment_id": "pi_3NjqxvAAuYT8V1Rg1h2j3k4l"
  }
]
```

#### 获取用户订阅记录

```
GET /api/subscriptions
```

**响应**：
```json
[
  {
    "id": "9f7c5e7a-8b3d-4f1a-9e6d-1a2b3c4d5e6f",
    "plan_id": "premium_monthly",
    "status": "active",
    "current_period_end": "2023-12-31T23:59:59Z",
    "created_at": "2023-11-25T10:30:00Z",
    "updated_at": "2023-11-25T10:30:00Z",
    "payment_method": "stripe",
    "stripe_subscription_id": "sub_3NjqxvAAuYT8V1Rg1h2j3k4l"
  }
]
```

## 前端集成指南

### Stripe支付集成

1. 引入Stripe.js库
2. 使用Elements组件收集支付信息
3. 调用后端API创建支付
4. 处理支付确认和结果

```javascript
// Stripe支付示例
import { loadStripe } from '@stripe/stripe-js';
const stripePromise = loadStripe('pk_test_yourpublickey');

async function handleStripePayment() {
  const stripe = await stripePromise;
  
  // 调用后端API创建支付
  const response = await fetch('/api/payments/stripe', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      amount: 99.99,
      currency: 'usd',
      payment_method_id: 'pm_card_visa',
      return_url: window.location.origin + '/payment/result'
    })
  });
  
  const data = await response.json();
  
  // 处理支付确认
  if (data.status === 'requires_action') {
    const { error } = await stripe.confirmCardPayment(data.client_secret);
    if (error) {
      console.error('支付失败', error);
    } else {
      console.log('支付成功');
    }
  }
}
```

### 微信支付集成

1. 调用后端API创建支付
2. 展示二维码让用户扫码
3. 轮询支付状态或等待跳转

```javascript
// 微信支付示例
async function handleWechatPayment() {
  // 调用后端API创建支付
  const response = await fetch('/api/payments/wechat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      amount: 99.99,
      product_description: 'AI论文检测高级会员'
    })
  });
  
  const data = await response.json();
  
  // 展示二维码
  displayQRCode(data.qr_code_url);
  
  // 轮询支付状态
  checkPaymentStatus(data.payment_id);
}
```

### 支付宝支付集成

1. 调用后端API创建支付
2. 重定向用户到支付宝支付页面
3. 处理支付结果回调

```javascript
// 支付宝支付示例
async function handleAlipayPayment() {
  // 调用后端API创建支付
  const response = await fetch('/api/payments/alipay', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      amount: 99.99,
      product_description: 'AI论文检测高级会员',
      return_url: window.location.origin + '/payment/result'
    })
  });
  
  const data = await response.json();
  
  // 重定向到支付宝支付页面
  window.location.href = data.pay_url;
}
```

## 测试方法

### Stripe测试卡号

- Visa: 4242 4242 4242 4242
- Mastercard: 5555 5555 5555 4444
- 任意有效的过期日期和CVV

### 微信支付和支付宝测试

请参考各自的开发文档进行测试。

## 故障排除

1. **支付创建失败**：检查API密钥和配置是否正确
2. **支付确认失败**：检查客户端代码和后端通信
3. **通知处理失败**：确保通知URL可公网访问并正确配置

## 安全考虑

1. 所有支付相关的API应使用HTTPS
2. 用户敏感信息不应在前端存储
3. 验证所有支付通知的签名
4. 使用适当的错误处理避免信息泄露 