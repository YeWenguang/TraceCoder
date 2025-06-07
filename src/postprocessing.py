import re
from typing import List

# 注意：原文件中的 os 和 csv 导入未使用，但为保持一致性可保留或移除。

def remove_code_block_markers(code: str) -> str:
    """
    去除代码字符串中可能残留的 ```python 和 ``` 标记。
    """
    code = re.sub(r'^\s*```(python|py|python3)?\s*', '', code, flags=re.IGNORECASE)
    code = re.sub(r'\s*```\s*$', '', code, flags=re.IGNORECASE)
    return code.strip()

def remove_main_block(code_string: str) -> str:
    """
    去除Python代码字符串中的 `if __name__ == "__main__":` 代码块及其内容。
    """
    main_block_match = re.search(r"if\s+__name__\s*==\s*['\"]__main__['\"]:", code_string, re.MULTILINE)
    if main_block_match:
        return code_string[:main_block_match.start()].rstrip()
    return code_string

def remove_test_section(input_str: str) -> str:
    """
    删除字符串中以 # Test 或 # test 开头的行及其后的所有内容
    """
    match = re.search(r"^#\s*(test|example).*$", input_str, re.IGNORECASE | re.MULTILINE)
    if match:
        return input_str[:match.start()].rstrip()
    return input_str

def remove_after_last_return(code: str) -> str:
    """
    删除给定代码中最后一个 'return' 语句之后的所有内容。
    """
    pattern = r'(.*)(return[\s\S]*)'
    match = re.search(pattern, code, re.DOTALL)
    if match:
        return match.group(1) + match.group(2).split('\n')[0]
    return code

def remove_main_function_cpp(cpp_code: str) -> str:
    pattern = r"int\s+main\s?\(.*?\)\s?\{.*\}"
    cleaned_code = re.sub(pattern, "", cpp_code, flags=re.DOTALL)
    return cleaned_code.strip()

def remove_main_function_go(go_code: str) -> str:
    go_code_no_main = re.sub(r'func main\([^\)]*\)\s*\{.*\}', '', go_code, flags=re.DOTALL)
    return go_code_no_main.strip()

def remove_main_function_java(java_code: str) -> str:
    pattern = r"public\s+static\s+void\s+main\s*\(.*\)\s*\{[\s\S]*"
    cleaned_code = re.sub(pattern, "", java_code, flags=re.DOTALL)
    return cleaned_code.strip()

def extract_python_code(text: str) -> str:
    """
    从文本中提取代码块，并根据语言类型处理。
    优先提取最后一个包含函数或类定义的Python代码块。
    """
    pattern = r"```(\w+)\s*?([\s\S]*?)```"
    matches = re.finditer(pattern, text, re.IGNORECASE)
    all_code_blocks = [(m.group(1).lower(), m.group(2).strip()) for m in matches]

    if not all_code_blocks:
        return text

    last_suitable_python_block_content = None
    for lang, block_content in reversed(all_code_blocks):
        if lang in {'python', 'py', 'python3'}:
            if re.search(r"\b(def|class)\s+[\w_]+\s*[:\(]", block_content):
                last_suitable_python_block_content = block_content
                break

    if last_suitable_python_block_content:
        processed = remove_test_section(last_suitable_python_block_content)
        processed = remove_main_block(processed)
        processed = remove_code_block_markers(processed)
        return processed.strip()
    else:
        lang_last, content_last = all_code_blocks[-1]
        if lang_last in {'python', 'py', 'python3'}:
            return text
        elif lang_last in {'cpp', 'c++', 'c'}:
            return remove_main_function_cpp(content_last)
        elif lang_last == 'go':
            return remove_main_function_go(content_last)
        elif lang_last == 'java':
            return remove_main_function_java(content_last)
        else:
            return content_last