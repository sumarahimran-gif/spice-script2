"""
SpiceScript Syntax Analyzer (Stage 2)
=====================================
Independent engine: a hand-written recursive-descent parser (the grammar is LL(1)).
It works on plain token dicts and imports no other compiler stage; the API layer is
what feeds it tokens.

Public API:
    parse(tokens: list[dict]) -> dict   # {"stage", "ok", "ast", "errors", "node_count"}

AST nodes are plain dicts: {"type": ..., "line": ..., "col": ..., ...fields}
    Program{body}  Declare{name,value}  Assign{name,value}  Print{value}
    If{cond,then,else}  While{cond,body}  BinOp{op,left,right}
    Number{value}  String{value}  Var{name}
"""

# Limits that keep hostile input from exhausting memory or the call stack.
MAX_BLOCK_DEPTH = 30      # nested taste/simmer blocks
MAX_OPERATIONS = 100      # operators in one expression
MAX_ERRORS = 100          # errors reported before the rest are dropped
MAX_NUMBER_CHARS = 18

STATEMENT_START = {"VAR_DECL", "IDENT", "PRINT", "IF", "LOOP"}
# Tokens the parser can safely resume at after an error.
SYNC = STATEMENT_START | {"BLOCK_END", "ELSE", "END_PROGRAM", "EOF"}
COMPARE = {"GT": "hotter", "LT": "cooler", "EQ": "matches"}
ADDITIVE = {"ADD": "plus", "SUB": "peel"}
MULTIPLICATIVE = {"MUL": "blend", "DIV": "slice"}


class ParseError(Exception):
    def __init__(self, message, token):
        super().__init__(message)
        self.message = message
        self.token = token


