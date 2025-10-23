# IMRaD knowledge graph extraction system

### environment setup

```bash
# 1. create environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# 2. install requirement
pip install -r requirements.txt

# 3. run the command
python run_semantic_pipeline.py data/artemisinin_pcos.pdf
python compare_methods.py outputs/artemisinin_pcos_nodes.csv outputs/artemisinin_pcos_semantic_semantic_nodes.csv

```

