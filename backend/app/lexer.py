"""
SpiceScript Lexical Analyzer (Stage 1)
======================================
Independent engine: takes source text, returns tokens and errors.
It imports nothing from the other compiler stages.

Public API:
    lex(source: str) -> dict   # {"ok": bool, "tokens": [...], "errors": [...]}
"""
import re
from enum import Enum, auto


class TokenType(Enum):
    KEYWORD = auto()
    OPERATOR = auto()
    IDENTIFIER = auto()
    NUMBER = auto()
    STRING = auto()
    EOF = auto()


# word -> (kind used by the parser)
KEYWORDS = {
    "mix": "VAR_DECL",
    "serve": "PRINT",
    "taste": "IF",
    "bland": "ELSE",
    "simmer": "LOOP",
    "done": "BLOCK_END",     # ends taste/bland and simmer blocks
    "plate": "END_PROGRAM",
}

WORD_OPERATORS = {
    "into": "ASSIGN",
    "plus": "ADD",
    "peel": "SUB",
    "blend": "MUL",
    "slice": "DIV",
    "hotter": "GT",
    "cooler": "LT",
    "matches": "EQ",
}


MAX_NUMBER_CHARS = 18   # keeps every number safely inside what the interpreter can handle


class Token:
    __slots__ = ("type", "kind", "lexeme", "line", "col")

    def __init__(self, type_, kind, lexeme, line, col):
        self.type = type_      # TokenType
        self.kind = kind       # fine-grained kind, e.g. ADD, VAR_DECL, NUMBER
        self.lexeme = lexeme   # raw text
        self.line = line
        self.col = col

    def to_dict(self):
        return {
            "type": self.type.name,
            "kind": self.kind,
            "lexeme": self.lexeme,
            "line": self.line,
            "col": self.col,
        }

    def __repr__(self):
        return f"Token({self.type.name}/{self.kind}, {self.lexeme!r}, {self.line}:{self.col})"


class LexerError:
    def __init__(self, message, line, col, lexeme=""):
        self.message = message
        self.line = line
        self.col = col
        self.lexeme = lexeme

    def to_dict(self):
        return {
            "stage": "lexical",
            "message": self.message,
            "line": self.line,
            "col": self.col,
            "lexeme": self.lexeme,
        }


class Lexer:
    # Order matters: more specific patterns come before general ones.
    TOKEN_REGEX = re.compile(
        r"""
          (?P<NEWLINE>     \n )
        | (?P<SKIP>        [ \t\r]+ )
        | (?P<COMMENT>     \#[^\n]* )
        | (?P<STRING>      "[^"\n]*" )
        | (?P<BAD_STRING>  "[^\n]* )
        | (?P<BAD_NUMBER>  \d+(?:\.\d+)?[A-Za-z_][A-Za-z0-9_]* )
        | (?P<NUMBER>      \d+(?:\.\d+)? )
        | (?P<WORD>        [A-Za-z_][A-Za-z0-9_]* )
        | (?P<MISMATCH>    . )
        """,
        re.VERBOSE,
    )

    def __init__(self, source: str):
        self.source = source
        self.tokens = []
        self.errors = []

    def tokenize(self):
        line = 1
        line_start = 0
        last_end = 0

        for m in self.TOKEN_REGEX.finditer(self.source):
            kind = m.lastgroup
            value = m.group()
            col = m.start() - line_start + 1
            last_end = m.end()

            if kind == "NEWLINE":
                line += 1
                line_start = m.end()
            elif kind in ("SKIP", "COMMENT"):
                continue
            elif kind == "STRING":
                self.tokens.append(Token(TokenType.STRING, "STRING", value, line, col))
            elif kind == "NUMBER":
                if len(value) > MAX_NUMBER_CHARS:
                    self.errors.append(LexerError(
                        f"Number is too long (limit {MAX_NUMBER_CHARS} characters)", line, col, value))
                else:
                    self.tokens.append(Token(TokenType.NUMBER, "NUMBER", value, line, col))
            elif kind == "WORD":
                if value in KEYWORDS:
                    self.tokens.append(Token(TokenType.KEYWORD, KEYWORDS[value], value, line, col))
                elif value in WORD_OPERATORS:
                    self.tokens.append(Token(TokenType.OPERATOR, WORD_OPERATORS[value], value, line, col))
                else:
                    self.tokens.append(Token(TokenType.IDENTIFIER, "IDENT", value, line, col))
            elif kind == "BAD_STRING":
                self.errors.append(LexerError("Unterminated string literal", line, col, value))
            elif kind == "BAD_NUMBER":
                self.errors.append(
                    LexerError(f"Malformed number or identifier {value!r}", line, col, value)
                )
            elif kind == "MISMATCH":
                self.errors.append(
                    LexerError(f"Unexpected character {value!r}", line, col, value)
                )

        eof_col = last_end - line_start + 1
        self.tokens.append(Token(TokenType.EOF, "EOF", "", line, eof_col))
        return self.tokens


def lex(source: str) -> dict:
    """Run the lexical stage and return a JSON-friendly result."""
    lexer = Lexer(source)
    tokens = lexer.tokenize()
    return {
        "stage": "lexical",
        "ok": len(lexer.errors) == 0,
        "tokens": [t.to_dict() for t in tokens],
        "errors": [e.to_dict() for e in lexer.errors],
        "token_count": len(tokens),
    }


if __name__ == "__main__":
    import sys

    src = open(sys.argv[1]).read() if len(sys.argv) > 1 else 'mix x into 10\nserve x\nplate'
    result = lex(src)
    for t in result["tokens"]:
        print(f'{t["line"]:<5}{t["col"]:<5}{t["type"]:<12}{t["kind"]:<12}{t["lexeme"]}')
    for e in result["errors"]:
        print(f'ERROR line {e["line"]}, col {e["col"]}: {e["message"]}')
