A compact pipeline to extract IMRaD-style knowledge graphs from scientific papers.
Converts paper text into typed nodes (Hypothesis, Experiment, Dataset, Analysis, Conclusion) and simple edges, with: rule-based deterministic extraction, optional LLM fallback + pattern learning, high-precision PDF text extraction, optional semantic augmentation, CSV/HTML export and comparison utilities.

Requirements & setup

Python >= 3.8

Install dependencies:

pip install -r requirements.txt
python -m spacy download en_core_web_sm


A recommended requirements.txt (already in repo):

PyMuPDF==1.23.8
spacy==3.7.2
pandas==2.0.3
pyvis==0.3.2
networkx==3.1
jupyter==1.0.0
matplotlib==3.7.2
scikit-learn==1.3.0
tqdm==4.66.1
python-dotenv==1.0.0
pdfplumber==0.10.3
numpy==1.24.3
seaborn==0.12.2
pytest==7.4.0
black==23.9.1
flake8==6.1.0


Note: pdfplumber is optional (alternate PDF parsing). Scanned PDFs need OCR before processing.

Quick start

Extract text from a PDF (enhanced)

python pdf_to_txt_enhanced.py path/to/your.pdf outputs/your_pdf_enhanced.txt


Run deterministic IMRaD extractor (example run)

python imrad_extractor.py


This prints example nodes/edges from the built-in demo text.

Run the semantic pipeline (if src/semantic_extractor.py is present)

python run_semantic_pipeline.py path/to/your.pdf


Outputs are saved under outputs/ (CSV, HTML visualizations).

Compare traditional vs semantic node sets

python compare_methods.py outputs/your_nodes.csv outputs/your_semantic_nodes.csv


Generates outputs/semantic_vs_traditional_comparison.html.

Open the demo notebook

notebooks/demo_pipeline.ipynb — step-through demo.

Project layout (key files)
.
├── notebooks/
│   └── demo_pipeline.ipynb
├── outputs/                   # generated CSV/HTML
├── src/
│   ├── extract_imrad.py
│   ├── imrad_extractor.py
│   ├── pdf_to_txt.py
│   ├── pdf_to_txt_enhanced.py
│   ├── semantic_extractor.py   # optional semantic module
│   ├── build_graph.py
│   ├── build_graph_no_pandas.py
│   ├── visualize_graph.py
│   ├── utils.py
│   └── run_no_pandas.py
├── compare_methods.py
├── run_pipeline.py
├── run_semantic_pipeline.py
├── run_ultimate.py
├── requirements.txt
└── README.md

Outputs / formats

Nodes CSV/JSON: id, type, text, section, confidence, evidence, semantic_context, timestamp

Edges CSV/JSON: start, end, type, confidence, semantic_evidence

HTML visualizations: *_graph.html (nodes grouped by section, edges listed)

Comparison report: semantic_vs_traditional_comparison.html

Design notes & usage tips

Deterministic-first: rule-based cue phrases + section priors for explainability and reproducibility.

LLM fallback: expand_with_fallbacks(api_client=...) allows an external LLM wrapper to classify hard sentences; learned short cues are persisted to learned_patterns.json.

Semantic augmentation: drop-in src/semantic_extractor.py can provide entity linking, role labeling, and richer relations.

PDF quality: performance depends on PDF text layer. OCR scanned PDFs first.

Pattern hygiene: periodically review learned_patterns.json to avoid noise accumulation from LLM mistakes.

Contributing & License

Recommended license: MIT or Apache-2.0 (add LICENSE to repo).

Contributions welcome: add cue patterns, implement/improve SemanticIMRaDExtractor, add tests and examples. Please include sample inputs + expected outputs in PRs.