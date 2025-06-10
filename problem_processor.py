import re
import time
from itertools import islice
import importlib 
from typing import Callable 

# 导入同级模块的函数
from config import DATASET_PATHS 
from reporting import format_check_correctness_result
from src.generation import generator 
from src.traceRunner import execute_code_and_capture_prints_last # <<< 新增导入
from src.postprocessing import remove_main_block # <<< 新增导入 for _parse_llm_response


# --- 辅助函数 ---
def _parse_llm_response(response_text: str) -> tuple[str, str, str]:
    """ 
    从LLM的完整响应中解析出“分析”、“修复的代码部分”和“完整的代码”。 
    LLM被指示以特定格式返回这三部分。 
    """ 
    plan = "计划未找到或LLM未解析。" 
    repaired_part = ""  # 如果未找到，则为空字符串 
    full_code = "" 

    # 1. 解析 PLAN (ANALYSIS) 
    plan_match = re.search(r"ANALYSIS:(.*?)END_ANALYSIS", response_text, re.DOTALL | re.IGNORECASE) 
    if plan_match: 
        plan = plan_match.group(1).strip() 

    # 2. 解析 Repaired CODE Part 
    #    需要注意```python可能在Repaired CODE Part:的下一行 
    repaired_part_match = re.search( 
        r"Repaired CODE Part:\s*(?:```python\n(.*?)\n```|```(.*?)\n```|(.*?))\s*(?:CODE:|END_CODE|$)", response_text, 
        re.DOTALL | re.IGNORECASE) 
    if repaired_part_match: 
        # group(1) 是 ```python ... ```, group(2)是 ``` ... ```, group(3) 是没有```但被CODE:或END_CODE或末尾截断的 
        repaired_part = (repaired_part_match.group(1) or repaired_part_match.group(2) or repaired_part_match.group(
            3) or "").strip() 

    # 3. 解析 CODE (完整的代码) 
    #    允许 CODE: 标记和 ```python 之间有可选的换行和空格 
    full_code_match = re.search(r"CODE:\s*```python\n(.*?)\n```\s*(?:END_CODE|$)", response_text, 
                                re.DOTALL | re.IGNORECASE) 
    if not full_code_match:  # 尝试没有 END_CODE 的情况 
        full_code_match = re.search(r"CODE:\s*```python\n(.*?)\n```", response_text, re.DOTALL | re.IGNORECASE) 
    if not full_code_match:  # 尝试没有 python 标签的情况 
        full_code_match = re.search(r"CODE:\s*```\n(.*?)\n```\s*(?:END_CODE|$)", response_text, 
                                    re.DOTALL | re.IGNORECASE) 
    if not full_code_match:  # 尝试没有 python 标签也没有 END_CODE 
        full_code_match = re.search(r"CODE:\s*```\n(.*?)\n```", response_text, re.DOTALL | re.IGNORECASE) 

    if full_code_match: 
        full_code = full_code_match.group(1).strip() 
    else:  # 如果严格格式未找到，尝试更宽松地从 "CODE:" 之后提取 
        code_marker_match = re.search(r"CODE:(.*)", response_text, re.DOTALL | re.IGNORECASE) 
        if code_marker_match: 
            potential_code_section = code_marker_match.group(1).strip() 
            # 再次尝试从中提取```python ... ``` 
            inner_code_match = re.search(r"```python\n(.*?)\n```", potential_code_section, re.DOTALL) 
            if not inner_code_match: inner_code_match = re.search(r"```(?:.*\n)?(.*?)\n```", potential_code_section, 
                                                                  re.DOTALL) 

            if inner_code_match: 
                full_code = inner_code_match.group(1).strip() 
            else:  # 否则，认为CODE:之后到END_CODE（如果存在）或末尾都是代码 
                full_code = potential_code_section.replace("END_CODE", "").strip() 
                if full_code.startswith("```python"): full_code = full_code[len("```python"):].strip() 
                if full_code.startswith("```"): full_code = full_code[len("```"):].strip() 
                if full_code.endswith("```"): full_code = full_code[:-len("```")].strip() 

    # 后处理和健全性检查 
    if not full_code and plan_match and "END_ANALYSIS" in response_text: 
        full_code = "# LLM提供了分析，但没有可解析的完整代码块。" 
    elif not full_code and not plan_match:  # 如果什么主要标记都没找到 
        # 尝试把整个响应作为代码，如果它看起来像代码 
        if "def " in response_text or "import " in response_text or "class " in response_text: 
            full_code = response_text 
            plan = "# 未找到明确的分析；整个响应被视为代码。" 
            # repaired_part 保持空 
        else:  # 否则，认为代码无效 
            plan = response_text  # 整个响应可能是分析 
            full_code = "# LLM响应中未找到可解析的完整代码。" 

    if full_code and not full_code.startswith("# LLM"): 
        full_code = remove_main_block(full_code) # 使用导入的 remove_main_block 
        # full_code = remove_comments_and_docstrings(full_code) # 用户提供的代码中此行是注释掉的 
        full_code = full_code.strip() 

    # 如果repaired_part为空但full_code有效，可以尝试从full_code中“猜测”一个repaired_part 
    # 但这比较复杂且可能不准确，暂时将其留空。LLM应明确提供。 

    return plan, repaired_part, full_code



