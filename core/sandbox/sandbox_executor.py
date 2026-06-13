"""Sandbox: executor — restricted Python script execution engine

Pipeline:
  1. AST validation (syntax-level safety)
  2. exec() with restricted __builtins__ (capability-level safety)
  3. Timeout via watchdog thread (_thread.interrupt_main)
  4. Extract and return result from g.execute()

The Agent's script is restricted: no imports, no file I/O, no dangerous
builtins.  The SDK (Graph class) runs unrestricted — it has full access
to NodeRegistry, GraphValidator, and GraphExecutor.
"""

import sys
import threading
import _thread as _thread_module
from typing import Any

from .ast_validator import ASTValidator, ASTValidationError
from core.exceptions import GatewayException, InvalidGraphError
from core.registry.node_registry import get_registry
from core.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Restricted builtins — the ONLY builtins available in Agent scripts
# ---------------------------------------------------------------------------

RESTRICTED_BUILTINS: dict[str, Any] = {
    # Constants
    "True": True,
    "False": False,
    "None": None,
    # Basic types
    "int": int,
    "float": float,
    "str": str,
    "bool": bool,
    "list": list,
    "dict": dict,
    "tuple": tuple,
    "set": set,
    # Sequence / iteration
    "len": len,
    "range": range,
    "enumerate": enumerate,
    "zip": zip,
    "map": map,
    "filter": filter,
    "reversed": reversed,
    "sorted": sorted,
    # Math
    "min": min,
    "max": max,
    "sum": sum,
    "abs": abs,
    "round": round,
    "pow": pow,
    # Output for debugging (stdout is captured by the gateway)
    "print": print,
    # String representation
    "repr": repr,
    "format": format,
    # Basic exception types (for graceful error handling patterns)
    "Exception": Exception,
    "ValueError": ValueError,
    "TypeError": TypeError,
    "KeyError": KeyError,
    "IndexError": IndexError,
    "AttributeError": AttributeError,
    "RuntimeError": RuntimeError,
}

# Explicitly NOT included (the dangerous ones):
#   type, isinstance, issubclass, getattr, setattr, delattr,
#   hasattr, vars, dir, object, super,
#   eval, exec, compile, __import__, open, input, breakpoint,
#   globals, locals, memoryview, bytearray, classmethod, staticmethod,
#   property, slice, iter, next, ord, chr, hex, oct, bin, id, hash,
#   all, any, callable, complex, divmod, ascii

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

# Default script execution timeout (seconds)
DEFAULT_TIMEOUT = 10

# Maximum allowed script length (bytes)
MAX_SCRIPT_SIZE = 100 * 1024  # 100 KB


class SandboxTimeoutError(Exception):
    """Raised when script execution exceeds the time limit."""
    pass


def execute_script(
    script: str,
    timeout: float = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """Execute a Python script in a restricted sandbox.

    Args:
        script: The Python script text submitted by the Agent.
        timeout: Maximum execution time in seconds.

    Returns:
        The result dict from g.execute().

    Raises:
        ASTValidationError: AST contains forbidden constructs.
        SandboxTimeoutError: Execution exceeded the time limit.
        InvalidGraphError: Graph validation failed.
        GatewayException: Other gateway-level errors.
    """
    # Guard: script size
    if len(script.encode("utf-8", errors="replace")) > MAX_SCRIPT_SIZE:
        raise ASTValidationError(
            f"Script too large ({len(script)} bytes, max {MAX_SCRIPT_SIZE})"
        )

    # Guard: empty script
    stripped = script.strip()
    if not stripped:
        raise ASTValidationError("Script is empty")

    # ---- Step 1: AST validation ----
    validator = ASTValidator()
    errors = validator.validate(stripped)
    if errors:
        # Raise with first error
        err = errors[0]
        raise ASTValidationError(
            err.get("message", str(err)),
            lineno=err.get("lineno"),
        )

    # ---- Step 2: Compile ----
    try:
        compiled = compile(stripped, "<agent_script>", "exec")
    except SyntaxError as e:
        raise ASTValidationError(str(e), lineno=e.lineno)

    # ---- Step 3: Build restricted execution namespace ----
    # The SDK's Graph class is injected into the namespace.
    # All other builtins are from RESTRICTED_BUILTINS.
    from gateway_sdk import Graph

    exec_globals: dict[str, Any] = {
        "__builtins__": RESTRICTED_BUILTINS,
        "Graph": Graph,
    }
    exec_locals: dict[str, Any] = {}

    # ---- Step 4: Execute with timeout ----
    # On Windows, signal.alarm() is unavailable.  We use a watchdog thread
    # that calls _thread.interrupt_main() to raise KeyboardInterrupt in the
    # main thread.
    #
    # Race-free design:
    #   executing flag is SET before watchdog starts waiting.
    #   If script finishes quickly → executing.clear() fires → watchdog
    #     wait() returns True immediately → no interrupt.
    #   If script still running → wait() times out → returns False →
    #     watchdog fires interrupt_main().

    executing = threading.Event()
    executing.set()  # MUST be set before watchdog starts

    def _watchdog():
        # executing.wait(timeout) returns:
        #   True  → flag was set (script finished), exit silently
        #   False → timeout elapsed (script still running), fire interrupt
        if not executing.wait(timeout):
            try:
                _thread_module.interrupt_main()
            except Exception:
                pass

    timer = threading.Thread(target=_watchdog, daemon=True)
    timer.start()

    try:
        exec(compiled, exec_globals, exec_locals)
    except KeyboardInterrupt:
        if not executing.is_set():
            raise SandboxTimeoutError(
                f"Script execution timed out after {timeout:.0f}s"
            )
        # Otherwise, genuine KeyboardInterrupt — re-raise
        raise KeyboardInterrupt("Script interrupted")
    finally:
        executing.clear()           # signal watchdog: script finished
        timer.join(timeout=2)       # wait for watchdog to exit

    # ---- Step 5: Extract result ----
    # The Agent's script must bind the result of g.execute() to a variable.
    # Convention: result = g.execute()
    result = exec_locals.get("result")
    if result is None:
        raise ASTValidationError(
            "Script must assign g.execute() result. "
            "Expected pattern:\n"
            "    g = Graph(plugin='amazon')\n"
            "    products = g.keyword_search(keyword='test')\n"
            "    g.output(products)\n"
            "    result = g.execute()"
        )

    return result
