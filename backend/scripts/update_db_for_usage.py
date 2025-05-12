#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
更新数据库，添加用户使用次数和订阅计划相关功能
"""

import sys
import os
import sqlite3

# 添加项目根目录到Python路径
script_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(script_dir)
sys.path.append(root_dir)

# 数据库文件路径
DB_PATH = os.path.join(root_dir, "app.db")
if not os.path.exists(DB_PATH):
    # 尝试其他可能的路径
    alt_path = os.path.join(os.path.dirname(root_dir), "app.db")
    if os.path.exists(alt_path):
        DB_PATH = alt_path
    else:
        print(f"警告: 无法找到数据库文件 {DB_PATH}")
        print(f"当前工作目录: {os.getcwd()}")
        print("请指定正确的数据库路径")

def update_db_for_usage():
    """更新数据库，添加用户使用次数和订阅计划相关功能"""
    print(f"开始更新数据库: {DB_PATH}...")
    
    if not os.path.exists(DB_PATH):
        print(f"错误: 数据库文件不存在: {DB_PATH}")
        print("请在正确的目录下运行脚本或指定正确的数据库路径")
        return
    
    # 连接数据库
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. 检查并添加用户表中的使用次数相关字段
    cursor.execute("PRAGMA table_info(users)")
    columns = {row[1] for row in cursor.fetchall()}
    
    if "usage_count" not in columns:
        print("添加 users.usage_count 字段")
        cursor.execute("ALTER TABLE users ADD COLUMN usage_count INTEGER DEFAULT 0")
    
    if "free_usage_limit" not in columns:
        print("添加 users.free_usage_limit 字段")
        cursor.execute("ALTER TABLE users ADD COLUMN free_usage_limit INTEGER DEFAULT 10")
    
    # 2. 创建订阅计划表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS subscription_plans (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT,
        plan_type TEXT NOT NULL,
        price REAL NOT NULL,
        currency TEXT DEFAULT 'CNY',
        duration_days INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_active BOOLEAN DEFAULT 1
    )
    """)
    
    # 3. 添加支付表中的plan_id字段
    cursor.execute("PRAGMA table_info(payments)")
    payment_columns = {row[1] for row in cursor.fetchall()}
    
    if "plan_id" not in payment_columns:
        print("添加 payments.plan_id 字段")
        cursor.execute("ALTER TABLE payments ADD COLUMN plan_id TEXT")
    
    # 4. 更新订阅表，修改plan_id字段
    cursor.execute("PRAGMA table_info(subscriptions)")
    subscription_columns = {row[1] for row in cursor.fetchall()}
    
    # 由于SQLite不支持直接修改字段或添加外键约束，我们需要重建表
    # 如果需要保留数据，这一步需要更复杂的处理
    
    # 提交更改
    conn.commit()
    conn.close()
    
    print("数据库更新完成")

if __name__ == "__main__":
    update_db_for_usage()
    
    # 提示初始化订阅计划
    print("\n请运行以下命令初始化订阅计划:")
    print("python backend/scripts/init_subscription_plans.py") 