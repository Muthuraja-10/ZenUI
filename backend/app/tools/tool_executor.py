from __future__ import annotations

import inspect

from app.tools.tool_models import (
    ToolCall,
    ToolResult,
)

from app.tools.tool_registry import (
    ToolRegistry,
)


# ============================================================
# TOOL EXECUTOR
# ============================================================


class ToolExecutor:
    """
    Executes ToolCall objects using ToolRegistry.

    This class does not select tools.
    """

    def __init__(
        self,
        registry: ToolRegistry,
    ) -> None:

        self.registry = registry

    # ========================================================
    # EXECUTE
    # ========================================================

    async def execute(
        self,
        call: ToolCall,
    ) -> ToolResult:

        try:

            tool = self.registry.get(
                call.tool_name
            )

            result = tool.function(
                **call.arguments
            )

            if inspect.isawaitable(
                result
            ):

                result = await result

            return ToolResult(
                success=True,
                tool_name=call.tool_name,
                data=result,
            )

        except Exception as error:

            return ToolResult(
                success=False,
                tool_name=call.tool_name,
                data=None,
                error=str(error),
            )

    # ========================================================
    # EXECUTE MANY
    # ========================================================

    async def execute_many(
        self,
        calls: list[ToolCall],
    ) -> list[ToolResult]:

        results: list[
            ToolResult
        ] = []

        for call in calls:

            results.append(
                await self.execute(
                    call
                )
            )

        return results