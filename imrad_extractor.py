# python >=3.8
# pip install spacy regex
# python -m spacy download en_core_web_sm
# # Optional (if using nltk instead of spaCy)
# pip install nltk


"""
imrad_extractor.py

Deterministic IMRaD extractor:
- Input: raw paper text (string)
- Output: JSON: nodes (Hypothesis/Experiment/Dataset/Analysis/Conclusion) + edges
- Strategy: section detection -> sentence segmentation -> deterministic regex/heuristics -> LLM fallback -> pattern learning

Author: ChatGPT (template)
"""

import re
import json
import uuid
import os
from collections import defaultdict, Counter

# Optional: spaCy for sentence segmentation
try:
    import spacy
    nlp = spacy.load("en_core_web_sm")
    def sents_from_text(text):
        return [sent.text.strip() for sent in nlp(text).sents if sent.text.strip()]
except Exception:
    # fallback to simple newline/sentence splitter
    import re
    def sents_from_text(text):
        # very simple: split on period/question/exclamation followed by space + capital letter
        chunks = re.split(r'(?<=[\.\?\!])\s+(?=[A-Z0-9])', text)
        return [c.strip() for c in chunks if c.strip()]


# -------------------------
# Config: deterministic cue phrases (can be expanded)
# -------------------------
CUE_PATTERNS = {
    "Hypothesis": [
        r"\bwe hypothesi[sz]e\b",
        r"\bwe hypothes[ie]d\b",
        r"\bwe propose\b",
        r"\bit is hypothesized\b",
        r"\bwe predict\b",
        r"\bthis suggests\b.*hypoth",
        r"\bhypothesi[sz]e\b",
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
    ],
    "Dataset": [
        r"\bcohort\b",
        r"\bTCGA\b",
        r"\bPCAWG\b",
        r"\b(n=|n =)\d+",
        r"\bdata (?:from|obtained from|available at)\b",
        r"\bGEO\b",
        r"\b(whole[- ]genome|exome|WGS|WES|RNA-Seq|RNA Sequencing)\b",
    ],
    "Analysis": [
        r"\bwe (?:analyz|computed|calculated|modeled|fit)\b",
        r"\bwe (?:used|applied) (?:regression|model|linear|xgboost|random forest|cox)\b",
        r"\bcorrelat",
        r"\bstatistical (?:analysis|test)\b",
        r"\bp-value\b|\bp < 0\.",
        r"\bwe trained\b",
    ],
    "Conclusion": [
        r"\bin conclusion\b",
        r"\bwe conclude\b",
        r"\bthese results (?:suggest|indicate|show)\b",
        r"\bthis study (?:shows|demonstrates)\b",
        r"\bsignificantly\b.*\b(implicat|associate|reduce|increase)\b",
    ]
}

# Patterns to detect section headings (IMRaD)
SECTION_HEADINGS = {
    "INTRODUCTION": re.compile(r'^\s*(introduction|background)\s*$', re.I | re.M),
    "METHODS": re.compile(r'^\s*(methods|materials and methods|methodology|experimental procedures)\s*$', re.I | re.M),
    "RESULTS": re.compile(r'^\s*(results)\s*$', re.I | re.M),
    "DISCUSSION": re.compile(r'^\s*(discussion|conclusions)\s*$', re.I | re.M),
    "ABSTRACT": re.compile(r'^\s*(abstract)\s*$', re.I | re.M),
    "CONCLUSION": re.compile(r'^\s*(conclusions|conclusion)\s*$', re.I | re.M)
}

# Simple mapping of sections to node relevance (heuristic)
SECTION_NODE_PRIOR = {
    "ABSTRACT": ["Hypothesis", "Conclusion"],
    "INTRODUCTION": ["Hypothesis"],
    "METHODS": ["Experiment", "Dataset"],
    "RESULTS": ["Experiment", "Analysis", "Dataset"],
    "DISCUSSION": ["Conclusion", "Hypothesis"],
    "CONCLUSION": ["Conclusion"]
}


# -------------------------
# Utilities
# -------------------------
def gen_id(prefix):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def match_patterns(text, patterns):
    """Return list of pattern matches (pattern, match_obj)"""
    matches = []
    for p in patterns:
        m = re.search(p, text, flags=re.I)
        if m:
            matches.append((p, m))
    return matches

