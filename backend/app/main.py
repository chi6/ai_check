from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from .routers import upload, detect, report, user, payment
import matplotlib
import os
import subprocess
import sys
from .utils.database import engine, get_db
from .utils.init_db import init_db
from .utils.font_utils import init_fonts
# 修改导入路径，使用相对路径导入
try:
    # 尝试从相对路径导入
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from backend.scripts.init_subscription_plans import init_subscription_plans
except ImportError:
    print("警告: 无法导入订阅计划初始化脚本，订阅计划可能需要手动初始化")
    # 创建一个空函数作为替代
    def init_subscription_plans():
        print("跳过订阅计划初始化")
import logging

# 确保可以导入字体工具模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 下载NLTK数据
try:
    import nltk
    nltk.download('punkt', quiet=True)
    print("NLTK punkt 数据已下载")
except Exception as e:
    print(f"NLTK数据下载失败: {str(e)}")

# 使用字体工具函数设置中文字体
try:
    from app.utils.font_utils import setup_chinese_fonts
    setup_chinese_fonts()
except Exception as e:
    print(f"配置中文字体失败: {str(e)}")
    # 如果配置失败，使用基本设置
    matplotlib.use('Agg')
    print("使用默认字体设置")

# 创建/更新数据库表
from .schemas.database_models import Base
try:
    Base.metadata.create_all(bind=engine)
    print("数据库表创建/更新成功")
except Exception as e:
    print(f"数据库表创建/更新失败: {str(e)}")

app = FastAPI(
    title="AI论文检测工具",
    description="检测论文中AI生成内容的比例",
    version="1.0.0"
)

# CORS设置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应限制为前端域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加一个中间件来处理身份验证错误
@app.middleware("http")
async def auth_middleware(request, call_next):
    response = await call_next(request)
    
    # 如果是认证错误，添加更详细的日志
    if response.status_code == 401:
        print(f"认证错误: 路径={request.url.path}, 方法={request.method}")
        print(f"请求头: {request.headers.get('Authorization', '无认证头')}")
    
    return response

# 包含路由
app.include_router(upload.router, prefix="/api", tags=["上传"])
app.include_router(detect.router, prefix="/api", tags=["检测"])
app.include_router(report.router, prefix="/api", tags=["报告"])
app.include_router(user.router, prefix="/api", tags=["用户"])
app.include_router(payment.router, prefix="/api", tags=["支付"])

# 更新报告路由API文档
for route in report.router.routes:
    if "get_report" in str(route.endpoint):
        route.description = """
        生成AI内容检测报告 (支持多种格式)
        
        支持以下格式:
        - json: JSON格式响应
        - html: HTML格式报告 (默认)
        - text: 纯文本格式报告
        
        可配置选项:
        - includeChart (bool): 是否包含图表
        - includeDetails (bool): 是否包含详细分析结果
        - includeOriginalText (bool): 是否包含原始文本内容
        - includeMetadata (bool): 是否包含元数据
        - includeHeaderFooter (bool): 是否包含页眉和页脚
        """

@app.on_event("startup")
async def startup_event():
    print("启动应用...")
    # 初始化数据库
    init_db()
    # 初始化订阅计划
    init_subscription_plans()
    # 设置日志级别
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    
    # 初始化字体
    try:
        init_fonts()
    except Exception as e:
        print(f"初始化字体时出错: {str(e)}")
        
    # 显示离线模式状态
    if os.environ.get("OFFLINE_MODE", "false").lower() == "true":
        print("\n-----\n\n运行在离线模式，将只使用本地模型\n\n-----\n")
    
    # 初始化支付环境变量
    payment_config = {
        "stripe": bool(os.environ.get("STRIPE_API_KEY")),
        "wechat": bool(os.environ.get("WECHAT_PAY_APPID")),
        "alipay": bool(os.environ.get("ALIPAY_APPID"))
    }
    print(f"\n支付配置状态: {payment_config}\n")

@app.get("/")
async def root():
    return {"message": "欢迎使用AI论文检测工具API"}

