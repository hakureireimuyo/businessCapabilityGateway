"""Sandbox: AST validator — pre-execution safety check

Parses the Agent's Python script into an AST and walks every node,
rejecting dangerous constructs before any code executes.

Blocked constructs:
  - import / import from statements (no module loading)
  - Attribute access to __dunder__ names (no escape via introspection)
  - Attribute access on __class__, __bases__, __mro__, __subclasses__
  - Calls to eval, exec, compile, open, __import__, getattr, setattr,
    delattr, globals, locals, vars
  - Subscript access on __class__, __bases__, __mro__

This is NOT a complete sandbox on its own — it is one layer combined
with restricted __builtins__ in the execution namespace.
"""

import ast
from typing import Any


# Names forbidden as direct function calls
FORBIDDEN_CALLS = frozenset({
    "eval", "exec", "compile", "open", "__import__",
    "getattr", "setattr", "delattr",
    "globals", "locals", "vars",
    "breakpoint", "input",
})

# Dunder attributes that enable MRO/sandbox escapes
FORBIDDEN_DUNDER_ATTRS = frozenset({
    "__class__", "__bases__", "__mro__", "__subclasses__",
    "__globals__", "__code__", "__func__", "__self__",
    "__builtins__", "__import__",
    "__reduce__", "__reduce_ex__",  # pickle escape
    "__init_subclass__", "__init__",
})

# Dunder subscript targets (e.g., obj["__class__"])
FORBIDDEN_DUNDER_SUBSCRIPTS = frozenset({
    "__class__", "__bases__", "__mro__", "__subclasses__",
    "__globals__", "__builtins__",
})


class ASTValidationError(Exception):
    """Raised when the AST contains forbidden constructs."""

    def __init__(self, message: str, lineno: int | None = None):
        self.lineno = lineno
        loc = f" (line {lineno})" if lineno else ""
        super().__init__(f"{message}{loc}")


class ASTValidator(ast.NodeVisitor):
    """Walk the AST and reject dangerous constructs."""

    def __init__(self):
        self.errors: list[dict[str, Any]] = []

    def validate(self, code: str) -> list[dict[str, Any]]:
        """Parse and validate code. Returns list of error dicts (empty = valid)."""
        self.errors = []
        try:
            tree = ast.parse(code, mode="exec")
        except SyntaxError as e:
            self.errors.append({
                "layer": "SYNTAX_ERROR",
                "message": str(e),
                "lineno": e.lineno,
            })
            return self.errors
        self.visit(tree)
        return self.errors

    def validate_or_raise(self, code: str) -> None:
        """Validate code. Raises ASTValidationError on first error."""
        errors = self.validate(code)
        if errors:
            err = errors[0]
            raise ASTValidationError(
                err.get("message", str(err)),
                lineno=err.get("lineno"),
            )

    def _add_error(self, msg: str, lineno: int | None = None) -> None:
        self.errors.append({
            "layer": "INVALID_SCRIPT",
            "message": msg,
            "lineno": lineno,
        })

    # ---------- statements ----------

    def visit_Import(self, node: ast.Import) -> None:
        names = ", ".join(a.name for a in node.names)
        self._add_error(
            f"Import statements are not allowed: 'import {names}'",
            lineno=node.lineno,
        )

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        names = ", ".join(a.name for a in node.names)
        module = node.module or "?"
        self._add_error(
            f"Import statements are not allowed: 'from {module} import {names}'",
            lineno=node.lineno,
        )

    # ---------- expressions ----------

    def visit_Call(self, node: ast.Call) -> None:
        # Check for direct calls to forbidden names: eval(), exec(), etc.
        if isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_CALLS:
            self._add_error(
                f"Call to '{node.func.id}' is not allowed",
                lineno=node.lineno,
            )
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        # Check: obj.__dangerous__
        if node.attr in FORBIDDEN_DUNDER_ATTRS:
            self._add_error(
                f"Access to '{node.attr}' is not allowed",
                lineno=node.lineno,
            )
        # Check: obj.attr.startswith("__") (any dunder)
        elif node.attr.startswith("__") and node.attr.endswith("__"):
            self._add_error(
                f"Access to dunder attribute '{node.attr}' is not allowed",
                lineno=node.lineno,
            )
        self.generic_visit(node)

    def visit_Subscript(self, node: ast.Subscript) -> None:
        # Check: obj["__class__"] or obj[constant_dangerous_key]
        if isinstance(node.slice, ast.Constant):
            key = node.slice.value
            if isinstance(key, str) and key in FORBIDDEN_DUNDER_SUBSCRIPTS:
                self._add_error(
                    f"Subscript access with key '{key}' is not allowed",
                    lineno=node.lineno,
                )
        self.generic_visit(node)

    def visit_Constant(self, node: ast.Constant) -> None:
        # Block extremely long strings (potential code smuggling)
        if isinstance(node.value, str) and len(node.value) > 10000:
            self._add_error(
                f"String literal too long ({len(node.value)} chars)",
                lineno=node.lineno,
            )