# -------------------------
# Core extractor
# -------------------------
class IMRaDExtractor:
    def __init__(self, patterns=CUE_PATTERNS, section_map=SECTION_HEADINGS,
                 node_prior=SECTION_NODE_PRIOR, pattern_store_path="learned_patterns.json"):
        self.patterns = {k: [re.compile(p, re.I) for p in v] for k, v in patterns.items()}
        self.section_map = section_map
        self.node_prior = node_prior
        self.pattern_store_path = pattern_store_path
        self.learned = self._load_learned_patterns()

    def _load_learned_patterns(self):
        if os.path.exists(self.pattern_store_path):
            try:
                with open(self.pattern_store_path, "r", encoding="utf8") as fh:
                    return json.load(fh)
            except Exception:
                pass
        return {k: [] for k in self.patterns.keys()}

    def _save_learned_patterns(self):
        with open(self.pattern_store_path, "w", encoding="utf8") as fh:
            json.dump(self.learned, fh, indent=2, ensure_ascii=False)

    def split_sections(self, text):
        """Split by headings if available. Returns list of (section_name, section_text)."""
        # naive approach: find lines that look like headings
        lines = text.splitlines()
        sections = []
        current_name = "BODY"
        buffer = []
        for ln in lines:
            ln_stripped = ln.strip()
            # if a heading line
            found = None
            for name, regex in self.section_map.items():
                if regex.match(ln_stripped.lower() if isinstance(ln_stripped, str) else ln_stripped):
                    found = name
                    break
            if found:
                # push previous
                if buffer:
                    sections.append((current_name, "\n".join(buffer).strip()))
                current_name = found
                buffer = []
            else:
                buffer.append(ln)
        # final push
        if buffer:
            sections.append((current_name, "\n".join(buffer).strip()))
        # normalize: if no headings found, return BODY as single section
        if not sections:
            return [("BODY", text)]
        return sections

    def assign_candidates_from_section(self, section_name, section_text):
        """Return list of (node_type, sentence, confidence, evidence) found in this section."""
        sentences = sents_from_text(section_text)
        candidates = []
        for s in sentences:
            found = False
            # check learned patterns first
            for node_type, learned_list in self.learned.items():
                for lp in learned_list:
                    if re.search(lp, s, re.I):
                        candidates.append((node_type, s, 0.92, f"learned:{lp}"))
                        found = True
                        break
                if found:
                    break
            if found:
                continue

            # check core patterns, but also apply section prior weight
            for node_type, pat_list in self.patterns.items():
                for pat in pat_list:
                    if pat.search(s):
                        # base confidence
                        base_conf = 0.85
                        # boost if section matches prior
                        if node_type in self.node_prior.get(section_name, []):
                            base_conf += 0.08
                        candidates.append((node_type, s, round(min(0.99, base_conf), 2), f"pattern:{pat.pattern}"))
                        found = True
                        break
                if found:
                    break
            if not found:
                # no deterministic match: candidate for LLM fallback if this sentence is important (length & punctuation heuristics)
                # save as potential fallback
                if len(s.split()) >= 6 and len(s) <= 400:
                    candidates.append(("FALLBACK", s, 0.10, "no_pattern"))
        return candidates

    def deterministic_extract(self, text):
        """Main deterministic pass over full text"""
        sections = self.split_sections(text)
        nodes = []
        edges = []
        for sec_name, sec_text in sections:
            candidates = self.assign_candidates_from_section(sec_name, sec_text)
            for node_type, sent, conf, evidence in candidates:
                if node_type == "FALLBACK":
                    continue
                node = {
                    "id": gen_id(node_type[:3].upper()),
                    "type": node_type,
                    "text": sent,
                    "section": sec_name,
                    "evidence": evidence,
                    "confidence": conf
                }
                nodes.append(node)
        # build simple edges: experiments support analyses, analyses support conclusions, hypothesis->experiment if nearby
        # naive heuristic: connect nodes by section ordering
        nodes_by_section = defaultdict(list)
        for n in nodes:
            nodes_by_section[n["section"]].append(n)

        # Link Hypothesis -> Experiment if in Introduction -> Methods/Results
        for hyp in [n for n in nodes if n["type"] == "Hypothesis"]:
            for exp in [n for n in nodes if n["type"] == "Experiment"]:
                # only connect if different sections (heuristic)
                if hyp["section"] != exp["section"]:
                    edges.append({
                        "start": hyp["id"], "end": exp["id"],
                        "type": "POSES_TEST",
                        "evidence": f"{hyp['evidence']} -> {exp['evidence']}",
                        "confidence": round(min(hyp["confidence"], exp["confidence"]), 2)
                    })
        # Experiment -> Dataset / Analysis
        for exp in [n for n in nodes if n["type"] == "Experiment"]:
            for ds in [n for n in nodes if n["type"] == "Dataset"]:
                edges.append({
                    "start": exp["id"], "end": ds["id"],
                    "type": "USES_DATASET",
                    "evidence": f"{exp['evidence']} -> {ds['evidence']}",
                    "confidence": round(min(exp["confidence"], ds["confidence"]), 2)
                })
            for an in [n for n in nodes if n["type"] == "Analysis"]:
                edges.append({
                    "start": exp["id"], "end": an["id"],
                    "type": "GENERATES_ANALYSIS",
                    "evidence": f"{exp['evidence']} -> {an['evidence']}",
                    "confidence": round(min(exp["confidence"], an["confidence"]), 2)
                })
        # Analysis -> Conclusion
        for an in [n for n in nodes if n["type"] == "Analysis"]:
            for c in [n for n in nodes if n["type"] == "Conclusion"]:
                edges.append({
                    "start": an["id"], "end": c["id"],
                    "type": "SUPPORTS_CONCLUSION",
                    "evidence": f"{an['evidence']} -> {c['evidence']}",
                    "confidence": round(min(an["confidence"], c["confidence"]), 2)
                })

        return {"nodes": nodes, "edges": edges, "sections": sections}

    # -------------------------
    # LLM fallback + pattern learning (very simple implementation)
    # -------------------------
    def llm_fallback(self, sentence, api_client=None, prompt_template=None):
        """
        Call an LLM for classification into one of node types.
        This function is a placeholder showing how to integrate with an LLM.
        Provide api_client that wraps the LLM call and returns string label.
        Example minimal api_client: lambda prompt: "Hypothesis"
        """
        # If no external client provided, raise or return None
        if api_client is None:
            return None
        # Example prompt:
        prompt = (f"Classify the following sentence into one of: Hypothesis, Experiment, Dataset, Analysis, Conclusion, None.\n"
                  f"Sentence: '''{sentence}'''")
        label = api_client(prompt)  # user-supplied wrapper
        # sanitize
        label = (label or "").strip().split()[0]
        if label not in ["Hypothesis", "Experiment", "Dataset", "Analysis", "Conclusion", "None"]:
            label = "None"
        return label

    def expand_with_fallbacks(self, text, api_client=None, learn_new_patterns=True):
        """
        Deterministic pass + fallback pass.
        - Run deterministic_extract to get nodes.
        - For sentences flagged as FALLBACK, call LLM (if provided) to classify.
        - If LLM returns a label, add node. Also extract simple phrases to add to learned patterns.
        """
        sections = self.split_sections(text)
        primary = self.deterministic_extract(text)
        nodes = primary["nodes"]
        edges = primary["edges"]
        fallback_sentences = []

        # Identify fallback sentences
        for sec_name, sec_text in sections:
            sents = sents_from_text(sec_text)
            # find sentences that weren't covered by deterministic patterns
            for s in sents:
                covered = False
                for nt in nodes:
                    if nt["text"].strip() == s.strip():
                        covered = True
                        break
                if not covered and len(s.split()) >= 6 and len(s) <= 500:
                    fallback_sentences.append((sec_name, s))

        # call LLM for each fallback (if provided)
        for sec_name, s in fallback_sentences:
            label = None
            if api_client:
                label = self.llm_fallback(s, api_client=api_client)
            if label and label != "None":
                node = {
                    "id": gen_id(label[:3].upper()),
                    "type": label,
                    "text": s,
                    "section": sec_name,
                    "evidence": "llm_fallback",
                    "confidence": 0.6  # lower than deterministic
                }
                nodes.append(node)
                # simple learning: extract short cue phrases and add to learned patterns
                if learn_new_patterns:
                    phrase = self.simple_extract_cue(s)
                    if phrase:
                        # avoid duplicates
                        existing = set(self.learned.get(label, []))
                        if phrase not in existing:
                            self.learned[label].append(phrase)
            # else: skip
        # save learned patterns
        if learn_new_patterns:
            self._save_learned_patterns()

        # Optionally rebuild edges (simple approach: reuse earlier edge builder)
        # For simplicity, regenerate edges from full nodes list:
        edges = self._build_edges_from_nodes(nodes)
        return {"nodes": nodes, "edges": edges, "learned_patterns": self.learned}

    def simple_extract_cue(self, sentence, max_len=6):
        """
        Heuristic to extract a short cue phrase from a sentence for future deterministic matching.
        Strategy: take first verb phrase or first 2-3 words containing 'we' or 'this' or 'suggest'.
        More sophisticated extraction can use POS tagging.
        """
        # look for "we <verb>" patterns
        m = re.search(r'\bwe\s+([a-zA-Z-]+)', sentence, re.I)
        if m:
            cue = rf"\bwe\s+{re.escape(m.group(1))}\b"
            return cue
        # look for "this suggests" etc
        m = re.search(r'\b(this|these)\s+[a-z]+\b', sentence, re.I)
        if m:
            return re.escape(m.group(0))
        # fallback: take first 3 words as phrase
        first_words = " ".join(sentence.split()[:3])
        return re.escape(first_words)

    def _build_edges_from_nodes(self, nodes):
        edges = []
        # same heuristics as deterministic_extract but using provided nodes list
        for hyp in [n for n in nodes if n["type"] == "Hypothesis"]:
            for exp in [n for n in nodes if n["type"] == "Experiment"]:
                if hyp["section"] != exp["section"]:
                    edges.append({
                        "start": hyp["id"], "end": exp["id"], "type": "POSES_TEST",
                        "evidence": f"{hyp['evidence']} -> {exp['evidence']}", "confidence": round(min(hyp['confidence'], exp['confidence']), 2)
                    })
        for exp in [n for n in nodes if n["type"] == "Experiment"]:
            for ds in [n for n in nodes if n["type"] == "Dataset"]:
                edges.append({
                    "start": exp["id"], "end": ds["id"], "type": "USES_DATASET",
                    "evidence": f"{exp['evidence']} -> {ds['evidence']}", "confidence": round(min(exp['confidence'], ds['confidence']), 2)
                })
            for an in [n for n in nodes if n["type"] == "Analysis"]:
                edges.append({
                    "start": exp["id"], "end": an["id"], "type": "GENERATES_ANALYSIS",
                    "evidence": f"{exp['evidence']} -> {an['evidence']}", "confidence": round(min(exp['confidence'], an['confidence']), 2)
                })
        for an in [n for n in nodes if n["type"] == "Analysis"]:
            for c in [n for n in nodes if n["type"] == "Conclusion"]:
                edges.append({
                    "start": an["id"], "end": c["id"], "type": "SUPPORTS_CONCLUSION",
                    "evidence": f"{an['evidence']} -> {c['evidence']}", "confidence": round(min(an['confidence'], c['confidence']), 2)
                })
        return edges


