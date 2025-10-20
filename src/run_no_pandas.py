#!/usr/bin/env python3
"""
完全不依赖pandas的完整pipeline
"""

import sys
import os
import time
from pathlib import Path

def main(pdf_path):
    """运行完整pipeline"""
    print(f"🚀 开始处理: {pdf_path}")
    start_time = time.time()
    
    # 确保输出目录存在
    Path("outputs").mkdir(exist_ok=True)
    
    try:
        # 步骤1: PDF转文本
        print("\n1. 📄 提取PDF文本...")
        from src.pdf_to_text import extract_text_from_pdf
        text = extract_text_from_pdf(pdf_path)
        print(f"   ✅ 提取了 {len(text)} 字符")
        
        if len(text) < 100:
            print("   ⚠️  警告: 提取的文本可能不完整")
            return
        
        # 步骤2: IMRaD解析
        print("\n2. 🔍 提取IMRaD节点...")
        from src.extract_imrad import extract_imrad_from_text
        nodes = extract_imrad_from_text(text)
        print(f"   ✅ 提取了 {len(nodes)} 个节点")
        
        if len(nodes) == 0:
            print("   ⚠️  警告: 未提取到任何节点")
            return
        
        # 显示节点类型统计
        from collections import Counter
        node_types = Counter([node['type'] for node in nodes])
        print(f"   📊 节点类型分布: {dict(node_types)}")
        
        # 显示一些示例节点
        print("\n   📝 示例节点:")
        for i, node in enumerate(nodes[:3]):
            print(f"      {i+1}. [{node['type']}] {node['text'][:80]}...")
        
        # 步骤3: 构建图谱 - 使用不依赖pandas的版本
        print("\n3. 🔗 构建边关系...")
        from src.build_graph_no_pandas import build_edges, export_to_csv
        edges = build_edges(nodes)
        print(f"   ✅ 构建了 {len(edges)} 条边")
        
        # 步骤4: 导出和可视化
        print("\n4. 💾 导出和可视化...")
        
        # 导出CSV - 使用不依赖pandas的版本
        base_name = Path(pdf_path).stem
        export_to_csv(nodes, edges, f"outputs/{base_name}")
        
        # 可视化
        try:
            from src.visualize_graph import visualize_knowledge_graph
            visualize_knowledge_graph(nodes, edges, f"outputs/{base_name}_graph.html")
        except Exception as e:
            print(f"   ⚠️  可视化失败: {e}")
        
        elapsed_time = time.time() - start_time
        print(f"\n🎉 处理完成! 用时 {elapsed_time:.2f} 秒!")
        print(f"📊 最终结果: {len(nodes)} 个节点, {len(edges)} 条边")
        print(f"📁 输出文件:")
        print(f"   - CSV节点: outputs/{base_name}_nodes.csv")
        print(f"   - CSV边: outputs/{base_name}_edges.csv") 
        print(f"   - 可视化: outputs/{base_name}_graph.html")
        
    except Exception as e:
        print(f"❌ 运行过程中出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python run_no_pandas.py <pdf_file>")
        print("Example: python run_no_pandas.py data/artemisinin_pcos.pdf")
        sys.exit(1)
    
    pdf_file = sys.argv[1]
    if not os.path.exists(pdf_file):
        print(f"错误: 文件不存在 {pdf_file}")
        sys.exit(1)
    
    main(pdf_file)