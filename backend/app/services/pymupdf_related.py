"""
处理PyMuPDF相关的辅助函数
"""
# 在这个模块中，我们导入PyMuPDF并提供正确的接口来使用它

try:
    # 尝试导入PyMuPDF的fitz模块
    import fitz
except ImportError:
    # 如果导入失败，尝试安装PyMuPDF
    import subprocess
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pymupdf==1.23.5"])
    import fitz

def extract_text_from_pdf(file_path):
    """从PDF文件中提取文本
    Args:
        file_path (str): PDF文件路径
    Returns:
        str: 提取的文本内容
    """
    text = ""
    try:
        # 正确使用PyMuPDF打开PDF文件
        doc = fitz.open(file_path)
        for page in doc:
            text += page.get_text()
        doc.close()
    except Exception as e:
        print(f"从PDF提取文本时出错: {str(e)}")
    return text 