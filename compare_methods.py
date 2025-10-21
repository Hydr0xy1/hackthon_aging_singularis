#!/usr/bin/env python3
"""
对比传统正则表达式方法与语义感知方法的效果
"""

import sys
import os
import json
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any
from collections import Counter, defaultdict

def load_nodes_from_csv(csv_file: str) -> List[Dict[str, Any]]:
    """从CSV文件加载节点"""
    if not os.path.exists(csv_file):
        return []
    
    df = pd.read_csv(csv_file)
    nodes = df.to_dict('records')
    return nodes

def analyze_semantic_improvements(traditional_nodes: List[Dict[str, Any]], 
                                semantic_nodes: List[Dict[str, Any]]) -> Dict[str, Any]:
    """分析语义改进效果"""
    
    analysis = {
        "basic_stats": {},
        "semantic_features": {},
        "disambiguation_analysis": {},
        "quality_improvements": {}
    }
    
    # 基本统计对比
    analysis["basic_stats"] = {
        "traditional_nodes": len(traditional_nodes),
        "semantic_nodes": len(semantic_nodes),
        "node_increase": len(semantic_nodes) - len(traditional_nodes),
        "improvement_rate": (len(semantic_nodes) - len(traditional_nodes)) / len(traditional_nodes) * 100 if traditional_nodes else 0
    }
    
    # 节点类型分布对比
    traditional_types = Counter([node.get("type", "Unknown") for node in traditional_nodes])
    semantic_types = Counter([node.get("type", "Unknown") for node in semantic_nodes])
    
    analysis["basic_stats"]["traditional_type_distribution"] = dict(traditional_types)
    analysis["basic_stats"]["semantic_type_distribution"] = dict(semantic_types)
    
    # 语义特征分析
    semantic_features = {
        "nodes_with_semantic_context": 0,
        "disambiguation_applied": 0,
        "semantic_roles_identified": set(),
        "entities_extracted": 0
    }
    
    for node in semantic_nodes:
        semantic_context = node.get("semantic_context", {})
        # 处理semantic_context可能是字符串的情况
        if isinstance(semantic_context, str):
            try:
                import json
                semantic_context = json.loads(semantic_context)
            except:
                semantic_context = {}
        
        if semantic_context:
            semantic_features["nodes_with_semantic_context"] += 1
            
            if semantic_context.get("disambiguation_applied", False):
                semantic_features["disambiguation_applied"] += 1
            
            role = semantic_context.get("role", "")
            if role:
                semantic_features["semantic_roles_identified"].add(role)
            
            entities = semantic_context.get("entities", [])
            semantic_features["entities_extracted"] += len(entities)
    
    analysis["semantic_features"] = {
        "nodes_with_semantic_context": semantic_features["nodes_with_semantic_context"],
        "disambiguation_applied": semantic_features["disambiguation_applied"],
        "unique_semantic_roles": len(semantic_features["semantic_roles_identified"]),
        "total_entities_extracted": semantic_features["entities_extracted"],
        "semantic_roles": list(semantic_features["semantic_roles_identified"])
    }
    
    # 语义消歧分析
    disambiguation_examples = []
    for node in semantic_nodes:
        semantic_context = node.get("semantic_context", {})
        # 处理semantic_context可能是字符串的情况
        if isinstance(semantic_context, str):
            try:
                import json
                semantic_context = json.loads(semantic_context)
            except:
                semantic_context = {}
        
        if semantic_context.get("disambiguation_applied", False):
            disambiguation_examples.append({
                "type": node.get("type"),
                "text": node.get("text", "")[:100],
                "role": semantic_context.get("role"),
                "entities": semantic_context.get("entities", [])[:3]
            })
    
    analysis["disambiguation_analysis"] = {
        "total_disambiguated": len(disambiguation_examples),
        "examples": disambiguation_examples[:5]  # 显示前5个示例
    }
    
    # 质量改进分析
    quality_metrics = {
        "average_confidence_traditional": 0,
        "average_confidence_semantic": 0,
        "evidence_diversity_traditional": 0,
        "evidence_diversity_semantic": 0
    }
    
    # 计算平均置信度
    if traditional_nodes:
        confidences = [node.get("confidence", 0) for node in traditional_nodes if isinstance(node.get("confidence"), (int, float))]
        quality_metrics["average_confidence_traditional"] = sum(confidences) / len(confidences) if confidences else 0
    
    if semantic_nodes:
        confidences = [node.get("confidence", 0) for node in semantic_nodes if isinstance(node.get("confidence"), (int, float))]
        quality_metrics["average_confidence_semantic"] = sum(confidences) / len(confidences) if confidences else 0
    
    # 证据多样性
    traditional_evidence = set([node.get("evidence", "") for node in traditional_nodes])
    semantic_evidence = set([node.get("evidence", "") for node in semantic_nodes])
    
    quality_metrics["evidence_diversity_traditional"] = len(traditional_evidence)
    quality_metrics["evidence_diversity_semantic"] = len(semantic_evidence)
    
    analysis["quality_improvements"] = quality_metrics
    
    return analysis

