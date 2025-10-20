#!/usr/bin/env python3
"""
主pipeline运行脚本
用法: python run_pipeline.py <pdf_file>
"""

import sys
import os
import time
from pathlib import Path

# 添加src到路径
sys.path.append('src')

from src.pdf_to_text import extract_text_from_pdf
from src.extract_imrad import extract_imrad_from_text
from src.build_graph import build_edges, export_to_csv
from src.visualize_graph import visualize_knowledge_graph

def main(pdf_path):
    """运行完整pipeline"""
    print(f"🚀 Starting pipeline for: {pdf_path}")
    start_time = time.time()
    
    # 确保输出目录存在
    Path("outputs").mkdir(exist_ok=True)
    
    # 步骤1: PDF转文本
    print("1. Extracting text from PDF...")
    text = extract_text_from_pdf(pdf_path)
    print(f"   Extracted {len(text)} characters")
    
    # 步骤2: IMRaD解析
    print("2. Extracting IMRaD nodes...")
    nodes = extract_imrad_from_text(text)
    print(f"   Extracted {len(nodes)} nodes")
    
    # 步骤3: 构建图谱
    print("3. Building graph edges...")
    edges = build_edges(nodes)
    print(f"   Built {len(edges)} edges")
    
    # 步骤4: 导出和可视化
    print("4. Exporting and visualizing...")
    
    # 导出CSV
    base_name = Path(pdf_path).stem
    export_to_csv(nodes, edges, f"outputs/{base_name}")
    
    # 可视化
    visualize_knowledge_graph(nodes, edges, f"outputs/{base_name}_graph.html")
    
    elapsed_time = time.time() - start_time
    print(f"✅ Pipeline completed in {elapsed_time:.2f} seconds!")
    print(f"   - Nodes CSV: outputs/{base_name}_nodes.csv")
    print(f"   - Edges CSV: outputs/{base_name}_edges.csv") 
    print(f"   - Graph HTML: outputs/{base_name}_graph.html")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python run_pipeline.py <pdf_file>")
        print("Example: python run_pipeline.py data/example_paper.pdf")
        sys.exit(1)
    
    pdf_file = sys.argv[1]
    if not os.path.exists(pdf_file):
        print(f"Error: File {pdf_file} not found")
        sys.exit(1)
    
    main(pdf_file)