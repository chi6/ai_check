#!/usr/bin/env python
import requests
import json
import sys
import os

# 设置API基础URL
BASE_URL = "http://localhost:8000"  # 根据实际情况修改

def test_auth(email, password):
    """测试认证流程"""
    print(f"开始测试认证流程: {email}")
    
    # 登录获取令牌
    print("\n1. 获取访问令牌...")
    login_url = f"{BASE_URL}/api/user/token"
    login_data = {
        "username": email,
        "password": password
    }
    
    try:
        response = requests.post(login_url, data=login_data)
        if response.status_code != 200:
            print(f"登录失败 (状态码: {response.status_code}): {response.text}")
            return
        
        token_data = response.json()
        access_token = token_data.get("access_token")
        if not access_token:
            print("登录成功但未获取到令牌")
            return
            
        print(f"登录成功，获取到令牌: {access_token[:15]}...")
        
        # 测试获取用户信息
        print("\n2. 获取用户信息...")
        me_url = f"{BASE_URL}/api/user/me"
        headers = {"Authorization": f"Bearer {access_token}"}
        
        me_response = requests.get(me_url, headers=headers)
        if me_response.status_code != 200:
            print(f"获取用户信息失败 (状态码: {me_response.status_code}): {me_response.text}")
            # 输出完整请求和响应信息用于调试
            print(f"\n请求头: {headers}")
            return
        
        user_data = me_response.json()
        print(f"获取用户信息成功: {user_data.get('email')}")
        
        # 认证流程验证完成
        print("\n认证流程测试成功!")
        
    except Exception as e:
        print(f"测试过程中出错: {str(e)}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("用法: python test_auth.py <邮箱> <密码>")
        sys.exit(1)
    
    email = sys.argv[1]
    password = sys.argv[2]
    
    test_auth(email, password) 