#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
更新现有用户的免费使用次数限制
将所有用户的免费使用次数限制从100次更新为10次
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

def update_users_free_usage_limit():
    """更新所有现有用户的免费使用次数限制为10次"""
    print(f"开始更新用户免费使用次数限制: {DB_PATH}...")
    
    if not os.path.exists(DB_PATH):
        print(f"错误: 数据库文件不存在: {DB_PATH}")
        print("请在正确的目录下运行脚本或指定正确的数据库路径")
        return
    
    # 连接数据库
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 检查users表和free_usage_limit字段是否存在
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    if not cursor.fetchone():
        print("错误: 数据库中不存在users表")
        conn.close()
        return
    
    cursor.execute("PRAGMA table_info(users)")
    columns = {row[1] for row in cursor.fetchall()}
    if "free_usage_limit" not in columns:
        print("错误: users表中不存在free_usage_limit字段")
        conn.close()
        return
    
    # 更新所有用户的免费使用次数限制为10
    try:
        # 查询当前值为100的用户数量
        cursor.execute("SELECT COUNT(*) FROM users WHERE free_usage_limit = 100")
        count_100 = cursor.fetchone()[0]
        
        # 更新所有用户的免费使用次数限制
        cursor.execute("UPDATE users SET free_usage_limit = 10 WHERE free_usage_limit = 100")
        updated_rows = cursor.rowcount
        
        # 提交更改
        conn.commit()
        
        print(f"成功将{updated_rows}个用户的免费使用次数限制从100次更新为10次")
        
        # 查询更新后的情况
        cursor.execute("SELECT COUNT(*) FROM users WHERE free_usage_limit = 10")
        count_10 = cursor.fetchone()[0]
        
        print(f"当前数据库中有{count_10}个用户的免费使用次数限制为10次")
        
    except Exception as e:
        print(f"更新用户免费使用次数限制时出错: {str(e)}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    update_users_free_usage_limit()
    print("用户免费使用次数限制更新完成") 