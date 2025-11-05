"""
改进的AI文本检测器
专门针对学术文本的AI生成特征检测
"""

import re
from typing import Dict, List, Tuple


def mean(numbers: List[float]) -> float:
    """计算平均值"""
    return sum(numbers) / len(numbers) if numbers else 0


def std(numbers: List[float]) -> float:
    """计算标准差"""
    if not numbers or len(numbers) < 2:
        return 0
    m = mean(numbers)
    variance = sum((x - m) ** 2 for x in numbers) / len(numbers)
    return variance ** 0.5


def split_sentences_improved(text: str) -> List[str]:
    """
    改进的句子分割 - 不在分号处分割，保持复杂句的完整性
    """
    # 规范化空白
    text_clean = ' '.join(text.split())
    
    # 只在句号、问号、感叹号后分割，不在分号、冒号处分割
    # 使用更智能的分割：考虑引用（如 "et al., 2021"）
    sentences = []
    current = ""
    i = 0
    
    while i < len(text_clean):
        char = text_clean[i]
        current += char
        
        # 检测句子结束标记
        if char in '.!?':
            # 检查是否是缩写或引用中的句号
            # 向前查看是否有 "et al" 或数字
            if char == '.':
                # 检查前面几个字符
                prev_chars = current[-10:].lower() if len(current) >= 10 else current.lower()
                if 'et al' in prev_chars or re.search(r'\d\.$', current):
                    # 这是引用或缩写中的句号，不分割
                    i += 1
                    continue
                    
                # 检查后面是否有闭括号（引用结束）
                if i + 1 < len(text_clean) and text_clean[i + 1] == ')':
                    current += ')'
                    i += 1
            
            # 确保句子有足够长度
            if len(current.strip()) > 15:
                sentences.append(current.strip())
                current = ""
        
        i += 1
    
    # 添加最后一个句子
    if current.strip() and len(current.strip()) > 15:
        sentences.append(current.strip())
    
    # 过滤掉太短的句子
    sentences = [s for s in sentences if len(s.split()) >= 8]
    
    return sentences


