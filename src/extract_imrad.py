import re
import sys
import os
import json
from pathlib import Path
from typing import List, Dict, Any
from collections import Counter

# 添加utils导入
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from src.utils import CUE_PATTERNS, sentence_segmentation, gen_id

def create_node(node_type: str, text: str, section: str, confidence: float = 0.9, evidence: str = "") -> Dict[str, Any]:
    """创建节点"""
    return {
        "id": gen_id(node_type[:3].upper()),
        "type": node_type,
        "text": text.strip(),
        "section": section,
        "confidence": confidence,
        "evidence": evidence
    }

def extract_nodes_from_section(section_name: str, text: str) -> List[Dict[str, Any]]:
    """从章节文本提取节点"""
    sentences = sentence_segmentation(text)
    nodes = []
    
    for sentence in sentences:
        matched = False
        for node_type, patterns in CUE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, sentence, re.IGNORECASE):
                    nodes.append(create_node(
                        node_type, sentence, section_name, 
                        evidence=f"pattern:{pattern}",
                        confidence=0.85
                    ))
                    matched = True
                    break
            if matched:
                break
        # 如果没有匹配到任何模式，跳过该句子
    
    return nodes

def extract_imrad_from_text(text: str) -> List[Dict[str, Any]]:
    """从完整文本提取IMRaD节点 - 这是缺失的关键函数！"""
    try:
        from src.pdf_to_text import segment_imrad
    except ImportError as e:
        print(f"导入segment_imrad失败: {e}")
        # 备用分段方法
        def simple_segment_imrad(text):
            sections = {}
            current_section = "body"
            sections[current_section] = text
            return sections
        segment_imrad = simple_segment_imrad
    
    sections = segment_imrad(text)
    all_nodes = []
    
    print(f"📑 发现 {len(sections)} 个章节: {list(sections.keys())}")
    
    for section_name, section_text in sections.items():
        if len(section_text.strip()) < 50:  # 跳过太短的章节
            continue
            
        print(f"  处理章节: {section_name} (长度: {len(section_text)} 字符)")
        nodes = extract_nodes_from_section(section_name, section_text)
        print(f"    在 {section_name} 中提取了 {len(nodes)} 个节点")
        all_nodes.extend(nodes)
    
    # 统计节点类型
    if all_nodes:
        node_types = Counter([node["type"] for node in all_nodes])
        print(f"📊 节点类型分布: {dict(node_types)}")
    
    return all_nodes

# 为了兼容性，也添加旧函数名
extract_imrad_nodes = extract_imrad_from_text

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python extract_imrad.py <text_file>")
        sys.exit(1)
    
    text_file = sys.argv[1]
    if not os.path.exists(text_file):
        print(f"Error: File {text_file} not found")
        sys.exit(1)
    
    with open(text_file, "r", encoding="utf-8") as f:
        text = f.read()
    
    nodes = extract_imrad_from_text(text)
    
    # 保存节点
    output_file = text_file.replace(".txt", "_nodes.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(nodes, f, indent=2, ensure_ascii=False)
    
    print(f"Extracted {len(nodes)} nodes to {output_file}")