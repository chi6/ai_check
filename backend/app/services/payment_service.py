import stripe
import os
import json
import requests
import time
import hashlib
import uuid
import base64
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from ..schemas.database_models import (
    Payment, User, Subscription, SubscriptionPlan,
    PAYMENT_STATUS_PENDING, PAYMENT_STATUS_COMPLETED, PAYMENT_STATUS_FAILED,
    SUBSCRIPTION_STATUS_ACTIVE, SUBSCRIPTION_STATUS_CANCELED, SUBSCRIPTION_STATUS_PAST_DUE,
    PLAN_TYPE_SINGLE_USE, PLAN_TYPE_DAILY, PLAN_TYPE_MONTHLY
)
from .usage_service import add_usage_credits

# Stripe配置
STRIPE_API_KEY = os.getenv("STRIPE_API_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

# 添加日志配置
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

print(f"STRIPE API KEY 设置: {'*' * 10 + STRIPE_API_KEY[-5:] if STRIPE_API_KEY else '未设置'}")
print(f"STRIPE WEBHOOK SECRET 设置: {'*' * 10 + STRIPE_WEBHOOK_SECRET[-5:] if STRIPE_WEBHOOK_SECRET else '未设置'}")

# 设置Stripe API密钥
if not STRIPE_API_KEY:
    print("警告: STRIPE_API_KEY未设置，Stripe支付功能将不可用")
    logger.warning("STRIPE_API_KEY未设置，Stripe支付功能将不可用")
else:
    stripe.api_key = STRIPE_API_KEY
    logger.info("Stripe API密钥配置成功")

# 支付宝配置
ALIPAY_APPID = os.getenv("ALIPAY_APPID", "")
ALIPAY_PRIVATE_KEY = os.getenv("ALIPAY_PRIVATE_KEY", "")
ALIPAY_PUBLIC_KEY = os.getenv("ALIPAY_PUBLIC_KEY", "")
ALIPAY_NOTIFY_URL = os.getenv("ALIPAY_NOTIFY_URL", "")
ALIPAY_GATEWAY = "https://openapi.alipay.com/gateway.do"

# 微信支付配置
WECHAT_PAY_APPID = os.getenv("WECHAT_PAY_APPID", "")
WECHAT_PAY_MCH_ID = os.getenv("WECHAT_PAY_MCH_ID", "")
WECHAT_PAY_API_KEY = os.getenv("WECHAT_PAY_API_KEY", "")
WECHAT_PAY_NOTIFY_URL = os.getenv("WECHAT_PAY_NOTIFY_URL", "")

# Stripe支付处理
def create_stripe_payment(
    db: Session, 
    user_id: str, 
    amount: float, 
    currency: str, 
    payment_method_id: str,
    return_url: str,
    plan_id: str = None
):
    """创建Stripe支付"""
    try:
        # 获取计划信息
        plan = None
        if plan_id:
            plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == plan_id).first()
        
        # 创建Stripe PaymentIntent
        payment_intent = stripe.PaymentIntent.create(
            amount=int(amount * 100),  # Stripe使用最小货币单位（如分）
            currency=currency.lower(),
            payment_method=payment_method_id,
            confirmation_method="manual",
            confirm=True,
            return_url=return_url
        )
        
        # 创建支付记录
        payment = Payment(
            user_id=user_id,
            amount=amount,
            currency=currency,
            status=PAYMENT_STATUS_PENDING,
            stripe_payment_id=payment_intent.id,
            plan_id=plan_id if plan_id else None
        )
        
        db.add(payment)
        db.commit()
        db.refresh(payment)
        
        # 返回支付信息
        return {
            "payment_id": payment.id,
            "stripe_payment_id": payment_intent.id,
            "status": payment_intent.status,
            "client_secret": payment_intent.client_secret,
            "next_action": payment_intent.next_action
        }
    except Exception as e:
        # 记录错误并返回
        print(f"Stripe支付创建失败: {str(e)}")
        return {
            "error": str(e)
        }

