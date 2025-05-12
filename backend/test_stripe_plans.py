#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sqlite3
import os
import json

def test_stripe_plans():
    # 获取数据库路径
    db_path = os.path.join(os.path.dirname(__file__), 'app.db')
    
    # 连接数据库
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # 使结果以字典形式返回
    cursor = conn.cursor()
    
    # 查询订阅计划表
    cursor.execute("SELECT * FROM subscription_plans")
    plans = [dict(row) for row in cursor.fetchall()]
    
    if not plans:
        print("数据库中没有找到订阅计划")
        return
    
    print(f"找到 {len(plans)} 个订阅计划:")
    for i, plan in enumerate(plans, 1):
        print(f"\n计划 {i}:")
        print(f"  ID: {plan.get('id', 'N/A')}")
        print(f"  名称: {plan.get('name', 'N/A')}")
        print(f"  描述: {plan.get('description', 'N/A')}")
        print(f"  类型: {plan.get('plan_type', 'N/A')}")
        print(f"  价格: {plan.get('price', 'N/A')} {plan.get('currency', 'USD')}")
        print(f"  持续天数: {plan.get('duration_days', 'N/A')}")
        print(f"  使用次数: {plan.get('usage_credits', 1)}")
        print(f"  Stripe链接: {plan.get('stripe_link', 'N/A')}")
    
    # 检查数据库表结构
    cursor.execute("PRAGMA table_info(subscription_plans)")
    columns = {row[1] for row in cursor.fetchall()}
    
    print("\n订阅计划表的列:")
    for col in sorted(columns):
        print(f"  - {col}")
    
    # 关闭数据库连接
    conn.close()

if __name__ == "__main__":
    test_stripe_plans() 