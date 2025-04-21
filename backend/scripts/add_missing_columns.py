#!/usr/bin/env python3
import sys
import os
import sqlite3

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 数据库文件路径
DB_PATH = "./app.db"

def add_missing_columns():
    """添加检测任务表中缺失的列"""
    print("开始修复数据库...")
    
    # 连接数据库
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 检查detection_tasks表结构
    cursor.execute("PRAGMA table_info(detection_tasks)")
    columns = {row[1] for row in cursor.fetchall()}
    
    # 添加缺失的列
    missing_columns = []
    
    if "overall_perplexity" not in columns:
        missing_columns.append(("overall_perplexity", "FLOAT"))
    
    if "overall_burstiness" not in columns:
        missing_columns.append(("overall_burstiness", "FLOAT"))
    
    if "overall_syntax_analysis" not in columns:
        missing_columns.append(("overall_syntax_analysis", "TEXT"))
    
    if "overall_coherence_analysis" not in columns:
        missing_columns.append(("overall_coherence_analysis", "TEXT"))
    
    if "overall_style_analysis" not in columns:
        missing_columns.append(("overall_style_analysis", "TEXT"))
    
    # 执行添加列的操作
    for column_name, column_type in missing_columns:
        print(f"添加列: {column_name} ({column_type})")
        try:
            cursor.execute(f"ALTER TABLE detection_tasks ADD COLUMN {column_name} {column_type}")
        except sqlite3.OperationalError as e:
            print(f"添加列 {column_name} 时出错: {str(e)}")
    
    # 提交更改
    conn.commit()
    conn.close()
    
    if missing_columns:
        print(f"成功添加了 {len(missing_columns)} 个缺失的列")
    else:
        print("没有发现缺失的列")
    
    print("数据库修复完成")

if __name__ == "__main__":
    add_missing_columns() 