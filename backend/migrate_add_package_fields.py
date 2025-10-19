#!/usr/bin/env python3
"""
数据库迁移脚本：添加套餐相关字段
- orders表添加package_type列
- licenses表添加unlimited列
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
        
        # 检查并添加 orders 表的 package_type 列
        cursor.execute("PRAGMA table_info(orders)")
        orders_columns = [col[1] for col in cursor.fetchall()]
        
        if 'package_type' not in orders_columns:
            print("✅ 向 orders 表添加 package_type 列...")
            cursor.execute("""
                ALTER TABLE orders 
                ADD COLUMN package_type TEXT
            """)
            print("   ✓ orders.package_type 列已添加")
        else:
            print("⏭️  orders 表已有 package_type 列，跳过")
        
        # 检查并添加 licenses 表的 unlimited 列
        cursor.execute("PRAGMA table_info(licenses)")
        licenses_columns = [col[1] for col in cursor.fetchall()]
        
        if 'unlimited' not in licenses_columns:
            print("✅ 向 licenses 表添加 unlimited 列...")
            cursor.execute("""
                ALTER TABLE licenses 
                ADD COLUMN unlimited BOOLEAN DEFAULT 0
            """)
            print("   ✓ licenses.unlimited 列已添加")
        else:
            print("⏭️  licenses 表已有 unlimited 列，跳过")
        
        conn.commit()
        print("\n🎉 数据库迁移成功完成！")
        print("\n新功能说明：")
        print("  • 支持4种套餐类型：")
        print("    - detect_once: 1次查重 (¥2)")
        print("    - ai_detect_once: 1次AI查询+查重 (¥9)")
        print("    - unlimited_1day: 1天不限次 (¥41)")
        print("    - unlimited_1week: 1周不限次 (¥87)")
        
    except sqlite3.Error as e:
        print(f"❌ 数据库迁移失败: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_database()