def confirm_stripe_payment(db: Session, payment_id: str, payment_intent_id: str):
    """确认Stripe支付状态"""
    try:
        # 查找支付记录
        payment = db.query(Payment).filter(Payment.id == payment_id).first()
        if not payment or payment.stripe_payment_id != payment_intent_id:
            return {"error": "支付记录不存在或ID不匹配"}
        
        # 获取Stripe支付状态
        payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        
        # 更新支付记录状态
        if payment_intent.status == "succeeded":
            payment.status = PAYMENT_STATUS_COMPLETED
            
            # 如果是购买单次使用，增加用户使用次数
            process_successful_payment(db, payment)
            
        elif payment_intent.status == "canceled":
            payment.status = PAYMENT_STATUS_FAILED
        
        db.commit()
        
        # 返回结果
        return {
            "payment_id": payment.id,
            "status": payment_intent.status
        }
    except Exception as e:
        print(f"确认Stripe支付失败: {str(e)}")
        return {
            "error": str(e)
        }

# 处理成功的支付
def process_successful_payment(db: Session, payment: Payment):
    """处理成功的支付，根据计划类型执行相应操作"""
    # 检查是否有关联的计划
    if not payment.plan_id:
        return
    
    # 获取计划信息
    plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == payment.plan_id).first()
    if not plan:
        return
    
    # 根据计划类型处理
    if plan.plan_type == PLAN_TYPE_SINGLE_USE:
        # 单次使用，增加用户使用次数
        # 检查是否有usage_credits字段
        credits = 1
        if hasattr(plan, 'usage_credits') and plan.usage_credits:
            credits = plan.usage_credits
        
        add_usage_credits(db, payment.user_id, credits)
    
    elif plan.plan_type in [PLAN_TYPE_DAILY, PLAN_TYPE_MONTHLY]:
        # 创建订阅
        now = datetime.now()
        end_time = now + timedelta(days=plan.duration_days)
        
        subscription = Subscription(
            user_id=payment.user_id,
            plan_id=plan.id,
            status=SUBSCRIPTION_STATUS_ACTIVE,
            current_period_end=end_time
        )
        
        db.add(subscription)
        db.commit()

# 微信支付处理
def create_wechat_payment(
    db: Session, 
    user_id: str, 
    amount: float, 
    product_description: str
):
    """创建微信支付订单"""
    # 确保用户存在
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 生成商户订单号
    out_trade_no = f"wx_{int(time.time())}_{user_id[:8]}"
    
    # 组装数据
    data = {
        "appid": WECHAT_PAY_APPID,
        "mch_id": WECHAT_PAY_MCH_ID,
        "nonce_str": str(uuid.uuid4()).replace('-', ''),
        "body": product_description,
        "out_trade_no": out_trade_no,
        "total_fee": int(amount * 100),  # 微信支付以分为单位
        "spbill_create_ip": "127.0.0.1",  # 应该使用实际的客户端IP
        "notify_url": WECHAT_PAY_NOTIFY_URL,
        "trade_type": "NATIVE"  # 生成二维码支付
    }
    
    # 签名
    sign_string = "&".join([f"{k}={v}" for k, v in sorted(data.items()) if v]) + f"&key={WECHAT_PAY_API_KEY}"
    data["sign"] = hashlib.md5(sign_string.encode()).hexdigest().upper()
    
    # XML格式
    xml = "<xml>"
    for k, v in data.items():
        xml += f"<{k}>{v}</{k}>"
    xml += "</xml>"
    
    try:
        # 发送请求
        response = requests.post(
            "https://api.mch.weixin.qq.com/pay/unifiedorder",
            data=xml.encode("utf-8"),
            headers={"Content-Type": "application/xml"}
        )
        
        # 解析响应
        import xml.etree.ElementTree as ET
        root = ET.fromstring(response.content)
        result = {child.tag: child.text for child in root}
        
        if result.get("return_code") == "SUCCESS" and result.get("result_code") == "SUCCESS":
            # 获取二维码URL
            code_url = result.get("code_url")
            
            # 创建支付记录
            payment = Payment(
                id=str(uuid.uuid4()),
                user_id=user_id,
                amount=amount,
                currency="CNY",
                status=PAYMENT_STATUS_PENDING,
                wechat_trade_no=out_trade_no,
                created_at=datetime.now()
            )
            
            db.add(payment)
            db.commit()
            db.refresh(payment)
            
            return {
                "payment_id": payment.id,
                "status": "pending",
                "wechat_trade_no": out_trade_no,
                "qr_code_url": code_url
            }
        else:
            error_msg = result.get("err_code_des") or result.get("return_msg") or "未知错误"
            raise HTTPException(status_code=400, detail=f"创建微信支付订单失败: {error_msg}")
            
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"微信支付处理失败: {str(e)}")

