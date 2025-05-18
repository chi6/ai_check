from fastapi import APIRouter, Depends, HTTPException, status, Request, Body, Response
from sqlalchemy.orm import Session
from typing import List
from ..schemas.models import (
    PaymentBase, StripePaymentRequest, WechatPaymentRequest, AlipayPaymentRequest,
    PaymentResponse, SubscriptionCreate, SubscriptionResponse, SubscriptionPlanResponse
)
from ..schemas.database_models import User, Payment, Subscription, SubscriptionPlan
from ..utils.database import get_db
from ..services.auth import get_current_user
from ..services.payment_service import (
    create_stripe_payment,
    confirm_stripe_payment,
    create_wechat_payment,
    process_wechat_payment_notification,
    create_alipay_payment,
    process_alipay_notification,
    create_subscription,
    cancel_subscription,
    get_subscription_plans,
    process_stripe_webhook
)
import stripe

router = APIRouter()

# Stripe支付相关路由
@router.post("/payments/stripe", response_model=dict)
async def create_stripe_payment_route(
    payment_request: StripePaymentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    创建Stripe支付
    """
    result = create_stripe_payment(
        db, 
        current_user.id, 
        payment_request.amount, 
        payment_request.currency, 
        payment_request.payment_method_id,
        payment_request.return_url
    )
    return result

@router.post("/payments/stripe/{payment_id}/confirm")
async def confirm_stripe_payment_route(
    payment_id: str,
    payment_intent_id: str = Body(..., embed=True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    确认Stripe支付状态
    """
    result = confirm_stripe_payment(db, payment_id, payment_intent_id)
    return result

# 微信支付相关路由
@router.post("/payments/wechat", response_model=dict)
async def create_wechat_payment_route(
    payment_request: WechatPaymentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    创建微信支付
    """
    result = create_wechat_payment(
        db, 
        current_user.id, 
        payment_request.amount, 
        payment_request.product_description
    )
    return result

@router.post("/payments/wechat/notify")
async def wechat_payment_notify(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    处理微信支付通知
    """
    notification_data = await request.body()
    result = process_wechat_payment_notification(db, notification_data)
    
    # 根据微信支付要求返回XML格式响应
    response_xml = "<xml>"
    for k, v in result.items():
        response_xml += f"<{k}>{v}</{k}>"
    response_xml += "</xml>"
    
    return Response(content=response_xml, media_type="application/xml")

# 支付宝支付相关路由
@router.post("/payments/alipay", response_model=dict)
async def create_alipay_payment_route(
    payment_request: AlipayPaymentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    创建支付宝支付
    """
    result = create_alipay_payment(
        db, 
        current_user.id, 
        payment_request.amount, 
        payment_request.product_description,
        payment_request.return_url
    )
    return result

@router.post("/payments/alipay/notify")
async def alipay_payment_notify(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    处理支付宝支付通知
    """
    # 支付宝通知参数是表单格式
    form_data = await request.form()
    notification_params = {k: v for k, v in form_data.items()}
    
    result = process_alipay_notification(db, notification_params)
    return result

# 订阅相关路由
@router.post("/subscriptions", response_model=dict)
async def create_subscription_route(
    subscription_request: SubscriptionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    创建订阅
    """
    result = create_subscription(
        db, 
        current_user.id, 
        subscription_request.plan_id, 
        subscription_request.payment_method,
        subscription_request.payment_method_id
    )
    return result

@router.delete("/subscriptions/{subscription_id}")
async def cancel_subscription_route(
    subscription_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    取消订阅
    """
    result = cancel_subscription(db, current_user.id, subscription_id)
    return result

# 获取用户支付和订阅记录
@router.get("/payments", response_model=list)
async def get_user_payments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取当前用户的所有支付记录
    """
    payments = db.query(Payment).filter(Payment.user_id == current_user.id).all()
    
    results = []
    for payment in payments:
        payment_data = {
            "id": payment.id,
            "amount": payment.amount,
            "currency": payment.currency,
            "status": payment.status,
            "created_at": payment.created_at,
        }
        
        # 添加支付方式特定的字段
        if payment.stripe_payment_id:
            payment_data["payment_method"] = "stripe"
            payment_data["stripe_payment_id"] = payment.stripe_payment_id
        elif payment.wechat_trade_no:
            payment_data["payment_method"] = "wechat"
            payment_data["wechat_trade_no"] = payment.wechat_trade_no
            payment_data["wechat_transaction_id"] = payment.wechat_transaction_id
        elif payment.alipay_trade_no:
            payment_data["payment_method"] = "alipay"
            payment_data["alipay_trade_no"] = payment.alipay_trade_no
            payment_data["alipay_transaction_id"] = payment.alipay_transaction_id
        
        results.append(payment_data)
    
    return results

@router.get("/subscriptions", response_model=list)
async def get_user_subscriptions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取当前用户的所有订阅记录
    """
    subscriptions = db.query(Subscription).filter(Subscription.user_id == current_user.id).all()
    
    results = []
    for subscription in subscriptions:
        subscription_data = {
            "id": subscription.id,
            "plan_id": subscription.plan_id,
            "status": subscription.status,
            "current_period_end": subscription.current_period_end,
            "created_at": subscription.created_at,
            "updated_at": subscription.updated_at
        }
        
        # 添加特定字段
        if subscription.stripe_subscription_id:
            subscription_data["payment_method"] = "stripe"
            subscription_data["stripe_subscription_id"] = subscription.stripe_subscription_id
        
        results.append(subscription_data)
    
    return results

# 获取订阅计划
@router.get("/plans", response_model=List[SubscriptionPlanResponse])
async def get_plans(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取所有可用的订阅计划
    """
    plans = get_subscription_plans(db)
    return plans

# 获取特定计划的Stripe支付链接
@router.get("/plans/{plan_id}/stripe-link")
async def get_plan_stripe_link(
    plan_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取特定计划的Stripe直接支付链接
    """
    plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == plan_id).first()
    
    if not plan:
        raise HTTPException(status_code=404, detail="计划不存在")
        
    # 检查是否有Stripe链接
    if not hasattr(plan, 'stripe_link') or not plan.stripe_link:
        raise HTTPException(status_code=400, detail="该计划没有配置Stripe支付链接")
    
    return {"stripe_link": plan.stripe_link}

# 创建购买计划的支付
@router.post("/checkout", response_model=dict)
async def create_plan_payment(
    plan_id: str = Body(...),
    payment_method: str = Body(...),  # "stripe", "wechat", "alipay"
    payment_method_id: str = Body(None),  # 用于Stripe支付
    return_url: str = Body(None),  # 用于支付后跳转
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    创建购买计划的支付
    """
    # 获取计划信息
    plan = db.query(SubscriptionPlan).filter(
        SubscriptionPlan.id == plan_id,
        SubscriptionPlan.is_active == True
    ).first()
    
    if not plan:
        raise HTTPException(status_code=404, detail="订阅计划不存在或已停用")
    
    # 根据支付方式创建不同的支付
    if payment_method == "stripe":
        if not payment_method_id:
            raise HTTPException(status_code=400, detail="Stripe支付需要提供payment_method_id")
        
        result = create_stripe_payment(
            db, 
            current_user.id, 
            plan.price, 
            plan.currency, 
            payment_method_id,
            return_url or "",
            plan_id
        )
        return result
    
    elif payment_method == "wechat":
        result = create_wechat_payment(
            db, 
            current_user.id, 
            plan.price,
            f"购买{plan.name}"
        )
        return result
    
    elif payment_method == "alipay":
        result = create_alipay_payment(
            db, 
            current_user.id, 
            plan.price,
            f"购买{plan.name}",
            return_url or ""
        )
        return result
    
    else:
        raise HTTPException(status_code=400, detail="不支持的支付方式")

# Stripe Webhook处理
@router.post("/payments/stripe/webhook", status_code=status.HTTP_200_OK)
async def stripe_webhook_handler(
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    """
    处理来自Stripe的webhook通知
    """
    # 获取原始请求体
    payload = await request.body()
    # 获取Stripe签名标头
    sig_header = request.headers.get("stripe-signature")

    # 处理webhook并返回结果
    result = process_stripe_webhook(db, payload, sig_header)
    
    # 如果处理失败，返回相应的状态码
    if "error" in result:
        response.status_code = status.HTTP_400_BAD_REQUEST
    
    return result

@router.post("/payments/stripe/create-checkout", response_model=dict)
async def create_stripe_checkout_session(
    plan_id: str = Body(...),
    success_url: str = Body(...),
    cancel_url: str = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建Stripe Checkout会话"""
    # 获取计划信息
    plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == plan_id).first()
    
    try:
        # 处理硬编码计划ID（从前端传递的官方计划）
        price = None
        if not plan:
            if plan_id == 'single_use_official':
                # 单次使用 - 1美元 - 直接使用实际价格而不是价格ID
                price_data = {
                    'unit_amount': 100,  # 1美元，以美分为单位
                    'currency': 'usd',
                    'product_data': {
                        'name': '单次使用检测额度',
                        'description': '充值1美元获取1次检测机会',
                    },
                }
            elif plan_id == 'ten_use_official':
                # 十次使用 - 5美元
                price_data = {
                    'unit_amount': 500,  # 5美元，以美分为单位
                    'currency': 'usd',
                    'product_data': {
                        'name': '十次使用检测额度',
                        'description': '充值5美元获取10次检测机会',
                    },
                }
            elif plan_id == 'hundred_use_official':
                # 百次使用 - 10美元
                price_data = {
                    'unit_amount': 1000,  # 10美元，以美分为单位
                    'currency': 'usd',
                    'product_data': {
                        'name': '百次使用检测额度',
                        'description': '充值10美元获取100次检测机会',
                    },
                }
            else:
                raise HTTPException(status_code=404, detail="计划不存在")
        else:
            # 使用数据库中的计划价格信息
            if plan.stripe_price_id:
                price = plan.stripe_price_id
            else:
                # 如果没有价格ID，使用价格数据创建
                price_data = {
                    'unit_amount': int(plan.price * 100),  # 转换为美分
                    'currency': plan.currency.lower(),
                    'product_data': {
                        'name': plan.name,
                        'description': plan.description or f"购买{plan.name}",
                    },
                }
        
        # 创建Checkout会话
        line_items = []
        if price:
            # 使用价格ID
            line_items.append({
                'price': price,
                'quantity': 1,
            })
        else:
            # 使用价格数据
            line_items.append({
                'price_data': price_data,
                'quantity': 1,
            })
            
        checkout_session = stripe.checkout.Session.create(
            customer_email=current_user.email,
            line_items=line_items,
            metadata={
                'user_id': current_user.id,
                'plan_id': plan_id,
            },
            mode='payment',
            success_url=success_url,
            cancel_url=cancel_url,
        )
        
        return {
            "checkout_url": checkout_session.url,
            "session_id": checkout_session.id
        }
    except Exception as e:
        print(f"创建Stripe Checkout会话失败: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=f"创建会话失败: {str(e)}") 