import unittest
from app.interpreter import execute


def I(op, text, line=1, **f):
    return {"op": op, "text": text, "line": line, "col": 1, **f}


class InterpreterTests(unittest.TestCase):
    def test_print_and_arithmetic(self):
        r = execute([I("assign", "x = 3", result="x", arg1="3"),
                     I("binop", "y = x * 4", result="y", arg1="x", operator="*", arg2="4"),
                     I("print", "print y", arg1="y")])
        self.assertTrue(r["ok"])
        self.assertEqual(r["output"], ["12"])

    def test_number_formatting(self):
        r = execute([I("binop", "a = 10 / 4", result="a", arg1="10", operator="/", arg2="4"),
                     I("binop", "b = 10 / 5", result="b", arg1="10", operator="/", arg2="5"),
                     I("binop", "c = 0.1 + 0.2", result="c", arg1="0.1", operator="+", arg2="0.2"),
                     I("print", "", arg1="a"), I("print", "", arg1="b"), I("print", "", arg1="c")])
        self.assertEqual(r["output"], ["2.5", "2", "0.3"])

    def test_string_concat_and_compare(self):
        r = execute([I("binop", "", result="s", arg1='"a"', operator="+", arg2='"b"'),
                     I("binop", "", result="t", arg1="s", operator="==", arg2='"ab"'),
                     I("print", "", arg1="s"), I("print", "", arg1="t")])
        self.assertEqual(r["output"], ["ab", "1"])

    def test_division_by_zero_reports_line(self):
        r = execute([I("assign", "", line=1, result="z", arg1="0"),
                     I("binop", "", line=2, result="q", arg1="1", operator="/", arg2="z")])
        self.assertFalse(r["ok"])
        self.assertEqual((r["errors"][0]["message"], r["errors"][0]["line"]), ("Division by zero", 2))

    def test_infinite_loop_is_stopped(self):
        r = execute([I("label", "L1:", label="L1"), I("goto", "goto L1", target="L1")], max_steps=100)
        self.assertFalse(r["ok"])
        self.assertIn("infinite loop", r["errors"][0]["message"])

    def test_output_kept_before_error(self):
        r = execute([I("print", "", arg1="1"),
                     I("binop", "", result="q", arg1="1", operator="/", arg2="0")])
        self.assertEqual(r["output"], ["1"])
        self.assertFalse(r["ok"])

    def test_missing_value(self):
        self.assertFalse(execute([I("print", "", arg1="nope")])["ok"])


if __name__ == "__main__":
    unittest.main()
