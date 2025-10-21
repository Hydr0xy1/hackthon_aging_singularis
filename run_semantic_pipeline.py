#!/usr/bin/env python3
"""
语义感知的IMRaD知识图谱提取系统
解决同一单词在不同语境中的语义歧义问题
"""

import sys
import os
import time
import json
import csv
from pathlib import Path
from typing import List, Dict, Any
from collections import defaultdict, Counter

# 导入语义提取器
try:
    from src.semantic_extractor import SemanticIMRaDExtractor
    SEMANTIC_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  语义提取器导入失败: {e}")
    SEMANTIC_AVAILABLE = False

# 导入其他必要模块
try:
    import fitz
    import re
    import uuid
    from collections import Counter, defaultdict
except ImportError as e:
    print(f"❌ 导入失败: {e}")
    sys.exit(1)

class SemanticIMRaDPipeline:
    """语义感知的IMRaD处理管道"""
    
    def __init__(self):
        self.semantic_extractor = SemanticIMRaDExtractor() if SEMANTIC_AVAILABLE else None
        
        # IMRaD章节模式
        self.section_patterns = {
            "introduction": r"(?:^|\n)(?:\s*\d*\.*\s*Introduction|Background)",
            "methods": r"(?:^|\n)(?:\s*\d*\.*\s*(Materials and Methods|Methods|Experimental Procedures))",
            "results": r"(?:^|\n)(?:\s*\d*\.*\s*Results?)",
            "discussion": r"(?:^|\n)(?:\s*\d*\.*\s*(Discussion|Conclusion|Summary))",
        }
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """从PDF提取文本"""
        print(f"📄 从 {os.path.basename(pdf_path)} 提取文本...")
        try:
            doc = fitz.open(pdf_path)
            text = ""
            for page_num, page in enumerate(doc):
                page_text = page.get_text("text")
                # 清理文本
                lines = []
                for line in page_text.split("\n"):
                    line = line.strip()
                    if (not re.match(r"^\s*\d+\s*$", line) and 
                        len(line) > 15 and
                        not line.isupper() and
                        not re.match(r'^\s*[A-Z\s]+\s*$', line)):
                        lines.append(line)
                text += " ".join(lines) + "\n\n"
            doc.close()
            return text
        except Exception as e:
            print(f"❌ PDF提取错误: {e}")
            return ""
    
    def segment_imrad(self, text: str) -> Dict[str, str]:
        """IMRaD分段"""
        indices = []
        for name, pattern in self.section_patterns.items():
            matches = list(re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE))
            if matches:
                indices.append((matches[0].start(), name))
        
        if not indices:
            print("⚠️  未检测到标准IMRaD章节，使用全文处理")
            return {"full_text": text}

        indices.sort()
        sections = {}
        
        for i, (start, name) in enumerate(indices):
            end = indices[i + 1][0] if i + 1 < len(indices) else len(text)
            section_content = text[start:end].strip()
            
            # 移除章节标题行
            lines = section_content.split('\n')
            if len(lines) > 1:
                section_content = '\n'.join(lines[1:]).strip()
            
            sections[name] = section_content
        
        return sections
    
    def extract_nodes_semantic(self, text: str) -> List[Dict[str, Any]]:
        """使用语义理解提取节点"""
        if not self.semantic_extractor:
            print("⚠️  语义提取器不可用，使用传统方法")
            return self._extract_nodes_traditional(text)
        
        print("🧠 使用语义理解提取节点...")
        sections = self.segment_imrad(text)
        nodes = self.semantic_extractor.extract_nodes_with_semantics(text, sections)
        
        # 统计节点类型
        if nodes:
            node_types = Counter([node["type"] for node in nodes])
            print(f"📊 语义节点类型分布: {dict(node_types)}")
            
            # 显示语义消歧示例
            disambiguation_examples = [n for n in nodes if n.get("semantic_context", {}).get("disambiguation_applied")]
            if disambiguation_examples:
                print(f"🔍 应用了语义消歧的节点: {len(disambiguation_examples)} 个")
                for example in disambiguation_examples[:3]:  # 显示前3个示例
                    print(f"   - {example['type']}: {example['text'][:60]}...")
        
        return nodes
    
    def _extract_nodes_traditional(self, text: str) -> List[Dict[str, Any]]:
        """传统正则表达式方法（备用）"""
        print("📝 使用传统正则表达式方法...")
        
        # 传统模式
        cue_patterns = {
            "Hypothesis": [
                r"\bwe hypothesi[sz]e\b", r"\bwe propose\b", r"\bthis study aims to\b",
                r"\bwe expect\b", r"\bwe predict\b", r"\bit is hypothesized\b"
            ],
            "Experiment": [
                r"\bwe conducted\b", r"\bwe performed\b", r"\bexperiments\b",
                r"\bwe treated\b", r"\bmethods\b", r"\bexperimental\b"
            ],
            "Dataset": [
                r"\bcohort\b", r"\bn\s*=\s*\d+", r"\bdata from\b",
                r"\bpatients\b", r"\bsamples\b", r"\bdataset\b"
            ],
            "Analysis": [
                r"\bwe analyzed\b", r"\bstatistical analysis\b", r"\bp\s*[<≤]\s*0\.\d+",
                r"\bsignificant\b", r"\bwe calculated\b", r"\bcorrelation\b"
            ],
            "Conclusion": [
                r"\bin conclusion\b", r"\bwe conclude\b", r"\bthese results suggest\b",
                r"\bthis study shows\b", r"\bour findings\b", r"\bthese data indicate\b"
            ]
        }
        
        sections = self.segment_imrad(text)
        nodes = []
        
        for section_name, section_text in sections.items():
            if len(section_text.strip()) < 100:
                continue
            
            # 简单句子分割
            sentences = re.split(r'(?<=[.!?])\s+', section_text)
            for sentence in sentences:
                sentence = sentence.strip()
                if len(sentence) < 20:
                    continue
                
                matched = False
                for node_type, patterns in cue_patterns.items():
                    for pattern in patterns:
                        if re.search(pattern, sentence, re.IGNORECASE):
                            nodes.append({
                                "id": f"{node_type[:3].upper()}_{uuid.uuid4().hex[:6]}",
                                "type": node_type,
                                "text": sentence[:350],
                                "section": section_name,
                                "confidence": 0.8,
                                "evidence": f"pattern:{pattern}",
                                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                            })
                            matched = True
                            break
                    if matched:
                        break
        
        return nodes
    
    def build_semantic_edges(self, nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """构建语义边关系"""
        if not self.semantic_extractor:
            return self._build_traditional_edges(nodes)
        
        print("🔗 构建语义边关系...")
        edges = self.semantic_extractor.build_semantic_edges(nodes)
        
        # 统计边类型
        if edges:
            edge_types = Counter([edge["type"] for edge in edges])
            print(f"📊 语义边类型分布: {dict(edge_types)}")
        
        return edges
    
    def _build_traditional_edges(self, nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """传统边构建方法"""
        edges = []
        node_ids_by_type = defaultdict(list)
        
        for node in nodes:
            node_ids_by_type[node['type']].append(node['id'])
        
        edge_rules = [
            ("Hypothesis", "Experiment", "hypothesis_to_experiment"),
            ("Experiment", "Dataset", "experiment_to_dataset"), 
            ("Dataset", "Analysis", "dataset_to_analysis"),
            ("Analysis", "Conclusion", "analysis_to_conclusion"),
        ]
        
        for src_type, tgt_type, rel_type in edge_rules:
            if src_type in node_ids_by_type and tgt_type in node_ids_by_type:
                count = 0
                for src_id in node_ids_by_type[src_type]:
                    for tgt_id in node_ids_by_type[tgt_type]:
                        edges.append({
                            "start": src_id,
                            "end": tgt_id,
                            "type": rel_type,
                            "confidence": 0.7
                        })
                        count += 1
                print(f"  🔗 {rel_type}: {count} 条边")
        
        return edges
    
    def export_to_csv(self, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]], base_name: str):
        """导出为CSV文件"""
        Path("outputs").mkdir(exist_ok=True)
        
        # 节点CSV
        if nodes:
            nodes_file = f"{base_name}_semantic_nodes.csv"
            with open(nodes_file, 'w', newline='', encoding='utf-8') as f:
                fieldnames = ['id', 'type', 'text', 'section', 'confidence', 'evidence', 'semantic_context', 'timestamp']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for node in nodes:
                    # 处理semantic_context字段
                    row = {field: node.get(field, '') for field in fieldnames}
                    if 'semantic_context' in row and isinstance(row['semantic_context'], dict):
                        row['semantic_context'] = json.dumps(row['semantic_context'])
                    writer.writerow(row)
            print(f"  💾 语义节点保存: {nodes_file}")
        
        # 边CSV  
        if edges:
            edges_file = f"{base_name}_semantic_edges.csv"
            with open(edges_file, 'w', newline='', encoding='utf-8') as f:
                fieldnames = ['start', 'end', 'type', 'confidence', 'semantic_evidence']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for edge in edges:
                    writer.writerow(edge)
            print(f"  💾 语义边保存: {edges_file}")
    
    def create_semantic_visualization(self, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]], output_file: str):
        """创建语义感知的可视化"""
        html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>语义感知的IMRaD知识图谱</title>
    <meta charset="utf-8">
    <style>
        body { 
            font-family: 'Segoe UI', Arial, sans-serif; 
            margin: 20px; 
            background: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 { 
            color: #2c3e50; 
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }
        .stats {
            background: #ecf0f1;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
        }
        .node { 
            margin: 10px 0; 
            padding: 15px; 
            border-radius: 8px; 
            color: white; 
            border-left: 5px solid rgba(0,0,0,0.2);
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        .hypothesis { background: #e67e22; }
        .experiment { background: #3498db; }
        .dataset { background: #1abc9c; }
        .analysis { background: #9b59b6; }
        .conclusion { background: #e74c3c; }
        .semantic-info {
            background: #f8f9fa;
            padding: 8px;
            margin: 5px 0;
            border-radius: 4px;
            font-size: 0.9em;
        }
        .disambiguation {
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 8px;
            margin: 5px 0;
            border-radius: 4px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🧠 语义感知的IMRaD知识图谱</h1>
        
        <div class="stats">
            <strong>语义提取统计:</strong><br>
            节点总数: %NODE_COUNT% | 边关系总数: %EDGE_COUNT%<br>
            语义消歧应用: %DISAMBIGUATION_COUNT% | 处理时间: %TIMESTAMP%
        </div>
        
        <h2>🔗 语义边关系</h2>
        %EDGES%
        
        <h2>📝 语义节点</h2>
        %NODES%
    </div>
</body>
</html>
        """
        
        # 按章节分组节点
        nodes_by_section = defaultdict(list)
        for node in nodes:
            nodes_by_section[node['section']].append(node)
        
        # 生成节点HTML
        nodes_html = ""
        disambiguation_count = 0
        
        for section_name, section_nodes in nodes_by_section.items():
            nodes_html += f'<div class="section" style="background: #2c3e50; color: white; padding: 10px 15px; margin: 20px 0 10px 0; border-radius: 5px; font-weight: bold;">📁 {section_name.upper()} 章节</div>'
            
            for node in section_nodes:
                # 检查是否应用了语义消歧
                semantic_context = node.get('semantic_context', {})
                disambiguation_applied = semantic_context.get('disambiguation_applied', False)
                if disambiguation_applied:
                    disambiguation_count += 1
                
                nodes_html += f"""
                <div class="node {node['type'].lower()}">
                    <div class="node-type" style="font-weight: bold; font-size: 1.1em;">{node['type']}</div>
                    <div class="node-text" style="margin: 8px 0; line-height: 1.4;">{node['text']}</div>
                    <div class="semantic-info">
                        <strong>语义角色:</strong> {semantic_context.get('role', 'N/A')}<br>
                        <strong>关键实体:</strong> {', '.join(semantic_context.get('entities', [])[:5])}<br>
                        <strong>置信度:</strong> {node.get('confidence', 'N/A')}
                    </div>
                    {f'<div class="disambiguation">🔍 已应用语义消歧</div>' if disambiguation_applied else ''}
                    <div class="node-meta" style="font-size: 0.9em; opacity: 0.8;">
                        ID: {node['id']} | 证据: {node.get('evidence', 'N/A')}
                    </div>
                </div>
                """
        
        # 生成边HTML
        edges_html = ""
        for edge in edges:
            semantic_evidence = edge.get('semantic_evidence', 'N/A')
            edges_html += f"""
            <div class="edge" style="margin: 8px 0; padding: 10px; background: #f8f9fa; border-left: 4px solid #34495e; border-radius: 4px;">
                <strong>{edge['start']}</strong> → 
                <strong>{edge['end']}</strong> 
                <small>({edge['type']} | 置信度: {edge.get('confidence', 'N/A')})</small>
                <br><small>语义证据: {semantic_evidence}</small>
            </div>
            """
        
        # 替换模板中的占位符
        html_content = html_content.replace("%NODE_COUNT%", str(len(nodes))) \
                                  .replace("%EDGE_COUNT%", str(len(edges))) \
                                  .replace("%DISAMBIGUATION_COUNT%", str(disambiguation_count)) \
                                  .replace("%TIMESTAMP%", time.strftime("%Y-%m-%d %H:%M:%S")) \
                                  .replace("%NODES%", nodes_html) \
                                  .replace("%EDGES%", edges_html)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"  🌐 语义可视化: {output_file}")

def main(pdf_path: str):
    """运行语义感知的完整pipeline"""
    print(f"🚀 开始语义感知处理: {pdf_path}")
    start_time = time.time()
    
    # 确保输出目录存在
    Path("outputs").mkdir(exist_ok=True)
    
    # 创建处理管道
    pipeline = SemanticIMRaDPipeline()
    
    try:
        # 步骤1: 提取文本
        text = pipeline.extract_text_from_pdf(pdf_path)
        if not text or len(text) < 100:
            print("❌ 文本提取失败或文本过短")
            return
        
        print(f"✅ 成功提取文本 ({len(text)} 字符)")
        
        # 步骤2: 语义节点提取
        print("\n🧠 正在进行语义节点提取...")
        nodes = pipeline.extract_nodes_semantic(text)
        
        if not nodes:
            print("❌ 未提取到任何节点")
            return
        
        print(f"✅ 成功提取 {len(nodes)} 个语义节点")
        
        # 步骤3: 构建语义边
        print("\n🔗 正在构建语义边关系...")
        edges = pipeline.build_semantic_edges(nodes)
        print(f"✅ 成功构建 {len(edges)} 条语义边")
        
        # 步骤4: 保存结果
        print("\n💾 正在保存语义结果...")
        base_name = f"outputs/{Path(pdf_path).stem}_semantic"
        
        pipeline.export_to_csv(nodes, edges, base_name)
        pipeline.create_semantic_visualization(nodes, edges, f"{base_name}_graph.html")
        
        elapsed_time = time.time() - start_time
        print(f"\n🎉 语义处理完成! 用时 {elapsed_time:.2f} 秒")
        print(f"📊 最终结果: {len(nodes)} 个语义节点, {len(edges)} 条语义边")
        print(f"📁 输出文件:")
        print(f"   - {base_name}_semantic_nodes.csv")
        print(f"   - {base_name}_semantic_edges.csv") 
        print(f"   - {base_name}_graph.html")
        
    except Exception as e:
        print(f"❌ 处理过程中出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("❌ 使用方法: python run_semantic_pipeline.py <PDF文件路径>")
        print("💡 示例:")
        print('   python run_semantic_pipeline.py "data/artemisinin_pcos.pdf"')
        sys.exit(1)
    
    pdf_file = sys.argv[1]
    if not os.path.exists(pdf_file):
        print(f"❌ 文件不存在: {pdf_file}")
        sys.exit(1)
    
    main(pdf_file)
