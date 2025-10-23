#!/usr/bin/env python3
"""
Semantic-Aware IMRaD Knowledge Graph Extraction System
Resolves semantic ambiguity of words across different contexts.
"""

import sys
import os
import time
import json
import csv
from pathlib import Path
from typing import List, Dict, Any
from collections import defaultdict, Counter

# Import semantic extractor
try:
    from src.semantic_extractor import SemanticIMRaDExtractor
    SEMANTIC_AVAILABLE = True
except ImportError as e:
    print(f"⚠️   Failed to import semantic extractor: {e}")
    SEMANTIC_AVAILABLE = False

# Import other necessary modules
try:
    import fitz
    import re
    import uuid
    from collections import Counter, defaultdict
except ImportError as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)

class SemanticIMRaDPipeline:
    """Semantic-aware IMRaD processing pipeline"""
    
    def __init__(self):
        self.semantic_extractor = SemanticIMRaDExtractor() if SEMANTIC_AVAILABLE else None
        
        # IMRaD section patterns
        self.section_patterns = {
            "introduction": r"(?:^|\n)(?:\s*\d*\.*\s*Introduction|Background)",
            "methods": r"(?:^|\n)(?:\s*\d*\.*\s*(Materials and Methods|Methods|Experimental Procedures))",
            "results": r"(?:^|\n)(?:\s*\d*\.*\s*Results?)",
            "discussion": r"(?:^|\n)(?:\s*\d*\.*\s*(Discussion|Conclusion|Summary))",
        }
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text from a PDF"""
        print(f"📄 extract text from {os.path.basename(pdf_path)} ...")
        try:
            doc = fitz.open(pdf_path)
            text = ""
            for page_num, page in enumerate(doc):
                page_text = page.get_text("text")
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
            print(f"❌ PDF extraction error: {e}")
            return ""
    
    def segment_imrad(self, text: str) -> Dict[str, str]:
        """Segment text into IMRaD sections"""
        indices = []
        for name, pattern in self.section_patterns.items():
            matches = list(re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE))
            if matches:
                indices.append((matches[0].start(), name))
        if not indices:
            print("⚠️  No standard IMRaD sections detected, using full text")
            return {"full_text": text}

        indices.sort()
        sections = {}
        
        for i, (start, name) in enumerate(indices):
            end = indices[i + 1][0] if i + 1 < len(indices) else len(text)
            section_content = text[start:end].strip()
            
            lines = section_content.split('\n')
            if len(lines) > 1:
                section_content = '\n'.join(lines[1:]).strip()
            
            sections[name] = section_content
        
        return sections
    
    def extract_nodes_semantic(self, text: str) -> List[Dict[str, Any]]:
        """Extract nodes using semantic understandin"""
        if not self.semantic_extractor:
            print("⚠️  Semantic extractor unavailable, using traditional method")
            return self._extract_nodes_traditional(text)
        
        print("🧠 Extracting nodes with semantic understanding...")
        sections = self.segment_imrad(text)
        nodes = self.semantic_extractor.extract_nodes_with_semantics(text, sections)
        
        # Summarize node type
        if nodes:
            node_types = Counter([node["type"] for node in nodes])
            print(f"📊 Semantic node type distribution: {dict(node_types)}")
            
            disambiguation_examples = [n for n in nodes if n.get("semantic_context", {}).get("disambiguation_applied")]
            if disambiguation_examples:
                print(f"🔍 Nodes with semantic disambiguation applied: {len(disambiguation_examples)} ")
                for example in disambiguation_examples[:3]: 
                    print(f"   - {example['type']}: {example['text'][:60]}...")
        
        return nodes
    
    def _extract_nodes_traditional(self, text: str) -> List[Dict[str, Any]]:
        """Fallback method using regex-based extraction"""
        print("📝 Using traditional regex-based method...")
        
        # Cue patterns
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
        """Build semantic relationships (edges)"""
        if not self.semantic_extractor:
            return self._build_traditional_edges(nodes)
        
        print("🔗 Build semantic relationships (edges)...")
        edges = self.semantic_extractor.build_semantic_edges(nodes)
        
        if edges:
            edge_types = Counter([edge["type"] for edge in edges])
            print(f"📊 Semantic edge type distribution: {dict(edge_types)}")
        
        return edges
    
    def _build_traditional_edges(self, nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Traditional rule-based edge construction"""
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
                print(f"  🔗 {rel_type}: {count} ")
        
        return edges
    
    def export_to_csv(self, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]], base_name: str):
        """Export nodes and edges as CSV"""
        Path("outputs").mkdir(exist_ok=True)
        
        # node CSV
        if nodes:
            nodes_file = f"{base_name}_semantic_nodes.csv"
            with open(nodes_file, 'w', newline='', encoding='utf-8') as f:
                fieldnames = ['id', 'type', 'text', 'section', 'confidence', 'evidence', 'semantic_context', 'timestamp']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for node in nodes:
                    row = {field: node.get(field, '') for field in fieldnames}
                    if 'semantic_context' in row and isinstance(row['semantic_context'], dict):
                        row['semantic_context'] = json.dumps(row['semantic_context'])
                    writer.writerow(row)
            print(f"  💾 Saved semantic nodes: {nodes_file}")
        
        # edge CSV  
        if edges:
            edges_file = f"{base_name}_semantic_edges.csv"
            with open(edges_file, 'w', newline='', encoding='utf-8') as f:
                fieldnames = ['start', 'end', 'type', 'confidence', 'semantic_evidence']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for edge in edges:
                    writer.writerow(edge)
            print(f"  💾 Saved semantic edges: {edges_file}")
    
    def create_semantic_visualization(self, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]], output_file: str):
        """Create semantic-aware visualization (HTML)"""
        html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>Semantic-Aware IMRaD Knowledge Graph</title>
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
        <h1>🧠 Semantic-Aware IMRaD Knowledge Graph</h1>
        
        <div class="stats">
            <strong>Semantic Extraction Stats:</strong><br>
            Total Nodes: %NODE_COUNT% | Total Edges: %EDGE_COUNT%<br>
            Disambiguations Applied: %DISAMBIGUATION_COUNT% | Processed at: %TIMESTAMP%
        </div>
        
        <h2>🔗 Semantic Relationships</h2>
        %EDGES%
        
        <h2>📝 Semantic Nodes</h2>
        %NODES%
    </div>
