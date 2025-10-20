#!/usr/bin/env python3
"""
修复参数处理的终极版本
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
    
    # 简化文件名（避免长路径问题）
    original_path = pdf_path
    if len(pdf_path) > 50:
        short_name = "data/artemisinin_pcos.pdf"
        if not os.path.exists(short_name) and os.path.exists(pdf_path):
            print(f"📝 将文件重命名为短名称: {short_name}")
            os.rename(pdf_path, short_name)
            pdf_path = short_name
    
    # 现在导入其他模块（避免在参数检查前导入可能失败的模块）
    try:
        import fitz
        import re
        import csv
        import json
        import uuid
        from collections import Counter, defaultdict
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        return
    
    class UltimateIMRaDExtractor:
        # 这里插入之前完整的 UltimateIMRaDExtractor 类代码
        # 为了简洁，我在这里省略了类的完整代码，但您需要将之前的内容复制到这里
        
        def __init__(self):
            self.section_patterns = {
                "introduction": r"(?:^|\n)(?:\s*\d*\.*\s*Introduction|Background)",
                "methods": r"(?:^|\n)(?:\s*\d*\.*\s*(Materials and Methods|Methods|Experimental Procedures))",
                "results": r"(?:^|\n)(?:\s*\d*\.*\s*Results?)",
                "discussion": r"(?:^|\n)(?:\s*\d*\.*\s*(Discussion|Conclusion|Summary))",
            }
            
            self.cue_patterns = {
                "Hypothesis": [
                    r"\bwe hypothesi[sz]e\b", r"\bwe propose\b", r"\bthis study aims to\b",
                    r"\bwe expect\b", r"\bwe predict\b", r"\bit is hypothesized\b"
                ],
                "Experiment": [
                    r"\bwe conducted\b", r"\bwe performed\b", r"\bexperiments\b",
                    r"\bwe treated\b", r"\bmethods\b", r"\bexperimental\b",
                    r"\bwe used\b", r"\bwe measured\b"
                ],
                "Dataset": [
                    r"\bcohort\b", r"\bn\s*=\s*\d+", r"\bdata from\b",
                    r"\bpatients\b", r"\bsamples\b", r"\bdataset\b",
                    r"\bclinical data\b", r"\bobtained from\b"
                ],
                "Analysis": [
                    r"\bwe analyzed\b", r"\bstatistical analysis\b", r"\bp\s*[<≤]\s*0\.\d+",
                    r"\bsignificant\b", r"\bdata demonstrate\b", r"\bwe calculated\b",
                    r"\bcorrelation\b", r"\bregression\b"
                ],
                "Conclusion": [
                    r"\bin conclusion\b", r"\bwe conclude\b", r"\bthese results suggest\b",
                    r"\bthis study shows\b", r"\bour findings\b", r"\bthese data indicate\b",
                    r"\boverall\b.*\bsuggest\b"
                ]
            }
            
            self.edge_rules = [
                ("Hypothesis", "Experiment", "hypothesis_to_experiment"),
                ("Experiment", "Dataset", "experiment_to_dataset"), 
                ("Dataset", "Analysis", "dataset_to_analysis"),
                ("Analysis", "Conclusion", "analysis_to_conclusion"),
            ]
        
        def extract_text_from_pdf(self, pdf_path):
            """从PDF提取文本"""
            print(f"📄 从 {os.path.basename(pdf_path)} 提取文本...")
            try:
                doc = fitz.open(pdf_path)
                text = ""
                for page_num, page in enumerate(doc):
                    page_text = page.get_text("text")
                    # 清理文本：移除页码和短行
                    lines = []
                    for line in page_text.split("\n"):
                        line = line.strip()
                        # 过滤掉页码和太短的行
                        if (not re.match(r"^\s*\d+\s*$", line) and 
                            len(line) > 15 and  # 增加最小长度
                            not line.isupper() and  # 过滤全大写的行
                            not re.match(r'^\s*[A-Z\s]+\s*$', line)):  # 过滤只有大写字母的行
                            lines.append(line)
                    text += " ".join(lines) + "\n\n"
                doc.close()
                return text
            except Exception as e:
                print(f"❌ PDF提取错误: {e}")
                return ""
        
        def sentence_segmentation(self, text):
            """句子分割 - 使用简单但有效的方法"""
            # 先按段落分割
            paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
            
            sentences = []
            for paragraph in paragraphs:
                # 在段落内按句子结束符分割
                paragraph_sentences = re.split(r'(?<=[.!?])\s+', paragraph)
                for sent in paragraph_sentences:
                    sent = sent.strip()
                    if len(sent) > 20:  # 只保留足够长的句子
                        sentences.append(sent)
            
            return sentences
        
        def gen_id(self, prefix):
            """生成唯一ID"""
            return f"{prefix}_{uuid.uuid4().hex[:6]}"
        
        def create_node(self, node_type, text, section, confidence=0.8, evidence=""):
            """创建节点"""
            return {
                "id": self.gen_id(node_type[:3].upper()),
                "type": node_type,
                "text": text[:350],  # 截断长文本但保留更多内容
                "section": section,
                "confidence": confidence,
                "evidence": evidence,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
        
        def segment_imrad(self, text):
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
                # 结束位置是下一个section的开始，或者是文本结尾
                end = indices[i + 1][0] if i + 1 < len(indices) else len(text)
                section_content = text[start:end].strip()
                
                # 移除章节标题行
                lines = section_content.split('\n')
                if len(lines) > 1:
                    # 跳过第一行（标题）
                    section_content = '\n'.join(lines[1:]).strip()
                
                sections[name] = section_content
            
            return sections
        
        def extract_nodes_from_section(self, section_name, text):
            """从章节文本提取节点"""
            sentences = self.sentence_segmentation(text)
            nodes = []
            
            for sentence in sentences:
                matched = False
                for node_type, patterns in self.cue_patterns.items():
                    for pattern in patterns:
                        if re.search(pattern, sentence, re.IGNORECASE):
                            nodes.append(self.create_node(
                                node_type, sentence, section_name,
                                evidence=f"pattern:{pattern}"
                            ))
                            matched = True
                            break
                    if matched:
                        break
            
            return nodes
        
        def extract_imrad_from_text(self, text):
            """从完整文本提取IMRaD节点"""
            sections = self.segment_imrad(text)
            all_nodes = []
            
            print(f"📑 检测到 {len(sections)} 个章节: {list(sections.keys())}")
            
            for section_name, section_text in sections.items():
                if len(section_text.strip()) < 100:  # 跳过太短的章节
                    continue
                    
                nodes = self.extract_nodes_from_section(section_name, section_text)
                print(f"   📍 {section_name}: 提取了 {len(nodes)} 个节点")
                all_nodes.extend(nodes)
            
            # 统计节点类型
            if all_nodes:
                node_types = Counter([node["type"] for node in all_nodes])
                print(f"📊 节点类型分布: {dict(node_types)}")
            else:
                print("⚠️  未提取到任何节点，将显示一些示例句子")
                # 显示一些句子用于调试
                sentences = self.sentence_segmentation(text)
                for i, sent in enumerate(sentences[:5]):
                    print(f"   示例 {i+1}: {sent[:80]}...")
            
            return all_nodes
        
        def build_edges(self, nodes):
            """构建边关系"""
            edges = []
            node_ids_by_type = defaultdict(list)
            
            for node in nodes:
                node_ids_by_type[node['type']].append(node['id'])
            
            edge_counts = {}
            for src_type, tgt_type, rel_type in self.edge_rules:
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
                    edge_counts[rel_type] = count
                    print(f"  🔗 {rel_type}: {count} 条边")
                else:
                    print(f"  ⚠️  跳过 {rel_type}: 缺少 {src_type} 或 {tgt_type}")
            
            return edges
        
        def export_to_csv(self, nodes, edges, base_name):
            """导出为CSV文件"""
            # 确保输出目录存在
            Path("outputs").mkdir(exist_ok=True)
            
            # 节点CSV
            if nodes:
                nodes_file = f"{base_name}_nodes.csv"
                with open(nodes_file, 'w', newline='', encoding='utf-8') as f:
                    fieldnames = ['id', 'type', 'text', 'section', 'confidence', 'evidence', 'timestamp']
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    for node in nodes:
                        # 确保所有字段都存在
                        row = {field: node.get(field, '') for field in fieldnames}
                        writer.writerow(row)
                print(f"  💾 节点保存: {nodes_file}")
            
            # 边CSV  
            if edges:
                edges_file = f"{base_name}_edges.csv"
                with open(edges_file, 'w', newline='', encoding='utf-8') as f:
                    fieldnames = ['start', 'end', 'type', 'confidence']
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    for edge in edges:
                        writer.writerow(edge)
                print(f"  💾 边保存: {edges_file}")
        
        def create_simple_visualization(self, nodes, edges, output_file):
            """创建简单的HTML可视化"""
            html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>IMRaD Knowledge Graph</title>
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
            .edge { 
                margin: 8px 0; 
                padding: 10px; 
                background: #f8f9fa;
                border-left: 4px solid #34495e;
                border-radius: 4px;
            }
            .section {
                background: #2c3e50;
                color: white;
                padding: 10px 15px;
                margin: 20px 0 10px 0;
                border-radius: 5px;
                font-weight: bold;
            }
            .node-type {
                font-weight: bold;
                font-size: 1.1em;
            }
            .node-text {
                margin: 8px 0;
                line-height: 1.4;
            }
            .node-meta {
                font-size: 0.9em;
                opacity: 0.8;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📊 IMRaD Knowledge Graph</h1>
            
            <div class="stats">
                <strong>提取统计:</strong><br>
                节点总数: %NODE_COUNT% | 边关系总数: %EDGE_COUNT%<br>
                处理时间: %TIMESTAMP%
            </div>
            
            <h2>🔗 边关系</h2>
            %EDGES%
            
            <h2>📝 提取的节点</h2>
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
            for section_name, section_nodes in nodes_by_section.items():
                nodes_html += f'<div class="section">📁 {section_name.upper()} 章节</div>'
                for node in section_nodes:
                    nodes_html += f"""
                    <div class="node {node['type'].lower()}">
                        <div class="node-type">{node['type']}</div>
                        <div class="node-text">{node['text']}</div>
                        <div class="node-meta">
                            ID: {node['id']} | 置信度: {node.get('confidence', 'N/A')} | 
                            证据: {node.get('evidence', 'N/A')}
                        </div>
                    </div>
                    """
            
            # 生成边HTML
            edges_html = ""
            for edge in edges:
                edges_html += f"""
                <div class="edge">
                    <strong>{edge['start']}</strong> → 
                    <strong>{edge['end']}</strong> 
                    <small>({edge['type']} | 置信度: {edge.get('confidence', 'N/A')})</small>
                </div>
                """
            
            # 替换模板中的占位符
            html_content = html_content.replace("%NODE_COUNT%", str(len(nodes))) \
                                      .replace("%EDGE_COUNT%", str(len(edges))) \
                                      .replace("%TIMESTAMP%", time.strftime("%Y-%m-%d %H:%M:%S")) \
                                      .replace("%NODES%", nodes_html) \
                                      .replace("%EDGES%", edges_html)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            print(f"  🌐 HTML可视化: {output_file}")

    extractor = UltimateIMRaDExtractor()
    
    try:
        # 步骤1: 提取文本
        text = extractor.extract_text_from_pdf(pdf_path)
        if not text or len(text) < 100:
            print("❌ 文本提取失败或文本过短")
            return
        
        print(f"✅ 成功提取文本 ({len(text)} 字符)")
        
        # 步骤2: 提取节点
        print("\n🔍 正在提取IMRaD节点...")
        nodes = extractor.extract_imrad_from_text(text)
        
        if not nodes:
            print("❌ 未提取到任何节点")
            print("💡 可能的原因:")
            print("   - PDF内容与IMRaD结构不匹配")
            print("   - 正则模式需要调整")
            print("   - PDF是扫描件或格式特殊")
            return
        
        print(f"✅ 成功提取 {len(nodes)} 个节点")
        
        # 步骤3: 构建边
        print("\n🔗 正在构建边关系...")
        edges = extractor.build_edges(nodes)
        print(f"✅ 成功构建 {len(edges)} 条边")
        
        # 步骤4: 保存结果
        print("\n💾 正在保存结果...")
        base_name = f"outputs/{Path(pdf_path).stem}"
        
        extractor.export_to_csv(nodes, edges, base_name)
        extractor.create_simple_visualization(nodes, edges, f"{base_name}_graph.html")
        
        elapsed_time = time.time() - start_time
        print(f"\n🎉 处理完成! 用时 {elapsed_time:.2f} 秒")
        print(f"📊 最终结果: {len(nodes)} 个节点, {len(edges)} 条边")
        print(f"📁 输出文件:")
        print(f"   - {base_name}_nodes.csv")
        print(f"   - {base_name}_edges.csv") 
        print(f"   - {base_name}_graph.html")
        
    except Exception as e:
        print(f"❌ 处理过程中出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("❌ 使用方法: python run_ultimate_fixed.py <PDF文件路径>")
        print("💡 示例:")
        print('   python run_ultimate_fixed.py "data/Artemisinins ameliorate polycystic ovarian syndrome by mediating LONP1-CYP11A1 interaction.pdf"')
        print("   或者: python run_ultimate_fixed.py data/artemisinin_pcos.pdf")
        sys.exit(1)
    
    pdf_file = sys.argv[1]
    if not os.path.exists(pdf_file):
        print(f"❌ 文件不存在: {pdf_file}")
        print("💡 请检查文件路径是否正确")
        sys.exit(1)
    
    main(pdf_file)