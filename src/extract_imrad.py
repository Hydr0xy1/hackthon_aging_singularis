import re
import sys
import os
import json
from pathlib import Path
from typing import List, Dict, Any
from collections import Counter

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from src.utils import CUE_PATTERNS, sentence_segmentation, gen_id

def create_node(node_type: str, text: str, section: str, confidence: float = 0.9, evidence: str = "") -> Dict[str, Any]:
    """create nodes"""
    return {
        "id": gen_id(node_type[:3].upper()),
        "type": node_type,
        "text": text.strip(),
        "section": section,
        "confidence": confidence,
        "evidence": evidence
    }

def extract_nodes_from_section(section_name: str, text: str) -> List[Dict[str, Any]]:
    """extract_nodes_from_section"""
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
    
    return nodes

def extract_imrad_from_text(text: str) -> List[Dict[str, Any]]:
    """extract IMRaD nodes rom complete text."""
    try:
        from src.pdf_to_text import segment_imrad
    except ImportError as e:
        print(f"Failed to import segment_imrad: {e}")
        def simple_segment_imrad(text):
            sections = {}
            current_section = "body"
            sections[current_section] = text
            return sections
        segment_imrad = simple_segment_imrad
    
    sections = segment_imrad(text)
    all_nodes = []
    
    print(f"📑 Find {len(sections)} sections: {list(sections.keys())}")
    
    for section_name, section_text in sections.items():
        if len(section_text.strip()) < 50:  # 跳过太短的章节
            continue
            
        print(f"  Deal with: {section_name} (length: {len(section_text)} characters)")
        nodes = extract_nodes_from_section(section_name, section_text)
        print(f"   Extract {len(nodes)} nodes from {section_name}")
        all_nodes.extend(nodes)
    
    # 统计节点类型
    if all_nodes:
        node_types = Counter([node["type"] for node in all_nodes])
        print(f"📊 node distribution type: {dict(node_types)}")
    
    return all_nodes

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
    
    output_file = text_file.replace(".txt", "_nodes.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(nodes, f, indent=2, ensure_ascii=False)
    
    print(f"Extracted {len(nodes)} nodes to {output_file}")