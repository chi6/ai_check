# 支付配置说明

## 环境变量配置

为了安全起见，所有的支付相关密钥都应该通过环境变量来配置，而不是硬编码在代码中。

### Stripe 配置

```bash
# Stripe 测试环境
STRIPE_API_KEY=sk_test_your_stripe_test_key_here
STRIPE_WEBHOOK_SECRET=whsec_your_stripe_webhook_secret_here

# Stripe 生产环境
# STRIPE_API_KEY=sk_live_your_stripe_live_key_here
# STRIPE_WEBHOOK_SECRET=whsec_your_stripe_live_webhook_secret_here
```

### 支付宝配置

```bash
ALIPAY_APPID=your_alipay_appid_here
ALIPAY_PRIVATE_KEY=your_alipay_private_key_here
ALIPAY_PUBLIC_KEY=your_alipay_public_key_here
ALIPAY_NOTIFY_URL=https://yourdomain.com/api/payment/alipay/notify
```

### 微信支付配置

```bash
WECHAT_PAY_APPID=your_wechat_pay_appid_here
WECHAT_PAY_MCH_ID=your_wechat_pay_mch_id_here
WECHAT_PAY_API_KEY=your_wechat_pay_api_key_here
WECHAT_PAY_NOTIFY_URL=https://yourdomain.com/api/payment/wechat/notify
```

## 配置方法

### 1. 本地开发

在项目根目录或 backend 目录下创建 .env 文件：

```bash
# 创建 .env 文件
touch backend/.env

# 编辑 .env 文件，添加上述环境变量
nano backend/.env
```

### 2. 生产环境

在生产环境中，建议通过系统环境变量或容器环境变量来设置：

```bash
# 通过 export 设置
export STRIPE_API_KEY=sk_live_your_stripe_live_key_here

# 或者在 Docker 中通过 -e 参数设置
docker run -e STRIPE_API_KEY=sk_live_your_stripe_live_key_here your_app
```

## 安全注意事项

1. **永远不要**将真实的 API 密钥提交到版本控制系统中
2. 使用测试密钥进行开发和测试
3. 在生产环境中使用生产密钥
4. 定期轮换 API 密钥
5. 确保 .env 文件已添加到 .gitignore 中

## 验证配置

启动应用后，检查日志输出，应该看到类似以下信息：

```
STRIPE API KEY 设置: **********abc123
```

如果看到 "未设置"，说明环境变量配置有问题。 