def describe(tok) -> str:
    return "end of input" if tok["kind"] == "EOF" else repr(tok["lexeme"])


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0
        self.errors = []
        self.depth = 0   # how many blocks we are inside
        self.ops = 0     # operators seen in the current expression

    # ---- helpers ------------------------------------------------------------
    @property
    def tok(self):
        return self.tokens[self.pos]

    def advance(self):
        t = self.tok
        if t["kind"] != "EOF":
            self.pos += 1
        return t

    def at(self, *kinds):
        return self.tok["kind"] in kinds

    def expect(self, kind, what):
        if not self.at(kind):
            raise ParseError(f"Expected {what} but found {describe(self.tok)}", self.tok)
        return self.advance()

    def node(self, type_, tok, **fields):
        return {"type": type_, "line": tok["line"], "col": tok["col"], **fields}

    def record(self, err: ParseError):
        t = err.token
        if len(self.errors) >= MAX_ERRORS:
            if len(self.errors) == MAX_ERRORS:   # say so once, then stay quiet
                self.errors.append({"stage": "syntax", "line": t["line"], "col": t["col"], "lexeme": "",
                                    "message": f"Too many errors; only the first {MAX_ERRORS} are shown"})
            return
        self.errors.append({"stage": "syntax", "message": err.message,
                            "line": t["line"], "col": t["col"], "lexeme": t["lexeme"]})

    def synchronize(self, start):
        """Skip to a safe token; always make progress so we never loop forever."""
        if self.pos == start and not self.at("EOF"):
            self.advance()
        while not self.at(*SYNC):
            self.advance()

    # ---- grammar ------------------------------------------------------------
    def program(self):
        first = self.tok
        body = self.statements(stop={"END_PROGRAM", "EOF"})
        if self.at("END_PROGRAM"):
            self.advance()
            if not self.at("EOF"):
                self.record(ParseError(f"Unexpected {describe(self.tok)} after 'plate'", self.tok))
        else:
            self.record(ParseError("Program must end with 'plate'", self.tok))
        return self.node("Program", first, body=body)

    def statements(self, stop):
        """statement* until one of the stop kinds; errors are recorded and skipped."""
        out = []
        while not self.at(*stop):
            start = self.pos
            try:
                if not self.at(*STATEMENT_START):
                    raise ParseError(f"Unexpected {describe(self.tok)}; expected a statement", self.tok)
                out.append(self.statement())
            except ParseError as err:
                self.record(err)
                self.synchronize(start)
                # A stray block closer at this level can never be consumed: skip it.
                if self.at("BLOCK_END", "ELSE") and not set(stop) & {"BLOCK_END", "ELSE"}:
                    self.record(ParseError(f"Unexpected {describe(self.tok)} without matching block", self.tok))
                    self.advance()
        return out

    def statement(self):
        t = self.tok
        kind = t["kind"]
        if kind == "VAR_DECL":
            self.advance()
            name = self.expect("IDENT", "a variable name after 'mix'")
            self.expect("ASSIGN", "'into'")
            return self.node("Declare", t, name=name["lexeme"], value=self.expr())
        if kind == "IDENT":
            self.advance()
            self.expect("ASSIGN", f"'into' after {t['lexeme']!r}")
            return self.node("Assign", t, name=t["lexeme"], value=self.expr())
        if kind == "PRINT":
            self.advance()
            return self.node("Print", t, value=self.expr())
        if kind in ("IF", "LOOP") and self.depth >= MAX_BLOCK_DEPTH:
            raise ParseError(f"Blocks are nested too deeply (limit {MAX_BLOCK_DEPTH})", t)
        if kind == "IF":
            self.advance()
            cond = self.expr()
            self.depth += 1
            try:
                then = self.statements(stop={"ELSE", "BLOCK_END", "END_PROGRAM", "EOF"})
                else_ = None
                if self.at("ELSE"):
                    self.advance()
                    else_ = self.statements(stop={"BLOCK_END", "END_PROGRAM", "EOF"})
            finally:
                self.depth -= 1
            self.expect("BLOCK_END", f"'done' to close the 'taste' on line {t['line']}")
            return self.node("If", t, cond=cond, **{"then": then, "else": else_})
        if kind == "LOOP":
            self.advance()
            cond = self.expr()
            self.depth += 1
            try:
                body = self.statements(stop={"BLOCK_END", "END_PROGRAM", "EOF"})
            finally:
                self.depth -= 1
            self.expect("BLOCK_END", f"'done' to close the 'simmer' on line {t['line']}")
            return self.node("While", t, cond=cond, body=body)
        raise ParseError(f"Unexpected {describe(t)}", t)  # unreachable

    def count_operation(self, op_token):
        self.ops += 1
        if self.ops > MAX_OPERATIONS:
            raise ParseError(f"Expression is too long (limit {MAX_OPERATIONS} operations)", op_token)

    def expr(self):
        self.ops = 0
        left = self.additive()
        if self.at(*COMPARE):
            op = self.advance()
            self.count_operation(op)
            return self.node("BinOp", op, op=COMPARE[op["kind"]], left=left, right=self.additive())
        return left

    def additive(self):
        left = self.term()
        while self.at(*ADDITIVE):
            op = self.advance()
            self.count_operation(op)
            left = self.node("BinOp", op, op=ADDITIVE[op["kind"]], left=left, right=self.term())
        return left

    def term(self):
        left = self.factor()
        while self.at(*MULTIPLICATIVE):
            op = self.advance()
            self.count_operation(op)
            left = self.node("BinOp", op, op=MULTIPLICATIVE[op["kind"]], left=left, right=self.factor())
        return left

    def factor(self):
        t = self.tok
        if t["kind"] == "NUMBER":
            if len(t["lexeme"]) > MAX_NUMBER_CHARS:
                raise ParseError(f"Number is too long (limit {MAX_NUMBER_CHARS} characters)", t)
            self.advance()
            return self.node("Number", t, value=float(t["lexeme"]) if "." in t["lexeme"] else int(t["lexeme"]))
        if t["kind"] == "STRING":
            self.advance()
            return self.node("String", t, value=t["lexeme"][1:-1])
        if t["kind"] == "IDENT":
            self.advance()
            return self.node("Var", t, name=t["lexeme"])
        raise ParseError(f"Expected a number, string or variable but found {describe(t)}", t)


def count_nodes(n) -> int:
    if isinstance(n, dict):
        return (1 if "type" in n else 0) + sum(count_nodes(v) for v in n.values())
    if isinstance(n, list):
        return sum(count_nodes(v) for v in n)
    return 0


def parse(tokens: list) -> dict:
    """Run the syntax stage on a token list (dicts with kind/lexeme/line/col)."""
    if not tokens or tokens[-1]["kind"] != "EOF":
        last = tokens[-1] if tokens else {"line": 1, "col": 1}
        tokens = list(tokens) + [{"type": "EOF", "kind": "EOF", "lexeme": "",
                                  "line": last["line"], "col": last["col"]}]
    p = Parser(tokens)
    tree = p.program()
    ok = not p.errors
    return {
        "stage": "syntax",
        "ok": ok,
        "ast": tree if ok else None,
        "errors": p.errors,
        "node_count": count_nodes(tree) if ok else 0,
    }
