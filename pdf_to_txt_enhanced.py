#!/usr/bin/env python3
"""
High-precision PDF text extractor
Solves various PDF text-extraction problems and improves accuracy.
"""

import fitz
import re
import sys
import os
from pathlib import Path
from typing import List, Tuple, Dict, Any
import unicodedata


class EnhancedPDFExtractor:
    """High-precision PDF text extractor"""

    def __init__(self):
        # Common PDF problem patterns
        self.problem_patterns = {
            'page_numbers': [
                r'^\s*\d+\s*$',              # plain numeric page numbers
                r'^\s*-\s*\d+\s*-\s*$',      # -1-, -2- style
                r'^\s*Page\s+\d+\s*$',       # Page 1, Page 2
                r'^\s*\d+\s*of\s+\d+\s*$',   # 1 of 10
            ],
            'headers_footers': [
                r'^\s*[A-Z\s]+\s*$',                     # all-caps headers
                r'^\s*[A-Z][a-z]+\s+[A-Z][a-z]+\s*$',   # author names, etc.
                r'^\s*©\s*\d{4}\s*',                     # copyright
                r'^\s*doi:\s*',                          # DOI
                r'^\s*http[s]?://',                      # URLs
            ],
            'figure_captions': [
                r'^\s*Figure\s+\d+',   # Figure 1, Figure 2
                r'^\s*Fig\.\s+\d+',    # Fig. 1
                r'^\s*Table\s+\d+',    # Table 1
                r'^\s*Tab\.\s+\d+',    # Tab. 1
            ],
            'references': [
                r'^\s*\[\d+\]',     # [1], [2]
                r'^\s*\d+\.\s*[A-Z]',  # 1. Author
            ],
            'noise_lines': [
                r'^\s*$',      # empty line
                r'^\s*\.\s*$', # only a dot
                r'^\s*-\s*$',  # only a dash
                r'^\s*_\s*$',  # only underscore
            ]
        }

        # Academic-paper-specific patterns
        self.academic_patterns = {
            'sections': [
                r'^\s*\d*\.?\s*(Abstract|Introduction|Methods?|Results?|Discussion|Conclusion|References)',
                r'^\s*\d+\.\d*\s+[A-Z]',  # 1.1, 1.2 subsections
            ],
            'citations': [
                r'\([A-Z][a-z]+\s+et\s+al\.\s*,\s*\d{4}\)',  # (Author et al., 2024)
                r'\[[A-Z][a-z]+\s+et\s+al\.\s*,\s*\d{4}\]',  # [Author et al., 2024]
            ],
            'measurements': [
                r'\d+\.\d+\s*(mg|kg|ml|μl|mm|cm|°C|°F)',  # units
                r'p\s*[<≤]\s*0\.\d+',                     # p < 0.05
            ]
        }

    # ------------------ public API ------------------
    def extract_text_from_pdf(self, pdf_path: str, out_path: str = None) -> str:
        """High-precision PDF text extraction"""
        print(f"📄 Starting high-precision extraction: {os.path.basename(pdf_path)}")

        try:
            doc = fitz.open(pdf_path)
            all_text = []
            page_stats = []

            for page_num, page in enumerate(doc):
                page_text = page.get_text("text")
                page_analysis = self._analyze_page_content(page_text, page_num)
                page_stats.append(page_analysis)

                cleaned_text = self._clean_page_text(page_text, page_analysis)
                if cleaned_text.strip():
                    all_text.append(c cleaned_text)

            doc.close()

            final_text = self._post_process_document(all_text, page_stats)

            if out_path:
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(final_text)
                print(f"✅ High-precision text saved: {out_path}")

            return final_text

        except Exception as e:
            print(f"❌ PDF extraction error: {e}")
            return ""

    # ------------------ internal helpers ------------------
    def _analyze_page_content(self, page_text: str, page_num: int) -> Dict[str, Any]:
        lines = page_text.split('\n')

        analysis = {
            'page_num': page_num,
            'total_lines': len(lines),
            'content_lines': 0,
            'header_lines': 0,
            'footer_lines': 0,
            'figure_captions': 0,
            'references': 0,
            'noise_lines': 0,
            'avg_line_length': 0,
            'has_abstract': False,
            'has_references': False,
            'content_quality': 'unknown'
        }

        content_lines = []

        for line in lines:
            line = line.strip()
            if not line:
                analysis['noise_lines'] += 1
                continue

            is_header = self._is_header_footer(line)
            is_figure = self._is_figure_caption(line)
            is_reference = self._is_reference(line)
            is_noise = self._is_noise_line(line)

            if is_header:
                analysis['header_lines'] += 1
            elif is_figure:
                analysis['figure_captions'] += 1
            elif is_reference:
                analysis['references'] += 1
            elif is_noise:
                analysis['noise_lines'] += 1
            else:
                content_lines.append(line)
                analysis['content_lines'] += 1

        if content_lines:
            analysis['avg_line_length'] = sum(len(l) for l in content_lines) / len(content_lines)

        full_text = ' '.join(content_lines).lower()
        analysis['has_abstract'] = 'abstract' in full_text
        analysis['has_references'] = any(k in full_text for k in ('references', 'bibliography'))
        analysis['content_quality'] = self._assess_content_quality(analysis)

        return analysis

    def _is_header_footer(self, line: str) -> bool:
        for pattern in self.problem_patterns['headers_footers']:
            if re.match(pattern, line, re.IGNORECASE):
                return True
        return False

    def _is_figure_caption(self, line: str) -> bool:
        for pattern in self.problem_patterns['figure_captions']:
            if re.match(pattern, line, re.IGNORECASE):
                return True
        return False

    def _is_reference(self, line: str) -> bool:
        for pattern in self.problem_patterns['references']:
            if re.match(pattern, line):
                return True
        return False

    def _is_noise_line(self, line: str) -> bool:
        for pattern in self.problem_patterns['noise_lines']:
            if re.match(pattern, line):
                return True
        return False

    def _assess_content_quality(self, analysis: Dict[str, Any]) -> str:
        content_ratio = analysis['content_lines'] / max(analysis['total_lines'], 1)
        if content_ratio > 0.8:
            return 'high'
        elif content_ratio > 0.6:
            return 'medium'
        return 'low'

    def _clean_page_text(self, page_text: str, analysis: Dict[str, Any]) -> str:
        lines = page_text.split('\n')
        cleaned_lines = []

        for line in lines:
            line = line.strip()
            if not line or self._is_noise_line(line):
                continue
            if self._is_header_footer(line):
                continue
            if re.match(r'^\s*\d+\s*$', line):  # page numbers
                continue

            # Optionally keep figure captions
            if self._is_figure_caption(line):
                if analysis['content_quality'] == 'high':
                    cleaned_lines.append(line)
                continue

            # Optionally keep references
            if self._is_reference(line):
                if analysis['has_references'] and analysis['content_quality'] == 'high':
                    cleaned_lines.append(line)
                continue

            if len(line) > 10:  # drop very short lines
                cleaned_lines.append(line)

        return '\n'.join(cleaned_lines)

    def _post_process_document(self, all_text: List[str], page_stats: List[Dict[str, Any]]) -> str:
        full_text = '\n\n'.join(all_text)
        full_text = re.sub(r'\n\s*\n\s*\n+', '\n\n', full_text)
        full_text = self._fix_common_pdf_issues(full_text)
        structure_info = self._add_structure_info(page_stats)
        return structure_info + '\n\n' + full_text

    def _fix_common_pdf_issues(self, text: str) -> str:
        # Rejoin hyphenated words split across lines
        text = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', text)
        # Rejoin sentences split across lines
        text = re.sub(r'(\w+)\s*\n\s*([a-z])', r'\1 \2', text)
        # Normalize unicode
        text = unicodedata.normalize('NFKC', text)
        # Rejoin split numbers
        text = re.sub(r'(\d+)\s+(\d+)', r'\1\2', text)
        return text

    def _add_structure_info(self, page_stats: List[Dict[str, Any]]) -> str:
        total_pages = len(page_stats)
        high_quality_pages = sum(1 for p in page_stats if p['content_quality'] == 'high')
        has_abstract = any(p['has_abstract'] for p in page_stats)
        has_references = any(p['has_references'] for p in page_stats)

        structure_info = f"""# PDF Document Structure Analysis
- Total pages: {total_pages}
- High-quality pages: {high_quality_pages} ({high_quality_pages/total_pages*100:.1f}%)
- Contains abstract: {'Yes' if has_abstract else 'No'}
- Contains references: {'Yes' if has_references else 'No'}
- Extraction time: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        return structure_info


# ------------------ CLI entry ------------------
def main():
    if len(sys.argv) < 2:
        print("❌ Usage: python pdf_to_txt_enhanced.py <PDF file path> [output file path]")
        print("💡 Examples:")
        print("   python pdf_to_txt_enhanced.py data/artemisinin_pcos.pdf")
        print("   python pdf_to_txt_enhanced.py data/artemisinin_pcos.pdf outputs/enhanced_text.txt")
        sys.exit(1)

    pdf_path = sys.argv[1]
    out_path = sys.argv[2] if len(sys.argv) > 2 else pdf_path.replace(".pdf", "_enhanced.txt")

    if not os.path.exists(pdf_path):
        print(f"❌ File not found: {pdf_path}")
        sys.exit(1)

    extractor = EnhancedPDFExtractor()
    text = extractor.extract_text_from_pdf(pdf_path, out_path)

    if text:
        print("✅ High-precision extraction completed!")
        print(f"📊 Extracted text length: {len(text)} characters")
        print(f"📄 Output file: {out_path}")
    else:
        print("❌ Text extraction failed")


if __name__ == "__main__":
    main()