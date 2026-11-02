"""
Pipeline glue (API layer)
=========================
This is the only place where the compiler engines meet. Each engine is independent;
here we hand one engine's output to the next and decide when a stage is blocked
because an earlier stage failed.

Stages in order: lexical -> syntax -> semantic -> icg -> run
"""
from .icg import generate
from .interpreter import execute
from .lexer import lex
from .parser import parse
from .semantic import analyze

ORDER = ["lexical", "syntax", "semantic", "icg", "run"]


def _execute(source: str, upto: str) -> dict:
    """Run stages in order up to `upto`; stop at the first stage that fails.

    Lexical errors only block the stages that produce code (icg, run); the syntax and
    semantic stages can still be shown for a program with lexical errors.
    """
    strict = upto in ("icg", "run")
    results, tokens, ast, tac = {}, None, None, None
    for stage in ORDER[: ORDER.index(upto) + 1]:
        if stage == "lexical":
            r = lex(source)
            tokens = r["tokens"]
        elif stage == "syntax":
            r = parse(tokens)
            ast = r["ast"]
        elif stage == "semantic":
            r = analyze(ast)
        elif stage == "icg":
            r = generate(ast)
            tac = r["instructions"]
        else:
            r = execute(tac)
        results[stage] = r
        if not r["ok"] and (stage != "lexical" or strict):
            break
    return results


def run_single(source: str, stage: str) -> dict:
    """Result of one stage; if an earlier stage failed, a blocked result explaining why."""
    results = _execute(source, stage)
    blocker = list(results)[-1]
    if blocker == stage:                 # the stage itself ran (it may have found errors)
        return results[stage]
    failed = results[blocker]
    blocked = {"stage": stage, "ok": False, "blocked_by": blocker,
               "errors": failed["errors"], "message": f"Fix the {blocker} errors first"}
    if stage == "semantic":
        blocked["symbol_table"] = []
    if stage == "icg":
        blocked["instructions"] = []
    if stage == "run":
        blocked["output"] = []
    return blocked


def run_all(source: str) -> dict:
    """The complete compilation: every stage, then the program's output."""
    results = _execute(source, "run")
    stages = {}
    stopped_at = None
    for stage in ORDER:
        if stage in results:
            stages[stage] = results[stage]
            if not results[stage]["ok"] and stopped_at is None:
                stopped_at = stage
        else:
            stages[stage] = {"stage": stage, "ok": None, "status": "skipped", "errors": []}
    ok = stopped_at is None
    return {
        "stage": "full",
        "ok": ok,
        "stopped_at": stopped_at,
        "stages": stages,
        "output": stages["run"].get("output", []) if ok else [],
        "errors": stages[stopped_at]["errors"] if stopped_at else [],
    }
