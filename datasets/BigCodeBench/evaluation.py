import unittest
import io
import sys
import traceback
import types
import os
import shutil
import signal
import tempfile
import builtins # For unsafe_execute's new_module.__dict__
import platform
import faulthandler
import resource
import contextlib
import time # For safe_environment cleanup logic

# --- Constants and Helper from first program ---
TIMEOUT_EXCEPTION_MSG = "Execution timed out!"
DEFAULT_TIMEOUT_SECONDS = 10.0 # Similar to TIMEOUT_LIMIT but for single execution

# --- Context Managers and Guards from bigcodebench.eval.utils ---
# (Slightly adapted or simplified for single-function use)

class TimeoutException(Exception):
    pass

@contextlib.contextmanager
def time_limit(seconds: float):
    def signal_handler(signum, frame):
        raise TimeoutException(TIMEOUT_EXCEPTION_MSG)

    # Set the alarm. In UNIX, this will deliver SIGALRM.
    # In Windows, signal.alarm is not available. This will only work on UNIX-like systems.
    if hasattr(signal, 'SIGALRM'):
        original_handler = signal.getsignal(signal.SIGALRM)
        signal.signal(signal.SIGALRM, signal_handler)
        signal.alarm(int(seconds)) # alarm takes integer seconds
        try:
            yield
        finally:
            signal.alarm(0) # Disable the alarm
            signal.signal(signal.SIGALRM, original_handler) # Restore original handler
    else:
        # No SIGALRM (e.g., on Windows), timeout will not be enforced by this mechanism.
        # Consider this a no-op for timeout on such platforms.
        print("Warning: signal.alarm based time_limit is not available on this platform.", file=sys.stderr)
        yield


@contextlib.contextmanager
def create_tempdir():
    dirname = tempfile.mkdtemp()
    try:
        with chdir(dirname):
            yield dirname
    finally:
        # Ensure cleanup, even if reliability_guard modified shutil.rmtree
        _rmtree = shutil.rmtree
        _rmdir = os.rmdir
        _chdir = os.chdir
        # In case these were changed by reliability_guard, restore them for cleanup
        shutil.rmtree = _rmtree
        os.rmdir = _rmdir
        os.chdir = _chdir
        try:
            shutil.rmtree(dirname)
        except Exception as e:
            print(f"Warning: Could not clean up temp directory {dirname}: {e}", file=sys.stderr)


@contextlib.contextmanager
def chdir(root):
    if root == ".":
        yield
        return
    cwd = os.getcwd()
    os.chdir(root)
    try:
        yield
    except BaseException as exc:
        # Ensure os.chdir(cwd) is called even if an exception occurs
        # but re-raise the original exception.
        os.chdir(cwd)
        raise exc
    os.chdir(cwd)


@contextlib.contextmanager
def swallow_io_and_capture_stderr(stderr_capture_buffer: io.StringIO):
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = io.StringIO() # Swallow stdout
    sys.stderr = stderr_capture_buffer # Capture stderr
    try:
        yield
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr

# Simplified safe_environment: Focus on what's feasible without multiprocessing child tracking
# The original safe_environment is quite complex due to subprocess management.
# For a single-process adaptation, we'll focus on more direct overrides.
@contextlib.contextmanager
def safe_environment_simplified():
    # Save original functions that might be commonly abused
    original_os_kill = os.kill
    original_os_system = os.system
    original_subprocess_call = getattr(subprocess, 'call', None) # Python 2/3
    original_subprocess_run = getattr(subprocess, 'run', None) # Python 3.5+

    def _disabled_function(*args, **kwargs):
        print(f"Warning: Call to a potentially disruptive function ({args[0] if args else 'unknown'}) was intercepted and disabled.", file=sys.stderr)
        # Simulate success or a non-disruptive failure
        if args and isinstance(args[0], (list, tuple)) and 'run' in str(args[0]): # For subprocess.run
             return subprocess.CompletedProcess(args=args, returncode=0)
        return 0

    os.kill = lambda pid, sig: print(f"Intercepted os.kill({pid}, {sig})", file=sys.stderr) if pid != os.getpid() else original_os_kill(pid,sig)
    os.system = _disabled_function
    if original_subprocess_call:
        subprocess.call = _disabled_function
    if original_subprocess_run:
        subprocess.run = _disabled_function
    # Add more overrides as needed (e.g., for file system access outside tempdir, network)

    try:
        yield
    finally:
        # Restore original functions
        os.kill = original_os_kill
        os.system = original_os_system
        if original_subprocess_call:
            subprocess.call = original_subprocess_call
        if original_subprocess_run:
            subprocess.run = original_subprocess_run


