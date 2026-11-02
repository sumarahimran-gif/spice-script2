import unittest
from app.lexer import lex
from app.parser import parse
from app.semantic import analyze
from app.grammar import SAMPLES


def run(src):
    r = parse(lex(src)["tokens"])
    assert r["ok"], r["errors"]
    return analyze(r["ast"])


def msgs(src):
    return [e["message"] for e in run(src)["errors"]]


class SemanticTests(unittest.TestCase):
    def test_valid_samples(self):
        for name in ("Arithmetic", "If / else", "Loop"):
            code = next(s["code"] for s in SAMPLES if s["name"] == name)
            self.assertTrue(run(code)["ok"], name)

    def test_symbol_table(self):
        r = run('mix x into 3\nmix s into "hi"\nserve x\nx into x plus 1\nplate')
        st = {s["name"]: s for s in r["symbol_table"]}
        self.assertEqual((st["x"]["type"], st["s"]["type"]), ("number", "string"))
        self.assertEqual((st["x"]["reads"], st["x"]["writes"]), (2, 2))
        self.assertEqual(st["s"]["line"], 2)

    def test_undeclared_read(self):
        r = run("serve z\nplate")
        self.assertEqual(len(r["errors"]), 1)
        self.assertIn("'z' is not declared", r["errors"][0]["message"])
        self.assertEqual((r["errors"][0]["line"], r["errors"][0]["col"]), (1, 7))

    def test_undeclared_assignment(self):
        self.assertIn("not declared", msgs("q into 1\nplate")[0])

    def test_redeclaration(self):
        self.assertIn("already declared (line 1)", msgs("mix a into 1\nmix a into 2\nplate")[0])

    def test_self_reference_in_declaration(self):
        self.assertIn("'x' is not declared", msgs("mix x into x plus 1\nplate")[0])

    def test_assign_type_mismatch(self):
        self.assertIn("Cannot assign string to 'x' (declared as number)",
                      msgs('mix x into 1\nx into "a"\nplate')[0])

    def test_string_plus_number(self):
        self.assertEqual(msgs('mix s into "hi" plus 5\nplate'), ["Cannot apply 'plus' to string and number"])

    def test_string_concat_allowed(self):
        self.assertTrue(run('mix s into "a" plus "b"\nplate')["ok"])

    def test_string_in_blend_slice_peel(self):
        for op in ("blend", "slice", "peel"):
            self.assertEqual(len(msgs(f'serve "a" {op} 2\nplate')), 1, op)

    def test_comparisons(self):
        self.assertTrue(run('serve "a" matches "b"\nplate')["ok"])
        self.assertEqual(len(msgs('serve "a" hotter "b"\nplate')), 1)
        self.assertEqual(len(msgs('serve 1 matches "b"\nplate')), 1)

    def test_condition_must_not_be_string(self):
        self.assertIn("Condition", msgs('taste "x"\n serve 1\ndone\nplate')[0])
        self.assertTrue(run("taste 1\n serve 1\ndone\nplate")["ok"])

    def test_division_by_zero(self):
        self.assertEqual(msgs("serve 4 slice 0\nplate"), ["Division by zero"])
        self.assertTrue(run("serve 4 slice 2\nplate")["ok"])

    def test_checks_inside_blocks(self):
        src = "mix x into 1\ntaste x hotter 0\n serve y\nbland\n serve w\ndone\nplate"
        self.assertEqual([e["line"] for e in run(src)["errors"]], [3, 5])

    def test_no_cascade_after_undeclared(self):
        self.assertEqual(len(msgs("mix a into zz plus 1\nserve a plus 2\nplate")), 1)

    def test_semantic_error_sample(self):
        code = next(s["code"] for s in SAMPLES if s["name"].startswith("Semantic"))
        r = run(code)
        self.assertEqual([e["line"] for e in r["errors"]], [1, 3, 4])


if __name__ == "__main__":
    unittest.main()
