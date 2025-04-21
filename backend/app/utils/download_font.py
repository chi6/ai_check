"""
字体下载工具 - 用于确保系统中有可用的中文字体
"""
import os
import sys
import urllib.request
import shutil
from pathlib import Path

# 可下载的免费开源中文字体列表
FONT_URLS = {
    "WenQuanYi Micro Hei": "https://sourceforge.net/projects/wqy/files/wqy-microhei/0.2.0-beta/wqy-microhei-0.2.0-beta.tar.gz/download",
    "Noto Sans CJK SC": "https://github.com/googlefonts/noto-cjk/raw/main/Sans/OTF/SimplifiedChinese/NotoSansCJKsc-Regular.otf",
    "Source Han Sans": "https://github.com/adobe-fonts/source-han-sans/raw/release/OTF/SimplifiedChinese/SourceHanSansSC-Regular.otf"
}

def download_font(font_name="Noto Sans CJK SC"):
    """
    下载指定的开源字体并保存到fonts目录
    
    Args:
        font_name: 要下载的字体名称，必须在FONT_URLS中定义
    
    Returns:
        字体文件路径或None（如果下载失败）
    """
    if font_name not in FONT_URLS:
        print(f"错误: 未知字体 '{font_name}'")
        return None
        
    url = FONT_URLS[font_name]
    
    # 确定字体目录
    root_dir = Path(__file__).parent.parent.parent
    font_dir = root_dir / "fonts"
    font_dir.mkdir(exist_ok=True)
    
    # 确定字体文件名称
    if font_name == "WenQuanYi Micro Hei":
        file_name = "wqy-microhei.ttc"
    elif font_name == "Noto Sans CJK SC":
        file_name = "NotoSansCJKsc-Regular.otf"
    elif font_name == "Source Han Sans":
        file_name = "SourceHanSansSC-Regular.otf"
    else:
        file_name = font_name.replace(" ", "_") + ".ttf"
    
    font_path = font_dir / file_name
    
    # 如果字体文件已存在，直接返回
    if font_path.exists():
        print(f"字体文件已存在: {font_path}")
        return str(font_path)
    
    # 下载字体文件
    try:
        print(f"正在下载 {font_name} 字体...")
        temp_file, _ = urllib.request.urlretrieve(url)
        
        # 复制到字体目录
        if font_name == "WenQuanYi Micro Hei":
            # 需要解压缩
            import tarfile
            with tarfile.open(temp_file, 'r:gz') as tar:
                for member in tar.getmembers():
                    if member.name.endswith('.ttc'):
                        f = tar.extractfile(member)
                        if f is not None:
                            with open(font_path, 'wb') as out:
                                shutil.copyfileobj(f, out)
                            break
        else:
            # 直接复制
            shutil.copy2(temp_file, font_path)
            
        print(f"字体下载成功: {font_path}")
        return str(font_path)
    except Exception as e:
        print(f"下载字体出错: {str(e)}")
        return None
    finally:
        # 清理临时文件
        try:
            if 'temp_file' in locals():
                os.unlink(temp_file)
        except:
            pass
    
if __name__ == "__main__":
    # 如果直接运行脚本，下载默认字体
    font_name = "Noto Sans CJK SC" 
    if len(sys.argv) > 1:
        font_name = sys.argv[1]
    
    path = download_font(font_name)
    if path:
        print(f"字体已下载到: {path}")
    else:
        print("字体下载失败") 