# Stripe 测试环境配置

## 测试环境API密钥

### Stripe API Key (测试环境)
```
STRIPE_API_KEY=sk_test_51NjpkiAAuYT8V1RgoIoZdGVP40JRz1FkPqYNHMhUdDdRkxL4IZRnj5ujsWYvgXuYRJcw30oajHnmCt2YdWSKMnEh003LQg87ZZ
```

### Stripe Webhook Secret (测试环境)
```
STRIPE_WEBHOOK_SECRET=whsec_KQ7O1NM8ebp5NCoBaKdbHXhs65v1uqjs
```

## 环境变量配置

在 `.env` 文件中添加以下配置：

```env
# Stripe 测试环境配置
STRIPE_API_KEY=sk_test_51NjpkiAAuYT8V1RgoIoZdGVP40JRz1FkPqYNHMhUdDdRkxL4IZRnj5ujsWYvgXuYRJcw30oajHnmCt2YdWSKMnEh003LQg87ZZ
STRIPE_WEBHOOK_SECRET=whsec_KQ7O1NM8ebp5NCoBaKdbHXhs65v1uqjs
```

## 注意事项

⚠️ **重要提醒**：
- 这些是测试环境密钥，仅用于开发和测试
- 生产环境必须使用正式的Stripe密钥
- 不要在生产环境中使用这些测试密钥
- 建议将此文件添加到 `.gitignore` 中以避免意外提交敏感信息

## 使用方法

1. 复制上述环境变量到你的 `.env` 文件
2. 重启应用服务
3. 测试Stripe支付功能

## 相关文件

- `backend/app/services/payment_service.py` - 支付服务实现
- `backend/.env` - 环境变量配置文件 