def _build_instrumentation_prompt(code_to_debug: str) -> str:
    """构建用于代码插桩的提示。"""
    return f"""The Python code below failed tests. Add `print()` statements to trace its execution and variable states, focusing on areas related to the 'Test Failure Feedback'.

Key Instrumentation Rules:
1.  Identify several logical blocks/steps in the code.
2.  For each block/step, print:
    *   Key inputs.
    *   Key outputs/results.
    *   Entry/exit of major functions/loops if helpful.
3.  ONLY add print statements(Don't comment it out). DO NOT change the original code logic or fix errors.
4.  Prints should be informative, like: `print(f"[BlockName] Input: {{var}}")`.

Code to Instrument:
```python
{code_to_debug}
```

Please provide ONLY the instrumented Python code.
"""


def _get_failed_history_str(history: list) -> str:
    """格式化历史失败记录。"""
    if not history:
        return "There have been no previous attempts to fix the failure for this specific problem instance."

    formatted_failed_list = []
    for i, attempt_info in enumerate(islice(reversed(history), 2)):
        plan_summary = attempt_info.get('plan', "N/A")
        eval_result = attempt_info['eval_result']
        formatted_failed_list.append(
            f"Historical Failed Fix Attempt {i + 1} (Passed {eval_result.get('passed_count', 0)}/{eval_result.get('total_count', 1)} tests):\n"
            f"Previous Analysis & Plan (which FAILED to lead to a full fix):\n'''\n{plan_summary}\n'''\n"
            f"That attempt resulted in these errors (on the generated code):\n{format_check_correctness_result(eval_result)}\n---"
        )
    return "\n".join(formatted_failed_list)


def _build_analysis_planning_prompt(problem_data, code_to_debug, captured_prints, history) -> str:
    """构建两步法中第一步（分析与规划）的提示。"""
    failed_history_str = _get_failed_history_str(history)
    return f"""You are a debugging assistant.
Given the following information about a Python function that failed tests:

1. Original Problem Description:
```python
{problem_data['complete_prompt']}
```
2. Code to Debug (this is the version before this repair attempt):
```python
{code_to_debug}
```
3. Captured Print Output and Execution Error Messages:
```text
{captured_prints}
```
4. MISTAKES TO AVOID:
```
{failed_history_str}
```
Your tasks are:
Step 1. Analyze the `Captured Print Output` to pinpoint the bug(s).
Step 2. Explain the root cause for each bug.
Step 3. Review `MISTAKES TO AVOID` and explain how your new plan is different and better.
Step 4. Propose a concise, step-by-step, actionable plan to fix the bug(s).

Output your response as clear text. Focus on an actionable plan. Let's think step by step.
"""


