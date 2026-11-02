import unittest
from app.lexer import lex


def kinds(src):
    return [t["kind"] for t in lex(src)["tokens"]]


class LexerTests(unittest.TestCase):
    def test_basic_declaration(self):
        r = lex("mix x into 10")
        self.assertTrue(r["ok"])
        self.assertEqual(kinds("mix x into 10"), ["VAR_DECL", "IDENT", "ASSIGN", "NUMBER", "EOF"])

    def test_all_operators(self):
        src = "plus peel blend slice hotter cooler matches"
        self.assertEqual(kinds(src), ["ADD", "SUB", "MUL", "DIV", "GT", "LT", "EQ", "EOF"])

    def test_done_keyword(self):
        self.assertIn("BLOCK_END", kinds("taste x hotter 1 serve x done"))

    def test_decimal_and_string(self):
        r = lex('serve 3.14\nserve "hi there"')
        lexemes = [t["lexeme"] for t in r["tokens"]]
        self.assertIn("3.14", lexemes)
        self.assertIn('"hi there"', lexemes)

    def test_comment_ignored(self):
        self.assertEqual(kinds("# just a comment\nplate"), ["END_PROGRAM", "EOF"])

    def test_positions(self):
        toks = lex("mix x\n  serve x")["tokens"]
        serve = [t for t in toks if t["lexeme"] == "serve"][0]
        self.assertEqual((serve["line"], serve["col"]), (2, 3))

    def test_collects_all_errors(self):
        r = lex('mix x into 10 @\nserve "oops\nmix 9lives into 1')
        self.assertFalse(r["ok"])
        msgs = [e["message"] for e in r["errors"]]
        self.assertEqual(len(msgs), 3)
        self.assertTrue(any("Unexpected character" in m for m in msgs))
        self.assertTrue(any("Unterminated string" in m for m in msgs))
        self.assertTrue(any("Malformed" in m for m in msgs))
        self.assertEqual([e["line"] for e in r["errors"]], [1, 2, 3])

    def test_tokens_still_returned_when_errors(self):
        r = lex("mix x into 10 @")
        self.assertEqual(r["tokens"][0]["lexeme"], "mix")

    def test_empty_source(self):
        r = lex("")
        self.assertTrue(r["ok"])
        self.assertEqual(kinds(""), ["EOF"])

    def test_keyword_is_case_sensitive(self):
        self.assertEqual(kinds("Mix"), ["IDENT", "EOF"])


if __name__ == "__main__":
    unittest.main()