def verify_wechat_payment_notification(data):
    """验证微信支付通知"""
    try:
        # 解析XML
        import xml.etree.ElementTree as ET
        root = ET.fromstring(data)
        result = {child.tag: child.text for child in root}
        
        # 验证签名
        sign = result.pop("sign", None)
        if not sign:
            return False, "签名缺失"
        
        # 重新计算签名
        sign_string = "&".join([f"{k}={v}" for k, v in sorted(result.items()) if v]) + f"&key={WECHAT_PAY_API_KEY}"
        calculated_sign = hashlib.md5(sign_string.encode()).hexdigest().upper()
        
        if calculated_sign != sign:
            return False, "签名验证失败"
        
        # 验证通知内容
        if result.get("return_code") != "SUCCESS" or result.get("result_code") != "SUCCESS":
            return False, "支付未成功"
        
        return True, result
    except Exception as e:
        return False, f"通知解析失败: {str(e)}"

def process_wechat_payment_notification(db: Session, notification_data):
    """处理微信支付通知"""
    valid, result = verify_wechat_payment_notification(notification_data)
    if not valid:
        return {"return_code": "FAIL", "return_msg": result}
    
    # 获取交易号
    out_trade_no = result.get("out_trade_no")
    transaction_id = result.get("transaction_id")
    
    # 查找支付记录
    payment = db.query(Payment).filter(Payment.wechat_trade_no == out_trade_no).first()
    if not payment:
        return {"return_code": "FAIL", "return_msg": "订单不存在"}
    
    # 更新支付状态
    payment.status = PAYMENT_STATUS_COMPLETED
    payment.wechat_transaction_id = transaction_id
    db.commit()
    
    return {"return_code": "SUCCESS", "return_msg": "OK"}

# 支付宝支付处理
def generate_alipay_signature(params, private_key):
    """生成支付宝签名"""
    # 排序参数
    sorted_params = sorted([(k, v) for k, v in params.items() if v and k != "sign"])
    sign_content = "&".join([f"{k}={v}" for k, v in sorted_params])
    
    # 使用私钥签名
    from Crypto.Signature import PKCS1_v1_5
    from Crypto.Hash import SHA256
    from Crypto.PublicKey import RSA
    
    private_key = RSA.importKey(private_key)
    signer = PKCS1_v1_5.new(private_key)
    signature = signer.sign(SHA256.new(sign_content.encode('utf-8')))
    
    # Base64编码
    return base64.b64encode(signature).decode('utf-8')

def create_alipay_payment(
    db: Session, 
    user_id: str, 
    amount: float, 
    product_description: str,
    return_url: str
):
    """创建支付宝支付"""
    # 确保用户存在
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 生成商户订单号
    out_trade_no = f"alipay_{int(time.time())}_{user_id[:8]}"
    
    # 组装参数
    params = {
        "app_id": ALIPAY_APPID,
        "method": "alipay.trade.page.pay",
        "charset": "utf-8",
        "sign_type": "RSA2",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "version": "1.0",
        "notify_url": ALIPAY_NOTIFY_URL,
        "return_url": return_url,
        "biz_content": json.dumps({
            "out_trade_no": out_trade_no,
            "product_code": "FAST_INSTANT_TRADE_PAY",
            "total_amount": str(amount),
            "subject": product_description,
            "body": product_description
        }, separators=(',', ':'))
    }
    
    # 签名
    params["sign"] = generate_alipay_signature(params, ALIPAY_PRIVATE_KEY)
    
    # 构建支付URL
    query = "&".join([f"{k}={requests.utils.quote(str(v))}" for k, v in params.items()])
    pay_url = f"{ALIPAY_GATEWAY}?{query}"
    
    # 创建支付记录
    payment = Payment(
        id=str(uuid.uuid4()),
        user_id=user_id,
        amount=amount,
        currency="CNY",
        status=PAYMENT_STATUS_PENDING,
        alipay_trade_no=out_trade_no,
        created_at=datetime.now()
    )
    
    db.add(payment)
    db.commit()
    db.refresh(payment)
    
    return {
        "payment_id": payment.id,
        "status": "pending",
        "alipay_trade_no": out_trade_no,
        "pay_url": pay_url
    }

