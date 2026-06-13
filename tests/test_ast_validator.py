"""Unit tests for ASTValidator — forbidden construct detection"""
import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.sandbox.ast_validator import ASTValidator, ASTValidationError


class TestASTValidator(unittest.TestCase):
    """Tests that ASTValidator correctly blocks dangerous constructs."""

    def setUp(self):
        self.validator = ASTValidator()

    # ---- Allowed constructs ----

    def test_valid_simple_script(self):
        """A typical graph-build script should pass."""
        code = """
g = Graph(plugin="amazon")
products = g.keyword_search(keyword="test")
analysis = g.market_analysis(products=products)
g.output(analysis)
result = g.execute()
"""
        errors = self.validator.validate(code)
        self.assertEqual(errors, [], f"Expected no errors, got: {errors}")

    def test_list_comprehension(self):
        """List comprehensions should be allowed."""
        code = "x = [i * 2 for i in range(10)]"
        errors = self.validator.validate(code)
        self.assertEqual(errors, [])

    def test_dict_literal(self):
        """Dict literals should be allowed."""
        code = 'd = {"key": "value", "num": 42}'
        errors = self.validator.validate(code)
        self.assertEqual(errors, [])

    def test_if_else(self):
        """Basic control flow should be allowed."""
        code = """
x = 10
if x > 5:
    y = 1
else:
    y = 0
"""
        errors = self.validator.validate(code)
        self.assertEqual(errors, [])

    # ---- Blocked constructs ----

    def test_import_blocked(self):
        """'import os' should be rejected."""
        code = "import os"
        errors = self.validator.validate(code)
        self.assertTrue(len(errors) > 0)
        self.assertIn("import", errors[0]["message"].lower())

    def test_import_from_blocked(self):
        """'from os import path' should be rejected."""
        code = "from os import path"
        errors = self.validator.validate(code)
        self.assertTrue(len(errors) > 0)
        self.assertIn("import", errors[0]["message"].lower())

    def test_eval_blocked(self):
        """Direct call to eval() should be rejected."""
        code = "eval('1+1')"
        errors = self.validator.validate(code)
        self.assertTrue(len(errors) > 0)
        self.assertIn("eval", errors[0]["message"])

    def test_exec_blocked(self):
        """Direct call to exec() should be rejected."""
        code = "exec('x=1')"
        errors = self.validator.validate(code)
        self.assertTrue(len(errors) > 0)
        self.assertIn("exec", errors[0]["message"])

    def test_open_blocked(self):
        """Direct call to open() should be rejected."""
        code = "open('/etc/passwd')"
        errors = self.validator.validate(code)
        self.assertTrue(len(errors) > 0)
        self.assertIn("open", errors[0]["message"])

    def test_getattr_blocked(self):
        """Direct call to getattr() should be rejected."""
        code = "getattr(obj, '__class__')"
        errors = self.validator.validate(code)
        self.assertTrue(len(errors) > 0)
        self.assertIn("getattr", errors[0]["message"])

    def test_dunder_attr_blocked(self):
        """Access to __class__ should be rejected."""
        code = "x = obj.__class__"
        errors = self.validator.validate(code)
        self.assertTrue(len(errors) > 0)
        self.assertIn("__class__", errors[0]["message"])

    def test_dunder_subscript_blocked(self):
        """Subscript access with '__class__' key should be rejected."""
        code = "x = obj['__class__']"
        errors = self.validator.validate(code)
        self.assertTrue(len(errors) > 0)
        self.assertIn("__class__", errors[0]["message"])

    def test_long_string_literal_blocked(self):
        """String literal > 10000 chars should be rejected."""
        code = 'x = "' + 'A' * 10001 + '"'
        errors = self.validator.validate(code)
        self.assertTrue(len(errors) > 0)
        self.assertIn("too long", errors[0]["message"].lower())

    # ---- validate_or_raise ----

    def test_validate_or_raise_valid(self):
        """validate_or_raise should not raise for valid code."""
        try:
            self.validator.validate_or_raise("x = 42")
        except ASTValidationError:
            self.fail("validate_or_raise raised for valid code")

    def test_validate_or_raise_invalid(self):
        """validate_or_raise should raise ASTValidationError for invalid code."""
        with self.assertRaises(ASTValidationError):
            self.validator.validate_or_raise("import os")


if __name__ == "__main__":
    unittest.main()
