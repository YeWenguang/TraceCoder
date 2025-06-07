import time
import re
import ast
from typing import Tuple, Any, List
import torch
from openai import OpenAI, APIError, Timeout, RateLimitError # 假设这些是相关的异常
from transformers import AutoTokenizer

# 导入同级模块的函数
from .postprocessing import extract_python_code

# --- OpenAI/兼容API的客户端配置 ---
# 注意: 将API密钥和base_url等敏感信息外部化(例如，通过环境变量或配置文件)是最佳实践。
# 为了简化，我们暂时保留在这里，但在生产环境中应修改。
client = OpenAI(
    api_key="your_api_key_here",  # 示例: "ywg12345678" or os.getenv("MY_API_KEY")
    base_url="https://speedaye-gemini.hf.space/v1"  # 示例
)


# --- 内联辅助函数提升为顶级函数 ---

def get_split_point_after_last_return(code_string: str) -> int:
    try:
        tree = ast.parse(code_string)
    except SyntaxError:
        return len(code_string)
    last_return_end_line_num = -1
    for node in ast.walk(tree):
        if isinstance(node, ast.Return):
            node_effective_end_line = getattr(node, 'end_lineno', node.lineno)
            if node_effective_end_line is not None and node_effective_end_line > last_return_end_line_num:
                last_return_end_line_num = node_effective_end_line
    if last_return_end_line_num == -1:
        return len(code_string)
    lines = code_string.splitlines(True)
    char_offset = sum(len(lines[i]) for i in range(min(last_return_end_line_num, len(lines))))
    return char_offset


def remove_content_after_last_return(code_string: str) -> str:
    if not code_string.strip(): return ""
    split_point = get_split_point_after_last_return(code_string)
    if split_point >= len(code_string): return code_string.strip()
    code_to_keep = code_string[:split_point]
    code_to_process = code_string[split_point:]
    print_pattern = r'(?m)^\s*print\s*\(.*?\)\s*(?:#.*)?\n?'
    processed_after = re.sub(print_pattern, '', code_to_process)
    comment_pattern = r'(?m)^\s*#.*?\n?'
    processed_after = re.sub(comment_pattern, '', processed_after)
    processed_after = re.sub(r'(\s*\n\s*){2,}', '\n', processed_after).strip()
    final_code = code_to_keep.rstrip('\n')
    if processed_after:
        final_code += '\n' + processed_after
    return final_code.strip()


def extract_python_code_with_logic(text: str, remove_main: bool = True, remove_prints: bool = True,
                                   remove_repl_examples: bool = True) -> str:
    pattern_explicit = r"```python\s*\n(.*?)\n?```"
    pattern_generic = r"```\s*\n(.*?)\n?```"
    explicit_matches = re.findall(pattern_explicit, text, re.DOTALL | re.IGNORECASE)
    extracted_code_blocks_raw = [block.strip() for block in explicit_matches]
    if not extracted_code_blocks_raw:
        generic_matches = re.findall(pattern_generic, text, re.DOTALL)
        for block in generic_matches:
            if any(keyword in block.lower() for keyword in ['def ', 'import ', 'class ']):
                extracted_code_blocks_raw.append(block.strip())
    processed_code_blocks = []
    for raw_block in extracted_code_blocks_raw:
        processed_block = raw_block
        if remove_repl_examples:
            processed_block = re.sub(r'(?m)^\s*(>>>|\.\.\.)\s.*$\n?', '', processed_block)
        if remove_main:
            main_block_pattern = r'(?m)^\s*if\s+__name__\s*==\s*("__main__"|\'__main__\'):.*?(\n\s*\n|\Z)'
            processed_block = re.sub(main_block_pattern, '', processed_block, flags=re.DOTALL)
        if remove_prints:
            processed_block = remove_content_after_last_return(processed_block)
        processed_block = re.sub(r'(?m)^\s*\n', '', processed_block).strip()
        if processed_block:
            processed_code_blocks.append(processed_block)
    return "\n\n".join(processed_code_blocks).strip()


# --- API 调用函数 ---
def call_api(prompt, model, max_tokens_response=4096):
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system",
                 "content": "You are a helpful assistant specialized in code generation and debugging."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
        )
        result_text = response.choices[0].message.content
        prompt_tokens = response.usage.prompt_tokens if response.usage else 0
        completion_tokens = response.usage.completion_tokens if response.usage else 0
        time.sleep(1)
        return result_text, prompt_tokens, completion_tokens
    except RateLimitError as e:
        logger.warning(f"API速率限制错误: {e}. 可能需要等待更长时间后重试。") # 假设 logger 已配置
        # 这里可以加入更长的等待时间或特定的重试策略
        return None, 0, 0
    except APIError as e:
        logger.error(f"API调用时发生错误: {e}")
        return None, 0, 0
    except Timeout as e:
        logger.error(f"API调用超时: {e}")
        return None, 0, 0
    except Exception as e: # 捕获其他所有未预料到的异常
        logger.error(f"调用API时发生未知错误：{e}")
        return None, 0, 0


# --- 主生成器函数 ---
def generator(text: str, status: str, model_name: str, models=None, tokenizers=None) -> Tuple[Any, int, int]:
    """
    根据状态(status)调用不同的模型或API来生成内容。
    返回: (生成的内容, prompt_tokens, completion_tokens)
    """
    # 如果提供了本地模型 (models) 和分词器 (tokenizers)
    if models and tokenizers:
        # 此处保留本地模型生成逻辑
        messages = [{"role": "user", "content": text}]
        inputs = tokenizers.apply_chat_template(messages, add_generation_prompt=True, return_tensors="pt").to(
            models.device)
        outputs = models.generate(inputs, max_new_tokens=4096, eos_token_id=tokenizers.eos_token_id)

        prompt_tokens = len(inputs[0])
        completion_tokens = len(outputs[0]) - prompt_tokens

        generation = tokenizers.decode(outputs[0][prompt_tokens:], skip_special_tokens=True)

        if status == "code1_generate":
            generation = extract_python_code_with_logic(generation)
        # 可以为本地模型添加更多status的处理逻辑

        torch.cuda.empty_cache()
        return generation, prompt_tokens, completion_tokens

    # 如果使用API模型
    else:
        max_retries = 5
        retry_count = 0

        while retry_count < max_retries:
            raw_generation, p_tokens, c_tokens = call_api(prompt=text, model=model_name)

            if raw_generation is not None:
                # 根据status对原始输出进行后处理
                if status in ["code3_generate", "code5_generate"]:
                    processed_generation = extract_python_code(raw_generation)
                    print(f"################# PROCESSED ({status}) #################\n{processed_generation}")
                    return processed_generation, p_tokens, c_tokens

                elif status in ["code4_generate", "code6_generate"]:
                    # 这些状态需要返回原始的、包含分析和代码的文本
                    print(f"################# RAW ({status}) #################\n{raw_generation}")
                    return raw_generation, p_tokens, c_tokens

                else:
                    # 默认行为：返回原始文本
                    return raw_generation, p_tokens, c_tokens

            retry_count += 1
            print(f"API调用失败，正在重试... (尝试 {retry_count}/{max_retries})")
            if retry_count < max_retries:
                time.sleep(5)

        # 所有重试失败
        error_message = f"错误: 在 {max_retries} 次重试后API调用仍然失败 (status: '{status}')."
        print(error_message)
        return error_message, 0, 0