def verify_alipay_signature(params, signature, public_key):
    """验证支付宝签名"""
    # 排除sign和sign_type
    params_to_verify = {k: v for k, v in params.items() if k not in ["sign", "sign_type"]}
    
    # 排序参数
    sorted_params = sorted([(k, v) for k, v in params_to_verify.items() if v])
    sign_content = "&".join([f"{k}={v}" for k, v in sorted_params])
    
    # 使用公钥验证签名
    from Crypto.Signature import PKCS1_v1_5
    from Crypto.Hash import SHA256
    from Crypto.PublicKey import RSA
    
    public_key = RSA.importKey(public_key)
    verifier = PKCS1_v1_5.new(public_key)
    
    # Base64解码签名
    signature_bytes = base64.b64decode(signature)
    
    # 验证
    return verifier.verify(SHA256.new(sign_content.encode('utf-8')), signature_bytes)

def process_alipay_notification(db: Session, notification_params):
    """处理支付宝支付通知"""
    # 获取签名
    signature = notification_params.get("sign")
    if not signature:
        return {"success": False, "message": "签名缺失"}
    
    # 验证签名
    if not verify_alipay_signature(notification_params, signature, ALIPAY_PUBLIC_KEY):
        return {"success": False, "message": "签名验证失败"}
    
    # 验证支付状态
    trade_status = notification_params.get("trade_status")
    if trade_status != "TRADE_SUCCESS" and trade_status != "TRADE_FINISHED":
        return {"success": False, "message": "支付未成功"}
    
    # 获取商户订单号和支付宝交易号
    out_trade_no = notification_params.get("out_trade_no")
    trade_no = notification_params.get("trade_no")
    
    # 查找支付记录
    payment = db.query(Payment).filter(Payment.alipay_trade_no == out_trade_no).first()
    if not payment:
        return {"success": False, "message": "订单不存在"}
    
    # 更新支付状态
    payment.status = PAYMENT_STATUS_COMPLETED
    payment.alipay_transaction_id = trade_no
    db.commit()
    
    return {"success": True, "message": "success"}

# 获取所有可用的订阅计划
def get_subscription_plans(db: Session) -> List[Dict[str, Any]]:
    """获取所有可用的订阅计划"""
    plans = db.query(SubscriptionPlan).filter(SubscriptionPlan.is_active == True).all()
    
    # 转换为字典列表返回
    result = []
    for plan in plans:
        plan_data = {
            "id": plan.id,
            "name": plan.name,
            "description": plan.description,
            "plan_type": plan.plan_type,
            "price": plan.price,
            "currency": plan.currency,
            "duration_days": plan.duration_days,
            "created_at": plan.created_at,
            "is_active": plan.is_active
        }
        
        # 添加Stripe链接字段（如果存在）
        if hasattr(plan, 'stripe_link') and plan.stripe_link:
            plan_data["stripe_link"] = plan.stripe_link
            
        # 添加使用次数字段（如果存在）
        if hasattr(plan, 'usage_credits') and plan.usage_credits:
            plan_data["usage_credits"] = plan.usage_credits
            
        result.append(plan_data)
    
    return result

