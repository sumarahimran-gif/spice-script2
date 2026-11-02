"""
SpiceScript Semantic Analyzer (Stage 3)
=======================================
Independent engine: takes the AST produced by the syntax stage (plain dicts) and
checks meaning. It imports no other compiler stage; the API layer connects them.

Types: "number" and "string" (a comparison yields a number, 1 or 0).
A variable has one type, fixed by its `mix` declaration, in a single global scope.

Rules checked
    - use of an undeclared variable (read or assignment)
    - redeclaration of a variable
    - assigning a value of the wrong type to a variable
    - plus: number+number or string+string; peel/blend/slice: numbers only
    - hotter/cooler: numbers only; matches: both sides the same type
    - taste/simmer condition must be a number (e.g. a comparison)
    - division by a literal zero

Public API:
    analyze(ast: dict) -> dict   # {"stage","ok","symbol_table","errors"}
"""

NUMBER, STRING, UNKNOWN = "number", "string", "unknown"   # UNKNOWN = already reported, stay quiet


class Analyzer:
    def __init__(self):
        self.symbols = {}   # name -> {name, type, line, col, reads, writes}
        self.errors = []

    def error(self, node, message):
        self.errors.append({"stage": "semantic", "message": message,
                            "line": node["line"], "col": node["col"]})

    # ---- statements ---------------------------------------------------------
    def block(self, stmts):
        for s in stmts or []:
            self.statement(s)

    def statement(self, n):
        t = n["type"]
        if t == "Declare":
            vtype = self.expr(n["value"])          # evaluate first: `mix x into x` is an error
            if n["name"] in self.symbols:
                first = self.symbols[n["name"]]
                self.error(n, f"Variable {n['name']!r} is already declared (line {first['line']})")
            else:
                self.symbols[n["name"]] = {"name": n["name"], "type": vtype, "line": n["line"],
                                           "col": n["col"], "reads": 0, "writes": 1}
        elif t == "Assign":
            vtype = self.expr(n["value"])
            sym = self.symbols.get(n["name"])
            if not sym:
                self.error(n, f"Variable {n['name']!r} is not declared; use 'mix' first")
            else:
                sym["writes"] += 1
                if sym["type"] == UNKNOWN:
                    sym["type"] = vtype            # first real type seen after an earlier error
                elif vtype not in (UNKNOWN, sym["type"]):
                    self.error(n, f"Cannot assign {vtype} to {n['name']!r} (declared as {sym['type']})")
        elif t == "Print":
            self.expr(n["value"])
        elif t in ("If", "While"):
            ctype = self.expr(n["cond"])
            if ctype == STRING:
                self.error(n["cond"], "Condition must be a number or a comparison, not a string")
            if t == "If":
                self.block(n["then"])
                self.block(n["else"])
            else:
                self.block(n["body"])

    # ---- expressions: return the expression's type --------------------------
    def expr(self, n):
        t = n["type"]
        if t == "Number":
            return NUMBER
        if t == "String":
            return STRING
        if t == "Var":
            sym = self.symbols.get(n["name"])
            if not sym:
                self.error(n, f"Variable {n['name']!r} is not declared")
                return UNKNOWN
            sym["reads"] += 1
            return sym["type"]
        return self.binop(n)

    def binop(self, n):
        op = n["op"]
        lt, rt = self.expr(n["left"]), self.expr(n["right"])
        if op == "slice" and n["right"]["type"] == "Number" and n["right"]["value"] == 0:
            self.error(n["right"], "Division by zero")
        if UNKNOWN in (lt, rt):                    # operand already reported; avoid cascades
            return STRING if op == "plus" and STRING in (lt, rt) else NUMBER
        if op == "plus":
            if lt == rt:
                return lt
            self.mismatch(n, op, lt, rt)
            return UNKNOWN
        if op in ("peel", "blend", "slice", "hotter", "cooler"):
            if lt != NUMBER or rt != NUMBER:
                self.mismatch(n, op, lt, rt)
            return NUMBER
        if op == "matches":
            if lt != rt:
                self.mismatch(n, op, lt, rt)
            return NUMBER
        return UNKNOWN

    def mismatch(self, n, op, lt, rt):
        self.error(n, f"Cannot apply {op!r} to {lt} and {rt}")


def analyze(ast: dict) -> dict:
    a = Analyzer()
    a.block(ast.get("body", []))
    errors = sorted(a.errors, key=lambda e: (e["line"], e["col"]))
    return {
        "stage": "semantic",
        "ok": not errors,
        "symbol_table": sorted(a.symbols.values(), key=lambda s: (s["line"], s["col"])),
        "errors": errors,
    }
