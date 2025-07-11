import sys
import time
from itertools import islice
from tqdm import tqdm

# 导入我们拆分出去的模块
from config import setup_arg_parser, DATASET_PATHS
from reporting import save_results, print_summary
# 从 problem_processor 导入 process_problem 和 _load_check_correctness_func
from problem_processor import process_problem, _load_check_correctness_func
from src.dataset_loader import load_dataset


def main():
    """
    实验的主执行函数。
    """
    # 1. 设置和解析参数
    parser = setup_arg_parser()
    args = parser.parse_args()

    # 2. 生成实验ID和输出文件名
    EXPERIMENT_ID = f"{args.dataset}_{args.model.replace('/', '_')}_{time.strftime('%Y%m%d_%H%M%S')}"
    OUTPUT_CSV_FILENAME = args.output_file or f"results/experiment_{EXPERIMENT_ID}.csv"

    # 3. 加载数据集
    if args.dataset not in DATASET_PATHS:
        print(f"错误: 数据集 '{args.dataset}' 的路径未在 config.py 中定义。")
        sys.exit(1)

    try:
        # 从 DATASET_PATHS[args.dataset] 字典中获取 'data_path'
        actual_dataset_path = DATASET_PATHS[args.dataset]["data_path"]
        datasets = load_dataset(args.dataset, actual_dataset_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"加载数据集时出错: {e}")
        sys.exit(1)
    except KeyError: # 新增 KeyErorr 捕获，以防 "data_path" 键不存在
        print(f"错误: 数据集 '{args.dataset}' 的配置中缺少 'data_path'。请检查 config.py。")
        sys.exit(1)

    # <<< 新增代码：加载 check_correctness 函数 >>>
    try:
        check_correctness_func = _load_check_correctness_func(args.dataset)
    except (ValueError, ImportError) as e:
        print(f"加载评估函数 check_correctness 时出错: {e}")
        sys.exit(1)
    # <<< 结束新增代码 >>>

    print(f"--- 实验开始: {EXPERIMENT_ID} ---")
    print(f"参数: {vars(args)}")

    # 4. 设置问题迭代器
    problem_keys = list(datasets.keys())
    start_index = args.start_index
    max_problems = len(problem_keys) if args.max_problems == -1 else args.max_problems
    end_index = min(start_index + max_problems, len(problem_keys))

    problem_iterator = islice(problem_keys, start_index, end_index)

    results_data = []

    # 5. 主循环
    try:
        for task_id in tqdm(problem_iterator, total=(end_index - start_index), desc="处理问题"):
            # 将加载的 check_correctness_func 传递下去
            problem_result = process_problem(datasets[task_id], task_id, args, check_correctness_func)
            results_data.append(problem_result)
    except KeyboardInterrupt:
        print("\n检测到手动中断。正在保存已有结果...")
    finally:
        # 6. 保存结果并打印总结
        save_results(results_data, OUTPUT_CSV_FILENAME)
        print_summary(results_data)


if __name__ == '__main__':
    main()