# 订阅相关功能
def create_subscription(
    db: Session,
    user_id: str,
    plan_id: str,
    payment_method: str,
    payment_method_id: Optional[str] = None
):
    """创建订阅"""
    # 确保用户存在
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 检查用户是否已有活动订阅
    active_subscription = db.query(Subscription).filter(
        Subscription.user_id == user_id,
        Subscription.status == SUBSCRIPTION_STATUS_ACTIVE
    ).first()
    
    if active_subscription:
        return {
            "subscription_id": active_subscription.id,
            "status": active_subscription.status,
            "current_period_end": active_subscription.current_period_end,
            "message": "用户已有活动订阅"
        }
    
    # 创建订阅（这里简化处理，实际应根据不同支付方式处理）
    if payment_method == "stripe" and payment_method_id:
        # 使用Stripe创建订阅
        try:
            stripe_subscription = stripe.Subscription.create(
                customer=user_id,  # 假设user_id即为stripe customer id
                items=[{"price": plan_id}],
                payment_behavior="default_incomplete",
                expand=["latest_invoice.payment_intent"],
                payment_settings={
                    "payment_method_types": ["card"],
                    "save_default_payment_method": "on_subscription"
                },
                payment_method=payment_method_id
            )
            
            # 计算订阅期限
            current_period_end = datetime.fromtimestamp(stripe_subscription.current_period_end)
            
            # 创建订阅记录
            subscription = Subscription(
                id=str(uuid.uuid4()),
                user_id=user_id,
                plan_id=plan_id,
                status=SUBSCRIPTION_STATUS_ACTIVE,
                current_period_end=current_period_end,
                stripe_subscription_id=stripe_subscription.id
            )
            
            db.add(subscription)
            db.commit()
            db.refresh(subscription)
            
            return {
                "subscription_id": subscription.id,
                "status": subscription.status,
                "current_period_end": subscription.current_period_end,
                "client_secret": stripe_subscription.latest_invoice.payment_intent.client_secret
            }
            
        except stripe.error.StripeError as e:
            raise HTTPException(status_code=400, detail=f"创建Stripe订阅失败: {str(e)}")
    
    else:
        # 对于其他支付方式，直接创建一个简单的订阅记录
        # 订阅期限为30天
        current_period_end = datetime.now() + timedelta(days=30)
        
        subscription = Subscription(
            id=str(uuid.uuid4()),
            user_id=user_id,
            plan_id=plan_id,
            status=SUBSCRIPTION_STATUS_ACTIVE,
            current_period_end=current_period_end
        )
        
        db.add(subscription)
        db.commit()
        db.refresh(subscription)
        
        return {
            "subscription_id": subscription.id,
            "status": subscription.status,
            "current_period_end": subscription.current_period_end
        }

def cancel_subscription(db: Session, user_id: str, subscription_id: str):
    """取消订阅"""
    # 获取订阅
    subscription = db.query(Subscription).filter(
        Subscription.id == subscription_id,
        Subscription.user_id == user_id
    ).first()
    
    if not subscription:
        raise HTTPException(status_code=404, detail="订阅不存在")
    
    # 如果是Stripe订阅，则通过API取消
    if subscription.stripe_subscription_id:
        try:
            stripe.Subscription.delete(subscription.stripe_subscription_id)
        except stripe.error.StripeError as e:
            raise HTTPException(status_code=400, detail=f"取消Stripe订阅失败: {str(e)}")
    
    # 更新订阅状态
    subscription.status = SUBSCRIPTION_STATUS_CANCELED
    db.commit()
    
    return {"subscription_id": subscription.id, "status": "canceled"}

def process_stripe_webhook(db: Session, payload: bytes, sig_header: str) -> Dict[str, Any]:
    """处理来自Stripe的webhook通知"""
    logger.info("收到Stripe webhook请求")
    
    try:
        # 验证Stripe签名
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
        
        # 根据事件类型处理不同的webhook通知
        event_type = event['type']
        data = event['data']['object']
        event_id = event.get('id', 'unknown')
        
        logger.info(f"处理Stripe webhook事件: {event_type}, Event ID: {event_id}")
        print(f"处理Stripe webhook事件: {event_type}, Event ID: {event_id}")
        
        if event_type == 'payment_intent.succeeded':
            # 支付成功
            logger.info(f"处理支付成功事件, PaymentIntent ID: {data.get('id')}")
            return handle_payment_intent_succeeded(db, data)
        
        elif event_type == 'payment_intent.payment_failed':
            # 支付失败
            logger.warning(f"处理支付失败事件, PaymentIntent ID: {data.get('id')}")
            return handle_payment_intent_failed(db, data)
        
        elif event_type == 'checkout.session.completed':
            # Checkout会话完成
            logger.info(f"处理Checkout会话完成事件, Session ID: {data.get('id')}")
            return handle_checkout_session_completed(db, data)
            
        elif event_type == 'invoice.paid':
            # 发票支付成功（订阅续费）
            logger.info(f"处理发票支付成功事件, Invoice ID: {data.get('id')}")
            return handle_invoice_paid(db, data)
            
        elif event_type == 'customer.subscription.deleted':
            # 订阅被取消
            logger.info(f"处理订阅取消事件, Subscription ID: {data.get('id')}")
            return handle_subscription_deleted(db, data)
            
        # 其他事件类型...可以根据需要添加
        else:
            logger.info(f"收到未处理的webhook事件类型: {event_type}")
        
        # 对于未处理的事件类型，返回成功但不做处理
        return {
            "status": "success",
            "message": f"收到未处理的webhook事件: {event_type}"
        }
        
    except stripe.error.SignatureVerificationError as e:
        # 签名验证失败
        error_msg = f"Stripe webhook签名验证失败: {str(e)}"
        logger.error(error_msg)
        print(error_msg)
        return {
            "error": "签名验证失败"
        }
    except Exception as e:
        # 其他异常
        error_msg = f"处理Stripe webhook时出错: {str(e)}"
        logger.error(error_msg)
        print(error_msg)
        return {
            "error": str(e)
        }

