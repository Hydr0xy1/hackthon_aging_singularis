#!/usr/bin/env python3
"""
高精度PDF文本提取器
解决PDF文本提取中的各种问题，提升精确度
"""

import fitz
import re
import sys
import os
from pathlib import Path
from typing import List, Tuple, Dict, Any
import unicodedata

class EnhancedPDFExtractor:
    """高精度PDF文本提取器"""
    
    def __init__(self):
        # 常见PDF问题模式
        self.problem_patterns = {
            'page_numbers': [
                r'^\s*\d+\s*$',  # 纯数字页码
                r'^\s*-\s*\d+\s*-\s*$',  # -1-, -2- 格式
                r'^\s*Page\s+\d+\s*$',  # Page 1, Page 2
                r'^\s*\d+\s*of\s+\d+\s*$',  # 1 of 10
            ],
            'headers_footers': [
                r'^\s*[A-Z\s]+\s*$',  # 全大写标题
                r'^\s*[A-Z][a-z]+\s+[A-Z][a-z]+\s*$',  # 作者名等
                r'^\s*©\s*\d{4}\s*',  # 版权信息
                r'^\s*doi:\s*',  # DOI信息
                r'^\s*http[s]?://',  # URL
            ],
            'figure_captions': [
                r'^\s*Figure\s+\d+',  # Figure 1, Figure 2
                r'^\s*Fig\.\s+\d+',  # Fig. 1
                r'^\s*Table\s+\d+',  # Table 1
                r'^\s*Tab\.\s+\d+',  # Tab. 1
            ],
            'references': [
                r'^\s*\[\d+\]',  # [1], [2]
                r'^\s*\d+\.\s*[A-Z]',  # 1. Author
            ],
            'noise_lines': [
                r'^\s*$',  # 空行
                r'^\s*\.\s*$',  # 只有点
                r'^\s*-\s*$',  # 只有横线
                r'^\s*_\s*$',  # 只有下划线
            ]
        }
        
        # 学术论文特定模式
        self.academic_patterns = {
            'sections': [
                r'^\s*\d*\.?\s*(Abstract|Introduction|Methods?|Results?|Discussion|Conclusion|References)',
                r'^\s*\d+\.\d*\s+[A-Z]',  # 1.1, 1.2 等子章节
            ],
            'citations': [
                r'\([A-Z][a-z]+\s+et\s+al\.\s*,\s*\d{4}\)',  # (Author et al., 2024)
                r'\[[A-Z][a-z]+\s+et\s+al\.\s*,\s*\d{4}\]',  # [Author et al., 2024]
            ],
            'measurements': [
                r'\d+\.\d+\s*(mg|kg|ml|μl|mm|cm|°C|°F)',  # 测量单位
                r'p\s*[<≤]\s*0\.\d+',  # p < 0.05
            ]
        }
    
    def extract_text_from_pdf(self, pdf_path: str, out_path: str = None) -> str:
        """高精度PDF文本提取"""
        print(f"📄 开始高精度提取: {os.path.basename(pdf_path)}")
        
        try:
            doc = fitz.open(pdf_path)
            all_text = []
            page_stats = []
            
            for page_num, page in enumerate(doc):
                # 获取页面文本
                page_text = page.get_text("text")
                
                # 分析页面内容
                page_analysis = self._analyze_page_content(page_text, page_num)
                page_stats.append(page_analysis)
                
                # 清理和优化文本
                cleaned_text = self._clean_page_text(page_text, page_analysis)
                
                if cleaned_text.strip():
                    all_text.append(cleaned_text)
            
            doc.close()
            
            # 后处理整个文档
            final_text = self._post_process_document(all_text, page_stats)
            
            # 保存结果
            if out_path:
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(final_text)
                print(f"✅ 高精度文本已保存: {out_path}")
            
            return final_text
            
        except Exception as e:
            print(f"❌ PDF提取错误: {e}")
            return ""
    
    def _analyze_page_content(self, page_text: str, page_num: int) -> Dict[str, Any]:
        """分析页面内容特征"""
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
            
            # 检查各种模式
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
        
        # 计算平均行长度
        if content_lines:
            analysis['avg_line_length'] = sum(len(line) for line in content_lines) / len(content_lines)
        
        # 检测特殊内容
        full_text = ' '.join(content_lines).lower()
        analysis['has_abstract'] = 'abstract' in full_text
        analysis['has_references'] = 'references' in full_text or 'bibliography' in full_text
        
        # 评估内容质量
        analysis['content_quality'] = self._assess_content_quality(analysis)
        
        return analysis
    
    def _is_header_footer(self, line: str) -> bool:
        """判断是否为页眉页脚"""
        for pattern in self.problem_patterns['headers_footers']:
            if re.match(pattern, line, re.IGNORECASE):
                return True
        return False
    
    def _is_figure_caption(self, line: str) -> bool:
        """判断是否为图表标题"""
        for pattern in self.problem_patterns['figure_captions']:
            if re.match(pattern, line, re.IGNORECASE):
                return True
        return False
    
    def _is_reference(self, line: str) -> bool:
        """判断是否为参考文献"""
        for pattern in self.problem_patterns['references']:
            if re.match(pattern, line):
                return True
        return False
    
    def _is_noise_line(self, line: str) -> bool:
        """判断是否为噪音行"""
        for pattern in self.problem_patterns['noise_lines']:
            if re.match(pattern, line):
                return True
        return False
    
    def _assess_content_quality(self, analysis: Dict[str, Any]) -> str:
        """评估页面内容质量"""
        content_ratio = analysis['content_lines'] / max(analysis['total_lines'], 1)
        
        if content_ratio > 0.8:
            return 'high'
        elif content_ratio > 0.6:
            return 'medium'
        else:
            return 'low'
    
    def _clean_page_text(self, page_text: str, analysis: Dict[str, Any]) -> str:
        """清理页面文本"""
        lines = page_text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            
            # 跳过空行和噪音
            if not line or self._is_noise_line(line):
                continue
            
            # 跳过页眉页脚
            if self._is_header_footer(line):
                continue
            
            # 跳过页码
            if re.match(r'^\s*\d+\s*$', line):
                continue
            
            # 处理图表标题（可选保留）
            if self._is_figure_caption(line):
                # 对于学术论文，可能想保留图表标题
                if analysis['content_quality'] == 'high':
                    cleaned_lines.append(line)
                continue
            
            # 处理参考文献（可选保留）
            if self._is_reference(line):
                # 根据页面质量决定是否保留
                if analysis['has_references'] and analysis['content_quality'] == 'high':
                    cleaned_lines.append(line)
                continue
            
            # 保留有效内容
            if len(line) > 10:  # 过滤太短的行
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def _post_process_document(self, all_text: List[str], page_stats: List[Dict[str, Any]]) -> str:
        """后处理整个文档"""
        # 合并所有页面文本
        full_text = '\n\n'.join(all_text)
        
        # 清理重复的空行
        full_text = re.sub(r'\n\s*\n\s*\n+', '\n\n', full_text)
        
        # 修复常见的PDF提取问题
        full_text = self._fix_common_pdf_issues(full_text)
        
        # 添加文档结构信息
        structure_info = self._add_structure_info(page_stats)
        
        return structure_info + '\n\n' + full_text
    
    def _fix_common_pdf_issues(self, text: str) -> str:
        """修复常见的PDF提取问题"""
        # 修复被分割的单词
        text = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', text)
        
        # 修复被分割的句子
        text = re.sub(r'(\w+)\s*\n\s*([a-z])', r'\1 \2', text)
        
        # 修复特殊字符
        text = unicodedata.normalize('NFKC', text)
        
        # 修复数字和单位
        text = re.sub(r'(\d+)\s+(\d+)', r'\1\2', text)  # 修复被分割的数字
        
        return text
    
    def _add_structure_info(self, page_stats: List[Dict[str, Any]]) -> str:
        """添加文档结构信息"""
        total_pages = len(page_stats)
        high_quality_pages = sum(1 for p in page_stats if p['content_quality'] == 'high')
        has_abstract = any(p['has_abstract'] for p in page_stats)
        has_references = any(p['has_references'] for p in page_stats)
        
        structure_info = f"""# PDF文档结构分析
- 总页数: {total_pages}
- 高质量页面: {high_quality_pages} ({high_quality_pages/total_pages*100:.1f}%)
- 包含摘要: {'是' if has_abstract else '否'}
- 包含参考文献: {'是' if has_references else '否'}
- 提取时间: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        return structure_info

def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("❌ 使用方法: python pdf_to_txt_enhanced.py <PDF文件路径> [输出文件路径]")
        print("💡 示例:")
        print("   python pdf_to_txt_enhanced.py data/artemisinin_pcos.pdf")
        print("   python pdf_to_txt_enhanced.py data/artemisinin_pcos.pdf outputs/enhanced_text.txt")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    out_path = sys.argv[2] if len(sys.argv) > 2 else pdf_path.replace(".pdf", "_enhanced.txt")
    
    if not os.path.exists(pdf_path):
        print(f"❌ 文件不存在: {pdf_path}")
        sys.exit(1)
    
    # 创建高精度提取器
    extractor = EnhancedPDFExtractor()
    
    # 提取文本
    text = extractor.extract_text_from_pdf(pdf_path, out_path)
    
    if text:
        print(f"✅ 高精度提取完成!")
        print(f"📊 提取文本长度: {len(text)} 字符")
        print(f"📄 输出文件: {out_path}")
    else:
        print("❌ 文本提取失败")

if __name__ == "__main__":
    main()
