"""Calculator Tool Implementation (SOLID - SRP / LSP)."""

import ast
import operator
import time
from typing import Any
from src.tools.contracts.tool import BaseTool, ToolMetadata, ToolResult


class CalculatorTool(BaseTool):
    """Safely evaluates mathematical expressions without shell injection risk."""

    _OPERATORS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
    }

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="calculator",
            description="Evaluates mathematical arithmetic expressions (e.g. '2 + 2 * 10').",
            parameters_schema={
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Mathematical expression string to evaluate"
                    }
                },
                "required": ["expression"]
            }
        )

    def _eval_node(self, node: ast.AST) -> float:
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        elif isinstance(node, ast.BinOp):
            left = self._eval_node(node.left)
            right = self._eval_node(node.right)
            op_type = type(node.op)
            if op_type in self._OPERATORS:
                return self._OPERATORS[op_type](left, right)
        elif isinstance(node, ast.UnaryOp):
            operand = self._eval_node(node.operand)
            op_type = type(node.op)
            if op_type in self._OPERATORS:
                return self._OPERATORS[op_type](operand)
        raise ValueError(f"Unsupported AST node or operation: {ast.dump(node)}")

    async def execute(self, **kwargs: Any) -> ToolResult:
        start_time = time.time()
        expression = kwargs.get("expression", "").strip()

        if not expression:
            return ToolResult(
                tool_name="calculator",
                success=False,
                output=None,
                error="No expression provided."
            )

        try:
            parsed_ast = ast.parse(expression, mode="eval")
            calc_result = self._eval_node(parsed_ast.body)
            duration = round((time.time() - start_time) * 1000, 2)
            return ToolResult(
                tool_name="calculator",
                success=True,
                output=calc_result,
                execution_time_ms=duration
            )
        except Exception as e:
            return ToolResult(
                tool_name="calculator",
                success=False,
                output=None,
                error=f"Calculation error: {str(e)}"
            )
