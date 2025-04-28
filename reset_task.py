#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import os
import sqlite3
import shutil

# 任务ID
TASK_ID = "ae2bdaf6-4b5e-49cf-9339-9b28016c3bb3"
# 数据库文件路径
DB_PATH = "./backend/app.db"
# 上传文件夹路径
UPLOAD_DIR = "./backend/uploads"
# 备份文件路径
BACKUP_FILE = "./test_gpt.txt"  # 这里应该是原始文件的备份

def reset_task_status(task_id):
    """将任务状态重置为uploaded并还原文件"""
    print("正在重置任务 {} 的状态...".format(task_id))
    
    # 连接数据库
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 查询当前任务状态
    cursor.execute("SELECT status, filename FROM detection_tasks WHERE id = ?", (task_id,))
    result = cursor.fetchone()
    
    if not result:
        print("任务 {} 未找到".format(task_id))
        conn.close()
        return
    
    current_status, filename = result
    print("当前任务状态: {}".format(current_status))
    print("文件名: {}".format(filename))
    
    # 更新任务状态为uploaded
    cursor.execute("UPDATE detection_tasks SET status = 'uploaded' WHERE id = ?", (task_id,))
    conn.commit()
    
    # 删除相关的段落分析结果
    cursor.execute("DELETE FROM paragraph_results WHERE task_id = ?", (task_id,))
    conn.commit()
    
    print("任务状态已重置为 'uploaded'")
    print("已删除 {} 条段落分析结果".format(cursor.rowcount))
    
    # 关闭连接
    conn.close()
    
    # 还原文件
    task_dir = os.path.join(UPLOAD_DIR, task_id)
    if not os.path.exists(task_dir):
        os.makedirs(task_dir)
        print("创建任务目录: {}".format(task_dir))
    
    target_file = os.path.join(task_dir, filename)
    
    if os.path.exists(BACKUP_FILE):
        shutil.copy2(BACKUP_FILE, target_file)
        print("已复制备份文件到: {}".format(target_file))
    else:
        print("警告: 备份文件 {} 不存在，无法还原文件".format(BACKUP_FILE))

if __name__ == "__main__":
    # 如果命令行提供了任务ID，则使用提供的ID
    if len(sys.argv) > 1:
        task_id = sys.argv[1]
    else:
        task_id = TASK_ID
        
    reset_task_status(task_id) 