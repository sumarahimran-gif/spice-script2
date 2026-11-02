import unittest
from app.lexer import lex
from app.parser import parse
from app.grammar import SAMPLES


def run(src):
    return parse(lex(src)["tokens"])


def sample(name):
    return next(s["code"] for s in SAMPLES if s["name"] == name)


class ParserTests(unittest.TestCase):
    def test_empty_program(self):
        r = run("plate")
        self.assertTrue(r["ok"])
        self.assertEqual(r["ast"]["body"], [])

    def test_all_valid_samples(self):
        for name in ("Arithmetic", "If / else", "Loop"):
            self.assertTrue(run(sample(name))["ok"], name)

    def test_declare_and_print(self):
        body = run('mix x into 3\nserve x\nplate')["ast"]["body"]
        self.assertEqual([n["type"] for n in body], ["Declare", "Print"])
        self.assertEqual(body[0]["value"]["value"], 3)

    def test_precedence(self):
        v = run("mix x into 1 plus 2 blend 3\nplate")["ast"]["body"][0]["value"]
        self.assertEqual(v["op"], "plus")
        self.assertEqual(v["right"]["op"], "blend")

    def test_left_associative(self):
        v = run("mix x into 9 peel 4 peel 1\nplate")["ast"]["body"][0]["value"]
        self.assertEqual(v["op"], "peel")
        self.assertEqual(v["left"]["op"], "peel")
        self.assertEqual(v["right"]["value"], 1)

    def test_comparison_binds_loosest(self):
        v = run("mix x into 1 plus 2 hotter 3\nplate")["ast"]["body"][0]["value"]
        self.assertEqual(v["op"], "hotter")
        self.assertEqual(v["left"]["op"], "plus")

    def test_if_else_structure(self):
        node = run(sample("If / else"))["ast"]["body"][2]
        self.assertEqual(node["type"], "If")
        self.assertEqual(len(node["then"]), 1)
        self.assertEqual(len(node["else"]), 1)

    def test_if_without_else(self):
        node = run("taste 1 hotter 0 serve 1 done\nplate")["ast"]["body"][0]
        self.assertIsNone(node["else"])

    def test_nested_blocks(self):
        src = "simmer 1 hotter 0\n taste 1 matches 1\n  serve 1\n done\ndone\nplate"
        loop = run(src)["ast"]["body"][0]
        self.assertEqual(loop["body"][0]["type"], "If")

    def test_positions(self):
        n = run("mix x into 1\n  serve x\nplate")["ast"]["body"][1]
        self.assertEqual((n["line"], n["col"]), (2, 3))

    def test_missing_plate(self):
        r = run("mix x into 1")
        self.assertFalse(r["ok"])
        self.assertIsNone(r["ast"])
        self.assertIn("plate", r["errors"][0]["message"])

    def test_missing_done(self):
        r = run("simmer 1 hotter 0\n serve 1\nplate")
        self.assertFalse(r["ok"])
        self.assertTrue(any("done" in e["message"] for e in r["errors"]))

    def test_missing_into(self):
        r = run("mix x 5\nplate")
        self.assertFalse(r["ok"])
        self.assertEqual((r["errors"][0]["line"], r["errors"][0]["col"]), (1, 7))

    def test_missing_operand(self):
        r = run("mix x into 1 plus\nplate")
        self.assertFalse(r["ok"])
        self.assertIn("Expected a number, string or variable", r["errors"][0]["message"])

    def test_chained_comparison_rejected(self):
        self.assertFalse(run("serve 1 hotter 2 hotter 3\nplate")["ok"])

    def test_stray_bland_and_done(self):
        self.assertFalse(run("bland\nplate")["ok"])
        self.assertFalse(run("done\nplate")["ok"])

    def test_text_after_plate(self):
        self.assertFalse(run("plate\nserve 1")["ok"])

    def test_collects_multiple_errors(self):
        r = run("mix x 5\nserve\nmix y into 2\nplate")
        self.assertGreaterEqual(len(r["errors"]), 2)
        self.assertEqual([e["line"] for e in r["errors"]][:2], [1, 3])

    def test_never_hangs_on_garbage(self):
        for src in ["", "plus plus plus", "taste taste taste", "into into", 'serve "a" "b" plate',
                    "done done bland plate", "mix", "x"]:
            run(src)  # must terminate

    def test_semantic_sample_is_syntactically_valid(self):
        self.assertTrue(run(sample("Semantic error"))["ok"])


if __name__ == "__main__":
    unittest.main()
