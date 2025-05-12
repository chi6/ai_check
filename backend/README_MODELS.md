# AI检测模型下载指南

本项目使用了多种NLP模型来进行AI生成内容检测。在离线环境或网络不稳定的情况下，可能需要预先下载这些模型。本指南将帮助您完成模型的下载和配置。

## 所需模型

项目使用以下模型：

1. **GPT-2**: 用于计算文本困惑度
2. **SentenceTransformer (all-MiniLM-L6-v2)**: 用于计算文本段落之间的风格一致性
3. **NLTK数据包**: 用于文本分割和预处理

## 自动下载模型

我们提供了一个简便的脚本来自动下载所有必要的模型。

### 使用方法

```bash
# 下载所有模型
python download_models.py --all

# 或者仅下载特定模型
python download_models.py --gpt2 --sentence-transformer
```

### 命令行选项

- `--all`: 下载所有模型和数据
- `--gpt2`: 仅下载GPT-2模型
- `--sentence-transformer`: 仅下载SentenceTransformer模型
- `--nltk`: 仅下载NLTK数据包
- `--models-dir`: 指定模型保存目录，默认为`models`

## 离线模式

如果您在完全离线的环境中工作，可以在`.env`文件中设置：

```
OFFLINE_MODE=true
```

这将告诉系统仅使用本地模型，不尝试在线下载。

## 手动下载和配置

如果您需要手动下载模型，请参考以下步骤：

### GPT-2模型

1. 从Hugging Face下载GPT-2模型
2. 将模型文件保存到`models/gpt2/`目录

### SentenceTransformer模型

1. 下载`all-MiniLM-L6-v2`模型
2. 将模型文件保存到`models/all-MiniLM-L6-v2/`目录

### NLTK数据

1. 下载NLTK的`punkt`数据包
2. 保存到`models/nltk_data/`目录

## 故障排除

如果遇到模型下载或加载问题，可尝试以下方法：

1. 确保网络连接正常
2. 检查您是否有足够的磁盘空间
3. 确保Python环境中已安装所有必要的依赖包
4. 如果在防火墙后面，确保已允许访问Hugging Face的域名

如果仍然遇到问题，可以尝试手动下载模型文件，并按照上述目录结构放置。

# 模型使用说明

本应用使用以下模型进行AI内容检测：

1. Sentence Transformer (all-MiniLM-L6-v2)：用于句子向量化
2. GPT-2：用于计算文本困惑度（Perplexity）
3. 其他统计特征提取模型

## 模型自动下载

首次运行应用时，系统会自动下载所需模型。请确保有稳定的网络连接和足够的磁盘空间。也可以手动运行：

```
python download_models.py
```

## 离线模式

如果您在没有网络连接的环境中运行应用，可以设置环境变量 `OFFLINE_MODE=true` 来使用本地模型。确保已经预先下载好所有必要的模型。

## 自定义模型路径

您可以在`.env`文件中自定义模型存储路径：

```
SENTENCE_TRANSFORMER_PATH=models/all-MiniLM-L6-v2
GPT2_MODEL_PATH=models/gpt2
TRANSFORMERS_CACHE=models/
SENTENCE_TRANSFORMERS_HOME=models/
```

# 登录和支付功能使用说明

本应用支持多种登录方式和支付集成。

## 登录系统

### 1. Email + 密码登录

这是最基础的登录方式，适用于所有用户。

**接口**：
- 注册：`POST /api/user/register`
- 登录：`POST /api/user/token`
- 获取用户信息：`GET /api/user/me`

**示例（使用curl）**：
```bash
# 注册新用户
curl -X POST "http://localhost:8000/api/user/register" \
     -H "Content-Type: application/json" \
     -d '{"email": "user@example.com", "username": "test_user", "password": "secure_password"}'

# 登录获取令牌
curl -X POST "http://localhost:8000/api/user/token" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "username=user@example.com&password=secure_password"
```

### 2. Google OAuth登录

允许用户使用Google账号登录。

**配置**：
1. 在Google Cloud Console创建OAuth客户端ID
2. 设置正确的重定向URI
3. 更新`.env`文件中的Google OAuth配置

**接口**：
- 登录：`POST /api/user/google-auth`

**流程**：
1. 前端使用Google OAuth按钮获取授权码
2. 将授权码发送到后端接口进行验证并获取令牌

### 3. 微信扫码登录

适用于中国用户的微信扫码登录。

**配置**：
1. 在微信开放平台注册应用
2. 更新`.env`文件中的微信配置

**接口**：
- 登录：`POST /api/user/wechat-auth`

**流程**：
1. 前端显示微信登录二维码，用户使用微信扫描
2. 扫描后获取授权码，发送到后端进行验证并获取令牌

## 支付系统

### 1. Stripe支付

适用于国际信用卡支付。

**配置**：
1. 注册Stripe账户并获取API密钥
2. 更新`.env`文件中的Stripe配置

**接口**：
- 创建支付：`POST /api/payments/stripe`
- 确认支付：`POST /api/payments/stripe/{payment_id}/confirm`

**示例（使用curl）**：
```bash
# 创建Stripe支付
curl -X POST "http://localhost:8000/api/payments/stripe" \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
     -d '{"amount": 100.00, "currency": "USD", "payment_method_id": "pm_card_visa", "return_url": "http://your-site.com/payment-success"}'
```

### 2. 微信支付

适用于中国用户的微信支付。

**配置**：
1. 注册微信支付商户号
2. 配置API密钥和回调URL
3. 更新`.env`文件中的微信支付配置

**接口**：
- 创建支付：`POST /api/payments/wechat`
- 支付通知：`POST /api/payments/wechat/notify`（由微信支付服务器调用）

### 3. 支付宝支付

适用于中国用户的支付宝支付。

**配置**：
1. 注册支付宝开放平台账户
2. 配置密钥和回调URL
3. 更新`.env`文件中的支付宝配置

**接口**：
- 创建支付：`POST /api/payments/alipay`
- 支付通知：`POST /api/payments/alipay/notify`（由支付宝服务器调用）

## 订阅功能

支持创建和管理用户订阅。

**接口**：
- 创建订阅：`POST /api/subscriptions`
- 取消订阅：`DELETE /api/subscriptions/{subscription_id}`

## 安全说明

1. 所有接口（除登录/注册外）都需要有效的JWT令牌
2. 密码使用bcrypt加密存储
3. 支付敏感信息通过HTTPS传输
4. 用户应确保服务器配置了HTTPS证书 