def reliability_guard(max_as_limit_mb, max_data_limit_mb, max_stack_limit_mb):
    # Disable functionalities that can make destructive changes to the test.
    # (Adapted from bigcodebench.eval.utils.reliability_guard)
    if hasattr(os, "nice"): # Not available on all platforms (e.g. Windows)
      os.nice(20) # Lower priority

    # Resource limits (won't work on Windows for many limits)
    if hasattr(resource, "setrlimit"):
        try:
            if max_as_limit_mb and max_as_limit_mb > 0:
                resource.setrlimit(resource.RLIMIT_AS, (max_as_limit_mb * 1024 * 1024, max_as_limit_mb * 1024 * 1024))
            if max_data_limit_mb and max_data_limit_mb > 0:
                resource.setrlimit(resource.RLIMIT_DATA, (max_data_limit_mb * 1024 * 1024, max_data_limit_mb * 1024 * 1024))
            if max_stack_limit_mb and max_stack_limit_mb > 0 and not platform.system() == "Darwin": # Stack limit not well supported on Darwin
                resource.setrlimit(resource.RLIMIT_STACK, (max_stack_limit_mb * 1024 * 1024, max_stack_limit_mb * 1024 * 1024))
        except Exception as e:
            print(f"Warning: Failed to set resource limits: {e}", file=sys.stderr)

    if hasattr(faulthandler, 'disable'):
        faulthandler.disable()

    # Override builtins.
    # Be cautious with these, as they might affect legitimate test operations.
    # For this adaptation, we'll be less aggressive than the original.
    # builtins.exit = lambda *args: print("builtins.exit called and intercepted.", file=sys.stderr)
    # builtins.quit = lambda *args: print("builtins.quit called and intercepted.", file=sys.stderr)
    # Disabling open might be too restrictive for many tests.
    # Consider a wrapper that restricts paths if needed.


# --- Helper function to get test IDs from the second program ---
def get_all_test_ids(suite_or_test):
    test_ids = set()
    try:
        for item in suite_or_test:
            test_ids.update(get_all_test_ids(item))
    except TypeError:
        try:
            test_ids.add(suite_or_test.id())
        except AttributeError:
            pass # Not a standard test case or suite
    return test_ids

