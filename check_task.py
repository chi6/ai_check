#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import os
import sqlite3

# 任务ID
TASK_ID = "ae2bdaf6-4b5e-49cf-9339-9b28016c3bb3"
# 数据库文件路径
DB_PATH = "./backend/app.db"

def check_task_status(task_id):
    """查询特定任务的状态"""
    print("正在查询任务 {} 的状态...".format(task_id))
    
    # 连接数据库
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # 启用行工厂，结果可以通过列名访问
    cursor = conn.cursor()
    
    # 查询任务
    cursor.execute("SELECT * FROM detection_tasks WHERE id = ?", (task_id,))
    task = cursor.fetchone()
    
    if not task:
        print("任务 {} 未找到".format(task_id))
        conn.close()
        return
    
    # 打印任务信息
    print("任务信息:")
    print("  ID: {}".format(task['id']))
    print("  文件名: {}".format(task['filename']))
    print("  状态: {}".format(task['status']))
    print("  AI生成内容百分比: {}".format(task['ai_generated_percentage']))
    print("  创建时间: {}".format(task['created_at']))
    print("  更新时间: {}".format(task['updated_at']))
    
    # 查询段落结果
    cursor.execute("SELECT COUNT(*) FROM paragraph_results WHERE task_id = ?", (task_id,))
    paragraph_count = cursor.fetchone()[0]
    print("  段落分析结果数量: {}".format(paragraph_count))
    
    # 关闭连接
    conn.close()

if __name__ == "__main__":
    # 如果命令行提供了任务ID，则使用提供的ID
    if len(sys.argv) > 1:
        task_id = sys.argv[1]
    else:
        task_id = TASK_ID
        
    check_task_status(task_id) 