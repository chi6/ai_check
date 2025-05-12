#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一键安装使用次数限制和订阅功能
这个脚本会:
1. 更新数据库结构
2. 初始化订阅计划
"""

import os
import sys
import subprocess

def main():
    print("开始安装使用次数限制和订阅功能...")
    
    # 获取当前脚本目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    print("\n1. 更新数据库结构...")
    try:
        subprocess.run([sys.executable, "scripts/update_db_for_usage.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"更新数据库时出错: {e}")
        return
    
    print("\n2. 初始化订阅计划...")
    try:
        subprocess.run([sys.executable, "scripts/init_subscription_plans.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"初始化订阅计划时出错: {e}")
        return
    
    print("\n安装完成!")
    print("现在您可以启动应用程序，使用次数限制和订阅功能已激活。")
    print("\n使用方法:")
    print("1. 每个新用户有10次免费使用机会")
    print("2. 用户可以购买单次使用(5元)或订阅(日18元/月200元)")
    print("3. 使用 /api/user/usage 接口获取用户使用情况")
    print("4. 使用 /api/plans 接口获取可用订阅计划")
    print("5. 使用 /api/checkout 接口购买计划")

if __name__ == "__main__":
    main() 