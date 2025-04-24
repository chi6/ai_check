# AI检测模型下载指南

本项目使用了多种NLP模型来进行AI生成内容检测。在离线环境或网络不稳定的情况下，可能需要预先下载这些模型。本指南将帮助您完成模型的下载和配置。

## 所需模型

项目使用以下模型：

1. **GPT-2**: 用于计算文本困惑度
2. **SentenceTransformer (all-MiniLM-L6-v2)**: 用于计算文本段落之间的风格一致性
3. **NLTK数据包**: 用于文本分割和预处理

## 自动下载模型

我们提供了一个简便的脚本来自动下载所有必要的模型。

### 使用方法

```bash
# 下载所有模型
python download_models.py --all

# 或者仅下载特定模型
python download_models.py --gpt2 --sentence-transformer
```

### 命令行选项

- `--all`: 下载所有模型和数据
- `--gpt2`: 仅下载GPT-2模型
- `--sentence-transformer`: 仅下载SentenceTransformer模型
- `--nltk`: 仅下载NLTK数据包
- `--models-dir`: 指定模型保存目录，默认为`models`

## 离线模式

如果您在完全离线的环境中工作，可以在`.env`文件中设置：

```
OFFLINE_MODE=true
```

这将告诉系统仅使用本地模型，不尝试在线下载。

## 手动下载和配置

如果您需要手动下载模型，请参考以下步骤：

### GPT-2模型

1. 从Hugging Face下载GPT-2模型
2. 将模型文件保存到`models/gpt2/`目录

### SentenceTransformer模型

1. 下载`all-MiniLM-L6-v2`模型
2. 将模型文件保存到`models/all-MiniLM-L6-v2/`目录

### NLTK数据

1. 下载NLTK的`punkt`数据包
2. 保存到`models/nltk_data/`目录

## 故障排除

如果遇到模型下载或加载问题，可尝试以下方法：

1. 确保网络连接正常
2. 检查您是否有足够的磁盘空间
3. 确保Python环境中已安装所有必要的依赖包
4. 如果在防火墙后面，确保已允许访问Hugging Face的域名

如果仍然遇到问题，可以尝试手动下载模型文件，并按照上述目录结构放置。 