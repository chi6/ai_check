# text_analysis_module.py

import re
from typing import List
from nltk.tokenize import sent_tokenize
from transformers import GPT2LMHeadModel, GPT2Tokenizer
import torch
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
import numpy as np
import openai

# ----------- 文本切分部分 -----------

def clean_text(text: str) -> str:
    text = re.sub(r'\r\n', '\n', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def paragraph_split(text: str, min_chars: int = 30) -> List[str]:
    raw_blocks = text.split('\n\n')
    processed = []
    buffer = ""
    for block in raw_blocks:
        block = block.strip()
        if len(block) < min_chars:
            buffer += " " + block
        else:
            if buffer:
                processed.append(buffer.strip())
                buffer = ""
            processed.append(block)
    if buffer:
        processed.append(buffer.strip())
    return processed

def segment_sentences(blocks: List[str], max_chars: int = 300) -> List[str]:
    result = []
    for block in blocks:
        sentences = sent_tokenize(block)
        segment = ""
        for sentence in sentences:
            if len(segment) + len(sentence) < max_chars:
                segment += " " + sentence
            else:
                result.append(segment.strip())
                segment = sentence
        if segment:
            result.append(segment.strip())
    return result

def smart_split(text: str, 
                min_chars: int = 30, 
                max_chars: int = 300,
                segment_level: str = "sentence") -> List[str]:
    text = clean_text(text)
    blocks = paragraph_split(text, min_chars=min_chars)
    if segment_level == "paragraph":
        return blocks
    elif segment_level == "sentence":
        return segment_sentences(blocks, max_chars=max_chars)
    else:
        raise ValueError("segment_level must be 'paragraph' or 'sentence'")

# ----------- 困惑度计算部分 -----------

def compute_perplexity(text: str) -> float:
    model_name = 'gpt2'
    model = GPT2LMHeadModel.from_pretrained(model_name)
    tokenizer = GPT2Tokenizer.from_pretrained(model_name)
    model.eval()
    encodings = tokenizer(text, return_tensors='pt')
    with torch.no_grad():
        outputs = model(**encodings, labels=encodings["input_ids"])
    loss = outputs.loss
    return torch.exp(loss).item()

# ----------- 风格一致性检测 -----------

embed_model = SentenceTransformer('all-MiniLM-L6-v2')

def compute_style_consistency(segments: List[str]) -> float:
    embeddings = embed_model.encode(segments)
    similarities = []
    for i in range(len(embeddings) - 1):
        sim = cosine_similarity([embeddings[i]], [embeddings[i + 1]])[0][0]
        similarities.append(sim)
    return float(np.mean(similarities)) if similarities else 0.0

# ----------- 大模型直接判断（OpenAI接口） -----------

def gpt_ai_judgment(text: str, perplexity: float, style_score: float, likelihood: str) -> dict:
    prompt = f"""
    请判断下面这段文字是否可能为AI生成，并说明理由：

    文本内容：\n"""{text}"""

    检测指标：
    - 困惑度（Perplexity）：{perplexity:.2f}
    - 风格一致性（Style Consistency）：{style_score:.3f}
    - 初步AI率判断：{likelihood}

    请结合这些数据，输出判断结果。
    输出格式为 JSON：{{"is_ai": "是/否", "reason": "解释原因"}}
    """
    
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=500
        )
        content = response['choices'][0]['message']['content'].strip()
        import json
        parsed = json.loads(content)
        return parsed
    except Exception as e:
        return {"is_ai": "判断失败", "reason": str(e)}

# ----------- AI率评分整合 -----------

def detect_ai_score(text: str) -> dict:
    segments = smart_split(text)
    avg_perplexity = np.mean([compute_perplexity(seg) for seg in segments])
    style_score = compute_style_consistency(segments)
    ai_likelihood = estimate_ai_likelihood(avg_perplexity, style_score)
    gpt_result = gpt_ai_judgment(text, avg_perplexity, style_score, ai_likelihood)

    return {
        "avg_perplexity": round(avg_perplexity, 2),
        "style_consistency": round(style_score, 3),
        "ai_likelihood": ai_likelihood,
        "gpt_judgment": gpt_result.get("is_ai", "未知"),
        "explanation": gpt_result.get("reason", "无解释返回")
    }

def estimate_ai_likelihood(perplexity: float, style: float) -> str:
    if perplexity < 20 and style > 0.95:
        return "高（AI生成可能性大）"
    elif perplexity < 30 and style > 0.90:
        return "中（可能为AI生成）"
    else:
        return "低（更可能为人类写作）"

# 示例调用
if __name__ == '__main__':
    sample_text = """
    在遥远的银河边界，一艘飞船缓缓前行。

    它的船长，是一位曾在地球大战中获得勋章的英雄。不过现在，他的任务并不是战斗，而是探索。
    """
    result = detect_ai_score(sample_text)
    print("检测结果：")
    for k, v in result.items():
        print(f"{k}: {v}")
