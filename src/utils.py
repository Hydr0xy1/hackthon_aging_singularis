import re
import uuid
import spacy
from typing import List, Dict, Any

# Try to load spaCy model，but have fallback
try:
    nlp = spacy.load("en_core_web_sm")
    SPACY_AVAILABLE = True
except OSError:
    print("⚠️  spaCy en_core_web_sm is not installed, use simple Sentence segmentation")
    print("   Run: python -m spacy download en_core_web_sm")
    nlp = None
    SPACY_AVAILABLE = False
except Exception as e:
    print(f"⚠️  spaCy import error: {e}，use simple Sentence segmentation")
    nlp = None
    SPACY_AVAILABLE = False

def gen_id(prefix: str) -> str:
    """Generate a unique ID"""
    return f"{prefix}_{uuid.uuid4().hex[:6]}"

def sentence_segmentation(text: str) -> List[str]:
    """Sentence segmentation - use spacy, and have fallback"""
    if SPACY_AVAILABLE and len(text) > 10:
        try:
            doc = nlp(text)
            return [sent.text.strip() for sent in doc.sents if sent.text.strip()]
        except Exception as e:
            print(f"spaCy segment filed: {e}，use simple sentence segmentation")
    
    # fallback: simple Sentence segmentation
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
    return [s.strip() for s in sentences if s.strip() and len(s.strip()) > 10]

# IMRaD section regex patterns
SECTION_PATTERNS = {
    "introduction": r"(?:^|\n)(?:\s*\d*\.*\s*Introduction|Background)",
    "methods": r"(?:^|\n)(?:\s*\d*\.*\s*(Materials and Methods|Methods|Experimental Procedures))",
    "results": r"(?:^|\n)(?:\s*\d*\.*\s*Results?)",
    "discussion": r"(?:^|\n)(?:\s*\d*\.*\s*(Discussion|Conclusion|Summary))",
}

# Node extraction regex patterns - missing CUE_PATTERNS!
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

# Simple mapping relationships
SECTION_NODE_PRIORITY = {
    "introduction": ["Hypothesis"],
    "methods": ["Experiment", "Dataset"],
    "results": ["Analysis", "Experiment"],
    "discussion": ["Conclusion", "Hypothesis"],
    "body": ["Hypothesis", "Experiment", "Dataset", "Analysis", "Conclusion"]
}

def match_patterns(text: str, patterns: List[str]) -> List[tuple]:
    """Return a list of matched patterns"""
    matches = []
    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            matches.append((pattern, True))
    return matches

def get_section_for_node(text: str, sections: Dict[str, str]) -> str:
    """Determine which section a node belongs to based on text"""
    for section_name, section_text in sections.items():
        if text in section_text:
            return section_name
    return "unknown"

# Test function
if __name__ == "__main__":
    # Sentence segmentation test
    test_text = "This is a test. We hypothesize that this works. We conducted experiments. In conclusion, it works."
    sentences = sentence_segmentation(test_text)
    print("Sentence segmentation test:")
    for i, sent in enumerate(sentences):
        print(f"  {i+1}. {sent}")
    
    print("\nPattern matching test:")
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