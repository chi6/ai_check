#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
初始化订阅计划数据
"""

import sys
import os

# 添加项目根目录到Python路径
script_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(script_dir)
sys.path.append(root_dir)

try:
    from app.utils.database import SessionLocal
    from app.schemas.database_models import SubscriptionPlan, PLAN_TYPE_SINGLE_USE, PLAN_TYPE_DAILY, PLAN_TYPE_MONTHLY
except ImportError:
    # 尝试另一种导入路径
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from backend.app.utils.database import SessionLocal
    from backend.app.schemas.database_models import SubscriptionPlan, PLAN_TYPE_SINGLE_USE, PLAN_TYPE_DAILY, PLAN_TYPE_MONTHLY

def init_subscription_plans():
    """初始化订阅计划"""
    print("开始初始化订阅计划...")
    
    db = SessionLocal()
    try:
        # 检查是否已存在计划
        existing_plans = db.query(SubscriptionPlan).all()
        if existing_plans:
            print(f"已存在 {len(existing_plans)} 个订阅计划，跳过初始化")
            return
        
        # 创建单次使用计划
        single_use_plan = SubscriptionPlan(
            name="单次使用",
            description="充值5元获取一次检测机会",
            plan_type=PLAN_TYPE_SINGLE_USE,
            price=5.0,
            currency="CNY",
            duration_days=0  # 0表示不是订阅，是单次购买
        )
        
        # 创建日订阅计划
        daily_plan = SubscriptionPlan(
            name="日订阅",
            description="一天内无限次使用，18元",
            plan_type=PLAN_TYPE_DAILY,
            price=18.0,
            currency="CNY",
            duration_days=1  # 订阅持续1天
        )
        
        # 创建月订阅计划
        monthly_plan = SubscriptionPlan(
            name="月订阅",
            description="一个月内无限次使用，200元",
            plan_type=PLAN_TYPE_MONTHLY,
            price=200.0,
            currency="CNY",
            duration_days=30  # 订阅持续30天
        )
        
        # 添加到数据库
        db.add(single_use_plan)
        db.add(daily_plan)
        db.add(monthly_plan)
        db.commit()
        
        print("成功创建3个订阅计划")
        
    except Exception as e:
        print(f"初始化订阅计划时出错: {str(e)}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    init_subscription_plans()
    print("订阅计划初始化完成") 