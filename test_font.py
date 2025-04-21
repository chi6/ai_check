# -*- coding: utf-8 -*-
from __future__ import print_function
import os
import urllib
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties

# 创建 fonts 目录
fonts_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fonts')
if not os.path.exists(fonts_dir):
    os.makedirs(fonts_dir)

# 中文字体文件路径
chinese_font_path = os.path.join(fonts_dir, 'NotoSansSC-Regular.ttf')

# 检查中文字体文件是否存在，如果不存在则下载
if not os.path.exists(chinese_font_path):
    try:
        # 下载 Noto Sans SC 字体（Google开源中文字体）
        print("下载中文字体到 " + chinese_font_path)
        url = "https://github.com/googlefonts/noto-cjk/raw/main/Sans/NotoSansSC-Regular.ttf"
        urllib.urlretrieve(url, chinese_font_path)
        print("中文字体下载成功")
    except Exception as e:
        print("下载中文字体失败: " + str(e))

# 设置中文字体
chinese_font = FontProperties(fname=chinese_font_path)
print("使用字体文件: " + chinese_font_path)

# 创建测试PDF
fig, ax = plt.subplots(figsize=(8, 6))
ax.text(0.5, 0.5, 'Test Chinese Font', ha='center', va='center', fontsize=20, fontproperties=chinese_font)
ax.set_xlim(0, 1)
ax.set_ylim(0, 1)
ax.axis('off')

test_pdf_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_font.pdf')
plt.savefig(test_pdf_path)
print('PDF生成成功，路径: ' + test_pdf_path) 