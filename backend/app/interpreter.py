"""
SpiceScript Interpreter (final output)
======================================
Independent engine: executes the three-address code from the ICG stage and collects
what the program prints with `serve`. It imports no other compiler stage.

Public API:
    execute(instructions: list[dict], max_steps: int = 10000) -> dict
        {"stage": "run", "ok", "output": [str], "errors": [...], "steps": int}
"""
import re

MAX_STRING = 10_000        # characters in one text value
MAX_NUMBER = 10 ** 30      # largest absolute value a number may reach
MAX_OUTPUT_LINES = 1000

NUMBER_RE = re.compile(r"^\d+(\.\d+)?$")


class RuntimeFault(Exception):
    pass


def normalize(v):
    """Keep numbers tidy: 6.0 -> 6, 0.1+0.2 -> 0.3."""
    if isinstance(v, float):
        v = round(v, 10)
        if v == int(v):
            return int(v)
    return v


def check_size(v):
    """Stop values from growing without bound (e.g. doubling a string or squaring a number in a loop)."""
    if isinstance(v, str):
        if len(v) > MAX_STRING:
            raise RuntimeFault(f"Text is too long (limit {MAX_STRING} characters)")
    elif v != v or abs(v) > MAX_NUMBER:
        raise RuntimeFault("Number is too large (limit 1e30)")
    return v


def show(v) -> str:
    return v if isinstance(v, str) else str(normalize(v))


def execute(instructions: list, max_steps: int = 10000) -> dict:
    labels = {i["label"]: pos for pos, i in enumerate(instructions) if i["op"] == "label"}
    env, output, errors = {}, [], []
    pc = steps = 0

    def value(operand):
        if operand.startswith('"'):
            return operand[1:-1]
        if NUMBER_RE.match(operand):
            return float(operand) if "." in operand else int(operand)
        if operand not in env:
            raise RuntimeFault(f"Variable {operand!r} has no value")
        return env[operand]

    def compute(op, a, b):
        if op == "+":
            if isinstance(a, str) != isinstance(b, str):
                raise RuntimeFault("Cannot add a string and a number")
            return a + b
        if op == "==":
            return 1 if a == b else 0
        if isinstance(a, str) or isinstance(b, str):
            raise RuntimeFault(f"Cannot apply '{op}' to a string")
        if op == "-":
            return a - b
        if op == "*":
            return a * b
        if op == "/":
            if b == 0:
                raise RuntimeFault("Division by zero")
            return a / b
        if op == ">":
            return 1 if a > b else 0
        if op == "<":
            return 1 if a < b else 0
        raise RuntimeFault(f"Unknown operator {op!r}")

    while pc < len(instructions):
        ins = instructions[pc]
        steps += 1
        if steps > max_steps:
            errors.append({"stage": "run", "line": ins["line"], "col": ins["col"],
                           "message": f"Stopped after {max_steps} steps (possible infinite loop)"})
            break
        try:
            op = ins["op"]
            if op == "assign":
                env[ins["result"]] = value(ins["arg1"])
            elif op == "binop":
                env[ins["result"]] = normalize(check_size(compute(ins["operator"], value(ins["arg1"]), value(ins["arg2"]))))
            elif op == "print":
                if len(output) >= MAX_OUTPUT_LINES:
                    raise RuntimeFault(f"Output limit reached ({MAX_OUTPUT_LINES} lines)")
                output.append(show(value(ins["arg1"])))
            elif op == "goto":
                pc = labels[ins["target"]]
                continue
            elif op == "iffalse":
                if not value(ins["arg1"]):
                    pc = labels[ins["target"]]
                    continue
        except RuntimeFault as err:
            errors.append({"stage": "run", "line": ins["line"], "col": ins["col"], "message": str(err)})
            break
        pc += 1

    return {"stage": "run", "ok": not errors, "output": output, "errors": errors, "steps": steps}
