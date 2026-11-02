import unittest
from app import pipeline
from app.grammar import SAMPLES


def sample(name):
    return next(s["code"] for s in SAMPLES if s["name"] == name)


class PipelineTests(unittest.TestCase):
    def test_sample_outputs(self):
        cases = {
            "Arithmetic": ["13", "30"],
            "If / else": ["x is bigger"],
            "Loop": ["3", "2", "1"],
            "Nested blocks": ["1", "two", "3"],
        }
        for name, expected in cases.items():
            r = pipeline.run_all(sample(name))
            self.assertTrue(r["ok"], name)
            self.assertEqual(r["output"], expected, name)

    def test_run_all_stops_at_first_failing_stage(self):
        r = pipeline.run_all(sample("Lexical error"))
        self.assertEqual(r["stopped_at"], "lexical")
        self.assertEqual(r["stages"]["syntax"]["status"], "skipped")
        r = pipeline.run_all(sample("Semantic error"))
        self.assertEqual(r["stopped_at"], "semantic")
        self.assertIn("icg", [k for k, v in r["stages"].items() if v.get("status") == "skipped"])
        r = pipeline.run_all("mix x 5\nplate")
        self.assertEqual(r["stopped_at"], "syntax")

    def test_runtime_error_in_full_run(self):
        r = pipeline.run_all("mix z into 0\nserve 1 slice z\nplate")
        self.assertEqual(r["stopped_at"], "run")
        self.assertEqual(r["errors"][0]["message"], "Division by zero")

    def test_infinite_loop_in_full_run(self):
        r = pipeline.run_all("simmer 1 hotter 0\nserve 1\ndone\nplate")
        self.assertEqual(r["stopped_at"], "run")

    def test_single_stage_blocked_by_earlier_failure(self):
        r = pipeline.run_single("serve zz\nplate", "icg")
        self.assertFalse(r["ok"])
        self.assertEqual(r["blocked_by"], "semantic")
        self.assertEqual(r["instructions"], [])
        r = pipeline.run_single("mix x 5\nplate", "semantic")
        self.assertEqual(r["blocked_by"], "syntax")

    def test_syntax_and_semantic_still_run_with_lexical_errors(self):
        src = "mix x into 10 @\nserve x\nplate"
        self.assertTrue(pipeline.run_single(src, "syntax")["ok"])
        self.assertTrue(pipeline.run_single(src, "semantic")["ok"])
        self.assertEqual(pipeline.run_single(src, "icg")["blocked_by"], "lexical")

    def test_engines_do_not_import_each_other(self):
        import ast, pathlib
        engines = {"lexer", "parser", "semantic", "icg", "interpreter"}
        for name in engines:
            tree = ast.parse(pathlib.Path(f"app/{name}.py").read_text())
            imported = set()
            for n in ast.walk(tree):
                if isinstance(n, ast.ImportFrom) and n.level:
                    imported.add((n.module or "").split(".")[0])
                elif isinstance(n, ast.ImportFrom) and (n.module or "").startswith("app."):
                    imported.add(n.module.split(".")[1])
            self.assertFalse(imported & engines, f"{name} imports {imported & engines}")


if __name__ == "__main__":
    unittest.main()