def _build_code_implementation_prompt(problem_data, code_to_fix, captured_prints, repair_plan) -> str:
    """构建两步法中第二步（代码实现）的提示。"""
    return f"""You are a code generation assistant.
You need to fix the following Python code based on the provided repair plan.

Original Problem Description:
```python
{problem_data['complete_prompt']}
```
Faulty Code to Fix:
```python
{code_to_fix}
```
Test Failure Feedback:
```
{captured_prints}
```
Detailed Repair Plan (Follow this plan carefully!):
```text
{repair_plan}
```
Your response MUST be in the specified format:
Repaired CODE Part:
```python
[The part of the code you modified/added.]
```
CODE:
```python
[Your complete corrected Python code here.]
```
END_CODE
"""


def _build_one_step_repair_prompt(problem_data, code_to_fix, failure_feedback, captured_prints, history) -> str:
    """构建单步修复的提示。"""
    failed_history_str = _get_failed_history_str(history)
    return f"""You are a debugging and code generation assistant. The following Python code failed tests.

Original Problem:
```python
{problem_data['complete_prompt']}
```
Faulty Code to Fix:
```python
{code_to_fix}
```
Test Failure Feedback:
```
{failure_feedback}
```
Captured Print Output (if available):
```text
{captured_prints}
```
MISTAKES TO AVOID:
```
{failed_history_str}
```
Your response MUST be in the specified format:
ANALYSIS:
[Your brief analysis and plan here.]
END_ANALYSIS
CODE:
```python
[Your complete corrected Python code here.]
```
END_CODE
"""

def _load_check_correctness_func(dataset_name: str) -> Callable:
    """
    根据数据集名称动态加载并返回相应的 check_correctness 函数。
    """
    try:
        module_path = DATASET_PATHS[dataset_name]["eval_module"]
        eval_module = importlib.import_module(module_path)
        check_correctness_func = getattr(eval_module, "check_correctness")
        return check_correctness_func
    except KeyError:
        raise ValueError(f"Dataset '{dataset_name}' not found in DATASET_PATHS in config.py.")
    except AttributeError:
        raise ImportError(f"'check_correctness' function not found in module '{module_path}'.")
    except ImportError as e:
        raise ImportError(f"Could not import evaluation module '{module_path}': {e}. Ensure __init__.py files exist in package directories.")


# --- 核心处理函数 ---
def _run_direct_generation(problem_data, args, check_correctness_func_param: Callable): # 新增参数
    """执行第一阶段：直接代码生成和评估。"""
    prompt = problem_data.get('complete_prompt', '')
    generated_code, p_tokens, c_tokens = generator(prompt, "code3_generate", args.model)
    # 使用传递进来的函数
    eval_result = check_correctness_func_param(problem_data, generated_code, args.timeout)
    return {"code": generated_code, "eval_result": eval_result, "prompt_tokens": p_tokens,
            "completion_tokens": c_tokens}


