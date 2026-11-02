"""
SpiceScript Intermediate Code Generator (Stage 4)
=================================================
Independent engine: takes a valid AST (plain dicts) and emits three-address code (TAC).
It imports no other compiler stage; the API layer connects them.

Instruction kinds (each is a dict with "index", "op", "text", "line", "col" + fields):
    assign   x = a             binop   x = a + b       print   print a
    label    L1:               goto    goto L1         iffalse ifFalse a goto L2
Operands are strings: a variable or temporary (`x`, `$t1`), a number (`3`, `2.5`)
or a quoted string (`"hi"`). Temporaries start with `$` so they cannot clash with
user identifiers.

    taste c A bland B done            simmer c B done
        <c> -> t                          L1:
        ifFalse t goto Lelse              <c> -> t
        A                                 ifFalse t goto L2
        goto Lend                         B
      Lelse:                              goto L1
        B                               L2:
      Lend:

Public API:
    generate(ast: dict) -> dict   # {"stage","ok","instructions","errors","instruction_count"}
"""

OPSYM = {"plus": "+", "peel": "-", "blend": "*", "slice": "/",
         "hotter": ">", "cooler": "<", "matches": "=="}


class Generator:
    def __init__(self):
        self.code = []
        self.temps = 0
        self.labels = 0

    def temp(self):
        self.temps += 1
        return f"$t{self.temps}"

    def new_label(self):
        self.labels += 1
        return f"L{self.labels}"

    def emit(self, node, op, text, **fields):
        self.code.append({"index": len(self.code) + 1, "op": op, "text": text,
                          "line": node["line"], "col": node["col"], **fields})

    # ---- statements ---------------------------------------------------------
    def block(self, stmts):
        for s in stmts or []:
            self.statement(s)

    def statement(self, n):
        t = n["type"]
        if t in ("Declare", "Assign"):
            value = n["value"]
            if value["type"] == "BinOp":
                self.expr(value, dest=n["name"])     # x = a + b, no extra copy
            else:
                a = self.expr(value)
                self.emit(n, "assign", f"{n['name']} = {a}", result=n["name"], arg1=a)
        elif t == "Print":
            a = self.expr(n["value"])
            self.emit(n, "print", f"print {a}", arg1=a)
        elif t == "If":
            else_l = self.new_label() if n["else"] is not None else None
            end_l = self.new_label()
            c = self.expr(n["cond"])
            skip = else_l or end_l
            self.emit(n, "iffalse", f"ifFalse {c} goto {skip}", arg1=c, target=skip)
            self.block(n["then"])
            if else_l:
                self.emit(n, "goto", f"goto {end_l}", target=end_l)
                self.emit(n, "label", f"{else_l}:", label=else_l)
                self.block(n["else"])
            self.emit(n, "label", f"{end_l}:", label=end_l)
        elif t == "While":
            start, end = self.new_label(), self.new_label()
            self.emit(n, "label", f"{start}:", label=start)
            c = self.expr(n["cond"])
            self.emit(n, "iffalse", f"ifFalse {c} goto {end}", arg1=c, target=end)
            self.block(n["body"])
            self.emit(n, "goto", f"goto {start}", target=start)
            self.emit(n, "label", f"{end}:", label=end)

    # ---- expressions: return the operand that holds the value ---------------
    def expr(self, n, dest=None):
        t = n["type"]
        if t == "Number":
            return str(n["value"])
        if t == "String":
            return f'"{n["value"]}"'
        if t == "Var":
            return n["name"]
        left, right = self.expr(n["left"]), self.expr(n["right"])
        target = dest or self.temp()
        sym = OPSYM[n["op"]]
        self.emit(n, "binop", f"{target} = {left} {sym} {right}",
                  result=target, arg1=left, operator=sym, arg2=right)
        return target


def generate(ast: dict) -> dict:
    g = Generator()
    g.block(ast.get("body", []))
    return {"stage": "icg", "ok": True, "instructions": g.code, "errors": [],
            "instruction_count": len(g.code)}
