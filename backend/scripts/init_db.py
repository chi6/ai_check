#!/usr/bin/env python3
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.database import engine, Base
from app.schemas.database_models import User, DetectionTask, ParagraphResult

def init_db():
    """初始化数据库，创建所有表"""
    print("开始初始化数据库...")
    
    # 创建所有表
    Base.metadata.create_all(bind=engine)
    print("数据库表创建完成")

if __name__ == "__main__":
    init_db() 