def generate_comparison_report(analysis: Dict[str, Any], output_file: str):
    """生成对比报告"""
    
    html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>语义方法 vs 传统方法对比报告</title>
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
        .comparison-table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }
        .comparison-table th, .comparison-table td {
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
        }
        .comparison-table th {
            background-color: #f2f2f2;
            font-weight: bold;
        }
        .improvement {
            background-color: #d4edda;
            color: #155724;
        }
        .degradation {
            background-color: #f8d7da;
            color: #721c24;
        }
        .metric-card {
            background: #f8f9fa;
            padding: 15px;
            margin: 10px 0;
            border-radius: 5px;
            border-left: 4px solid #007bff;
        }
        .semantic-feature {
            background: #e7f3ff;
            padding: 10px;
            margin: 5px 0;
            border-radius: 4px;
            border-left: 3px solid #007bff;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 语义方法 vs 传统方法对比报告</h1>
        
        <div class="metric-card">
            <h3>📈 基本统计对比</h3>
            <table class="comparison-table">
                <tr>
                    <th>指标</th>
                    <th>传统方法</th>
                    <th>语义方法</th>
                    <th>改进</th>
                </tr>
                <tr>
                    <td>节点总数</td>
                    <td>%TRADITIONAL_NODES%</td>
                    <td>%SEMANTIC_NODES%</td>
                    <td class="%NODE_IMPROVEMENT_CLASS%">%NODE_IMPROVEMENT%</td>
                </tr>
                <tr>
                    <td>平均置信度</td>
                    <td>%TRADITIONAL_CONFIDENCE%</td>
                    <td>%SEMANTIC_CONFIDENCE%</td>
                    <td class="%CONFIDENCE_IMPROVEMENT_CLASS%">%CONFIDENCE_IMPROVEMENT%</td>
                </tr>
                <tr>
                    <td>证据多样性</td>
                    <td>%TRADITIONAL_EVIDENCE%</td>
                    <td>%SEMANTIC_EVIDENCE%</td>
                    <td class="%EVIDENCE_IMPROVEMENT_CLASS%">%EVIDENCE_IMPROVEMENT%</td>
                </tr>
            </table>
        </div>
        
        <div class="metric-card">
            <h3>🧠 语义特征分析</h3>
            <div class="semantic-feature">
                <strong>语义上下文节点:</strong> %SEMANTIC_CONTEXT_NODES% 个
            </div>
            <div class="semantic-feature">
                <strong>语义消歧应用:</strong> %DISAMBIGUATION_COUNT% 个节点
            </div>
            <div class="semantic-feature">
                <strong>识别的语义角色:</strong> %UNIQUE_ROLES% 种
            </div>
            <div class="semantic-feature">
                <strong>提取的实体总数:</strong> %TOTAL_ENTITIES% 个
            </div>
        </div>
        
        <div class="metric-card">
            <h3>🔍 语义消歧示例</h3>
            %DISAMBIGUATION_EXAMPLES%
        </div>
        
        <div class="metric-card">
            <h3>📊 节点类型分布对比</h3>
            %TYPE_DISTRIBUTION%
        </div>
    </div>
</body>
</html>
    """
    
    # 计算改进指标
    basic_stats = analysis["basic_stats"]
    quality_improvements = analysis["quality_improvements"]
    semantic_features = analysis["semantic_features"]
    disambiguation_analysis = analysis["disambiguation_analysis"]
    
    # 节点数量改进
    node_improvement = basic_stats["node_increase"]
    node_improvement_class = "improvement" if node_improvement > 0 else "degradation"
    
    # 置信度改进
    conf_improvement = quality_improvements["average_confidence_semantic"] - quality_improvements["average_confidence_traditional"]
    conf_improvement_class = "improvement" if conf_improvement > 0 else "degradation"
    
    # 证据多样性改进
    evidence_improvement = quality_improvements["evidence_diversity_semantic"] - quality_improvements["evidence_diversity_traditional"]
    evidence_improvement_class = "improvement" if evidence_improvement > 0 else "degradation"
    
    # 生成消歧示例HTML
    disambiguation_html = ""
    for example in disambiguation_analysis["examples"]:
        disambiguation_html += f"""
        <div style="background: #fff3cd; padding: 10px; margin: 5px 0; border-radius: 4px; border-left: 3px solid #ffc107;">
            <strong>{example['type']}:</strong> {example['text']}...<br>
            <small>语义角色: {example['role']} | 实体: {', '.join(example['entities'])}</small>
        </div>
        """
    
    # 生成类型分布HTML
    type_distribution_html = ""
    traditional_dist = basic_stats["traditional_type_distribution"]
    semantic_dist = basic_stats["semantic_type_distribution"]
    
    all_types = set(traditional_dist.keys()) | set(semantic_dist.keys())
    for node_type in all_types:
        traditional_count = traditional_dist.get(node_type, 0)
        semantic_count = semantic_dist.get(node_type, 0)
        change = semantic_count - traditional_count
        change_class = "improvement" if change > 0 else "degradation" if change < 0 else ""
        
        type_distribution_html += f"""
        <tr>
            <td>{node_type}</td>
            <td>{traditional_count}</td>
            <td>{semantic_count}</td>
            <td class="{change_class}">{change:+d}</td>
        </tr>
        """
    
    # 替换占位符
    html_content = html_content.replace("%TRADITIONAL_NODES%", str(basic_stats["traditional_nodes"])) \
                              .replace("%SEMANTIC_NODES%", str(basic_stats["semantic_nodes"])) \
                              .replace("%NODE_IMPROVEMENT%", f"{node_improvement:+d}") \
                              .replace("%NODE_IMPROVEMENT_CLASS%", node_improvement_class) \
                              .replace("%TRADITIONAL_CONFIDENCE%", f"{quality_improvements['average_confidence_traditional']:.2f}") \
                              .replace("%SEMANTIC_CONFIDENCE%", f"{quality_improvements['average_confidence_semantic']:.2f}") \
                              .replace("%CONFIDENCE_IMPROVEMENT%", f"{conf_improvement:+.2f}") \
                              .replace("%CONFIDENCE_IMPROVEMENT_CLASS%", conf_improvement_class) \
                              .replace("%TRADITIONAL_EVIDENCE%", str(quality_improvements["evidence_diversity_traditional"])) \
                              .replace("%SEMANTIC_EVIDENCE%", str(quality_improvements["evidence_diversity_semantic"])) \
                              .replace("%EVIDENCE_IMPROVEMENT%", f"{evidence_improvement:+d}") \
                              .replace("%EVIDENCE_IMPROVEMENT_CLASS%", evidence_improvement_class) \
                              .replace("%SEMANTIC_CONTEXT_NODES%", str(semantic_features["nodes_with_semantic_context"])) \
                              .replace("%DISAMBIGUATION_COUNT%", str(semantic_features["disambiguation_applied"])) \
                              .replace("%UNIQUE_ROLES%", str(semantic_features["unique_semantic_roles"])) \
                              .replace("%TOTAL_ENTITIES%", str(semantic_features["total_entities_extracted"])) \
                              .replace("%DISAMBIGUATION_EXAMPLES%", disambiguation_html) \
                              .replace("%TYPE_DISTRIBUTION%", type_distribution_html)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"📊 对比报告已生成: {output_file}")

def main():
    """主函数"""
    if len(sys.argv) != 3:
        print("❌ 使用方法: python compare_methods.py <传统方法节点CSV> <语义方法节点CSV>")
        print("💡 示例:")
        print("   python compare_methods.py outputs/artemisinin_pcos_nodes.csv outputs/artemisinin_pcos_semantic_nodes.csv")
        sys.exit(1)
    
    traditional_csv = sys.argv[1]
    semantic_csv = sys.argv[2]
    
    if not os.path.exists(traditional_csv):
        print(f"❌ 传统方法文件不存在: {traditional_csv}")
        sys.exit(1)
    
    if not os.path.exists(semantic_csv):
        print(f"❌ 语义方法文件不存在: {semantic_csv}")
        sys.exit(1)
    
    print("📊 开始对比分析...")
    
    # 加载节点数据
    traditional_nodes = load_nodes_from_csv(traditional_csv)
    semantic_nodes = load_nodes_from_csv(semantic_csv)
    
    print(f"📁 传统方法节点: {len(traditional_nodes)} 个")
    print(f"📁 语义方法节点: {len(semantic_nodes)} 个")
    
    # 进行分析
    analysis = analyze_semantic_improvements(traditional_nodes, semantic_nodes)
    
    # 生成报告
    output_file = "outputs/semantic_vs_traditional_comparison.html"
    generate_comparison_report(analysis, output_file)
    
    # 打印关键指标
    print("\n🎯 关键改进指标:")
    print(f"   节点数量改进: {analysis['basic_stats']['node_increase']:+d}")
    print(f"   语义消歧应用: {analysis['semantic_features']['disambiguation_applied']} 个节点")
    print(f"   语义角色识别: {analysis['semantic_features']['unique_semantic_roles']} 种")
    print(f"   实体提取总数: {analysis['semantic_features']['total_entities_extracted']} 个")
    
    print(f"\n📊 详细对比报告: {output_file}")

if __name__ == "__main__":
    main()
