from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from enum import Enum
from ..schemas.database_models import PAYMENT_STATUS_PENDING, PAYMENT_STATUS_COMPLETED, PAYMENT_STATUS_FAILED, SUBSCRIPTION_STATUS_ACTIVE, SUBSCRIPTION_STATUS_CANCELED, SUBSCRIPTION_STATUS_PAST_DUE

class TaskStatus(str, Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class ParagraphAnalysis(BaseModel):
    paragraph: str
    ai_generated: bool
    reason: str
    metrics: Optional[Dict[str, Any]] = None
    confidence: Optional[float] = None
    perplexity: Optional[float] = None
    ai_likelihood: Optional[str] = None
    additional_metrics: Optional[Dict[str, Any]] = None

class DetailedAnalysisResult(BaseModel):
    """文本AI检测的详细分析结果"""
    is_ai_generated: Optional[bool] = None
    confidence: Optional[float] = None
    reason: Optional[str] = None
    models_results: Optional[Dict[str, Any]] = None
    # 保留原有字段，兼容旧版本
    perplexity: Optional[float] = None
    burstiness: Optional[float] = None
    style_consistency: Optional[float] = None
    ai_likelihood: Optional[str] = None
    syntax_metrics: Optional[Dict[str, Any]] = None
    coherence_metrics: Optional[Dict[str, Any]] = None
    style_metrics: Optional[Dict[str, Any]] = None

class DetectionResult(BaseModel):
    task_id: str
    status: TaskStatus
    ai_generated_percentage: Optional[float] = None
    details: Optional[List[ParagraphAnalysis]] = None
    overall_analysis: Optional[DetailedAnalysisResult] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

class UploadResponse(BaseModel):
    task_id: str
    status: TaskStatus = TaskStatus.UPLOADED
    filename: str
    file_size: int
    created_at: datetime = Field(default_factory=datetime.now)

# 用户相关模型
class UserBase(BaseModel):
    email: EmailStr
    username: str

class UserCreate(UserBase):
    password: str

class GoogleAuthRequest(BaseModel):
    code: str
    redirect_uri: str

class WechatAuthRequest(BaseModel):
    code: str

class UserResponse(UserBase):
    id: str
    email_verified: bool = False
    created_at: datetime
    google_id: Optional[str] = None
    wechat_open_id: Optional[str] = None
    usage_count: int = 0
    free_usage_limit: int = 100
    
    class Config:
        orm_mode = True

# 令牌相关模型
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse

class TokenData(BaseModel):
    user_id: Optional[str] = None

# 支付相关模型
class PaymentStatus(str, Enum):
    PENDING = PAYMENT_STATUS_PENDING
    COMPLETED = PAYMENT_STATUS_COMPLETED
    FAILED = PAYMENT_STATUS_FAILED

class PaymentBase(BaseModel):
    amount: float
    currency: str = "CNY"

class StripePaymentRequest(PaymentBase):
    payment_method_id: str
    return_url: str

class WechatPaymentRequest(PaymentBase):
    product_description: str

class AlipayPaymentRequest(PaymentBase):
    product_description: str
    return_url: str

class PaymentCreate(PaymentBase):
    user_id: str
    payment_method: str  # "stripe", "wechat", "alipay"

class PaymentResponse(PaymentBase):
    id: str
    status: PaymentStatus
    created_at: datetime
    payment_method: str
    
    # 不同支付方式的特定字段
    stripe_payment_id: Optional[str] = None
    wechat_trade_no: Optional[str] = None
    wechat_qr_code_url: Optional[str] = None
    alipay_trade_no: Optional[str] = None
    alipay_pay_url: Optional[str] = None
    
    class Config:
        orm_mode = True

# 订阅相关模型
class SubscriptionStatus(str, Enum):
    ACTIVE = SUBSCRIPTION_STATUS_ACTIVE
    CANCELED = SUBSCRIPTION_STATUS_CANCELED
    PAST_DUE = SUBSCRIPTION_STATUS_PAST_DUE

class SubscriptionCreate(BaseModel):
    plan_id: str
    payment_method_id: Optional[str] = None  # 用于Stripe
    payment_method: str  # "stripe", "wechat", "alipay"
    
class SubscriptionResponse(BaseModel):
    id: str
    status: SubscriptionStatus
    current_period_end: datetime
    created_at: datetime
    
    class Config:
        orm_mode = True

# 订阅计划模型
class SubscriptionPlanBase(BaseModel):
    name: str
    description: Optional[str] = None
    plan_type: str
    price: float
    currency: str = "CNY"
    duration_days: int = 0
    
class SubscriptionPlanResponse(SubscriptionPlanBase):
    id: str
    created_at: datetime
    is_active: bool = True
    
    class Config:
        orm_mode = True

# 用户使用情况响应
class UserUsageResponse(BaseModel):
    can_use: bool
    reason: str
    remaining_free_usage: int
    active_subscription: Optional[Dict[str, Any]] = None 