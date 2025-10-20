import sys
import os
import json
import csv
from pathlib import Path
from typing import List, Dict, Any
from collections import defaultdict

# 边规则定义
EDGE_RULES = [
    ("Hypothesis", "Experiment", "hypothesis_to_experiment"),
    ("Experiment", "Dataset", "experiment_to_dataset"), 
    ("Dataset", "Analysis", "dataset_to_analysis"),
    ("Analysis", "Conclusion", "analysis_to_conclusion"),
]

def build_edges(nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """构建边关系 - 不使用pandas"""
    edges = []
    
    if not nodes:
        print("⚠️  没有节点可用于构建边")
        return edges
    
    # 按类型分组节点
    nodes_by_type = defaultdict(list)
    for node in nodes:
        nodes_by_type[node["type"]].append(node)
    
    print(f"📊 节点类型分布: {{ {', '.join([f'{k}:{len(v)}' for k, v in nodes_by_type.items()])} }}")
    
    # 应用边规则
    for src_type, tgt_type, rel_type in EDGE_RULES:
        if src_type in nodes_by_type and tgt_type in nodes_by_type:
            src_nodes = nodes_by_type[src_type]
            tgt_nodes = nodes_by_type[tgt_type]
            
            for src_node in src_nodes:
                for tgt_node in tgt_nodes:
                    edges.append({
                        "start": src_node["id"],
                        "end": tgt_node["id"], 
                        "type": rel_type,
                        "confidence": min(src_node.get("confidence", 0.5), tgt_node.get("confidence", 0.5))
                    })
            
            print(f"  🔗 创建了 {len(src_nodes)}×{len(tgt_nodes)} = {len(src_nodes)*len(tgt_nodes)} 条 {rel_type} 边")
    
    return edges

def export_to_csv(nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]], base_name: str):
    """导出为CSV文件 - 不使用pandas"""
    # 确保输出目录存在
    Path("outputs").mkdir(exist_ok=True)
    
    # 节点CSV
    if nodes:
        nodes_file = f"{base_name}_nodes.csv"
        with open(nodes_file, 'w', newline='', encoding='utf-8') as f:
            if nodes:
                fieldnames = nodes[0].keys()
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(nodes)
        print(f"  💾 节点保存: {nodes_file} (共 {len(nodes)} 个)")
    else:
        print("  ⚠️  没有节点可保存")
    
    # 边CSV  
    if edges:
        edges_file = f"{base_name}_edges.csv"
        with open(edges_file, 'w', newline='', encoding='utf-8') as f:
            if edges:
                fieldnames = edges[0].keys()
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(edges)
        print(f"  💾 边保存: {edges_file} (共 {len(edges)} 条)")
    else:
        print("  ⚠️  没有边可保存")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python build_graph_no_pandas.py <nodes_json_file>")
        sys.exit(1)
    
    nodes_file = sys.argv[1]
    if not os.path.exists(nodes_file):
        print(f"错误: 文件不存在 {nodes_file}")
        sys.exit(1)
    
    try:
        with open(nodes_file, "r", encoding="utf-8") as f:
            nodes = json.load(f)
        
        print(f"📁 从 {nodes_file} 加载了 {len(nodes)} 个节点")
        
        # 构建边
        edges = build_edges(nodes)
        
        # 导出CSV
        base_name = nodes_file.replace("_nodes.json", "")
        export_to_csv(nodes, edges, base_name)
        
        print(f"✅ 处理完成! 保存了 {len(nodes)} 个节点和 {len(edges)} 条边")
        
    except Exception as e:
        print(f"❌ 处理失败: {e}")
        import traceback
        traceback.print_exc()