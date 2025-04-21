from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import upload, detect, report, user
import matplotlib
import os
import subprocess
import sys

# 确保可以导入字体工具模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 使用字体工具函数设置中文字体
try:
    from app.utils.font_utils import setup_chinese_fonts
    setup_chinese_fonts()
except Exception as e:
    print(f"配置中文字体失败: {str(e)}")
    # 如果配置失败，使用基本设置
    matplotlib.use('Agg')
    print("使用默认字体设置")

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

# 包含路由
app.include_router(upload.router, prefix="/api", tags=["上传"])
app.include_router(detect.router, prefix="/api", tags=["检测"])
app.include_router(report.router, prefix="/api", tags=["报告"])
app.include_router(user.router, prefix="/api", tags=["用户"])

@app.get("/")
async def root():
    return {"message": "欢迎使用AI论文检测工具API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True) 