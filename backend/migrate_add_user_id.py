#!/usr/bin/env python3
"""
数据库迁移脚本：添加 user_id 列到 orders 和 licenses 表
"""
import sqlite3
import os
import sys

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(__file__))

def migrate_database():
    # 数据库文件路径
    db_path = os.path.join(os.path.dirname(__file__), 'app.db')
    
    if not os.path.exists(db_path):
        print(f"❌ 数据库文件不存在: {db_path}")
        print("提示：首次运行时会自动创建数据库，无需迁移。")
        return
    
    print(f"📁 数据库文件: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("\n开始数据库迁移...")
        
        # 检查并添加 orders 表的 user_id 列
        cursor.execute("PRAGMA table_info(orders)")
        orders_columns = [col[1] for col in cursor.fetchall()]
        
        if 'user_id' not in orders_columns:
            print("✅ 向 orders 表添加 user_id 列...")
            cursor.execute("""
                ALTER TABLE orders 
                ADD COLUMN user_id TEXT
            """)
            print("   ✓ orders.user_id 列已添加")
        else:
            print("⏭️  orders 表已有 user_id 列，跳过")
        
        # 检查并添加 licenses 表的 user_id 列
        cursor.execute("PRAGMA table_info(licenses)")
        licenses_columns = [col[1] for col in cursor.fetchall()]
        
        if 'user_id' not in licenses_columns:
            print("✅ 向 licenses 表添加 user_id 列...")
            cursor.execute("""
                ALTER TABLE licenses 
                ADD COLUMN user_id TEXT
            """)
            print("   ✓ licenses.user_id 列已添加")
        else:
            print("⏭️  licenses 表已有 user_id 列，跳过")
        
        conn.commit()
        print("\n🎉 数据库迁移成功完成！")
        
    except sqlite3.Error as e:
        print(f"❌ 数据库迁移失败: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_database()