# -------------------------
# Example usage
# -------------------------
if __name__ == "__main__":
    # Example: minimal test text to show pipeline
    sample_text = """
    Abstract
    Here we hypothesize that intermittent fasting reduces epigenetic age. We performed experiments in a mouse model.
    Introduction
    Epigenetic aging has been observed in many tissues. We propose that lifestyle can modulate epigenetic clocks.
    Methods
    We used a cohort of n=24 mice and measured methylation using Illumina arrays. We treated mice with daily fasting cycles.
    Results
    We observed a significant reduction of epigenetic age (p < 0.01). Our XGBoost model predicted chronological age with r=0.83.
    Discussion
    In conclusion, our data support the hypothesis that intermittent fasting reduces epigenetic age.
    """

    extractor = IMRaDExtractor()
    res_det = extractor.deterministic_extract(sample_text)
    print("Deterministic nodes:")
    print(json.dumps(res_det["nodes"], indent=2, ensure_ascii=False))
    print("Deterministic edges:")
    print(json.dumps(res_det["edges"], indent=2, ensure_ascii=False))

    # Simulate fallback: we provide a trivial LLM wrapper that labels sentences containing "clock" as Analysis
    def fake_llm(prompt):
        if "clock" in prompt.lower():
            return "Analysis"
        if "fasting" in prompt.lower():
            return "Hypothesis"
        return "None"

    res_full = extractor.expand_with_fallbacks(sample_text, api_client=fake_llm, learn_new_patterns=True)
    print("\nAfter fallback + learning:")
    print(json.dumps({"nodes": res_full["nodes"], "edges": res_full["edges"], "learned": extractor.learned}, indent=2, ensure_ascii=False))
