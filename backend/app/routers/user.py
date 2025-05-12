from fastapi import APIRouter, Depends, HTTPException, status, Request, Body, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from ..schemas.models import (
    UserCreate, UserResponse, Token, GoogleAuthRequest, WechatAuthRequest,
    PaymentBase, StripePaymentRequest, WechatPaymentRequest, AlipayPaymentRequest,
    PaymentResponse, SubscriptionCreate, SubscriptionResponse, UserUsageResponse
)
from ..schemas.database_models import User, Payment, Subscription
from ..utils.database import get_db
from ..services.auth import (
    get_user, 
    authenticate_user, 
    create_access_token, 
    get_password_hash,
    get_current_user,
    verify_google_token,
    verify_wechat_code,
    get_user_by_google_id,
    get_user_by_wechat_id,
    verify_password,
    SECRET_KEY,
    ALGORITHM
)
from ..services.payment_service import (
    create_stripe_payment,
    confirm_stripe_payment,
    create_wechat_payment,
    process_wechat_payment_notification,
    create_alipay_payment,
    process_alipay_notification,
    create_subscription,
    cancel_subscription
)
from ..services.usage_service import check_user_usage_eligibility, add_usage_credits
from datetime import timedelta, datetime
from jose import jwt

router = APIRouter()

# 用户注册与认证
@router.post("/user/register", response_model=UserResponse)
async def register_user(user: UserCreate, db: Session = Depends(get_db)):
    """
    注册新用户
    """
    # 检查邮箱是否已被注册
    db_user = get_user(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="邮箱已被注册")
    
    # 验证密码强度
    if len(user.password) < 8:
        raise HTTPException(status_code=400, detail="密码长度必须至少为8个字符")
    
    # 密码复杂度检查
    has_uppercase = any(c.isupper() for c in user.password)
    has_lowercase = any(c.islower() for c in user.password)
    has_digit = any(c.isdigit() for c in user.password)
    has_special = any(not c.isalnum() for c in user.password)
    
    if not (has_uppercase and has_lowercase and has_digit and has_special):
        raise HTTPException(
            status_code=400, 
            detail="密码必须包含大写字母、小写字母、数字和特殊字符"
        )
    
    # 创建新用户
    hashed_password = get_password_hash(user.password)
    db_user = User(
        email=user.email,
        username=user.username,
        hashed_password=hashed_password,
        created_at=datetime.now()
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    print(f"用户注册成功: 邮箱 {user.email}, 用户名 {user.username}")
    
    return UserResponse(
        id=db_user.id,
        email=db_user.email,
        username=db_user.username,
        created_at=db_user.created_at
    )

@router.post("/user/token", response_model=Token)
async def login_for_access_token(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    获取访问令牌（用户名密码登录）
    """
    print(f"尝试登录: 用户名={form_data.username}")
    
    # 使用form_data.username作为邮箱，而不是用户名
    user = authenticate_user(db, form_data.username, form_data.password)
    
    # 如果直接通过邮箱查找失败，尝试查找用户名对应的用户
    if not user:
        # 查找与username匹配的用户
        db_user = db.query(User).filter(User.username == form_data.username).first()
        if db_user and verify_password(form_data.password, db_user.hashed_password):
            user = db_user
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="邮箱/用户名或密码不正确",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 创建更长效的令牌，避免频繁失效
    access_token_expires = timedelta(hours=24)
    access_token, expires_in = create_access_token(
        data={"sub": user.id}, expires_delta=access_token_expires
    )
    
    # 设置cookie中的令牌
    cookie_expires = int(expires_in)  # 转换为秒
    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=cookie_expires,
        httponly=True,  # 防止JavaScript访问
        samesite="lax",  # 允许跨站点GET请求携带Cookie
        secure=False  # 开发环境可以设为False，生产环境应为True
    )
    
    # 打印生成的令牌和有效期，用于调试
    print(f"生成访问令牌成功，有效期: {expires_in}秒")
    print("已将令牌设置到Cookie中")
    
    return Token(
        access_token=access_token, 
        token_type="bearer",
        expires_in=expires_in,
        user=UserResponse(
            id=user.id,
            email=user.email,
            username=user.username,
            email_verified=user.email_verified,
            created_at=user.created_at,
            google_id=user.google_id,
            wechat_open_id=user.wechat_open_id
        )
    )

@router.post("/user/google-auth", response_model=Token)
async def google_auth(
    auth_request: GoogleAuthRequest,
    db: Session = Depends(get_db)
):
    """
    Google OAuth登录
    """
    try:
        # 验证Google授权码
        user_info = verify_google_token(auth_request.code, auth_request.redirect_uri)
        
        # 检查用户是否已存在
        db_user = get_user_by_google_id(db, user_info["google_id"])
        
        if not db_user:
            # 检查是否存在同email的用户
            email_user = get_user(db, user_info["email"])
            
            if email_user:
                # 关联Google账号
                email_user.google_id = user_info["google_id"]
                email_user.google_access_token = user_info["access_token"]
                email_user.google_refresh_token = user_info.get("refresh_token")
                email_user.email_verified = True
                db.commit()
                db_user = email_user
            else:
                # 创建新用户
                db_user = User(
                    email=user_info["email"],
                    username=user_info["name"],
                    google_id=user_info["google_id"],
                    google_access_token=user_info["access_token"],
                    google_refresh_token=user_info.get("refresh_token"),
                    email_verified=True,
                    created_at=datetime.now()
                )
                db.add(db_user)
                db.commit()
                db.refresh(db_user)
        else:
            # 更新令牌
            db_user.google_access_token = user_info["access_token"]
            if user_info.get("refresh_token"):
                db_user.google_refresh_token = user_info["refresh_token"]
            db.commit()
        
        # 创建访问令牌
        access_token_expires = timedelta(minutes=30)
        access_token, expires_in = create_access_token(
            data={"sub": db_user.id}, expires_delta=access_token_expires
        )
        
        return Token(
            access_token=access_token, 
            token_type="bearer",
            expires_in=expires_in,
            user=UserResponse(
                id=db_user.id,
                email=db_user.email,
                username=db_user.username,
                email_verified=db_user.email_verified,
                created_at=db_user.created_at,
                google_id=db_user.google_id,
                wechat_open_id=db_user.wechat_open_id
            )
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Google认证失败: {str(e)}",
        )

@router.post("/user/wechat-auth", response_model=Token)
async def wechat_auth(
    auth_request: WechatAuthRequest,
    db: Session = Depends(get_db)
):
    """
    微信登录
    """
    try:
        # 验证微信授权码
        user_info = verify_wechat_code(auth_request.code)
        
        # 检查用户是否已存在
        db_user = get_user_by_wechat_id(db, user_info["open_id"])
        
        if not db_user:
            # 创建新用户
            db_user = User(
                email=f"wx_{user_info['open_id']}@example.com",  # 微信用户可能没有email
                username=user_info.get("nickname", "微信用户"),
                wechat_open_id=user_info["open_id"],
                wechat_union_id=user_info.get("union_id"),
                created_at=datetime.now()
            )
            db.add(db_user)
            db.commit()
            db.refresh(db_user)
        
        # 创建访问令牌
        access_token_expires = timedelta(minutes=30)
        access_token, expires_in = create_access_token(
            data={"sub": db_user.id}, expires_delta=access_token_expires
        )
        
        return Token(
            access_token=access_token, 
            token_type="bearer",
            expires_in=expires_in,
            user=UserResponse(
                id=db_user.id,
                email=db_user.email,
                username=db_user.username,
                email_verified=db_user.email_verified,
                created_at=db_user.created_at,
                google_id=db_user.google_id,
                wechat_open_id=db_user.wechat_open_id
            )
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"微信认证失败: {str(e)}",
        )

@router.get("/user/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_user)):
    """
    获取当前用户信息
    """
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        email_verified=current_user.email_verified,
        created_at=current_user.created_at,
        google_id=current_user.google_id,
        wechat_open_id=current_user.wechat_open_id
    )

@router.get("/user/tasks")
async def get_user_tasks(
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """
    获取用户任务列表
    """
    tasks = current_user.detection_tasks
    return [
        {
            "id": task.id,
            "filename": task.filename,
            "status": task.status,
            "ai_generated_percentage": task.ai_generated_percentage,
            "created_at": task.created_at
        }
        for task in tasks
    ]

# 支付相关路由
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
        db=db,
        user_id=current_user.id,
        amount=payment_request.amount,
        currency=payment_request.currency,
        payment_method_id=payment_request.payment_method_id,
        return_url=payment_request.return_url
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
        db=db,
        user_id=current_user.id,
        amount=payment_request.amount,
        product_description=payment_request.product_description
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
    
    if result.get("return_code") == "SUCCESS":
        # 返回XML格式
        return f"<xml><return_code><![CDATA[SUCCESS]]></return_code><return_msg><![CDATA[OK]]></return_msg></xml>"
    else:
        return f"<xml><return_code><![CDATA[FAIL]]></return_code><return_msg><![CDATA[{result.get('return_msg', '处理失败')}]]></return_msg></xml>"

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
        db=db,
        user_id=current_user.id,
        amount=payment_request.amount,
        product_description=payment_request.product_description,
        return_url=payment_request.return_url
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
    form_data = await request.form()
    notification_params = dict(form_data)
    
    result = process_alipay_notification(db, notification_params)
    
    if result.get("success"):
        return "success"
    else:
        return result.get("message", "fail")

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
        db=db,
        user_id=current_user.id,
        plan_id=subscription_request.plan_id,
        payment_method=subscription_request.payment_method,
        payment_method_id=subscription_request.payment_method_id
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

# 获取用户使用情况接口
@router.get("/user/usage", response_model=UserUsageResponse)
async def get_user_usage(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取当前用户的使用情况，包括剩余免费次数和订阅状态
    """
    result = check_user_usage_eligibility(db, current_user.id)
    return UserUsageResponse(**result)

# 添加管理员端点（仅用于调试和紧急情况）
@router.post("/admin/reset-user-password")
async def admin_reset_password(
    email: str = Body(...),
    new_password: str = Body(...),
    admin_key: str = Body(...),
    db: Session = Depends(get_db)
):
    """
    管理员重置用户密码（仅限调试和紧急情况）
    """
    # 安全检查 - 使用简单的密钥验证，生产环境应使用更强的身份验证
    if admin_key != "admin_secret_key_for_debug_only":  # 在生产环境中应从环境变量获取
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="管理员密钥不正确"
        )
    
    user = get_user(db, email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"用户 {email} 不存在"
        )
    
    # 重置密码
    hashed_password = get_password_hash(new_password)
    user.hashed_password = hashed_password
    db.commit()
    
    return {"message": f"用户 {email} 的密码已重置"}

@router.get("/admin/user-info")
async def admin_get_user_info(
    email: str,
    admin_key: str,
    db: Session = Depends(get_db)
):
    """
    获取用户信息（仅限调试和紧急情况）
    """
    # 安全检查
    if admin_key != "admin_secret_key_for_debug_only":  # 在生产环境中应从环境变量获取
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="管理员密钥不正确"
        )
    
    user = get_user(db, email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"用户 {email} 不存在"
        )
    
    # 返回用户信息（不包括密码哈希）
    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "email_verified": user.email_verified,
        "created_at": user.created_at,
        "has_password": bool(user.hashed_password),
        "google_id": user.google_id,
        "wechat_open_id": user.wechat_open_id
    }