@app.get("/auth-guide")
async def auth_guide():
    """提供前端认证指南"""
    return {
        "message": "前端认证指南",
        "login_endpoint": "/api/user/token",
        "login_method": "POST",
        "login_body": {
            "username": "your_email@example.com",
            "password": "your_password"
        },
        "login_response": {
            "access_token": "jwt_token_here",
            "token_type": "bearer",
            "expires_in": 86400,
            "user": {
                "id": "user_id",
                "email": "user_email",
                "username": "username"
            }
        },
        "authenticated_requests": {
            "header": "Authorization: Bearer your_access_token",
            "example": "fetch('/api/user/me', { headers: { 'Authorization': 'Bearer ' + access_token } })"
        },
        "common_issues": [
            "确保令牌前缀为'Bearer '（注意空格）",
            "确保令牌未过期",
            "检查请求URL是否正确",
            "确保跨域请求设置正确"
        ]
    }

@app.get("/auth-test", response_class=HTMLResponse)
async def auth_test_page():
    """提供一个简单的HTML页面用于测试认证"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>认证测试页面</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
            .card { border: 1px solid #ddd; border-radius: 8px; padding: 20px; margin-bottom: 20px; }
            button { padding: 8px 16px; background-color: #4CAF50; color: white; border: none; border-radius: 4px; cursor: pointer; }
            input { padding: 8px; margin: 5px 0; width: 100%; box-sizing: border-box; }
            pre { background-color: #f5f5f5; padding: 10px; border-radius: 4px; overflow-x: auto; }
        </style>
    </head>
    <body>
        <h1>认证测试工具</h1>
        
        <div class="card">
            <h2>登录</h2>
            <div>
                <input type="text" id="email" placeholder="邮箱/用户名" />
                <input type="password" id="password" placeholder="密码" />
                <button onclick="login()">登录</button>
            </div>
            <pre id="login-result">结果将显示在这里</pre>
        </div>
        
        <div class="card">
            <h2>验证令牌</h2>
            <button onclick="checkAuth()">获取当前用户信息</button>
            <pre id="auth-result">结果将显示在这里</pre>
        </div>
        
        <div class="card">
            <h2>手动设置令牌</h2>
            <input type="text" id="token" placeholder="输入令牌" />
            <button onclick="setToken()">保存令牌</button>
        </div>
        
        <script>
            // 登录函数
            async function login() {
                const email = document.getElementById('email').value;
                const password = document.getElementById('password').value;
                const result = document.getElementById('login-result');
                
                try {
                    const response = await fetch('/api/user/token', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/x-www-form-urlencoded',
                        },
                        body: `username=${encodeURIComponent(email)}&password=${encodeURIComponent(password)}`,
                        credentials: 'include'
                    });
                    
                    const data = await response.json();
                    if (response.ok) {
                        localStorage.setItem('access_token', data.access_token);
                        result.textContent = '登录成功!\n' + JSON.stringify(data, null, 2);
                    } else {
                        result.textContent = '登录失败!\n' + JSON.stringify(data, null, 2);
                    }
                } catch (error) {
                    result.textContent = '请求出错: ' + error.message;
                }
            }
            
            // 验证令牌
            async function checkAuth() {
                const token = localStorage.getItem('access_token');
                const result = document.getElementById('auth-result');
                
                try {
                    const response = await fetch('/api/user/me', {
                        method: 'GET',
                        headers: {
                            'Authorization': token ? `Bearer ${token}` : '',
                        },
                        credentials: 'include'
                    });
                    
                    if (response.ok) {
                        const data = await response.json();
                        result.textContent = '认证成功!\n' + JSON.stringify(data, null, 2);
                    } else {
                        result.textContent = `认证失败! 状态码: ${response.status}\n详情: ${await response.text()}`;
                    }
                } catch (error) {
                    result.textContent = '请求出错: ' + error.message;
                }
            }
            
            // 手动设置令牌
            function setToken() {
                const token = document.getElementById('token').value;
                if (token) {
                    localStorage.setItem('access_token', token);
                    alert('令牌已保存!');
                } else {
                    alert('请输入有效的令牌!');
                }
            }
        </script>
    </body>
    </html>
    """

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True) 