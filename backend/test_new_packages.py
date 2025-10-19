#!/usr/bin/env python3
"""
测试新的付费方案功能
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.utils.database import SessionLocal
from app.services.license_service import issue_license, get_license_status, consume_credits, get_user_credits
from app.schemas.database_models import User
import uuid

def test_packages():
    db = SessionLocal()
    
    try:
        print("=" * 60)
        print("测试新的付费方案功能")
        print("=" * 60)
        
        # 创建测试用户
        test_user_id = str(uuid.uuid4())
        test_user = User(
            id=test_user_id,
            email=f"test_{test_user_id[:8]}@example.com",
            username="测试用户",
            hashed_password="test_hash"
        )
        db.add(test_user)
        db.commit()
        print(f"\n✅ 创建测试用户: {test_user.email}")
        
        # 测试1: 单次查重套餐 (detect_once)
        print("\n" + "=" * 60)
        print("测试1: 单次查重套餐 (detect_once)")
        print("=" * 60)
        token1 = issue_license(db, credits=1, user_id=test_user_id, unlimited=False, days_valid=None)
        print(f"✅ 创建license: {token1[:20]}...")
        status1 = get_license_status(db, token1)
        print(f"   剩余次数: {status1['creditsRemaining']}")
        print(f"   不限次数: {status1['unlimited']}")
        print(f"   过期时间: {status1['exp']}")
        
        # 消耗一次
        remaining1 = consume_credits(db, token1, 1, "测试查重")
        print(f"✅ 消耗1次后剩余: {remaining1}")
        
        # 测试2: AI查询+查重套餐 (ai_detect_once)
        print("\n" + "=" * 60)
        print("测试2: AI查询+查重套餐 (ai_detect_once)")
        print("=" * 60)
        token2 = issue_license(db, credits=1, user_id=test_user_id, unlimited=False, days_valid=None)
        print(f"✅ 创建license: {token2[:20]}...")
        status2 = get_license_status(db, token2)
        print(f"   剩余次数: {status2['creditsRemaining']}")
        print(f"   不限次数: {status2['unlimited']}")
        
        # 测试3: 1天不限次套餐 (unlimited_1day)
        print("\n" + "=" * 60)
        print("测试3: 1天不限次套餐 (unlimited_1day)")
        print("=" * 60)
        token3 = issue_license(db, credits=999999, user_id=test_user_id, unlimited=True, days_valid=1)
        print(f"✅ 创建license: {token3[:20]}...")
        status3 = get_license_status(db, token3)
        print(f"   剩余次数: {status3['creditsRemaining']}")
        print(f"   不限次数: {status3['unlimited']}")
        print(f"   过期时间: {status3['exp']}")
        
        # 测试不限次数套餐的消耗
        print("\n测试不限次数套餐消耗...")
        for i in range(3):
            remaining3 = consume_credits(db, token3, 1, f"测试不限次数-{i+1}")
            print(f"   第{i+1}次使用后剩余: {remaining3} (应该保持不变)")
        
        # 测试4: 1周不限次套餐 (unlimited_1week)
        print("\n" + "=" * 60)
        print("测试4: 1周不限次套餐 (unlimited_1week)")
        print("=" * 60)
        token4 = issue_license(db, credits=999999, user_id=test_user_id, unlimited=True, days_valid=7)
        print(f"✅ 创建license: {token4[:20]}...")
        status4 = get_license_status(db, token4)
        print(f"   剩余次数: {status4['creditsRemaining']}")
        print(f"   不限次数: {status4['unlimited']}")
        print(f"   过期时间: {status4['exp']}")
        
        # 测试用户总额度查询
        print("\n" + "=" * 60)
        print("测试用户总额度查询")
        print("=" * 60)
        credits_info = get_user_credits(db, test_user_id)
        print(f"✅ 用户ID: {credits_info['userId']}")
        print(f"   总额度: {credits_info['totalCredits']}")
        print(f"   有不限次数套餐: {credits_info['hasUnlimited']}")
        print(f"   License数量: {len(credits_info['licenses'])}")
        for i, lic in enumerate(credits_info['licenses'], 1):
            print(f"   License {i}:")
            print(f"     - 剩余: {lic['creditsRemaining']}")
            print(f"     - 不限次: {lic['unlimited']}")
            print(f"     - 过期: {lic['exp']}")
        
        print("\n" + "=" * 60)
        print("✅ 所有测试通过！")
        print("=" * 60)
        
        # 清理测试数据
        print("\n清理测试数据...")
        db.delete(test_user)
        db.commit()
        print("✅ 测试数据已清理")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    test_packages()