@router.post("/debug/test-token")
async def debug_test_token(
    token: str = Body(..., embed=True),
    db: Session = Depends(get_db)
):
    """
    测试令牌解析（调试用）
    """
    try:
        # 手动尝试解析令牌
        print(f"手动测试令牌: {token[:15]}...")
        
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            print(f"令牌解码成功: {payload}")
            
            # 获取用户ID
            user_id = payload.get("sub")
            if not user_id:
                return {"success": False, "error": "令牌中没有用户ID"}
                
            # 查找用户
            from ..services.auth import get_user_by_id
            user = get_user_by_id(db, user_id)
            
            if user:
                return {
                    "success": True, 
                    "user_id": user_id,
                    "email": user.email,
                    "username": user.username
                }
            else:
                return {"success": False, "error": f"找不到ID为 {user_id} 的用户"}
                
        except Exception as e:
            return {"success": False, "error": f"令牌解码失败: {str(e)}"}
            
    except Exception as e:
        return {"success": False, "error": f"处理过程中出错: {str(e)}"}

@router.post("/debug/direct-login")
async def debug_direct_login(
    email: str = Body(...),
    password: str = Body(...),
    db: Session = Depends(get_db)
):
    """
    直接登录接口（调试用）
    """
    print(f"尝试直接登录：邮箱 {email}")
    
    # 查找用户
    user = get_user(db, email)
    if not user:
        return {"success": False, "error": f"找不到邮箱为 {email} 的用户"}
    
    # 验证密码
    if not verify_password(password, user.hashed_password):
        return {"success": False, "error": "密码不正确"}
    
    # 创建令牌
    access_token_expires = timedelta(minutes=60)  # 延长令牌有效期用于调试
    access_token, expires_in = create_access_token(
        data={"sub": user.id}, expires_delta=access_token_expires
    )
    
    return {
        "success": True,
        "user_id": user.id,
        "email": user.email,
        "username": user.username,
        "access_token": access_token,
        "expires_in": expires_in,
        "hashed_password": user.hashed_password[:10] + "..." # 只显示部分哈希用于验证
    } 