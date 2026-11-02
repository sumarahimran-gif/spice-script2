import unittest
from app.lexer import lex
from app.parser import parse
from app.icg import generate


def tac(src):
    ast = parse(lex(src)["tokens"])["ast"]
    return [i["text"] for i in generate(ast)["instructions"]]


class IcgTests(unittest.TestCase):
    def test_declaration_and_print(self):
        self.assertEqual(tac("mix x into 3\nserve x\nplate"), ["x = 3", "print x"])

    def test_binop_goes_straight_to_destination(self):
        self.assertEqual(tac("mix x into 1\nx into x peel 1\nplate"), ["x = 1", "x = x - 1"])

    def test_temporaries_and_precedence(self):
        self.assertEqual(tac("mix r into 1 plus 2 blend 3\nplate"),
                         ["$t1 = 2 * 3", "r = 1 + $t1"])

    def test_string_operand(self):
        self.assertEqual(tac('serve "hi"\nplate'), ['print "hi"'])

    def test_while_loop(self):
        src = "mix x into 3\nsimmer x hotter 0\n serve x\n x into x peel 1\ndone\nplate"
        self.assertEqual(tac(src), [
            "x = 3", "L1:", "$t1 = x > 0", "ifFalse $t1 goto L2",
            "print x", "x = x - 1", "goto L1", "L2:"])

    def test_if_else(self):
        src = 'mix x into 1\ntaste x matches 1\n serve "a"\nbland\n serve "b"\ndone\nplate'
        self.assertEqual(tac(src), [
            "x = 1", "$t1 = x == 1", "ifFalse $t1 goto L1", 'print "a"',
            "goto L2", "L1:", 'print "b"', "L2:"])

    def test_if_without_else(self):
        self.assertEqual(tac("taste 1\n serve 1\ndone\nplate"),
                         ["ifFalse 1 goto L1", "print 1", "L1:"])

    def test_indexes_and_source_lines(self):
        ins = generate(parse(lex("mix x into 1\n serve x\nplate")["tokens"])["ast"])["instructions"]
        self.assertEqual([i["index"] for i in ins], [1, 2])
        self.assertEqual([i["line"] for i in ins], [1, 2])

    def test_all_jump_targets_exist(self):
        src = next(s["code"] for s in __import__("app.grammar", fromlist=["x"]).SAMPLES if s["name"] == "Nested blocks")
        ins = generate(parse(lex(src)["tokens"])["ast"])["instructions"]
        labels = {i["label"] for i in ins if i["op"] == "label"}
        self.assertTrue(all(i["target"] in labels for i in ins if "target" in i))


if __name__ == "__main__":
    unittest.main()