def handle_payment_intent_succeeded(db: Session, data: Dict[str, Any]) -> Dict[str, Any]:
    """处理支付成功事件"""
    payment_intent_id = data.get('id')
    amount = data.get('amount', 0) / 100  # Stripe金额单位为分
    currency = data.get('currency', 'usd')
    
    logger.info(f"开始处理支付成功事件 - PaymentIntent ID: {payment_intent_id}, 金额: {amount} {currency}")
    
    # 查找对应的支付记录
    payment = db.query(Payment).filter(Payment.stripe_payment_id == payment_intent_id).first()
    
    if not payment:
        logger.warning(f"数据库中未找到支付记录: {payment_intent_id}，这可能是通过Checkout创建的支付")
        # 对于通过Checkout创建的支付，我们等待checkout.session.completed事件来处理
        # 这里只记录日志，不返回错误
        return {
            "status": "success", 
            "message": "支付成功，等待Checkout会话完成事件处理"
        }
    
    logger.info(f"找到支付记录 - Payment ID: {payment.id}, User ID: {payment.user_id}, 原状态: {payment.status}")
    
    # 更新支付状态为完成
    if payment.status != PAYMENT_STATUS_COMPLETED:
        old_status = payment.status
        payment.status = PAYMENT_STATUS_COMPLETED
        payment.updated_at = datetime.now()
        db.commit()
        
        logger.info(f"支付状态已更新 - Payment ID: {payment.id}, 状态变更: {old_status} -> {PAYMENT_STATUS_COMPLETED}")
        
        # 处理支付成功后的逻辑（例如增加用户使用额度）
        try:
            process_successful_payment(db, payment)
            logger.info(f"支付成功后处理完成 - Payment ID: {payment.id}")
        except Exception as e:
            logger.error(f"处理支付成功后逻辑时出错 - Payment ID: {payment.id}, 错误: {str(e)}")
    else:
        logger.info(f"支付记录已经是完成状态 - Payment ID: {payment.id}")
    
    return {
        "status": "success",
        "message": "支付成功处理完成",
        "payment_id": payment.id
    }

def handle_payment_intent_failed(db: Session, data: Dict[str, Any]) -> Dict[str, Any]:
    """处理支付失败事件"""
    payment_intent_id = data.get('id')
    amount = data.get('amount', 0) / 100  # Stripe金额单位为分
    currency = data.get('currency', 'usd')
    last_payment_error = data.get('last_payment_error', {})
    failure_code = last_payment_error.get('code', 'unknown')
    failure_message = last_payment_error.get('message', 'Unknown error')
    
    logger.warning(f"开始处理支付失败事件 - PaymentIntent ID: {payment_intent_id}, 金额: {amount} {currency}")
    logger.warning(f"失败原因 - Code: {failure_code}, Message: {failure_message}")
    
    # 查找对应的支付记录
    payment = db.query(Payment).filter(Payment.stripe_payment_id == payment_intent_id).first()
    
    if not payment:
        error_msg = f"未找到对应的支付记录: {payment_intent_id}"
        logger.error(error_msg)
        print(error_msg)
        return {
            "status": "error",
            "message": error_msg
        }
    
    logger.info(f"找到支付记录 - Payment ID: {payment.id}, User ID: {payment.user_id}, 原状态: {payment.status}")
    
    # 更新支付状态为失败
    old_status = payment.status
    payment.status = PAYMENT_STATUS_FAILED
    payment.updated_at = datetime.now()
    # 记录失败原因
    if hasattr(payment, 'failure_reason'):
        payment.failure_reason = f"{failure_code}: {failure_message}"
    db.commit()
    
    logger.warning(f"支付状态已更新为失败 - Payment ID: {payment.id}, 状态变更: {old_status} -> {PAYMENT_STATUS_FAILED}")
    logger.warning(f"失败详情 - User ID: {payment.user_id}, Amount: {payment.amount}, Reason: {failure_code}")
    
    return {
        "status": "success",
        "message": "支付失败状态已更新",
        "payment_id": payment.id
    }