def _run_self_debugging(initial_code, initial_eval, problem_data, args, check_correctness_func_param: Callable): # 新增参数
    """执行第二阶段：自调试循环 (已更新，包含完整逻辑)。"""
    code_to_debug, last_eval, best_code, best_eval = initial_code, initial_eval, initial_code, initial_eval
    log, history, p_tokens, c_tokens, streak = [], [], 0, 0, 0

    for attempt in range(1, args.max_debug_attempts + 1):
        print(
            f"--- 调试尝试: {attempt}/{args.max_debug_attempts} | 最佳: {best_eval.get('passed_count', 0)}/{best_eval.get('total_count', 1)} ---")

        # 1. 插桩
        captured_prints = "Instrumentation skipped or not applicable."
        if not args.no_instrumentation:
            instr_prompt = _build_instrumentation_prompt(code_to_debug)
            instrumented_code, p, c = generator(instr_prompt, "code3_generate", args.model)
            p_tokens, c_tokens = p_tokens + p, c_tokens + c

            if instrumented_code.strip():
                exec_result = execute_code_and_capture_prints_last(
                    instrumented_code + "\n\n" + problem_data.get('test', ''), timeout_seconds=args.timeout)
                captured_prints = exec_result.get('display_output', 'No instrumentation output captured.')

        # 2. 调用LLM进行修复 (根据策略选择 prompt)
        plan, candidate_code = "N/A", ""

        if not args.no_two_step_repair:
            # 两步法
            analysis_prompt = _build_analysis_planning_prompt(problem_data, code_to_debug, captured_prints, history)
            plan, p, c = generator(analysis_prompt, "code4_generate", args.model)
            p_tokens, c_tokens = p_tokens + p, c_tokens + c

            if plan.strip():
                impl_prompt = _build_code_implementation_prompt(problem_data, code_to_debug, captured_prints, plan)
                # 使用 code4_generate 是因为原始脚本中修复也是用这个，它会返回结构化文本
                llm_response, p, c = generator(impl_prompt, "code4_generate", args.model)
                p_tokens, c_tokens = p_tokens + p, c_tokens + c
                _, _, candidate_code = _parse_llm_response(llm_response)
        else:
            # 单步法
            one_step_prompt = _build_one_step_repair_prompt(problem_data, code_to_debug,
                                                            format_check_correctness_result(last_eval), captured_prints,
                                                            history)
            llm_response, p, c = generator(one_step_prompt, "code4_generate", args.model)
            p_tokens, c_tokens = p_tokens + p, c_tokens + c
            plan, _, candidate_code = _parse_llm_response(llm_response)

        # 3. 评估和决策
        if not candidate_code.strip():
            print("LLM 未提供有效代码，终止调试。");
            break

        eval_candidate = check_correctness_func_param(problem_data, candidate_code, args.timeout) # 使用传递进来的函数
        print(f"候选修复结果: {format_check_correctness_result(eval_candidate)}")

        attempt_log = {"attempt": attempt, "plan": plan, "eval_result": eval_candidate}
        log.append(attempt_log)

        if eval_candidate.get('passed'):
            best_code, best_eval = candidate_code, eval_candidate;
            break

        if eval_candidate.get('passed_count', 0) > best_eval.get('passed_count', 0):
            best_code, best_eval, code_to_debug, last_eval, streak = candidate_code, eval_candidate, candidate_code, eval_candidate, 0
        else:
            streak += 1

        history.append(attempt_log)
        if streak >= args.max_no_improvement_streak:
            print(f"连续 {streak} 次无改进，终止调试。");
            break

    return {"final_code": best_code, "final_eval": best_eval, "session_log": log, "prompt_tokens": p_tokens,
            "completion_tokens": c_tokens}


# `process_problem` 函数保持不变，因为它只是调用上面的核心函数
def process_problem(problem_data, task_id, args, check_correctness_func_param: Callable): # 新增参数
    # (此函数无需修改，从上一版本复制即可)
    print(f"\n{'=' * 25} 正在处理问题: {task_id} {'=' * 25}")
    start_time = time.time()

    gen_res = _run_direct_generation(problem_data, args, check_correctness_func_param) # 传递参数

    result = {
        "task_id": task_id, "model": args.model, "dataset": args.dataset,
        "method_instrumentation": not args.no_instrumentation,
        "method_two_step_repair": not args.no_two_step_repair,
        "direct_gen_code": gen_res["code"], "direct_gen_eval": gen_res["eval_result"],
        "direct_gen_passed": gen_res["eval_result"].get("passed", False),
    }

    total_p, total_c = gen_res["prompt_tokens"], gen_res["completion_tokens"]

    if result["direct_gen_passed"]:
        print("直接生成成功通过。")
        result.update({"final_code": gen_res["code"], "final_eval": gen_res["eval_result"], "final_passed": True,
                       "stopped_reason": "Passed on direct generation"})
    else:
        print("直接生成失败，进入自调试阶段。")
        debug_res = _run_self_debugging(gen_res["code"], gen_res["eval_result"], problem_data, args, check_correctness_func_param) # 传递参数
        result.update({
            "final_code": debug_res["final_code"], "final_eval": debug_res["final_eval"],
            "final_passed": debug_res["final_eval"].get("passed", False),
            "debug_session_log": debug_res["session_log"], "stopped_reason": "Debug cycle completed"
        })
        total_p += debug_res["prompt_tokens"]
        total_c += debug_res["completion_tokens"]

    result.update({"total_prompt_tokens": total_p, "total_completion_tokens": total_c,
                   "processing_time_seconds": time.time() - start_time})

    print(f"问题 {task_id} 处理完毕。最终结果: {'通过' if result['final_passed'] else '失败'}")
    return result
