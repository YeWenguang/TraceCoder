# TraceLearnCoder

`TraceLearnCoder` 是一个用于进行代码生成和自动修复实验的 Python 框架。它支持使用不同的语言模型和数据集来评估和改进代码生成与修复技术。

## 主要功能

- **可配置的实验流程**: 通过命令行参数轻松配置模型、数据集、调试尝试次数等。
- **多种数据集支持**: 内置对 `HumanEval`、`BigCodeBench` 等流行代码数据集的加载和处理逻辑。
- **代码生成与评估**: 支持直接从提示生成代码，并根据数据集提供的测试用例进行评估。
- **自调试能力**: 实现了一个多轮自调试循环，模型可以尝试分析错误、插桩代码并进行修复。
- **灵活的评估机制**: 允许为不同数据集动态加载特定的评估函数。
- **结果报告**: 实验结果可以保存为 CSV 文件，并提供总结性输出。
- **模块化设计**: 项目结构清晰，易于扩展和维护。

一个用于代码生成与自调试实验的框架，支持多模型、多数据集的代码生成质量评估与自动修复流程验证。

---

## 核心功能

- **多数据集支持**：内置支持以下数据集（可通过 `config.py` 扩展）：
  - `humaneval`：HumanEval 代码生成测试集（JSONL 格式）
  - `humanevalplus`：HumanEval+ 增强测试集（Parquet 格式）
  - `bigcodebench`：BigCodeBench 大规模代码评估集（Parquet 格式）
  - `classeval`：ClassEval 类相关代码测试集（Parquet 格式）

- **代码生成与评估**：
  - 集成模型调用接口（支持本地模型推理或第三方 API，如 Gemini）
  - 自动加载数据集配套的评估模块（`datasets/*/execution.py` 或 `evaluation.py`）验证代码正确性

- **自调试流程**：
  - 两步修复机制：直接生成 → 插桩分析 → LLM 修复（可通过 `--no-two-step-repair` 禁用）
  - 支持调试尝试次数（`--max-debug-attempts`）、无改进阈值（`--max-no-improvement-streak`）等参数控制

- **执行安全防护**：
  - 代码沙箱限制危险操作（文件系统访问、系统调用等）
  - 执行超时控制（默认 10 秒，可通过 `--timeout` 调整）

- **结果记录**：
  - 自动输出包含生成代码、评估结果、调试日志的 CSV 报告（默认路径：`results/experiment_*.csv`）

---

## 目录结构

```plaintext
TraceLearnCoder/
├── config.py               # 全局配置（数据集路径、命令行参数）
├── trace_learn_coder.py    # 主执行入口
├── problem_processor.py    # 问题处理核心逻辑（生成/调试流程）
├── reporting.py            # 结果保存与汇总
├── src/                    # 工具模块
│   ├── dataset_loader.py   # 数据集加载（支持 JSONL/Parquet）
│   ├── generation.py       # 模型调用与生成逻辑
│   ├── traceRunner.py      # 代码执行与输出捕获
│   └── postprocessing.py   # 代码后处理（如移除 main 块）
└── datasets/               # 各数据集评估模块
    ├── human_eval/         # HumanEval 执行逻辑（含安全沙箱）
    ├── human_eval_plus/    # HumanEval+ 执行逻辑
    ├── BigCodeBench/       # BigCodeBench 评估逻辑
    └── ClassEval/          # ClassEval 评估逻辑
```

## 快速开始

### 1. 环境准备
```bash
# 安装基础依赖（根据实际项目需求调整）
pip install pandas transformers openai python-dotenv  # 包含数据集加载、模型调用、环境变量管理库
```

### 2. 配置数据集路径

修改 config.py 中的 DATASET_PATHS 字段，将各数据集的 data_path 替换为本地实际存储路径：
```python
# config.py（关键配置片段）
DATASET_PATHS = {
    "humaneval": {
        "data_path": "/your/local/path/human_eval/data/test.jsonl",  # 本地 HumanEval 测试集路径（JSONL）
        "eval_module": "datasets.human_eval.execution"
    },
    "humanevalplus": {
        "data_path": "/your/local/path/human_eval_plus/data/test.parquet",  # 本地 HumanEval+ 测试集路径（Parquet）
        "eval_module": "datasets.human_eval.execution"
    },
    "bigcodebench": {
        "data_path": "/your/local/path/BigCodeBench/data/v0.1.4.parquet",  # 本地 BigCodeBench 测试集路径（Parquet）
        "eval_module": "datasets.BigCodeBench.evaluation"
    },
    "classeval": {
        "data_path": "/your/local/path/ClassEval/data/test.parquet",  # 本地 ClassEval 测试集路径（Parquet）
        "eval_module": "datasets.ClassEval.evaluation"
    }
}
```

### 3. 运行实验

```bash
# 基础运行（使用默认模型和 HumanEval 数据集）
python trace_learn_coder.py -m gemini-2.5-flash-preview-04-17 -d humaneval

# 高级参数示例（禁用插桩、限制问题数、自定义超时）
python trace_learn_coder.py \
    -m your_custom_model \          # 替换为实际模型名称（如本地部署的 LLM）
    -d bigcodebench \               # 指定使用 BigCodeBench 数据集
    --no-instrumentation \          # 禁用代码插桩（跳过执行日志捕获）
    --max-problems 50 \             # 最多处理 50 个问题
    --timeout 15 \                  # 代码执行超时时间调整为 15 秒
    --output-file ./results/my_exp.csv  # 自定义结果输出路径
```
