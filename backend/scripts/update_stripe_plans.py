#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import sqlite3
import uuid
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 导入数据库模型常量
from app.schemas.database_models import (
    PLAN_TYPE_SINGLE_USE,
    PLAN_TYPE_DAILY
)

def generate_uuid():
    """生成UUID"""
    return str(uuid.uuid4())

def update_stripe_plans():
    """更新数据库中的Stripe支付计划"""
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'app.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 先删除所有现有的计划
    cursor.execute("DELETE FROM subscription_plans")
    
    # 创建新的Stripe支付计划
    plans = [
        # 一美元一次检测
        {
            "id": generate_uuid(),
            "name": "One AI detection - $1",
            "description": "Purchase a single AI detection check for $1",
            "plan_type": PLAN_TYPE_SINGLE_USE,
            "price": 1.0,
            "currency": "USD",
            "duration_days": 0,  # 不是订阅，是单次购买
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "is_active": 1,
            "stripe_link": "https://buy.stripe.com/bIYcPz53W8aM0JaaEF"
        },
        # 5美元十次检测
        {
            "id": generate_uuid(),
            "name": "10 AI detections - $5",
            "description": "Purchase 10 AI detection checks for $5",
            "plan_type": PLAN_TYPE_SINGLE_USE,
            "price": 5.0,
            "currency": "USD",
            "duration_days": 0,  # 单次购买10次使用权
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "is_active": 1,
            "stripe_link": "https://buy.stripe.com/eVabLv2VO62EbnO5kk",
            "usage_credits": 10  # 新增字段，表示购买后获得的使用次数
        },
        # 10美元100次检测
        {
            "id": generate_uuid(),
            "name": "100 AI detections - $10",
            "description": "Purchase 100 AI detection checks for $10",
            "plan_type": PLAN_TYPE_SINGLE_USE,
            "price": 10.0,
            "currency": "USD",
            "duration_days": 0,  # 单次购买100次使用权
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "is_active": 1,
            "stripe_link": "https://buy.stripe.com/4gw8zjdAsdv63VmcMO",
            "usage_credits": 100  # 新增字段，表示购买后获得的使用次数
        }
    ]
    
    # 检查表结构是否有stripe_link字段
    cursor.execute("PRAGMA table_info(subscription_plans)")
    columns = {row[1] for row in cursor.fetchall()}
    
    # 如果没有stripe_link字段，添加该字段
    if "stripe_link" not in columns:
        cursor.execute("ALTER TABLE subscription_plans ADD COLUMN stripe_link TEXT")
    
    # 如果没有usage_credits字段，添加该字段
    if "usage_credits" not in columns:
        cursor.execute("ALTER TABLE subscription_plans ADD COLUMN usage_credits INTEGER DEFAULT 1")
    
    # 插入新的计划数据
    for plan in plans:
        cursor.execute("""
        INSERT INTO subscription_plans 
        (id, name, description, plan_type, price, currency, duration_days, 
         created_at, updated_at, is_active, stripe_link, usage_credits)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            plan["id"],
            plan["name"],
            plan["description"],
            plan["plan_type"],
            plan["price"],
            plan["currency"],
            plan["duration_days"],
            plan["created_at"],
            plan["updated_at"],
            plan["is_active"],
            plan["stripe_link"],
            plan.get("usage_credits", 1)  # 默认为1次
        ))
    
    # 提交更改
    conn.commit()
    print(f"成功更新{len(plans)}个Stripe支付计划")
    
    # 验证数据已经插入
    cursor.execute("SELECT * FROM subscription_plans")
    results = cursor.fetchall()
    print(f"数据库中现有{len(results)}个订阅计划")
    
    conn.close()

if __name__ == "__main__":
    update_stripe_plans() 