def detect_parallel_structures_improved(text: str) -> Dict:
    """
    改进的平行结构检测
    重点检测AI最典型的模式：分号连接的平行结构和序列化列举
    """
    results = {
        'colon_semicolon_pattern': 0,  # 冒号+多分号（最强AI特征）
        'semicolon_and_pattern': 0,    # 分号 + and的平行结构
        'multiple_semicolons': 0,       # 多个分号
        'ordinal_enumeration': 0,       # First, Second, Third等序列化列举
        'total_count': 0,
        'patterns_found': []
    }
    
    # 规范化文本（保留分号和冒号，修复缺失的空格）
    # 先在句号、问号、感叹号后添加空格（如果缺失）
    text_normalized = re.sub(r'([.!?])([A-Z])', r'\1 \2', text)
    text_normalized = ' '.join(text_normalized.split())
    
    # 1. 冒号后跟多个分号的模式（最典型的AI特征）
    # 匹配: 冒号 ... 内容1 ; 内容2 ; 内容3 或 : 内容1 ; 内容2
    pattern1_multi = r':\s*[^.!?]{15,}?;\s*[^.!?]{15,}?;'  # 冒号+两个分号
    matches1_multi = re.findall(pattern1_multi, text_normalized, re.DOTALL)
    if matches1_multi:
        results['colon_semicolon_pattern'] = len(matches1_multi)
        for m in matches1_multi:
            results['patterns_found'].append(f"冒号+多分号: {m[:70]}...")
    else:
        # 如果没有多个分号，检测单个分号的情况
        pattern1_single = r':\s*[^.!?]{30,}?;'
        matches1_single = re.findall(pattern1_single, text_normalized)
        if matches1_single:
            results['colon_semicolon_pattern'] = len(matches1_single)
            for m in matches1_single:
                results['patterns_found'].append(f"冒号+分号: {m[:70]}...")
    
    # 2. 分号 + and 的模式（AI常用，即使只有一个分号）
    # 修改：不要求有两个分号，单个 "; and" 也算
    pattern2 = r';\s*and\s+[a-z]+\s+[a-z]+'  # ; and [代词/名词] [动词]
    matches2 = re.findall(pattern2, text_normalized)
    if matches2:
        results['semicolon_and_pattern'] = len(matches2)
        # 为每个匹配查找上下文
        for m in matches2:
            # 找到匹配在文本中的位置
            pos = text_normalized.find(m)
            if pos != -1:
                start = max(0, pos - 40)
                end = min(len(text_normalized), pos + len(m) + 40)
                context = text_normalized[start:end]
                results['patterns_found'].append(f"分号+and: ...{context}...")
    
    # 3. 一句话中有多个分号（任意类型的复杂平行结构）
    # 查找包含2个以上分号的句子
    sentences_with_semicolons = re.findall(r'[^.!?]*;[^.!?]*;[^.!?]*[.!?]', text_normalized)
    if sentences_with_semicolons:
        results['multiple_semicolons'] = len(sentences_with_semicolons)
        for s in sentences_with_semicolons[:2]:  # 最多记录2个
            # 提取句子的前部分
            sentence_preview = s[:100] if len(s) > 100 else s
            results['patterns_found'].append(f"多分号句: {sentence_preview}...")
    
    # 4. 序列化列举（AI非常喜欢用First, Second, Third这种结构）
    # 检测"First, ... Second, ... Third,"或"Firstly, ... Secondly, ... Thirdly,"模式
    ordinal_patterns = [
        r'\bFirst,.*?\bSecond,.*?\bThird,',  # First, ... Second, ... Third,
        r'\bFirstly,.*?\bSecondly,.*?\bThirdly,',  # Firstly, ... Secondly, ... Thirdly,
        r'\b1\.\s*.*?\b2\.\s*.*?\b3\.',  # 1. ... 2. ... 3.
    ]
    
    for pattern in ordinal_patterns:
        matches = re.findall(pattern, text_normalized, re.DOTALL | re.IGNORECASE)
        if matches:
            results['ordinal_enumeration'] += len(matches)
            for m in matches[:1]:  # 最多记录1个
                preview = m[:80] if len(m) > 80 else m
                results['patterns_found'].append(f"序列化列举: {preview}...")
            break  # 只匹配一种模式就够了
    
    results['total_count'] = (
        results['colon_semicolon_pattern'] +
        results['semicolon_and_pattern'] +
        results['multiple_semicolons'] +
        results['ordinal_enumeration']
    )
    
    return results


def detect_repetitive_sentence_structures(text: str) -> Dict:
    """
    检测重复的句式结构（AI常用）
    例如: "The X Stage focuses on..." "The Y Stage centers on..."
    """
    results = {
        'repetitive_patterns': [],
        'count': 0
    }
    
    # 规范化文本
    text_normalized = re.sub(r'([.!?])([A-Z])', r'\1 \2', text)
    text_normalized = ' '.join(text_normalized.split())
    
    # 检测模式1: "The X [名词] [动词] on"
    pattern1 = r'The\s+\w+\s+\w+\s+(focuses|centers|concentrates|emphasizes)\s+on'
    matches1 = re.findall(pattern1, text_normalized, re.IGNORECASE)
    if len(matches1) >= 2:  # 至少出现2次
        results['count'] += 1
        results['repetitive_patterns'].append(f"重复句式: 'The X Stage [动词] on' (出现{len(matches1)}次)")
    
    # 检测模式2: 连续多个句子以相同方式开头
    sentences = re.split(r'[.!?]\s+', text_normalized)
    if len(sentences) >= 3:
        sentence_starts = [s.split()[:3] for s in sentences if len(s.split()) >= 3]
        # 检查前两个词是否有重复模式
        if sentence_starts:
            first_two_words = [' '.join(start[:2]) for start in sentence_starts]
            from collections import Counter
            word_counts = Counter(first_two_words)
            for words, count in word_counts.items():
                if count >= 3:  # 至少3个句子以相同方式开头
                    results['count'] += 1
                    results['repetitive_patterns'].append(f"重复开头: '{words}...' (出现{count}次)")
                    break
    
    return results


