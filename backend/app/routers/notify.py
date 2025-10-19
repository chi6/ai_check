from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import Optional

from ..utils.database import get_db
from ..schemas.database_models import Order
from ..services.license_service import issue_license, revoke_license_by_token
from ..services.pay_wechat import verify_and_parse_notify as wechat_verify
from ..services.pay_alipay import verify_notify as alipay_verify
from .pay import PACKAGES


router = APIRouter()


@router.post("/pay/notify/wechat")
async def wechat_notify(request: Request, db: Session = Depends(get_db)):
    # MOCK或正式验签
    body_bytes = await request.body()
    result = wechat_verify(request.headers, body_bytes)
    print("wechat_verify result:", result)
    # 从body_bytes解析JSON，而不是再次读取request
    import json
    payload = json.loads(body_bytes.decode('utf-8'))
    print("payload:", payload)
    # 如果是正式微信回调，从resource中获取订单号
    if result and isinstance(result, dict) and 'resource' in result and result['resource'] is not None:
        resource = result['resource']
        print("resource:", resource)
        # 如果resource是字符串，需要解析为字典
        if isinstance(resource, str):
            resource = json.loads(resource)
        order_id = resource.get("out_trade_no")
    else:
        # MOCK模式或直接传递的情况
        order_id = payload.get("orderId") or payload.get("out_trade_no")
    print("order_id:", order_id)
    # 将32位无连字符的out_trade_no回转为标准UUID格式（若匹配）
    if order_id and len(order_id) == 32 and '-' not in order_id:
        try:
            import uuid
            order_id = str(uuid.UUID(order_id))
        except Exception:
            pass
    
    credits = payload.get("credits")
    if not order_id:
        raise HTTPException(status_code=400, detail="缺少orderId")

    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    if order.status == "PAID":
        return {"code": "SUCCESS"}

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
        credits or order.credits, 
        user_id=order.user_id,
        unlimited=unlimited,
        days_valid=days_valid
    )
    order.license_token = token
    db.add(order)
    db.commit()
    return {"code": "SUCCESS"}


@router.post("/pay/notify/alipay")
async def alipay_notify(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    if not alipay_verify(form):
        raise HTTPException(status_code=400, detail="验签失败")
    order_id = form.get("out_trade_no")
    if not order_id:
        raise HTTPException(status_code=400, detail="缺少out_trade_no")
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    if order.status == "PAID":
        return "success"

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
    return "success"


@router.post("/pay/refund/wechat")
async def wechat_refund_notify(request: Request, db: Session = Depends(get_db)):
    body_bytes = await request.body()
    _ = wechat_verify(request.headers, body_bytes)
    payload = await request.json()
    order_id = payload.get("orderId") or payload.get("out_trade_no")
    if order_id and len(order_id) == 32 and '-' not in order_id:
        try:
            import uuid
            order_id = str(uuid.UUID(order_id))
        except Exception:
            pass
    if not order_id:
        raise HTTPException(status_code=400, detail="缺少订单号")
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    order.status = "REFUNDED"
    if order.license_token:
        try:
            revoke_license_by_token(db, order.license_token)
        except Exception:
            pass
    db.add(order)
    db.commit()
    return {"code": "SUCCESS"}


@router.post("/pay/refund/alipay")
async def alipay_refund_notify(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    if not alipay_verify(form):
        raise HTTPException(status_code=400, detail="验签失败")
    order_id = form.get("out_trade_no")
    if not order_id:
        raise HTTPException(status_code=400, detail="缺少订单号")
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    order.status = "REFUNDED"
    if order.license_token:
        try:
            revoke_license_by_token(db, order.license_token)
        except Exception:
            pass
    db.add(order)
    db.commit()
    return "success"


