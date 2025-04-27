import asyncio
import sys
from app.services.ai_detection_service import detect_ai_content

async def test_detection():
    """测试AI内容检测功能"""
    print("开始AI内容检测测试...")
    
    test_text = """
    人工智能（Artificial Intelligence，缩写为AI）是计算机科学的一个分支，它企图了解智能的实质，并生产出一种新的能以人类智能相似的方式做出反应的智能机器，该领域的研究包括机器人、语言识别、图像识别、自然语言处理和专家系统等。人工智能从诞生以来，理论和技术日益成熟，应用领域也不断扩大，可以设想，未来人工智能带来的科技产品，将会是人类智慧的"容器"。人工智能可以对人的意识、思维的信息过程的模拟。人工智能不是人的智能，但能像人那样思考、也可能超过人的智能。
    
    人工智能是一门极富挑战性的科学，从事这项工作的人必须懂得计算机知识、心理学和哲学。人工智能是包括十分广泛的科学，它由不同的领域组成，如机器学习、计算机视觉等等，总的说来，人工智能研究的一个主要目标是使机器能够胜任一些通常需要人类智能才能完成的复杂工作。但不同的时代、不同的人对这种"复杂工作"的理解是不同的。
    """
    
    try:
        ai_percentage, paragraph_analyses = await detect_ai_content(test_text)
        
        print(f"\n检测结果: AI内容比例 {ai_percentage:.2f}%\n")
        
        print("段落分析:")
        for i, analysis in enumerate(paragraph_analyses):
            print(f"\n段落 {i+1}:")
            print(f"- AI生成: {'是' if analysis.ai_generated else '否'}")
            print(f"- 置信度: {analysis.confidence:.2f}%")
            print(f"- 原因: {analysis.reason}")
            
            if analysis.metrics:
                print("\n指标数据:")
                if "burstiness" in analysis.metrics:
                    print(f"- 爆发度: {analysis.metrics['burstiness']:.4f}")
                if "syntax_analysis" in analysis.metrics:
                    print(f"- 句式重复度: {analysis.metrics['syntax_analysis']['repetition_score']:.4f}")
                    print(f"- 可疑句式: {'是' if analysis.metrics['syntax_analysis']['is_suspicious'] else '否'}")
                if "style_analysis" in analysis.metrics:
                    print(f"- 风格一致性方差: {analysis.metrics['style_analysis']['style_variance']:.4f}")
                    print(f"- 风格可疑: {'是' if analysis.metrics['style_analysis']['is_suspicious'] else '否'}")
        
        print("\n测试完成!")
        
    except Exception as e:
        print(f"测试过程中出错: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_detection()) 