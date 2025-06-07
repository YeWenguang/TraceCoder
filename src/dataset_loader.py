import os
import json
import pandas as pd

def load_dataset(dataset_name: str, dataset_path: str):
    """
    根据数据集名称和路径加载数据集。
    """
    print(f"正在从路径加载数据集 '{dataset_name}': {dataset_path}")
    if not os.path.exists(dataset_path):
        raise FileNotFoundError(f"数据集文件未找到: {dataset_path}")

    if dataset_name == 'bigcodebench':
        return load_parquet_dataset(dataset_path)
    elif dataset_name == 'humaneval':
        # HumanEval通常是一个jsonl文件
        return load_jsonl_dataset(dataset_path)
    # 此处可以添加更多数据集类型的加载逻辑
    else:
        raise ValueError(f"不支持的数据集名称: {dataset_name}")

def load_jsonl_dataset(path):
    datasets_dict = {}
    with open(path, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            data = json.loads(line)
            task_id = data.get('task_id', f"jsonl_task/{i}")
            data['task_id'] = task_id
            # 确保关键字段存在
            data.setdefault('entry_point', data.get('name', f'func_{i}'))
            data.setdefault('prompt', data.get('signature', f"def {data['entry_point']}():\n pass"))
            data.setdefault('test', data.get('tests', "assert True # Dummy test"))
            data.setdefault('complete_prompt', data.get('prompt') + data.get('docstring', ''))
            datasets_dict[task_id] = data
    print(f"已从 {path} 加载 {len(datasets_dict)} 个问题")
    return datasets_dict

def load_parquet_dataset(path):
    datasets_dict = {}
    df = pd.read_parquet(path)
    if 'task_id' not in df.columns:
        df['task_id'] = [f"parquet_task/{i}" for i in range(len(df))]
    for _, row in df.iterrows():
        data = row.to_dict()
        task_id = data['task_id']
        data.setdefault('entry_point', data.get('name', f'func_{task_id.split("/")[-1]}'))
        data.setdefault('test', data.get('tests', "assert True # Dummy test"))
        # BigCodeBench的'prompt'字段通常是完整的提示
        data.setdefault('complete_prompt', data.get('prompt', ''))
        datasets_dict[task_id] = data
    print(f"已从 {path} 加载 {len(datasets_dict)} 个问题")
    return datasets_dict