# -*- coding: utf-8 -*-
from __future__ import print_function
import os
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties, findfont

# 使用系统字体
try:
    chinese_font_path = findfont(FontProperties(family='Arial Unicode MS'))
    print("找到字体路径: " + chinese_font_path)
    chinese_font = FontProperties(fname=chinese_font_path)
except Exception as e:
    print("获取字体时出错: " + str(e))
    chinese_font = FontProperties()

# 创建测试PDF
fig, ax = plt.subplots(figsize=(8, 6))
ax.text(0.5, 0.5, 'Test Chinese Font - 测试中文字体', ha='center', va='center', fontsize=20, fontproperties=chinese_font)
ax.set_xlim(0, 1)
ax.set_ylim(0, 1)
ax.axis('off')

test_pdf_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_font_fixed.pdf')
plt.savefig(test_pdf_path)
print('PDF生成成功，路径: ' + test_pdf_path) 