def detect_ai_vocabulary(text: str) -> Dict:
    """
    检测AI高频词汇
    """
    # AI最常用的词汇列表（学术写作中）
    ai_words = {
        # 描述性词汇
        'exhibit', 'characteristics', 'demonstrate', 'illustrate',
        'significant', 'substantial', 'considerable', 'notable',
        'crucial', 'essential', 'fundamental', 'vital',
        'comprehensive', 'extensive', 'thorough',
        # 连接词
        'moreover', 'furthermore', 'consequently', 'therefore',
        'nevertheless', 'nonetheless',
        # 强调词
        'emphasize', 'highlight', 'underscore',
        # 新增：AI常用描述性词汇
        'distinct', 'typical', 'various', 'numerous', 'multiple',
        'particular', 'specific', 'certain', 'prominent'
    }
    
    # 清理文本，提取单词
    words = re.findall(r'\b\w+\b', text.lower())
    total_words = len(words)
    
    # 统计AI词汇
    ai_words_found = [w for w in words if w in ai_words]
    ai_word_count = len(ai_words_found)
    ai_word_density = ai_word_count / total_words if total_words > 0 else 0
    
    # 统计唯一AI词汇
    unique_ai_words = list(set(ai_words_found))
    
    # 检测AI典型短语组合
    ai_combinations = []
    ai_combination_patterns = [
        (r'\bexhibit\s+(?:distinct|typical|various|certain|specific)\s+characteristics\b', 'exhibit_[adj]_characteristics'),
        (r'\bdemonstrate\s+(?:significant|considerable|substantial)\s+(?:impact|effect)\b', 'demonstrate_[adj]_impact'),
        (r'\bplay\s+a\s+(?:crucial|vital|significant|key)\s+role\b', 'play_[adj]_role'),
    ]
    
    text_lower = text.lower()
    for pattern, name in ai_combination_patterns:
        if re.search(pattern, text_lower):
            ai_combinations.append(name)
    
    return {
        'ai_word_count': ai_word_count,
        'ai_word_density': ai_word_density,
        'unique_ai_words': unique_ai_words,
        'total_words': total_words,
        'ai_combinations': ai_combinations  # 新增
    }


def detect_perfect_citations(text: str) -> Dict:
    """
    检测完美的引用格式
    """
    # 匹配标准学术引用格式
    patterns = [
        r'\([A-Z][a-z]+\s+et\s+al\.?,?\s+\d{4}\)',  # (Author et al., 2021)
        r'\([A-Z][a-z]+\s*&\s*[A-Z][a-z]+,?\s+\d{4}\)',  # (Author & Author, 2021)
        r'\([A-Z][a-z]+,?\s+\d{4}\)',  # (Author, 2021)
    ]
    
    citations = []
    for pattern in patterns:
        matches = re.findall(pattern, text)
        citations.extend(matches)
    
    return {
        'citation_count': len(citations),
        'citations': citations,
        'has_perfect_format': len(citations) > 0
    }


def compute_burstiness_improved(text: str) -> Dict:
    """
    改进的爆发度计算 - 不在分号处分割句子
    """
    sentences = split_sentences_improved(text)
    
    if len(sentences) < 2:
        return {
            'sentence_count': len(sentences),
            'sentence_lengths': [len(s.split()) for s in sentences],
            'length_mean': 0,
            'length_std': 0,
            'length_burstiness': 0.5,
            'start_variety': 0.5,
            'punct_variety': 0.5,
            'overall_burstiness': 0.5
        }
    
    # 句子长度分析
    lengths = [len(s.split()) for s in sentences]
    mean_len = mean(lengths)
    std_len = std(lengths)
    length_burstiness = std_len / mean_len if mean_len > 0 else 0
    
    # 句子开头多样性
    starts = [s.split()[0] if s.split() else "" for s in sentences]
    start_variety = len(set(starts)) / len(starts) if starts else 0
    
    # 标点多样性
    puncts = re.findall(r'[.!?,;:]', text)
    punct_variety = len(set(puncts)) / len(puncts) if puncts else 0
    
    # 综合爆发度
    overall = mean([length_burstiness, start_variety, punct_variety])
    
    return {
        'sentence_count': len(sentences),
        'sentence_lengths': lengths,
        'length_mean': mean_len,
        'length_std': std_len,
        'length_burstiness': length_burstiness,
        'start_variety': start_variety,
        'punct_variety': punct_variety,
        'overall_burstiness': overall
    }


