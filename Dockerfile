FROM python:3.9-slim

WORKDIR /app

# 安装系统依赖项，这些是PyMuPDF和中文字体所需的
RUN apt-get update && apt-get install -y \
    build-essential \
    libffi-dev \
    libssl-dev \
    libjpeg-dev \
    zlib1g-dev \
    fontconfig \
    # 安装更多中文字体
    fonts-wqy-microhei \
    fonts-wqy-zenhei \
    fonts-arphic-ukai \
    fonts-arphic-uming \
    xfonts-wqy \
    && rm -rf /var/lib/apt/lists/*

# 创建matplotlib配置目录
RUN mkdir -p /root/.config/matplotlib

# 刷新字体缓存
RUN echo "font.family : WenQuanYi Micro Hei, WenQuanYi Zen Hei, AR PL UMing CN, AR PL UKai CN, sans-serif" > /root/.config/matplotlib/matplotlibrc

# 设置中文字体
RUN fc-cache -fv

COPY ./backend/requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt

# 创建文件并设置matplotlib默认使用中文字体
RUN mkdir -p /root/.config/matplotlib
RUN echo "backend : Agg" > /root/.config/matplotlib/matplotlibrc
RUN echo "font.family : WenQuanYi Micro Hei, WenQuanYi Zen Hei, AR PL UMing CN, sans-serif" >> /root/.config/matplotlib/matplotlibrc 
RUN echo "axes.unicode_minus : False" >> /root/.config/matplotlib/matplotlibrc

COPY ./backend /app/

# 创建上传目录
RUN mkdir -p /app/uploads

# 设置环境变量
ENV PYTHONPATH=/app
ENV PORT=8000

# 测试matplotlib字体设置
RUN python -c "import matplotlib.pyplot as plt; print('Available fonts:', [f.name for f in plt.matplotlib.font_manager.fontManager.ttflist if 'WenQuanYi' in f.name or 'AR PL' in f.name])"

CMD ["python", "run.py"] 