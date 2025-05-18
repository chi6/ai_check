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
STRIPE_API_KEY = os.getenv("STRIPE_API_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
print(f"STRIPE API KEY 设置: {'*' * 10 + STRIPE_API_KEY[-5:] if STRIPE_API_KEY else '未设置'}")

# 设置Stripe API密钥
if not STRIPE_API_KEY:
    print("警告: STRIPE_API_KEY未设置，Stripe支付功能将不可用")
else:
    stripe.api_key = STRIPE_API_KEY

# 微信支付配置
WECHAT_PAY_APPID = os.getenv("WECHAT_PAY_APPID", "")
WECHAT_PAY_MCH_ID = os.getenv("WECHAT_PAY_MCH_ID", "")
WECHAT_PAY_API_KEY = os.getenv("WECHAT_PAY_API_KEY", "")
WECHAT_PAY_NOTIFY_URL = os.getenv("WECHAT_PAY_NOTIFY_URL", "")

# 支付宝配置
ALIPAY_APPID = os.getenv("ALIPAY_APPID", "")
ALIPAY_PRIVATE_KEY = os.getenv("ALIPAY_PRIVATE_KEY", "")
ALIPAY_PUBLIC_KEY = os.getenv("ALIPAY_PUBLIC_KEY", "")
ALIPAY_NOTIFY_URL = os.getenv("ALIPAY_NOTIFY_URL", "")
ALIPAY_GATEWAY = "https://openapi.alipay.com/gateway.do"

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
    try:
        # 验证Stripe签名
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
        
        # 根据事件类型处理不同的webhook通知
        event_type = event['type']
        data = event['data']['object']
        
        print(f"处理Stripe webhook事件: {event_type}")
        
        if event_type == 'payment_intent.succeeded':
            # 支付成功
            return handle_payment_intent_succeeded(db, data)
        
        elif event_type == 'payment_intent.payment_failed':
            # 支付失败
            return handle_payment_intent_failed(db, data)
        
        elif event_type == 'checkout.session.completed':
            # Checkout会话完成
            return handle_checkout_session_completed(db, data)
            
        elif event_type == 'invoice.paid':
            # 发票支付成功（订阅续费）
            return handle_invoice_paid(db, data)
            
        elif event_type == 'customer.subscription.deleted':
            # 订阅被取消
            return handle_subscription_deleted(db, data)
            
        # 其他事件类型...可以根据需要添加
        
        # 对于未处理的事件类型，返回成功但不做处理
        return {
            "status": "success",
            "message": f"收到未处理的webhook事件: {event_type}"
        }
        
    except stripe.error.SignatureVerificationError:
        # 签名验证失败
        print("Stripe webhook签名验证失败")
        return {
            "error": "签名验证失败"
        }
    except Exception as e:
        # 其他异常
        print(f"处理Stripe webhook时出错: {str(e)}")
        return {
            "error": str(e)
        }

def handle_payment_intent_succeeded(db: Session, data: Dict[str, Any]) -> Dict[str, Any]:
    """处理支付成功事件"""
    payment_intent_id = data.get('id')
    
    # 查找对应的支付记录
    payment = db.query(Payment).filter(Payment.stripe_payment_id == payment_intent_id).first()
    
    if not payment:
        print(f"未找到对应的支付记录: {payment_intent_id}")
        return {
            "status": "error",
            "message": f"未找到对应的支付记录: {payment_intent_id}"
        }
    
    # 更新支付状态为完成
    if payment.status != PAYMENT_STATUS_COMPLETED:
        payment.status = PAYMENT_STATUS_COMPLETED
        db.commit()
        
        # 处理支付成功后的逻辑（例如增加用户使用额度）
        process_successful_payment(db, payment)
    
    return {
        "status": "success",
        "message": "支付成功处理完成",
        "payment_id": payment.id
    }

def handle_payment_intent_failed(db: Session, data: Dict[str, Any]) -> Dict[str, Any]:
    """处理支付失败事件"""
    payment_intent_id = data.get('id')
    
    # 查找对应的支付记录
    payment = db.query(Payment).filter(Payment.stripe_payment_id == payment_intent_id).first()
    
    if not payment:
        return {
            "status": "error",
            "message": f"未找到对应的支付记录: {payment_intent_id}"
        }
    
    # 更新支付状态为失败
    payment.status = PAYMENT_STATUS_FAILED
    db.commit()
    
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
    
    # 如果有支付意图ID，尝试查找对应的支付记录
    if payment_intent_id:
        payment = db.query(Payment).filter(Payment.stripe_payment_id == payment_intent_id).first()
        
        if payment:
            # 更新支付状态
            payment.status = PAYMENT_STATUS_COMPLETED
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
        session = stripe.checkout.Session.retrieve(
            session_id,
            expand=['line_items']
        )
        
        # 查找客户对应的用户
        user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
        
        if not user:
            # 尝试通过元数据找到用户
            if 'metadata' in data and 'user_id' in data['metadata']:
                user_id = data['metadata']['user_id']
                user = db.query(User).filter(User.id == user_id).first()
            
            if not user:
                return {
                    "status": "error",
                    "message": f"无法找到对应的用户: {customer_id}"
                }
        
        # 处理购买的商品
        if session.get('line_items', {}).get('data'):
            for item in session['line_items']['data']:
                price_id = item.get('price', {}).get('id')
                quantity = item.get('quantity', 1)
                
                # 查找对应的订阅计划
                plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.stripe_price_id == price_id).first()
                
                if plan:
                    # 创建新的支付记录
                    payment = Payment(
                        user_id=user.id,
                        amount=plan.price,
                        currency=plan.currency,
                        status=PAYMENT_STATUS_COMPLETED,
                        stripe_payment_id=payment_intent_id,
                        plan_id=plan.id
                    )
                    
                    db.add(payment)
                    db.commit()
                    db.refresh(payment)
                    
                    # 处理支付成功后的逻辑
                    process_successful_payment(db, payment)
                    
                    return {
                        "status": "success",
                        "message": "新购买已处理",
                        "payment_id": payment.id
                    }
        
        return {
            "status": "success",
            "message": "Checkout会话已处理，但未找到对应的商品"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"处理Checkout会话时出错: {str(e)}"
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