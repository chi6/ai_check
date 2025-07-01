# Stripe 支付配置指南

## 配置密钥

### 后端环境变量配置

在 `backend/.env` 文件中添加以下配置：

```bash
# Stripe API密钥（后端使用）
STRIPE_API_KEY=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

# Stripe Webhook签名密钥
STRIPE_WEBHOOK_SECRET=whsec_QL0K8i1CqYd32xVbOtgesSUs65cltl22

# 其他必要配置
DATABASE_URL=sqlite:///./app.db
SECRET_KEY=your_production_secret_key_here
AI_DETECTION_API_KEY=your_api_key_here
AI_DETECTION_API_ENDPOINT=https://api.example.com/detect
```

### 前端配置

前端Stripe Publishable Key已配置在 `frontend/src/config/stripe.js`:

```javascript
publishableKey: 'pk_live_51RKWOaKXvLtctMCt32h7z0v9UF6oK3QtL12fn3He1eeTsZjD7u3waOkDlgXx7uKXa9YcHF7cmoZV5GDqBKYE4gjT00DSpU6hW5'
```

## Webhook配置

### 1. Stripe控制台配置

1. 登录Stripe控制台
2. 导航到"开发者" → "Webhooks"
3. 点击"添加端点"
4. 设置端点URL：`https://你的域名:8000/api/payments/stripe/webhook`
5. 选择要监听的事件：
   - `payment_intent.succeeded`
   - `payment_intent.payment_failed`
   - `checkout.session.completed`
   - `invoice.paid`
   - `customer.subscription.deleted`

### 2. 获取Webhook签名密钥

配置完Webhook后，从Stripe控制台复制"签名密钥"，并将其设置为环境变量 `STRIPE_WEBHOOK_SECRET`。

## 支付流程

### 1. 支付成功流程

```
用户选择计划 → 创建Checkout会话 → 重定向到Stripe → 用户完成支付 
→ Stripe发送Webhook → 后端处理Webhook → 更新用户账户 → 显示成功页面
```

### 2. 日志记录

系统会记录详细的支付日志：

- 支付创建
- 支付成功/失败
- Webhook事件处理
- 用户账户更新

查看日志：
```bash
# 后端日志
tail -f backend/app.log

# 实时日志（如果使用PM2）
pm2 logs
```

### 3. 支付状态页面

用户完成支付后会重定向到：
- 成功：`/payment/status?success=true&session_id=xxx`
- 取消：`/payment/status?canceled=true`
- 失败：`/payment/status?success=false&error=xxx`

## 测试

### 1. 测试卡号

Stripe提供测试卡号用于开发测试：

- 成功支付：`4242 4242 4242 4242`
- 需要验证：`4000 0027 6000 3184`
- 支付失败：`4000 0000 0000 0002`

### 2. 测试Webhook

使用Stripe CLI测试Webhook：

```bash
# 安装Stripe CLI
stripe listen --forward-to localhost:8000/api/payments/stripe/webhook

# 触发测试事件
stripe trigger payment_intent.succeeded
```

## 故障排除

### 1. 常见问题

- **Webhook签名验证失败**：检查 `STRIPE_WEBHOOK_SECRET` 是否正确
- **支付状态不更新**：检查Webhook端点是否可访问
- **用户余额未增加**：检查 `process_successful_payment` 函数日志

### 2. 调试信息

开发环境下，支付状态页面会显示调试信息，包括：
- URL参数
- 支付状态
- 支付详情

### 3. 日志级别

系统使用Python logging记录详细信息：
- `INFO`：正常操作
- `WARNING`：支付失败等警告
- `ERROR`：系统错误

## 安全注意事项

1. **密钥保护**：
   - 不要在前端暴露API密钥
   - 使用环境变量存储敏感信息
   - 定期轮换密钥

2. **HTTPS**：
   - Webhook端点必须使用HTTPS
   - 生产环境必须配置SSL证书

3. **签名验证**：
   - 始终验证Webhook签名
   - 处理重复事件（幂等性）

## 生产部署检查清单

- [ ] 环境变量已正确配置
- [ ] Webhook端点可从互联网访问
- [ ] SSL证书已配置
- [ ] 日志记录正常工作
- [ ] 测试支付流程完整
- [ ] 监控和报警已设置

## 联系支持

如遇到问题，请检查：
1. 后端日志文件
2. Stripe控制台的事件日志
3. 浏览器开发者工具的网络请求 