def calculate_ai_score_improved(
    burstiness: Dict,
    parallel_structures: Dict,
    repetitive_structures: Dict,
    vocabulary: Dict,
    citations: Dict
) -> Tuple[int, List[str], str]:
    """
    改进的AI评分算法
    
    Returns:
        (score, indicators, likelihood)
    """
    score = 0
    indicators = []
    
    # 1. 平行结构评分 (最高40分) - 这是最强的AI特征
    if parallel_structures['colon_semicolon_pattern'] > 0:
        score += 40
        indicators.append(f"检测到{parallel_structures['colon_semicolon_pattern']}个冒号+分号平行结构（强AI特征）")
    
    if parallel_structures['semicolon_and_pattern'] > 0:
        score += 30
        indicators.append(f"检测到{parallel_structures['semicolon_and_pattern']}个分号+and平行结构（AI特征）")
    
    if parallel_structures['multiple_semicolons'] > 0:
        # 多个分号但不是上面两种情况
        if parallel_structures['colon_semicolon_pattern'] == 0 and parallel_structures['semicolon_and_pattern'] == 0:
            score += 20
            indicators.append(f"检测到{parallel_structures['multiple_semicolons']}个多分号复杂句")
    
    # 序列化列举（AI常用）
    if parallel_structures['ordinal_enumeration'] > 0:
        score += 25
        indicators.append(f"检测到序列化列举（First, Second, Third等）- 典型AI特征")
    
    # 1.5 重复句式评分 (最高20分)
    if repetitive_structures['count'] > 0:
        score += 20
        for pattern in repetitive_structures['repetitive_patterns']:
            indicators.append(pattern)
    
    # 2. AI词汇评分 (最高30分)
    if vocabulary['ai_word_density'] > 0.04:
        score += 30
        indicators.append(f"AI词汇密度极高（{vocabulary['ai_word_density']:.1%}）")
    elif vocabulary['ai_word_density'] > 0.025:
        score += 20
        indicators.append(f"AI词汇密度偏高（{vocabulary['ai_word_density']:.1%}）")
    elif vocabulary['ai_word_density'] > 0.015:
        score += 10
        indicators.append(f"含有一定AI词汇（{vocabulary['ai_word_density']:.1%}）")
    
    # 检测AI典型短语组合 - 提高权重
    ai_combinations = vocabulary.get('ai_combinations', [])
    if ai_combinations:
        combination_bonus = len(ai_combinations) * 20  # 每个组合加20分
        score += combination_bonus
        for combo in ai_combinations:
            indicators.append(f"⚠️ 检测到AI高度典型短语: {combo}")
    
    # 特殊加分：出现"exhibit"和"characteristics"词汇（即使不在一起）
    if 'exhibit' in vocabulary['unique_ai_words'] and 'characteristics' in vocabulary['unique_ai_words']:
        if not ai_combinations:  # 如果上面没有检测到组合模式，这里给一些分
            score += 10
            indicators.append("出现AI常用词汇: exhibit + characteristics")
    
    # 3. 爆发度评分 (最高20分)
    if burstiness['overall_burstiness'] < 0.25:
        score += 20
        indicators.append(f"爆发度极低（{burstiness['overall_burstiness']:.3f}）")
    elif burstiness['overall_burstiness'] < 0.35:
        score += 15
        indicators.append(f"爆发度偏低（{burstiness['overall_burstiness']:.3f}）")
    elif burstiness['overall_burstiness'] < 0.45:
        score += 8
    
    # 4. 引用格式评分 (最高20分) - 提高权重
    if citations['citation_count'] >= 4:
        score += 20
        indicators.append(f"多个完美引用格式（{citations['citation_count']}个）- AI倾向明显")
    elif citations['citation_count'] >= 3:
        score += 15
        indicators.append(f"多个完美引用格式（{citations['citation_count']}个）")
    elif citations['citation_count'] >= 2:
        score += 10
        indicators.append(f"含有完美引用格式（{citations['citation_count']}个）")
    elif citations['citation_count'] >= 1:
        score += 5
        indicators.append(f"含有完美引用格式（{citations['citation_count']}个）")
    
    # 确定可能性等级 - 进一步降低阈值，提高检测灵敏度
    if score >= 40:  # 从50降到40
        likelihood = "高 - AI生成可能性大"
    elif score >= 30:  # 从35降到30
        likelihood = "中等偏高 - 很可能是AI生成"
    elif score >= 25:  # 从30降到25
        likelihood = "中等 - 可能是AI生成"
    elif score >= 18:  # 从20降到18
        likelihood = "低中 - 有一定AI倾向"
    else:
        likelihood = "低 - 更可能是人类写作"
    
    return score, indicators, likelihood


