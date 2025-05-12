import sys
import os
import requests
import json
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.payment_service import (
    create_stripe_payment,
    confirm_stripe_payment,
    create_wechat_payment,
    create_alipay_payment
)
from app.utils.database import get_db, SessionLocal
from app.schemas.database_models import User, Payment

def test_stripe_payment():
    """测试Stripe支付流程"""
    print("\n=== 测试Stripe支付 ===")
    
    # 获取数据库会话
    db = SessionLocal()
    
    try:
        # 查询第一个用户用于测试
        user = db.query(User).first()
        if not user:
            print("错误: 数据库中没有用户")
            return
        
        # 测试参数
        amount = 99.99
        currency = "usd"
        payment_method_id = "pm_card_visa"  # Stripe测试卡
        return_url = "http://localhost:3000/payment/result"
        
        print(f"创建支付，金额: {amount} {currency}")
        
        # 创建支付
        payment_result = create_stripe_payment(
            db, user.id, amount, currency, payment_method_id, return_url
        )
        
        print(f"支付创建结果: {json.dumps(payment_result, default=str, indent=2)}")
        
        # 如果需要确认
        if payment_result.get("status") == "requires_action":
            print("支付需要额外操作，通常在前端处理...")
        elif payment_result.get("status") == "pending":
            # 确认支付
            payment_id = payment_result.get("payment_id")
            stripe_payment_id = payment_result.get("client_secret").split("_secret")[0]
            
            confirm_result = confirm_stripe_payment(db, payment_id, stripe_payment_id)
            print(f"确认支付结果: {json.dumps(confirm_result, default=str, indent=2)}")
        
        # 检查支付记录
        payment = db.query(Payment).filter(Payment.id == payment_result.get("payment_id")).first()
        print(f"支付记录状态: {payment.status}")
        
    except Exception as e:
        print(f"测试过程中发生错误: {str(e)}")
    finally:
        db.close()

def test_wechat_payment():
    """测试微信支付流程"""
    print("\n=== 测试微信支付 ===")
    
    # 获取数据库会话
    db = SessionLocal()
    
    try:
        # 查询第一个用户用于测试
        user = db.query(User).first()
        if not user:
            print("错误: 数据库中没有用户")
            return
        
        # 测试参数
        amount = 99.99
        product_description = "AI论文检测高级会员"
        
        print(f"创建微信支付，金额: {amount} CNY")
        
        # 创建支付
        payment_result = create_wechat_payment(
            db, user.id, amount, product_description
        )
        
        print(f"微信支付创建结果: {json.dumps(payment_result, default=str, indent=2)}")
        
        # 在实际应用中，此时会展示二维码让用户扫码支付
        # 之后接收微信支付的异步通知来更新支付状态
        print(f"请用微信扫描二维码进行支付: {payment_result.get('qr_code_url')}")
        
    except Exception as e:
        print(f"测试过程中发生错误: {str(e)}")
    finally:
        db.close()

def test_alipay_payment():
    """测试支付宝支付流程"""
    print("\n=== 测试支付宝支付 ===")
    
    # 获取数据库会话
    db = SessionLocal()
    
    try:
        # 查询第一个用户用于测试
        user = db.query(User).first()
        if not user:
            print("错误: 数据库中没有用户")
            return
        
        # 测试参数
        amount = 99.99
        product_description = "AI论文检测高级会员"
        return_url = "http://localhost:3000/payment/result"
        
        print(f"创建支付宝支付，金额: {amount} CNY")
        
        # 创建支付
        payment_result = create_alipay_payment(
            db, user.id, amount, product_description, return_url
        )
        
        print(f"支付宝支付创建结果: {json.dumps(payment_result, default=str, indent=2)}")
        
        # 在实际应用中，此时会重定向用户到支付宝支付页面
        print(f"支付链接: {payment_result.get('pay_url')}")
        
    except Exception as e:
        print(f"测试过程中发生错误: {str(e)}")
    finally:
        db.close()

def main():
    """运行所有测试"""
    print("开始支付系统测试...", datetime.now())
    
    # 测试Stripe支付
    test_stripe_payment()
    
    # 测试微信支付
    # test_wechat_payment()
    
    # 测试支付宝支付
    # test_alipay_payment()
    
    print("\n支付系统测试完成!", datetime.now())

if __name__ == "__main__":
    main() 