# --- The main evaluation function ---
def evaluate_generated_code(
    generated_code: str,
    test_code: str,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    max_as_limit_mb: float = 1024, # In MB
    max_data_limit_mb: float = 1024, # In MB
    max_stack_limit_mb: float = 64, # In MB
):
    """
    Evaluates generated Python code against unittest cases with safety features,
    mimicking the output of the second program.
    """
    result_details = {
        'passed': False,
        'passed_count': 0,
        'failed_count': 0,
        'total_tests': 0,
        'passed_tests': [],
        'failed_tests': [],
        'stderr_output': '',
        'execution_error': None
    }
    captured_stderr = io.StringIO()

    # These system calls are needed for create_tempdir cleanup,
    # so store them before safe_environment_simplified might alter them.
    _shutil_rmtree = shutil.rmtree
    _os_rmdir = os.rmdir
    _os_chdir = os.chdir

    try:
        # Apply context managers: safety, temp dir, I/O capture, time limit
        with safe_environment_simplified(), \
             create_tempdir(), \
             swallow_io_and_capture_stderr(captured_stderr), \
             time_limit(timeout_seconds):

            # Apply reliability guards (resource limits, etc.)
            reliability_guard(max_as_limit_mb, max_data_limit_mb, max_stack_limit_mb)

            # --- Core execution logic (adapted from unsafe_execute) ---
            module_name = "__bigcodebench_test_module__"
            # Create a new module object
            # exec_namespace will hold the executed code's definitions
            exec_namespace = types.ModuleType(module_name).__dict__
            exec_namespace.update({
                '__builtins__': builtins,
                '__file__': f"{module_name}.py", # Fake file path
                '__package__': None,
                '__doc__': None,
                # Make common modules available if tests/code expect them implicitly
                'sys': sys,
                'os': os,
                'unittest': unittest,
                'datetime': __import__('datetime'), # Make datetime available
                'logging': __import__('logging'),   # Make logging available
            })

            full_code_to_run = generated_code + "\n\n" + test_code

            # Compile and execute the combined code in the new module's namespace
            compiled_code = compile(full_code_to_run, f"{module_name}.py", 'exec')
            exec(compiled_code, exec_namespace, exec_namespace)

            # Discover and run tests (similar to the second program)
            loader = unittest.TestLoader()
            suite = unittest.TestSuite()
            test_case_classes_found = []

            for name, obj in exec_namespace.items():
                if isinstance(obj, type) and issubclass(obj, unittest.TestCase) and obj is not unittest.TestCase:
                    test_case_classes_found.append(obj)

            if not test_case_classes_found:
                result_details['execution_error'] = "No unittest.TestCase classes were found or defined in the executed code."
                result_details['stderr_output'] = captured_stderr.getvalue()
                # Restore shutil and os for tempdir cleanup if error occurs here
                shutil.rmtree, os.rmdir, os.chdir = _shutil_rmtree, _os_rmdir, _os_chdir
                return result_details

            for test_case_class in test_case_classes_found:
                tests = loader.loadTestsFromTestCase(test_case_class)
                suite.addTests(tests)

            result_details['total_tests'] = suite.countTestCases()

            if result_details['total_tests'] == 0:
                result_details['execution_error'] = "Test suite was created but contained no tests."
                result_details['stderr_output'] = captured_stderr.getvalue()
                shutil.rmtree, os.rmdir, os.chdir = _shutil_rmtree, _os_rmdir, _os_chdir
                return result_details

            all_test_ids = get_all_test_ids(suite)

            # Use unittest.TestResult directly for more detailed control
            test_run_result = unittest.TestResult()
            suite.run(test_run_result)

            # Process results
            result_details['passed'] = test_run_result.wasSuccessful()
            failures_and_errors = test_run_result.failures + test_run_result.errors
            result_details['failed_count'] = len(failures_and_errors)
            result_details['passed_count'] = result_details['total_tests'] - result_details['failed_count']

            failed_test_details = []
            failed_test_ids = set()
            for test, err_traceback in test_run_result.failures:
                test_id = test.id()
                failed_test_details.append({'name': test_id, 'type': 'Failure', 'details': err_traceback})
                failed_test_ids.add(test_id)
            for test, err_traceback in test_run_result.errors:
                test_id = test.id()
                failed_test_details.append({'name': test_id, 'type': 'Error', 'details': err_traceback})
                failed_test_ids.add(test_id)

            result_details['failed_tests'] = failed_test_details
            result_details['passed_tests'] = sorted(list(all_test_ids - failed_test_ids))

    except TimeoutException:
        result_details['passed'] = False
        result_details['execution_error'] = TIMEOUT_EXCEPTION_MSG
        # In a timeout, assume all tests that didn't complete are not passed.
        # Depending on when timeout occurred, partial results might be in test_run_result.
        # For simplicity, if a timeout occurs, we mark the overall as not passed.
        # If result_details['total_tests'] was set, failed_count might be total_tests.
        if result_details['total_tests'] > 0 and result_details['passed_count'] + result_details['failed_count'] < result_details['total_tests'] :
             result_details['failed_count'] = result_details['total_tests'] - result_details['passed_count']

    except Exception: # Catch any other exceptions during setup or execution
        error_type, error_value, tb = sys.exc_info()
        error_details_str = "".join(traceback.format_exception(error_type, error_value, tb))
        result_details['passed'] = False
        result_details['execution_error'] = f"An unexpected exception occurred:\n{error_details_str}"
    finally:
        result_details['stderr_output'] = captured_stderr.getvalue() + result_details.get('stderr_output', '') # Append if already set
        # Restore shutil and os for tempdir cleanup, especially if safe_environment changed them
        shutil.rmtree, os.rmdir, os.chdir = _shutil_rmtree, _os_rmdir, _os_chdir


    return result_details
