from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .routers import upload, detect, report, user
from .routers import pay, notify, license as license_router, usage
import matplotlib
import os
import subprocess
import sys
from .utils.database import engine, get_db
from .utils.init_db import init_db
from .utils.font_utils import init_fonts

# 确保可以导入字体工具模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 下载NLTK数据
def ensure_nltk_data():
    try:
        import nltk
        import nltk.data as nltk_data
        data_dir = os.environ.get("NLTK_DATA") or os.path.abspath("models/nltk_data")
        os.makedirs(data_dir, exist_ok=True)
        os.environ["NLTK_DATA"] = data_dir
        # 确保 punkt
        try:
            nltk_data.find("tokenizers/punkt")
        except LookupError:
            nltk.download("punkt", download_dir=data_dir, quiet=True)
        # 确保 punkt_tab（较新NLTK版本需要）
        try:
            nltk_data.find("tokenizers/punkt_tab")
        except LookupError:
            try:
                nltk.download("punkt_tab", download_dir=data_dir, quiet=True)
            except Exception:
                pass
        print("NLTK 数据已准备就绪")
    except Exception as e:
        print(f"NLTK数据准备失败: {str(e)}")

ensure_nltk_data()

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

# 包含路由
app.include_router(upload.router, prefix="/api", tags=["上传"])
# 兼容无前缀访问（例如前端错误直连 /upload）
app.include_router(upload.router, tags=["上传(兼容)"])
app.include_router(detect.router, prefix="/api", tags=["检测"])
app.include_router(report.router, prefix="/api", tags=["报告"])
app.include_router(user.router, prefix="/api", tags=["用户"])
app.include_router(pay.router, prefix="/api", tags=["支付"])
app.include_router(notify.router, prefix="/api", tags=["支付回调"])
app.include_router(license_router.router, prefix="/api", tags=["许可证"])
app.include_router(usage.router, prefix="/api", tags=["用量"])

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
    """应用启动时执行的初始化操作"""
    # 初始化数据库
    init_db()
    
    # 初始化字体
    try:
        init_fonts()
    except Exception as e:
        print(f"初始化字体时出错: {str(e)}")
        
    # 显示离线模式状态
    if os.environ.get("OFFLINE_MODE", "false").lower() == "true":
        print("\n-----\n\n运行在离线模式，将只使用本地模型\n\n-----\n")

@app.get("/")
async def root():
    return {"message": "欢迎使用AI论文检测工具API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True) 