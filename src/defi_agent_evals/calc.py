"""A safe arithmetic evaluator for the agent's calculator tool (no names, attributes, or calls beyond math)."""

from __future__ import annotations

import ast
import math
import operator

_BIN = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg}
_FUNCS = {"sqrt": math.sqrt, "log": math.log, "exp": math.exp, "abs": abs, "int": int, "float": float}
MAX_INT_BITS = 100_000
MAX_LEN = 2_000


class CalcError(ValueError):
    pass


def evaluate(expr: str) -> int | float:
    if len(expr) > MAX_LEN:
        raise CalcError("expression too long")
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as e:
        raise CalcError(f"syntax error: {e.msg}") from e
    return _eval(tree.body)


def _eval(node: ast.AST) -> int | float:
    if isinstance(node, ast.Constant) and isinstance(node.value, int | float) and not isinstance(node.value, bool):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN:
        left, right = _eval(node.left), _eval(node.right)
        if (
            isinstance(node.op, ast.Pow)
            and isinstance(left, int)
            and isinstance(right, int)
            and abs(left) > 1
            and right * math.log2(abs(left)) > MAX_INT_BITS
        ):
            raise CalcError("integer power too large")
        try:
            return _BIN[type(node.op)](left, right)
        except (ZeroDivisionError, OverflowError) as e:
            raise CalcError(str(e)) from e
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
        return _UNARY[type(node.op)](_eval(node.operand))
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _FUNCS and not node.keywords:
        try:
            return _FUNCS[node.func.id](*[_eval(a) for a in node.args])
        except (ValueError, TypeError, OverflowError) as e:
            raise CalcError(str(e)) from e
    raise CalcError(f"unsupported expression: {ast.dump(node)[:80]}")