def handle_checkout_session_completed(db: Session, data: Dict[str, Any]) -> Dict[str, Any]:
    """处理Checkout会话完成事件"""
    session_id = data.get('id')
    customer_id = data.get('customer')
    payment_intent_id = data.get('payment_intent')
    customer_email = data.get('customer_details', {}).get('email')
    
    logger.info(f"处理Checkout会话完成 - Session ID: {session_id}")
    logger.info(f"Customer ID: {customer_id}, Email: {customer_email}, PaymentIntent: {payment_intent_id}")
    
    # 如果有支付意图ID，尝试查找对应的支付记录
    if payment_intent_id:
        payment = db.query(Payment).filter(Payment.stripe_payment_id == payment_intent_id).first()
        
        if payment:
            logger.info(f"找到现有支付记录 - Payment ID: {payment.id}")
            # 更新支付状态
            payment.status = PAYMENT_STATUS_COMPLETED
            payment.updated_at = datetime.now()
            db.commit()
            
            # 处理支付成功后的逻辑
            process_successful_payment(db, payment)
            
            return {
                "status": "success",
                "message": "Checkout会话完成，支付已处理",
                "payment_id": payment.id
            }
    
    # 如果没有找到现有支付记录，可能是通过Stripe Checkout创建的新支付
    # 获取会话详情，查看购买的商品
    try:
        logger.info(f"获取Checkout会话详情 - Session ID: {session_id}")
        session = stripe.checkout.Session.retrieve(
            session_id,
            expand=['line_items']
        )
        
        logger.info(f"会话详情: {session}")
        
        # 查找客户对应的用户
        user = None
        
        # 首先尝试通过元数据找到用户
        metadata = session.get('metadata', {})
        if 'user_id' in metadata:
            user_id = metadata['user_id']
            user = db.query(User).filter(User.id == user_id).first()
            logger.info(f"通过元数据找到用户 - User ID: {user_id}")
        
        # 如果通过元数据没找到，尝试通过customer_id查找
        if not user and customer_id:
            user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
            logger.info(f"通过Customer ID查找用户: {customer_id}")
        
        # 如果还没找到，尝试通过邮箱查找
        if not user and customer_email:
            user = db.query(User).filter(User.email == customer_email).first()
            logger.info(f"通过邮箱查找用户: {customer_email}")
        
        if not user:
            error_msg = f"无法找到对应的用户 - Customer ID: {customer_id}, Email: {customer_email}"
            logger.error(error_msg)
            return {
                "status": "error",
                "message": error_msg
            }
        
        logger.info(f"找到用户 - User ID: {user.id}, Email: {user.email}")
        
        # 处理购买的商品
        line_items = session.get('line_items', {}).get('data', [])
        logger.info(f"处理 {len(line_items)} 个商品")
        
        if line_items:
            for item in line_items:
                price_data = item.get('price', {})
                price_id = price_data.get('id')
                unit_amount = price_data.get('unit_amount', 0) / 100  # 转换为美元
                currency = price_data.get('currency', 'usd')
                quantity = item.get('quantity', 1)
                product_name = price_data.get('product', {}).get('name', 'Unknown Product') if isinstance(price_data.get('product'), dict) else 'Unknown Product'
                
                logger.info(f"处理商品 - Name: {product_name}, Amount: {unit_amount} {currency}, Quantity: {quantity}")
                
                # 根据金额和元数据推断计划类型和使用次数
                plan_id = metadata.get('plan_id')
                usage_credits = 1  # 默认值
                
                # 根据元数据中的计划ID确定使用次数
                if plan_id:
                    if 'single_use_official' in plan_id:
                        usage_credits = 1
                    elif 'ten_use_official' in plan_id:
                        usage_credits = 10
                    elif 'hundred_use_official' in plan_id:
                        usage_credits = 100
                    else:
                        # 如果元数据中没有明确的计划，根据金额推断
                        if unit_amount == 1.0:
                            usage_credits = 1
                        elif unit_amount == 5.0:
                            usage_credits = 10
                        elif unit_amount == 10.0:
                            usage_credits = 100
                else:
                    # 如果没有元数据，完全根据金额推断
                    if unit_amount == 1.0:
                        usage_credits = 1
                    elif unit_amount == 5.0:
                        usage_credits = 10
                    elif unit_amount == 10.0:
                        usage_credits = 100
                
                logger.info(f"确定使用次数: {usage_credits}")
                
                # 创建新的支付记录
                import uuid
                payment = Payment(
                    user_id=user.id,
                    amount=unit_amount,
                    currency=currency.upper(),
                    status=PAYMENT_STATUS_COMPLETED,
                    stripe_payment_id=payment_intent_id,
                    plan_id=None,  # 暂时不关联具体的订阅计划
                    created_at=datetime.now()
                )
                
                db.add(payment)
                db.commit()
                db.refresh(payment)
                
                logger.info(f"创建支付记录 - Payment ID: {payment.id}")
                
                # 直接添加使用次数
                try:
                    add_usage_credits(db, user.id, usage_credits)
                    logger.info(f"成功添加使用次数 - User ID: {user.id}, Credits: {usage_credits}")
                except Exception as e:
                    logger.error(f"添加使用次数失败 - User ID: {user.id}, Error: {str(e)}")
                
                return {
                    "status": "success",
                    "message": f"新购买已处理，添加了 {usage_credits} 次使用机会",
                    "payment_id": payment.id,
                    "usage_credits": usage_credits
                }
        
        logger.warning("Checkout会话中没有找到商品")
        return {
            "status": "success",
            "message": "Checkout会话已处理，但未找到对应的商品"
        }
    except Exception as e:
        error_msg = f"处理Checkout会话时出错: {str(e)}"
        logger.error(error_msg)
        return {
            "status": "error",
            "message": error_msg
        }

