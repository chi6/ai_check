from fastapi import UploadFile
import os
import shutil
import aiofiles
# import fitz  # PyMuPDF
import docx
from pathlib import Path
# 导入我们新创建的模块
from .pymupdf_related import extract_text_from_pdf as pdf_text_extractor

# 创建上传文件存储路径
UPLOAD_DIR = Path("./uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

def get_file_extension(filename: str) -> str:
    """获取文件扩展名"""
    return os.path.splitext(filename)[1].lower()

def validate_file(file: UploadFile) -> bool:
    """验证文件格式是否支持"""
    valid_extensions = ['.pdf', '.docx', '.doc', '.txt']
    return get_file_extension(file.filename) in valid_extensions

async def save_upload_file(task_id: str, file: UploadFile) -> str:
    """保存上传文件"""
    # 为每个任务创建目录
    task_dir = UPLOAD_DIR / task_id
    task_dir.mkdir(exist_ok=True)
    print(f"保存文件到: {task_dir}")
    # 保存文件
    file_path = task_dir / file.filename
    async with aiofiles.open(file_path, 'wb') as out_file:
        content = await file.read()
        await out_file.write(content)
    
    return file.filename

def extract_text_from_pdf(file_path: str) -> str:
    """从PDF文件中提取文本"""
    # 使用新的辅助函数
    return pdf_text_extractor(file_path)

def extract_text_from_docx(file_path: str) -> str:
    """从DOCX文件中提取文本"""
    text = ""
    try:
        doc = docx.Document(file_path)
        for para in doc.paragraphs:
            text += para.text + "\n"
    except Exception as e:
        print(f"从DOCX提取文本时出错: {str(e)}")
    return text

def extract_text_from_txt(file_path: str) -> str:
    """从TXT文件中提取文本"""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except UnicodeDecodeError:
        # 如果UTF-8解码失败，尝试其他编码
        try:
            with open(file_path, 'r', encoding='gbk') as file:
                return file.read()
        except Exception as e:
            print(f"从TXT提取文本时出错: {str(e)}")
            return ""

def extract_text(task_id: str, filename: str) -> str:
    """根据文件类型提取文本"""
    file_path = UPLOAD_DIR / task_id / filename
    ext = get_file_extension(filename)
    
    if ext == '.pdf':
        return extract_text_from_pdf(str(file_path))
    elif ext in ['.docx', '.doc']:
        return extract_text_from_docx(str(file_path))
    elif ext == '.txt':
        return extract_text_from_txt(str(file_path))
    else:
        return ""

def clean_up_task_files(task_id: str):
    """清理任务文件"""
    task_dir = UPLOAD_DIR / task_id
    if task_dir.exists():
        shutil.rmtree(task_dir) 