import re
import uuid
import spacy
from typing import List, Dict, Any

# 尝试加载spacy模型，但有fallback
try:
    nlp = spacy.load("en_core_web_sm")
    SPACY_AVAILABLE = True
except OSError:
    print("⚠️  spaCy英语模型未安装，使用简单句子分割")
    print("   运行: python -m spacy download en_core_web_sm")
    nlp = None
    SPACY_AVAILABLE = False
except Exception as e:
    print(f"⚠️  spaCy加载失败: {e}，使用简单句子分割")
    nlp = None
    SPACY_AVAILABLE = False

def gen_id(prefix: str) -> str:
    """生成唯一ID"""
    return f"{prefix}_{uuid.uuid4().hex[:6]}"

def sentence_segmentation(text: str) -> List[str]:
    """句子分割 - 使用spacy，有fallback"""
    if SPACY_AVAILABLE and len(text) > 10:
        try:
            doc = nlp(text)
            return [sent.text.strip() for sent in doc.sents if sent.text.strip()]
        except Exception as e:
            print(f"spaCy分割失败: {e}，使用简单分割")
    
    # fallback: 简单句子分割
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
    return [s.strip() for s in sentences if s.strip() and len(s.strip()) > 10]

# IMRaD分段正则模式
SECTION_PATTERNS = {
    "introduction": r"(?:^|\n)(?:\s*\d*\.*\s*Introduction|Background)",
    "methods": r"(?:^|\n)(?:\s*\d*\.*\s*(Materials and Methods|Methods|Experimental Procedures))",
    "results": r"(?:^|\n)(?:\s*\d*\.*\s*Results?)",
    "discussion": r"(?:^|\n)(?:\s*\d*\.*\s*(Discussion|Conclusion|Summary))",
}

# 节点提取正则模式 - 这是缺失的 CUE_PATTERNS！
CUE_PATTERNS = {
    "Hypothesis": [
        r"\bwe hypothesi[sz]e\b",
        r"\bwe hypothes[ie]d\b",
        r"\bwe propose\b",
        r"\bit is hypothesized\b",
        r"\bwe predict\b",
        r"\bthis suggests\b.*hypoth",
        r"\bhypothesi[sz]e\b",
        r"\bthis study (?:aims|seeks|was designed) to\b",
        r"\bwe expect\b",
    ],
    "Experiment": [
        r"\bwe (?:performed|conducted|carried out|did)\b",
        r"\bwe treated\b",
        r"\bwe injected\b",
        r"\bwe administered\b",
        r"\bwe used (?:an )?(?:assay|model|mouse|cell|cohort|experiment)\b",
        r"\bmouse model\b",
        r"\bin vitro\b",
        r"\bin vivo\b",
        r"\busing (?:the )?(?:protocol|method|assay)\b",
        r"\bexperimental (?:setup|design|procedure)\b",
        r"\bmethods.*used\b",
    ],
    "Dataset": [
        r"\bcohort\b",
        r"\bTCGA\b",
        r"\bPCAWG\b",
        r"\b(n=|n =)\d+",
        r"\bdata (?:from|obtained from|available at)\b",
        r"\bGEO\b",
        r"\b(whole[- ]genome|exome|WGS|WES|RNA-Seq|RNA Sequencing)\b",
        r"\bdataset\b",
        r"\bpatients?\b.*\b(n=|included)\b",
        r"\bsamples\b",
    ],
    "Analysis": [
        r"\bwe (?:analyz|computed|calculated|modeled|fit)\b",
        r"\bwe (?:used|applied) (?:regression|model|linear|xgboost|random forest|cox)\b",
        r"\bcorrelat",
        r"\bstatistical (?:analysis|test)\b",
        r"\bp-value\b|\bp < 0\.",
        r"\bwe trained\b",
        r"\bwe analyzed\b",
        r"\bstatistical analysis\b",
        r"\bp\s*[<≤]\s*0\.\d+\b",
        r"\bwe calculated\b",
        r"\bcorrelation\b",
        r"\bregression\b",
    ],
    "Conclusion": [
        r"\bin conclusion\b",
        r"\bwe conclude\b",
        r"\bthese results (?:suggest|indicate|show)\b",
        r"\bthis study (?:shows|demonstrates)\b",
        r"\bsignificantly\b.*\b(implicat|associate|reduce|increase)\b",
        r"\bthis study (?:shows|demonstrates|reveals)\b",
        r"\bour findings\b",
        r"\bthese data\b.*\bsuggest\b",
    ]
}

# 简单的映射关系
SECTION_NODE_PRIORITY = {
    "introduction": ["Hypothesis"],
    "methods": ["Experiment", "Dataset"],
    "results": ["Analysis", "Experiment"],
    "discussion": ["Conclusion", "Hypothesis"],
    "body": ["Hypothesis", "Experiment", "Dataset", "Analysis", "Conclusion"]
}

def match_patterns(text: str, patterns: List[str]) -> List[tuple]:
    """返回匹配的模式列表"""
    matches = []
    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            matches.append((pattern, True))
    return matches

def get_section_for_node(text: str, sections: Dict[str, str]) -> str:
    """根据文本内容确定节点所属的章节"""
    for section_name, section_text in sections.items():
        if text in section_text:
            return section_name
    return "unknown"

# 测试函数
if __name__ == "__main__":
    # 测试句子分割
    test_text = "This is a test. We hypothesize that this works. We conducted experiments. In conclusion, it works."
    sentences = sentence_segmentation(test_text)
    print("句子分割测试:")
    for i, sent in enumerate(sentences):
        print(f"  {i+1}. {sent}")
    
    # 测试模式匹配
    print("\n模式匹配测试:")
    test_sentences = [
        "We hypothesize that artemisinin works.",
        "We conducted experiments with n=24 mice.",
        "We analyzed the data using statistical tests.",
        "In conclusion, our findings are significant."
    ]
    
    for sent in test_sentences:
        for node_type, patterns in CUE_PATTERNS.items():
            if any(re.search(p, sent, re.IGNORECASE) for p in patterns):
                print(f"  '{sent[:30]}...' → {node_type}")
                break