import os
import json
import pandas as pd


def format_check_correctness_result(result_dict: dict) -> str:
    """
    将评估结果字典格式化为人类可读的字符串。
    """
    if not isinstance(result_dict, dict):
        return "无效的评估结果格式。"
    if result_dict.get('passed', False):
        return "所有测试通过。"

    failure_detail = result_dict.get('result', "未提供具体的失败细节。")
    passed_count = result_dict.get('passed_count', -1)
    total_count = result_dict.get('total_count', -1)

    return f"失败 ({passed_count}/{total_count} 通过): {failure_detail}"


def save_results(results_data, filename):
    """
    将实验结果列表保存到CSV文件。
    """
    if not results_data:
        print("没有结果可供保存。")
        return

    try:
        df = pd.DataFrame(results_data)
        # 将字典和列表列转换为JSON字符串以便安全存储
        for col in df.columns:
            if df[col].apply(lambda x: isinstance(x, (dict, list))).any():
                df[col] = df[col].apply(lambda x: json.dumps(x) if isinstance(x, (dict, list)) else x)

        output_dir = os.path.dirname(filename)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)

        df.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"\n实验结果已成功保存到: {filename}")
    except Exception as e:
        print(f"保存结果到CSV时出错: {e}")


def print_summary(results_data: list):
    """
    在实验结束时打印最终的统计摘要。
    """
    if not results_data:
        print("\n--- 实验总结 ---")
        print("未处理任何问题。")
        return

    df = pd.DataFrame(results_data)
    direct_pass_rate = df['direct_gen_passed'].mean() * 100
    final_pass_rate = df['final_passed'].mean() * 100
    print("\n--- 实验总结 ---")
    print(f"共处理问题: {len(df)}")
    print(f"直接通过率 (Pass@1): {direct_pass_rate:.2f}%")
    print(f"最终通过率 (调试后): {final_pass_rate:.2f}%")