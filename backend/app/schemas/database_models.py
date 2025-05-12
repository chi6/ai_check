from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Float, DateTime, Text, Enum
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from ..utils.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String, unique=True, index=True)
    username = Column(String, index=True)
    hashed_password = Column(String, nullable=True)  # 允许为空，因为OAuth登录可能不需要密码
    email_verified = Column(Boolean, default=False)
    
    # 使用次数相关字段
    usage_count = Column(Integer, default=0)  # 已使用的次数
    free_usage_limit = Column(Integer, default=10)  # 免费使用的次数限制
    
    # Google OAuth 相关字段
    google_id = Column(String, nullable=True, unique=True)
    google_access_token = Column(String, nullable=True)
    google_refresh_token = Column(String, nullable=True)
    
    # 微信登录相关字段
    wechat_open_id = Column(String, nullable=True, unique=True)
    wechat_union_id = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    detection_tasks = relationship("DetectionTask", back_populates="owner")
    payments = relationship("Payment", back_populates="user")
    subscriptions = relationship("Subscription", back_populates="user")

class DetectionTask(Base):
    __tablename__ = "detection_tasks"

    id = Column(String, primary_key=True, default=generate_uuid)
    filename = Column(String)
    file_size = Column(Integer)
    status = Column(String)
    ai_generated_percentage = Column(Float, nullable=True)
    
    # 添加整体分析结果
    overall_perplexity = Column(Float, nullable=True)
    overall_burstiness = Column(Float, nullable=True)
    overall_syntax_analysis = Column(String, nullable=True)  # JSON存储
    overall_coherence_analysis = Column(String, nullable=True)  # JSON存储
    overall_style_analysis = Column(String, nullable=True)  # JSON存储
    overall_analysis_result = Column(String, nullable=True)  # 新的JSON格式存储所有分析结果
    
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    owner_id = Column(String, ForeignKey("users.id"))
    
    owner = relationship("User", back_populates="detection_tasks")
    paragraphs = relationship("ParagraphResult", back_populates="task")

class ParagraphResult(Base):
    __tablename__ = "paragraph_results"

    id = Column(String, primary_key=True, default=generate_uuid)
    paragraph = Column(Text)
    ai_generated = Column(Boolean)
    reason = Column(String)
    
    # 添加详细指标
    perplexity = Column(Float, nullable=True)
    burstiness = Column(Float, nullable=True)
    confidence = Column(Float, nullable=True)
    ai_likelihood = Column(String, nullable=True)  # 存储AI可能性评级（高/中/低）
    metrics_data = Column(String, nullable=True)  # JSON存储所有其他指标
    
    task_id = Column(String, ForeignKey("detection_tasks.id"))
    
    task = relationship("DetectionTask", back_populates="paragraphs")

# 支付相关模型

# 定义支付状态字符串常量，而不是使用Enum类
PAYMENT_STATUS_PENDING = "pending"
PAYMENT_STATUS_COMPLETED = "completed"
PAYMENT_STATUS_FAILED = "failed"

# 定义订阅计划类型常量
PLAN_TYPE_SINGLE_USE = "single_use"  # 单次使用
PLAN_TYPE_DAILY = "daily"  # 日订阅
PLAN_TYPE_MONTHLY = "monthly"  # 月订阅

class SubscriptionPlan(Base):
    """订阅计划表"""
    __tablename__ = "subscription_plans"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)  # 计划名称，如"单次使用"、"日订阅"、"月订阅"
    description = Column(String, nullable=True)  # 计划描述
    plan_type = Column(String, nullable=False)  # 计划类型，使用上面定义的常量
    price = Column(Float, nullable=False)  # 价格
    currency = Column(String, default="CNY")  # 货币
    duration_days = Column(Integer, default=0)  # 订阅持续天数，0表示不是订阅而是单次购买
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    is_active = Column(Boolean, default=True)  # 是否有效

class Payment(Base):
    __tablename__ = "payments"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"))
    amount = Column(Float)
    currency = Column(String, default="CNY")
    status = Column(Enum(PAYMENT_STATUS_PENDING, PAYMENT_STATUS_COMPLETED, PAYMENT_STATUS_FAILED, name="payment_status"))
    created_at = Column(DateTime, default=datetime.now)
    
    # 新增关联计划ID
    plan_id = Column(String, ForeignKey("subscription_plans.id"), nullable=True)
    
    # Stripe支付相关字段
    stripe_payment_id = Column(String, nullable=True)
    
    # 微信支付相关字段
    wechat_trade_no = Column(String, nullable=True)
    wechat_transaction_id = Column(String, nullable=True)
    
    # 支付宝相关字段
    alipay_trade_no = Column(String, nullable=True)
    alipay_transaction_id = Column(String, nullable=True)
    
    user = relationship("User", back_populates="payments")
    plan = relationship("SubscriptionPlan", foreign_keys=[plan_id])

# 定义订阅状态字符串常量
SUBSCRIPTION_STATUS_ACTIVE = "active"
SUBSCRIPTION_STATUS_CANCELED = "canceled"
SUBSCRIPTION_STATUS_PAST_DUE = "past_due"

class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"))
    plan_id = Column(String, ForeignKey("subscription_plans.id"))  # 引用订阅计划表
    status = Column(Enum(SUBSCRIPTION_STATUS_ACTIVE, SUBSCRIPTION_STATUS_CANCELED, SUBSCRIPTION_STATUS_PAST_DUE, name="subscription_status"))
    current_period_end = Column(DateTime)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Stripe订阅相关字段
    stripe_subscription_id = Column(String, nullable=True)
    
    user = relationship("User", back_populates="subscriptions")
    plan = relationship("SubscriptionPlan") 