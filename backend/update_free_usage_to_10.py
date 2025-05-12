#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将免费使用次数从100次更新为10次的一键执行脚本
这个脚本会:
1. 更新数据库结构中的默认值为10
2. 更新现有用户的免费使用次数限制为10
"""

import os
import sys
import subprocess

def main():
    print("开始更新免费使用次数从100次到10次...")
    
    # 获取当前脚本目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    print("\n1. 更新数据库结构中的默认值...")
    try:
        subprocess.run([sys.executable, "scripts/update_db_for_usage.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"更新数据库时出错: {e}")
        return
    
    print("\n2. 更新现有用户的免费使用次数限制...")
    try:
        subprocess.run([sys.executable, "scripts/update_existing_users_limit.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"更新用户免费使用次数时出错: {e}")
        return
    
    print("\n更新完成!")
    print("现在每个新用户和现有用户都只有10次免费使用机会")
    print("\n如果需要重新初始化订阅计划，请运行:")
    print("python backend/scripts/init_subscription_plans.py")

if __name__ == "__main__":
    main() 