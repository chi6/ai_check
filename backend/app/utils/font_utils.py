"""
用于下载和管理字体的工具模块。
这个模块提供了自动下载字体文件的功能，
确保报告生成时具有正确的中文字体支持。
"""

import os
import shutil
import requests
import zipfile
import tempfile
from pathlib import Path

# 字体目录
FONTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'fonts')

# 确保字体目录存在
os.makedirs(FONTS_DIR, exist_ok=True)

# Noto Sans CJK SC字体下载链接
NOTO_SANS_CJK_SC_URL = "https://github.com/googlefonts/noto-cjk/raw/main/Sans/OTF/SimplifiedChinese/NotoSansCJKsc-Regular.otf"

def download_font(url, font_name, force=False):
    """
    下载字体文件
    
    参数:
        url: 字体下载URL
        font_name: 字体文件名
        force: 是否强制重新下载
    
    返回:
        bool: 下载是否成功
    """
    font_path = os.path.join(FONTS_DIR, font_name)
    
    # 如果字体已存在且不强制重新下载，直接返回
    if os.path.exists(font_path) and not force:
        print(f"字体 {font_name} 已存在")
        return True
        
    try:
        print(f"正在下载字体 {font_name}...")
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        with open(font_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                
        print(f"字体 {font_name} 下载完成")
        return True
    except Exception as e:
        print(f"下载字体 {font_name} 时出错: {str(e)}")
        return False

def setup_noto_sans_cjk_font(force=False):
    """
    设置 Noto Sans CJK SC 字体
    
    参数:
        force: 是否强制重新下载
    
    返回:
        bool: 字体设置是否成功
    """
    return download_font(NOTO_SANS_CJK_SC_URL, "NotoSansCJKsc-Regular.otf", force)

def check_system_chinese_fonts():
    """
    检查系统中是否存在支持中文的字体
    
    返回:
        list: 找到的中文字体列表
    """
    import matplotlib.font_manager as fm
    
    # 常见的中文字体名称
    chinese_fonts = ['SimHei', 'Microsoft YaHei', 'PingFang SC', 'Hiragino Sans GB', 'Heiti SC', 'STHeiti', 'SimSun']
    
    # 获取系统所有字体
    system_fonts = fm.findSystemFonts()
    
    # 查找中文字体
    found_fonts = []
    for font_name in chinese_fonts:
        for font_path in system_fonts:
            if font_name.lower() in os.path.basename(font_path).lower():
                found_fonts.append((font_name, font_path))
                break
    
    return found_fonts

def init_fonts():
    """
    初始化字体，检查系统字体，如果没有找到中文字体则下载
    """
    # 检查系统中文字体
    chinese_fonts = check_system_chinese_fonts()
    
    if chinese_fonts:
        print(f"找到系统中文字体: {', '.join([f[0] for f in chinese_fonts])}")
        return True
    else:
        print("系统中未找到中文字体，将下载 Noto Sans CJK SC...")
        return setup_noto_sans_cjk_font()

# 如果直接运行，执行字体配置
if __name__ == "__main__":
    font = init_fonts()
    print(f"配置的字体: {font}") 