</body>
</html>
        """
        
        # Generate HTML content
        nodes_by_section = defaultdict(list)
        for node in nodes:
            nodes_by_section[node['section']].append(node)
        
        nodes_html = ""
        disambiguation_count = 0
        
        for section_name, section_nodes in nodes_by_section.items():
            nodes_html += f'<div class="section" style="background: #2c3e50; color: white; padding: 10px 15px; margin: 20px 0 10px 0; border-radius: 5px; font-weight: bold;">📁 {section_name.upper()} Section</div>'
            
            for node in section_nodes:
                semantic_context = node.get('semantic_context', {})
                disambiguation_applied = semantic_context.get('disambiguation_applied', False)
                if disambiguation_applied:
                    disambiguation_count += 1
                
                nodes_html += f"""
                <div class="node {node['type'].lower()}">
                    <div class="node-type" style="font-weight: bold; font-size: 1.1em;">{node['type']}</div>
                    <div class="node-text" style="margin: 8px 0; line-height: 1.4;">{node['text']}</div>
                    <div class="semantic-info">
                        <strong>Semantic Role:</strong> {semantic_context.get('role', 'N/A')}<br>
                        <strong>Key Entities:</strong> {', '.join(semantic_context.get('entities', [])[:5])}<br>
                        <strong>Confidence:</strong> {node.get('confidence', 'N/A')}
                    </div>
                    </div>
                    {f'<div class="disambiguation">🔍 Semantic disambiguation applied</div>' if disambiguation_applied else ''}
                    <div class="node-meta" style="font-size: 0.9em; opacity: 0.8;">
                        ID: {node['id']} | Evidence: {node.get('evidence', 'N/A')}
                    </div>
                </div>
                """
        
        edges_html = ""
        for edge in edges:
            semantic_evidence = edge.get('semantic_evidence', 'N/A')
            edges_html += f"""
            <div class="edge" style="margin: 8px 0; padding: 10px; background: #f8f9fa; border-left: 4px solid #34495e; border-radius: 4px;">
                <strong>{edge['start']}</strong> → 
                <strong>{edge['end']}</strong> 
                <small>({edge['type']} | Confidence: {edge.get('confidence', 'N/A')})</small>
                <br><small>Semantic Evidence: {semantic_evidence}</small>
            </div>
            """
        
        html_content = html_content.replace("%NODE_COUNT%", str(len(nodes))) \
                                  .replace("%EDGE_COUNT%", str(len(edges))) \
                                  .replace("%DISAMBIGUATION_COUNT%", str(disambiguation_count)) \
                                  .replace("%TIMESTAMP%", time.strftime("%Y-%m-%d %H:%M:%S")) \
                                  .replace("%NODES%", nodes_html) \
                                  .replace("%EDGES%", edges_html)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"  🌐 Semantic visualization saved: {output_file}")

def main(pdf_path: str):
    """Run the full semantic-aware pipeline"""
    print(f"🚀 Starting semantic-aware processing: {pdf_path}")
    start_time = time.time()
    
    Path("outputs").mkdir(exist_ok=True)
    
    pipeline = SemanticIMRaDPipeline()
    
    try:
        text = pipeline.extract_text_from_pdf(pdf_path)
        if not text or len(text) < 100:
            print("❌ Text extraction failed or too short")
            return
        
        print(f"✅ Successfully extracted text ({len(text)} characters)")
        
        print("\n🧠 Extracting semantic nodes...")
        nodes = pipeline.extract_nodes_semantic(text)
        
        if not nodes:
            print("❌ No nodes extracted")
            return
        
        print(f"✅ Extracted {len(nodes)} semantic nodes")
        

        print("\n🔗 Building semantic relationships...")
        edges = pipeline.build_semantic_edges(nodes)
        print(f"✅ Built {len(edges)} semantic edges")
        

        print("\n💾 Saving semantic results...")
        base_name = f"outputs/{Path(pdf_path).stem}_semantic"
        
        pipeline.export_to_csv(nodes, edges, base_name)
        pipeline.create_semantic_visualization(nodes, edges, f"{base_name}_graph.html")
        
        elapsed_time = time.time() - start_time
        print(f"\n🎉 Semantic processing completed in {elapsed_time:.2f} seconds")
        print(f"📊 Final results: {len(nodes)} nodes, {len(edges)} edges")
        print(f"📁 Output files:")
        print(f"   - {base_name}_semantic_nodes.csv")
        print(f"   - {base_name}_semantic_edges.csv") 
        print(f"   - {base_name}_graph.html")
        
    except Exception as e:
        print(f"❌ Error during processing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("❌ Usage: python run_semantic_pipeline.py <PDF file path>")
        print("💡 Example:")
        print('   python run_semantic_pipeline.py "data/artemisinin_pcos.pdf"')
        sys.exit(1)
    
    pdf_file = sys.argv[1]
    if not os.path.exists(pdf_file):
        print(f"❌ No such file: {pdf_file}")
        sys.exit(1)
    
    main(pdf_file)
