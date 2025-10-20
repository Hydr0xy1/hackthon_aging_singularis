import fitz
import re
import sys
import os
from pathlib import Path
from typing import Dict

def extract_text_from_pdf(pdf_path: str) -> str:
    """从PDF提取文本并清理"""
    try:
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            page_text = page.get_text("text")
            # 清理页码和页眉页脚
            lines = []
            for line in page_text.split("\n"):
                line = line.strip()
                # 过滤页码和短行
                if (not re.match(r"^\s*\d+\s*$", line) and 
                    len(line) > 10 and  # 过滤太短的行
                    not line.isupper()):  # 过滤全大写的行（可能是页眉）
                    lines.append(line)
            text += " ".join(lines) + "\n\n"
        return text
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        return ""

def segment_imrad(text: str) -> Dict[str, str]:
    """IMRaD分段"""
    from .utils import SECTION_PATTERNS
    
    indices = []
    for name, pattern in SECTION_PATTERNS.items():
        matches = list(re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE))
        if matches:
            # 取第一个匹配的位置
            indices.append((matches[0].start(), name))
    
    if not indices:
        return {"body": text}

    # 按位置排序
    indices.sort()
    sections = {}
    
    for i, (start, name) in enumerate(indices):
        # 结束位置是下一个section的开始，或者是文本结尾
        end = indices[i + 1][0] if i + 1 < len(indices) else len(text)
        sections[name] = text[start:end].strip()
    
    return sections

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python pdf_to_text.py <pdf_file>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    text = extract_text_from_pdf(pdf_path)
    
    # 保存原始文本
    base_name = Path(pdf_path).stem
    output_dir = Path("outputs")
    output_dir.mkdir(exist_ok=True)
    
    with open(output_dir / f"{base_name}_full.txt", "w", encoding="utf-8") as f:
        f.write(text)
    
    print(f"Extracted text saved to outputs/{base_name}_full.txt")
    print(f"Text length: {len(text)} characters")