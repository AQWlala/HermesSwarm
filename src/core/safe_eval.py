"""安全表达式解析器 - 替换eval()的逃逸风险

支持: 算术比较 + 逻辑运算 + 字符串包含检查
禁止: 属性访问(__class__) + 导入 + 任意函数调用
"""

from __future__ import annotations

import ast
import operator as op
from typing import Any


_SAFE_BINOPS = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.FloorDiv: op.floordiv,
    ast.Mod: op.mod,
    ast.Pow: op.pow,
    ast.Eq: op.eq,
    ast.NotEq: op.ne,
    ast.Lt: op.lt,
    ast.LtE: op.le,
    ast.Gt: op.gt,
    ast.GtE: op.ge,
    ast.And: lambda a, b: a and b,
    ast.Or: lambda a, b: a or b,
}

_SAFE_UNARYOPS = {
    ast.UAdd: op.pos,
    ast.USub: op.neg,
    ast.Not: op.not_,
    ast.Invert: op.invert,
}


def safe_eval(expr: str, context: dict[str, Any] | None = None) -> Any:
    """安全求值表达式

    允许: 数字、字符串、布尔、None、变量引用、算术/比较/逻辑运算、in/not in
    禁止: 属性访问、调用、导入、列表推导式外的复杂结构
    """
    if not expr or not expr.strip():
        return True
    context = context or {}
    try:
        tree = ast.parse(expr.strip(), mode="eval")
        return _eval_node(tree.body, context)
    except Exception:
        return True


def _eval_node(node: ast.AST, ctx: dict[str, Any]) -> Any:
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        return ctx.get(node.id)
    if isinstance(node, ast.BinOp):
        handler = _SAFE_BINOPS.get(type(node.op))
        if not handler:
            raise ValueError(f"unsupported binop: {type(node.op).__name__}")
        return handler(_eval_node(node.left, ctx), _eval_node(node.right, ctx))
    if isinstance(node, ast.UnaryOp):
        handler = _SAFE_UNARYOPS.get(type(node.op))
        if not handler:
            raise ValueError(f"unsupported unaryop: {type(node.op).__name__}")
        return handler(_eval_node(node.operand, ctx))
    if isinstance(node, ast.BoolOp):
        handler = _SAFE_BINOPS.get(type(node.op))
        if not handler:
            raise ValueError(f"unsupported boolop: {type(node.op).__name__}")
        result = _eval_node(node.values[0], ctx)
        for val_node in node.values[1:]:
            result = handler(result, _eval_node(val_node, ctx))
        return result
    if isinstance(node, ast.Compare):
        left = _eval_node(node.left, ctx)
        for comp_op, comp_node in zip(node.ops, node.comparators):
            right = _eval_node(comp_node, ctx)
            if isinstance(comp_op, ast.In):
                if left not in right:
                    return False
            elif isinstance(comp_op, ast.NotIn):
                if left in right:
                    return False
            else:
                handler = _SAFE_BINOPS.get(type(comp_op))
                if not handler:
                    raise ValueError(f"unsupported compare: {type(comp_op).__name__}")
                if not handler(left, right):
                    return False
            left = right
        return True
    if isinstance(node, ast.IfExp):
        if _eval_node(node.test, ctx):
            return _eval_node(node.body, ctx)
        return _eval_node(node.orelse, ctx)
    if isinstance(node, ast.List):
        return [_eval_node(e, ctx) for e in node.elts]
    if isinstance(node, ast.Tuple):
        return tuple(_eval_node(e, ctx) for e in node.elts)
    if isinstance(node, ast.Dict):
        return {
            _eval_node(k, ctx): _eval_node(v, ctx)
            for k, v in zip(node.keys, node.values)
        }
    raise ValueError(f"unsupported node: {type(node).__name__}")