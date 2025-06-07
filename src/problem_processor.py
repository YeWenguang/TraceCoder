import importlib.util
import os
import sys
import traceback

# Adjusting sys.path to correctly import config from the parent directory
current_script_path = os.path.abspath(__file__)
src_dir = os.path.dirname(current_script_path)
project_root = os.path.dirname(src_dir)  # This should be TraceLearnCoder
sys.path.insert(0, project_root) # Insert at the beginning to prioritize project's config

try:
    from config import DATASET_PATHS, TIMEOUT_SECONDS
except ImportError:
    print("Error: Could not import from config.py. Ensure it's in the project root (e.g., d:\\codellama-main\\evaluate-repair\\TraceLearnCoder)")
    print(f"Current sys.path: {sys.path}")
    print(f"Attempted project_root: {project_root}")
    # Provide default values or raise an error if config is critical
    DATASET_PATHS = {
        "human_eval": "./datasets/human_eval/human_eval_problems.jsonl",
        "BigCodeBench": "./datasets/BigCodeBench/BigCodeBench.jsonl",
        "ClassEval": "./datasets/ClassEval/ClassEval_problems.jsonl",
    }
    TIMEOUT_SECONDS = 10  # Default timeout in seconds
    print("Warning: Using default DATASET_PATHS and TIMEOUT_SECONDS due to import error.")

# Define a mapping from dataset_name to its evaluation script relative path and function name
# Paths are relative to the 'datasets' directory within the project_root
EVALUATION_SCRIPTS = {
    "human_eval": {
        "script_subpath": "human_eval/execution.py",
        "function_name": "check_correctness"
    },
    "BigCodeBench": {
        "script_subpath": "BigCodeBench/evaluation.py",
        "function_name": "evaluate_generated_code"
    },
    "ClassEval": {
        "script_subpath": "ClassEval/evaluation.py",
        "function_name": "check_correctness"
    }
    # Add other datasets here with their respective script subpaths and function names
}

