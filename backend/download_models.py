#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import torch
import argparse
from pathlib import Path
from dotenv import load_dotenv

"""
模型下载脚本：用于预先下载和缓存所需的NLP模型
支持下载GPT-2和SentenceTransformer模型
"""

def setup_folders():
    """创建必要的目录结构"""
    Path("models/gpt2").mkdir(parents=True, exist_ok=True)
    Path("models/all-MiniLM-L6-v2").mkdir(parents=True, exist_ok=True)
    
def download_gpt2_model(model_path="models/gpt2"):
    """下载GPT-2模型"""
    print("开始下载GPT-2模型...")
    
    # 设置模型缓存路径
    os.environ['TRANSFORMERS_CACHE'] = os.path.abspath("models")
    
    try:
        from transformers import GPT2LMHeadModel, GPT2Tokenizer
        
        # 下载模型
        model = GPT2LMHeadModel.from_pretrained('gpt2')
        tokenizer = GPT2Tokenizer.from_pretrained('gpt2')
        
        # 保存到指定路径
        model.save_pretrained(model_path)
        tokenizer.save_pretrained(model_path)
        
        print(f"GPT-2模型下载完成，保存在: {os.path.abspath(model_path)}")
        return True
    except Exception as e:
        print(f"下载GPT-2模型时出错: {e}")
        return False

def download_sentence_transformer(model_path="models/all-MiniLM-L6-v2"):
    """下载SentenceTransformer模型"""
    print("开始下载SentenceTransformer模型...")
    
    # 设置模型缓存路径
    os.environ['SENTENCE_TRANSFORMERS_HOME'] = os.path.abspath("models")
    
    try:
        from sentence_transformers import SentenceTransformer
        
        # 下载模型
        model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # 保存到指定路径
        model.save(model_path)
        
        # 验证模型下载
        test_model = SentenceTransformer(model_path)
        test_embed = test_model.encode("测试句子嵌入是否正常工作")
        assert len(test_embed) > 0, "模型嵌入生成失败"
        
        print(f"SentenceTransformer模型下载完成，保存在: {os.path.abspath(model_path)}")
        return True
    except Exception as e:
        print(f"下载SentenceTransformer模型时出错: {e}")
        return False

def download_nltk_data():
    """下载NLTK数据包"""
    print("开始下载NLTK数据...")
    
    try:
        import nltk
        nltk.download('punkt', download_dir='./models/nltk_data')
        os.environ['NLTK_DATA'] = os.path.abspath('./models/nltk_data')
        print("NLTK数据下载完成")
        return True
    except Exception as e:
        print(f"下载NLTK数据时出错: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='下载和缓存NLP模型')
    parser.add_argument('--gpt2', action='store_true', help='下载GPT-2模型')
    parser.add_argument('--sentence-transformer', action='store_true', help='下载SentenceTransformer模型')
    parser.add_argument('--nltk', action='store_true', help='下载NLTK数据包')
    parser.add_argument('--all', action='store_true', help='下载所有模型和数据')
    parser.add_argument('--models-dir', type=str, default='models', help='模型保存目录')
    
    args = parser.parse_args()
    
    # 加载环境变量
    load_dotenv()
    
    # 准备目录
    setup_folders()
    
    success = []
    
    if args.all or args.gpt2:
        gpt2_path = os.path.join(args.models_dir, 'gpt2')
        if download_gpt2_model(gpt2_path):
            success.append('GPT-2')
    
    if args.all or args.sentence_transformer:
        st_path = os.path.join(args.models_dir, 'all-MiniLM-L6-v2')
        if download_sentence_transformer(st_path):
            success.append('SentenceTransformer')
    
    if args.all or args.nltk:
        if download_nltk_data():
            success.append('NLTK')
    
    if not (args.all or args.gpt2 or args.sentence_transformer or args.nltk):
        print("请指定要下载的模型。使用 --help 查看选项。")
        print("例如: python download_models.py --all")
        return
    
    print("\n==== 下载摘要 ====")
    print(f"成功下载的模型: {', '.join(success) if success else '无'}")
    
    # 更新环境变量建议
    print("\n您可以在.env文件中设置以下路径:")
    print(f"SENTENCE_TRANSFORMER_PATH={os.path.abspath(os.path.join(args.models_dir, 'all-MiniLM-L6-v2'))}")
    print(f"GPT2_MODEL_PATH={os.path.abspath(os.path.join(args.models_dir, 'gpt2'))}")
    print(f"TRANSFORMERS_CACHE={os.path.abspath(args.models_dir)}")
    print(f"SENTENCE_TRANSFORMERS_HOME={os.path.abspath(args.models_dir)}")
    print(f"NLTK_DATA={os.path.abspath('./models/nltk_data')}")

if __name__ == "__main__":
    main() 