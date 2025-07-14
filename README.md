
# TraceCoder  
  
- [English](./README.md)  
- [中文](./README_CN.md)  

**TraceCoder** is a Python framework designed for conducting experiments in code generation and automated code repair. It enables the evaluation and enhancement of code generation and debugging techniques using various language models and datasets.

## Key Features

- **Configurable Experiment Workflow**: Easily configure models, datasets, number of debugging attempts, and other parameters via command-line arguments.
- **Multi-Dataset Support**: Built-in support for loading and processing popular code datasets such as `HumanEval`, `BigCodeBench`, and others.
- **Code Generation and Evaluation**: Capable of generating code from prompts and evaluating it against test cases provided by the dataset.
- **Self-Debugging Capability**: Implements a multi-round self-debugging loop where the model analyzes errors, instruments code, and attempts repairs.
- **Flexible Evaluation Mechanism**: Dynamically loads dataset-specific evaluation functions for different benchmarks.
- **Results Reporting**: Experiment results can be saved as CSV files with summary statistics.
- **Modular Design**: Well-structured project layout for easy extension and maintenance.

A framework for code generation and self-debugging experiments, supporting evaluation of code generation quality and validation of automated repair workflows across multiple models and datasets.

---

## Core Functionalities

- **Multi-Dataset Support**: Built-in support for the following datasets:
  - `humaneval`: HumanEval code generation benchmark
  - `humanevalplus`: HumanEval+ enhanced benchmark
  - `bigcodebench`: BigCodeBench large-scale code evaluation dataset
  - `classeval`: ClassEval class-related code benchmark

- **Code Generation and Evaluation**:
  - Integrated model invocation interfaces
  - Automatic loading of dataset-specific evaluation modules to verify code correctness

- **Self-Debugging Workflow**:
  - Three-step repair mechanism: Code Instrumentation → Error Analysis → Code Repair
  - Configurable parameters such as maximum debugging attempts (`--max-debug-attempts`) and improvement thresholds (`--max-no-improvement-streak`)

- **Execution Safety Measures**:
  - Code sandboxing to restrict dangerous operations (filesystem access, system calls, etc.)
  - Execution timeout control (default 10 seconds, adjustable via `--timeout`)

- **Results Logging**:
  - Automatic generation of CSV reports containing generated code, evaluation results, and debugging logs

---

## Experimental Results

**Performance comparison (Pass@1, %) of TraceCoder against baseline methods on four benchmarks across different foundation models. "Ours" refers to our proposed TraceCoder. The best result in each setting is marked in bold. The value in parentheses indicates the absolute improvement (↑) over the second-best method.**

| Models | Methods | Humaneval | Humanevalplus | ClassEval | BigCodeBench-Complete | BigCodeBench-Instruct |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Gemini-2.5-Flash-0417 | **Ours** | **99.39 (↑ 0.61)** | **98.17 (↑ 1.83)** | **81.00 (↑ 20.00)** | **89.04 (↑ 10.97)** | **85.00 (↑ 13.95)** |
| DeepSeek-V3-0324 | **Ours** | **98.78 (↑ 3.05)** | **96.34 (↑ 3.66)** | **78.00 (↑ 15.00)** | **88.33 (↑ 5.96)** | **83.77 (↑ 9.21)** |
| Qwen-Plus-2025-01-25 | **Ours** | **96.34 (↑ 1.22)** | **93.90 (↑ 2.44)** | **63.00 (↑ 14.00)** | **71.93 (↑ 0.97)** | **68.60 (↑ 4.83)** |

---

## Directory Structure

```plaintext
TraceCoder/
├── config.py               # Global configuration
├── trace_learn_coder.py    # Main execution entry point
├── problem_processor.py    # Core problem processing logic
├── reporting.py            # Results saving and summarization
├── src/                    # Utility modules
│   ├── dataset_loader.py   # Dataset loading
│   ├── generation.py       # Model invocation and generation logic
│   ├── traceRunner.py      # Code execution and output capture
│   └── postprocessing.py   # Code post-processing
└── datasets/               # Dataset-specific evaluation modules
    ├── human_eval/         # HumanEval execution logic
    ├── human_eval_plus/    # HumanEval+ execution logic
    ├── BigCodeBench/       # BigCodeBench evaluation logic
    └── ClassEval/          # ClassEval evaluation logic
```

## Quick Start

### 1. Environment Setup
```bash
# Install base dependencies
pip install pandas transformers openai python-dotenv  # Includes dataset loading, model invocation, and environment variable management libraries
```

### 2. Configure Dataset Paths

Modify the DATASET_PATHS section in config.py to point to your local dataset storage locations:
```python
# config.py
DATASET_PATHS = {
    "humaneval": {
        "data_path": "/your/local/path/human_eval/data/test.jsonl",  # Local HumanEval test set path (JSONL)
        "eval_module": "datasets.human_eval.execution"
    },
    "humanevalplus": {
        "data_path": "/your/local/path/human_eval_plus/data/test.parquet",  # Local HumanEval+ test set path (Parquet)
        "eval_module": "datasets.human_eval.execution"
    },
    "bigcodebench": {
        "data_path": "/your/local/path/BigCodeBench/data/v0.1.4.parquet",  # Local BigCodeBench test set path (Parquet)
        "eval_module": "datasets.BigCodeBench.evaluation"
    },
    "classeval": {
        "data_path": "/your/local/path/ClassEval/data/test.parquet",  # Local ClassEval test set path (Parquet)
        "eval_module": "datasets.ClassEval.evaluation"
    }
}
```

### 3. Configure API Keys

Modify the OpenAI configuration in src/generation.py:
```python
# --- OpenAI/Compatible API Client Configuration ---
client = OpenAI(
    api_key="your_api_key_here", 
    base_url="your_base_url_here" 
)
```

### 4. Run Experiments

```bash
# Basic run (using default model and HumanEval dataset)
python trace_learn_coder.py -m gemini-2.5-flash-preview-04-17 -d humaneval

# Advanced parameter example (disable instrumentation, limit problems, customize timeout)
python trace_learn_coder.py \
    -m your_custom_model \          # Replace with actual model name
    -d bigcodebench \               # Specify BigCodeBench dataset
    --max-problems 50 \             # Process up to 50 problems
    --timeout 15 \                  # Adjust code execution timeout to 15 seconds
    --output-file ./results/my_exp.csv  # Custom results output path
```