def analyze_text_improved(text: str, text_name: str = "") -> Dict:
    """
    改进的文本分析主函数
    
    Args:
        text: 要分析的文本
        text_name: 文本名称（用于显示）
    
    Returns:
        分析结果字典
    """
    # 1. 爆发度分析
    burstiness = compute_burstiness_improved(text)
    
    # 2. 平行结构检测
    parallel_structures = detect_parallel_structures_improved(text)
    
    # 3. 重复句式检测
    repetitive_structures = detect_repetitive_sentence_structures(text)
    
    # 4. AI词汇检测
    vocabulary = detect_ai_vocabulary(text)
    
    # 5. 引用格式检测
    citations = detect_perfect_citations(text)
    
    # 6. 计算AI评分
    ai_score, indicators, likelihood = calculate_ai_score_improved(
        burstiness, parallel_structures, repetitive_structures, vocabulary, citations
    )
    
    # 判断是否为AI生成（降低阈值到30分）
    is_ai_generated = ai_score >= 30
    
    return {
        'text_name': text_name,
        'is_ai_generated': is_ai_generated,
        'ai_score': ai_score,
        'likelihood': likelihood,
        'indicators': indicators,
        'burstiness': burstiness,
        'parallel_structures': parallel_structures,
        'repetitive_structures': repetitive_structures,
        'vocabulary': vocabulary,
        'citations': citations
    }


def print_analysis_report(result: Dict, verbose: bool = True):
    """
    打印分析报告
    """
    print("\n" + "=" * 80)
    if result['text_name']:
        print(f"分析: {result['text_name']}")
        print("=" * 80)
    
    # 基本判断
    status_icon = "❌" if result['is_ai_generated'] else "✅"
    print(f"\n{status_icon} 判断结果: {result['likelihood']}")
    print(f"AI评分: {result['ai_score']}/100")
    
    # 关键指标
    if result['indicators']:
        print(f"\n关键指标:")
        for i, indicator in enumerate(result['indicators'], 1):
            print(f"  {i}. {indicator}")
    
    if verbose:
        # 详细信息
        print(f"\n详细分析:")
        
        # 平行结构
        parallel = result['parallel_structures']
        print(f"\n  平行结构:")
        print(f"    - 冒号+分号模式: {parallel['colon_semicolon_pattern']}")
        print(f"    - 分号+and模式: {parallel['semicolon_and_pattern']}")
        print(f"    - 多分号句: {parallel['multiple_semicolons']}")
        print(f"    - 序列化列举: {parallel['ordinal_enumeration']}")
        if parallel['patterns_found']:
            print(f"    发现的模式:")
            for pattern in parallel['patterns_found'][:3]:  # 只显示前3个
                print(f"      • {pattern}")
        
        # 重复句式
        repetitive = result['repetitive_structures']
        if repetitive['count'] > 0:
            print(f"\n  重复句式:")
            print(f"    - 检测到: {repetitive['count']}种")
            for pattern in repetitive['repetitive_patterns']:
                print(f"      • {pattern}")
        
        # AI词汇
        vocab = result['vocabulary']
        print(f"\n  AI词汇:")
        print(f"    - 密度: {vocab['ai_word_density']:.1%}")
        print(f"    - 数量: {vocab['ai_word_count']} / {vocab['total_words']}")
        if vocab['unique_ai_words']:
            print(f"    - 发现: {', '.join(vocab['unique_ai_words'])}")
        
        # 爆发度
        burst = result['burstiness']
        print(f"\n  爆发度:")
        print(f"    - 总体: {burst['overall_burstiness']:.3f}")
        print(f"    - 句子数: {burst['sentence_count']}")
        if burst['sentence_count'] >= 2:
            print(f"    - 平均长度: {burst['length_mean']:.1f} 词")
            print(f"    - 长度变化: {burst['length_burstiness']:.3f}")
        
        # 引用
        cite = result['citations']
        print(f"\n  引用格式:")
        print(f"    - 数量: {cite['citation_count']}")
        if cite['citations']:
            print(f"    - 示例: {', '.join(cite['citations'][:3])}")
    
    print()