def handle_invoice_paid(db: Session, data: Dict[str, Any]) -> Dict[str, Any]:
    """处理发票支付成功事件（订阅续费）"""
    subscription_id = data.get('subscription')
    customer_id = data.get('customer')
    
    if not subscription_id:
        return {
            "status": "error",
            "message": "发票中未包含订阅ID"
        }
    
    # 查找对应的订阅
    subscription = db.query(Subscription).filter(Subscription.stripe_subscription_id == subscription_id).first()
    
    if not subscription:
        return {
            "status": "error",
            "message": f"未找到对应的订阅: {subscription_id}"
        }
    
    # 获取Stripe订阅详情，更新当前周期结束时间
    try:
        stripe_subscription = stripe.Subscription.retrieve(subscription_id)
        current_period_end = datetime.fromtimestamp(stripe_subscription.current_period_end)
        
        subscription.current_period_end = current_period_end
        subscription.status = SUBSCRIPTION_STATUS_ACTIVE
        
        # 创建新的支付记录
        plan = subscription.plan
        
        if plan:
            payment = Payment(
                user_id=subscription.user_id,
                amount=plan.price,
                currency=plan.currency,
                status=PAYMENT_STATUS_COMPLETED,
                plan_id=plan.id,
                stripe_payment_id=data.get('payment_intent')
            )
            
            db.add(payment)
        
        db.commit()
        
        return {
            "status": "success",
            "message": "订阅续费成功",
            "subscription_id": subscription.id
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"处理订阅续费时出错: {str(e)}"
        }

def handle_subscription_deleted(db: Session, data: Dict[str, Any]) -> Dict[str, Any]:
    """处理订阅被取消事件"""
    subscription_id = data.get('id')
    
    # 查找对应的订阅
    subscription = db.query(Subscription).filter(Subscription.stripe_subscription_id == subscription_id).first()
    
    if not subscription:
        return {
            "status": "error",
            "message": f"未找到对应的订阅: {subscription_id}"
        }
    
    # 更新订阅状态
    subscription.status = SUBSCRIPTION_STATUS_CANCELED
    db.commit()
    
    return {
        "status": "success",
        "message": "订阅已取消",
        "subscription_id": subscription.id
    } 