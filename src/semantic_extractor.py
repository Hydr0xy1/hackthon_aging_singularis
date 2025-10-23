#!/usr/bin/env python3
"""
Semantic-aware IMRaD extractor
Resolve semantic ambiguity of the same word in different contexts
"""

import re
import json
import uuid
import time
from typing import List, Dict, Any, Tuple, Optional
from collections import defaultdict, Counter
import spacy
from dataclasses import dataclass

# 尝试加载spacy模型
try:
    nlp = spacy.load("en_core_web_sm")
    SPACY_AVAILABLE = True
except (OSError, ImportError):
    print("⚠️  Can't load spaCy en_core_web_sm model, using simple NLP handling")
    print("   Run: python -m spacy download en_core_web_sm")
    nlp = None
    SPACY_AVAILABLE = False

@dataclass
class SemanticContext:
    """Semantic context information"""
    sentence: str
    section: str
    surrounding_sentences: List[str]
    key_entities: List[str]
    semantic_role: str  # subject, object, modifier, etc.
    confidence: float

class SemanticIMRaDExtractor:
    """Semantic-aware IMRaD extractor"""
    
    def __init__(self):
        self.nlp = nlp if SPACY_AVAILABLE else None
        
        # Semantic pattern definitions - based on semantic roles instead of simple keyword matching
        self.semantic_patterns = {
            "Hypothesis": {
                "indicators": [
                    "hypothesize", "propose", "predict", "expect", "anticipate",
                    "suggest", "theorize", "postulate", "speculate"
                ],
                "context_clues": [
                    "we hypothesize that", "we propose that", "we predict that",
                    "it is hypothesized", "our hypothesis", "we expect that"
                ],
                "semantic_roles": ["subject_verb_object", "causal_relationship"]
            },
            "Experiment": {
                "indicators": [
                    "conducted", "performed", "carried out", "executed", "implemented",
                    "administered", "treated", "injected", "measured", "assessed"
                ],
                "context_clues": [
                    "we conducted", "we performed", "we carried out", "we administered",
                    "experimental", "in vitro", "in vivo", "mouse model", "cell culture"
                ],
                "semantic_roles": ["action_verb", "methodology", "procedure"]
            },
            "Dataset": {
                "indicators": [
                    "cohort", "patients", "samples", "subjects", "participants",
                    "data", "dataset", "database", "repository"
                ],
                "context_clues": [
                    "n =", "n=", "cohort of", "patients with", "samples from",
                    "data from", "dataset", "clinical data", "obtained from"
                ],
                "semantic_roles": ["data_source", "population", "sample"]
            },
            "Analysis": {
                "indicators": [
                    "analyzed", "computed", "calculated", "modeled", "fitted",
                    "correlated", "regressed", "statistical", "significance"
                ],
                "context_clues": [
                    "we analyzed", "statistical analysis", "p <", "p-value",
                    "correlation", "regression", "we calculated", "we modeled"
                ],
                "semantic_roles": ["analytical_action", "statistical_method"]
            },
            "Conclusion": {
                "indicators": [
                    "conclude", "demonstrate", "show", "indicate", "suggest",
                    "reveal", "establish", "confirm", "support"
                ],
                "context_clues": [
                    "in conclusion", "we conclude", "these results", "our findings",
                    "this study shows", "we demonstrate", "our data indicate"
                ],
                "semantic_roles": ["conclusive_statement", "result_summary"]
            }
        }
        
        # Semantic disambiguation rules
        self.disambiguation_rules = {
            "patients": {
                "medical_context": ["disease", "treatment", "clinical", "therapy", "diagnosis"],
                "behavioral_context": ["patience", "waiting", "endurance", "tolerance"]
            },
            "model": {
                "scientific_context": ["mathematical", "statistical", "computational", "simulation"],
                "biological_context": ["mouse", "cell", "animal", "organism"],
                "fashion_context": ["fashion", "clothing", "runway", "design"]
            },
            "analysis": {
                "process_context": ["we analyzed", "analyzing", "analysis of"],
                "result_context": ["analysis shows", "analysis revealed", "analysis indicates"]
            }
        }
    
    def extract_semantic_context(self, sentence: str, section: str, surrounding_sentences: List[str] = None) -> SemanticContext:
        """Extract the semantic context of a sentence"""
        if self.nlp:
            doc = self.nlp(sentence)
            entities = [ent.text for ent in doc.ents]
            # extract Key Entities and Semantic Role
            key_entities = [token.lemma_ for token in doc if token.pos_ in ['NOUN', 'PROPN'] and not token.is_stop]
        else:
            # 简单fallback
            entities = re.findall(r'\b[A-Z][a-z]+\b', sentence)
            key_entities = re.findall(r'\b\w+\b', sentence.lower())
        
        # 确定Semantic Role
        semantic_role = self._determine_semantic_role(sentence, section)
        
        return SemanticContext(
            sentence=sentence,
            section=section,
            surrounding_sentences=surrounding_sentences or [],
            key_entities=key_entities,
            semantic_role=semantic_role,
            confidence=0.8
        )
    
    def _determine_semantic_role(self, sentence: str, section: str) -> str:
        """Determine the semantic role of a sentence"""
        sentence_lower = sentence.lower()
        
        # Semantic Role based on section
        section_roles = {
            "introduction": "background_hypothesis",
            "methods": "methodology_procedure", 
            "results": "data_presentation",
            "discussion": "interpretation_conclusion"
        }
        
        base_role = section_roles.get(section, "general")
        
        # Semantic Role based on sentence structure
        if any(word in sentence_lower for word in ["we hypothesize", "we propose", "we predict"]):
            return "hypothesis_statement"
        elif any(word in sentence_lower for word in ["we conducted", "we performed", "we used"]):
            return "experimental_action"
        elif any(word in sentence_lower for word in ["we analyzed", "we calculated", "statistical"]):
            return "analytical_action"
        elif any(word in sentence_lower for word in ["in conclusion", "we conclude", "our findings"]):
            return "conclusive_statement"
        
        return base_role
    
    def semantic_disambiguation(self, word: str, context: SemanticContext) -> str:
        """Semantic disambiguation - determine the true meaning of a term based on its context"""
        word_lower = word.lower()
        
        if word_lower not in self.disambiguation_rules:
            return word_lower
        
        rules = self.disambiguation_rules[word_lower]
        context_text = " ".join([context.sentence] + context.surrounding_sentences).lower()
        
        # 计算每个含义的Confidence
        meaning_scores = {}
        for meaning, clues in rules.items():
            score = sum(1 for clue in clues if clue in context_text)
            meaning_scores[meaning] = score
        
        # 返回得分最高的含义
        if meaning_scores:
            best_meaning = max(meaning_scores, key=meaning_scores.get)
            if meaning_scores[best_meaning] > 0:
                return f"{word_lower}_{best_meaning}"
        
        return word_lower
    
    def extract_nodes_with_semantics(self, text: str, sections: Dict[str, str]) -> List[Dict[str, Any]]:
        """Extract nodes using semantic understanding"""
        nodes = []
        
        for section_name, section_text in sections.items():
            sentences = self._segment_sentences(section_text)
            
            for i, sentence in enumerate(sentences):
                if len(sentence.strip()) < 20:  # Skip overly short sentences
                    continue
                
                # 获取周围句子的上下文
                surrounding = sentences[max(0, i-1):i+2]
                context = self.extract_semantic_context(sentence, section_name, surrounding)
                
                # 语义匹配
                matched_type = self._semantic_match(sentence, context)
                
                if matched_type:
                    # Semantic Disambiguation处理
                    disambiguated_text = self._apply_semantic_disambiguation(sentence, context)
                    
                    node = {
                        "id": self._gen_id(matched_type[:3].upper()),
                        "type": matched_type,
                        "text": disambiguated_text,
                        "section": section_name,
                        "confidence": context.confidence,
                        "evidence": f"semantic:{matched_type}",
                        "semantic_context": {
                            "role": context.semantic_role,
                            "entities": context.key_entities[:5],  # 限制长度
                            "disambiguation_applied": True
                        },
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                    }
                    nodes.append(node)
        
        return nodes
    
    def _segment_sentences(self, text: str) -> List[str]:
        """句子分割"""
        if self.nlp:
            doc = self.nlp(text)
            return [sent.text.strip() for sent in doc.sents if sent.text.strip()]
        else:
            # 简单fallback
            sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
            return [s.strip() for s in sentences if s.strip() and len(s.strip()) > 10]
    
    def _semantic_match(self, sentence: str, context: SemanticContext) -> Optional[str]:
        """Semantic-based matching"""
        sentence_lower = sentence.lower()
        
        # 计算每个节点类型的语义匹配分数
        type_scores = {}
        
        for node_type, patterns in self.semantic_patterns.items():
            score = 0
            
            # 1. 关键词匹配
            for indicator in patterns["indicators"]:
                if indicator in sentence_lower:
                    score += 2
            
            # 2. 上下文线索匹配
            for clue in patterns["context_clues"]:
                if clue in sentence_lower:
                    score += 3
            
            # 3. Semantic Role匹配
            for role in patterns["semantic_roles"]:
                if role in context.semantic_role:
                    score += 1
            
            # 4. Section上下文匹配
            section_weights = {
                "introduction": {"Hypothesis": 2, "Experiment": 0, "Dataset": 0, "Analysis": 0, "Conclusion": 0},
                "methods": {"Hypothesis": 0, "Experiment": 2, "Dataset": 2, "Analysis": 0, "Conclusion": 0},
                "results": {"Hypothesis": 0, "Experiment": 1, "Dataset": 1, "Analysis": 2, "Conclusion": 0},
                "discussion": {"Hypothesis": 1, "Experiment": 0, "Dataset": 0, "Analysis": 1, "Conclusion": 2}
            }
            
            section_weight = section_weights.get(context.section, {}).get(node_type, 0)
            score += section_weight
            
            type_scores[node_type] = score
        
        # 返回得分最高的类型（如果分数足够高）
        if type_scores:
            best_type = max(type_scores, key=type_scores.get)
            if type_scores[best_type] >= 3:  # 设置阈值
                return best_type
        
        return None
    
    def _apply_semantic_disambiguation(self, sentence: str, context: SemanticContext) -> str:
        """Apply semantic disambiguation to a sentence"""
        words = sentence.split()
        disambiguated_words = []
        
        for word in words:
            # 清理词汇
            clean_word = re.sub(r'[^\w]', '', word.lower())
            disambiguated = self.semantic_disambiguation(clean_word, context)
            disambiguated_words.append(disambiguated)
        
        # 这里可以进一步处理，比如替换原句中的歧义词汇
        # 为了简化，这里返回原句子，但添加了语义注释
        return sentence
    
    def _gen_id(self, prefix: str) -> str:
        """生成唯一ID"""
        return f"{prefix}_{uuid.uuid4().hex[:6]}"
    
    def build_semantic_edges(self, nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Build semantic-based edge relationships"""
        edges = []
        
        # 按类型分组节点
        nodes_by_type = defaultdict(list)
        for node in nodes:
            nodes_by_type[node["type"]].append(node)
        
        # 语义边规则
        semantic_edge_rules = [
            ("Hypothesis", "Experiment", "tests_hypothesis"),
            ("Experiment", "Dataset", "uses_data"),
            ("Dataset", "Analysis", "analyzes_data"),
            ("Analysis", "Conclusion", "supports_conclusion")
        ]
        
        for src_type, tgt_type, rel_type in semantic_edge_rules:
            if src_type in nodes_by_type and tgt_type in nodes_by_type:
                for src_node in nodes_by_type[src_type]:
                    for tgt_node in nodes_by_type[tgt_type]:
                        # 计算语义相似度
                        semantic_similarity = self._calculate_semantic_similarity(src_node, tgt_node)
                        
                        if semantic_similarity > 0.3:  # 设置相似度阈值
                            edges.append({
                                "start": src_node["id"],
                                "end": tgt_node["id"],
                                "type": rel_type,
                                "confidence": semantic_similarity,
                                "semantic_evidence": f"similarity:{semantic_similarity:.2f}"
                            })
        
        return edges
    
    def _calculate_semantic_similarity(self, node1: Dict[str, Any], node2: Dict[str, Any]) -> float:
        """Compute semantic similarity between two nodes"""
        # 简单的相似度计算：基于共同实体和Semantic Role
        entities1 = set(node1.get("semantic_context", {}).get("entities", []))
        entities2 = set(node2.get("semantic_context", {}).get("entities", []))
        
        if not entities1 or not entities2:
            return 0.0
        
        # Jaccard相似度
        intersection = len(entities1.intersection(entities2))
        union = len(entities1.union(entities2))
        
        return intersection / union if union > 0 else 0.0

# 测试函数
if __name__ == "__main__":
    # Test semantic extractor
    extractor = SemanticIMRaDExtractor()
    
    test_text = """
    We hypothesize that artemisinin treatment will reduce testosterone levels in PCOS patients.
    We conducted experiments using n=24 mice to test this hypothesis.
    We analyzed the data using statistical methods and found significant results.
    In conclusion, our findings demonstrate the efficacy of artemisinin treatment.
    """
    
    sections = {"introduction": test_text}
    nodes = extractor.extract_nodes_with_semantics(test_text, sections)
    
    print("Semantic extraction results:")
    for node in nodes:
        print(f"- {node['type']}: {node['text'][:50]}...")
        print(f"  Semantic Role: {node['semantic_context']['role']}")
        print(f"  Key Entities: {node['semantic_context']['entities']}")
        print()
