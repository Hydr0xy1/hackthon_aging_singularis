# IMRaD 知识图谱提取系统

从科研论文PDF中自动提取IMRaD结构（假设、实验、数据集、分析、结论）并构建交互式知识图谱。

## 🚀 快速开始

### 环境设置

```bash
# 1. 创建虚拟环境
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# 2. 安装依赖
pip install -r requirements.txt

# 3. 设置环境（自动安装缺失依赖）
python setup_environment.py
```

project/
├── data/           # 输入PDF文件
├── src/            # 源代码
│   ├── pdf_to_text.py     # PDF文本提取
│   ├── extract_imrad.py   # IMRaD结构解析
│   ├── build_graph.py     # 图谱构建
│   ├── visualize_graph.py # 可视化
│   └── utils.py           # 工具函数
├── outputs/        # 输出文件
├── notebooks/      # Jupyter笔记本
├── tests/          # 测试文件
└── docs/           # 文档