def dynamically_load_evaluation_function(dataset_name: str):
    """
    Dynamically loads the evaluation function for a given dataset.
    Assumes evaluation scripts are located in subdirectories under a 'datasets' folder 
    at the project root.
    """
    if dataset_name not in EVALUATION_SCRIPTS:
        raise ValueError(f"Evaluation script configuration not found for dataset: {dataset_name}")

    script_config = EVALUATION_SCRIPTS[dataset_name]
    script_subpath = script_config["script_subpath"]
    function_name = script_config["function_name"]

    # Construct the absolute path to the evaluation script
    # e.g., d:\codellama-main\evaluate-repair\TraceLearnCoder\datasets\human_eval\execution.py
    datasets_dir = os.path.join(project_root, "datasets")
    script_full_path = os.path.join(datasets_dir, script_subpath)

    if not os.path.exists(script_full_path):
        raise FileNotFoundError(f"Evaluation script not found at: {script_full_path}")

    # Create a unique module name for importlib, e.g., TraceLearnCoder.datasets.human_eval.execution
    module_name_parts = os.path.normpath(script_subpath).split(os.sep)
    module_name = f"TraceLearnCoder.datasets.{'.'.join(module_name_parts).replace('.py', '')}"

    try:
        spec = importlib.util.spec_from_file_location(module_name, script_full_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not create module spec for {module_name} from {script_full_path}")
        
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module  # Crucial: Add to sys.modules BEFORE exec_module
        spec.loader.exec_module(module)
        
        eval_function = getattr(module, function_name)
        return eval_function
    except Exception as e:
        tb_str = traceback.format_exc()
        raise ImportError(f"Failed to load evaluation function '{function_name}' from '{script_full_path}': {e}\n{tb_str}")

def process_and_evaluate_problem(dataset_name: str, problem_data: dict, generated_code: str, timeout: int = None):
    """
    Processes a problem: loads the appropriate evaluation function and runs it.
    Adapts the call to the evaluation function based on the dataset's specific signature.
    """
    if timeout is None:
        timeout = TIMEOUT_SECONDS

    try:
        eval_function = dynamically_load_evaluation_function(dataset_name)
    except (ValueError, FileNotFoundError, ImportError) as e:
        print(f"Error loading evaluation function for {dataset_name}: {e}")
        return {"passed": False, "result": str(e), "error_type": "loading_error"}

    try:
        if dataset_name == "human_eval":
            # Expected signature: check_correctness(problem: Dict, completion: str, timeout: float, completion_id: Optional[int] = None)
            return eval_function(problem=problem_data, completion=generated_code, timeout=float(timeout))
        elif dataset_name == "BigCodeBench":
            # Expected signature: evaluate_generated_code(generated_code: str, test_code: str, timeout_seconds: float, ...)
            test_code = problem_data.get("test") # Assuming 'test' key holds the test code string
            if test_code is None:
                return {"passed": False, "result": "'test' code not found in problem_data for BigCodeBench", "error_type": "missing_data"}
            return eval_function(generated_code=generated_code, test_code=test_code, timeout_seconds=float(timeout))
        elif dataset_name == "ClassEval":
            # Expected signature: check_correctness(dataset, generated_code, timeout_seconds=10)
            # Here 'dataset' is the problem_data dictionary itself.
            return eval_function(dataset=problem_data, generated_code=generated_code, timeout_seconds=float(timeout))
        else:
            return {"passed": False, "result": f"Evaluation logic for dataset '{dataset_name}' is not specifically implemented in the processor.", "error_type": "not_implemented"}

    except Exception as e:
        tb_str = traceback.format_exc()
        print(f"Error during evaluation of {dataset_name} problem {problem_data.get('task_id', 'N/A')}: {e}\n{tb_str}")
        return {"passed": False, "result": str(e), "error_type": "runtime_error", "traceback": tb_str}

if __name__ == '__main__':
    print(f"Problem Processor - Example Usage (Project Root: {project_root})")

    # Mock problem data and generated code for testing
    # These examples assume the evaluation scripts exist at the configured paths.

    sample_human_eval_problem = {
        "task_id": "HumanEval/0",
        "prompt": "def add(a, b):\n    \"\"\"Return the sum of two numbers.\"\"\"\n",
        "entry_point": "add",
        "test": "\n\nMETADATA = {\n    'author': 'example',\n    'dataset': 'example'\n}\n\n\ndef check(candidate):\n    assert candidate(1, 2) == 3\n    assert candidate(-1, 1) == 0\n"
    }
    sample_human_eval_code_pass = "    return a + b"
    sample_human_eval_code_fail = "    return a - b"

    sample_bigcode_problem = {
        "task_id": "BigCodeBench/example_id",
        "prompt": "def get_greeting(name):\n    pass\n",
        "test": "import unittest\nclass TestGreeting(unittest.TestCase):\n    def test_world(self):\n        self.assertEqual(get_greeting(\"World\"), \"Hello, World!\")\n    def test_empty(self):\n        self.assertEqual(get_greeting(\"\"), \"Hello, !\")\nif __name__ == '__main__': unittest.main()",
        "entry_point": "get_greeting"
    }
    sample_bigcode_code_pass = "    return f\"Hello, {name}!\""
    sample_bigcode_code_fail = "    return f\"Hi, {name}\""

    sample_classeval_problem = {
        "task_id": "ClassEval/example_id",
        "prompt": "class Counter:\n  def __init__(self):\n    self.count = 0\n  def increment(self):\n    pass\n  def get_count(self):\n    pass",
        "test": "import unittest\nclass TestCounter(unittest.TestCase):\n  def test_initial(self):\n    c = Counter()\n    self.assertEqual(c.get_count(), 0)\n  def test_increment(self):\n    c = Counter()\n    c.increment()\n    self.assertEqual(c.get_count(), 1)\n    c.increment()\n    self.assertEqual(c.get_count(), 2)\nif __name__ == '__main__': unittest.main()",
        "entry_point": "Counter"
    }
    sample_classeval_code_pass = "  def increment(self):\n    self.count += 1\n  def get_count(self):\n    return self.count"
    # For ClassEval, generated code is often a snippet to be inserted or the full class if simple.
    # Assuming generated_code here completes the class methods for simplicity of example.
    full_classeval_code_pass = f"{sample_classeval_problem['prompt'].replace('pass', sample_classeval_code_pass, 2)}"


    print("\n--- Testing HumanEval ---")
    if "human_eval" in EVALUATION_SCRIPTS:
        result_pass = process_and_evaluate_problem("human_eval", sample_human_eval_problem, sample_human_eval_code_pass)
        print(f"HumanEval (Pass) Result: {result_pass}")
        result_fail = process_and_evaluate_problem("human_eval", sample_human_eval_problem, sample_human_eval_code_fail)
        print(f"HumanEval (Fail) Result: {result_fail}")
    else:
        print("HumanEval not configured in EVALUATION_SCRIPTS.")

    print("\n--- Testing BigCodeBench ---")
    if "BigCodeBench" in EVALUATION_SCRIPTS:
        result_pass_bcb = process_and_evaluate_problem("BigCodeBench", sample_bigcode_problem, sample_bigcode_code_pass)
        print(f"BigCodeBench (Pass) Result: {result_pass_bcb}")
        result_fail_bcb = process_and_evaluate_problem("BigCodeBench", sample_bigcode_problem, sample_bigcode_code_fail)
        print(f"BigCodeBench (Fail) Result: {result_fail_bcb}")
    else:
        print("BigCodeBench not configured in EVALUATION_SCRIPTS.")

    print("\n--- Testing ClassEval ---")
    if "ClassEval" in EVALUATION_SCRIPTS:
        # For ClassEval, the generated code might be the full class or parts of it.
        # The sample_classeval_problem['prompt'] provides the class structure.
        # The check_correctness in ClassEval's evaluation.py expects the full code.
        result_pass_ce = process_and_evaluate_problem("ClassEval", sample_classeval_problem, full_classeval_code_pass)
        print(f"ClassEval (Pass) Result: {result_pass_ce}")
        # Example for fail (assuming generated code leads to incorrect behavior)
        bad_classeval_code = f"{sample_classeval_problem['prompt'].replace('pass', 'self.count += 2\n  def get_count(self):\n    return 0', 2)}"
        result_fail_ce = process_and_evaluate_problem("ClassEval", sample_classeval_problem, bad_classeval_code)
        print(f"ClassEval (Fail) Result: {result_fail_ce}")
    else:
        print("ClassEval not configured in EVALUATION_SCRIPTS.")

    print("\n--- Testing NonExistentDataset ---")
    result_non_existent = process_and_evaluate_problem("NonExistentDataset", {}, "")
    print(f"NonExistentDataset Result: {result_non_existent}")

    # Test case for config import failure (if you temporarily rename config.py)
    # print("\n--- Testing config import failure scenario (requires manual config.py rename) ---")
    # You would need to simulate the ImportError for this to show the warning.