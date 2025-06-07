import argparse

# --- 数据集路径配置 ---
# 请将这里的路径修改为你本地的实际文件路径
DATASET_PATHS = {
    "humaneval": { # 'human_eval' 键名已更改为 'humaneval' 以匹配 argparse choices
        "data_path": "./datasets/human_eval/data/test.jsonl", # 请替换为实际本地路径
        "eval_module": "datasets.human_eval.execution" # 评估模块的Python导入路径
    },
    "humanevalplus": {
        "data_path": "./datasets/human_eval_plus/data/test-00000-of-00001-5973903632b82d40.parquet", # 请替换为实际本地路径
        "eval_module": "datasets.human_eval.execution" # 评估模块的Python导入路径
    },
    "bigcodebench": {
        "data_path": "./datasets/BigCodeBench/data/v0.1.4-00000-of-00001.parquet",   # 请替换为实际本地路径
        "eval_module": "datasets.BigCodeBench.evaluation" # 评估模块的Python导入路径
    },
    "classeval": { # 新增 ClassEval 的 eval_module
        "data_path": "./datasets/ClassEval/data/test-00000-of-00001-5c45fa6e45572491.parquet",      # 请替换为实际本地路径
        "eval_module": "datasets.ClassEval.evaluation" # 评估模块的Python导入路径
    }
    # Add other datasets here, ensure they have 'data_path' and 'eval_module'
}

# 注意：请确保上述路径指向您本地存储数据集文件的实际位置。
# 文件名 (e.g., human_eval_problems.jsonl) 也是示例，请根据您的实际文件名进行调整。

# 评估函数 (check_correctness) 将在 problem_processor.py 中根据数据集动态加载和调用。
# 因此，此处的占位符函数已被移除。


def setup_arg_parser():
    """
    设置和解析命令行参数。
    """
    parser = argparse.ArgumentParser(description="运行代码生成和修复实验的框架")
    parser.add_argument('-m', '--model', type=str, default='gemini-2.5-flash-preview-04-17', help='要使用的模型名称')
    # 更新 choices 以匹配 DATASET_PATHS 中的键
    parser.add_argument('-d', '--dataset', type=str, required=True, choices=list(DATASET_PATHS.keys()), help='要使用的数据集')
    parser.add_argument('--no-instrumentation', action='store_true', help='禁用代码插桩步骤')
    parser.add_argument('--no-two-step-repair', action='store_true', help='禁用两步修复流程，使用单步修复')
    parser.add_argument('--start-index', type=int, default=0, help='数据集中开始处理问题的索引')
    parser.add_argument('--max-problems', type=int, default=-1, help='要处理的最大问题数量 (-1 表示处理所有)')
    parser.add_argument('--max-debug-attempts', type=int, default=5, help='每个问题的最大调试尝试次数')
    parser.add_argument('--max-no-improvement-streak', type=int, default=2, help='连续无改进时停止调试的阈值')
    parser.add_argument('--timeout', type=int, default=10, help='代码执行的超时时间（秒）')
    parser.add_argument('-o', '--output-file', type=str, default=None, help='指定输出CSV文件的路径和名称')
    return parser