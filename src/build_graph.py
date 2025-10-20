import sys
import os
import json
import pandas as pd
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
    """构建边关系 - 这是缺失的关键函数！"""
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
            
            # 简单策略：连接每个源节点到每个目标节点
            for src_node in src_nodes:
                for tgt_node in tgt_nodes:
                    edges.append({
                        "start": src_node["id"],
                        "end": tgt_node["id"], 
                        "type": rel_type,
                        "confidence": min(src_node.get("confidence", 0.5), tgt_node.get("confidence", 0.5))
                    })
            
            print(f"  🔗 创建了 {len(src_nodes)}×{len(tgt_nodes)} = {len(src_nodes)*len(tgt_nodes)} 条 {rel_type} 边")
        else:
            missing_src = src_type not in nodes_by_type
            missing_tgt = tgt_type not in nodes_by_type
            if missing_src and missing_tgt:
                print(f"  ⚠️  跳过 {rel_type}: 缺少 {src_type} 和 {tgt_type}")
            elif missing_src:
                print(f"  ⚠️  跳过 {rel_type}: 缺少 {src_type}")
            else:
                print(f"  ⚠️  跳过 {rel_type}: 缺少 {tgt_type}")
    
    return edges

def export_to_csv(nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]], base_name: str):
    """导出为CSV文件"""
    # 确保输出目录存在
    Path("outputs").mkdir(exist_ok=True)
    
    # 节点CSV
    if nodes:
        nodes_df = pd.DataFrame(nodes)
        # 重新排列列的顺序，让id和type在前面
        preferred_order = ['id', 'type', 'text', 'section', 'confidence', 'evidence']
        existing_columns = [col for col in preferred_order if col in nodes_df.columns]
        other_columns = [col for col in nodes_df.columns if col not in preferred_order]
        nodes_df = nodes_df[existing_columns + other_columns]
        
        nodes_file = f"{base_name}_nodes.csv"
        nodes_df.to_csv(nodes_file, index=False, encoding='utf-8')
        print(f"  💾 节点保存: {nodes_file} (共 {len(nodes)} 个)")
    else:
        print("  ⚠️  没有节点可保存")
    
    # 边CSV  
    if edges:
        edges_df = pd.DataFrame(edges)
        edges_file = f"{base_name}_edges.csv"
        edges_df.to_csv(edges_file, index=False, encoding='utf-8')
        print(f"  💾 边保存: {edges_file} (共 {len(edges)} 条)")
    else:
        print("  ⚠️  没有边可保存")

def create_simple_edges(nodes: List[Dict[str, Any]], strategy: str = "sequential") -> List[Dict[str, Any]]:
    """创建简单边关系（备选方案）"""
    edges = []
    
    if strategy == "sequential":
        # 顺序连接：节点0→1→2→3...
        for i in range(len(nodes) - 1):
            edges.append({
                "start": nodes[i]["id"],
                "end": nodes[i+1]["id"],
                "type": "connected_to",
                "confidence": min(nodes[i].get("confidence", 0.5), nodes[i+1].get("confidence", 0.5))
            })
    
    elif strategy == "by_section":
        # 按章节分组连接
        sections = {}
        for node in nodes:
            section = node.get("section", "unknown")
            if section not in sections:
                sections[section] = []
            sections[section].append(node)
        
        for section_name, section_nodes in sections.items():
            if len(section_nodes) > 1:
                for i in range(len(section_nodes) - 1):
                    edges.append({
                        "start": section_nodes[i]["id"],
                        "end": section_nodes[i+1]["id"],
                        "type": f"in_{section_name}",
                        "confidence": min(section_nodes[i].get("confidence", 0.5), section_nodes[i+1].get("confidence", 0.5))
                    })
    
    return edges

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python build_graph.py <nodes_json_file>")
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
        
        # 如果规则边太少，添加简单边
        if len(edges) < len(nodes) // 2:
            print("📈 添加顺序边以增强连接性...")
            simple_edges = create_simple_edges(nodes, "sequential")
            edges.extend(simple_edges)
            print(f"  添加了 {len(simple_edges)} 条顺序边")
        
        # 导出CSV
        base_name = nodes_file.replace("_nodes.json", "")
        export_to_csv(nodes, edges, base_name)
        
        # 保存完整图谱
        graph = {"nodes": nodes, "edges": edges}
        graph_file = f"{base_name}_graph.json"
        with open(graph_file, "w", encoding="utf-8") as f:
            json.dump(graph, f, indent=2, ensure_ascii=False)
        
        print(f"💾 图谱保存: {graph_file}")
        
    except Exception as e:
        print(f"❌ 处理失败: {e}")
        import traceback
        traceback.print_exc()