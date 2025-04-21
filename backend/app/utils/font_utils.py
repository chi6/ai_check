"""
提供中文字体支持的工具函数
"""
import os
import sys
import matplotlib
import matplotlib.font_manager as fm
import platform
import subprocess
from pathlib import Path

# 尝试导入字体下载模块
try:
    from .download_font import download_font
except ImportError:
    # 如果在直接运行时导入失败，尝试相对导入
    try:
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from app.utils.download_font import download_font
    except ImportError:
        # 如果仍然失败，提供一个空函数
        def download_font(font_name=None):
            print(f"警告: 字体下载功能不可用")
            return None

def setup_chinese_fonts():
    """
    设置中文字体支持
    返回找到的第一个可用中文字体名称，或None
    """
    # 初始化非交互式后端
    matplotlib.use('Agg')
    
    # 获取当前系统信息
    system = platform.system()
    print(f"当前系统: {system}")
    
    # 尝试刷新字体缓存 (Linux/macOS)
    if system != "Windows" and os.path.exists('/usr/bin/fc-cache'):
        try:
            subprocess.run(['fc-cache', '-fv'], check=False, capture_output=True)
            print("已刷新字体缓存")
        except Exception as e:
            print(f"刷新字体缓存失败: {e}")
    
    # 常见中文字体列表 (按系统)
    chinese_fonts = []
    
    if system == "Windows":
        chinese_fonts = ['SimHei', 'SimSun', 'Microsoft YaHei', 'FangSong', 'KaiTi']
    elif system == "Darwin":  # macOS
        chinese_fonts = ['PingFang SC', 'Heiti SC', 'STHeiti', 'STSong', 'Arial Unicode MS']
    else:  # Linux
        chinese_fonts = ['WenQuanYi Micro Hei', 'WenQuanYi Zen Hei', 'AR PL UMing CN', 'Noto Sans CJK SC', 'Noto Sans CJK TC']
    
    # 当前项目根目录，用于查找内嵌字体
    root_dir = Path(__file__).parent.parent.parent
    
    # 检查是否有内嵌字体目录及文件
    embedded_font_dir = root_dir / "fonts"
    embedded_font_dir.mkdir(exist_ok=True)  # 确保目录存在
    
    print(f"检查内嵌字体目录: {embedded_font_dir}")
    embedded_fonts = list(embedded_font_dir.glob("*.ttf")) + list(embedded_font_dir.glob("*.ttc")) + list(embedded_font_dir.glob("*.otf"))
    
    if not embedded_fonts:
        # 如果没有内嵌字体，尝试下载一个
        print("未发现内嵌字体，尝试下载...")
        try:
            font_path = download_font("Noto Sans CJK SC")
            if font_path:
                embedded_fonts.append(Path(font_path))
                print(f"成功下载字体: {font_path}")
        except Exception as e:
            print(f"下载字体失败: {e}")
    
    # 添加内嵌字体
    for font_path in embedded_fonts:
        try:
            font_path_str = str(font_path)
            print(f"添加内嵌字体: {font_path.name}")
            fm.fontManager.addfont(font_path_str)
        except Exception as e:
            print(f"添加内嵌字体失败 {font_path.name}: {e}")
    
    # 重置缓存以确保新字体生效
    fm._rebuild()
    
    # 尝试找到一个可用的中文字体
    found_font = None
    
    # 首先尝试使用内嵌字体
    for font_path in embedded_fonts:
        try:
            font_name = font_path.stem  # 使用文件名作为字体名
            print(f"尝试使用内嵌字体: {font_name}")
            # 尝试获取字体属性并设置
            fm.findfont(fm.FontProperties(fname=str(font_path)))
            matplotlib.rcParams['font.family'] = ['sans-serif']
            if "CJK" in font_name or "WenQuanYi" in font_name:
                matplotlib.rcParams['font.sans-serif'] = [font_name, 'DejaVu Sans', 'Bitstream Vera Sans']
            else:
                matplotlib.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Bitstream Vera Sans', font_name]
            found_font = font_name
            print(f"使用内嵌字体: {font_name}")
            break
        except Exception as e:
            print(f"内嵌字体 {font_name} 配置失败: {e}")
    
    # 如果内嵌字体不可用，尝试系统字体
    if not found_font:
        for font_name in chinese_fonts:
            try:
                font_path = fm.findfont(fm.FontProperties(family=font_name))
                if os.path.exists(font_path):
                    print(f"找到中文字体: {font_name} -> {font_path}")
                    found_font = font_name
                    # 设置全局字体
                    matplotlib.rcParams['font.family'] = ['sans-serif']
                    matplotlib.rcParams['font.sans-serif'] = [font_name, 'DejaVu Sans', 'Bitstream Vera Sans']
                    break
            except Exception as e:
                print(f"字体 {font_name} 不可用: {e}")
    
    # 如果找不到中文字体，打印警告并使用默认字体
    if not found_font:
        print("警告: 未找到中文字体，将使用默认字体")
        matplotlib.rcParams['font.family'] = ['sans-serif']
    
    # 设置通用属性
    matplotlib.rcParams['axes.unicode_minus'] = False  # 确保负号显示正常
    
    # 打印当前可用的中文字体列表
    all_fonts = sorted([f.name for f in fm.fontManager.ttflist])
    chinese_font_list = [f for f in all_fonts if any(
        char in f for char in ['黑', '宋', 'WenQuanYi', 'Hei', 'Song', 'Ming', 'PingFang', 'Noto', 'Source Han', 'CJK']
    )]
    
    print(f"系统可用中文字体: {chinese_font_list}")
    print(f"当前matplotlib字体设置: {matplotlib.rcParams['font.sans-serif']}")
    
    return found_font

# 如果直接运行，执行字体配置
if __name__ == "__main__":
    font = setup_chinese_fonts()
    print(f"配置的字体: {font}") 