from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Optional, Literal
from jose import JWTError, jwt

from ..utils.database import get_db
from ..schemas.database_models import Order, User
from ..services.pay_wechat import create_native_order
from ..services.pay_alipay import create_page_pay
from ..services.auth import SECRET_KEY, ALGORITHM


router = APIRouter()
security = HTTPBearer(auto_error=False)

# 套餐配置
PACKAGES = {
    "detect_once": {
        "name": "1次查重",
        "credits": 1,
        "amount": 1.0,
        "unlimited": False,
        "days_valid": None,
        "description": "单次文本查重检测"
    },
    "ai_detect_once": {
        "name": "1次AI查询+查重",
        "credits": 1,
        "amount": 4.98,
        "unlimited": False,
        "days_valid": None,
        "description": "单次AI检测+文本查重"
    },
    "unlimited_1day": {
        "name": "1天不限次",
        "credits": 999999,  # 占位符，实际使用unlimited标志
        "amount": 19.98,
        "unlimited": True,
        "days_valid": 1,
        "description": "24小时内不限次数使用（查重+AI）"
    },
    "unlimited_1week": {
        "name": "1周不限次",
        "credits": 999999,  # 占位符，实际使用unlimited标志
        "amount": 39.98,
        "unlimited": True,
        "days_valid": 7,
        "description": "7天内不限次数使用（查重+AI）"
    }
}


def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """可选的用户认证，如果没有token或token无效则返回None"""
    if not credentials:
        return None
    
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
        
        user = db.query(User).filter(User.id == user_id).first()
        return user
    except JWTError:
        return None


class CreateOrderBody(BaseModel):
    channel: Literal["wechat", "alipay"]
    packageType: str  # 套餐类型: detect_once, ai_detect_once, unlimited_1day, unlimited_1week
    deviceId: Optional[str] = None
    # 保留向后兼容（旧的客户端可能还会传这些字段）
    credits: Optional[int] = None
    amount: Optional[float] = None


@router.post("/pay/create_order")
def create_order(body: CreateOrderBody, db: Session = Depends(get_db), current_user: Optional[User] = Depends(get_current_user_optional)):
    # 如果用户已登录，关联用户ID
    user_id = current_user.id if current_user else None
    
    # 获取套餐配置
    print(body.packageType)
    package = PACKAGES.get(body.packageType)
    print(package)
    if not package:
        # 向后兼容：如果没有packageType，使用旧的credits和amount字段
        print(body.credits, body.amount)
        if body.credits and body.amount:
            amount = body.amount
            credits = body.credits
            package_type = None
            description = f"充值{body.credits}次"
        else:
            raise HTTPException(status_code=400, detail="无效的套餐类型")
    else:
        amount = package["amount"]
        credits = package["credits"]
        package_type = body.packageType
        description = package["name"]
    
    order = Order(
        channel=body.channel, 
        amount=amount, 
        credits=credits,
        package_type=package_type,
        status="PENDING",
        user_id=user_id
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    if body.channel == "wechat":
        code_url, _ = create_native_order(amount, description, order.id)
        return {"orderId": order.id, "channel": "wechat", "qrcodeUrl": code_url}
    else:
        pay_url, _ = create_page_pay(amount, description, order.id)
        return {"orderId": order.id, "channel": "alipay", "payUrl": pay_url}


class PollBody(BaseModel):
    orderId: str


@router.get("/pay/packages")
def get_packages():
    """获取所有可用的付费套餐"""
    return {"packages": [
        {
            "packageType": pkg_type,
            "name": pkg_data["name"],
            "amount": pkg_data["amount"],
            "description": pkg_data.get("description", ""),
            "unlimited": pkg_data.get("unlimited", False),
            "daysValid": pkg_data.get("days_valid"),
        }
        for pkg_type, pkg_data in PACKAGES.items()
    ]}


@router.post("/pay/poll")
def poll_order(body: PollBody, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == body.orderId).first()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    resp = {"status": order.status}
    if order.status == "PAID" and order.license_token:
        resp["licenseToken"] = order.license_token
    return resp


@router.get("/pay/mock/wechat_qr/{order_id}")
def mock_wechat_pay(order_id: str, db: Session = Depends(get_db)):
    """MOCK模式：模拟微信支付成功"""
    import os
    if os.getenv('PAY_MOCK', 'true').lower() != 'true':
        raise HTTPException(status_code=404, detail="此端点仅在MOCK模式下可用")
    
    from ..services.license_service import issue_license
    
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    
    if order.status != "PAID":
        order.status = "PAID"
        
        # 根据套餐类型创建license
        unlimited = False
        days_valid = None
        if order.package_type and order.package_type in PACKAGES:
            package = PACKAGES[order.package_type]
            unlimited = package.get("unlimited", False)
            days_valid = package.get("days_valid")
        
        token = issue_license(
            db, 
            order.credits, 
            user_id=order.user_id,
            unlimited=unlimited,
            days_valid=days_valid
        )
        order.license_token = token
        db.add(order)
        db.commit()
    
    return {"message": "支付成功", "orderId": order_id}


@router.get("/pay/mock/alipay_url/{order_id}")
def mock_alipay_pay(order_id: str, db: Session = Depends(get_db)):
    """MOCK模式：模拟支付宝支付成功"""
    import os
    if os.getenv('PAY_MOCK', 'true').lower() != 'true':
        raise HTTPException(status_code=404, detail="此端点仅在MOCK模式下可用")
    
    from ..services.license_service import issue_license
    
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    
    if order.status != "PAID":
        order.status = "PAID"
        
        # 根据套餐类型创建license
        unlimited = False
        days_valid = None
        if order.package_type and order.package_type in PACKAGES:
            package = PACKAGES[order.package_type]
            unlimited = package.get("unlimited", False)
            days_valid = package.get("days_valid")
        
        token = issue_license(
            db, 
            order.credits, 
            user_id=order.user_id,
            unlimited=unlimited,
            days_valid=days_valid
        )
        order.license_token = token
        db.add(order)
        db.commit()
    
    return {"message": "支付成功", "orderId": order_id}


