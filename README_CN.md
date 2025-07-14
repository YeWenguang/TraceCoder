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

- **多数据集支持**：内置支持以下数据集：
  - `humaneval`：HumanEval 代码生成测试集
  - `humanevalplus`：HumanEval+ 增强测试集
  - `bigcodebench`：BigCodeBench 大规模代码评估集
  - `classeval`：ClassEval 类相关代码测试集

- **代码生成与评估**：
  - 集成模型调用接口
  - 自动加载数据集配套的评估模块验证代码正确性

- **自调试流程**：
  - 三步修复机制：代码插桩 → 代码分析 → 代码修复
  - 支持调试尝试次数（`--max-debug-attempts`）、无改进阈值（`--max-no-improvement-streak`）等参数控制

- **执行安全防护**：
  - 代码沙箱限制危险操作（文件系统访问、系统调用等）
  - 执行超时控制（默认 10 秒，可通过 `--timeout` 调整）

- **结果记录**：
  - 自动输出包含生成代码、评估结果、调试日志的 CSV 报告

---

## 实验结果

**在不同基础模型上，TraceCoder 与基准方法在四个基准测试中的性能对比（通过率 @1，%）。“Ours” 指我们提出的 TraceCoder。每种设置下的最佳结果以粗体标记。括号中的数值表示相较于次优方法的绝对提升（↑）。**

| Models | Methods | Humaneval | Humanevalplus | ClassEval | BigCodeBench-Complete | BigCodeBench-Instruct |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Gemini-2.5-Flash-0417 | Direct | 96.34 | 91.46 | 38.00 | 53.77 | 43.77 |
| | CoT | 93.90 | 91.46 | 41.00 | 53.86 | 43.68 |
| | Self-Planning | 94.51 | 90.85 | 36.00 | 55.61 | 43.15 |
| | Self-Debugging | 98.78 | 96.34 | 61.00 | 78.07 | 71.05 |
| | INTERVENOR | **99.39 (↑ 0.61)** | 95.12 | 61.00 | 75.88 | 69.82 |
| | **Ours** | **99.39 (↑ 0.61)** | **98.17 (↑ 1.83)** | **81.00 (↑ 20.00)** | **89.04 (↑ 10.97)** | **85.00 (↑ 13.95)** |
| DeepSeek-V3-0324 | Direct | 94.51 | 90.24 | 41.00 | 38.25 | 46.67 |
| | CoT | 93.29 | 88.41 | 41.00 | 60.35 | 47.98 |
| | Self-Planning | 95.12 | 90.24 | 37.00 | 61.14 | 26.93 |
| | Self-Debugging | **98.78 (↑ 3.05)** | **96.34 (↑ 3.66)** | 61.00 | 82.37 | 74.56 |
| | INTERVENOR | 95.73 | 92.68 | 63.00 | 79.82 | 70.79 |
| | **Ours** | **98.78 (↑ 3.05)** | **96.34 (↑ 3.66)** | **78.00 (↑ 15.00)** | **88.33 (↑ 5.96)** | **83.77 (↑ 9.21)** |
| Qwen-Plus-2025-01-25 | Direct | 90.85 | 86.59 | 31.00 | 50.09 | 41.49 |
| | CoT | 93.29 | 87.19 | 33.00 | 48.07 | 43.50 |
| | Self-Planning | 90.85 | 84.75 | 37.00 | 37.36 | 41.75 |
| | Self-Debugging | **96.34 (↑ 1.22)** | **93.90 (↑ 2.44)** | 49.00 | 70.96 | 63.77 |
| | INTERVENOR | 95.12 | 91.46 | 48.00 | 68.60 | 61.75 |
| | **Ours** | **96.34 (↑ 1.22)** | **93.90 (↑ 2.44)** | **63.00 (↑ 14.00)** | **71.93 (↑ 0.97)** | **68.60 (↑ 4.83)** |

---

## 目录结构

```plaintext
TraceLearnCoder/
├── config.py               # 全局配置
├── trace_learn_coder.py    # 主执行入口
├── problem_processor.py    # 问题处理核心逻辑
├── reporting.py            # 结果保存与汇总
├── src/                    # 工具模块
│   ├── dataset_loader.py   # 数据集加载
│   ├── generation.py       # 模型调用与生成逻辑
│   ├── traceRunner.py      # 代码执行与输出捕获
│   └── postprocessing.py   # 代码后处理
└── datasets/               # 各数据集评估模块
    ├── human_eval/         # HumanEval 执行逻辑
    ├── human_eval_plus/    # HumanEval+ 执行逻辑
    ├── BigCodeBench/       # BigCodeBench 评估逻辑
    └── ClassEval/          # ClassEval 评估逻辑
```

## 快速开始

### 1. 环境准备
```bash
# 安装基础依赖
pip install pandas transformers openai python-dotenv  # 包含数据集加载、模型调用、环境变量管理库
```

### 2. 配置数据集路径

修改 config.py 中的 DATASET_PATHS 字段，将各数据集的 data_path 替换为本地实际存储路径：
```python
# config.py
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

### 3. 配置数据集路径

修改 src/generation.py 中的 OpenAI 字段，配置API：
```python
# --- OpenAI/兼容API的客户端配置 ---
client = OpenAI(
    api_key="your_api_key_here", 
    base_url="your_base_url_here" 
)
```

### 4. 运行实验

```bash
# 基础运行（使用默认模型和 HumanEval 数据集）
python trace_learn_coder.py -m gemini-2.5-flash-preview-04-17 -d humaneval

# 高级参数示例（禁用插桩、限制问题数、自定义超时）
python trace_learn_coder.py \
    -m your_custom_model \          # 替换为实际模型名称
    -d bigcodebench \               # 指定使用 BigCodeBench 数据集
    --max-problems 50 \             # 最多处理 50 个问题
    --timeout 15 \                  # 代码执行超时时间调整为 15 秒
    --output-file ./results/my_exp.csv  # 自定义结果输出路径
```
